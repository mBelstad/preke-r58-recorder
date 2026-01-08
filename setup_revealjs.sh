#!/bin/bash
# Setup script for Reveal.js on Mekotronics R58 device
# This script installs Reveal.js and its dependencies

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Reveal.js Setup for Mekotronics R58"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed."
    echo "Please install Node.js 18.0.0 or higher."
    echo "On Debian/Ubuntu: sudo apt-get install nodejs npm"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "WARNING: Node.js version is less than 18.0.0"
    echo "Current version: $(node --version)"
    echo "Reveal.js requires Node.js 18.0.0 or higher"
    if [ "${NON_INTERACTIVE:-false}" != "true" ]; then
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "NON_INTERACTIVE=true, continuing anyway..."
    fi
fi

echo "✓ Node.js $(node --version) found"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm is not installed."
    exit 1
fi

echo "✓ npm $(npm --version) found"

# Check git
if ! command -v git &> /dev/null; then
    echo "ERROR: git is not installed."
    echo "Please install git: sudo apt-get install git"
    exit 1
fi

echo "✓ git $(git --version | cut -d' ' -f3) found"
echo ""

# Check if reveal.js already exists
if [ -d "reveal.js" ]; then
    # Check if it's a valid reveal.js installation (has dist/ directory)
    if [ -d "reveal.js/dist" ]; then
        echo "Reveal.js already installed and built."
        if [ "${FORCE_REINSTALL:-false}" != "true" ]; then
            echo "Skipping installation. Using existing reveal.js directory."
            echo ""
            echo "To update Reveal.js:"
            echo "  cd reveal.js"
            echo "  git pull"
            echo "  npm install"
            echo "  npm run build"
            echo ""
            echo "To force reinstall, set FORCE_REINSTALL=true"
            exit 0
        else
            echo "FORCE_REINSTALL=true, removing existing installation..."
            rm -rf reveal.js
        fi
    else
        echo "Reveal.js directory exists but appears incomplete. Reinstalling..."
        rm -rf reveal.js
    fi
fi

# Clone Reveal.js repository
echo "Cloning Reveal.js repository..."
if git clone https://github.com/hakimel/reveal.js.git; then
    echo "✓ Repository cloned successfully"
else
    echo "ERROR: Failed to clone repository"
    exit 1
fi

echo ""

# Install dependencies
echo "Installing dependencies (this may take a few minutes)..."
cd reveal.js
if npm install; then
    echo "✓ Dependencies installed successfully"
else
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""

# Build Reveal.js
echo "Building Reveal.js..."
if npm run build; then
    echo "✓ Build completed successfully"
else
    echo "ERROR: Build failed"
    exit 1
fi

echo ""
echo "========================================="
echo "Reveal.js Setup Complete!"
echo "========================================="
echo ""
echo "Installation location: $SCRIPT_DIR/reveal.js"
echo ""
echo "Next steps:"
echo "1. Start development server: cd reveal.js && npm run start:dev"
echo "2. Access at: http://$(hostname -I | awk '{print $1}'):8001"
echo "3. Built files are served by FastAPI at: http://$(hostname -I | awk '{print $1}'):8000/reveal.js/"
echo ""
echo "To customize Reveal.js:"
echo "  - Edit source files in reveal.js/js/ and reveal.js/css/"
echo "  - Run 'npm run build' to rebuild"
echo "  - Restart FastAPI to serve updated files"
echo ""

