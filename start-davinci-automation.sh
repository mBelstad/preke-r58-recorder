#!/bin/bash
# Start DaVinci Resolve Automation Service

cd "$(dirname "$0")"

echo "Starting DaVinci Resolve Automation Service..."
echo "Make sure DaVinci Resolve Studio is running!"
echo ""

python3 scripts/davinci-automation-service.py
