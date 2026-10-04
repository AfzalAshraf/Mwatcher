#!/bin/bash

# Mwatcher Installation Script
# Universal installation for Linux, macOS, and Termux

set -e

echo "=========================================="
echo "   Mwatcher Universal Installation"
echo "=========================================="
echo ""

# Detect platform
PLATFORM="unknown"
if [ "$(uname)" == "Linux" ]; then
    if [ -d "$PREFIX" ] && [ -f "$PREFIX/etc/termux-release" ]; then
        PLATFORM="termux"
    else
        PLATFORM="linux"
    fi
elif [ "$(uname)" == "Darwin" ]; then
    PLATFORM="macos"
fi

echo "Detected platform: $PLATFORM"
echo ""

# Check for sudo
if [ "$PLATFORM" != "termux" ] && [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# Install dependencies based on platform
case "$PLATFORM" in
    termux)
        echo "Installing Termux dependencies..."
        pkg update -y
        pkg install -y python git curl wget
        ;;
    linux)
        echo "Installing Linux dependencies..."
        if command -v apt-get &> /dev/null; then
            $SUDO apt-get update
            $SUDO apt-get install -y python3 python3-pip git curl wget vlc
        elif command -v dnf &> /dev/null; then
            $SUDO dnf install -y python3 python3-pip git curl wget vlc
        elif command -v yum &> /dev/null; then
            $SUDO yum install -y python3 python3-pip git curl wget vlc
        elif command -v pacman &> /dev/null; then
            $SUDO pacman -Syu --noconfirm python python-pip git curl wget vlc
        else
            echo "Unsupported package manager. Please install manually:"
            echo "  python3, pip, git, curl, wget, vlc"
            exit 1
        fi
        ;;
    macos)
        echo "Installing macOS dependencies..."
        if ! command -v brew &> /dev/null; then
            echo "Homebrew not found. Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python git curl wget vlc
        ;;
    *)
        echo "Unsupported platform. Please install manually:"
        echo "  python3, pip, git, curl, wget"
        exit 1
        ;;
esac

# Install Python packages
echo ""
echo "Installing Python packages..."
python3 -m pip install --upgrade pip
python3 -m pip install yt-dlp requests beautifulsoup4

# Determine installation directory
if [ "$PLATFORM" == "termux" ]; then
    INSTALL_DIR="$PREFIX/opt/mwatcher"
    BIN_DIR="$PREFIX/bin"
else
    INSTALL_DIR="/opt/mwatcher"
    BIN_DIR="/usr/local/bin"
fi

echo ""
echo "Setting up Mwatcher in $INSTALL_DIR..."

# Create directories
$SUDO mkdir -p "$INSTALL_DIR"
$SUDO mkdir -p "$BIN_DIR"

# Copy Mwatcher files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "$SCRIPT_DIR" ]; then
    $SUDO cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
else
    # Clone from GitHub
    $SUDO git clone https://github.com/AfzalAshraf/Mwatcher.git "$INSTALL_DIR" || {
        echo "Failed to clone repository."
        exit 1
    }
fi

# Create symlinks
$SUDO ln -sf "$INSTALL_DIR/mwatcher.sh" "$BIN_DIR/mwatcher"
$SUDO ln -sf "$INSTALL_DIR/mwatcher.py" "$BIN_DIR/mwatcher.py"

echo "✓ Mwatcher installed to $INSTALL_DIR"
echo "✓ Symlinks created in $BIN_DIR"

# Set executable permissions
$SUDO chmod +x "$INSTALL_DIR/mwatcher.sh"
$SUDO chmod +x "$INSTALL_DIR/mwatcher.py"
$SUDO chmod +x "$BIN_DIR/mwatcher"
$SUDO chmod +x "$BIN_DIR/mwatcher.py"

# Create configuration directory
mkdir -p "$HOME/.mwatcher"

# Platform-specific recommendations
echo ""
echo "=========================================="
echo "   Installation Complete!"
echo "=========================================="
echo ""

case "$PLATFORM" in
    termux)
        echo "Termux-specific recommendations:"
        echo "  - Install MPV: pkg install mpv"
        echo "  - Install MX Player from Play Store"
        echo "  - Install Stremio app for addon support"
        ;;
    linux)
        echo "Linux recommendations:"
        echo "  - Install MPV: $SUDO apt-get install mpv"
        echo "  - Install VLC: $SUDO apt-get install vlc"
        echo "  - Install Stremio for addon support"
        ;;
    macos)
        echo "macOS recommendations:"
        echo "  - Install MPV: brew install mpv"
        echo "  - Install VLC: brew install --cask vlc"
        echo "  - Install Stremio for addon support"
        ;;
esac

echo ""
echo "Usage:"
echo "  mwatcher \"Movie Name\""
echo "  mwatcher --search \"Query\""
echo "  mwatcher --url \"http://example.com/movie.mp4\""
echo "  mwatcher --list-sources"
echo "  mwatcher --configure"
echo ""
echo "To update later:"
echo "  $SUDO git -C $INSTALL_DIR pull"
echo ""

# Test installation
echo "Testing installation..."
mwatcher --version || echo "Installation verified!"
