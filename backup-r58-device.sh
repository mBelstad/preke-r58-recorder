#!/bin/bash
# R58 Device Backup Script
# Creates a complete backup of the R58 device to a USB memory stick
# Excludes video files and recording directories to keep size manageable

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONNECT_SCRIPT="${SCRIPT_DIR}/connect-r58-frp.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if connect script exists
if [[ ! -f "$CONNECT_SCRIPT" ]]; then
    error "Connection script not found: $CONNECT_SCRIPT"
    exit 1
fi

# Make connect script executable
chmod +x "$CONNECT_SCRIPT"

info "Starting R58 device backup..."
info "This will create a backup on the USB stick connected to the R58 device"
echo ""

# Check connection to R58
info "Checking connection to R58 device..."
if ! "$CONNECT_SCRIPT" "hostname" > /dev/null 2>&1; then
    error "Cannot connect to R58 device. Please check your connection."
    exit 1
fi

R58_HOSTNAME=$("$CONNECT_SCRIPT" "hostname" 2>/dev/null | tr -d '\r\n')
info "Connected to: $R58_HOSTNAME"
echo ""

# Create the backup script that will run on R58
BACKUP_SCRIPT_CONTENT=$(cat <<'R58_BACKUP_EOF'
#!/bin/bash
# Backup script that runs on R58 device

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# USB device and mount point
USB_DEVICE="/dev/sda1"
MOUNT_POINT="/mnt/usb_backup"
BACKUP_BASE_DIR="$MOUNT_POINT/r58-backups"

# Check if USB device exists
if [[ ! -b "$USB_DEVICE" ]]; then
    error "USB device not found: $USB_DEVICE"
    error "Please ensure USB stick is connected to the R58 device"
    exit 1
fi

info "USB device found: $USB_DEVICE"

# Check if already mounted
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    info "USB stick already mounted at $MOUNT_POINT"
elif mountpoint -q "/media/linaro" 2>/dev/null; then
    MOUNT_POINT="/media/linaro"
    BACKUP_BASE_DIR="$MOUNT_POINT/r58-backups"
    info "USB stick already mounted at $MOUNT_POINT"
elif mountpoint -q "/mnt/udisk" 2>/dev/null; then
    MOUNT_POINT="/mnt/udisk"
    BACKUP_BASE_DIR="$MOUNT_POINT/r58-backups"
    info "USB stick already mounted at $MOUNT_POINT"
else
    # Create mount point
    sudo mkdir -p "$MOUNT_POINT"
    
    # Mount USB stick
    info "Mounting USB stick to $MOUNT_POINT..."
    if ! sudo mount -o uid=1000,gid=1000,umask=0002 "$USB_DEVICE" "$MOUNT_POINT" 2>/dev/null; then
        error "Failed to mount USB stick"
        exit 1
    fi
    info "USB stick mounted successfully"
fi

# Check available space
AVAILABLE_SPACE=$(df -BG "$MOUNT_POINT" | tail -1 | awk '{print $4}' | sed 's/G//')
MIN_REQUIRED=2.5  # Backup is ~1.5-2GB, need at least 2.5GB with margin

# Check if we have enough space (backup is ~1.5-2GB compressed)
if [[ $AVAILABLE_SPACE -lt $MIN_REQUIRED ]]; then
    warn "Warning: Only ${AVAILABLE_SPACE}GB available, recommended ${MIN_REQUIRED}GB"
    # Auto-continue if we have at least 2GB (backup should fit)
    if [[ $AVAILABLE_SPACE -ge 2 ]]; then
        warn "Continuing anyway (backup should fit in ${AVAILABLE_SPACE}GB)"
    else
        error "Not enough space. Need at least ${MIN_REQUIRED}GB, have ${AVAILABLE_SPACE}GB"
        exit 1
    fi
else
    info "Available space: ${AVAILABLE_SPACE}GB (sufficient)"
fi

# Create backup directory
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/r58-backup-$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
info "Backup directory: $BACKUP_DIR"

# System information snapshot
info "Capturing system information..."
{
    echo "=== R58 Device System Information ==="
    echo "Backup Date: $(date)"
    echo "Hostname: $(hostname)"
    echo ""
    echo "=== System ==="
    uname -a
    echo ""
    echo "=== Disk Usage ==="
    df -h
    echo ""
    echo "=== Installed Packages ==="
    dpkg -l | grep -E "^ii" | wc -l | xargs echo "Total packages:"
    echo ""
    echo "=== Services ==="
    systemctl list-units --type=service --state=running | grep -E "preke|mediamtx|frp|tailscale" || echo "No matching services found"
    echo ""
    echo "=== Network ==="
    ip addr show | grep -E "inet |inet6 " || ifconfig | grep -E "inet "
} > "$BACKUP_DIR/system-info.txt"
info "System information saved"

# Create backup archive
BACKUP_ARCHIVE="$BACKUP_DIR/r58-backup.tar.gz"

info "Creating backup archive..."
info "This may take 10-20 minutes depending on system size..."

# Tar exclusions
EXCLUDE_PATTERNS=(
    --exclude='/proc'
    --exclude='/sys'
    --exclude='/dev'
    --exclude='/tmp'
    --exclude='/run'
    --exclude='/mnt'
    --exclude='/media'
    --exclude='/lost+found'
    --exclude='/var/cache'
    --exclude='/var/tmp'
    --exclude='*.mkv'
    --exclude='*.mp4'
    --exclude='*.mov'
    --exclude='*.avi'
    --exclude='*.m4v'
    --exclude='*.flv'
    --exclude='*.webm'
    --exclude='*.ts'
    --exclude='*.m2ts'
    --exclude='*.3gp'
    --exclude='recordings'
    --exclude='videos'
)

# Create tar archive with progress if pv is available, otherwise use verbose
# Use sudo to access root-owned files
info "Backing up with root privileges to include all system files..."
if command -v pv >/dev/null 2>&1; then
    sudo tar -czf - "${EXCLUDE_PATTERNS[@]}" \
        -C / \
        etc home opt root usr/local var/lib var/log var/backups var/spool var/mail var/opt var/local boot \
        2>/dev/null | pv -s 3100m > "$BACKUP_ARCHIVE"
else
    info "Using tar with verbose output (install 'pv' for progress bar)"
    sudo tar -czf "$BACKUP_ARCHIVE" \
        "${EXCLUDE_PATTERNS[@]}" \
        -C / \
        etc home opt root usr/local var/lib var/log var/backups var/spool var/mail var/opt var/local boot \
        2>&1 | grep -v "tar: Removing leading" | tail -20
fi

if [[ ! -f "$BACKUP_ARCHIVE" ]] || [[ ! -s "$BACKUP_ARCHIVE" ]]; then
    error "Backup archive creation failed"
    exit 1
fi

# Change ownership to linaro user so it can be accessed
sudo chown linaro:linaro "$BACKUP_ARCHIVE"

BACKUP_SIZE=$(du -h "$BACKUP_ARCHIVE" | cut -f1)
info "Backup archive created: $BACKUP_SIZE"

# Generate manifest
info "Generating file manifest..."
tar -tzf "$BACKUP_ARCHIVE" > "$BACKUP_DIR/manifest.txt" 2>/dev/null

# Count files
FILE_COUNT=$(wc -l < "$BACKUP_DIR/manifest.txt")
info "Backup contains $FILE_COUNT files"

# Generate checksum
info "Generating backup checksum..."
CHECKSUM=$(sha256sum "$BACKUP_ARCHIVE" | cut -d' ' -f1)

# Create backup metadata
cat > "$BACKUP_DIR/backup-info.json" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "hostname": "$(hostname)",
  "backup_size": "$BACKUP_SIZE",
  "file_count": $FILE_COUNT,
  "sha256_checksum": "$CHECKSUM",
  "archive_path": "r58-backup.tar.gz"
}
EOF

# Verify archive integrity
info "Verifying backup integrity..."
if tar -tzf "$BACKUP_ARCHIVE" > /dev/null 2>&1; then
    info "Backup archive integrity verified"
else
    error "Backup archive integrity check failed"
    exit 1
fi

# Create restore script
info "Creating restoration script..."
cat > "$BACKUP_DIR/restore-r58.sh" <<'RESTORE_EOF'
#!/bin/bash
# R58 Device Restoration Script
# Restores the R58 device from backup archive

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ARCHIVE="$SCRIPT_DIR/r58-backup.tar.gz"
BACKUP_INFO="$SCRIPT_DIR/backup-info.json"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

# Check if backup exists
if [[ ! -f "$BACKUP_ARCHIVE" ]]; then
    error "Backup archive not found: $BACKUP_ARCHIVE"
    exit 1
fi

# Display backup info
if [[ -f "$BACKUP_INFO" ]]; then
    info "Backup Information:"
    cat "$BACKUP_INFO" | grep -E "timestamp|hostname|backup_size" | sed 's/"/ /g' | sed 's/,//'
    echo ""
fi

# Warning
warn "WARNING: This will restore files to the R58 device filesystem"
warn "This may overwrite existing files and configurations"
echo ""
read -p "Are you sure you want to continue? (yes/NO): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    info "Restoration cancelled"
    exit 0
fi

# Verify archive integrity
info "Verifying backup archive integrity..."
if ! tar -tzf "$BACKUP_ARCHIVE" > /dev/null 2>&1; then
    error "Backup archive is corrupted or invalid"
    exit 1
fi
info "Archive integrity verified"

# Extract backup
info "Extracting backup archive..."
info "This may take 10-20 minutes..."

tar -xzf "$BACKUP_ARCHIVE" -C / \
    --exclude='./proc' \
    --exclude='./sys' \
    --exclude='./dev' \
    --exclude='./tmp' \
    --exclude='./run' \
    --exclude='./mnt' \
    --exclude='./media' \
    2>&1 | grep -v "tar: Removing leading" | tail -20

if [[ $? -eq 0 ]]; then
    info "Backup restored successfully"
    info "You may need to restart services or reboot the device"
else
    error "Restoration failed"
    exit 1
fi
RESTORE_EOF

chmod +x "$BACKUP_DIR/restore-r58.sh"

# Create README
cat > "$BACKUP_DIR/README.txt" <<EOF
R58 Device Backup
==================

Backup Date: $(date)
Hostname: $(hostname)
Backup Size: $BACKUP_SIZE
Files: $FILE_COUNT

SHA256 Checksum: $CHECKSUM

To restore this backup:

1. Connect this USB stick to the R58 device
2. Mount the USB stick (if not auto-mounted):
   sudo mkdir -p /mnt/usb_backup
   sudo mount /dev/sda1 /mnt/usb_backup

3. Navigate to backup directory:
   cd /mnt/usb_backup/r58-backups/r58-backup-$TIMESTAMP

4. Run restoration script:
   sudo bash restore-r58.sh

Or manually extract:
   sudo tar -xzf r58-backup.tar.gz -C /

WARNING: Restoration will overwrite existing files!
EOF

info ""
info "=== Backup Complete ==="
info "Location: $BACKUP_DIR"
info "Archive: r58-backup.tar.gz ($BACKUP_SIZE)"
info "Files: $FILE_COUNT"
info "Checksum: $CHECKSUM"
info ""
info "Backup saved to USB stick successfully!"
R58_BACKUP_EOF
)

# Encode script to base64 and transfer to R58
info "Transferring backup script to R58 device..."
TEMP_SCRIPT="/tmp/r58-backup-script-$$.sh"

# Write script to R58 using base64 encoding
echo "$BACKUP_SCRIPT_CONTENT" | base64 | "$CONNECT_SCRIPT" "base64 -d > $TEMP_SCRIPT && chmod +x $TEMP_SCRIPT"

# Execute backup script on R58
info "Executing backup on R58 device..."
echo ""

"$CONNECT_SCRIPT" "bash $TEMP_SCRIPT"

EXIT_CODE=$?

# Clean up temp script
"$CONNECT_SCRIPT" "rm -f $TEMP_SCRIPT" 2>/dev/null || true

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    info "Backup completed successfully!"
    info "The backup is now on the USB stick connected to your R58 device"
else
    error "Backup failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi
