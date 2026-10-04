# 🎬 Mwatcher - Universal Movie Watcher

**Watch any movie from any device with just ONE command!**

✅ **Works Everywhere**: Termux (Android), Linux, macOS, Windows (WSL)
✅ **All Players**: VLC, MPV, MX Player, and system defaults
✅ **All Sources**: YouTube, Torrent, Stremio, PrimeWire, FMovies, Putlocker, SolarMovie
✅ **One-Click Install**: Simple installation scripts for all platforms
✅ **Offline Mode**: Download movies for later viewing
✅ **Stremio Integration**: Full support for Stremio addons

---

## 🚀 Super Quick Start

### Termux (Android)
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

### Linux / macOS
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### Then just run:
```bash
mwatcher "Inception"
```

---

## 🌟 Features

### 📱 Multi-Platform Support
- **Termux** on Android (full Linux environment)
- **Linux** (Ubuntu, Debian, Fedora, Arch, etc.)
- **macOS** Terminal
- **Windows** (via WSL or Git Bash)

### 🎥 Supported Players
| Player | Platform | Notes |
|--------|----------|-------|
| **VLC** | All | Most popular, full-featured |
| **MPV** | Linux, macOS, Termux | Lightweight, keyboard-controlled |
| **MX Player** | Android | Hardware-accelerated |
| **Termux MPV** | Termux | Optimized for mobile |
| **Default** | All | System file opener |

### 🌐 Content Sources
| Source | Type | Notes |
|--------|------|-------|
| **YouTube** | Streaming | Full movies, trailers |
| **Torrent** | P2P Streaming | WebTorrent-based |
| **Stremio** | Addon System | Netflix, Disney+, HBO, etc. |
| **PrimeWire** | Streaming | Free movies |
| **FMovies** | Streaming | Popular site |
| **Putlocker** | Streaming | Another source |
| **SolarMovie** | Streaming | HD quality |
| **Custom** | Any | Add your own! |

### ⚡ Key Features
- 🔍 **Smart Search**: Search across multiple sources simultaneously
- 🎬 **Direct Play**: One command to find and play any movie
- 📥 **Download**: Save movies for offline viewing
- ⚙️ **Configurable**: Choose sources, players, quality
- 📱 **Mobile-Optimized**: Perfect for Termux on Android
- 🎯 **Quality Control**: 480p, 720p, 1080p, or best
- 🌐 **URL Support**: Play any direct video URL
- 🔄 **Fallback System**: Automatically tries alternative players

---

## 📖 Usage Examples

### Basic Commands
```bash
# Play a movie (auto-selects best source)
mwatcher "Inception"

# Search for movies without playing
mwatcher --search "The Matrix"

# Play with specific source
mwatcher --source youtube "Interstellar"
mwatcher --source torrent "John Wick"

# Use specific player
mwatcher --player vlc "Pulp Fiction"
mwatcher --player mpv "The Dark Knight"

# Download instead of playing
mwatcher --download "The Shawshank Redemption"

# Play direct URL
mwatcher --url "https://example.com/movie.mp4"

# List available sources
mwatcher --list-sources

# List available players
mwatcher --list-players

# Configure settings
mwatcher --configure

# Check version
mwatcher --version
```

### Stremio Integration
```bash
# Search via Stremio addons
mwatcher --source stremio "Dune"

# Use specific Stremio addon
mwatcher --stremio "stremio://cinemeta/com.cinemeta.addon"

# With Torrentio (requires REAL-DEBRID)
mwatcher --source stremio "Movie Name"
```

### Advanced Usage
```bash
# Search and play first result
mwatcher --search "Movie" && mwatcher "Movie"

# Batch download
for movie in "Inception" "Matrix" "Interstellar"; do
  mwatcher --download "$movie"
done

# Use with xargs
echo -e "Movie1\nMovie2" | xargs -I {} mwatcher "{}"
```

---

## 📦 Installation

### Termux (Android) - RECOMMENDED

```bash
# 1. Install Termux from Play Store or F-Droid
# 2. Open Termux and run:

pkg update && pkg upgrade
pkg install python git curl wget mpv
pip install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

**Recommended Android Apps:**
- **MX Player** (Play Store) - Best for Android
- **VLC for Android** (Play Store) - Alternative player
- **Stremio** ([strem.io](https://strem.io)) - For addon support
- **Termux:Widget** (F-Droid) - Home screen shortcuts

### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install python3 python3-pip git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### Linux (Fedora)

```bash
sudo dnf install python3 python3-pip git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### Linux (Arch)

```bash
sudo pacman -Syu python python-pip git curl wget vlc mpv
pip install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### macOS

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### Windows (WSL)

```bash
# Install WSL (Windows Subsystem for Linux)
wsl --install

# Then in WSL (Ubuntu):
sudo apt update && sudo apt install python3 python3-pip git curl wget vlc
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

---

## 🛠️ Configuration

### Interactive Configuration
```bash
mwatcher --configure
```

This guides you through:
- ✅ Preferred sources (order of searching)
- ✅ Preferred player (default player)
- ✅ Video quality (480p, 720p, 1080p, best)
- ✅ Subtitles (enable/disable)
- ✅ Custom sources (add your own)

### Manual Configuration

Edit `~/.mwatcher/config.json`:

```json
{
  "preferred_sources": ["stremio", "torrent", "youtube", "primewire"],
  "preferred_player": "vlc",
  "quality": "1080p",
  "subtitles": true,
  "cache_enabled": true,
  "custom_sources": {
    "my_site": {
      "name": "My Movie Site",
      "search_url": "https://mymovies.com/search/{query}",
      "stream_extractor": "html"
    }
  }
}
```

### Environment Variables

```bash
# Override player
export MWATCHER_PLAYER=mpv
mwatcher "Movie"

# Override sources
export MWATCHER_SOURCES="youtube,torrent,stremio"
mwatcher "Movie"
```

---

## 🌟 Stremio Addons

Mwatcher fully integrates with **Stremio addons** for premium content:

### Popular Addons
| Addon | ID | Content | Login Required |
|-------|----|---------|----------------|
| **Torrentio** | `com.torrentio.addon` | Torrent streaming | REAL-DEBRID |
| **Cinemeta** | `com.cinemeta.addon` | Metadata, subtitles | ❌ No |
| **Popcorn Time** | `com.popcorntime.addon` | Movie catalog | ❌ No |
| **YouTube** | `com.github.youTube.addon` | YouTube videos | ❌ No |
| **Netflix** | `com.netflix.addon` | Netflix content | ✅ Yes |
| **Disney+** | `com.disneyplus.addon` | Disney+ content | ✅ Yes |
| **HBO Max** | `com.hbomax.addon` | HBO Max content | ✅ Yes |
| **Amazon Prime** | `com.amazonprime.addon` | Prime Video | ✅ Yes |

### Setup Instructions

1. Install Stremio from [https://strem.io](https://strem.io)
2. Install desired addons in Stremio
3. Configure REAL-DEBRID for Torrentio (recommended)
4. Use with Mwatcher:
   ```bash
   mwatcher --source stremio "Movie Name"
   ```

---

## 🎯 Tips & Tricks

### Termux-Specific
- **Grant storage access**: `termux-setup-storage`
- **Home screen shortcut**: Install Termux:Widget
- **Background playback**: Run with `&` (e.g., `mwatcher "Movie" &`)
- **Disable battery optimization**: Prevent Termux from being killed

### General Tips
- **Faster searches**: Specify source (e.g., `--source youtube`)
- **Better quality**: Use `--configure` to set quality to 1080p or best
- **Offline viewing**: Use `--download` to save movies
- **Custom aliases**: Add to `~/.bashrc`:
  ```bash
  alias movie='mwatcher'
  alias moviedl='mwatcher --download'
  ```

### Keyboard Shortcuts
- **MPV**: Space (pause), ←/→ (seek), ↑/↓ (volume), f (fullscreen), q (quit)
- **VLC**: Space (pause), ←/→ (seek), ↑/↓ (volume), f (fullscreen), q (quit)

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Command not found" | Check installation, ensure symlink exists |
| "No module named 'yt_dlp'" | `pip install yt-dlp` |
| "Player not found" | Install VLC or MPV |
| "No results found" | Try different source, check internet |
| "Permission denied" | Grant storage access, check permissions |
| Slow streaming | Lower quality, try different source |

### Debug Mode
```bash
# Run with verbose output
python3 mwatcher.py "Movie" -v

# Check dependencies
python3 -c "import yt_dlp, requests, bs4; print('OK')"

# View logs
cat ~/.mwatcher/logs/mwatcher.log
```

---

## 📚 Documentation

- [Full Usage Guide](docs/USAGE.md) - Complete command reference
- [Termux Guide](docs/TERMUX.md) - Android-specific guide
- [Stremio Integration](docs/STREMIO.md) - Full Stremio addon guide

---

## 🎨 Command Reference

```
usage: mwatcher.py [-h] [--search SEARCH] [--url URL] [--stremio STREMIO] [--source SOURCE] 
                   [--player PLAYER] [--download] [--list-sources] [--list-players] 
                   [--configure] [--version] [query]

Universal Movie Watcher

positional arguments:
  query                 Movie name or URL to play

optional arguments:
  -h, --help            show this help message and exit
  --search SEARCH, -s SEARCH
                        Search for movies
  --url URL, -u URL     Direct URL to play
  --stremio STREMIO     Stremio addon URL
  --source SOURCE      Specific source to use
  --player PLAYER, -p PLAYER
                        Specific player to use
  --download, -d        Download instead of playing
  --list-sources        List all available sources
  --list-players        List all available players
  --configure           Configure Mwatcher settings
  --version, -v        Show version

Environment Variables:
  MWATCHER_PLAYER: Override preferred player
  MWATCHER_SOURCES: Comma-separated list of preferred sources
```

---

## 🔧 Dependencies

### Required
- Python 3.6+
- pip
- yt-dlp
- requests
- beautifulsoup4

### Recommended
- VLC Media Player
- MPV Player
- MX Player (Android)
- Stremio (for addon support)
- REAL-DEBRID (for torrent streaming)

---

## 📜 License

**MIT License** - Free to use, modify, and distribute.

---

## 🙏 Contributing

Contributions welcome! Please submit issues or pull requests.

### Development
```bash
git clone https://github.com/AfzalAshraf/Mwatcher.git
cd Mwatcher
pip install -r requirements.txt
python mwatcher.py
```

---

## 📞 Support

- **GitHub Issues**: [https://github.com/AfzalAshraf/Mwatcher/issues](https://github.com/AfzalAshraf/Mwatcher/issues)
- **Documentation**: This README and docs/ folder

---

## 🎉 Real-World Examples

```bash
# Movie night
mwatcher "The Avengers"

# Classic film
mwatcher --source youtube "The Godfather"

# Latest release via torrent
mwatcher --source torrent "John Wick 4"

# Netflix via Stremio
mwatcher --source stremio "Stranger Things"

# Download for travel
mwatcher --download "Inception"

# Use MX Player on Android
mwatcher --player mxplayer "Interstellar"

# Search across all sources
mwatcher --search "Marvel"

# Play with VLC on Linux
mwatcher --player vlc "Pulp Fiction"
```

---

## 🏆 Why Mwatcher?

| Feature | Mwatcher | Alternatives |
|---------|----------|--------------|
| **One Command** | ✅ Yes | ❌ Multiple steps |
| **Multi-Platform** | ✅ All devices | ❌ Limited |
| **No Ads** | ✅ Clean | ❌ Ads everywhere |
| **Offline Mode** | ✅ Download | ❌ Streaming only |
| **Stremio Support** | ✅ Full | ❌ Partial/Limited |
| **Custom Sources** | ✅ Add any | ❌ Fixed |
| **Open Source** | ✅ Free | ❌ Proprietary |
| **Privacy** | ✅ No tracking | ❌ Tracking |

---

**Enjoy your movies! 🎬🍿**

*Made with ❤️ for movie lovers everywhere*

*Copyright © 2024 Afzal Ashraf*

*GitHub: [https://github.com/AfzalAshraf/Mwatcher](https://github.com/AfzalAshraf/Mwatcher)*