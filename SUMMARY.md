# 📋 Mwatcher - Project Summary

## 🎯 What We Built

**Mwatcher** is a universal movie watcher that allows you to watch movies from any device with just one command. It supports:

- ✅ **All Platforms**: Termux (Android), Linux, macOS, Windows (WSL)
- ✅ **All Players**: VLC, MPV, MX Player, and system defaults
- ✅ **All Sources**: YouTube, Torrent, Stremio, PrimeWire, FMovies, Putlocker, SolarMovie
- ✅ **Stremio Integration**: Full support for Stremio addons
- ✅ **Download Feature**: Save movies for offline viewing
- ✅ **One-Click Installation**: Simple scripts for all platforms

---

## 📁 Project Structure

```
Mwatcher/
├── README.md                    # Main documentation
├── SUMMARY.md                  # This file
├── mwatcher.py                 # Main Python script (core functionality)
├── mwatcher.sh                 # Shell wrapper for easy execution
├── mwatcher_cli.py             # CLI entry point for pip installation
├── setup.py                    # Setup script for pip installation
├── requirements.txt            # Python dependencies
├── install.sh                  # Universal installation script
├── install_termux.sh           # Termux-specific installation script
├── docs/
│   ├── USAGE.md                # Complete usage guide
│   ├── TERMUX.md               # Termux-specific guide
│   └── STREMIO.md              # Stremio integration guide
└── .git/
```

---

## 🚀 Core Features

### 1. Multi-Platform Support
- **Termux** on Android with full Linux environment
- **Linux** (Ubuntu, Debian, Fedora, Arch, etc.)
- **macOS** Terminal
- **Windows** via WSL or Git Bash

### 2. Video Player Integration
- **VLC Media Player**: Most popular, full-featured
- **MPV Player**: Lightweight, keyboard-controlled
- **MX Player**: Android-optimized with hardware acceleration
- **Termux MPV**: Optimized for mobile
- **Default Players**: System file openers as fallback

### 3. Content Sources
- **YouTube**: Full movies, trailers, documentaries
- **Torrent Streaming**: Peer-to-peer streaming via WebTorrent
- **Stremio**: Full integration with Stremio addons (Netflix, Disney+, HBO, etc.)
- **PrimeWire**: Free movie streaming
- **FMovies**: Popular streaming site
- **Putlocker**: Another streaming source
- **SolarMovie**: HD quality movies
- **Custom Sources**: Add your own movie sites

### 4. Key Functionality
- **Smart Search**: Search across multiple sources simultaneously
- **Direct Play**: One command to find and play any movie
- **Download Mode**: Save movies for offline viewing
- **Configuration**: Choose sources, players, quality
- **Quality Control**: 480p, 720p, 1080p, or best
- **URL Support**: Play any direct video URL
- **Fallback System**: Automatically tries alternative players

---

## 💻 Installation Methods

### 1. Termux (Android)
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

### 2. Linux/macOS
```bash
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)
```

### 3. Manual Installation
```bash
# Install dependencies
pip install yt-dlp requests beautifulsoup4

# Clone repository
git clone https://github.com/AfzalAshraf/Mwatcher.git
cd Mwatcher

# Make executable
chmod +x mwatcher.sh mwatcher.py

# Create symlink
ln -s $(pwd)/mwatcher.sh /usr/local/bin/mwatcher
```

### 4. pip Installation
```bash
pip install -r requirements.txt
python setup.py install
```

---

## 📖 Usage Examples

### Basic Commands
```bash
# Play a movie
mwatcher "Inception"

# Search for movies
mwatcher --search "The Matrix"

# Play with specific source
mwatcher --source youtube "Interstellar"

# Use specific player
mwatcher --player vlc "Pulp Fiction"

# Download movie
mwatcher --download "The Shawshank Redemption"

# Play direct URL
mwatcher --url "https://example.com/movie.mp4"
```

### Stremio Integration
```bash
# Search via Stremio
mwatcher --source stremio "Dune"

# Use specific addon
mwatcher --stremio "stremio://cinemeta/com.cinemeta.addon"
```

---

## 🛠️ Technical Details

### Python Modules
- **mwatcher.py**: Main script with all core functionality
  - `ConfigManager`: Manages configuration and settings
  - `MovieSearcher`: Searches for movies across multiple sources
  - `StreamExtractor`: Extracts playable streams from various sources
  - `PlayerManager`: Manages video players and playback
  - `Mwatcher`: Main class that ties everything together

### Supported Stremio Addons
- Torrentio (with REAL-DEBRID)
- Cinemeta (metadata)
- Popcorn Time (catalog)
- YouTube
- Netflix, Disney+, HBO Max, Amazon Prime (require login)
- And many more community addons

### Configuration
- Configuration file: `~/.mwatcher/config.json`
- Cache directory: `~/.mwatcher/cache/`
- Logs directory: `~/.mwatcher/logs/`

---

## 🎨 User Experience

### Termux (Android)
- Full Linux environment on Android
- Support for MX Player, VLC, MPV
- Storage access for downloads
- Background playback
- Home screen shortcuts via Termux:Widget

### Linux/macOS
- Native terminal integration
- Full keyboard control
- System tray integration (future)
- Desktop notifications (future)

### All Platforms
- Consistent command-line interface
- Smart source selection
- Automatic fallback to alternative players
- Configurable quality and subtitles

---

## 📊 Statistics

- **Lines of Code**: ~1000+ (Python)
- **Files Created**: 11
- **Documentation Pages**: 4
- **Supported Platforms**: 4
- **Supported Players**: 5+
- **Supported Sources**: 7+
- **Stremio Addons**: 20+

---

## 🎯 Use Cases

### 1. Quick Movie Night
```bash
mwatcher "The Avengers"
```

### 2. Research and Learning
```bash
mwatcher --source youtube "Documentary Title"
```

### 3. Offline Travel
```bash
mwatcher --download "Movie for Travel"
```

### 4. Premium Content Access
```bash
mwatcher --source stremio "Netflix Original"
```

### 5. Torrent Streaming
```bash
mwatcher --source torrent "Latest Release"
```

### 6. Batch Operations
```bash
for movie in "Movie1" "Movie2" "Movie3"; do
  mwatcher --download "$movie"
done
```

---

## 🌟 Unique Selling Points

### vs. Other Solutions

| Feature | Mwatcher | Popcorn Time | Stremio | Kodi |
|---------|----------|--------------|--------|------|
| **One Command** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Multi-Platform** | ✅ All | ❌ Limited | ✅ Most | ✅ Most |
| **No Installation** | ⚠️ Minimal | ✅ Yes | ❌ Required | ❌ Required |
| **Stremio Integration** | ✅ Full | ❌ No | ✅ Native | ❌ No |
| **Torrent Streaming** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Custom Sources** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **CLI-First** | ✅ Yes | ❌ GUI | ⚠️ Both | ⚠️ Both |
| **Mobile-Friendly** | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Partial |
| **Open Source** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

### Advantages

1. **Simplicity**: One command to find and play any movie
2. **Flexibility**: Works on any device with any player
3. **Extensibility**: Easy to add new sources and features
4. **Integration**: Full Stremio addon support
5. **Portability**: Works on Android via Termux
6. **Privacy**: No tracking, open source
7. **Offline**: Download capability

---

## 🔧 Customization Options

### 1. Add Custom Sources
```bash
mwatcher --configure
# Select "Add custom source"
```

### 2. Change Default Player
```bash
mwatcher --configure
# Select "Change preferred player"
```

### 3. Set Quality Preferences
```bash
mwatcher --configure
# Set quality to 480p, 720p, 1080p, or best
```

### 4. Enable/Disable Subtitles
```bash
mwatcher --configure
# Toggle subtitles
```

### 5. Environment Variables
```bash
export MWATCHER_PLAYER=mpv
export MWATCHER_SOURCES="youtube,torrent,stremio"
```

---

## 📚 Documentation

### Available Guides
1. **[README.md](README.md)**: Main documentation with quick start
2. **[USAGE.md](docs/USAGE.md)**: Complete usage guide and command reference
3. **[TERMUX.md](docs/TERMUX.md)**: Android-specific guide with Termux tips
4. **[STREMIO.md](docs/STREMIO.md)**: Full Stremio integration guide

### Documentation Features
- Step-by-step installation guides
- Platform-specific instructions
- Troubleshooting sections
- Best practices
- Advanced usage examples

---

## 🐛 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Command not found | Check PATH, verify symlink |
| Module not found | Install dependencies with pip |
| Player not found | Install VLC or MPV |
| No results | Try different source, check internet |
| Permission denied | Grant storage access |
| Slow streaming | Lower quality, try different source |

### Debug Commands
```bash
# Check installation
mwatcher --version

# Check dependencies
python3 -c "import yt_dlp, requests, bs4; print('OK')"

# View logs
cat ~/.mwatcher/logs/mwatcher.log
```

---

## 🚀 Future Enhancements

### Planned Features
- [ ] **Subtitle Download**: Automatic subtitle download and sync
- [ ] **Playlist Support**: Create and manage movie playlists
- [ ] **Watch History**: Track watched movies
- [ ] **Favorites**: Save favorite movies for quick access
- [ ] **Web Interface**: Browser-based control panel
- [ ] **Chromecast Support**: Cast to TV directly
- [ ] **AirPlay Support**: Stream to Apple TV
- [ ] **DLNA Support**: Stream to smart TVs
- [ ] **Multi-Language**: Support for non-English sources
- [ ] **Parental Controls**: Family-friendly mode

### Potential Integrations
- **Plex**: Access Plex media server
- **Jellyfin**: Open-source media server
- **Emby**: Media server alternative
- **Sonarr/Radarr**: Automation integration
- **Trakt.tv**: Movie tracking
- **Letterboxd**: Movie logging

---

## 🎓 Learning Outcomes

### What You Can Learn from This Project

1. **Python Scripting**: Building command-line tools
2. **Cross-Platform Development**: Supporting multiple platforms
3. **API Integration**: Working with YouTube, Stremio, etc.
4. **Web Scraping**: Extracting data from websites
5. **Process Management**: Running external programs (players)
6. **Configuration Management**: User preferences and settings
7. **Error Handling**: Robust error handling and fallbacks
8. **Documentation**: Writing comprehensive guides
9. **Installation Scripts**: Creating easy installation methods
10. **Modular Design**: Separating concerns (search, extract, play)

---

## 🙏 Contributing

### How to Contribute

1. **Fork the repository** on GitHub
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Contribution Ideas

- Add new movie sources
- Improve existing sources
- Add new player integrations
- Improve error handling
- Enhance documentation
- Add translations
- Implement new features from roadmap

---

## 📜 License

This project is licensed under the **MIT License** - free to use, modify, and distribute.

---

## 📞 Support & Community

- **GitHub Issues**: [https://github.com/AfzalAshraf/Mwatcher/issues](https://github.com/AfzalAshraf/Mwatcher/issues)
- **Documentation**: This repository
- **Discord**: Coming soon
- **Email**: Contact via GitHub

---

## 🎉 Conclusion

Mwatcher is a powerful, flexible, and easy-to-use movie watching solution that works on virtually any device. Whether you're on your phone via Termux, your laptop running Linux or macOS, or even Windows with WSL, Mwatcher provides a consistent, ad-free experience for watching movies with just one command.

### Key Benefits
- ✅ **Universal**: Works on all your devices
- ✅ **Simple**: One command to watch any movie
- ✅ **Powerful**: Access to multiple sources and players
- ✅ **Flexible**: Customizable to your preferences
- ✅ **Free**: Open source, no subscriptions
- ✅ **Private**: No tracking, no ads

**Start watching movies the easy way with Mwatcher!**

---

*Made with ❤️ for movie lovers everywhere*

*Copyright © 2024 Afzal Ashraf*

*GitHub: [https://github.com/AfzalAshraf/Mwatcher](https://github.com/AfzalAshraf/Mwatcher)*
