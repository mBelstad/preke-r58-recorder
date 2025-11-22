#!/bin/bash
# Start script for R58 recorder

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Run the application with uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000

