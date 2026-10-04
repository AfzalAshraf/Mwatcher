#!/usr/bin/env python3
"""
Mwatcher - Universal Movie Watcher
Watch movies from any device with just one command
Supports: Termux, Terminal, VLC, MPV, and Stremio addons

Usage:
    python mwatcher.py "Movie Name"
    python mwatcher.py --search "query"
    python mwatcher.py --stremio "addon://..."
    python mwatcher.py --url "http://..."
    python mwatcher.py --list-sources
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
    },
    "mpv": {
        "name": "MPV Player",
        "command": "mpv",
        "args": "{url}",
        "platforms": ["linux", "darwin"],
    },
    "termux": {
        "name": "Termux MPV",
        "command": "mpv",
        "args": "{url} --no-input-default-bindings",
        "platforms": ["android"],
    },
    "mxplayer": {
        "name": "MX Player",
        "command": "am start -a android.intent.action.VIEW -d {url} -n com.mxtech.videoplayer.ad/.ActivityScreen",
        "args": "",
        "platforms": ["android"],
    },
    "default": {
        "name": "Default Browser",
        "command": "xdg-open" if platform.system().lower() != "darwin" else "open",
        "args": "{url}",
        "platforms": ["linux", "darwin", "windows"],
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
            "preferred_sources": ["stremio", "torrent", "youtube"],
            "preferred_player": self._detect_default_player(),
            "quality": "1080p",
            "subtitles": True,
            "cache_enabled": True,
            "custom_sources": {},
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
        return sources
    
    def get_player(self, player_name: Optional[str] = None) -> Dict:
        """Get player configuration"""
        player_name = player_name or self.config.get("preferred_player", "default")
        return PLAYERS.get(player_name, PLAYERS["default"])


class MovieSearcher:
    """Search for movies across multiple sources"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sources = config.get_sources()
    
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
                else:
                    # Generic HTML-based search
                    results.extend(self._search_generic(query, src))
            except Exception as e:
                print(f"Error searching {src.get('name', src_name)}: {e}")
        
        return results
    
    def _search_youtube(self, query: str) -> List[Dict]:
        """Search YouTube for movies"""
        import requests
        from bs4 import BeautifulSoup
        
        url = DEFAULT_SOURCES["youtube"]["search_url"].format(query=urllib.parse.quote(query + " movie"))
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for item in soup.select('ytd-video-renderer')[:5]:  # Top 5 results
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
        import requests
        
        url = DEFAULT_SOURCES["torrent"]["search_url"].format(query=urllib.parse.quote(query))
        
        try:
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
        # Stremio addon manifest example
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
        import requests
        from bs4 import BeautifulSoup
        
        url = source["search_url"].format(query=urllib.parse.quote(query))
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Try to find movie links - this is generic and may need adjustment
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
    
    def extract(self, url: str, source: str) -> Optional[str]:
        """Extract playable stream URL"""
        try:
            if source == "youtube":
                return self._extract_youtube(url)
            elif source == "torrent":
                return self._extract_torrent(url)
            elif source == "stremio":
                return self._extract_stremio(url)
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
        # Stremio URLs are handled by Stremio itself
        return url
    
    def _extract_generic(self, url: str) -> Optional[str]:
        """Generic stream extraction"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
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
    """Manage video players and playback"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def play(self, url: str, player_name: Optional[str] = None, subtitles: Optional[str] = None):
        """Play a stream with the selected player"""
        player = self.config.get_player(player_name)
        command = player["command"]
        args = player["args"].format(url=url)
        
        full_command = f"{command} {args}"
        
        if subtitles:
            full_command += f" --sub-file={subtitles}"
        
        print(f"Playing: {url}")
        print(f"Using: {player['name']}")
        print(f"Command: {full_command}")
        
        try:
            # Parse and execute the command
            parsed_command = shlex.split(full_command)
            subprocess.run(parsed_command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error playing with {player['name']}: {e}")
            # Try with default player
            self.play(url, "default", subtitles)
        except FileNotFoundError:
            print(f"Player not found: {player['name']}")
            print("Trying alternative players...")
            # Try other players
            for pname, pconfig in PLAYERS.items():
                if pname != player_name:
                    try:
                        self.play(url, pname, subtitles)
                        return
                    except:
                        continue
            print("No suitable player found. Please install VLC, MPV, or another supported player.")
    
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


class Mwatcher:
    """Main Mwatcher class"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.searcher = MovieSearcher(self.config)
        self.extractor = StreamExtractor(self.config)
        self.player = PlayerManager(self.config)
    
    def search_movies(self, query: str, source: Optional[str] = None) -> List[Dict]:
        """Search for movies"""
        return self.searcher.search(query, source)
    
    def play_movie(self, query: str, source: Optional[str] = None, player: Optional[str] = None):
        """Search and play a movie"""
        results = self.search_movies(query, source)
        
        if not results:
            print("No results found.")
            return
        
        # If only one result, play it
        if len(results) == 1:
            self._play_result(results[0], player)
            return
        
        # Show menu for multiple results
        print("\nSelect a movie to play:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'Untitled')} [{result.get('source', 'unknown')}]")
            if result.get('rating'):
                print(f"   Rating: {result['rating']}/10")
            if result.get('duration'):
                print(f"   Duration: {result['duration']}")
        
        try:
            choice = int(input("\nEnter number (0 to cancel): "))
            if 0 < choice <= len(results):
                self._play_result(results[choice - 1], player)
            else:
                print("Invalid selection.")
        except (ValueError, EOFError):
            print("Invalid input.")
    
    def _play_result(self, result: Dict, player: Optional[str] = None):
        """Play a specific result"""
        url = result.get('url', '')
        source = result.get('source', 'unknown')
        
        # Extract stream if needed
        if source != "stremio" and not url.startswith(('http://', 'https://', 'magnet:')):
            stream_url = self.extractor.extract(url, source)
            if stream_url:
                url = stream_url
        
        # Play the stream
        self.player.play(url, player)
    
    def play_url(self, url: str, player: Optional[str] = None):
        """Play a direct URL"""
        self.player.play(url, player)
    
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
        
        stream_url = self.extractor.extract(url, source)
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
            print(f"  - {name}: {info['name']}{available}")
    
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
        print("\nMwatcher Configuration")
        print("=" * 40)
        
        # Show current config
        print("\nCurrent Configuration:")
        print(f"  Preferred sources: {', '.join(self.config.config.get('preferred_sources', []))}")
        print(f"  Preferred player: {self.config.config.get('preferred_player', 'default')}")
        print(f"  Quality: {self.config.config.get('quality', '1080p')}")
        print(f"  Subtitles: {'Enabled' if self.config.config.get('subtitles') else 'Disabled'}")
        
        # Options
        print("\nOptions:")
        print("  1. Change preferred sources")
        print("  2. Change preferred player")
        print("  3. Change quality")
        print("  4. Toggle subtitles")
        print("  5. Add custom source")
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
                self._configure_subtitles()
            elif choice == 5:
                self._configure_custom_source()
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
        """Configure quality"""
        print(f"\nCurrent quality: {self.config.config.get('quality', '1080p')}")
        quality = input("Enter quality (e.g., 1080p, 720p, best): ").strip()
        if quality:
            self.config.config['quality'] = quality
    
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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mwatcher - Universal Movie Watcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mwatcher.py "Inception"
  mwatcher.py --search "The Matrix"
  mwatcher.py --url "https://example.com/movie.mp4"
  mwatcher.py --stremio "addon://..."
  mwatcher.py --list-sources
  mwatcher.py --configure

Environment Variables:
  MWATCHER_PLAYER: Override preferred player
  MWATCHER_SOURCES: Comma-separated list of preferred sources
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
        '--source',
        help='Specific source to use (youtube, torrent, stremio, etc.)'
    )
    parser.add_argument(
        '--player', '-p',
        help='Specific player to use (vlc, mpv, termux, etc.)'
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
        print("Mwatcher v1.0.0")
        print("Universal Movie Watcher")
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
    
    if args.url:
        if args.download:
            mwatcher.player.download(args.url)
        else:
            mwatcher.play_url(args.url, args.player)
        return
    
    if args.stremio:
        mwatcher.play_url(args.stremio, args.player)
        return
    
    if args.search:
        results = mwatcher.search_movies(args.search, args.source)
        if results:
            print(f"\nFound {len(results)} results for '{args.search}':")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.get('title', 'Untitled')} [{result.get('source', 'unknown')}]")
        else:
            print(f"No results found for '{args.search}'")
        return
    
    if args.query:
        if args.download:
            mwatcher.download_movie(args.query, args.source)
        else:
            mwatcher.play_movie(args.query, args.source, args.player)
        return
    
    # Interactive mode
    print("Mwatcher - Universal Movie Watcher")
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
                print("  search <query>    - Search for movies")
                print("  play <query>      - Search and play a movie")
                print("  url <url>         - Play a direct URL")
                print("  download <query>  - Download a movie")
                print("  sources           - List available sources")
                print("  players           - List available players")
                print("  configure         - Configure settings")
                print("  help, ?           - Show this help")
                print("  quit, exit, q     - Exit")
                continue
            
            if command.lower().startswith('search '):
                query = command[7:].strip()
                results = mwatcher.search_movies(query, args.source)
                if results:
                    print(f"\nFound {len(results)} results:")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. {result.get('title', 'Untitled')} [{result.get('source', 'unknown')}]")
                else:
                    print("No results found.")
                continue
            
            if command.lower().startswith('play '):
                query = command[5:].strip()
                mwatcher.play_movie(query, args.source, args.player)
                continue
            
            if command.lower().startswith('url '):
                url = command[4:].strip()
                mwatcher.play_url(url, args.player)
                continue
            
            if command.lower().startswith('download '):
                query = command[9:].strip()
                mwatcher.download_movie(query, args.source)
                continue
            
            if command.lower() == 'sources':
                mwatcher.list_sources()
                continue
            
            if command.lower() == 'players':
                mwatcher.list_players()
                continue
            
            if command.lower() == 'configure':
                mwatcher.configure()
                continue
            
            # Assume it's a search query
            mwatcher.play_movie(command, args.source, args.player)
            
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")


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


if __name__ == "__main__":
    main()
