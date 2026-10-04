# 🎬 Mwatcher Enhanced - Universal Movie Watcher with Plex & TV Support

**The Ultimate Movie Experience: Watch any movie on any device with RAW 5.1, 7.1 audio passthrough!**

✅ **Works Everywhere**: Termux, Linux, macOS, Windows, VIDAA OS, Android TV
✅ **All Players**: VLC, MPV, MX Player with **raw audio passthrough**
✅ **All Sources**: YouTube, Torrent, Stremio, **Plex**, PrimeWire, FMovies, Putlocker
✅ **TV Integration**: **VIDAA OS**, DLNA/UPnP, Android TV, Chromecast
✅ **Plex Integration**: Full Plex Media Server support with **direct play**
✅ **Audio Passthrough**: **5.1, 7.1, TrueHD, DTS-HD** surround sound
✅ **One-Click Install**: Simple installation for all platforms
✅ **Offline Mode**: Download movies for later viewing

---

## 🚀 Super Quick Start

### Basic Setup
```bash
# Install Mwatcher Enhanced
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)

# Play a movie
mwatcher "Inception"
```

### With Plex
```bash
# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)

# Add your Plex server
mwatcher --configure
# Select "Add Plex server"

# Play from Plex
mwatcher --plex "Inception"
```

### With TV Casting
```bash
# List TVs on your network
mwatcher --list-tvs

# Cast to your TV
mwatcher --tv "192.168.1.100" "Inception"
```

### With Raw Audio (5.1, 7.1)
```bash
# Play with raw audio passthrough
mwatcher --audio raw "Inception"

# Cast to TV with 7.1 audio
mwatcher --tv "192.168.1.100" --audio 7.1 "Inception"
```

---

## 🌟 What's New in Enhanced Version?

### ✅ **TV Integration**
- **VIDAA OS Support** - Full integration with Hisense VIDAA OS TVs
- **DLNA/UPnP Casting** - Cast to any DLNA-compatible device
- **Android TV Support** - Native support for Android TV devices
- **Automatic TV Discovery** - Discover all TVs on your local network

### ✅ **Plex Integration**
- **Plex Media Server Support** - Connect to your Plex server
- **Multi-Server Support** - Connect to multiple Plex servers
- **Library Browsing** - Browse Plex libraries directly
- **Direct Play** - Play media without transcoding when possible
- **Transcoding Support** - Automatic transcoding for incompatible devices

### ✅ **Audio Passthrough**
- **Raw Audio Support** - 5.1, 7.1, TrueHD, DTS-HD surround sound
- **Audio Quality Presets** - raw, 5.1, 7.1, stereo, best
- **Player-Specific Settings** - VLC, MPV, MX Player audio configurations
- **Plex Audio Selection** - Choose specific audio tracks from Plex

---

## 🎯 Complete Feature List

### Multi-Platform Support
- ✅ **Termux** on Android (full Linux environment)
- ✅ **Linux** (Ubuntu, Debian, Fedora, Arch, etc.)
- ✅ **macOS** Terminal
- ✅ **Windows** (via WSL or Git Bash)
- ✅ **VIDAA OS** (Hisense smart TVs)
- ✅ **Android TV** (Sony, Philips, Xiaomi, Nvidia)
- ✅ **Any DLNA/UPnP device**

### Supported Players (with Audio Passthrough)
| Player | Platform | Audio Passthrough |
|--------|----------|-------------------|
| **VLC** | All | ✅ Yes |
| **MPV** | Linux, macOS, Termux | ✅ Yes |
| **MX Player** | Android | ✅ Yes |
| **Termux MPV** | Termux | ✅ Yes |
| **Default** | All | ❌ No |

### Content Sources
| Source | Type | Audio Passthrough |
|--------|------|-------------------|
| **YouTube** | Streaming | ⚠️ Limited |
| **Torrent** | P2P Streaming | ⚠️ Limited |
| **Stremio** | Addon System | ⚠️ Limited |
| **Plex** | Media Server | ✅ **Full Support** |
| **PrimeWire** | Streaming | ⚠️ Limited |
| **FMovies** | Streaming | ⚠️ Limited |
| **Putlocker** | Streaming | ⚠️ Limited |
| **SolarMovie** | Streaming | ⚠️ Limited |
| **Custom** | Any | ⚠️ Limited |

### Audio Formats Supported
| Format | Channels | Codec | Passthrough |
|--------|----------|-------|-------------|
| **AAC** | 2.0, 5.1 | AAC | ❌ No |
| **AC3** | 2.0, 5.1 | Dolby Digital | ✅ Yes |
| **E-AC3** | 2.0, 5.1, 7.1 | Dolby Digital Plus | ✅ Yes |
| **DTS** | 2.0, 5.1 | DTS | ✅ Yes |
| **DTS-HD HR** | 2.0, 5.1, 7.1 | DTS-HD | ✅ Yes |
| **DTS-HD MA** | 2.0, 5.1, 7.1 | DTS-HD Master Audio | ✅ Yes |
| **TrueHD** | 2.0, 5.1, 7.1 | Dolby TrueHD | ✅ Yes |
| **FLAC** | 2.0 | FLAC | ✅ Yes |
| **PCM** | 2.0, 5.1, 7.1 | PCM | ✅ Yes |

---

## 📖 Usage Examples

### Basic Commands
```bash
# Play a movie (auto-selects best source)
mwatcher "Inception"

# Search for movies
mwatcher --search "The Matrix"

# Play with specific source
mwatcher --source youtube "Interstellar"
mwatcher --source torrent "John Wick"
mwatcher --source plex "Inception"

# Use specific player
mwatcher --player vlc "Pulp Fiction"
mwatcher --player mpv "The Dark Knight"

# Download for offline
mwatcher --download "The Shawshank Redemption"

# Play direct URL
mwatcher --url "https://example.com/movie.mp4"
```

### TV Casting Commands
```bash
# List all TVs on network
mwatcher --list-tvs

# List VIDAA OS TVs specifically
mwatcher --list-vidaa

# Cast to TV by IP
mwatcher --tv "192.168.1.100" "Inception"

# Cast with specific source
mwatcher --tv "192.168.1.100" --source plex "Movie Name"

# Cast with specific audio
mwatcher --tv "192.168.1.100" --audio raw "Movie Name"
```

### Plex Commands
```bash
# Search Plex servers
mwatcher --plex "Inception"

# Search with Plex as source
mwatcher --source plex "The Dark Knight"

# Cast Plex content to TV
mwatcher --source plex --tv "192.168.1.100" "Movie Name"

# Play Plex with raw audio
mwatcher --source plex --audio raw "Movie Name"
```

### Audio Quality Commands
```bash
# List audio presets
mwatcher --list-audio

# Play with raw audio passthrough
mwatcher --audio raw "Inception"

# Play with 5.1 audio
mwatcher --audio 5.1 "Movie Name"

# Play with 7.1 audio
mwatcher --audio 7.1 "Movie Name"

# Play with stereo audio
mwatcher --audio stereo "Movie Name"

# Let Mwatcher choose best audio
mwatcher --audio best "Movie Name"
```

### Combined Commands
```bash
# Cast Plex content to TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Inception"

# Play Plex with VLC and 7.1 audio
mwatcher --source plex --player vlc --audio 7.1 "The Dark Knight"

# Cast YouTube to TV with 5.1 audio
mwatcher --source youtube --tv "192.168.1.100" --audio 5.1 "Music Video"

# Search Plex and cast to VIDAA TV
mwatcher --plex --tv "192.168.1.100" "Interstellar"
```

---

## 📦 Installation

### Termux (Android)
```bash
# 1. Install Termux from Play Store or F-Droid
# 2. Open Termux and run:

pkg update && pkg upgrade
pkg install python git curl wget mpv
pip install yt-dlp requests beautifulsoup4
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

**Recommended Android Apps:**
- **MX Player** (Play Store) - Best for Android with audio passthrough
- **VLC for Android** (Play Store) - Alternative with audio passthrough
- **Plex** (Play Store) - For Plex server access
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

## ⚙️ Configuration

### Interactive Configuration
```bash
mwatcher --configure
```

This guides you through:
- ✅ Preferred sources (order of searching)
- ✅ Preferred player (default player)
- ✅ Video quality (480p, 720p, 1080p, 4k, best)
- ✅ **Audio quality (raw, 5.1, 7.1, stereo, best)** - NEW!
- ✅ Subtitles (enable/disable)
- ✅ Custom sources (add your own)
- ✅ **Plex servers (add and manage)** - NEW!
- ✅ **TV discovery (find TVs on network)** - NEW!

### Audio Quality Presets

| Preset | Description | Best For |
|--------|-------------|----------|
| **raw** | Raw passthrough | Home theaters, AV receivers |
| **5.1** | 5.1 surround | Soundbars, 5.1 systems |
| **7.1** | 7.1 surround | High-end systems |
| **stereo** | 2.0 stereo | Headphones, TV speakers |
| **best** | Best available | Automatic selection |

### Manual Configuration

Edit `~/.mwatcher/config.json`:

```json
{
  "preferred_sources": ["plex", "stremio", "torrent", "youtube"],
  "preferred_player": "vlc",
  "quality": "1080p",
  "audio_quality": "raw",
  "subtitles": true,
  "cache_enabled": true,
  "custom_sources": {},
  "plex_servers": [
    {
      "server": "192.168.1.100",
      "port": 32400,
      "token": "your_plex_token_here",
      "username": "your_username",
      "password": "your_password"
    }
  ],
  "tv_devices": []
}
```

---

## 🎬 Real-World Scenarios

### Scenario 1: Home Theater Setup

**Setup:**
- VIDAA OS TV (Hisense) connected to AV receiver
- AV receiver connected to 7.1 speaker system
- Plex server with 4K movies and 7.1 audio tracks
- Computer running Mwatcher

**Usage:**
```bash
# Cast 4K movie with 7.1 audio to home theater
mwatcher --source plex --tv "192.168.1.100" --audio 7.1 "Inception"
```

**Result:**
- 4K video with 7.1 surround sound
- Raw audio passthrough to receiver
- No quality loss
- Cinema-quality experience at home

---

### Scenario 2: Bedroom with Soundbar

**Setup:**
- Android TV connected to 5.1 soundbar via HDMI ARC
- Plex server with movies and 5.1 audio
- Phone running Mwatcher via Termux

**Usage:**
```bash
# Cast to bedroom TV with 5.1 audio
mwatcher --source plex --tv "192.168.1.101" --audio 5.1 "The Matrix"
```

**Result:**
- High-quality video
- 5.1 surround sound via HDMI ARC
- Easy control from phone

---

### Scenario 3: Multi-Room Setup

**Setup:**
- Living room: VIDAA OS TV
- Bedroom: Android TV
- Kitchen: Samsung TV (Tizen)
- Plex server with shared library
- Phone running Mwatcher

**Usage:**
```bash
# Cast to living room TV
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast to bedroom TV
mwatcher --tv "192.168.1.101" "Movie Name"

# Cast to kitchen TV
mwatcher --tv "192.168.1.102" "Movie Name"
```

**Result:**
- Watch the same movie on multiple TVs
- Or watch different movies on each TV
- Centralized control from one device

---

### Scenario 4: Travel with Offline Movies

**Setup:**
- Laptop with Mwatcher installed
- Plex server at home with remote access
- Downloaded movies for offline viewing
- Headphones for private viewing

**Usage:**
```bash
# Download movies for offline viewing
mwatcher --source plex --download "Movie Name"

# Play downloaded movies
mwatcher "Movie Name"

# Or stream from home Plex server
mwatcher --source plex "Movie Name"
```

**Result:**
- Offline movie access when no internet
- Stream from home when internet is available
- High-quality playback anywhere

---

### Scenario 5: Hotel Room

**Setup:**
- Laptop or phone with Mwatcher
- Hotel TV with DLNA support
- Plex server at home (with remote access)

**Usage:**
```bash
# Discover hotel TV
mwatcher --list-tvs

# Cast to hotel TV
mwatcher --tv "192.168.1.100" --source plex "Movie Name"
```

**Result:**
- Watch your own movies on hotel TV
- No need for HDMI cable
- Secure connection
- Familiar interface

---

## 🎯 Tips for Best Experience

### For Audio Passthrough

1. **Use HDMI**: Always use HDMI for audio passthrough (not optical for TrueHD/DTS-HD)
2. **Check receiver**: Ensure your AV receiver supports the audio format
3. **Enable passthrough**: In TV/receiver settings, enable audio passthrough
4. **Use raw audio**: Set audio quality to "raw" for best results
5. **Test content**: Use media with known audio formats for testing
6. **Check cables**: Use high-speed HDMI cables (1.4 or higher for 4K)

### For TV Casting

1. **Same network**: Ensure all devices are on the same network
2. **Enable DLNA**: On your TV, enable DLNA/UPnP media sharing
3. **Check IP**: Use `--list-tvs` to find the correct IP address
4. **Test connection**: Verify network connectivity before casting
5. **Use wired**: For best performance, use wired connections
6. **Check firewall**: Ensure firewall allows DLNA traffic (port 1900)

### For Plex

1. **Direct play**: Configure Plex to prefer direct play
2. **Enable transcoding**: Ensure transcoding is enabled for incompatible clients
3. **Organize libraries**: Keep your media well-organized
4. **Add metadata**: Ensure your media has proper metadata
5. **Regular updates**: Keep Plex server updated
6. **Backup**: Regularly backup your Plex configuration

---

## 📚 Documentation

### Available Guides

1. **[README.md](README.md)** - Main documentation
2. **[README_ENHANCED.md](README_ENHANCED.md)** - This file (Enhanced features)
3. **[QUICKSTART.md](QUICKSTART.md)** - Quick reference guide
4. **[SUMMARY.md](SUMMARY.md)** - Project summary
5. **[ENHANCED_FEATURES.md](ENHANCED_FEATURES.md)** - Complete list of new features
6. **[docs/USAGE.md](docs/USAGE.md)** - Complete usage guide
7. **[docs/TERMUX.md](docs/TERMUX.md)** - Android-specific guide
8. **[docs/STREMIO.md](docs/STREMIO.md)** - Stremio integration guide
9. **[docs/TV_INTEGRATION.md](docs/TV_INTEGRATION.md)** - TV integration guide
10. **[docs/PLEX.md](docs/PLEX.md)** - Plex integration guide

---

## 🐛 Troubleshooting

### TV Discovery Issues

| Issue | Solution |
|-------|----------|
| No TVs found | Check network connection, ensure TV is on same network |
| TV not responding | Enable DLNA/UPnP on TV, check firewall |
| VIDAA TV not detected | Enable media sharing in VIDAA settings |
| IP address not working | Use `--list-tvs` to find correct IP |

### Casting Issues

| Issue | Solution |
|-------|----------|
| Casting fails | Check if TV supports the video format |
| Audio not playing | Try different audio quality (raw, 5.1, stereo) |
| Video not playing | Try transcoding via Plex |
| Playback stops | Check network stability, try lower quality |

### Plex Issues

| Issue | Solution |
|-------|----------|
| Server not found | Check server IP and port |
| Authentication fails | Verify token or credentials |
| No results | Check Plex server is running and accessible |
| Transcoding required | Enable transcoding in Plex settings |

### Audio Issues

| Issue | Solution |
|-------|----------|
| No sound | Check HDMI connection, enable HDMI audio |
| Wrong audio format | Set audio quality to "raw" or "best" |
| Audio out of sync | Try different player or adjust audio sync |
| Only stereo | Check if source has surround sound, use "raw" audio |
| Audio cutting out | Lower audio quality or use transcoding |

---

## 📊 Comparison: Mwatcher vs Alternatives

| Feature | Mwatcher Enhanced | Popcorn Time | Stremio | Kodi | Plex |
|---------|------------------|--------------|--------|------|------|
| **One Command** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Multi-Platform** | ✅ All | ❌ Limited | ✅ Most | ✅ Most | ✅ Most |
| **No Ads** | ✅ Clean | ❌ Ads | ✅ Clean | ✅ Clean | ✅ Clean |
| **Offline Mode** | ✅ Download | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Stremio Support** | ✅ Full | ❌ No | ✅ Native | ❌ No | ❌ No |
| **Plex Support** | ✅ **Full** | ❌ No | ❌ No | ✅ Plugin | ✅ Native |
| **TV Casting** | ✅ **Full** | ❌ No | ❌ No | ✅ Plugin | ✅ Yes |
| **VIDAA OS Support** | ✅ **Full** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Audio Passthrough** | ✅ **Full** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **5.1/7.1 Support** | ✅ **Full** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **CLI-First** | ✅ Yes | ❌ GUI | ⚠️ Both | ⚠️ Both | ❌ GUI |
| **Mobile-Friendly** | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Partial | ✅ Yes |
| **Open Source** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Free** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ Premium |

---

## 🎉 What's Next?

### Planned Enhancements

- [ ] **Chromecast Support** - Google Cast protocol integration
- [ ] **AirPlay Support** - Apple TV and AirPlay devices
- [ ] **Miracast Support** - Wireless display casting
- [ ] **CEC Control** - TV remote control via HDMI CEC
- [ ] **Multi-Room Audio** - Synchronized audio across multiple devices
- [ ] **Voice Control** - Google Assistant and Alexa integration
- [ ] **Plex Webhooks** - Real-time notifications for new content
- [ ] **Plex Watch History** - Sync watch history with Plex
- [ ] **Plex User Switching** - Switch between Plex users
- [ ] **Plex Collections** - Browse Plex collections

### Potential Integrations

- **Kodi** - Direct integration with Kodi media center
- **Emby** - Alternative to Plex
- **Jellyfin** - Open-source alternative to Plex
- **Sonarr** - TV show automation
- **Radarr** - Movie automation
- **Trakt.tv** - Movie tracking
- **Letterboxd** - Movie logging
- **Tautulli** - Plex monitoring

---

## 🏆 Why Choose Mwatcher Enhanced?

### 1. **Universal Compatibility**
- Works on **any device**: Phone, tablet, computer, TV
- Works on **any platform**: Android, Linux, macOS, Windows
- Works with **any TV**: VIDAA OS, Android TV, Samsung, LG, etc.

### 2. **Best Audio Quality**
- **Raw audio passthrough** for lossless quality
- **5.1, 7.1 surround sound** support
- **Multiple audio formats** (AC3, E-AC3, DTS, TrueHD, etc.)
- **Player-specific optimization** for best results

### 3. **Full Plex Integration**
- **Your own media library** anywhere
- **Direct play** without transcoding when possible
- **Automatic transcoding** for incompatible devices
- **Multi-server support** for large libraries

### 4. **TV Casting**
- **No HDMI cable needed**
- **Cast to any TV** on your network
- **VIDAA OS support** for Hisense TVs
- **DLNA/UPnP** for universal compatibility

### 5. **Easy to Use**
- **One command** to watch any movie
- **Simple installation** on any platform
- **Interactive configuration**
- **Comprehensive documentation**

### 6. **Free and Open Source**
- **No subscriptions**
- **No ads**
- **No tracking**
- **Full control** over your data

---

## 🌟 Real-World Examples

```bash
# Movie night with 7.1 surround
mwatcher --source plex --tv "192.168.1.100" --audio 7.1 "Inception"

# Classic film with 5.1 audio
mwatcher --source plex --player vlc --audio 5.1 "The Godfather"

# Latest release via torrent with raw audio
mwatcher --source torrent --audio raw "John Wick 4"

# Netflix via Stremio with best audio
mwatcher --source stremio --audio best "Stranger Things"

# Download for travel
mwatcher --source plex --download "The Shawshank Redemption"

# Cast to VIDAA OS TV
mwatcher --tv "192.168.1.100" --source plex "Interstellar"

# Use MX Player on Android with raw audio
mwatcher --player mxplayer --audio raw "Pulp Fiction"

# Search and cast to TV
mwatcher --search "Marvel" && mwatcher --tv "192.168.1.100" "Avengers"
```

---

**Enjoy the ultimate movie experience on any device with amazing sound! 🎬🎧📺🍿**

*Made with ❤️ for movie and TV lovers everywhere*

*Copyright © 2024 Afzal Ashraf*

*GitHub: [https://github.com/AfzalAshraf/Mwatcher](https://github.com/AfzalAshraf/Mwatcher)*
