#!/bin/bash
# =============================================================================
# R58 Update Preflight Check Script
# Validates system state before applying an update
# =============================================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_info() { echo -e "[INFO] $1"; }

MANIFEST="${1:-}"
PREFLIGHT_PASSED=true

if [[ -z "$MANIFEST" ]]; then
    echo "Usage: $(basename "$0") <manifest.json>"
    echo ""
    echo "Runs preflight checks before applying an R58 update."
    exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
    log_fail "Manifest file not found: $MANIFEST"
    exit 1
fi

echo "=== R58 Update Preflight Checks ==="
echo ""

# -----------------------------------------------------------------------------
# Check 1: Disk Space
# -----------------------------------------------------------------------------
REQUIRED_MB=$(jq -r '.requirements.disk_mb // 500' "$MANIFEST")
AVAILABLE_MB=$(df -BM /opt 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'M')

# Fallback for macOS
if [[ -z "$AVAILABLE_MB" || "$AVAILABLE_MB" == "0" ]]; then
    AVAILABLE_MB=$(df -m /opt 2>/dev/null | awk 'NR==2 {print $4}')
fi

if [[ "$AVAILABLE_MB" -ge "$REQUIRED_MB" ]]; then
    log_pass "Disk space: ${AVAILABLE_MB}MB available (${REQUIRED_MB}MB required)"
else
    log_fail "Disk space: ${AVAILABLE_MB}MB available, need ${REQUIRED_MB}MB"
    PREFLIGHT_PASSED=false
fi

# -----------------------------------------------------------------------------
# Check 2: Python Version
# -----------------------------------------------------------------------------
REQUIRED_PYTHON=$(jq -r '.requirements.python // ">=3.11"' "$MANIFEST")
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2)

if [[ -n "$PYTHON_VERSION" ]]; then
    # Simple check for 3.11+
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 11 ]]; then
        log_pass "Python version: $PYTHON_VERSION (required: $REQUIRED_PYTHON)"
    else
        log_fail "Python version: $PYTHON_VERSION (required: $REQUIRED_PYTHON)"
        PREFLIGHT_PASSED=false
    fi
else
    log_fail "Python 3 not found"
    PREFLIGHT_PASSED=false
fi

# -----------------------------------------------------------------------------
# Check 3: Current Version Compatibility
# -----------------------------------------------------------------------------
CURRENT_MANIFEST="/opt/r58-app/current/manifest.json"
MIN_VERSION=$(jq -r '.min_version // ""' "$MANIFEST")
NEW_VERSION=$(jq -r '.version' "$MANIFEST")

if [[ -f "$CURRENT_MANIFEST" ]]; then
    CURRENT_VERSION=$(jq -r '.version' "$CURRENT_MANIFEST")
    
    if [[ -n "$MIN_VERSION" ]]; then
        # Simple version comparison (works for semver x.y.z)
        compare_versions() {
            local v1="$1" v2="$2"
            if [[ "$(printf '%s\n' "$v1" "$v2" | sort -V | head -n1)" == "$v2" ]]; then
                return 0  # v1 >= v2
            else
                return 1  # v1 < v2
            fi
        }
        
        if compare_versions "$CURRENT_VERSION" "$MIN_VERSION"; then
            log_pass "Version compatibility: $CURRENT_VERSION >= $MIN_VERSION (min)"
        else
            log_fail "Version compatibility: $CURRENT_VERSION < $MIN_VERSION (min required)"
            PREFLIGHT_PASSED=false
        fi
    else
        log_pass "Version upgrade: $CURRENT_VERSION -> $NEW_VERSION"
    fi
else
    log_info "Fresh installation (no current version)"
fi

# -----------------------------------------------------------------------------
# Check 4: Service Status
# -----------------------------------------------------------------------------
if command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet r58-api 2>/dev/null; then
        log_pass "R58 API service is running"
    else
        log_warn "R58 API service not running (will start after install)"
    fi
else
    log_info "Systemd not available, skipping service check"
fi

# -----------------------------------------------------------------------------
# Check 5: No Active Recording
# -----------------------------------------------------------------------------
RECORDER_URL="${R58_API_URL:-http://localhost:8000}/api/v1/sessions/status"

if curl -sf "$RECORDER_URL" >/dev/null 2>&1; then
    RECORDING_STATUS=$(curl -sf "$RECORDER_URL" | jq -r '.status // "unknown"')
    
    if [[ "$RECORDING_STATUS" == "recording" ]]; then
        log_fail "Active recording in progress - cannot update now"
        PREFLIGHT_PASSED=false
    elif [[ "$RECORDING_STATUS" == "unknown" ]]; then
        log_warn "Could not determine recording status"
    else
        log_pass "No active recording (status: $RECORDING_STATUS)"
    fi
else
    log_info "API not reachable, skipping recording check"
fi

# -----------------------------------------------------------------------------
# Check 6: RAM Available
# -----------------------------------------------------------------------------
REQUIRED_RAM=$(jq -r '.requirements.ram_mb // 256' "$MANIFEST")

# Get available RAM (works on Linux)
if [[ -f /proc/meminfo ]]; then
    AVAILABLE_RAM=$(grep MemAvailable /proc/meminfo | awk '{print int($2/1024)}')
    
    if [[ "$AVAILABLE_RAM" -ge "$REQUIRED_RAM" ]]; then
        log_pass "Available RAM: ${AVAILABLE_RAM}MB (${REQUIRED_RAM}MB required)"
    else
        log_warn "Low RAM: ${AVAILABLE_RAM}MB available (${REQUIRED_RAM}MB recommended)"
    fi
else
    log_info "Cannot check RAM (not Linux), skipping"
fi

# -----------------------------------------------------------------------------
# Check 7: Network Connectivity (if update server configured)
# -----------------------------------------------------------------------------
UPDATE_SERVER="${R58_UPDATE_SERVER:-}"

if [[ -n "$UPDATE_SERVER" ]]; then
    if curl -sf "${UPDATE_SERVER}/health" >/dev/null 2>&1; then
        log_pass "Update server reachable: $UPDATE_SERVER"
    else
        log_warn "Update server not reachable: $UPDATE_SERVER"
    fi
fi

# -----------------------------------------------------------------------------
# Check 8: Required Directories Writable
# -----------------------------------------------------------------------------
DIRS_TO_CHECK=(
    "/opt/r58-app/releases"
    "/opt/r58-app/shared/config"
    "/opt/r58-app/shared/logs"
)

for dir in "${DIRS_TO_CHECK[@]}"; do
    if [[ -d "$dir" ]]; then
        if [[ -w "$dir" ]]; then
            log_pass "Directory writable: $dir"
        else
            log_fail "Directory not writable: $dir"
            PREFLIGHT_PASSED=false
        fi
    else
        log_info "Directory will be created: $dir"
    fi
done

# -----------------------------------------------------------------------------
# Check 9: GPG Signature (if signature file exists)
# -----------------------------------------------------------------------------
RELEASE_DIR="$(dirname "$MANIFEST")"
TARBALL=$(ls "${RELEASE_DIR}"/*.tar.gz 2>/dev/null | head -1 || echo "")
SIGNATURE="${TARBALL}.asc"

if [[ -f "$SIGNATURE" ]]; then
    if gpg --verify "$SIGNATURE" "$TARBALL" 2>/dev/null; then
        log_pass "Release signature verified"
    else
        log_fail "Release signature verification failed"
        PREFLIGHT_PASSED=false
    fi
else
    log_info "No signature file, skipping GPG verification"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=== Preflight Summary ==="

if $PREFLIGHT_PASSED; then
    log_pass "All preflight checks passed!"
    echo ""
    echo "Ready to proceed with update to version $NEW_VERSION"
    exit 0
else
    log_fail "Some preflight checks failed!"
    echo ""
    echo "Please resolve the issues above before proceeding with the update."
    exit 1
fi

