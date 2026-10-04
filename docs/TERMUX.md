# Mwatcher on Termux - Complete Guide

The ultimate guide to using Mwatcher on Android via Termux.

---

## 📋 Table of Contents

1. [Why Use Termux?](#why-use-termux)
2. [Termux Setup](#termux-setup)
3. [Mwatcher Installation](#mwatcher-installation)
4. [Termux-Specific Features](#termux-specific-features)
5. [Usage Examples](#usage-examples)
6. [Recommended Apps](#recommended-apps)
7. [Termux Tips & Tricks](#termux-tips--tricks)
8. [Troubleshooting](#troubleshooting)

---

## Why Use Termux?

**Termux** is a powerful terminal emulator for Android that gives you a full Linux environment on your phone. Combined with Mwatcher, you get:

✅ **Full movie streaming** on your Android device
✅ **Command-line power** with a touch interface
✅ **No ads** - Clean streaming experience
✅ **Offline downloads** - Save movies to watch later
✅ **Customizable** - Tailor to your preferences
✅ **Privacy** - No tracking, open source
✅ **Free** - No subscriptions required

---

## Termux Setup

### Step 1: Install Termux

1. **From Google Play Store** (recommended):
   - Search for "Termux"
   - Install the official Termux app by Fredrik Fornwall
   
2. **From F-Droid** (alternative):
   - Install F-Droid from [f-droid.org](https://f-droid.org)
   - Search for "Termux" in F-Droid
   - Install Termux

3. **From Termux Website**:
   - Download from [https://termux.com](https://termux.com)

### Step 2: Update Termux

Open Termux and run:

```bash
pkg update && pkg upgrade
```

This updates all packages to the latest versions.

### Step 3: Grant Storage Access

To save downloads and access files:

```bash
termux-setup-storage
```

This grants Termux access to your device's storage. Press **Allow** when prompted.

### Step 4: Install Termux:Widget (Optional)

For home screen shortcuts:

1. Install **Termux:Widget** from F-Droid or Play Store
2. Add the widget to your home screen
3. Configure it to run Mwatcher commands

---

## Mwatcher Installation

### Method 1: Automatic Installation (Recommended)

```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

This script will:
- Install all required dependencies
- Set up Mwatcher
- Create symlinks for easy access
- Configure everything automatically

### Method 2: Manual Installation

```bash
# 1. Install dependencies
pkg install python git curl wget mpv

# 2. Install Python packages
pip install yt-dlp requests beautifulsoup4

# 3. Clone Mwatcher repository
 git clone https://github.com/AfzalAshraf/Mwatcher.git
cd Mwatcher

# 4. Make scripts executable
chmod +x mwatcher.sh mwatcher.py

# 5. Create symlink for easy access
ln -s $(pwd)/mwatcher.sh $PREFIX/bin/mwatcher

# 6. Test installation
mwatcher --version
```

### Method 3: Local File Installation

If you already have the Mwatcher files:

```bash
# Copy files to Termux
# (Copy the Mwatcher folder to your Termux home directory)

# Navigate to Mwatcher directory
cd ~/Mwatcher

# Install dependencies
pkg install python git curl wget mpv
pip install yt-dlp requests beautifulsoup4

# Make scripts executable
chmod +x mwatcher.sh mwatcher.py

# Create symlink
ln -s $(pwd)/mwatcher.sh $PREFIX/bin/mwatcher

# Test
mwatcher --version
```

---

## Termux-Specific Features

### Supported Players on Termux

| Player | Command | Notes |
|--------|---------|-------|
| **MPV** | `mpv` | Built-in Termux player |
| **MX Player** | `mxplayer` | Requires MX Player app |
| **VLC** | `vlc` | Requires VLC for Android |
| **Termux MPV** | `termux` | Optimized for Termux |
| **Default** | `default` | Uses Termux file opener |

### Player Installation

#### MPV (Recommended)

```bash
pkg install mpv
```

MPV is a lightweight, powerful media player that works well in Termux.

#### MX Player (Alternative)

1. Install **MX Player** from Google Play Store
2. In Mwatcher, use:
   ```bash
   mwatcher --player mxplayer "Movie Name"
   ```

#### VLC for Android

1. Install **VLC for Android** from Google Play Store
2. In Mwatcher, use:
   ```bash
   mwatcher --player vlc "Movie Name"
   ```

### Termux-Specific Configuration

Mwatcher automatically detects Termux and optimizes for it:

```json
{
  "preferred_player": "termux",
  "quality": "720p",
  "subtitles": true
}
```

You can change this with:

```bash
mwatcher --configure
```

---

## Usage Examples

### Basic Commands

```bash
# Play a movie
mwatcher "Inception"

# Search for movies
mwatcher --search "The Matrix"

# Play with specific source
mwatcher --source youtube "Movie Name"

# Use MX Player
mwatcher --player mxplayer "Movie Name"

# Download a movie
mwatcher --download "Movie Name"
```

### Source-Specific Examples

```bash
# YouTube
mwatcher --source youtube "Full Movie Title"

# Torrent streaming
mwatcher --source torrent "John Wick"

# Stremio
mwatcher --source stremio "Movie Name"

# PrimeWire
mwatcher --source primewire "Movie Name"
```

### Player Examples

```bash
# Use MPV (default)
mwatcher "Movie Name"

# Use MX Player
mwatcher --player mxplayer "Movie Name"

# Use VLC
mwatcher --player vlc "Movie Name"

# Use Termux MPV
mwatcher --player termux "Movie Name"
```

### Download Examples

```bash
# Download a movie
mwatcher --download "Movie Name"

# Download from specific source
mwatcher --download --source youtube "Movie Name"

# Download with specific quality
mwatcher --configure  # Set quality first
mwatcher --download "Movie Name"
```

### Configuration Examples

```bash
# Configure Mwatcher
mwatcher --configure

# List available sources
mwatcher --list-sources

# List available players
mwatcher --list-players

# Check version
mwatcher --version
```

---

## Recommended Apps

### Media Players

| App | Install | Notes |
|-----|---------|-------|
| **MX Player** | Play Store | Best for Android, hardware acceleration |
| **VLC for Android** | Play Store | Open source, supports all formats |
| **MPV** | Termux | Built-in, lightweight |

### Streaming Enhancers

| App | Install | Purpose |
|-----|---------|---------|
| **Stremio** | [strem.io](https://strem.io) | Addon support for premium content |
| **REAL-DEBRID** | [real-debrid.com](https://real-debrid.com) | Faster torrent streaming |
| **Orbot** | Play Store | Tor network for privacy |

### File Managers

| App | Install | Notes |
|-----|---------|-------|
| **Solid Explorer** | Play Store | Access Termux files |
| **FX File Explorer** | Play Store | Access Termux files |
| **MiXplorer** | XDA Labs | Powerful file manager |

### Utilities

| App | Install | Purpose |
|-----|---------|---------|
| **Termux:Widget** | F-Droid | Home screen shortcuts |
| **Termux:API** | F-Droid | Device integration |
| **Termux:Boot** | F-Droid | Run scripts at boot |
| **Termux:Tasker** | F-Droid | Tasker integration |

---

## Termux Tips & Tricks

### 1. Termux Shortcuts

Create a shortcut on your home screen:

```bash
# Create a widget to open Mwatcher
termux-widget-create --label "Mwatcher" --command "termux-open-url 'mwatcher://'"
```

### 2. Termux Keybindings

Mwatcher works well with Termux's keybindings:

- **Volume Up/Down**: Control volume in MPV
- **Swipe from left**: Show/hide keyboard
- **Long press on screen**: Paste text
- **Ctrl+C**: Copy selected text
- **Ctrl+V**: Paste

### 3. Background Playback

Run Mwatcher in the background:

```bash
mwatcher "Movie Name" &
```

Then you can continue using Termux for other tasks.

### 4. Notification on Download Completion

Install Termux:API for notifications:

```bash
pkg install termux-api

# Then use in your scripts
termux-notification --title "Download Complete" --content "Movie downloaded"
```

### 5. Battery Optimization

To prevent Termux from being killed in the background:

1. Go to **Device Settings** → **Apps** → **Termux**
2. Tap **Battery**
3. Select **Don't optimize** or **Unrestricted**

### 6. Storage Access

To access external storage (SD card):

```bash
# List all storage locations
ls /sdcard
ls /storage/emulated/0

# Navigate to Downloads
cd /sdcard/Download
```

### 7. Custom Commands

Create custom commands in `~/.bashrc`:

```bash
# Edit .bashrc
nano ~/.bashrc

# Add aliases
alias movie='mwatcher'
alias moviedl='mwatcher --download'
alias moviesearch='mwatcher --search'

# Reload .bashrc
source ~/.bashrc

# Now use:
movie "Inception"
moviedl "The Matrix"
```

### 8. Termux Styling

Customize your Termux appearance:

```bash
# Install termux-styling
pkg install termux-styling

# Change font and colors
termux-styling
```

### 9. Termux in Split Screen

Use Termux in split screen mode:

1. Open Termux
2. Open recent apps
3. Long press on Termux icon
4. Select **Split screen**
5. Run Mwatcher in one pane and monitor in another

### 10. Termux File Sharing

Share files between Termux and other apps:

```bash
# Copy file to shared storage
cp movie.mp4 /sdcard/Download/

# Open with other apps
termux-open /sdcard/Download/movie.mp4
```

---

## Troubleshooting

### Common Issues

#### 1. "Command not found" after installation

**Solution**:
```bash
# Check if symlink was created
ls $PREFIX/bin/mwatcher

# If not, create it manually
ln -s ~/Mwatcher/mwatcher.sh $PREFIX/bin/mwatcher

# Reload PATH
export PATH="$PREFIX/bin:$PATH"
```

#### 2. "No module named 'yt_dlp'"

**Solution**:
```bash
pip install yt-dlp
# Or
pip3 install yt-dlp
```

#### 3. "Player not found"

**Solution**: Install the required player:
```bash
# For MPV
pkg install mpv

# For MX Player (install from Play Store)
mwatcher --player mxplayer "Movie Name"

# For VLC (install from Play Store)
mwatcher --player vlc "Movie Name"
```

#### 4. "Permission denied" when creating symlink

**Solution**:
```bash
# Use sudo equivalent in Termux
ln -s ~/Mwatcher/mwatcher.sh $PREFIX/bin/mwatcher

# Or check permissions
ls -la $PREFIX/bin/
```

#### 5. "No results found"

**Solutions**:
- Check your internet connection: `ping google.com`
- Try a different source: `mwatcher --source youtube "Movie Name"`
- The movie might not be available on default sources
- Try a more specific search query

#### 6. Slow streaming or buffering

**Solutions**:
- Try a different source
- Lower the quality: `mwatcher --configure` → Set quality to 480p or 720p
- Use a different player: `mwatcher --player mpv "Movie Name"`
- Close other apps to free up RAM
- Connect to WiFi instead of mobile data

#### 7. Downloads not working

**Solutions**:
- Grant storage permission: `termux-setup-storage`
- Check if you have space: `df -h`
- Try downloading to a different location

#### 8. Termux keeps stopping

**Solutions**:
- Disable battery optimization for Termux
- Clear Termux cache and data
- Reinstall Termux
- Try Termux from F-Droid instead of Play Store

#### 9. Keyboard not showing

**Solution**: Swipe from the left edge of the screen to show/hide the keyboard.

#### 10. Text is too small

**Solution**:
```bash
# Increase font size
termux-styling
# Select a larger font
```

### Debugging Commands

```bash
# Check Python version
python --version
python3 --version

# Check pip version
pip --version
pip3 --version

# Check installed packages
pip list

# Check Termux version
termux -v

# Check device info
uname -a

# Check storage
df -h

# Check network
ping -c 4 google.com

# Check DNS
nslookup google.com
```

### Log Files

Mwatcher creates log files in `~/.mwatcher/logs/` for debugging.

View logs:
```bash
cat ~/.mwatcher/logs/mwatcher.log
```

---

## Performance Tips

### 1. Optimize for Slow Devices

```bash
# Use lower quality
mwatcher --configure
# Set quality to 480p or 720p

# Use MPV instead of VLC
mwatcher --player mpv "Movie Name"
```

### 2. Reduce Data Usage

```bash
# Use lower quality
mwatcher --configure
# Set quality to 480p

# Use torrent streaming (less data than progressive download)
mwatcher --source torrent "Movie Name"
```

### 3. Improve Battery Life

- Close Termux when not in use
- Use headphones instead of speakers
- Lower screen brightness
- Use airplane mode if downloading (then enable WiFi)

### 4. Faster Startup

```bash
# Pre-load dependencies
python3 -c "import yt_dlp, requests, bs4"
```

---

## Security Tips

### 1. Use VPN for Privacy

```bash
# Install OpenVPN
pkg install openvpn

# Connect to VPN
openvpn --config your-config.ovpn
```

### 2. Use Tor for Anonymity

```bash
# Install Orbot from Play Store
# Then in Termux:
pkg install torsocks

# Use with Mwatcher (advanced)
torsocks mwatcher "Movie Name"
```

### 3. Keep Termux Updated

```bash
pkg update && pkg upgrade -y
```

### 4. Use Strong Passwords

If you use REAL-DEBRID or other services, use strong, unique passwords.

### 5. Clear History

```bash
# Clear Termux history
rm ~/.bash_history

# Clear Mwatcher cache
rm -rf ~/.mwatcher/cache/*
```

---

## Customization

### Custom Sources

Add your favorite movie sites:

```bash
mwatcher --configure
# Select "Add custom source"
```

### Custom Players

You can add custom player commands in the configuration.

### Custom Quality Settings

```bash
mwatcher --configure
# Set quality to: 480p, 720p, 1080p, best
```

---

## Advanced Usage

### Scripting with Mwatcher

Create a script to automate movie watching:

```bash
#!/bin/bash

# Movie marathon script
movies=(
  "The Godfather"
  "The Godfather Part II"
  "The Godfather Part III"
)

for movie in "${movies[@]}"; do
  echo "Now playing: $movie"
  mwatcher "$movie"
  read -p "Press Enter to continue to next movie..." 
done
```

### Batch Downloads

```bash
#!/bin/bash

# Download multiple movies
movies=(
  "Inception"
  "The Dark Knight"
  "Interstellar"
)

for movie in "${movies[@]}"; do
  echo "Downloading: $movie"
  mwatcher --download "$movie"
done

# Notification when all done
termux-notification --title "All Downloads Complete" --content "All movies downloaded successfully"
```

### Scheduled Downloads

Use Termux:Tasker to schedule downloads:

```bash
# Create a script
cat > ~/download_movie.sh << 'EOF'
#!/bin/bash
mwatcher --download "$1"
termux-notification --title "Download Complete" --content "$1 downloaded"
EOF

chmod +x ~/download_movie.sh

# Then use Termux:Tasker to run this script at specific times
```

---

## Conclusion

Mwatcher + Termux gives you a powerful, portable movie streaming solution on your Android device. With these tips and tricks, you can get the most out of your setup.

**Happy Watching on Android! 📱🎬🍿**
