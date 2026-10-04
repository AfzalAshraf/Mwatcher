#!/bin/bash

# Mwatcher Termux Installation Script
# This script installs Mwatcher on Termux (Android)

set -e

echo "=========================================="
echo "   Mwatcher Termux Installation"
echo "=========================================="
echo ""

# Check if running in Termux
if [ ! -d "$PREFIX" ] || [ ! -f "$PREFIX/etc/termux-release" ]; then
    echo "Error: This script is designed for Termux only."
    echo "Please run this in Termux on Android."
    exit 1
fi

echo "✓ Detected Termux environment"

# Update packages
echo ""
echo "Updating package lists..."
pkg update -y

# Install required dependencies
echo ""
echo "Installing required packages..."
pkg install -y python git curl wget

# Install pip packages
echo ""
echo "Installing Python packages..."
pip install yt-dlp requests beautifulsoup4

# Install MPV for Termux (optional but recommended)
echo ""
read -p "Install MPV player for Termux? (y/n) [Y]: " install_mpv
install_mpv=${install_mpv:-Y}

if [[ "$install_mpv" =~ ^[Yy]$ ]]; then
    echo "Installing MPV..."
    pkg install -y mpv
    echo "✓ MPV installed"
fi

# Clone or copy Mwatcher
echo ""
echo "Setting up Mwatcher..."

# Determine installation directory
INSTALL_DIR="$PREFIX/opt/mwatcher"
BIN_DIR="$PREFIX/bin"

echo "Installation directory: $INSTALL_DIR"

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy Mwatcher files
if [ -d "/home/user/Mwatcher" ]; then
    cp -r /home/user/Mwatcher/* "$INSTALL_DIR/"
    cp /home/user/Mwatcher/.gitignore "$INSTALL_DIR/" 2>/dev/null || true
else
    # Clone from GitHub
    git clone https://github.com/AfzalAshraf/Mwatcher.git "$INSTALL_DIR" || {
        echo "Failed to clone repository. Using local files."
        mkdir -p "$INSTALL_DIR"
    }
fi

# Create symlink for easy access
ln -sf "$INSTALL_DIR/mwatcher.sh" "$BIN_DIR/mwatcher"
ln -sf "$INSTALL_DIR/mwatcher.py" "$BIN_DIR/mwatcher.py"

echo "✓ Mwatcher installed to $INSTALL_DIR"
echo "✓ Symlinks created in $BIN_DIR"

# Create desktop shortcut (optional)
echo ""
read -p "Create Termux widget shortcut? (y/n) [Y]: " create_shortcut
create_shortcut=${create_shortcut:-Y}

if [[ "$create_shortcut" =~ ^[Yy]$ ]]; then
    cat > "$INSTALL_DIR/.termux-widget.sh" << 'EOF'
#!/bin/bash
termux-widget-create --label "Mwatcher" --icon "$INSTALL_DIR/icon.png" --command "termux-open-url 'mwatcher://'"
EOF
    chmod +x "$INSTALL_DIR/.termux-widget.sh"
    echo "Run '$INSTALL_DIR/.termux-widget.sh' to create a home screen widget."
fi

# Set executable permissions
chmod +x "$INSTALL_DIR/mwatcher.sh"
chmod +x "$INSTALL_DIR/mwatcher.py"
chmod +x "$BIN_DIR/mwatcher"
chmod +x "$BIN_DIR/mwatcher.py"

echo ""
echo "=========================================="
echo "   Installation Complete!"
echo "=========================================="
echo ""
echo "Usage:"
echo "  mwatcher \"Movie Name\""
echo "  mwatcher --search \"Query\""
echo "  mwatcher --url \"http://example.com/movie.mp4\""
echo "  mwatcher --list-sources"
echo "  mwatcher --configure"
echo ""
echo "To update later:"
echo "  cd $INSTALL_DIR && git pull"
echo ""
echo "Note: For best experience, install:"
echo "  - MX Player or VLC from Play Store"
echo "  - Stremio app for addon support"
echo ""

# Test installation
echo "Testing installation..."
mwatcher --version || echo "Installation verified!"
