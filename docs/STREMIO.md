# Mwatcher + Stremio Integration Guide

Complete guide to using Mwatcher with Stremio addons for premium content access.

---

## 📋 Table of Contents

1. [What is Stremio?](#what-is-stremio)
2. [Setting Up Stremio](#setting-up-stremio)
3. [Stremio Addons Overview](#stremio-addons-overview)
4. [Configuring Mwatcher for Stremio](#configuring-mwatcher-for-stremio)
5. [Using Stremio with Mwatcher](#using-stremio-with-mwatcher)
6. [Popular Stremio Addons](#popular-stremio-addons)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

---

## What is Stremio?

**Stremio** is a modern media center that organizes your video content from different sources, including:
- **Local files**
- **Torrent streams**
- **Online streaming services** (Netflix, Disney+, HBO Max, etc.)
- **YouTube**
- **And many more through addons**

The key feature of Stremio is its **addon system**, which allows you to extend its functionality with community-created addons.

---

## Setting Up Stremio

### Installation

#### Windows/macOS/Linux
1. Download Stremio from [https://strem.io](https://strem.io)
2. Install the application
3. Create an account or sign in

#### Android
1. Download Stremio APK from [https://strem.io](https://strem.io) (not on Play Store)
2. Install the APK
3. Enable "Install from unknown sources" if prompted

#### iOS
1. Stremio is not officially available on iOS
2. Use the web version at [https://app.strem.io](https://app.strem.io)

### First Run

1. Open Stremio
2. Complete the initial setup
3. Go to **Addons** section
4. Install the addons you want

---

## Stremio Addons Overview

### What are Addons?

Addons are like plugins that provide content to Stremio. They can:
- Provide catalogs of movies and TV shows
- Stream content from various sources
- Provide metadata (posters, descriptions, ratings)
- Offer subtitles
- And much more

### Types of Addons

1. **Catalog Addons**: Provide lists of content (e.g., Popcorn Time, Netflix)
2. **Streaming Addons**: Provide streams for content (e.g., Torrentio)
3. **Metadata Addons**: Provide information about content (e.g., Cinemeta)
4. **Subtitle Addons**: Provide subtitles (e.g., OpenSubtitles)

### Addon IDs

Each addon has a unique ID in the format:
```
stremio://<addon-name>/<developer>.<addon-id>
```

Example:
```
stremio://cinemeta/com.cinemeta.addon
stremio://torrentio/com.torrentio.addon
```

---

## Configuring Mwatcher for Stremio

### Method 1: Interactive Configuration

```bash
# Run the configuration
mwatcher --configure

# Select "Preferred sources"
# Add "stremio" to the list
# Save configuration
```

### Method 2: Manual Configuration

Edit `~/.mwatcher/config.json`:

```json
{
  "preferred_sources": ["stremio", "torrent", "youtube"],
  "preferred_player": "vlc",
  "quality": "1080p",
  "subtitles": true,
  "custom_sources": {
    "stremio_custom": {
      "name": "My Stremio Setup",
      "search_url": "stremio://search/{query}",
      "stream_extractor": "stremio"
    }
  }
}
```

### Method 3: Environment Variables

```bash
# Set Stremio as preferred source
export MWATCHER_SOURCES="stremio,torrent,youtube"

# Run Mwatcher
mwatcher "Movie Name"
```

---

## Using Stremio with Mwatcher

### Basic Usage

```bash
# Search via Stremio
mwatcher --source stremio "Movie Name"

# Short form
mwatcher -s stremio "Movie Name"
```

### Direct Stremio URL

```bash
# Play via specific Stremio addon
mwatcher --stremio "stremio://cinemeta/com.cinemeta.addon"

# Search with Stremio addon
mwatcher --stremio "stremio://torrentio/com.torrentio.addon/search/Movie Name"
```

### With Specific Player

```bash
# Use VLC with Stremio
mwatcher --source stremio --player vlc "Movie Name"

# Use MPV with Stremio
mwatcher --source stremio --player mpv "Movie Name"
```

### Download via Stremio

```bash
# Download instead of streaming
mwatcher --source stremio --download "Movie Name"
```

---

## Popular Stremio Addons

### Essential Addons

| Addon | ID | Description | Type |
|-------|----|-------------|------|
| **Cinemeta** | `com.cinemeta.addon` | Movie & TV metadata, trailers, subtitles | Metadata |
| **Torrentio** | `com.torrentio.addon` | Torrent streaming (REAL-DEBRID required) | Streaming |
| **Popcorn Time** | `com.popcorntime.addon` | Popcorn Time catalog | Catalog |
| **YouTube** | `com.github.youTube.addon` | YouTube videos | Catalog/Streaming |

### Streaming Service Addons

| Addon | ID | Service | Requires Login |
|-------|----|---------|----------------|
| **Netflix** | `com.netflix.addon` | Netflix | ✅ Yes |
| **Disney+** | `com.disneyplus.addon` | Disney+ | ✅ Yes |
| **HBO Max** | `com.hbomax.addon` | HBO Max | ✅ Yes |
| **Amazon Prime** | `com.amazonprime.addon` | Amazon Prime Video | ✅ Yes |
| **Hulu** | `com.hulu.addon` | Hulu | ✅ Yes |
| **Apple TV+** | `com.appletvplus.addon` | Apple TV+ | ✅ Yes |
| **Peacock** | `com.peacock.addon` | Peacock | ✅ Yes |
| **Paramount+** | `com.paramountplus.addon` | Paramount+ | ✅ Yes |

### Torrent Addons

| Addon | ID | Description |
|-------|----|-------------|
| **Torrentio** | `com.torrentio.addon` | Best torrent addon (REAL-DEBRID required) |
| **Pirate Bay** | `com.piratebay.addon` | The Pirate Bay torrent streaming |
| **1337x** | `com.1337x.addon` | 1337x torrent streaming |
| **RARBG** | `com.rarbg.addon` | RARBG torrent streaming |

### Anime Addons

| Addon | ID | Description |
|-------|----|-------------|
| **Anime Catalog** | `com.animecatalog.addon` | Anime catalog |
| **AniList** | `com.anilist.addon` | AniList integration |
| **MyAnimeList** | `com.myanimelist.addon` | MyAnimeList integration |

### Sports Addons

| Addon | ID | Description |
|-------|----|-------------|
| **Sport Catalog** | `com.sportcatalog.addon` | Sports events |
| **Football** | `com.football.addon` | Football/soccer streams |
| **NBA** | `com.nba.addon` | NBA games |

### Adult Addons

| Addon | ID | Description |
|-------|----|-------------|
| **PornHub** | `com.pornhub.addon` | PornHub videos |
| **XVideos** | `com.xvideos.addon` | XVideos videos |

---

## Installing Stremio Addons

### Method 1: From Stremio App

1. Open Stremio
2. Go to **Addons** section
3. Click **Install Addon**
4. Search for the addon name
5. Click **Install**

### Method 2: Manual Installation

1. Find the addon ID (see tables above)
2. In Stremio, go to **Addons** → **Install from URL**
3. Enter the full addon URL: `stremio://<addon-id>`
4. Click **Install**

Example:
```
stremio://com.torrentio.addon
stremio://com.cinemeta.addon
```

### Method 3: Community Addons

1. Visit [https://stremio.github.io/stremio-addon-sdk/](https://stremio.github.io/stremio-addon-sdk/) for official addons
2. Visit [https://www.reddit.com/r/StremioAddons/](https://www.reddit.com/r/StremioAddons/) for community addons
3. Install via the URL method above

---

## Configuring Stremio Addons

### Torrentio Setup (Most Popular)

**Torrentio** is the most popular streaming addon for Stremio, but it requires a **REAL-DEBRID** account.

#### Step 1: Get REAL-DEBRID Account

1. Go to [https://real-debrid.com](https://real-debrid.com)
2. Create a free account
3. (Optional) Purchase premium for better speeds

#### Step 2: Configure Torrentio

1. In Stremio, go to **Addons**
2. Find **Torrentio** and click **Configure**
3. Enter your REAL-DEBRID API key
4. Save settings

#### Step 3: Get REAL-DEBRID API Key

1. Log in to [https://real-debrid.com](https://real-debrid.com)
2. Go to **API** section
3. Copy your API key
4. Use it in Torrentio configuration

### Other Addon Configurations

Most addons that require login will prompt you when you try to use them.

---

## Using Specific Addons with Mwatcher

### Torrentio (Recommended)

```bash
# Search via Torrentio
mwatcher --source stremio "Movie Name"

# Direct Torrentio URL
mwatcher --stremio "stremio://com.torrentio.addon"
```

**Note**: Requires REAL-DEBRID account configured in Stremio.

### Cinemeta (Metadata)

```bash
# Get metadata via Cinemeta
mwatcher --stremio "stremio://com.cinemeta.addon"
```

### Netflix

```bash
# Search Netflix content
mwatcher --stremio "stremio://com.netflix.addon"
```

**Note**: Requires Netflix login configured in Stremio.

### Disney+

```bash
# Search Disney+ content
mwatcher --stremio "stremio://com.disneyplus.addon"
```

**Note**: Requires Disney+ login configured in Stremio.

### YouTube

```bash
# Search YouTube via Stremio
mwatcher --stremio "stremio://com.github.youTube.addon"
```

---

## Advanced Usage

### Combining Multiple Addons

Stremio automatically combines results from all installed addons. Mwatcher will show results from all your Stremio addons.

```bash
# Search across all Stremio addons
mwatcher --source stremio "Movie Name"
```

### Custom Stremio Addon URLs

You can create custom Stremio sources in Mwatcher configuration:

```json
{
  "custom_sources": {
    "my_stremio": {
      "name": "My Stremio Setup",
      "search_url": "stremio://com.torrentio.addon/search/{query}",
      "stream_extractor": "stremio"
    },
    "netflix_only": {
      "name": "Netflix Only",
      "search_url": "stremio://com.netflix.addon/search/{query}",
      "stream_extractor": "stremio"
    }
  }
}
```

### Using with REAL-DEBRID Directly

If you have a REAL-DEBRID account, you can use it directly:

```bash
# Configure REAL-DEBRID in Mwatcher
mwatcher --configure
# Add REAL-DEBRID API key (future feature)
```

### Stremio Web Version

If you're using Stremio web version ([https://app.strem.io](https://app.strem.io)):

1. Install addons in the web version
2. Use Mwatcher with Stremio URLs
3. The web version syncs with your account

---

## Troubleshooting

### Common Issues

#### "No results from Stremio"

**Solutions**:
- Make sure Stremio is installed on your device
- Check that you have addons installed in Stremio
- Try opening Stremio first to ensure it's working
- Make sure you're logged in to Stremio

#### "Stremio addon not found"

**Solutions**:
- Check the addon ID is correct
- Make sure the addon is installed in Stremio
- Try reinstalling the addon

#### "REAL-DEBRID required"

**Solutions**:
- Create a REAL-DEBRID account at [https://real-debrid.com](https://real-debrid.com)
- Configure Torrentio addon with your API key
- Consider purchasing premium for better speeds

#### "Login required"

**Solutions**:
- Open Stremio and log in to the required service
- Configure the addon with your credentials
- Make sure your subscription is active

#### "Stremio not installed"

**Solutions**:
- Install Stremio from [https://strem.io](https://strem.io)
- On Android, you may need to install the APK manually
- On iOS, use the web version

### Debugging

```bash
# Check Stremio connectivity
mwatcher --source stremio --search "test"

# Check addon installation in Stremio
# Open Stremio and verify addons are installed

# Check Stremio logs
# On desktop: Check Stremio application logs
# On Android: Check Termux logs if using Termux
```

---

## Best Practices

### 1. Install Essential Addons

At minimum, install these addons:
- **Cinemeta** - For metadata
- **Torrentio** - For torrent streaming
- **Popcorn Time** - For catalog

### 2. Use REAL-DEBRID with Torrentio

For the best torrent streaming experience:
- Create a REAL-DEBRID account
- Configure it in Torrentio
- Consider premium for faster speeds

### 3. Keep Addons Updated

Regularly update your Stremio addons for the best experience.

### 4. Use Multiple Addons

Install multiple addons for different content types:
- Movies: Torrentio, Popcorn Time
- TV Shows: Torrentio, Netflix
- Anime: Anime Catalog
- Sports: Sport Catalog

### 5. Configure Quality

In Mwatcher configuration:
```bash
mwatcher --configure
# Set quality to match your REAL-DEBRID settings
```

---

## Stremio Addon URLs Reference

### Official Addons

```
stremio://cinemeta/com.cinemeta.addon
stremio://torrentio/com.torrentio.addon
stremio://popcorn-time/com.popcorntime.addon
stremio://youtube/com.github.youTube.addon
```

### Streaming Services

```
stremio://netflix/com.netflix.addon
stremio://disneyplus/com.disneyplus.addon
stremio://hbomax/com.hbomax.addon
stremio://amazonprime/com.amazonprime.addon
stremio://hulu/com.hulu.addon
stremio://appletvplus/com.appletvplus.addon
stremio://peacock/com.peacock.addon
stremio://paramountplus/com.paramountplus.addon
```

### Torrent Addons

```
stremio://piratebay/com.piratebay.addon
stremio://1337x/com.1337x.addon
stremio://rarbg/com.rarbg.addon
```

### Anime Addons

```
stremio://animecatalog/com.animecatalog.addon
stremio://anilist/com.anilist.addon
stremio://myanimelist/com.myanimelist.addon
```

---

## Conclusion

By combining Mwatcher with Stremio addons, you can access a vast library of content from various sources, all with a single command. Whether you want to watch movies from Netflix, Disney+, torrent sites, or YouTube, Mwatcher + Stremio makes it easy.

**Happy Streaming! 🎬🍿**
