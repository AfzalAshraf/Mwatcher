# 🎬 Mwatcher - Quick Start Guide

**Watch any movie from any device with ONE command!**

---

## ⚡ One-Line Installation

### Termux (Android)
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

### Linux / macOS
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

---

## 🚀 Basic Usage

```bash
# Play any movie
mwatcher "Inception"

# Search for movies
mwatcher --search "The Matrix"

# Download for offline
mwatcher --download "Movie Name"

# Play with specific player
mwatcher --player vlc "Movie Name"

# Use specific source
mwatcher --source youtube "Movie Name"
```

---

## 📱 Termux Setup

```bash
# 1. Install Termux from Play Store
# 2. Open Termux and run:

pkg update && pkg upgrade
pkg install python git curl wget mpv
pip install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)

# 3. Install recommended apps:
#    - MX Player (Play Store)
#    - VLC for Android (Play Store)
#    - Stremio (strem.io)
```

---

## 💻 Linux Setup

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)

# Fedora
sudo dnf install python3 python3-pip git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)

# Arch
sudo pacman -Syu python python-pip git curl wget vlc mpv
pip install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

---

## 🍎 macOS Setup

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python git curl wget vlc mpv
pip3 install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

---

## 🌟 Common Commands

| Command | Description |
|---------|-------------|
| `mwatcher "Movie"` | Play a movie |
| `mwatcher -s "Movie"` | Search for movies |
| `mwatcher -d "Movie"` | Download movie |
| `mwatcher -p vlc "Movie"` | Play with VLC |
| `mwatcher -p mpv "Movie"` | Play with MPV |
| `mwatcher -p mxplayer "Movie"` | Play with MX Player |
| `mwatcher --source youtube "Movie"` | Use YouTube |
| `mwatcher --source torrent "Movie"` | Use torrent |
| `mwatcher --source stremio "Movie"` | Use Stremio |
| `mwatcher --url "http://..."` | Play direct URL |
| `mwatcher --list-sources` | List all sources |
| `mwatcher --list-players` | List all players |
| `mwatcher --configure` | Configure settings |
| `mwatcher --version` | Show version |

---

## 🎥 Supported Players

| Player | Platform | Command |
|--------|----------|---------|
| VLC | All | `vlc` |
| MPV | Linux, macOS, Termux | `mpv` |
| MX Player | Android | `mxplayer` |
| Termux MPV | Termux | `termux` |
| Default | All | `default` |

---

## 🌐 Supported Sources

| Source | Type | Notes |
|--------|------|-------|
| YouTube | Streaming | Full movies |
| Torrent | P2P | WebTorrent |
| Stremio | Addons | Netflix, Disney+, etc. |
| PrimeWire | Streaming | Free movies |
| FMovies | Streaming | Popular |
| Putlocker | Streaming | Free |
| SolarMovie | Streaming | HD |
| Custom | Any | Add your own |

---

## ⚙️ Configuration

```bash
# Interactive configuration
mwatcher --configure

# Manual configuration
nano ~/.mwatcher/config.json

# Environment variables
export MWATCHER_PLAYER=mpv
export MWATCHER_SOURCES="youtube,torrent"
```

---

## 🌟 Stremio Integration

```bash
# Install Stremio from strem.io
# Install addons in Stremio
# Use with Mwatcher

mwatcher --source stremio "Movie Name"
```

**Popular Addons:**
- Torrentio (requires REAL-DEBRID)
- Cinemeta (metadata)
- Popcorn Time (catalog)
- Netflix, Disney+, HBO Max (require login)

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Command not found | Check installation |
| Module not found | `pip install yt-dlp requests beautifulsoup4` |
| Player not found | Install VLC or MPV |
| No results | Try different source |
| Permission denied | Grant storage access |

---

## 📚 More Info

- **Full Documentation**: [README.md](README.md)
- **Usage Guide**: [docs/USAGE.md](docs/USAGE.md)
- **Termux Guide**: [docs/TERMUX.md](docs/TERMUX.md)
- **Stremio Guide**: [docs/STREMIO.md](docs/STREMIO.md)
- **GitHub**: [https://github.com/AfzalAshraf/Mwatcher](https://github.com/AfzalAshraf/Mwatcher)

---

## 🎉 Examples

```bash
# Movie night
mwatcher "The Avengers"

# Classic film
mwatcher --source youtube "The Godfather"

# Latest release
mwatcher --source torrent "John Wick 4"

# Netflix via Stremio
mwatcher --source stremio "Stranger Things"

# Download for travel
mwatcher --download "Inception"

# Use MX Player on Android
mwatcher --player mxplayer "Interstellar"
```

---

**Enjoy your movies! 🎬🍿**
