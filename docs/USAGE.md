# Mwatcher Usage Guide

Complete guide to using Mwatcher on all platforms.

---

## 📋 Table of Contents

1. [Basic Commands](#-basic-commands)
2. [Source-Specific Usage](#-source-specific-usage)
3. [Player Options](#-player-options)
4. [Downloading Movies](#-downloading-movies)
5. [Configuration](#-configuration)
6. [Termux-Specific Guide](#-termux-specific-guide)
7. [Linux/macOS Guide](#-linuxmacos-guide)
8. [Stremio Integration](#-stremio-integration)
9. [Troubleshooting](#-troubleshooting)

---

## 🎯 Basic Commands

### Quick Start

```bash
# Play a movie (auto-selects best source and player)
mwatcher "Movie Name"

# Examples:
mwatcher "Inception"
mwatcher "The Dark Knight Rises"
mwatcher "John Wick 4"
```

### Search Without Playing

```bash
# Search for movies and show results without playing
mwatcher --search "Movie Name"
mwatcher -s "Movie Name"

# Example:
mwatcher --search "Marvel"
```

### Play Direct URL

```bash
# Play any direct video URL
mwatcher --url "https://example.com/movie.mp4"
mwatcher -u "https://youtube.com/watch?v=dQw4w9WgXcQ"

# With specific player
mwatcher --url "https://example.com/movie.mp4" --player vlc
```

### List Available Options

```bash
# List all available movie sources
mwatcher --list-sources

# List all available players
mwatcher --list-players

# Show version
mwatcher --version
mwatcher -v
```

---

## 🌐 Source-Specific Usage

### YouTube

```bash
# Search and play from YouTube
mwatcher --source youtube "Movie Name"

# Examples:
mwatcher --source youtube "Full Movie Title"
mwatcher -s youtube "Documentary Name"
```

**Note**: YouTube may have copyright restrictions. Use responsibly.

### Torrent Streaming

```bash
# Stream movies via torrent (peer-to-peer)
mwatcher --source torrent "Movie Name"

# Examples:
mwatcher --source torrent "John Wick"
mwatcher -s torrent "Avengers"
```

**Requirements**:
- WebTorrent or similar torrent streaming support
- Good internet connection for peer discovery

### Stremio

```bash
# Use Stremio addons
mwatcher --source stremio "Movie Name"

# Direct Stremio URL
mwatcher --stremio "stremio://addon/path"
```

### PrimeWire

```bash
# Search PrimeWire
mwatcher --source primewire "Movie Name"
```

### FMovies

```bash
# Search FMovies
mwatcher --source fmovies "Movie Name"
```

### Putlocker

```bash
# Search Putlocker
mwatcher --source putlocker "Movie Name"
```

### SolarMovie

```bash
# Search SolarMovie
mwatcher --source solarmovie "Movie Name"
```

---

## 🎬 Player Options

### Available Players

| Player | Platform | Command |
|--------|----------|---------|
| VLC | Linux, macOS, Windows | `vlc` |
| MPV | Linux, macOS, Termux | `mpv` |
| Termux MPV | Termux | `termux` |
| MX Player | Android | `mxplayer` |
| Default Browser | All | `default` |

### Specify Player

```bash
# Use VLC
mwatcher --player vlc "Movie Name"
mwatcher -p vlc "Movie Name"

# Use MPV
mwatcher --player mpv "Movie Name"

# Use MX Player (Android)
mwatcher --player mxplayer "Movie Name"

# Use default system player
mwatcher --player default "Movie Name"
```

### Player-Specific Features

#### VLC Options

```bash
# VLC supports many options
mwatcher --player vlc --url "movie.mp4"
```

#### MPV Options

```bash
# MPV with additional arguments
mwatcher --player mpv "Movie Name"
```

#### MX Player (Android)

```bash
# Use MX Player for better Android playback
mwatcher --player mxplayer "Movie Name"
```

---

## 💾 Downloading Movies

### Download Instead of Play

```bash
# Download a movie
mwatcher --download "Movie Name"
mwatcher -d "Movie Name"

# Examples:
mwatcher --download "The Shawshank Redemption"
mwatcher -d "Inception"
```

### Download with Specific Source

```bash
# Download from a specific source
mwatcher --download --source youtube "Movie Name"
mwatcher -d -s torrent "Movie Name"
```

### Download Direct URL

```bash
# Download a direct URL
mwatcher --download --url "https://example.com/movie.mp4"
```

### Download Location

By default, movies are downloaded to `~/Downloads/`. You can change this in the configuration.

---

## ⚙️ Configuration

### Interactive Configuration

```bash
# Start interactive configuration
mwatcher --configure
```

This will guide you through:
1. **Preferred Sources**: Choose which sources to search first
2. **Preferred Player**: Set your default player
3. **Quality**: Set default video quality (480p, 720p, 1080p, best)
4. **Subtitles**: Enable or disable subtitles
5. **Custom Sources**: Add your own movie sources

### Configuration File

Configuration is stored in `~/.mwatcher/config.json`:

```json
{
  "preferred_sources": ["stremio", "torrent", "youtube"],
  "preferred_player": "vlc",
  "quality": "1080p",
  "subtitles": true,
  "cache_enabled": true,
  "custom_sources": {}
}
```

### Manual Configuration

You can manually edit the configuration file:

```bash
# Edit configuration
nano ~/.mwatcher/config.json

# Or use a text editor
vim ~/.mwatcher/config.json
```

### Environment Variables

```bash
# Override preferred player for a session
export MWATCHER_PLAYER=mpv
mwatcher "Movie Name"

# Override preferred sources
export MWATCHER_SOURCES="youtube,torrent,stremio"
mwatcher "Movie Name"
```

---

## 📱 Termux-Specific Guide

### Installation

```bash
# 1. Update Termux
pkg update && pkg upgrade

# 2. Install dependencies
pkg install python git curl wget mpv

# 3. Install Python packages
pip install yt-dlp requests beautifulsoup4

# 4. Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

### Recommended Setup

1. **Install MX Player** from Google Play Store for better playback
2. **Install Stremio** from [strem.io](https://strem.io) for addon support
3. **Install Termux:Widget** from F-Droid for home screen shortcuts

### Termux Usage

```bash
# Basic playback
mwatcher "Movie Name"

# Use MX Player (recommended for Android)
mwatcher --player mxplayer "Movie Name"

# Use Termux MPV
mwatcher --player termux "Movie Name"

# Download for offline viewing
mwatcher --download "Movie Name"
```

### Termux Tips

- **Storage Access**: Grant Termux storage permission to save downloads
- **External Storage**: Use `termux-setup-storage` to access external storage
- **Battery Optimization**: Disable battery optimization for Termux to prevent background process killing
- **Notifications**: Enable Termux notifications for download completion alerts

### Termux Shortcuts

Create a shortcut on your home screen:

```bash
# Create a Termux widget
termux-widget-create --label "Mwatcher" --command "termux-open-url 'mwatcher://'"
```

---

## 💻 Linux/macOS Guide

### Linux Installation

#### Ubuntu/Debian

```bash
# Install dependencies
sudo apt update && sudo apt install python3 python3-pip git curl wget vlc mpv

# Install Python packages
pip3 install yt-dlp requests beautifulsoup4

# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

#### Fedora

```bash
# Install dependencies
sudo dnf install python3 python3-pip git curl wget vlc mpv

# Install Python packages
pip3 install yt-dlp requests beautifulsoup4

# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

#### Arch Linux

```bash
# Install dependencies
sudo pacman -Syu python python-pip git curl wget vlc mpv

# Install Python packages
pip install yt-dlp requests beautifulsoup4

# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### macOS Installation

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python git curl wget vlc mpv

# Install Python packages
pip3 install yt-dlp requests beautifulsoup4

# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### Linux/macOS Usage

```bash
# Play with VLC
mwatcher --player vlc "Movie Name"

# Play with MPV (recommended for keyboard control)
mwatcher --player mpv "Movie Name"

# Download movies
mwatcher --download "Movie Name"

# Search across all sources
mwatcher --search "Movie Name"
```

### Keyboard Shortcuts (MPV)

| Key | Action |
|-----|--------|
| Space | Pause/Resume |
| ← → | Seek backward/forward |
| ↑ ↓ | Volume up/down |
| f | Fullscreen |
| q | Quit |
| s | Screenshot |

### Keyboard Shortcuts (VLC)

| Key | Action |
|-----|--------|
| Space | Pause/Resume |
| ← → | Seek backward/forward |
| ↑ ↓ | Volume up/down |
| f | Fullscreen |
| q | Quit |
| Ctrl + c | Stop |

---

## 🌟 Stremio Integration

### What is Stremio?

Stremio is a media center that uses addons to provide content. Mwatcher can integrate with Stremio addons to access a wide range of content.

### Installing Stremio Addons

1. **Install Stremio** from [strem.io](https://strem.io)
2. **Install addons** in Stremio
3. **Configure Mwatcher** to use Stremio

### Popular Stremio Addons

| Addon | ID | Content |
|-------|----|---------|
| Cinemeta | `com.cinemeta.addon` | Movie metadata, trailers, subtitles |
| Torrentio | `com.torrentio.addon` | Torrent streaming (recommended) |
| Popcorn Time | `com.popcorntime.addon` | Popcorn Time catalog |
| YouTube | `com.github.youTube.addon` | YouTube videos |
| Netflix | `com.netflix.addon` | Netflix content (requires login) |
| Disney+ | `com.disneyplus.addon` | Disney+ content (requires login) |
| HBO Max | `com.hbomax.addon` | HBO Max content (requires login) |
| Amazon Prime | `com.amazonprime.addon` | Prime Video content |

### Using Stremio with Mwatcher

```bash
# Search via Stremio
mwatcher --source stremio "Movie Name"

# Use specific Stremio addon
mwatcher --stremio "stremio://cinemeta/com.cinemeta.addon"
```

### Configuring Stremio in Mwatcher

```bash
# Run configuration
mwatcher --configure

# Select Stremio as a preferred source
# Add custom Stremio addon URLs
```

### Stremio Addon URLs

```
stremio://cinemeta/com.cinemeta.addon
stremio://torrentio/com.torrentio.addon
stremio://popcorn-time/com.popcorntime.addon
stremio://youtube/com.github.youTube.addon
```

---

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### 1. "Command not found" after installation

**Solution**:
```bash
# Check if the script is in your PATH
echo $PATH

# Add Mwatcher to PATH manually
export PATH="$PATH:/path/to/mwatcher"

# Or reinstall with proper symlinks
bash install.sh
```

#### 2. "No module named 'yt_dlp'"

**Solution**:
```bash
pip install yt-dlp
# Or
pip3 install yt-dlp
```

#### 3. "Player not found"

**Solution**: Install the required player for your platform:

```bash
# Linux (Debian/Ubuntu)
sudo apt install vlc mpv

# macOS
brew install vlc mpv

# Termux
pkg install mpv
```

#### 4. "No results found"

**Solutions**:
- Check your internet connection
- Try a different source: `mwatcher --source youtube "Movie Name"`
- The movie might not be available on the default sources
- Try a more specific search query
- Check if the movie is available on the source website

#### 5. Slow streaming or buffering

**Solutions**:
- Try a different source
- Lower the quality: `mwatcher --configure` → Set quality to 720p or 480p
- Use a wired connection if possible
- Close other bandwidth-intensive applications
- Try a different player (MPV is often more efficient than VLC)

#### 6. "Permission denied" on Termux

**Solution**:
```bash
chmod +x ~/.termux/bin/mwatcher
chmod +x ~/.termux/opt/mwatcher/mwatcher.sh
```

#### 7. Downloads not working

**Solutions**:
- Check if you have write permissions to the download directory
- On Termux, grant storage permission: `termux-setup-storage`
- Try downloading to a different location

#### 8. Subtitles not showing

**Solutions**:
- Enable subtitles in configuration: `mwatcher --configure`
- Make sure the source provides subtitles
- Try a different player that supports subtitles better

### Debug Mode

For detailed error information:

```bash
# Run with Python directly to see full error messages
python3 mwatcher.py "Movie Name"

# Check dependencies
python3 -c "import yt_dlp, requests, bs4; print('All dependencies OK')"
```

### Log Files

Mwatcher creates log files in `~/.mwatcher/logs/` for debugging.

---

## 📚 Advanced Usage

### Chaining Commands

```bash
# Search and then play the first result
mwatcher --search "Movie Name" && mwatcher "Movie Name"
```

### Using with xargs

```bash
# Play multiple movies from a list
echo -e "Movie1\nMovie2\nMovie3" | xargs -I {} mwatcher "{}"
```

### Creating Aliases

```bash
# Add to your ~/.bashrc or ~/.zshrc
alias movie='mwatcher'
alias moviedl='mwatcher --download'
alias moviesearch='mwatcher --search'

# Then use:
movie "Inception"
moviedl "The Matrix"
moviesearch "John Wick"
```

### Using with tmux

```bash
# Start a tmux session for background playback
tmux new -s movie
mwatcher "Movie Name"
# Detach with Ctrl+b, then d
# Reattach with: tmux attach -t movie
```

---

## 🎓 Tips and Tricks

### 1. Faster Searches

Limit the number of sources searched:

```bash
mwatcher --source youtube "Movie Name"
```

### 2. Better Quality

Set higher quality in configuration:

```bash
mwatcher --configure
# Set quality to "best" or "1080p"
```

### 3. Offline Viewing

Download movies for offline viewing:

```bash
mwatcher --download "Movie Name"
```

### 4. Batch Downloads

Create a script to download multiple movies:

```bash
#!/bin/bash
movies=(
  "Inception"
  "The Dark Knight"
  "Interstellar"
)

for movie in "${movies[@]}"; do
  mwatcher --download "$movie"
done
```

### 5. Custom Sources

Add your favorite movie sites:

```bash
mwatcher --configure
# Select "Add custom source"
```

### 6. Keyboard Control

Use MPV for better keyboard control:

```bash
mwatcher --player mpv "Movie Name"
```

### 7. Background Playback

On Termux, use `&` to run in background:

```bash
mwatcher "Movie Name" &
```

### 8. Notification on Completion

On Termux, enable notifications for download completion:

```bash
termux-notification --title "Download Complete" --content "Movie downloaded successfully"
```

---

## 📖 Command Reference

```
usage: mwatcher.py [-h] [--search SEARCH] [--url URL] [--stremio STREMIO] [--source SOURCE] [--player PLAYER] [--download] [--list-sources] [--list-players] [--configure] [--version] [query]

Universal Movie Watcher

positional arguments:
  query                 Movie name or URL to play

optional arguments:
  -h, --help            show this help message and exit
  --search SEARCH, -s SEARCH
                        Search for movies
  --url URL, -u URL     Direct URL to play
  --stremio STREMIO     Stremio addon URL
  --source SOURCE      Specific source to use (youtube, torrent, stremio, etc.)
  --player PLAYER, -p PLAYER
                        Specific player to use (vlc, mpv, termux, etc.)
  --download, -d        Download instead of playing
  --list-sources        List all available sources
  --list-players        List all available players
  --configure           Configure Mwatcher settings
  --version, -v        Show version
```

---

## 🌟 Best Practices

1. **Use Specific Sources**: For better results, specify the source you want
2. **Start with Lower Quality**: If you have a slow connection, start with 480p or 720p
3. **Check Legality**: Only watch content you have rights to access
4. **Use VPN**: For privacy and accessing geo-restricted content
5. **Keep Updated**: Regularly update Mwatcher and its dependencies
6. **Monitor Data Usage**: Streaming uses data, be mindful of your data plan
7. **Use Headphones**: For better audio experience, especially on mobile

---

**Happy Watching! 🎬🍿**
