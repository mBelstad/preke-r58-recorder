#!/bin/bash
# Initialize all HDMI inputs before starting the recorder service
#
# The LT6911 HDMI-to-MIPI bridges on the R58 4x4 3S report resolution via
# their V4L2 subdevs, but the video devices start with 0x0 resolution.
# This script queries each subdev and sets the format on the video device.
#
# Device Mapping:
#   HDMI N0  → /dev/video0  ← subdev v4l-subdev2 (LT6911 7-002b)
#   HDMI N11 → /dev/video11 ← subdev v4l-subdev7 (LT6911 4-002b)
#   HDMI N21 → /dev/video22 ← subdev v4l-subdev12 (LT6911 2-002b)
#   HDMI N60 → /dev/video60 (direct HDMI RX, no initialization needed)

init_device() {
    local video_dev=$1
    local subdev=$2
    local port_name=$3
    
    echo "Initializing $port_name ($video_dev via $subdev)..."
    
    # Check if devices exist
    if [ ! -e "$video_dev" ]; then
        echo "  WARNING: $video_dev does not exist"
        return 1
    fi
    
    if [ ! -e "$subdev" ]; then
        echo "  WARNING: $subdev does not exist"
        return 1
    fi
    
    # Get resolution from subdev
    # Format: "Width/Height      : 1920/1080"
    resolution=$(v4l2-ctl -d "$subdev" --get-subdev-fmt pad=0 2>/dev/null | grep "Width/Height" | awk -F': ' '{print $2}')
    width=$(echo "$resolution" | cut -d'/' -f1 | tr -d ' ')
    height=$(echo "$resolution" | cut -d'/' -f2 | tr -d ' ')
    
    if [ -z "$width" ] || [ -z "$height" ] || [ "$width" = "0" ] || [ "$height" = "0" ]; then
        echo "  No signal detected on $port_name (resolution: $width x $height)"
        return 1
    fi
    
    echo "  Detected signal: ${width}x${height}"
    
    # Set format on video device - use UYVY which works for all LT6911 bridges
    v4l2-ctl -d "$video_dev" --set-fmt-video=width="$width",height="$height",pixelformat=UYVY 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "  Successfully set $video_dev to ${width}x${height} UYVY"
        return 0
    else
        echo "  ERROR: Failed to set format on $video_dev"
        return 1
    fi
}

echo "========================================"
echo "R58 4x4 3S HDMI Input Initialization"
echo "========================================"
echo ""

# Initialize each rkcif device (LT6911 bridge devices)
init_device /dev/video0 /dev/v4l-subdev2 "HDMI N0"
init_device /dev/video11 /dev/v4l-subdev7 "HDMI N11"
init_device /dev/video22 /dev/v4l-subdev12 "HDMI N21"

echo ""
echo "HDMI input initialization complete"
echo ""

# Show final status
echo "Final device status:"
for dev in /dev/video0 /dev/video11 /dev/video22 /dev/video60; do
    if [ -e "$dev" ]; then
        info=$(v4l2-ctl -d "$dev" --get-fmt-video 2>/dev/null | grep -E "(Width|Pixel)" | tr '\n' ' ')
        echo "  $dev: $info"
    fi
done

exit 0

