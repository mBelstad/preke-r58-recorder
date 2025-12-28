#!/bin/bash
# =============================================================================
# R58 Release Build Script
# Creates a versioned, signed release artifact ready for deployment
# =============================================================================
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/dist"
ARCH="${ARCH:-arm64}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Build a release artifact for R58 deployment.

Options:
    -v, --version VERSION    Version tag (e.g., v1.0.0). If not provided, uses git describe.
    -c, --channel CHANNEL    Release channel: stable, beta, dev (default: stable)
    -a, --arch ARCH          Target architecture: arm64, amd64 (default: arm64)
    -s, --sign               Sign the release with GPG
    -o, --output DIR         Output directory (default: ./dist)
    -h, --help               Show this help message

Examples:
    $(basename "$0") -v v1.0.0 -c stable -s
    $(basename "$0") --version v1.1.0-beta.1 --channel beta
EOF
    exit 1
}

# Parse arguments
VERSION=""
CHANNEL="stable"
SIGN=false
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version) VERSION="$2"; shift 2 ;;
        -c|--channel) CHANNEL="$2"; shift 2 ;;
        -a|--arch) ARCH="$2"; shift 2 ;;
        -s|--sign) SIGN=true; shift ;;
        -o|--output) OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

# Determine version from git if not provided
if [[ -z "$VERSION" ]]; then
    VERSION=$(git describe --tags --always 2>/dev/null || echo "dev")
    log_info "Using version from git: $VERSION"
fi

# Strip 'v' prefix if present for manifest
VERSION_NUM="${VERSION#v}"

# Set output directory
OUTPUT_DIR="${OUTPUT_DIR:-$BUILD_DIR}"
mkdir -p "$OUTPUT_DIR"

# Release artifact name
RELEASE_NAME="r58-${VERSION}-${ARCH}"
RELEASE_DIR="${OUTPUT_DIR}/${RELEASE_NAME}"
RELEASE_TARBALL="${OUTPUT_DIR}/${RELEASE_NAME}.tar.gz"

log_info "Building release: $RELEASE_NAME"
log_info "Channel: $CHANNEL"
log_info "Architecture: $ARCH"

# =============================================================================
# Step 1: Clean and prepare build directory
# =============================================================================
log_info "Preparing build directory..."
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"/{packages,scripts,systemd,config,migrations}

# =============================================================================
# Step 2: Copy backend code
# =============================================================================
log_info "Copying backend code..."
cp -r "${PROJECT_ROOT}/packages/backend/r58_api" "${RELEASE_DIR}/packages/backend/"
cp "${PROJECT_ROOT}/packages/backend/requirements.txt" "${RELEASE_DIR}/packages/backend/"
cp "${PROJECT_ROOT}/packages/backend/pyproject.toml" "${RELEASE_DIR}/packages/backend/" 2>/dev/null || true

# Remove __pycache__ directories
find "${RELEASE_DIR}/packages/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${RELEASE_DIR}/packages/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Step 3: Build frontend (if exists)
# =============================================================================
if [[ -d "${PROJECT_ROOT}/packages/frontend" ]]; then
    log_info "Building frontend..."
    cd "${PROJECT_ROOT}/packages/frontend"
    
    if [[ -f "package.json" ]]; then
        npm ci --silent 2>/dev/null || npm install --silent
        npm run build 2>/dev/null || log_warn "Frontend build failed, skipping"
        
        if [[ -d "dist" ]]; then
            cp -r dist "${RELEASE_DIR}/packages/frontend/"
        fi
    fi
    
    cd "$PROJECT_ROOT"
else
    log_warn "No frontend directory found, skipping frontend build"
fi

# =============================================================================
# Step 4: Copy scripts
# =============================================================================
log_info "Copying deployment scripts..."
cat > "${RELEASE_DIR}/scripts/install.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Fresh installation of R58 release
set -e

RELEASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="/opt/r58-app"

echo "Installing R58 from $RELEASE_DIR..."

# Create directory structure
sudo mkdir -p "$TARGET_DIR"/{releases,shared/{recordings,config,logs,db},scripts,keys}
sudo chown -R $(whoami):$(whoami) "$TARGET_DIR"

# Get version from manifest
VERSION=$(jq -r '.version' "$RELEASE_DIR/manifest.json")

# Copy release
cp -r "$RELEASE_DIR" "$TARGET_DIR/releases/$VERSION"

# Create virtualenv and install dependencies
cd "$TARGET_DIR/releases/$VERSION"
python3 -m venv venv
source venv/bin/activate
pip install -q -r packages/backend/requirements.txt

# Create symlinks
ln -sf "$TARGET_DIR/shared/recordings" "$TARGET_DIR/releases/$VERSION/recordings"
ln -sf "$TARGET_DIR/shared/config" "$TARGET_DIR/releases/$VERSION/config"

# Set as current
ln -sfn "$TARGET_DIR/releases/$VERSION" "$TARGET_DIR/current"

# Install systemd service
sudo cp "$RELEASE_DIR/systemd/r58-api.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable r58-api

echo "Installation complete. Start with: sudo systemctl start r58-api"
INSTALL_SCRIPT
chmod +x "${RELEASE_DIR}/scripts/install.sh"

cat > "${RELEASE_DIR}/scripts/upgrade.sh" << 'UPGRADE_SCRIPT'
#!/bin/bash
# Upgrade from previous version
set -e

RELEASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="/opt/r58-app"

echo "Upgrading R58..."

# Get version from manifest
VERSION=$(jq -r '.version' "$RELEASE_DIR/manifest.json")

# Run preflight checks
if [[ -x "$TARGET_DIR/scripts/update-preflight.sh" ]]; then
    "$TARGET_DIR/scripts/update-preflight.sh" "$RELEASE_DIR/manifest.json"
fi

# Stop service
sudo systemctl stop r58-api || true

# Backup current version info
CURRENT_VERSION=$(cat "$TARGET_DIR/current/manifest.json" 2>/dev/null | jq -r '.version' || echo "unknown")
echo "Upgrading from $CURRENT_VERSION to $VERSION"

# Copy release
cp -r "$RELEASE_DIR" "$TARGET_DIR/releases/$VERSION"

# Create virtualenv and install dependencies
cd "$TARGET_DIR/releases/$VERSION"
python3 -m venv venv
source venv/bin/activate
pip install -q -r packages/backend/requirements.txt

# Run migrations
if [[ -d "$TARGET_DIR/releases/$VERSION/migrations" ]]; then
    echo "Running migrations..."
    python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '$TARGET_DIR/releases/$VERSION/packages/backend')
from r58_api.migrations import run_pending_migrations
run_pending_migrations(
    Path('$TARGET_DIR/shared/db/r58.db'),
    Path('$TARGET_DIR/releases/$VERSION/migrations')
)
" 2>/dev/null || echo "No migrations to run"
fi

# Create symlinks
ln -sf "$TARGET_DIR/shared/recordings" "$TARGET_DIR/releases/$VERSION/recordings"
ln -sf "$TARGET_DIR/shared/config" "$TARGET_DIR/releases/$VERSION/config"

# Switch to new version (atomic)
ln -sfn "$TARGET_DIR/releases/$VERSION" "$TARGET_DIR/current"

# Update systemd service if changed
sudo cp "$RELEASE_DIR/systemd/r58-api.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Start service
sudo systemctl start r58-api

# Health check
sleep 3
if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    echo "Upgrade to $VERSION complete!"
else
    echo "Health check failed! Rolling back..."
    ln -sfn "$TARGET_DIR/releases/$CURRENT_VERSION" "$TARGET_DIR/current"
    sudo systemctl restart r58-api
    exit 1
fi
UPGRADE_SCRIPT
chmod +x "${RELEASE_DIR}/scripts/upgrade.sh"

cat > "${RELEASE_DIR}/scripts/rollback.sh" << 'ROLLBACK_SCRIPT'
#!/bin/bash
# Emergency rollback to previous version
set -e

TARGET_DIR="/opt/r58-app"
CURRENT=$(readlink "$TARGET_DIR/current")

# Find previous release
RELEASES=($(ls -t "$TARGET_DIR/releases"))
PREVIOUS=""

for REL in "${RELEASES[@]}"; do
    if [ "$TARGET_DIR/releases/$REL" != "$CURRENT" ]; then
        PREVIOUS=$REL
        break
    fi
done

if [ -z "$PREVIOUS" ]; then
    echo "ERROR: No previous release found to rollback to"
    exit 1
fi

echo "Rolling back from $(basename $CURRENT) to $PREVIOUS..."

# Switch symlink
ln -sfn "$TARGET_DIR/releases/$PREVIOUS" "$TARGET_DIR/current"

# Restart service
sudo systemctl restart r58-api

# Health check
sleep 3
if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    echo "Rollback to $PREVIOUS complete!"
else
    echo "WARNING: Health check failed after rollback"
    exit 1
fi
ROLLBACK_SCRIPT
chmod +x "${RELEASE_DIR}/scripts/rollback.sh"

# =============================================================================
# Step 5: Copy systemd unit
# =============================================================================
log_info "Creating systemd unit..."
cat > "${RELEASE_DIR}/systemd/r58-api.service" << 'SERVICE'
[Unit]
Description=R58 API
After=network.target mediamtx.service
Wants=mediamtx.service

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/r58-app/current
Environment="PATH=/opt/r58-app/current/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/r58-app/current/packages/backend"
ExecStartPre=-/usr/bin/pkill -9 gst-plugin-scanner
ExecStartPre=-/bin/sleep 1
ExecStartPre=-/opt/r58-app/current/scripts/init_hdmi_inputs.sh
ExecStart=/opt/r58-app/current/venv/bin/uvicorn r58_api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
WatchdogSec=60

[Install]
WantedBy=multi-user.target
SERVICE

# =============================================================================
# Step 6: Create example config
# =============================================================================
log_info "Creating example config..."
cat > "${RELEASE_DIR}/config/r58.env.example" << 'CONFIG'
# R58 Configuration
# Copy this file to /opt/r58-app/shared/config/r58.env and customize

# API Settings
R58_API_HOST=0.0.0.0
R58_API_PORT=8000
R58_DEBUG=false

# Authentication
R58_JWT_SECRET=change-this-to-a-secure-random-string

# Database
R58_DB_PATH=/opt/r58-app/shared/db/r58.db

# MediaMTX
R58_MEDIAMTX_API_URL=http://localhost:9997
R58_MEDIAMTX_WHEP_BASE=http://localhost:8889

# VDO.ninja
R58_VDONINJA_ENABLED=true
R58_VDONINJA_PORT=8443
R58_VDONINJA_ROOM=studio

# Fleet Management
R58_FLEET_ENABLED=false
R58_FLEET_API_URL=https://fleet.r58.itagenten.no
R58_DEVICE_ID=r58-change-me

# Inputs
R58_ENABLED_INPUTS=cam1,cam2
CONFIG

# =============================================================================
# Step 7: Generate manifest
# =============================================================================
log_info "Generating manifest..."
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Calculate checksums
BACKEND_CHECKSUM=$(find "${RELEASE_DIR}/packages/backend" -type f -exec sha256sum {} \; | sha256sum | cut -d' ' -f1)
FRONTEND_CHECKSUM=""
if [[ -d "${RELEASE_DIR}/packages/frontend" ]]; then
    FRONTEND_CHECKSUM=$(find "${RELEASE_DIR}/packages/frontend" -type f -exec sha256sum {} \; | sha256sum | cut -d' ' -f1)
fi

# Find migrations
MIGRATIONS="[]"
if [[ -d "${RELEASE_DIR}/migrations" ]] && [[ -n "$(ls -A ${RELEASE_DIR}/migrations/*.py 2>/dev/null)" ]]; then
    MIGRATIONS=$(ls "${RELEASE_DIR}/migrations"/*.py 2>/dev/null | xargs -I {} basename {} .py | jq -R . | jq -s .)
fi

cat > "${RELEASE_DIR}/manifest.json" << EOF
{
  "version": "${VERSION_NUM}",
  "channel": "${CHANNEL}",
  "build_date": "${BUILD_DATE}",
  "git_sha": "${GIT_SHA}",
  "arch": "${ARCH}",
  "min_version": "1.0.0",
  "checksums": {
    "packages/backend": "sha256:${BACKEND_CHECKSUM}",
    "packages/frontend": "sha256:${FRONTEND_CHECKSUM:-none}"
  },
  "requirements": {
    "python": ">=3.11",
    "disk_mb": 500,
    "ram_mb": 256
  },
  "migrations": ${MIGRATIONS}
}
EOF

# =============================================================================
# Step 8: Copy CHANGELOG if exists
# =============================================================================
if [[ -f "${PROJECT_ROOT}/CHANGELOG.md" ]]; then
    cp "${PROJECT_ROOT}/CHANGELOG.md" "${RELEASE_DIR}/"
fi

# =============================================================================
# Step 9: Create tarball
# =============================================================================
log_info "Creating release tarball..."
cd "$OUTPUT_DIR"
tar -czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"

# Calculate tarball checksum
TARBALL_SHA256=$(sha256sum "${RELEASE_NAME}.tar.gz" | cut -d' ' -f1)
echo "$TARBALL_SHA256  ${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.tar.gz.sha256"

# =============================================================================
# Step 10: Sign release (optional)
# =============================================================================
if [[ "$SIGN" == "true" ]]; then
    log_info "Signing release..."
    if gpg --list-keys r58-release@itagenten.no >/dev/null 2>&1; then
        gpg --armor --detach-sign -u r58-release@itagenten.no "${RELEASE_NAME}.tar.gz"
        log_info "Release signed: ${RELEASE_NAME}.tar.gz.asc"
    else
        log_warn "GPG key not found, skipping signing"
    fi
fi

# =============================================================================
# Step 11: Cleanup and summary
# =============================================================================
rm -rf "$RELEASE_DIR"

log_info "=============================================="
log_info "Release build complete!"
log_info "=============================================="
log_info "Artifact: ${RELEASE_TARBALL}"
log_info "Size: $(du -h "${RELEASE_TARBALL}" | cut -f1)"
log_info "SHA256: ${TARBALL_SHA256}"
log_info ""
log_info "To deploy:"
log_info "  1. Copy to device: scp ${RELEASE_TARBALL} user@device:/tmp/"
log_info "  2. Extract: tar -xzf ${RELEASE_NAME}.tar.gz -C /tmp/"
log_info "  3. Install: /tmp/${RELEASE_NAME}/scripts/install.sh"
log_info "  4. Or upgrade: /tmp/${RELEASE_NAME}/scripts/upgrade.sh"

