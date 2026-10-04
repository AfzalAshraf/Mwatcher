# 🚀 Mwatcher Enhanced Features

**Complete list of enhanced features for TV integration, Plex support, and raw audio passthrough**

---

## 🎯 New Features Summary

### ✅ **TV Integration**
- **VIDAA OS Support** - Full integration with Hisense VIDAA OS TVs
- **DLNA/UPnP Casting** - Cast to any DLNA-compatible device
- **Android TV Support** - Native support for Android TV devices
- **Automatic TV Discovery** - Discover all TVs on your local network
- **IP-Based Casting** - Cast to any TV by its IP address

### ✅ **Plex Integration**
- **Plex Media Server Support** - Connect to your Plex server
- **Multi-Server Support** - Connect to multiple Plex servers
- **Automatic Discovery** - Discover Plex servers on your network
- **Library Browsing** - Browse Plex libraries directly
- **Direct Play** - Play media without transcoding when possible
- **Transcoding Support** - Automatic transcoding for incompatible devices

### ✅ **Audio Passthrough**
- **Raw Audio Support** - 5.1, 7.1, and other surround sound formats
- **Audio Quality Presets** - raw, 5.1, 7.1, stereo, best
- **Player-Specific Settings** - VLC, MPV, MX Player audio configurations
- **Plex Audio Selection** - Choose specific audio tracks from Plex
- **Automatic Audio Detection** - Detect and use the best available audio

### ✅ **Enhanced Player Support**
- **Audio Passthrough Flags** - Player-specific audio passthrough settings
- **TV Casting Integration** - Cast to TVs from any player
- **Fallback System** - Automatic fallback to compatible players
- **Quality Control** - Video and audio quality settings

---

## 📁 New Files Added

### Core Modules
1. **[mwatcher_plex.py](mwatcher_plex.py)** - Complete Plex integration module
   - `PlexServer` - Plex server connection and management
   - `PlexManager` - Multiple Plex server management
   - `PlexAudioHandler` - Audio stream detection and selection
   - `DLNACaster` - DLNA/UPnP device discovery and casting
   - `TVPlatformHandler` - TV platform detection and handling
   - `EnhancedPlayerManager` - Player management with audio passthrough

2. **[mwatcher_enhanced.py](mwatcher_enhanced.py)** - Enhanced main script
   - Full TV and Plex integration
   - Audio passthrough support
   - Enhanced configuration options
   - New command-line arguments

### Documentation
3. **[docs/TV_INTEGRATION.md](docs/TV_INTEGRATION.md)** - Complete TV integration guide
   - VIDAA OS setup and usage
   - DLNA/UPnP casting
   - Android TV integration
   - Audio passthrough configuration

4. **[docs/PLEX.md](docs/PLEX.md)** - Complete Plex integration guide
   - Plex Media Server setup
   - Audio passthrough (5.1, 7.1)
   - Direct play vs transcoding
   - Usage examples and troubleshooting

---

## 🎛️ New Command-Line Arguments

### TV Casting
```bash
# Cast to TV by IP
mwatcher --tv "192.168.1.100" "Movie Name"

# List all TVs on network
mwatcher --list-tvs

# List VIDAA OS TVs specifically
mwatcher --list-vidaa
```

### Plex Integration
```bash
# Search Plex servers
mwatcher --plex "Movie Name"

# Search with Plex as source
mwatcher --source plex "Movie Name"
```

### Audio Quality
```bash
# Set audio quality
mwatcher --audio raw "Movie Name"
mwatcher --audio 5.1 "Movie Name"
mwatcher --audio 7.1 "Movie Name"
mwatcher --audio stereo "Movie Name"
mwatcher --audio best "Movie Name"

# List audio presets
mwatcher --list-audio
```

### Combined Features
```bash
# Cast Plex content to TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Movie Name"

# Play Plex content with specific player and audio
mwatcher --source plex --player vlc --audio 7.1 "Movie Name"
```

---

## 🌟 Feature Details

### 1. VIDAA OS Integration

**VIDAA OS** is Hisense's smart TV operating system. Mwatcher now fully supports VIDAA OS TVs with:

#### Features
- **Automatic Discovery**: Find all VIDAA OS TVs on your network
- **Direct Casting**: Cast movies directly to VIDAA OS TVs
- **Audio Passthrough**: Support for 5.1, 7.1 surround sound
- **Format Support**: MP4, MKV, AVI, MOV, and more
- **High-Definition**: 1080p and 4K support

#### Setup
```bash
# Discover VIDAA TVs
mwatcher --list-vidaa

# Cast to VIDAA TV
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast with specific audio
mwatcher --tv "192.168.1.100" --audio 5.1 "Movie Name"
```

#### Requirements
- VIDAA OS TV connected to the same network
- DLNA/UPnP enabled on the TV
- Media sharing enabled in VIDAA settings

---

### 2. DLNA/UPnP Casting

**DLNA (Digital Living Network Alliance)** is a standard for sharing media across devices. Mwatcher supports:

#### Supported Devices
- **VIDAA OS** (Hisense)
- **Tizen** (Samsung)
- **webOS** (LG)
- **Android TV** (Sony, Philips, Xiaomi, Nvidia)
- **Roku** (via Roku Media Player)
- **Amazon Fire TV**
- **PlayStation**
- **Xbox**
- **Chromecast** (via DLNA)
- **And many more DLNA-certified devices**

#### Features
- **Universal Compatibility**: Works with most DLNA-certified devices
- **Automatic Discovery**: Discovers devices on your local network
- **IP-Based Casting**: Cast to any device by its IP address
- **Format Support**: Supports most video and audio formats
- **Quality Control**: Adjust quality based on device capabilities

#### Usage
```bash
# Discover all DLNA devices
mwatcher --list-tvs

# Cast to any DLNA device
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast with specific source
mwatcher --tv "192.168.1.100" --source plex "Movie Name"
```

---

### 3. Plex Integration

**Plex** is a media server platform. Mwatcher now integrates with Plex for:

#### Features
- **Plex Server Connection**: Connect to your Plex Media Server
- **Multi-Server Support**: Connect to multiple Plex servers
- **Library Browsing**: Browse Plex libraries directly
- **Direct Play**: Play media without transcoding when possible
- **Transcoding**: Automatic transcoding for incompatible devices
- **Audio Selection**: Choose specific audio tracks
- **Metadata**: Access Plex metadata and artwork

#### Setup
```bash
# Add Plex server interactively
mwatcher --configure
# Select "Add Plex server"

# Discover Plex servers on network
mwatcher --configure
# Select "Discover Plex servers"
```

#### Usage
```bash
# Search Plex servers
mwatcher --plex "Movie Name"

# Search with Plex as source
mwatcher --source plex "Movie Name"

# Cast Plex content to TV
mwatcher --source plex --tv "192.168.1.100" "Movie Name"
```

---

### 4. Audio Passthrough (5.1, 7.1)

**Audio Passthrough** allows you to send raw, uncompressed audio directly to your receiver or TV. This preserves:
- **Original audio quality** (lossless formats)
- **Surround sound** (5.1, 7.1 channel audio)
- **Dynamic range** (full audio spectrum)

#### Supported Audio Formats
| Format | Channels | Codec | Raw Passthrough |
|--------|----------|-------|-----------------|
| **AAC** | 2.0, 5.1 | AAC | ❌ No |
| **AC3** | 2.0, 5.1 | Dolby Digital | ✅ Yes |
| **E-AC3** | 2.0, 5.1, 7.1 | Dolby Digital Plus | ✅ Yes |
| **DTS** | 2.0, 5.1 | DTS | ✅ Yes |
| **DTS-HD HR** | 2.0, 5.1, 7.1 | DTS-HD | ✅ Yes |
| **DTS-HD MA** | 2.0, 5.1, 7.1 | DTS-HD Master Audio | ✅ Yes |
| **TrueHD** | 2.0, 5.1, 7.1 | Dolby TrueHD | ✅ Yes |
| **FLAC** | 2.0 | FLAC | ✅ Yes |
| **PCM** | 2.0, 5.1, 7.1 | PCM | ✅ Yes |

#### Audio Quality Presets
| Preset | Description | Best For |
|--------|-------------|----------|
| **raw** | Raw passthrough | Home theaters, AV receivers |
| **5.1** | 5.1 surround | Soundbars, 5.1 systems |
| **7.1** | 7.1 surround | High-end systems |
| **stereo** | 2.0 stereo | Headphones, TV speakers |
| **best** | Best available | Automatic selection |

#### Configuration
```bash
# Set default audio quality
mwatcher --configure
# Select "Change audio quality"

# Use command line
mwatcher --audio raw "Movie Name"
```

#### Player-Specific Settings

**VLC Media Player:**
```
--spdif: Enable S/PDIF passthrough
--audio-channels=6: Force 5.1 channels
--audio-channels=8: Force 7.1 channels
--audio-device=hdmi: Use HDMI audio device
```

**MPV Player:**
```
--audio-device=alsa/default: Use ALSA audio device
--audio-channels=auto: Automatic channel selection
--audio-channels=5.1: Force 5.1 channels
--audio-channels=7.1: Force 7.1 channels
--audio-format=s16le: 16-bit little-endian format
```

---

## 🎬 Usage Examples

### Basic Examples

```bash
# Play a movie with raw audio
mwatcher --audio raw "Inception"

# Cast to VIDAA OS TV
mwatcher --tv "192.168.1.100" "Movie Name"

# Search Plex servers
mwatcher --plex "Movie Name"

# List all TVs on network
mwatcher --list-tvs
```

### Combined Features

```bash
# Cast Plex content to TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Inception"

# Play Plex content with VLC and 7.1 audio
mwatcher --source plex --player vlc --audio 7.1 "The Dark Knight"

# Search Plex and cast to VIDAA TV
mwatcher --plex --tv "192.168.1.100" "Interstellar"

# Cast YouTube to TV with 5.1 audio
mwatcher --source youtube --tv "192.168.1.100" --audio 5.1 "Music Video"
```

### Advanced Examples

```bash
# Discover TVs and cast
mwatcher --list-tvs
mwatcher --tv "192.168.1.100" --source plex --audio raw "Movie"

# Batch cast to TV
for movie in "Movie1" "Movie2" "Movie3"; do
  mwatcher --tv "192.168.1.100" "$movie"
done

# Play with specific audio and cast
mwatcher --source plex --player mpv --audio 7.1 --tv "192.168.1.100" "Movie"
```

---

## 🔧 Technical Details

### TV Discovery

Mwatcher uses **SSDP (Simple Service Discovery Protocol)** to discover DLNA/UPnP devices:

1. Sends M-SEARCH multicast to `239.255.255.250:1900`
2. Listens for responses from devices
3. Parses device descriptions (XML)
4. Identifies device type (VIDAA, Android TV, etc.)
5. Stores device information for casting

### Plex API

Mwatcher uses the **Plex HTTP API** to:

1. Authenticate with Plex servers
2. Discover Plex servers on network
3. Browse libraries
4. Search for content
5. Get direct play URLs
6. Get transcoded URLs
7. Access metadata and artwork

### Audio Detection

Mwatcher analyzes media to detect:

1. Available audio streams
2. Audio codecs (AC3, E-AC3, DTS, etc.)
3. Channel counts (2.0, 5.1, 7.1)
4. Bitrates
5. Language tags
6. Raw passthrough capability

---

## 📊 Comparison: Before vs After

### Before (Original Mwatcher)

| Feature | Support | Notes |
|---------|---------|-------|
| Basic movie playback | ✅ Yes | Works great |
| Multiple sources | ✅ Yes | YouTube, torrent, etc. |
| Multiple players | ✅ Yes | VLC, MPV, etc. |
| Stremio integration | ✅ Yes | Full support |
| Download capability | ✅ Yes | Offline viewing |
| TV casting | ❌ No | Not supported |
| Plex integration | ❌ No | Not supported |
| Audio passthrough | ❌ No | Not supported |
| VIDAA OS support | ❌ No | Not supported |

### After (Enhanced Mwatcher)

| Feature | Support | Notes |
|---------|---------|-------|
| Basic movie playback | ✅ Yes | Still works great |
| Multiple sources | ✅ Yes | YouTube, torrent, etc. |
| Multiple players | ✅ Yes | VLC, MPV, etc. |
| Stremio integration | ✅ Yes | Full support |
| Download capability | ✅ Yes | Offline viewing |
| **TV casting** | ✅ **Yes** | **NEW: DLNA/UPnP** |
| **Plex integration** | ✅ **Yes** | **NEW: Full Plex support** |
| **Audio passthrough** | ✅ **Yes** | **NEW: 5.1, 7.1 support** |
| **VIDAA OS support** | ✅ **Yes** | **NEW: Hisense TVs** |

---

## 🎯 What's Next?

### Planned Enhancements

1. **Chromecast Support** - Google Cast protocol integration
2. **AirPlay Support** - Apple TV and AirPlay devices
3. **Miracast Support** - Wireless display casting
4. **CEC Control** - TV remote control via HDMI CEC
5. **Multi-Room Audio** - Synchronized audio across multiple devices
6. **Voice Control** - Google Assistant and Alexa integration
7. **Plex Webhooks** - Real-time notifications for new content
8. **Plex Watch History** - Sync watch history with Plex
9. **Plex User Switching** - Switch between Plex users
10. **Plex Collections** - Browse Plex collections

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

## 📚 Documentation

### New Documentation Files

1. **[docs/TV_INTEGRATION.md](docs/TV_INTEGRATION.md)**
   - Complete TV integration guide
   - VIDAA OS setup and usage
   - DLNA/UPnP casting
   - Android TV integration
   - Audio passthrough configuration

2. **[docs/PLEX.md](docs/PLEX.md)**
   - Complete Plex integration guide
   - Plex Media Server setup
   - Audio passthrough (5.1, 7.1)
   - Direct play vs transcoding
   - Usage examples and troubleshooting

### Updated Documentation

- **[README.md](README.md)** - Updated with new features
- **[QUICKSTART.md](QUICKSTART.md)** - Updated with new commands
- **[SUMMARY.md](SUMMARY.md)** - Updated with new features
- **[docs/USAGE.md](docs/USAGE.md)** - Updated with new usage examples

---

## 🎉 Real-World Use Cases

### 1. Home Theater Setup

```bash
# Discover VIDAA OS TV
mwatcher --list-vidaa

# Cast 4K movie with 7.1 audio to home theater
mwatcher --source plex --tv "192.168.1.100" --audio 7.1 "Movie Name"
```

**Setup:**
- VIDAA OS TV connected via HDMI to AV receiver
- AV receiver connected to 7.1 speaker system
- Plex server with 4K movies and 7.1 audio tracks

**Result:**
- 4K video with 7.1 surround sound
- Raw audio passthrough to receiver
- No quality loss

### 2. Bedroom TV

```bash
# Cast to bedroom Android TV with 5.1 soundbar
mwatcher --source plex --tv "192.168.1.101" --audio 5.1 "Movie Name"
```

**Setup:**
- Android TV connected to 5.1 soundbar via HDMI ARC
- Plex server with movies and 5.1 audio

**Result:**
- High-quality video
- 5.1 surround sound via HDMI ARC
- Easy control from phone or computer

### 3. Multi-Room Setup

```bash
# Cast to living room TV
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast to bedroom TV
mwatcher --tv "192.168.1.101" "Movie Name"
```

**Setup:**
- Multiple TVs on the same network
- Plex server with shared library
- Mwatcher on phone or computer

**Result:**
- Watch the same movie on multiple TVs
- Or watch different movies on each TV
- Centralized control

### 4. Travel Setup

```bash
# Download movies for offline viewing
mwatcher --source plex --download "Movie Name"

# Play downloaded movies
mwatcher "Movie Name"
```

**Setup:**
- Laptop with Mwatcher installed
- Downloaded movies from Plex
- Headphones for private viewing

**Result:**
- Offline movie access
- No internet required
- High-quality playback

### 5. Hotel Room

```bash
# Cast to hotel TV via DLNA
mwatcher --tv "192.168.1.100" --source plex "Movie Name"
```

**Setup:**
- Laptop or phone with Mwatcher
- Hotel TV with DLNA support
- Plex server at home (with remote access)

**Result:**
- Watch your own movies on hotel TV
- No need for HDMI cable
- Secure connection

---

## 💡 Tips and Tricks

### For Best Audio Quality

1. **Use HDMI**: Always use HDMI for audio passthrough
2. **Check receiver**: Ensure your AV receiver supports the audio format
3. **Enable passthrough**: In TV/receiver settings, enable audio passthrough
4. **Use raw audio**: Set audio quality to "raw" for best results
5. **Test content**: Use media with known audio formats for testing

### For TV Casting

1. **Same network**: Ensure all devices are on the same network
2. **Enable DLNA**: On your TV, enable DLNA/UPnP media sharing
3. **Check IP**: Use `--list-tvs` to find the correct IP address
4. **Test connection**: Verify network connectivity before casting
5. **Use wired**: For best performance, use wired connections

### For Plex

1. **Direct play**: Configure Plex to prefer direct play
2. **Enable transcoding**: Ensure transcoding is enabled for incompatible clients
3. **Organize libraries**: Keep your media well-organized
4. **Add metadata**: Ensure your media has proper metadata
5. **Regular updates**: Keep Plex server updated

---

## 🐛 Troubleshooting

### TV Discovery Issues

| Issue | Solution |
|-------|----------|
| No TVs found | Check network connection |
| TV not responding | Enable DLNA/UPnP on TV |
| VIDAA TV not detected | Enable media sharing in VIDAA settings |
| Wrong IP address | Use `--list-tvs` to find correct IP |

### Casting Issues

| Issue | Solution |
|-------|----------|
| Casting fails | Check if TV supports the format |
| Audio not playing | Try different audio quality |
| Video not playing | Try transcoding via Plex |
| Playback stops | Check network stability |

### Plex Issues

| Issue | Solution |
|-------|----------|
| Server not found | Check IP and port |
| Authentication fails | Verify token/credentials |
| No results | Check library configuration |
| Transcoding required | Enable transcoding in Plex |

### Audio Issues

| Issue | Solution |
|-------|----------|
| No sound | Check HDMI connection |
| Wrong format | Set audio quality to "raw" |
| Out of sync | Try different player |
| Only stereo | Check source audio tracks |

---

## 📞 Support

### Getting Help

1. **Documentation**: Check the docs/ folder for detailed guides
2. **GitHub Issues**: Report issues at [https://github.com/AfzalAshraf/Mwatcher/issues](https://github.com/AfzalAshraf/Mwatcher/issues)
3. **Community**: Join the Discord server (coming soon)
4. **Plex Support**: [https://support.plex.tv](https://support.plex.tv)
5. **DLNA Support**: Check your TV manufacturer's support

### Debug Commands

```bash
# Check TV discovery
mwatcher --list-tvs -v

# Check Plex connection
mwatcher --plex "test" -v

# Check audio streams
mwatcher --source plex --audio raw "Movie" -v

# View logs
cat ~/.mwatcher/logs/mwatcher.log
```

---

## 🎊 Conclusion

**Mwatcher Enhanced** brings **powerful new features** to the universal movie watcher:

✅ **TV Integration** - Cast to any TV on your network
✅ **VIDAA OS Support** - Full support for Hisense TVs
✅ **Plex Integration** - Access your media library anywhere
✅ **Audio Passthrough** - 5.1, 7.1 surround sound support
✅ **Multi-Device** - Watch on any device with best quality
✅ **Easy to Use** - Simple commands for complex features

With these enhancements, Mwatcher is now the **ultimate movie watching solution** for any device, any platform, with the best possible audio and video quality!

---

**Enjoy the ultimate movie experience! 🎬🎧📺🍿**

*Made with ❤️ for movie and TV lovers everywhere*

*Copyright © 2024 Afzal Ashraf*
