#!/bin/bash
#
# R58 Diagnostics Collection Script
# 
# Collects system information, logs, and health status into a timestamped archive.
# This script is READ-ONLY and does not modify the system.
#
# Usage: ./scripts/collect-diagnostics.sh [output-dir]
#
# Output: r58-diagnostics-YYYYMMDD_HHMMSS.tar.gz
#

set -e

# Configuration
OUTPUT_DIR="${1:-/tmp}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DIAG_DIR="/tmp/r58-diagnostics-${TIMESTAMP}"
ARCHIVE_NAME="r58-diagnostics-${TIMESTAMP}.tar.gz"
API_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create temp directory
mkdir -p "${DIAG_DIR}"/{logs,config,system,api}

echo "=========================================="
echo "R58 Diagnostics Collection"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo "Output: ${OUTPUT_DIR}/${ARCHIVE_NAME}"
echo ""

# =============================================================================
# System Information
# =============================================================================
log_info "Collecting system information..."

# Basic system info
{
    echo "=== System Information ==="
    echo "Hostname: $(hostname)"
    echo "Date: $(date)"
    echo "Uptime: $(uptime)"
    echo ""
    echo "=== OS Information ==="
    cat /etc/os-release 2>/dev/null || echo "Unable to read /etc/os-release"
    echo ""
    echo "=== Kernel ==="
    uname -a
    echo ""
    echo "=== Architecture ==="
    uname -m
} > "${DIAG_DIR}/system/system_info.txt" 2>&1

# CPU info
{
    echo "=== CPU Information ==="
    cat /proc/cpuinfo 2>/dev/null | grep -E "^(processor|model name|cpu MHz)" | head -20
    echo ""
    echo "=== CPU Usage ==="
    top -bn1 | head -15
} > "${DIAG_DIR}/system/cpu.txt" 2>&1

# Memory info
{
    echo "=== Memory Information ==="
    free -h
    echo ""
    echo "=== Detailed Memory ==="
    cat /proc/meminfo 2>/dev/null | head -30
} > "${DIAG_DIR}/system/memory.txt" 2>&1

# Disk info
{
    echo "=== Disk Usage ==="
    df -h
    echo ""
    echo "=== Disk Usage (recordings) ==="
    df -h /opt/preke-r58-recorder/recordings 2>/dev/null || df -h /opt/r58/recordings 2>/dev/null || echo "Recordings path not found"
    echo ""
    echo "=== Block Devices ==="
    lsblk 2>/dev/null || echo "lsblk not available"
} > "${DIAG_DIR}/system/disk.txt" 2>&1

# Temperature (RK3588 specific)
{
    echo "=== Temperature ==="
    for zone in /sys/class/thermal/thermal_zone*/temp; do
        if [ -f "$zone" ]; then
            zone_name=$(dirname "$zone" | xargs -I{} cat {}/type 2>/dev/null || echo "unknown")
            temp=$(cat "$zone" 2>/dev/null)
            if [ -n "$temp" ]; then
                echo "${zone_name}: $((temp/1000))°C"
            fi
        fi
    done
} > "${DIAG_DIR}/system/temperature.txt" 2>&1

# Network info
{
    echo "=== Network Interfaces ==="
    ip addr 2>/dev/null || ifconfig 2>/dev/null || echo "No network info available"
    echo ""
    echo "=== Listening Ports ==="
    ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo "No port info available"
    echo ""
    echo "=== DNS Resolution ==="
    cat /etc/resolv.conf 2>/dev/null
} > "${DIAG_DIR}/system/network.txt" 2>&1

# =============================================================================
# Video Devices
# =============================================================================
log_info "Collecting video device information..."

{
    echo "=== Video Devices ==="
    v4l2-ctl --list-devices 2>/dev/null || echo "v4l2-ctl not available"
    echo ""
    
    for dev in /dev/video*; do
        if [ -e "$dev" ]; then
            echo "=== $dev ==="
            v4l2-ctl -d "$dev" --all 2>/dev/null | head -50 || echo "Cannot query $dev"
            echo ""
        fi
    done
} > "${DIAG_DIR}/system/video_devices.txt" 2>&1

# =============================================================================
# Service Status
# =============================================================================
log_info "Collecting service status..."

services=("r58-api" "r58-pipeline" "mediamtx" "vdo-signaling" "vdo-webapp" "frpc" "r58-admin-api")

{
    echo "=== Service Status Overview ==="
    for svc in "${services[@]}"; do
        status=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
        printf "%-20s %s\n" "$svc" "$status"
    done
    echo ""
    
    echo "=== Detailed Service Status ==="
    for svc in "${services[@]}"; do
        echo "--- $svc ---"
        systemctl status "$svc" --no-pager 2>&1 | head -20
        echo ""
    done
} > "${DIAG_DIR}/system/services.txt" 2>&1

# =============================================================================
# Logs
# =============================================================================
log_info "Collecting service logs..."

for svc in "${services[@]}"; do
    journalctl -u "$svc" -n 500 --no-pager 2>/dev/null > "${DIAG_DIR}/logs/${svc}.log" || true
done

# Kernel messages (for hardware issues)
dmesg 2>/dev/null | tail -500 > "${DIAG_DIR}/logs/dmesg.log" || true

# =============================================================================
# API Health
# =============================================================================
log_info "Collecting API health information..."

# Basic health
curl -s "${API_URL}/api/v1/health" 2>/dev/null > "${DIAG_DIR}/api/health.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/health.json"

# Detailed health
curl -s "${API_URL}/api/v1/health/detailed" 2>/dev/null > "${DIAG_DIR}/api/health_detailed.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/health_detailed.json"

# Capabilities
curl -s "${API_URL}/api/v1/capabilities" 2>/dev/null > "${DIAG_DIR}/api/capabilities.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/capabilities.json"

# Recorder status
curl -s "${API_URL}/api/v1/recorder/status" 2>/dev/null > "${DIAG_DIR}/api/recorder_status.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/recorder_status.json"

# Alerts
curl -s "${API_URL}/api/v1/alerts" 2>/dev/null > "${DIAG_DIR}/api/alerts.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/alerts.json"

# Degradation status
curl -s "${API_URL}/api/v1/degradation" 2>/dev/null > "${DIAG_DIR}/api/degradation.json" || echo '{"error": "API not reachable"}' > "${DIAG_DIR}/api/degradation.json"

# MediaMTX paths
curl -s "http://localhost:9997/v3/paths/list" 2>/dev/null > "${DIAG_DIR}/api/mediamtx_paths.json" || echo '{"error": "MediaMTX API not reachable"}' > "${DIAG_DIR}/api/mediamtx_paths.json"

# =============================================================================
# Configuration (Sanitized)
# =============================================================================
log_info "Collecting configuration (sanitized)..."

# MediaMTX config
if [ -f /opt/preke-r58-recorder/mediamtx.yml ]; then
    cp /opt/preke-r58-recorder/mediamtx.yml "${DIAG_DIR}/config/mediamtx.yml"
fi

# App config
if [ -f /opt/preke-r58-recorder/config.yml ]; then
    cp /opt/preke-r58-recorder/config.yml "${DIAG_DIR}/config/config.yml"
fi

# Environment (sanitized)
if [ -f /etc/r58/r58.env ]; then
    grep -v -E "(SECRET|PASSWORD|TOKEN|KEY)" /etc/r58/r58.env > "${DIAG_DIR}/config/r58.env.sanitized" 2>/dev/null || true
fi

# FRP config (sanitized)
if [ -f /etc/frp/frpc.toml ]; then
    grep -v -E "(token|secret)" /etc/frp/frpc.toml > "${DIAG_DIR}/config/frpc.toml.sanitized" 2>/dev/null || true
fi

# =============================================================================
# Recordings Directory
# =============================================================================
log_info "Collecting recordings info..."

{
    echo "=== Recordings Directory ==="
    ls -lah /opt/preke-r58-recorder/recordings/ 2>/dev/null || ls -lah /opt/r58/recordings/ 2>/dev/null || echo "Recordings directory not found"
    echo ""
    echo "=== Recent Recordings (last 10) ==="
    ls -lt /opt/preke-r58-recorder/recordings/*.mp4 2>/dev/null | head -10 || ls -lt /opt/r58/recordings/*.mp4 2>/dev/null | head -10 || echo "No recordings found"
} > "${DIAG_DIR}/system/recordings.txt" 2>&1

# =============================================================================
# Package Versions
# =============================================================================
log_info "Collecting version information..."

{
    echo "=== Software Versions ==="
    echo "Python: $(python3 --version 2>/dev/null || echo 'not found')"
    echo "Node: $(node --version 2>/dev/null || echo 'not found')"
    echo "npm: $(npm --version 2>/dev/null || echo 'not found')"
    echo "GStreamer: $(gst-launch-1.0 --version 2>/dev/null | head -1 || echo 'not found')"
    echo ""
    
    echo "=== Git Information ==="
    if [ -d /opt/preke-r58-recorder/.git ]; then
        cd /opt/preke-r58-recorder
        echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
        echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        echo "Last commit: $(git log -1 --format='%ci %s' 2>/dev/null || echo 'unknown')"
    else
        echo "Git repository not found"
    fi
} > "${DIAG_DIR}/system/versions.txt" 2>&1

# =============================================================================
# Create Summary
# =============================================================================
log_info "Creating summary..."

{
    echo "R58 Diagnostics Summary"
    echo "======================="
    echo "Generated: $(date)"
    echo "Hostname: $(hostname)"
    echo ""
    
    echo "=== Service Status ==="
    for svc in "${services[@]}"; do
        status=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
        printf "%-20s %s\n" "$svc" "$status"
    done
    echo ""
    
    echo "=== API Health ==="
    cat "${DIAG_DIR}/api/health.json" 2>/dev/null || echo "API not reachable"
    echo ""
    
    echo "=== Disk Space ==="
    df -h / /opt/preke-r58-recorder/recordings 2>/dev/null | tail -n +2 || echo "Unable to check disk"
    echo ""
    
    echo "=== Temperature ==="
    cat "${DIAG_DIR}/system/temperature.txt" 2>/dev/null || echo "Unable to check temperature"
    echo ""
    
    echo "=== Active Alerts ==="
    if [ -f "${DIAG_DIR}/api/alerts.json" ]; then
        cat "${DIAG_DIR}/api/alerts.json" | grep -o '"level":"[^"]*"' | head -5 || echo "No alerts"
    fi
} > "${DIAG_DIR}/SUMMARY.txt" 2>&1

# =============================================================================
# Create Archive
# =============================================================================
log_info "Creating archive..."

cd /tmp
tar -czf "${ARCHIVE_NAME}" "r58-diagnostics-${TIMESTAMP}"

# Move to output directory
mv "${ARCHIVE_NAME}" "${OUTPUT_DIR}/"

# Cleanup
rm -rf "${DIAG_DIR}"

echo ""
echo "=========================================="
log_info "Diagnostics collection complete!"
echo "=========================================="
echo ""
echo "Archive created: ${OUTPUT_DIR}/${ARCHIVE_NAME}"
echo ""
echo "Contents:"
echo "  - system/       System info (CPU, memory, disk, temp, network)"
echo "  - logs/         Service logs (last 500 lines each)"
echo "  - api/          API health and status responses"
echo "  - config/       Configuration files (sanitized)"
echo "  - SUMMARY.txt   Quick overview"
echo ""
echo "To extract: tar -xzf ${ARCHIVE_NAME}"
echo ""

