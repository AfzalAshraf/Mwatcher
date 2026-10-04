#!/usr/bin/env python3
"""
Mwatcher Enhanced - Universal Movie Watcher with Plex & TV Support
Watch movies from any device with just one command
Supports: Termux, Terminal, VLC, MPV, Stremio addons, Plex, DLNA/UPnP, VIDAA OS

Usage:
    python mwatcher_enhanced.py "Movie Name"
    python mwatcher_enhanced.py --search "query"
    python mwatcher_enhanced.py --plex "Movie Name"
    python mwatcher_enhanced.py --tv "192.168.1.100" "Movie Name"
    python mwatcher_enhanced.py --url "http://..."
"""

import argparse
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import enhanced modules
try:
    from mwatcher_plex import PlexManager, PlexServer, PlexAudioHandler, AUDIO_PRESETS
    from mwatcher_plex import EnhancedPlayerManager, TVPlatformHandler, DLNACaster
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False

# Configuration
CONFIG_DIR = Path.home() / ".mwatcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = CONFIG_DIR / "cache"

# Default sources (can be extended via config)
DEFAULT_SOURCES = {
    "youtube": {
        "name": "YouTube",
        "search_url": "https://www.youtube.com/results?search_query={query}",
        "stream_extractor": "yt-dlp",
        "quality": "best",
    },
    "torrent": {
        "name": "Torrent Stream",
        "search_url": "https://yts.mx/api/v2/list_movies.json?query_term={query}",
        "stream_extractor": "webtorrent",
        "quality": "1080p",
    },
    "stremio": {
        "name": "Stremio",
        "addon_url": "stremio://addon",
        "stream_extractor": "stremio",
    },
    "primewire": {
        "name": "PrimeWire (Movies2Watch)",
        "search_url": "https://www.primewire.li/search/{query}/1",
        "stream_extractor": "html",
    },
    "fmovies": {
        "name": "FMovies",
        "search_url": "https://fmovies.to/search/{query}",
        "stream_extractor": "html",
    },
    "putlocker": {
        "name": "Putlocker",
        "search_url": "https://putlocker.is/search/{query}",
        "stream_extractor": "html",
    },
    "solarmovie": {
        "name": "SolarMovie",
        "search_url": "https://solarmovie.to/search/{query}",
        "stream_extractor": "html",
    },
}

# Supported players
PLAYERS = {
    "vlc": {
        "name": "VLC Media Player",
        "command": "vlc",
        "args": "{url}",
        "platforms": ["linux", "windows", "darwin"],
        "audio_passthrough": True,
    },
    "mpv": {
        "name": "MPV Player",
        "command": "mpv",
        "args": "{url}",
        "platforms": ["linux", "darwin"],
        "audio_passthrough": True,
    },
    "termux": {
        "name": "Termux MPV",
        "command": "mpv",
        "args": "{url} --no-input-default-bindings",
        "platforms": ["android"],
        "audio_passthrough": True,
    },
    "mxplayer": {
        "name": "MX Player",
        "command": "am start -a android.intent.action.VIEW -d {url} -n com.mxtech.videoplayer.ad/.ActivityScreen",
        "args": "",
        "platforms": ["android"],
        "audio_passthrough": True,
    },
    "default": {
        "name": "Default Browser",
        "command": "xdg-open" if platform.system().lower() != "darwin" else "open",
        "args": "{url}",
        "platforms": ["linux", "darwin", "windows"],
        "audio_passthrough": False,
    },
}


class ConfigManager:
    """Manage configuration and settings"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Default configuration
        return {
            "preferred_sources": ["stremio", "torrent", "youtube", "plex"],
            "preferred_player": self._detect_default_player(),
            "quality": "1080p",
            "audio_quality": "raw",  # raw, 5.1, 7.1, stereo, best
            "subtitles": True,
            "cache_enabled": True,
            "custom_sources": {},
            "plex_servers": [],
            "tv_devices": [],
        }
    
    def _detect_default_player(self) -> str:
        """Detect the best available player"""
        system = platform.system().lower()
        
        # Check for Termux
        if os.environ.get('PREFIX', '').startswith('/data/data/com.termux'):
            return "termux"
        
        # Check for Android
        if system == "linux" and os.path.exists("/system/bin/sh"):
            return "mxplayer"
        
        # Check for VLC
        if self._command_exists("vlc"):
            return "vlc"
        
        # Check for MPV
        if self._command_exists("mpv"):
            return "mpv"
        
        return "default"
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(
                ["which", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def save(self):
        """Save configuration to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_sources(self) -> Dict:
        """Get all available sources"""
        sources = DEFAULT_SOURCES.copy()
        sources.update(self.config.get("custom_sources", {}))
        
        # Add Plex as a source if configured
        if PLEX_AVAILABLE and self.config.get("plex_servers"):
            sources["plex"] = {
                "name": "Plex",
                "search_url": "plex://search/{query}",
                "stream_extractor": "plex",
            }
        
        return sources
    
    def get_player(self, player_name: Optional[str] = None) -> Dict:
        """Get player configuration"""
        player_name = player_name or self.config.get("preferred_player", "default")
        return PLAYERS.get(player_name, PLAYERS["default"])
    
    def get_audio_quality(self) -> str:
        """Get audio quality setting"""
        return self.config.get("audio_quality", "raw")
    
    def set_audio_quality(self, quality: str):
        """Set audio quality"""
        if quality in AUDIO_PRESETS:
            self.config["audio_quality"] = quality
            self.save()
            return True
        return False


class MovieSearcher:
    """Search for movies across multiple sources"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sources = config.get_sources()
        self.plex_manager = None
        
        if PLEX_AVAILABLE and self.config.config.get("plex_servers"):
            self.plex_manager = PlexManager()
    
    def search(self, query: str, source: Optional[str] = None) -> List[Dict]:
        """Search for movies"""
        results = []
        
        sources_to_search = [source] if source else self.config.config.get("preferred_sources", [])
        
        for src_name in sources_to_search:
            if src_name not in self.sources:
                continue
            
            src = self.sources[src_name]
            try:
                if src_name == "youtube":
                    results.extend(self._search_youtube(query))
                elif src_name == "torrent":
                    results.extend(self._search_torrent(query))
                elif src_name == "stremio":
                    results.extend(self._search_stremio(query))
                elif src_name == "plex" and PLEX_AVAILABLE and self.plex_manager:
                    results.extend(self._search_plex(query))
                else:
                    # Generic HTML-based search
                    results.extend(self._search_generic(query, src))
            except Exception as e:
                print(f"Error searching {src.get('name', src_name)}: {e}")
        
        return results
    
    def _search_plex(self, query: str) -> List[Dict]:
        """Search Plex servers"""
        if not self.plex_manager:
            return []
        
        results = self.plex_manager.search_all(query, limit=10)
        
        # Add audio information
        for result in results:
            if result.get("plex_id"):
                # Get audio streams
                audio_handler = PlexAudioHandler(self.plex_manager)
                audio_streams = audio_handler.get_audio_streams(result)
                result["audio_streams"] = audio_streams
                
                # Get best raw audio
                raw_audio = audio_handler.get_raw_audio_stream(result)
                if raw_audio:
                    result["has_raw_audio"] = True
                    result["raw_audio_channels"] = raw_audio.get("channels")
        
        return results
    
    def _search_youtube(self, query: str) -> List[Dict]:
        """Search YouTube for movies"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = DEFAULT_SOURCES["youtube"]["search_url"].format(query=urllib.parse.quote(query + " movie"))
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for item in soup.select('ytd-video-renderer')[:5]:
                title = item.select_one('#video-title').text.strip()
                video_url = "https://www.youtube.com" + item.select_one('#video-title')['href']
                duration = item.select_one('.ytd-thumbnail-overlay-time-status-renderer').text.strip()
                
                results.append({
                    "title": title,
                    "url": video_url,
                    "source": "youtube",
                    "duration": duration,
                    "type": "video",
                })
            
            return results
        except Exception as e:
            print(f"YouTube search failed: {e}")
            return []
    
    def _search_torrent(self, query: str) -> List[Dict]:
        """Search for torrent streams"""
        try:
            import requests
            
            url = DEFAULT_SOURCES["torrent"]["search_url"].format(query=urllib.parse.quote(query))
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            results = []
            for movie in data.get("data", {}).get("movies", [])[:5]:
                title = movie.get("title", "")
                year = movie.get("year", 0)
                rating = movie.get("rating", 0)
                
                # Get torrent URLs
                torrents = movie.get("torrents", [])
                for torrent in torrents:
                    if torrent.get("quality") == self.config.config.get("quality", "1080p"):
                        magnet = torrent.get("url", "")
                        if magnet:
                            results.append({
                                "title": f"{title} ({year})",
                                "url": magnet,
                                "source": "torrent",
                                "quality": torrent.get("quality", ""),
                                "seeds": torrent.get("seeds", 0),
                                "peers": torrent.get("peers", 0),
                                "rating": rating,
                                "type": "torrent",
                            })
                            break
            
            return results
        except Exception as e:
            print(f"Torrent search failed: {e}")
            return []
    
    def _search_stremio(self, query: str) -> List[Dict]:
        """Search Stremio addons"""
        stremio_addons = {
            "cinemeta": "stremio://cinemeta/com.cinemeta.addon",
            "torrentio": "stremio://torrentio/com.torrentio.addon",
            "popcorn": "stremio://popcorn-time/com.popcorntime.addon",
            "youtube": "stremio://youtube/com.github.youTube.addon",
        }
        
        results = []
        for addon_id, addon_url in stremio_addons.items():
            results.append({
                "title": f"Search on {addon_id}",
                "url": f"{addon_url}/search/{urllib.parse.quote(query)}",
                "source": "stremio",
                "addon": addon_id,
                "type": "stremio",
            })
        
        return results
    
    def _search_generic(self, query: str, source: Dict) -> List[Dict]:
        """Generic search for HTML-based sources"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = source["search_url"].format(query=urllib.parse.quote(query))
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for link in soup.find_all('a', href=True)[:10]:
                href = link['href']
                title = link.text.strip()
                
                if query.lower() in title.lower() and any(
                    ext in href.lower() for ext in ['.mp4', '.mkv', '.avi', '.mov']
                ):
                    results.append({
                        "title": title,
                        "url": href if href.startswith('http') else url + href,
                        "source": source["name"],
                        "type": "video",
                    })
            
            return results
        except Exception as e:
            print(f"Search failed for {source.get('name', 'unknown')}: {e}")
            return []


class StreamExtractor:
    """Extract and handle streams from various sources"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def extract(self, url: str, source: str, item_data: Optional[Dict] = None) -> Optional[str]:
        """Extract playable stream URL"""
        try:
            if source == "youtube":
                return self._extract_youtube(url)
            elif source == "torrent":
                return self._extract_torrent(url)
            elif source == "stremio":
                return self._extract_stremio(url)
            elif source == "plex" and PLEX_AVAILABLE:
                return self._extract_plex(url, item_data)
            else:
                return self._extract_generic(url)
        except Exception as e:
            print(f"Error extracting stream from {source}: {e}")
            return None
    
    def _extract_youtube(self, url: str) -> str:
        """Extract YouTube stream"""
        return url  # yt-dlp will handle it
    
    def _extract_torrent(self, url: str) -> str:
        """Extract torrent stream"""
        if url.startswith("magnet:"):
            return url
        return url
    
    def _extract_stremio(self, url: str) -> str:
        """Extract Stremio stream"""
        return url
    
    def _extract_plex(self, url: str, item_data: Optional[Dict] = None) -> Optional[str]:
        """Extract Plex stream with audio passthrough"""
        if not PLEX_AVAILABLE or not item_data:
            return url
        
        # Get audio quality preference
        config = ConfigManager()
        audio_quality = config.get_audio_quality()
        
        # If raw audio is preferred, try to get direct play URL with best audio
        if audio_quality == "raw" or audio_quality == "best":
            plex_manager = PlexManager()
            audio_handler = PlexAudioHandler(plex_manager)
            
            # Get the best raw audio stream
            raw_audio = audio_handler.get_raw_audio_stream(item_data)
            if raw_audio:
                # Find the Plex server for this item
                for server in plex_manager.get_servers():
                    if server.friendly_name == item_data.get("plex_server"):
                        return server.get_direct_play_url(item_data, raw_audio.get("index"))
        
        # Return direct play URL
        if item_data and item_data.get("direct_url"):
            return item_data.get("direct_url")
        
        return url
    
    def _extract_generic(self, url: str) -> Optional[str]:
        """Generic stream extraction"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for video elements
            video = soup.find('video')
            if video and video.get('src'):
                return video['src']
            
            # Look for iframe
            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                return iframe['src']
            
            # Look for direct video links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(ext in href.lower() for ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']):
                    return href if href.startswith('http') else url + href
            
            return None
        except Exception as e:
            print(f"Generic extraction failed: {e}")
            return None


class PlayerManager:
    """Manage video players and playback with audio passthrough"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.tv_handler = TVPlatformHandler() if PLEX_AVAILABLE else None
    
    def play(self, url: str, player_name: Optional[str] = None, subtitles: Optional[str] = None,
             tv_ip: Optional[str] = None, audio_quality: Optional[str] = None):
        """Play a stream with the selected player or TV"""
        
        # Check if we should cast to TV
        if tv_ip:
            return self._cast_to_tv(tv_ip, url)
        
        # Get audio quality from config if not specified
        if audio_quality is None:
            audio_quality = self.config.get_audio_quality()
        
        player = self.config.get_player(player_name)
        command = player["command"]
        args = player["args"].format(url=url)
        
        # Add audio passthrough flags if supported
        if player.get("audio_passthrough") and audio_quality != "stereo":
            audio_flags = self._get_audio_flags(audio_quality, player.get("name", ""))
            args += f" {audio_flags}"
        
        # Add subtitles if specified
        if subtitles:
            args += f" --sub-file={subtitles}"
        
        full_command = f"{command} {args}"
        
        print(f"Playing: {url}")
        if tv_ip:
            print(f"Casting to: {tv_ip}")
        else:
            print(f"Using: {player['name']}")
        print(f"Audio Quality: {audio_quality}")
        if audio_flags:
            print(f"Audio Flags: {audio_flags}")
        print(f"Command: {full_command}")
        
        try:
            import shlex
            parsed_command = shlex.split(full_command)
            subprocess.run(parsed_command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error playing with {player['name']}: {e}")
            # Try with default player
            if player_name != "default":
                return self.play(url, "default", subtitles, tv_ip, audio_quality)
            return False
        except FileNotFoundError:
            print(f"Player not found: {player['name']}")
            print("Trying alternative players...")
            # Try other players
            for pname, pconfig in PLAYERS.items():
                if pname != player_name:
                    try:
                        return self.play(url, pname, subtitles, tv_ip, audio_quality)
                    except:
                        continue
            print("No suitable player found. Please install VLC, MPV, or another supported player.")
            return False
    
    def _cast_to_tv(self, tv_ip: str, url: str) -> bool:
        """Cast to TV"""
        if not self.tv_handler:
            print("TV casting not available (Plex module not loaded)")
            return False
        
        # Detect platform
        platform = self.tv_handler.detect_platform(tv_ip)
        
        print(f"Casting to {tv_ip} ({platform or 'DLNA'})")
        
        # Cast to TV
        return self.tv_handler.cast_to_tv(tv_ip, url, "Movie", platform)
    
    def _get_audio_flags(self, audio_quality: str, player_name: str) -> str:
        """Get audio passthrough flags for player"""
        
        if audio_quality == "raw" or audio_quality == "best":
            if player_name == "VLC Media Player":
                return "--spdif --audio-filter normvol --audio-sync 0"
            elif player_name == "MPV Player":
                return "--audio-device=alsa/default --audio-channels=auto --audio-format=s16le"
            elif player_name == "Termux MPV":
                return "--audio-channels=auto"
            elif player_name == "MX Player":
                return ""  # MX Player handles passthrough automatically
        
        elif audio_quality == "5.1":
            if player_name == "VLC Media Player":
                return "--audio-channels=6 --spdif"
            elif player_name == "MPV Player":
                return "--audio-channels=5.1 --audio-device=alsa/default"
            elif player_name == "Termux MPV":
                return "--audio-channels=5.1"
        
        elif audio_quality == "7.1":
            if player_name == "VLC Media Player":
                return "--audio-channels=8 --spdif"
            elif player_name == "MPV Player":
                return "--audio-channels=7.1 --audio-device=alsa/default"
            elif player_name == "Termux MPV":
                return "--audio-channels=7.1"
        
        elif audio_quality == "stereo":
            if player_name == "VLC Media Player":
                return "--audio-channels=2"
            elif player_name == "MPV Player":
                return "--audio-channels=2.0"
        
        return ""
    
    def download(self, url: str, output_path: Optional[str] = None):
        """Download a stream"""
        import requests
        
        output_path = output_path or f"{Path.home()}/Downloads/{Path(url).name}"
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                        print(f"\rDownloading: {downloaded / (1024*1024):.2f} MB ({progress:.1f}%)", end="")
            
            print(f"\nDownloaded to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Download failed: {e}")
            return None
    
    def list_tvs(self) -> List[Dict]:
        """List all TVs on the network"""
        if self.tv_handler:
            return self.tv_handler.get_all_tvs()
        return []
    
    def list_vidaa_tvs(self) -> List[Dict]:
        """List all VIDAA OS TVs on the network"""
        if self.tv_handler:
            return self.tv_handler.get_vidaa_tvs()
        return []


class PlexManagerWrapper:
    """Wrapper for Plex functionality"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.plex_manager = None
        
        if PLEX_AVAILABLE:
            from mwatcher_plex import PlexManager, PlexAudioHandler
            self.plex_manager = PlexManager()
            self.audio_handler = PlexAudioHandler(self.plex_manager)
    
    def add_server(self, server: str, port: int = 32400, token: Optional[str] = None,
                   username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Add a Plex server"""
        if not self.plex_manager:
            return False
        
        plex_server = self.plex_manager.add_server(server, port, token, username, password)
        if plex_server:
            # Update config
            server_data = {
                "server": server,
                "port": port,
                "token": token,
                "username": username,
                "password": password,
            }
            
            if "plex_servers" not in self.config.config:
                self.config.config["plex_servers"] = []
            
            self.config.config["plex_servers"].append(server_data)
            self.config.save()
            return True
        
        return False
    
    def discover_servers(self) -> List[Dict]:
        """Discover Plex servers on network"""
        if self.plex_manager:
            return self.plex_manager.discover_servers()
        return []
    
    def get_servers(self) -> List[Dict]:
        """Get configured Plex servers"""
        return self.config.config.get("plex_servers", [])
    
    def search_plex(self, query: str) -> List[Dict]:
        """Search Plex servers"""
        if self.plex_manager:
            return self.plex_manager.search_all(query)
        return []


class Mwatcher:
    """Main Mwatcher class with enhanced features"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.searcher = MovieSearcher(self.config)
        self.extractor = StreamExtractor(self.config)
        self.player = PlayerManager(self.config)
        self.plex_wrapper = PlexManagerWrapper(self.config)
    
    def search_movies(self, query: str, source: Optional[str] = None) -> List[Dict]:
        """Search for movies"""
        return self.searcher.search(query, source)
    
    def play_movie(self, query: str, source: Optional[str] = None, player: Optional[str] = None,
                   tv_ip: Optional[str] = None, audio_quality: Optional[str] = None):
        """Search and play a movie"""
        results = self.search_movies(query, source)
        
        if not results:
            print("No results found.")
            return
        
        # If only one result, play it
        if len(results) == 1:
            self._play_result(results[0], player, tv_ip, audio_quality)
            return
        
        # Show menu for multiple results
        print("\nSelect a movie to play:")
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Untitled')
            source_name = result.get('source', 'unknown')
            
            # Show audio info for Plex items
            if result.get('has_raw_audio'):
                channels = result.get('raw_audio_channels', 0)
                audio_info = f" [🎧 {channels}ch Raw]"
            else:
                audio_info = ""
            
            print(f"{i}. {title} [{source_name}]{audio_info}")
            if result.get('rating'):
                print(f"   Rating: {result['rating']}/10")
            if result.get('duration'):
                print(f"   Duration: {result['duration']}")
            if result.get('quality'):
                print(f"   Quality: {result['quality']}")
        
        try:
            choice = int(input("\nEnter number (0 to cancel): "))
            if 0 < choice <= len(results):
                self._play_result(results[choice - 1], player, tv_ip, audio_quality)
            else:
                print("Invalid selection.")
        except (ValueError, EOFError):
            print("Invalid input.")
    
    def _play_result(self, result: Dict, player: Optional[str] = None, 
                     tv_ip: Optional[str] = None, audio_quality: Optional[str] = None):
        """Play a specific result"""
        url = result.get('url', '')
        source = result.get('source', 'unknown')
        
        # Extract stream if needed
        if source != "stremio" and not url.startswith(('http://', 'https://', 'magnet:')):
            stream_url = self.extractor.extract(url, source, result)
            if stream_url:
                url = stream_url
        
        # Play the stream
        self.player.play(url, player, None, tv_ip, audio_quality)
    
    def play_url(self, url: str, player: Optional[str] = None, 
                 tv_ip: Optional[str] = None, audio_quality: Optional[str] = None):
        """Play a direct URL"""
        self.player.play(url, player, None, tv_ip, audio_quality)
    
    def download_movie(self, query: str, source: Optional[str] = None):
        """Search and download a movie"""
        results = self.search_movies(query, source)
        
        if not results:
            print("No results found.")
            return
        
        if len(results) == 1:
            self._download_result(results[0])
            return
        
        print("\nSelect a movie to download:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'Untitled')} [{result.get('source', 'unknown')}]")
        
        try:
            choice = int(input("\nEnter number (0 to cancel): "))
            if 0 < choice <= len(results):
                self._download_result(results[choice - 1])
            else:
                print("Invalid selection.")
        except (ValueError, EOFError):
            print("Invalid input.")
    
    def _download_result(self, result: Dict):
        """Download a specific result"""
        url = result.get('url', '')
        source = result.get('source', 'unknown')
        
        stream_url = self.extractor.extract(url, source, result)
        if stream_url:
            output_name = f"{result.get('title', 'movie')}.mp4"
            self.player.download(stream_url, Path.home() / "Downloads" / output_name)
    
    def list_sources(self):
        """List all available sources"""
        sources = self.config.get_sources()
        print("\nAvailable Sources:")
        for name, info in sources.items():
            print(f"  - {name}: {info.get('name', name)}")
    
    def list_players(self):
        """List all available players"""
        print("\nAvailable Players:")
        for name, info in PLAYERS.items():
            available = " (installed)" if self._is_player_available(name) else ""
            audio_support = " [🎧 Passthrough]" if info.get("audio_passthrough") else ""
            print(f"  - {name}: {info['name']}{available}{audio_support}")
    
    def list_tvs(self):
        """List all TVs on the network"""
        tvs = self.player.list_tvs()
        print(f"\nFound {len(tvs)} TV(s) on the network:")
        for i, tv in enumerate(tvs, 1):
            tv_type = tv.get('type', 'DLNA')
            if tv_type == 'vidaa':
                tv_type = "VIDAA OS"
            print(f"  {i}. {tv.get('friendly_name', 'Unknown TV')} ({tv.get('ip')}) - {tv_type}")
    
    def list_vidaa_tvs(self):
        """List all VIDAA OS TVs"""
        tvs = self.player.list_vidaa_tvs()
        print(f"\nFound {len(tvs)} VIDAA OS TV(s):")
        for i, tv in enumerate(tvs, 1):
            print(f"  {i}. {tv.get('friendly_name', 'Unknown VIDAA TV')} ({tv.get('ip')})")
    
    def list_audio_presets(self):
        """List available audio presets"""
        print("\nAvailable Audio Presets:")
        for preset_name, preset in AUDIO_PRESETS.items():
            current = " [CURRENT]" if preset_name == self.config.get_audio_quality() else ""
            print(f"  - {preset_name}: {preset['description']}{current}")
    
    def _is_player_available(self, player_name: str) -> bool:
        """Check if a player is available"""
        player = PLAYERS.get(player_name, {})
        command = player.get("command", "")
        
        if not command:
            return False
        
        try:
            subprocess.run(
                ["which", command.split()[0]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except:
            return False
    
    def configure(self):
        """Configure Mwatcher"""
        print("\nMwatcher Enhanced Configuration")
        print("=" * 40)
        
        # Show current config
        print("\nCurrent Configuration:")
        print(f"  Preferred sources: {', '.join(self.config.config.get('preferred_sources', []))}")
        print(f"  Preferred player: {self.config.config.get('preferred_player', 'default')}")
        print(f"  Quality: {self.config.config.get('quality', '1080p')}")
        print(f"  Audio Quality: {self.config.get_audio_quality()}")
        print(f"  Subtitles: {'Enabled' if self.config.config.get('subtitles') else 'Disabled'}")
        
        # Options
        print("\nOptions:")
        print("  1. Change preferred sources")
        print("  2. Change preferred player")
        print("  3. Change video quality")
        print("  4. Change audio quality (5.1, 7.1, Raw)")
        print("  5. Toggle subtitles")
        print("  6. Add custom source")
        print("  7. Add Plex server")
        print("  8. Discover Plex servers")
        print("  9. Discover TVs on network")
        print("  0. Save and exit")
        
        try:
            choice = int(input("\nEnter choice: "))
            
            if choice == 1:
                self._configure_sources()
            elif choice == 2:
                self._configure_player()
            elif choice == 3:
                self._configure_quality()
            elif choice == 4:
                self._configure_audio()
            elif choice == 5:
                self._configure_subtitles()
            elif choice == 6:
                self._configure_custom_source()
            elif choice == 7:
                self._configure_plex_server()
            elif choice == 8:
                self._discover_plex_servers()
            elif choice == 9:
                self._discover_tvs()
            elif choice == 0:
                self.config.save()
                print("Configuration saved!")
                return
            else:
                print("Invalid choice.")
        except (ValueError, EOFError):
            pass
        
        self.configure()
    
    def _configure_sources(self):
        """Configure preferred sources"""
        sources = list(self.config.get_sources().keys())
        print(f"\nAvailable sources: {', '.join(sources)}")
        print(f"Current preferred: {', '.join(self.config.config.get('preferred_sources', []))}")
        
        preferred = input("Enter preferred sources (comma-separated): ").strip()
        if preferred:
            self.config.config['preferred_sources'] = [s.strip() for s in preferred.split(',')]
    
    def _configure_player(self):
        """Configure preferred player"""
        players = list(PLAYERS.keys())
        print(f"\nAvailable players: {', '.join(players)}")
        print(f"Current preferred: {self.config.config.get('preferred_player', 'default')}")
        
        player = input("Enter preferred player: ").strip()
        if player in players:
            self.config.config['preferred_player'] = player
        else:
            print("Invalid player.")
    
    def _configure_quality(self):
        """Configure video quality"""
        print(f"\nCurrent quality: {self.config.config.get('quality', '1080p')}")
        quality = input("Enter quality (480p, 720p, 1080p, 4k, best): ").strip()
        if quality:
            self.config.config['quality'] = quality
    
    def _configure_audio(self):
        """Configure audio quality"""
        print(f"\nCurrent audio quality: {self.config.get_audio_quality()}")
        print("\nAvailable options:")
        for preset_name, preset in AUDIO_PRESETS.items():
            print(f"  - {preset_name}: {preset['description']}")
        
        audio = input("\nEnter audio quality: ").strip().lower()
        if audio in AUDIO_PRESETS:
            self.config.set_audio_quality(audio)
        else:
            print("Invalid audio quality.")
    
    def _configure_subtitles(self):
        """Configure subtitles"""
        current = self.config.config.get('subtitles', True)
        print(f"\nSubtitles are currently {'Enabled' if current else 'Disabled'}")
        choice = input("Enable subtitles? (y/n): ").strip().lower()
        self.config.config['subtitles'] = choice == 'y'
    
    def _configure_custom_source(self):
        """Add custom source"""
        print("\nAdd Custom Source")
        name = input("Source name: ").strip()
        if not name:
            return
        
        search_url = input("Search URL (use {query} for search term): ").strip()
        stream_extractor = input("Stream extractor (yt-dlp, webtorrent, html): ").strip() or "html"
        
        self.config.config.setdefault('custom_sources', {})[name] = {
            "name": name,
            "search_url": search_url,
            "stream_extractor": stream_extractor,
        }
        print(f"Custom source '{name}' added!")
    
    def _configure_plex_server(self):
        """Add Plex server"""
        print("\nAdd Plex Server")
        server = input("Server IP or hostname: ").strip()
        if not server:
            return
        
        port = input("Port [32400]: ").strip()
        port = int(port) if port else 32400
        
        token = input("Token (leave empty if none): ").strip() or None
        username = input("Username (leave empty if none): ").strip() or None
        password = input("Password (leave empty if none): ").strip() or None
        
        if self.plex_wrapper.add_server(server, port, token, username, password):
            print(f"Plex server {server}:{port} added!")
        else:
            print("Failed to add Plex server. Check connection and credentials.")
    
    def _discover_plex_servers(self):
        """Discover Plex servers on network"""
        print("\nDiscovering Plex servers on local network...")
        servers = self.plex_wrapper.discover_servers()
        
        if servers:
            print(f"\nFound {len(servers)} Plex server(s):")
            for i, server in enumerate(servers, 1):
                print(f"  {i}. {server.get('url')}")
            
            choice = input("\nEnter number to add (0 to cancel): ").strip()
            try:
                choice_idx = int(choice)
                if 0 < choice_idx <= len(servers):
                    server = servers[choice_idx - 1]
                    self.plex_wrapper.add_server(
                        server.get('server'),
                        server.get('port', 32400)
                    )
            except (ValueError, IndexError):
                pass
        else:
            print("No Plex servers found on the local network.")
    
    def _discover_tvs(self):
        """Discover TVs on network"""
        print("\nDiscovering TVs on local network...")
        self.list_tvs()


def check_dependencies():
    """Check for required dependencies"""
    required = [
        ('yt-dlp', 'pip install yt-dlp'),
        ('requests', 'pip install requests'),
        ('beautifulsoup4', 'pip install beautifulsoup4'),
    ]
    
    missing = []
    for package, install_cmd in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append((package, install_cmd))
    
    if missing:
        print("Missing dependencies:")
        for package, install_cmd in missing:
            print(f"  - {package}: {install_cmd}")
        print("\nInstall with: pip install yt-dlp requests beautifulsoup4")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mwatcher Enhanced - Universal Movie Watcher with Plex & TV Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mwatcher_enhanced.py "Inception"
  mwatcher_enhanced.py --search "The Matrix"
  mwatcher_enhanced.py --plex "Movie Name"
  mwatcher_enhanced.py --tv "192.168.1.100" "Movie Name"
  mwatcher_enhanced.py --url "http://example.com/movie.mp4"
  mwatcher_enhanced.py --audio 5.1 "Movie Name"
  mwatcher_enhanced.py --list-tvs

Environment Variables:
  MWATCHER_PLAYER: Override preferred player
  MWATCHER_SOURCES: Comma-separated list of preferred sources
  MWATCHER_AUDIO: Override audio quality (raw, 5.1, 7.1, stereo, best)
        """
    )
    
    parser.add_argument(
        'query',
        nargs='?',
        help='Movie name or URL to play'
    )
    parser.add_argument(
        '--search', '-s',
        help='Search for movies'
    )
    parser.add_argument(
        '--url', '-u',
        help='Direct URL to play'
    )
    parser.add_argument(
        '--stremio',
        help='Stremio addon URL'
    )
    parser.add_argument(
        '--plex',
        help='Search Plex servers'
    )
    parser.add_argument(
        '--tv',
        help='Cast to TV IP address'
    )
    parser.add_argument(
        '--source',
        help='Specific source to use (youtube, torrent, stremio, plex, etc.)'
    )
    parser.add_argument(
        '--player', '-p',
        help='Specific player to use (vlc, mpv, termux, etc.)'
    )
    parser.add_argument(
        '--audio',
        help='Audio quality (raw, 5.1, 7.1, stereo, best)'
    )
    parser.add_argument(
        '--download', '-d',
        action='store_true',
        help='Download instead of playing'
    )
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List all available sources'
    )
    parser.add_argument(
        '--list-players',
        action='store_true',
        help='List all available players'
    )
    parser.add_argument(
        '--list-tvs',
        action='store_true',
        help='List all TVs on network'
    )
    parser.add_argument(
        '--list-vidaa',
        action='store_true',
        help='List all VIDAA OS TVs'
    )
    parser.add_argument(
        '--list-audio',
        action='store_true',
        help='List audio presets'
    )
    parser.add_argument(
        '--configure',
        action='store_true',
        help='Configure Mwatcher settings'
    )
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Show version'
    )
    
    args = parser.parse_args()
    
    # Check for yt-dlp and other dependencies
    check_dependencies()
    
    mwatcher = Mwatcher()
    
    if args.version:
        print("Mwatcher Enhanced v1.0.0")
        print("Universal Movie Watcher with Plex & TV Support")
        return
    
    if args.configure:
        mwatcher.configure()
        return
    
    if args.list_sources:
        mwatcher.list_sources()
        return
    
    if args.list_players:
        mwatcher.list_players()
        return
    
    if args.list_tvs:
        mwatcher.list_tvs()
        return
    
    if args.list_vidaa:
        mwatcher.list_vidaa_tvs()
        return
    
    if args.list_audio:
        mwatcher.list_audio_presets()
        return
    
    if args.url:
        if args.download:
            mwatcher.player.download(args.url)
        else:
            mwatcher.play_url(args.url, args.player, args.tv, args.audio)
        return
    
    if args.stremio:
        mwatcher.play_url(args.stremio, args.player, args.tv, args.audio)
        return
    
    if args.plex:
        mwatcher.play_movie(args.plex, "plex", args.player, args.tv, args.audio)
        return
    
    if args.search:
        results = mwatcher.search_movies(args.search, args.source)
        if results:
            print(f"\nFound {len(results)} results for '{args.search}':")
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Untitled')
                source_name = result.get('source', 'unknown')
                audio_info = " [🎧 Raw]" if result.get('has_raw_audio') else ""
                print(f"{i}. {title} [{source_name}]{audio_info}")
        else:
            print(f"No results found for '{args.search}'")
        return
    
    if args.query:
        if args.download:
            mwatcher.download_movie(args.query, args.source)
        else:
            mwatcher.play_movie(args.query, args.source, args.player, args.tv, args.audio)
        return
    
    # Interactive mode
    print("Mwatcher Enhanced - Universal Movie Watcher with Plex & TV Support")
    print("Type 'help' for commands, 'quit' to exit")
    
    while True:
        try:
            command = input("\nmwatcher> ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
            
            if command.lower() in ['help', '?']:
                print("\nCommands:")
                print("  search <query>       - Search for movies")
                print("  play <query>         - Search and play a movie")
                print("  url <url>            - Play a direct URL")
                print("  plex <query>         - Search Plex servers")
                print("  tv <ip> <query>      - Cast to TV")
                print("  download <query>     - Download a movie")
                print("  sources              - List available sources")
                print("  players              - List available players")
                print("  tvs                 - List TVs on network")
                print("  vidaa               - List VIDAA OS TVs")
                print("  audio               - List audio presets")
                print("  configure            - Configure settings")
                print("  help, ?              - Show this help")
                print("  quit, exit, q        - Exit")
                continue
            
            if command.lower().startswith('search '):
                query = command[7:].strip()
                results = mwatcher.search_movies(query)
                if results:
                    print(f"\nFound {len(results)} results:")
                    for i, result in enumerate(results, 1):
                        title = result.get('title', 'Untitled')
                        source_name = result.get('source', 'unknown')
                        audio_info = " [🎧 Raw]" if result.get('has_raw_audio') else ""
                        print(f"{i}. {title} [{source_name}]{audio_info}")
                else:
                    print("No results found.")
                continue
            
            if command.lower().startswith('play '):
                query = command[5:].strip()
                mwatcher.play_movie(query)
                continue
            
            if command.lower().startswith('plex '):
                query = command[5:].strip()
                mwatcher.play_movie(query, "plex")
                continue
            
            if command.lower().startswith('tv '):
                parts = command[3:].strip().split(maxsplit=1)
                if len(parts) >= 2:
                    tv_ip, query = parts[0], parts[1]
                    mwatcher.play_movie(query, None, None, tv_ip)
                else:
                    print("Usage: tv <ip> <query>")
                continue
            
            if command.lower().startswith('url '):
                url = command[4:].strip()
                mwatcher.play_url(url)
                continue
            
            if command.lower().startswith('download '):
                query = command[9:].strip()
                mwatcher.download_movie(query)
                continue
            
            if command.lower() == 'sources':
                mwatcher.list_sources()
                continue
            
            if command.lower() == 'players':
                mwatcher.list_players()
                continue
            
            if command.lower() == 'tvs':
                mwatcher.list_tvs()
                continue
            
            if command.lower() == 'vidaa':
                mwatcher.list_vidaa_tvs()
                continue
            
            if command.lower() == 'audio':
                mwatcher.list_audio_presets()
                continue
            
            if command.lower() == 'configure':
                mwatcher.configure()
                continue
            
            # Assume it's a search query
            mwatcher.play_movie(command)
            
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
