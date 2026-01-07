#!/bin/bash
# Setup script for R58 recorder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up R58 Recorder..."

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS"
    PLATFORM="macos"
    
    # Check for GStreamer
    if ! command -v gst-launch-1.0 &> /dev/null; then
        echo "GStreamer not found. Install with: brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav"
        exit 1
    fi
else
    echo "Detected Linux (assuming R58)"
    PLATFORM="r58"
    
    # Check for GStreamer
    if ! command -v gst-launch-1.0 &> /dev/null; then
        echo "GStreamer not found. Install with: sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-rtsp python3-gi"
        exit 1
    fi
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create recordings directory
if [ "$PLATFORM" == "macos" ]; then
    RECORDINGS_DIR="$SCRIPT_DIR/recordings"
else
    RECORDINGS_DIR="/var/recordings"
    echo "Note: On R58, ensure /var/recordings exists and is writable"
fi

mkdir -p "$RECORDINGS_DIR"

echo "Setup complete!"
echo ""
echo "To start the application:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python -m src.main"

