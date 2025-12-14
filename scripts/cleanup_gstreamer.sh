#!/bin/bash
# Cleanup script to kill stuck GStreamer processes before service start
# Run with: sudo ./cleanup_gstreamer.sh

echo "Cleaning up GStreamer processes..."

# Kill any stuck gst-plugin-scanner processes (try gracefully first)
pkill -TERM gst-plugin-scanner 2>/dev/null
sleep 1

# Force kill if still running
pkill -9 gst-plugin-scanner 2>/dev/null

# Kill any stuck GStreamer launch processes
pkill -9 -f "gst-launch" 2>/dev/null

# Kill any stuck uvicorn processes from previous runs
pkill -9 -f "uvicorn.*preke-r58-recorder" 2>/dev/null

# Kill any stuck Python processes that might be holding video devices
# Be careful not to kill system Python processes
pkill -9 -f "python.*src\.main:app" 2>/dev/null

# Release video devices by killing any v4l2 processes
fuser -k /dev/video0 /dev/video11 /dev/video21 /dev/video60 2>/dev/null || true

# Clear GStreamer registry cache (can help with corrupted registry)
rm -rf ~/.cache/gstreamer-1.0 2>/dev/null
rm -rf /root/.cache/gstreamer-1.0 2>/dev/null

# Small delay to ensure cleanup completes
sleep 1

# Check if any gst-plugin-scanner still running
STUCK=$(pgrep -c gst-plugin-scanner 2>/dev/null || echo "0")
if [ "$STUCK" -gt 0 ]; then
    echo "WARNING: $STUCK gst-plugin-scanner processes still running (may be in D state, requires reboot)"
    # Check if they're in D state
    ps aux | grep gst-plugin-scanner | grep -v grep | awk '{print $8}' | grep -q "D" && \
        echo "ERROR: Processes in uninterruptible sleep - REBOOT REQUIRED"
else
    echo "Cleanup complete - no stuck processes"
fi

exit 0

