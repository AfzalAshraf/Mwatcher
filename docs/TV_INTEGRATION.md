# 📺 Mwatcher TV Integration Guide

Complete guide to using Mwatcher with TVs, including VIDAA OS, Android TV, and DLNA/UPnP devices.

---

## 📋 Table of Contents

1. [VIDAA OS Integration](#vidaa-os-integration)
2. [DLNA/UPnP Casting](#dlnaupnp-casting)
3. [Android TV Integration](#android-tv-integration)
4. [Plex Integration](#plex-integration)
5. [Audio Passthrough (5.1, 7.1)](#audio-passthrough-51-71)
6. [Setup Instructions](#setup-instructions)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)

---

## VIDAA OS Integration

**VIDAA OS** is Hisense's smart TV operating system. Mwatcher can discover and cast to VIDAA OS TVs on your local network.

### How It Works

Mwatcher uses **DLNA/UPnP** protocol to discover VIDAA OS TVs and cast content directly to them. VIDAA OS supports:
- **Video playback** from local network sources
- **Audio passthrough** for 5.1 and 7.1 surround sound
- **Various video formats** (MP4, MKV, AVI, etc.)
- **High-definition** playback (1080p, 4K)

### Setup

1. **Connect to the same network**: Ensure your device running Mwatcher is on the same network as your VIDAA OS TV
2. **Enable network sharing**: On your VIDAA TV, go to Settings → Network → Enable media sharing
3. **Enable DLNA**: On your VIDAA TV, go to Settings → Connectivity → DLNA and enable it

### Discovery

```bash
# Discover all TVs on the network
mwatcher --list-tvs

# Discover only VIDAA OS TVs
mwatcher --list-vidaa
```

### Casting to VIDAA OS

```bash
# Cast a movie to your VIDAA TV
mwatcher --tv "192.168.1.100" "Inception"

# Cast with specific source
mwatcher --tv "192.168.1.100" --source plex "Movie Name"

# Cast with specific audio quality
mwatcher --tv "192.168.1.100" --audio raw "Movie Name"
```

### VIDAA OS Specific Features

- **Direct play**: VIDAA OS supports direct play of most video formats
- **Transcoding**: For unsupported formats, Mwatcher can transcode via Plex
- **Audio passthrough**: Supports 5.1 and 7.1 surround sound via HDMI
- **Subtitles**: Supports embedded subtitles and external subtitle files

---

## DLNA/UPnP Casting

**DLNA (Digital Living Network Alliance)** is a standard for sharing media across devices. Mwatcher can cast to any DLNA-compatible device.

### Supported Devices

| Device Type | Brand | OS | Notes |
|------------|-------|----|-------|
| Smart TVs | Hisense | VIDAA OS | Full support |
| Smart TVs | Samsung | Tizen | Full support |
| Smart TVs | LG | webOS | Full support |
| Smart TVs | Sony | Android TV | Full support |
| Smart TVs | Philips | Android TV | Full support |
| Streaming Devices | Roku | Roku OS | Limited support |
| Streaming Devices | Amazon | Fire TV | Full support |
| Streaming Devices | Google | Chromecast | Via DLNA |
| Gaming Consoles | Sony | PlayStation | Full support |
| Gaming Consoles | Microsoft | Xbox | Full support |
| Gaming Consoles | Nintendo | Switch | Limited support |
| Media Players | Various | Various | Full support |

### Discovery

```bash
# List all DLNA devices on the network
mwatcher --list-tvs
```

### Casting

```bash
# Cast to any DLNA device by IP
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast with specific audio quality
mwatcher --tv "192.168.1.100" --audio 5.1 "Movie Name"
```

### DLNA Features

- **Universal compatibility**: Works with most DLNA-certified devices
- **Automatic detection**: Discovers devices on your local network
- **IP-based casting**: Cast to any device by its IP address
- **Format support**: Supports most video and audio formats

---

## Android TV Integration

**Android TV** is Google's TV platform used by Sony, Philips, Xiaomi, and other brands.

### Setup

1. **Install Mwatcher on Android TV**:
   - Install Termux from Play Store
   - Install Mwatcher using the Termux installation script
   - Or sideload the APK (future feature)

2. **Enable unknown sources**: Go to Settings → Security & restrictions → Enable unknown sources

3. **Install a file manager**: For accessing downloaded movies

### Usage

```bash
# On Android TV with Termux
mwatcher "Movie Name"

# Use MX Player (recommended for Android TV)
mwatcher --player mxplayer "Movie Name"

# Cast to another TV from Android TV
mwatcher --tv "192.168.1.101" "Movie Name"
```

### Android TV Specific Features

- **MX Player integration**: Optimized for Android TV with hardware acceleration
- **VLC for Android**: Alternative player with full format support
- **Remote control**: Use your TV remote with Termux
- **Voice search**: Use Google Assistant to control playback

---

## Plex Integration

**Plex** is a media server platform that organizes your personal media library. Mwatcher integrates with Plex for:

- **Direct play**: Play media directly from your Plex server
- **Transcoding**: Automatically transcode for incompatible devices
- **Raw audio passthrough**: Support for 5.1, 7.1, and other surround sound formats
- **Multi-server support**: Connect to multiple Plex servers

### Setup

#### Step 1: Install Plex Media Server

1. Download Plex Media Server from [https://plex.tv](https://plex.tv)
2. Install on your computer or NAS
3. Add your media libraries

#### Step 2: Configure Plex in Mwatcher

```bash
# Interactive configuration
mwatcher --configure
# Select "Add Plex server"

# Or manually
mwatcher --configure
# Option 7: Add Plex server
```

#### Step 3: Discover Plex Servers

```bash
# Automatically discover Plex servers on your network
mwatcher --configure
# Option 8: Discover Plex servers
```

### Usage

```bash
# Search Plex servers
mwatcher --plex "Movie Name"

# Search with specific source
mwatcher --source plex "Movie Name"

# Play with raw audio passthrough
mwatcher --source plex --audio raw "Movie Name"

# Cast Plex content to TV
mwatcher --source plex --tv "192.168.1.100" "Movie Name"
```

### Plex Features

- **Direct stream**: Play media without transcoding when possible
- **Quality selection**: Choose from available qualities
- **Audio selection**: Select specific audio tracks (5.1, 7.1, stereo)
- **Subtitle support**: Download and display subtitles
- **Multi-user support**: Connect to multiple Plex servers
- **Remote access**: Access your Plex server from anywhere

---

## Audio Passthrough (5.1, 7.1)

Mwatcher supports **raw audio passthrough** for high-quality surround sound. This is especially important for:

- **Home theater systems** with 5.1 or 7.1 speakers
- **Soundbars** with surround sound support
- **AV receivers** with HDMI ARC/eARC
- **High-end TVs** with built-in surround sound

### Supported Audio Formats

| Format | Channels | Bitrate | Notes |
|--------|----------|---------|-------|
| **AAC** | 2.0, 5.1 | Up to 320 kbps | Most common |
| **AC3 (Dolby Digital)** | 2.0, 5.1 | Up to 640 kbps | Standard 5.1 |
| **E-AC3 (Dolby Digital Plus)** | 2.0, 5.1, 7.1 | Up to 1.5 Mbps | Advanced 5.1/7.1 |
| **DTS** | 2.0, 5.1 | Up to 1.5 Mbps | DTS surround |
| **DTS-HD** | 2.0, 5.1, 7.1 | Up to 6 Mbps | High-definition DTS |
| **TrueHD** | 2.0, 5.1, 7.1 | Up to 18 Mbps | Lossless Dolby |
| **FLAC** | 2.0 | Variable | Lossless audio |
| **PCM** | 2.0, 5.1, 7.1 | Variable | Uncompressed |

### Audio Quality Presets

Mwatcher provides several audio quality presets:

| Preset | Description | Best For |
|--------|-------------|----------|
| **raw** | Raw passthrough | Home theaters, AV receivers |
| **5.1** | 5.1 surround | Soundbars, 5.1 systems |
| **7.1** | 7.1 surround | High-end systems |
| **stereo** | 2.0 stereo | Headphones, TV speakers |
| **best** | Best available | Automatic selection |

### Configuration

```bash
# Set audio quality in configuration
mwatcher --configure
# Option 4: Change audio quality

# Or use command line
mwatcher --audio raw "Movie Name"
mwatcher --audio 5.1 "Movie Name"
mwatcher --audio 7.1 "Movie Name"
```

### Player-Specific Audio Settings

#### VLC Media Player

```bash
# Raw passthrough (S/PDIF)
mwatcher --player vlc --audio raw "Movie Name"

# Specific channel count
mwatcher --player vlc --audio 5.1 "Movie Name"
```

VLC audio flags used:
- `--spdif`: Enable S/PDIF passthrough
- `--audio-channels=6`: Force 5.1 channels
- `--audio-channels=8`: Force 7.1 channels
- `--audio-filter normvol`: Normalize volume
- `--audio-sync 0`: No audio sync adjustment

#### MPV Player

```bash
# Raw passthrough
mwatcher --player mpv --audio raw "Movie Name"

# Specific channel count
mwatcher --player mpv --audio 5.1 "Movie Name"
```

MPV audio flags used:
- `--audio-device=alsa/default`: Use ALSA audio device
- `--audio-channels=auto`: Automatic channel selection
- `--audio-channels=5.1`: Force 5.1 channels
- `--audio-channels=7.1`: Force 7.1 channels
- `--audio-format=s16le`: 16-bit little-endian format

### Plex Audio Passthrough

When using Plex with Mwatcher:

1. **Direct play**: Mwatcher requests the direct play URL with the best audio stream
2. **Audio selection**: Mwatcher automatically selects the best audio stream based on your preference
3. **Raw passthrough**: If you select "raw" audio quality, Mwatcher will prefer audio streams that support passthrough

```bash
# Play from Plex with raw audio
mwatcher --source plex --audio raw "Movie Name"

# Cast from Plex to TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Movie Name"
```

### Troubleshooting Audio

| Issue | Solution |
|-------|----------|
| No sound | Check HDMI connection, enable HDMI audio |
| Wrong audio format | Set audio quality to "raw" or "best" |
| Audio out of sync | Try different player or enable audio sync |
| Only stereo sound | Check if source has surround sound, use "raw" audio |
| Audio cutting out | Lower audio quality or use transcoding |

---

## Setup Instructions

### Prerequisites

1. **Network connectivity**: All devices must be on the same local network
2. **Python 3.6+**: Required for Mwatcher
3. **Required packages**: `yt-dlp`, `requests`, `beautifulsoup4`
4. **Optional packages**: For TV discovery and casting

### Installation

```bash
# Install Mwatcher
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install.sh)

# Or for Termux
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/install_termux.sh)
```

### Enable TV Discovery

```bash
# List TVs on your network
mwatcher --list-tvs

# List VIDAA OS TVs specifically
mwatcher --list-vidaa
```

### Add Plex Server

```bash
# Add Plex server interactively
mwatcher --configure
# Select "Add Plex server"

# Or discover automatically
mwatcher --configure
# Select "Discover Plex servers"
```

---

## Usage Examples

### Basic TV Casting

```bash
# Discover TVs
mwatcher --list-tvs

# Cast to TV
mwatcher --tv "192.168.1.100" "Inception"

# Cast with specific source
mwatcher --tv "192.168.1.100" --source plex "Movie Name"

# Cast with specific audio
mwatcher --tv "192.168.1.100" --audio raw "Movie Name"
```

### Plex with TV

```bash
# Add Plex server
mwatcher --configure
# Add your Plex server

# Search Plex
mwatcher --plex "Movie Name"

# Cast Plex to TV
mwatcher --plex --tv "192.168.1.100" "Movie Name"

# Cast Plex with raw audio
mwatcher --plex --tv "192.168.1.100" --audio raw "Movie Name"
```

### VIDAA OS Specific

```bash
# List VIDAA TVs
mwatcher --list-vidaa

# Cast to VIDAA TV
mwatcher --tv "192.168.1.100" "Movie Name"

# Cast with 5.1 audio
mwatcher --tv "192.168.1.100" --audio 5.1 "Movie Name"
```

### Audio Passthrough

```bash
# List audio presets
mwatcher --list-audio

# Play with raw audio
mwatcher --audio raw "Movie Name"

# Play with 5.1 audio
mwatcher --audio 5.1 "Movie Name"

# Play with 7.1 audio
mwatcher --audio 7.1 "Movie Name"

# Cast with raw audio
mwatcher --tv "192.168.1.100" --audio raw "Movie Name"
```

### Advanced Usage

```bash
# Cast Plex content to VIDAA TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Movie Name"

# Search and cast first result to TV
mwatcher --search "Movie" && mwatcher --tv "192.168.1.100" "Movie"

# Batch cast to TV
for movie in "Movie1" "Movie2" "Movie3"; do
  mwatcher --tv "192.168.1.100" "$movie"
done
```

---

## Troubleshooting

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
| Audio not playing | Try different audio quality (stereo, 5.1, raw) |
| Video not playing | Try transcoding via Plex |
| Playback stops | Check network stability, try lower quality |

### Plex Issues

| Issue | Solution |
|-------|----------|
| Plex server not found | Check server IP and port |
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

### Network Issues

| Issue | Solution |
|-------|----------|
| Slow streaming | Use wired connection, lower quality |
| Buffering | Check network speed, close other apps |
| Connection drops | Check router settings, enable QoS |
| Firewall blocking | Allow Mwatcher through firewall |

---

## Best Practices

### For VIDAA OS

1. **Use wired connection**: For best performance, connect your VIDAA TV via Ethernet
2. **Enable media sharing**: Go to Settings → Network → Enable media sharing
3. **Update firmware**: Keep your VIDAA TV firmware up to date
4. **Use compatible formats**: VIDAA OS supports MP4, MKV, AVI, MOV, etc.
5. **Check audio settings**: Ensure HDMI audio output is enabled

### For Plex

1. **Enable direct play**: In Plex settings, enable direct play for compatible devices
2. **Set quality limits**: Configure quality limits based on your network speed
3. **Enable transcoding**: Ensure transcoding is enabled for incompatible devices
4. **Organize libraries**: Organize your media into proper libraries
5. **Add metadata**: Ensure your media has proper metadata for best experience

### For Audio Passthrough

1. **Use HDMI**: For raw audio passthrough, use HDMI connection
2. **Check receiver settings**: Ensure your AV receiver supports the audio format
3. **Enable passthrough**: In your TV or receiver settings, enable audio passthrough
4. **Use compatible player**: VLC and MPV support audio passthrough
5. **Check source quality**: Ensure your media has high-quality audio tracks

---

## Supported TV Brands and Models

### VIDAA OS (Hisense)
- **All models**: 2016 and newer
- **Features**: Full DLNA support, 4K, HDR, surround sound
- **Limitations**: Some older models may have limited format support

### Android TV
- **Sony**: All Android TV models
- **Philips**: All Android TV models
- **Xiaomi**: Mi TV series
- **Nvidia**: Shield TV
- **Features**: Full DLNA support, Google Cast, various apps

### Tizen (Samsung)
- **All models**: 2015 and newer
- **Features**: DLNA support, Smart View
- **Limitations**: Some format restrictions

### webOS (LG)
- **All models**: 2014 and newer
- **Features**: DLNA support, TV Plus
- **Limitations**: Some format restrictions

### Roku
- **All models**: Roku 2 and newer
- **Features**: Limited DLNA support via Roku Media Player
- **Limitations**: Not all formats supported

---

## Future Enhancements

### Planned Features
- [ ] **Direct VIDAA OS API integration** (better than DLNA)
- [ ] **Chromecast support** (Google Cast protocol)
- [ ] **AirPlay support** (Apple TV)
- [ ] **Miracast support** (Wireless display)
- [ ] **TV remote control** (via CEC)
- [ ] **Automatic quality adjustment** (based on network speed)
- [ ] **Multi-room audio sync** (for whole-home audio)
- [ ] **Voice control integration** (Google Assistant, Alexa)

### Potential Integrations
- **Kodi**: Direct integration with Kodi media center
- **Emby**: Alternative to Plex
- **Jellyfin**: Open-source alternative to Plex
- **Sonarr/Radarr**: Automation integration
- **Trakt.tv**: Movie tracking
- **Letterboxd**: Movie logging

---

## Conclusion

Mwatcher provides **comprehensive TV integration** with support for:
- **VIDAA OS** and other smart TV platforms
- **DLNA/UPnP** casting to any compatible device
- **Plex Media Server** integration with raw audio passthrough
- **5.1 and 7.1 surround sound** support
- **Multiple audio formats** and quality options

With Mwatcher, you can **watch movies on any TV** with **high-quality audio** using just one command!

---

**Enjoy your movies on the big screen with amazing sound! 🎬🔊🍿**
