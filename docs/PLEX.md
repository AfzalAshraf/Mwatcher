# 🎬 Mwatcher Plex Integration Guide

Complete guide to using Mwatcher with Plex Media Server for the ultimate movie experience with raw 5.1, 7.1 audio.

---

## 📋 Table of Contents

1. [What is Plex?](#what-is-plex)
2. [Setup Plex Media Server](#setup-plex-media-server)
3. [Configure Plex in Mwatcher](#configure-plex-in-mwatcher)
4. [Audio Passthrough (5.1, 7.1)](#audio-passthrough-51-71)
5. [Direct Play vs Transcoding](#direct-play-vs-transcoding)
6. [Usage Examples](#usage-examples)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## What is Plex?

**Plex** is a media server platform that:
- **Organizes** your personal media library (movies, TV shows, music, photos)
- **Streams** media to any device (TVs, phones, tablets, computers)
- **Transcodes** media on-the-fly for incompatible devices
- **Provides** a beautiful, Netflix-like interface
- **Supports** multiple users with personalized recommendations

### Why Use Plex with Mwatcher?

| Feature | Plex + Mwatcher | Standalone Mwatcher |
|---------|----------------|---------------------|
| **Your own library** | ✅ Yes | ❌ No |
| **Raw audio passthrough** | ✅ Yes | ⚠️ Limited |
| **5.1/7.1 surround** | ✅ Yes | ⚠️ Source-dependent |
| **High-quality streaming** | ✅ Yes | ✅ Yes |
| **Offline access** | ✅ Yes | ✅ Yes |
| **Multi-device sync** | ✅ Yes | ❌ No |
| **Metadata & artwork** | ✅ Yes | ❌ No |
| **Subtitles** | ✅ Yes | ⚠️ Limited |

---

## Setup Plex Media Server

### Step 1: Install Plex Media Server

#### Windows
1. Download from [https://plex.tv/downloads](https://plex.tv/downloads)
2. Run the installer
3. Follow the setup wizard

#### macOS
1. Download from [https://plex.tv/downloads](https://plex.tv/downloads)
2. Open the DMG file
3. Drag Plex Media Server to Applications
4. Open from Applications folder

#### Linux (Ubuntu/Debian)
```bash
# Download the .deb package
wget https://downloads.plex.tv/plex-media-server-new/1.28.0.6114-123456789/debian/plexmediaserver_1.28.0.6114-123456789_amd64.deb

# Install
sudo dpkg -i plexmediaserver_*.deb

# Or use our script
bash <(curl -s https://raw.githubusercontent.com/AfzalAshraf/Mwatcher/main/scripts/install_plex.sh)
```

#### Linux (Fedora)
```bash
# Download the .rpm package
wget https://downloads.plex.tv/plex-media-server-new/1.28.0.6114-123456789/fedora/plexmediaserver-1.28.0.6114-123456789.x86_64.rpm

# Install
sudo rpm -i plexmediaserver-*.rpm
```

#### Docker
```bash
# Run Plex in Docker
docker run -d \
  --name=plex \
  --net=host \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -e TZ=Your/Timezone \
  -v /path/to/plex/config:/config \
  -v /path/to/media:/data \
  -v /path/to/transcode:/transcode \
  plexinc/pms-docker
```

#### NAS Devices
- **Synology**: Install from Package Center
- **QNAP**: Install from QTS App Center
- **TrueNAS**: Install from Community Plugins
- **Unraid**: Install from Community Applications

### Step 2: Initial Setup

1. Open Plex Web App: [http://localhost:32400/web](http://localhost:32400/web)
2. Sign in with your Plex account (or create one)
3. Name your server
4. Add libraries (Movies, TV Shows, Music, etc.)

### Step 3: Add Media

1. Click **Add Library**
2. Select library type (Movies, TV Shows, etc.)
3. Add folders containing your media
4. Set library name and language
5. Click **Add Library**

### Step 4: Configure Settings

Go to **Settings** → **Server** and configure:

#### General
- **Server name**: Customize your server name
- **Friendly name**: Display name for clients

#### Transcoder
- **Transcoder quality**: Set to "Prefer higher speed encoding" or "Prefer higher quality encoding"
- **Transcoder temporary directory**: Set a fast disk for transcoding
- **Background transcoding x264 preset**: Set quality preset

#### Network
- **Secure connections**: Enable for remote access
- **Remote access**: Enable if you want to access your server outside your home network
- **Bandwidth limits**: Set limits based on your network speed

#### Audio
- **Audio boost**: Enable to normalize audio levels
- **Audio quality**: Set to "Maximum" for best quality

---

## Configure Plex in Mwatcher

### Method 1: Interactive Configuration

```bash
# Run configuration
mwatcher --configure

# Select "Add Plex server"
# Enter server details when prompted
```

### Method 2: Discover Plex Servers

```bash
# Automatically discover Plex servers on your network
mwatcher --configure
# Select "Discover Plex servers"
# Select the server you want to add
```

### Method 3: Manual Configuration

Edit `~/.mwatcher/config.json`:

```json
{
  "preferred_sources": ["plex", "torrent", "youtube"],
  "preferred_player": "vlc",
  "quality": "1080p",
  "audio_quality": "raw",
  "plex_servers": [
    {
      "server": "192.168.1.100",
      "port": 32400,
      "token": "your_plex_token_here",
      "username": "your_username",
      "password": "your_password"
    }
  ]
}
```

### Method 4: Command Line

```bash
# Add a Plex server
mwatcher --configure
# Then select option 7: Add Plex server

# Or use environment variables
export PLEX_SERVER="192.168.1.100:32400"
export PLEX_TOKEN="your_token"
mwatcher --source plex "Movie Name"
```

### Finding Your Plex Token

1. **From Plex Web App**:
   - Open [http://localhost:32400/web](http://localhost:32400/web)
   - Open browser developer tools (F12)
   - Go to Network tab
   - Refresh the page
   - Look for a request to `/identity`
   - Check the `X-Plex-Token` header

2. **From Plex Preferences.xml**:
   - Windows: `%LOCALAPPDATA%\Plex Media Server\Preferences.xml`
   - macOS: `~/Library/Application Support/Plex Media Server/Preferences.xml`
   - Linux: `~/.plexms/Preferences.xml`
   - Look for `PlexOnlineToken="..."`

3. **From Plex Server Logs**:
   - Check the logs for authentication tokens

---

## Audio Passthrough (5.1, 7.1)

### What is Audio Passthrough?

**Audio passthrough** is the ability to send raw, uncompressed audio directly to your receiver or TV without decoding and re-encoding. This preserves:
- **Original audio quality** (lossless formats like TrueHD, DTS-HD)
- **Surround sound** (5.1, 7.1 channel audio)
- **Dynamic range** (full audio spectrum)

### Supported Audio Formats

| Format | Channels | Bitrate | Codec | Raw Passthrough |
|--------|----------|---------|-------|-----------------|
| **AAC** | 2.0, 5.1 | 128-320 kbps | AAC | ❌ No |
| **AC3 (Dolby Digital)** | 2.0, 5.1 | 384-640 kbps | AC3 | ✅ Yes |
| **E-AC3 (Dolby Digital Plus)** | 2.0, 5.1, 7.1 | 640-1536 kbps | EAC3 | ✅ Yes |
| **DTS** | 2.0, 5.1 | 768-1536 kbps | DTS | ✅ Yes |
| **DTS-HD HR** | 2.0, 5.1, 7.1 | 1536-3072 kbps | DTS-HD | ✅ Yes |
| **DTS-HD MA** | 2.0, 5.1, 7.1 | 3072-6144 kbps | DTS-HD | ✅ Yes |
| **Dolby TrueHD** | 2.0, 5.1, 7.1 | 640-18000 kbps | TrueHD | ✅ Yes |
| **FLAC** | 2.0 | Variable | FLAC | ✅ Yes |
| **PCM** | 2.0, 5.1, 7.1 | Variable | PCM | ✅ Yes |

### Audio Quality Presets in Mwatcher

| Preset | Description | Best For |
|--------|-------------|----------|
| **raw** | Raw passthrough | Home theaters, AV receivers |
| **5.1** | 5.1 surround | Soundbars, 5.1 systems |
| **7.1** | 7.1 surround | High-end systems |
| **stereo** | 2.0 stereo | Headphones, TV speakers |
| **best** | Best available | Automatic selection |

### Configuration

#### Set Default Audio Quality

```bash
# Interactive configuration
mwatcher --configure
# Select "Change audio quality"
# Choose from: raw, 5.1, 7.1, stereo, best
```

#### Per-Playback Audio Quality

```bash
# Play with raw audio passthrough
mwatcher --audio raw "Movie Name"

# Play with 5.1 audio
mwatcher --audio 5.1 "Movie Name"

# Play with 7.1 audio
mwatcher --audio 7.1 "Movie Name"

# Cast to TV with raw audio
mwatcher --tv "192.168.1.100" --audio raw "Movie Name"
```

### Player-Specific Audio Settings

#### VLC Media Player

VLC supports audio passthrough via S/PDIF (optical or coaxial) or HDMI.

```bash
# Play with VLC and raw audio
mwatcher --player vlc --audio raw "Movie Name"
```

**VLC Audio Flags:**
- `--spdif`: Enable S/PDIF passthrough
- `--audio-channels=6`: Force 5.1 channels
- `--audio-channels=8`: Force 7.1 channels
- `--audio-device=hdmi`: Use HDMI audio device
- `--audio-filter normvol`: Normalize volume
- `--audio-sync 0`: No audio sync adjustment

#### MPV Player

MPV is a lightweight player with excellent audio passthrough support.

```bash
# Play with MPV and raw audio
mwatcher --player mpv --audio raw "Movie Name"
```

**MPV Audio Flags:**
- `--audio-device=alsa/default`: Use ALSA audio device
- `--audio-device=pulse`: Use PulseAudio
- `--audio-device=hdmi`: Use HDMI audio
- `--audio-channels=auto`: Automatic channel selection
- `--audio-channels=5.1`: Force 5.1 channels
- `--audio-channels=7.1`: Force 7.1 channels
- `--audio-format=s16le`: 16-bit little-endian format
- `--audio-exclusive`: Exclusive audio mode

#### MX Player (Android)

MX Player has built-in audio passthrough support for Android devices.

```bash
# Play with MX Player and raw audio
mwatcher --player mxplayer --audio raw "Movie Name"
```

**Note**: MX Player automatically handles audio passthrough when connected via HDMI to a compatible receiver.

### Plex Audio Settings

#### Enable Direct Play

For raw audio passthrough, you need **Direct Play** (no transcoding):

1. In Plex Web App, go to **Settings** → **Transcoder**
2. Under **Video**, set:
   - **Video Quality**: Maximum
   - **Video Resolution**: Original
   - **Video Bitrate**: Maximum
3. Under **Audio**, set:
   - **Audio Quality**: Maximum
   - **Audio Boost**: Enabled (optional)

#### Audio Profile Settings

1. Go to **Settings** → **Profiles**
2. Select your profile or create a new one
3. Under **Transcoder**, set:
   - **Video**: Direct Play
   - **Audio*: Direct Play
   - **Subtitles*: Burn in (if needed)

#### Client-Specific Settings

1. Go to **Settings** → **Devices**
2. Find your Mwatcher device (or the device you're using)
3. Click the pencil icon to edit
4. Set:
   - **Quality**: Maximum
   - **Bandwidth**: Original
   - **Direct Play*: Enabled
   - **Direct Stream*: Enabled

---

## Direct Play vs Transcoding

### Direct Play

**Direct Play** means the media is played exactly as it is, without any modification. This is ideal for:
- **Raw audio passthrough**: Preserves original audio quality
- **High-quality streaming**: No quality loss from transcoding
- **Fast startup**: No transcoding delay
- **Lower CPU usage**: No transcoding required

**Requirements for Direct Play:**
- Client device supports the video codec (H.264, H.265, VP9, etc.)
- Client device supports the audio codec (AC3, E-AC3, DTS, etc.)
- Client device supports the container format (MP4, MKV, etc.)
- Network bandwidth is sufficient for the original bitrate

### Transcoding

**Transcoding** converts the media to a compatible format. This is used when:
- Client doesn't support the video codec
- Client doesn't support the audio codec
- Network bandwidth is insufficient
- Quality needs to be reduced

**Transcoding Options:**
- **Video**: Convert to H.264 (most compatible)
- **Audio**: Convert to AAC (most compatible)
- **Quality**: Adjust bitrate based on network speed
- **Resolution**: Reduce resolution for lower bandwidth

### How Mwatcher Handles It

Mwatcher automatically:
1. **Tries Direct Play first**: Requests the direct play URL from Plex
2. **Falls back to transcoding**: If direct play fails, requests transcoded stream
3. **Respects audio preferences**: When using "raw" audio, prefers direct play with compatible audio
4. **Selects best audio stream**: Chooses the best audio stream based on your preference

```bash
# Force direct play (may fail if incompatible)
mwatcher --source plex --audio raw "Movie Name"

# Allow transcoding (more compatible)
mwatcher --source plex "Movie Name"
```

---

## Usage Examples

### Basic Plex Usage

```bash
# Search Plex servers
mwatcher --plex "Inception"

# Search with specific source
mwatcher --source plex "The Dark Knight"

# Play with default settings
mwatcher --plex "Interstellar"
```

### Audio Quality Examples

```bash
# Play with raw audio passthrough
mwatcher --source plex --audio raw "Movie Name"

# Play with 5.1 audio
mwatcher --source plex --audio 5.1 "Movie Name"

# Play with 7.1 audio
mwatcher --source plex --audio 7.1 "Movie Name"

# Play with stereo audio
mwatcher --source plex --audio stereo "Movie Name"

# Let Mwatcher choose best audio
mwatcher --source plex --audio best "Movie Name"
```

### Player-Specific Examples

```bash
# Use VLC with raw audio
mwatcher --source plex --player vlc --audio raw "Movie Name"

# Use MPV with raw audio
mwatcher --source plex --player mpv --audio raw "Movie Name"

# Use MX Player with raw audio (Android)
mwatcher --source plex --player mxplayer --audio raw "Movie Name"
```

### TV Casting Examples

```bash
# Cast Plex content to TV
mwatcher --source plex --tv "192.168.1.100" "Movie Name"

# Cast Plex to TV with raw audio
mwatcher --source plex --tv "192.168.1.100" --audio raw "Movie Name"

# Cast Plex to VIDAA OS TV
mwatcher --source plex --tv "192.168.1.100" --audio 5.1 "Movie Name"
```

### Download Examples

```bash
# Download from Plex
mwatcher --source plex --download "Movie Name"

# Download with specific quality
mwatcher --source plex --download "Movie Name"
```

### Advanced Examples

```bash
# Search Plex and play first result with raw audio
mwatcher --source plex --audio raw "Movie Name"

# Search Plex and cast to TV
mwatcher --source plex --tv "192.168.1.100" "Movie Name"

# Batch play from Plex
for movie in "Movie1" "Movie2" "Movie3"; do
  mwatcher --source plex --audio raw "$movie"
done

# Play Plex content with specific player and audio
mwatcher --source plex --player vlc --audio 7.1 "Movie Name"
```

---

## Advanced Configuration

### Custom Plex Libraries

You can configure Mwatcher to search specific Plex libraries:

```json
{
  "plex_libraries": {
    "movies": {
      "server": "192.168.1.100",
      "library_id": 1,
      "library_name": "Movies"
    },
    "tv": {
      "server": "192.168.1.100",
      "library_id": 2,
      "library_name": "TV Shows"
    }
  }
}
```

### Multiple Plex Servers

Configure multiple Plex servers for failover or load balancing:

```json
{
  "plex_servers": [
    {
      "server": "192.168.1.100",
      "port": 32400,
      "token": "token1",
      "priority": 1
    },
    {
      "server": "192.168.1.101",
      "port": 32400,
      "token": "token2",
      "priority": 2
    }
  ]
}
```

### Plex Quality Profiles

Configure different quality profiles for different network conditions:

```json
{
  "plex_profiles": {
    "home": {
      "quality": "original",
      "bitrate": "20000",
      "audio": "raw"
    },
    "mobile": {
      "quality": "720p",
      "bitrate": "2000",
      "audio": "stereo"
    },
    "remote": {
      "quality": "1080p",
      "bitrate": "5000",
      "audio": "5.1"
    }
  }
}
```

### Custom Audio Mappings

Map specific audio codecs to your preferences:

```json
{
  "audio_codec_preferences": {
    "truehd": "raw",
    "dtshd": "raw",
    "eac3": "5.1",
    "ac3": "5.1",
    "dts": "5.1",
    "aac": "stereo"
  }
}
```

---

## Troubleshooting

### Common Issues

#### "Plex server not found"

**Solutions:**
- Check the server IP address
- Verify the server is running
- Check the port number (default: 32400)
- Verify network connectivity
- Check firewall settings

#### "Authentication failed"

**Solutions:**
- Verify the Plex token
- Check username and password
- Ensure the server allows remote connections
- Try re-authenticating

#### "No results found"

**Solutions:**
- Check the library names
- Verify media is properly organized in Plex
- Check Plex server is indexed
- Try a different search query

#### "Direct play not available"

**Solutions:**
- Check client compatibility
- Enable transcoding in Plex settings
- Try a different player
- Lower the quality settings

#### "Audio not playing"

**Solutions:**
- Check HDMI connection
- Enable HDMI audio output
- Try different audio quality (raw, 5.1, stereo)
- Check receiver settings
- Verify audio codec support

#### "Audio out of sync"

**Solutions:**
- Try a different player
- Adjust audio sync settings
- Enable audio normalization
- Check for variable frame rate (VFR) content

#### "Transcoding required"

**Solutions:**
- Enable transcoding in Plex settings
- Check client compatibility
- Lower quality settings
- Use a more compatible player

### Debug Commands

```bash
# Check Plex server connectivity
curl http://192.168.1.100:32400/identity

# Check Plex libraries
curl http://192.168.1.100:32400/library/sections -H "X-Plex-Token: YOUR_TOKEN"

# Check Plex media
curl http://192.168.1.100:32400/library/all -H "X-Plex-Token: YOUR_TOKEN" -d "type=1"

# Test direct play URL
curl "http://192.168.1.100:32400/library/metadata/12345?X-Plex-Token=YOUR_TOKEN"
```

### Log Files

- **Plex Server Logs**: Check for transcoding and playback issues
- **Mwatcher Logs**: `~/.mwatcher/logs/mwatcher.log`

---

## Best Practices

### For Audio Passthrough

1. **Use HDMI**: For raw audio passthrough, always use HDMI connection
2. **Check receiver capabilities**: Ensure your AV receiver supports the audio format
3. **Enable HDMI passthrough**: In your TV or receiver settings
4. **Use compatible player**: VLC and MPV support audio passthrough
5. **Check source audio**: Ensure your media has high-quality audio tracks
6. **Test with known content**: Use media with known audio formats for testing

### For Plex Server

1. **Use wired connection**: For best performance, connect your server via Ethernet
2. **Enable direct play**: Configure Plex to prefer direct play
3. **Set quality limits**: Configure quality limits based on client capabilities
4. **Enable transcoding**: Ensure transcoding is enabled for incompatible clients
5. **Organize libraries**: Keep your media well-organized
6. **Add metadata**: Ensure your media has proper metadata
7. **Regular updates**: Keep Plex server updated
8. **Backup configuration**: Regularly backup your Plex configuration

### For Network

1. **Use wired connections**: For best performance, use Ethernet where possible
2. **Enable QoS**: Configure Quality of Service on your router
3. **Sufficient bandwidth**: Ensure your network can handle the bitrate
4. **Check firewall**: Allow Plex traffic (port 32400)
5. **Use gigabit network**: For 4K and high-bitrate content

### For Media

1. **Use compatible formats**: MP4, MKV, AVI are widely supported
2. **Add proper metadata**: Use Plex agents to add metadata
3. **Organize by type**: Separate movies, TV shows, music
4. **Use consistent naming**: Follow Plex naming conventions
5. **Add subtitles**: Include subtitles for accessibility
6. **Test playback**: Verify media plays correctly before adding to library

---

## Plex Naming Conventions

For best results with Plex, follow these naming conventions:

### Movies

```
Movies/
├── The Matrix (1999)/
│   ├── The Matrix (1999).mkv
│   ├── The Matrix (1999).en.srt
│   └── poster.jpg
└── Inception (2010)/
    ├── Inception (2010).mkv
    └── Inception (2010).en.srt
```

### TV Shows

```
TV Shows/
└── Breaking Bad/
    ├── Season 01/
    │   ├── Breaking Bad - S01E01 - Pilot.mkv
    │   ├── Breaking Bad - S01E01 - Pilot.en.srt
    │   └── ...
    └── Season 02/
        └── ...
```

### Music

```
Music/
└── Artist/
    └── Album/
        ├── 01 - Song.mp3
        ├── 02 - Song.mp3
        └── folder.jpg
```

---

## Supported Audio Codecs by Device

### VLC Media Player

| Codec | Direct Play | Transcode | Notes |
|-------|-------------|-----------|-------|
| AAC | ✅ Yes | ❌ No | |
| AC3 | ✅ Yes | ❌ No | |
| E-AC3 | ✅ Yes | ❌ No | |
| DTS | ✅ Yes | ❌ No | |
| DTS-HD | ✅ Yes | ❌ No | |
| TrueHD | ✅ Yes | ❌ No | |
| FLAC | ✅ Yes | ❌ No | |
| PCM | ✅ Yes | ❌ No | |

### MPV Player

| Codec | Direct Play | Transcode | Notes |
|-------|-------------|-----------|-------|
| AAC | ✅ Yes | ❌ No | |
| AC3 | ✅ Yes | ❌ No | |
| E-AC3 | ✅ Yes | ❌ No | |
| DTS | ✅ Yes | ❌ No | |
| DTS-HD | ✅ Yes | ❌ No | |
| TrueHD | ✅ Yes | ❌ No | |
| FLAC | ✅ Yes | ❌ No | |
| PCM | ✅ Yes | ❌ No | |

### MX Player (Android)

| Codec | Direct Play | Transcode | Notes |
|-------|-------------|-----------|-------|
| AAC | ✅ Yes | ❌ No | |
| AC3 | ✅ Yes | ❌ No | |
| E-AC3 | ✅ Yes | ❌ No | |
| DTS | ✅ Yes | ❌ No | |
| DTS-HD | ❌ No | ✅ Yes | May require software decode |
| TrueHD | ❌ No | ✅ Yes | May require software decode |
| FLAC | ✅ Yes | ❌ No | |
| PCM | ✅ Yes | ❌ No | |

### VIDAA OS (Hisense)

| Codec | Direct Play | Transcode | Notes |
|-------|-------------|-----------|-------|
| AAC | ✅ Yes | ❌ No | |
| AC3 | ✅ Yes | ❌ No | |
| E-AC3 | ✅ Yes | ❌ No | |
| DTS | ✅ Yes | ❌ No | |
| DTS-HD | ⚠️ Partial | ✅ Yes | Depends on model |
| TrueHD | ❌ No | ✅ Yes | Requires transcoding |
| FLAC | ✅ Yes | ❌ No | |
| PCM | ✅ Yes | ❌ No | |

### Android TV

| Codec | Direct Play | Transcode | Notes |
|-------|-------------|-----------|-------|
| AAC | ✅ Yes | ❌ No | |
| AC3 | ✅ Yes | ❌ No | |
| E-AC3 | ✅ Yes | ❌ No | |
| DTS | ✅ Yes | ❌ No | |
| DTS-HD | ⚠️ Partial | ✅ Yes | Depends on device |
| TrueHD | ❌ No | ✅ Yes | Requires transcoding |
| FLAC | ✅ Yes | ❌ No | |
| PCM | ✅ Yes | ❌ No | |

---

## Plex Server Requirements

### Hardware Requirements

| Users | CPU | RAM | Storage |
|-------|-----|-----|---------|
| 1-2 | 2 cores | 2 GB | 50 GB |
| 3-5 | 4 cores | 4 GB | 100 GB |
| 5-10 | 6+ cores | 8 GB | 200 GB |
| 10+ | 8+ cores | 16 GB | 500+ GB |

### Bandwidth Requirements

| Quality | Bitrate | Bandwidth per Stream |
|---------|---------|---------------------|
| 480p | 1-2 Mbps | 2-4 Mbps |
| 720p | 2-5 Mbps | 4-10 Mbps |
| 1080p | 5-10 Mbps | 10-20 Mbps |
| 4K | 15-25 Mbps | 25-50 Mbps |
| 4K HDR | 25-50 Mbps | 50-100 Mbps |

### Transcoding Requirements

| Quality | CPU Usage | Bandwidth |
|---------|-----------|----------|
| 480p | Low | 1-2 Mbps |
| 720p | Medium | 2-5 Mbps |
| 1080p | High | 5-10 Mbps |
| 4K | Very High | 15-25 Mbps |

---

## Conclusion

Mwatcher + Plex provides the **ultimate movie experience** with:
- ✅ **Your own media library** - Access all your movies, TV shows, and music
- ✅ **Raw audio passthrough** - 5.1, 7.1, and other surround sound formats
- ✅ **High-quality streaming** - Direct play without transcoding when possible
- ✅ **Multi-device support** - Watch on any device, anywhere
- ✅ **Flexible audio options** - Choose the audio quality that works best for you
- ✅ **TV casting** - Cast to VIDAA OS, Android TV, and other DLNA devices

With Mwatcher and Plex, you can **enjoy your media library with the best possible audio quality** on any device!

---

**Enjoy your movies with amazing sound! 🎬🎧🍿**
