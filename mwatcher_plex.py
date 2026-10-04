#!/usr/bin/env python3
"""
Mwatcher Plex Integration Module
Adds Plex Media Server support with direct play and transcoding
Supports raw audio passthrough (5.1, 7.1, etc.)
"""

import json
import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

# Plex API endpoints
PLEX_API_BASE = "http://{server}:{port}"
PLEX_LIBRARY_SECTIONS = "/library/sections"
PLEX_LIBRARY_ALL = "/library/all"
PLEX_SEARCH = "/search"
PLEX_TRANSCODE = "/video/:/transcode/universal/start"
PLEX_DIRECT_STREAM = "/video/:/stream"


class PlexServer:
    """Represents a Plex Media Server connection"""
    
    def __init__(self, server: str, port: int = 32400, token: Optional[str] = None, 
                 username: Optional[str] = None, password: Optional[str] = None):
        self.server = server
        self.port = port
        self.token = token
        self.username = username
        self.password = password
        self.base_url = PLEX_API_BASE.format(server=server, port=port)
        self.friendly_name = f"{server}:{port}"
        self.libraries = []
        self._authenticated = False
    
    def get_auth_headers(self) -> Dict:
        """Get authentication headers"""
        headers = {
            "Accept": "application/json",
            "X-Plex-Client-Identifier": "mwatcher",
            "X-Plex-Product": "Mwatcher",
            "X-Plex-Version": "1.0.0",
            "X-Plex-Platform": "Linux",
        }
        
        if self.token:
            headers["X-Plex-Token"] = self.token
        
        return headers
    
    def authenticate(self) -> bool:
        """Authenticate with Plex server"""
        import requests
        
        # Try with token first
        if self.token:
            try:
                response = requests.get(
                    f"{self.base_url}/library/sections",
                    headers=self.get_auth_headers(),
                    timeout=5
                )
                if response.status_code == 200:
                    self._authenticated = True
                    self._load_libraries()
                    return True
            except:
                pass
        
        # Try with username/password
        if self.username and self.password:
            try:
                auth_url = f"{self.base_url}/users/signin"
                response = requests.post(
                    auth_url,
                    json={
                        "user": {
                            "login": self.username,
                            "password": self.password
                        }
                    },
                    headers={"Accept": "application/json"},
                    timeout=5
                )
                if response.status_code == 201:
                    data = response.json()
                    self.token = data.get("user", {}).get("authToken")
                    self._authenticated = True
                    self._load_libraries()
                    return True
            except:
                pass
        
        # Try without authentication (local network)
        try:
            response = requests.get(
                f"{self.base_url}/library/sections",
                timeout=5
            )
            if response.status_code == 200:
                self._authenticated = True
                self._load_libraries()
                return True
        except:
            pass
        
        return False
    
    def _load_libraries(self):
        """Load available libraries from server"""
        import requests
        
        try:
            response = requests.get(
                f"{self.base_url}/library/sections",
                headers=self.get_auth_headers(),
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.libraries = data.get("MediaContainer", {}).get("Directory", [])
        except:
            self.libraries = []
    
    def get_libraries(self) -> List[Dict]:
        """Get list of available libraries"""
        if not self._authenticated:
            self.authenticate()
        return self.libraries
    
    def search(self, query: str, library: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search for content on Plex server"""
        import requests
        
        if not self._authenticated:
            if not self.authenticate():
                return []
        
        results = []
        
        # Search all libraries or specific one
        url = f"{self.base_url}/search"
        params = {
            "query": query,
            "limit": limit,
        }
        
        if library:
            params["sectionID"] = library
        
        try:
            response = requests.get(
                url,
                headers=self.get_auth_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("MediaContainer", {}).get("Hub", []):
                    for hub_item in item.get("Item", []):
                        results.append(self._parse_plex_item(hub_item))
                
                # Also try direct search
                if not results:
                    search_url = f"{self.base_url}/library/all"
                    search_params = {
                        "title": query,
                        "limit": limit,
                    }
                    if library:
                        search_params["sectionID"] = library
                    
                    response2 = requests.get(
                        search_url,
                        headers=self.get_auth_headers(),
                        params=search_params,
                        timeout=10
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        for item in data2.get("MediaContainer", {}).get("Metadata", []):
                            results.append(self._parse_plex_item(item))
        
        except Exception as e:
            print(f"Error searching Plex: {e}")
        
        return results
    
    def _parse_plex_item(self, item: Dict) -> Dict:
        """Parse Plex item into standard format"""
        # Get the best video stream
        media = item.get("Media", [{}])[0] if isinstance(item.get("Media"), list) else item.get("Media", {})
        
        # Get video resolution
        video_resolution = None
        if media:
            video = media.get("Video", [{}])[0] if isinstance(media.get("Video"), list) else media.get("Video", {})
            if video:
                video_resolution = video.get("resolution")
        
        # Get audio info
        audio_info = []
        if media:
            for audio in media.get("Audio", []):
                if isinstance(audio, dict):
                    audio_info.append({
                        "codec": audio.get("codec"),
                        "channels": audio.get("channels"),
                        "language": audio.get("language"),
                        "bitrate": audio.get("bitrate"),
                    })
        
        return {
            "title": item.get("title", "Unknown"),
            "year": item.get("year"),
            "type": item.get("type", "movie"),
            "source": "plex",
            "plex_id": item.get("ratingKey"),
            "plex_server": self.friendly_name,
            "url": self._get_stream_url(item),
            "direct_url": self._get_direct_url(item),
            "quality": video_resolution,
            "audio": audio_info,
            "duration": item.get("duration"),
            "rating": item.get("rating"),
            "summary": item.get("summary"),
            "thumb": item.get("thumb"),
            "art": item.get("art"),
            "library": item.get("librarySectionTitle"),
        }
    
    def _get_stream_url(self, item: Dict) -> str:
        """Get stream URL for the item"""
        rating_key = item.get("ratingKey")
        if rating_key:
            return f"{self.base_url}/video/:/transcode/universal/start?path=/library/metadata/{rating_key}"
        return ""
    
    def _get_direct_url(self, item: Dict) -> str:
        """Get direct play URL for the item"""
        rating_key = item.get("ratingKey")
        if rating_key:
            # Get the first media part
            media = item.get("Media", [{}])[0] if isinstance(item.get("Media"), list) else item.get("Media", {})
            if media:
                parts = media.get("Part", [{}])[0] if isinstance(media.get("Part"), list) else media.get("Part", {})
                if parts:
                    file_path = parts.get("file")
                    if file_path:
                        return f"{self.base_url}{file_path}?X-Plex-Token={self.token}"
            return f"{self.base_url}/library/metadata/{rating_key}"
        return ""
    
    def get_direct_play_url(self, item: Dict, audio_stream: Optional[int] = None) -> str:
        """Get direct play URL with optional audio stream selection"""
        rating_key = item.get("ratingKey")
        if not rating_key:
            return ""
        
        media = item.get("Media", [{}])[0] if isinstance(item.get("Media"), list) else item.get("Media", {})
        if not media:
            return ""
        
        parts = media.get("Part", [{}])[0] if isinstance(media.get("Part"), list) else media.get("Part", {})
        if not parts:
            return ""
        
        file_path = parts.get("file")
        if not file_path:
            return ""
        
        # Build URL with audio stream selection
        url = f"{self.base_url}{file_path}?X-Plex-Token={self.token}"
        
        # Add audio stream parameter if specified
        if audio_stream is not None:
            url += f"&audioStreamID={audio_stream}"
        
        return url
    
    def get_transcode_url(self, item: Dict, quality: str = "1080p", audio_quality: str = "original") -> str:
        """Get transcoding URL for the item"""
        rating_key = item.get("ratingKey")
        if not rating_key:
            return ""
        
        # Map quality to Plex quality
        quality_map = {
            "480p": "720x480",
            "720p": "1280x720",
            "1080p": "1920x1080",
            "4k": "3840x2160",
            "best": "original",
        }
        
        video_quality = quality_map.get(quality, "1920x1080")
        
        # Map audio quality
        audio_map = {
            "original": "original",
            "5.1": "5.1",
            "7.1": "7.1",
            "stereo": "2.0",
        }
        
        audio_q = audio_map.get(audio_quality, "original")
        
        url = f"{self.base_url}/video/:/transcode/universal/start"
        params = {
            "path": f"/library/metadata/{rating_key}",
            "offset": 0,
            "X-Plex-Token": self.token,
            "maxVideoBitrate": 20000 if video_quality != "original" else None,
            "videoResolution": video_quality if video_quality != "original" else None,
            "videoQuality": 100,
            "audioQuality": 100,
            "audioBoost": 100,
        }
        
        # Add audio channels if specified
        if audio_q in ["5.1", "7.1"]:
            params["audioChannels"] = audio_q
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        
        return f"{url}?{query_string}"


class PlexManager:
    """Manage multiple Plex servers"""
    
    def __init__(self):
        self.servers = []
        self._load_servers()
    
    def _load_servers(self):
        """Load Plex servers from configuration"""
        config_dir = Path.home() / ".mwatcher"
        config_file = config_dir / "plex_servers.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    servers_data = json.load(f)
                    for server_data in servers_data.get("servers", []):
                        self.servers.append(PlexServer(
                            server=server_data.get("server", "localhost"),
                            port=server_data.get("port", 32400),
                            token=server_data.get("token"),
                            username=server_data.get("username"),
                            password=server_data.get("password")
                        ))
            except:
                pass
    
    def save_servers(self):
        """Save Plex servers to configuration"""
        config_dir = Path.home() / ".mwatcher"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "plex_servers.json"
        
        servers_data = {
            "servers": [
                {
                    "server": s.server,
                    "port": s.port,
                    "token": s.token,
                    "username": s.username,
                    "password": s.password,
                }
                for s in self.servers
            ]
        }
        
        with open(config_file, 'w') as f:
            json.dump(servers_data, f, indent=2)
    
    def add_server(self, server: str, port: int = 32400, token: Optional[str] = None,
                   username: Optional[str] = None, password: Optional[str] = None) -> PlexServer:
        """Add a new Plex server"""
        plex_server = PlexServer(server, port, token, username, password)
        if plex_server.authenticate():
            self.servers.append(plex_server)
            self.save_servers()
            return plex_server
        return None
    
    def remove_server(self, index: int):
        """Remove a Plex server"""
        if 0 <= index < len(self.servers):
            self.servers.pop(index)
            self.save_servers()
    
    def get_servers(self) -> List[PlexServer]:
        """Get list of configured Plex servers"""
        return self.servers
    
    def search_all(self, query: str, limit: int = 10) -> List[Dict]:
        """Search across all Plex servers"""
        all_results = []
        for server in self.servers:
            results = server.search(query, limit=limit)
            for result in results:
                result["plex_server_name"] = server.friendly_name
                all_results.append(result)
        return all_results
    
    def discover_servers(self) -> List[Dict]:
        """Discover Plex servers on local network"""
        import requests
        import socket
        import concurrent.futures
        
        discovered = []
        local_ips = self._get_local_ips()
        
        # Common Plex ports
        ports = [32400, 32401, 32402]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for ip in local_ips:
                for port in ports:
                    futures.append(executor.submit(self._check_plex_server, ip, port))
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    discovered.append(result)
        
        return discovered
    
    def _get_local_ips(self) -> List[str]:
        """Get local IP addresses"""
        import socket
        import netifaces
        
        ips = []
        
        try:
            # Try using netifaces for better detection
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                try:
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info.get('addr')
                            if ip and not ip.startswith('127.'):
                                # Get network prefix
                                netmask = addr_info.get('netmask', '255.255.255.0')
                                network = self._ip_to_network(ip, netmask)
                                if network:
                                    ips.append(network)
                except:
                    continue
        except:
            pass
        
        # Fallback to simple localhost
        if not ips:
            ips = ["127.0.0.1"]
        
        return ips
    
    def _ip_to_network(self, ip: str, netmask: str) -> str:
        """Convert IP and netmask to network address"""
        import ipaddress
        
        try:
            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            return str(network.network_address)
        except:
            return ""
    
    def _check_plex_server(self, ip: str, port: int) -> Optional[Dict]:
        """Check if a Plex server is running at the given IP and port"""
        import requests
        
        try:
            url = f"http://{ip}:{port}/identity"
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                return {
                    "server": ip,
                    "port": port,
                    "url": f"http://{ip}:{port}",
                }
        except:
            pass
        
        return None


class PlexAudioHandler:
    """Handle Plex audio streams with raw passthrough support"""
    
    def __init__(self, plex_manager: PlexManager):
        self.plex_manager = plex_manager
    
    def get_audio_streams(self, item: Dict) -> List[Dict]:
        """Get available audio streams for an item"""
        media = item.get("Media", [{}])[0] if isinstance(item.get("Media"), list) else item.get("Media", {})
        if not media:
            return []
        
        audio_streams = []
        for i, audio in enumerate(media.get("Audio", [])):
            if isinstance(audio, dict):
                audio_streams.append({
                    "index": i,
                    "codec": audio.get("codec", "unknown"),
                    "channels": audio.get("channels", 2),
                    "language": audio.get("language", "unknown"),
                    "bitrate": audio.get("bitrate", 0),
                    "sample_rate": audio.get("sampleRate", 0),
                    "is_raw": self._is_raw_audio(audio.get("codec", "")),
                })
        
        return audio_streams
    
    def _is_raw_audio(self, codec: str) -> bool:
        """Check if audio codec supports raw passthrough"""
        raw_codecs = [
            "aac", "ac3", "eac3", "dts", "dtshd", "truehd",
            "flac", "mp3", "pcm", "vorbis", "opus"
        ]
        return codec.lower() in raw_codecs
    
    def get_raw_audio_stream(self, item: Dict) -> Optional[Dict]:
        """Get the best raw audio stream (5.1, 7.1, etc.)"""
        audio_streams = self.get_audio_streams(item)
        
        # Prefer raw audio with most channels
        raw_streams = [s for s in audio_streams if s.get("is_raw")]
        if not raw_streams:
            return None
        
        # Sort by channel count (descending)
        raw_streams.sort(key=lambda x: x.get("channels", 0), reverse=True)
        
        return raw_streams[0] if raw_streams else None
    
    def get_best_audio_stream(self, item: Dict, prefer_raw: bool = True) -> Optional[Dict]:
        """Get the best audio stream based on preferences"""
        audio_streams = self.get_audio_streams(item)
        if not audio_streams:
            return None
        
        if prefer_raw:
            # Try to find raw audio with most channels
            raw_streams = [s for s in audio_streams if s.get("is_raw")]
            if raw_streams:
                raw_streams.sort(key=lambda x: x.get("channels", 0), reverse=True)
                return raw_streams[0]
        
        # Return the stream with most channels
        audio_streams.sort(key=lambda x: x.get("channels", 0), reverse=True)
        return audio_streams[0]


class DLNACaster:
    """Cast to DLNA/UPnP devices (including VIDAA OS TVs)"""
    
    def __init__(self):
        self.devices = []
        self._discover_devices()
    
    def _discover_devices(self):
        """Discover DLNA/UPnP devices on the network"""
        import requests
        import socket
        import xml.etree.ElementTree as ET
        
        try:
            # Use SSDP to discover UPnP devices
            ssdp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ssdp_socket.settimeout(3)
            
            # SSDP multicast address
            ssdp_address = ('239.255.255.250', 1900)
            
            # Send SSDP M-SEARCH
            search_request = (
                'M-SEARCH * HTTP/1.1\r\n'
                'HOST: 239.255.255.250:1900\r\n'
                'MAN: "ssdp:discover"\r\n'
                'MX: 3\r\n'
                'ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n'
                '\r\n'
            )
            
            ssdp_socket.sendto(search_request.encode(), ssdp_address)
            
            # Listen for responses
            self.devices = []
            try:
                while True:
                    data, addr = ssdp_socket.recvfrom(8192)
                    if b'ST: urn:schemas-upnp-org:device:MediaRenderer:1' in data:
                        self._parse_ssdp_response(data.decode(), addr[0])
            except socket.timeout:
                pass
            
            ssdp_socket.close()
            
        except Exception as e:
            print(f"DLNA discovery error: {e}")
    
    def _parse_ssdp_response(self, response: str, ip: str):
        """Parse SSDP response to extract device info"""
        import re
        
        # Extract LOCATION header
        location_match = re.search(r'LOCATION:\s*(.+?)\r\n', response, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()
            try:
                # Fetch device description
                import requests
                response = requests.get(location, timeout=3)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    
                    # Extract device info
                    device = {
                        'ip': ip,
                        'location': location,
                        'friendly_name': '',
                        'model': '',
                        'manufacturer': '',
                        'udn': '',
                    }
                    
                    # Find friendly name
                    for elem in root.iter():
                        if elem.tag.endswith('friendlyName'):
                            device['friendly_name'] = elem.text or ''
                        elif elem.tag.endswith('modelName'):
                            device['model'] = elem.text or ''
                        elif elem.tag.endswith('manufacturer'):
                            device['manufacturer'] = elem.text or ''
                        elif elem.tag.endswith('UDN'):
                            device['udn'] = elem.text or ''
                    
                    # Check if this is a VIDAA OS device
                    if 'vidaa' in device['model'].lower() or 'hisense' in device['manufacturer'].lower():
                        device['type'] = 'vidaa'
                    else:
                        device['type'] = 'dlna'
                    
                    self.devices.append(device)
            except:
                pass
    
    def get_devices(self) -> List[Dict]:
        """Get list of discovered DLNA/UPnP devices"""
        return self.devices
    
    def discover_vidaa_tvs(self) -> List[Dict]:
        """Get list of VIDAA OS TVs specifically"""
        return [d for d in self.devices if d.get('type') == 'vidaa']
    
    def cast_to_device(self, device_ip: str, url: str, title: str = "Movie") -> bool:
        """Cast a URL to a DLNA device"""
        import requests
        
        # Find the device
        device = next((d for d in self.devices if d.get('ip') == device_ip), None)
        if not device:
            return False
        
        try:
            # Get the control URL from device description
            import xml.etree.ElementTree as ET
            response = requests.get(device['location'], timeout=3)
            if response.status_code != 200:
                return False
            
            root = ET.fromstring(response.text)
            
            # Find AVTransport service
            av_transport_url = None
            for elem in root.iter():
                if elem.tag.endswith('AVTransport') and elem.tag.endswith('controlURL'):
                    av_transport_url = elem.text
                    break
            
            if not av_transport_url:
                # Try to construct from base URL
                av_transport_url = f"{device['location'].rsplit('/', 1)[0]}/AVTransport/control"
            
            # Build SOAP request for SetAVTransportURI
            soap_body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{url}</CurrentURI>
      <CurrentURIMetaData>
        <DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
          <item id="0" parentID="0" restricted="1">
            <dc:title>{title}</dc:title>
            <dc:creator>Mwatcher</dc:creator>
            <upnp:class>object.item.videoItem</upnp:class>
          </item>
        </DIDL-Lite>
      </CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPACTION': '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"',
            }
            
            response = requests.post(
                av_transport_url,
                data=soap_body,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                # Now send Play command
                play_body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>'''
                
                play_headers = {
                    'Content-Type': 'text/xml; charset="utf-8"',
                    'SOAPACTION': '"urn:schemas-upnp-org:service:AVTransport:1#Play"',
                }
                
                play_response = requests.post(
                    av_transport_url,
                    data=play_body,
                    headers=play_headers,
                    timeout=5
                )
                
                return play_response.status_code == 200
            
        except Exception as e:
            print(f"Error casting to DLNA: {e}")
            return False
        
        return False
    
    def cast_to_vidaa(self, tv_ip: str, url: str, title: str = "Movie") -> bool:
        """Cast to VIDAA OS TV specifically"""
        # VIDAA OS uses a custom API
        import requests
        
        try:
            # VIDAA OS API endpoint
            api_url = f"http://{tv_ip}:8080/api/v1/play"
            
            payload = {
                "action": "play",
                "type": "video",
                "url": url,
                "title": title,
                "format": "mp4"
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mwatcher/1.0"
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=5)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error casting to VIDAA: {e}")
            # Try alternative VIDAA API
            try:
                alt_url = f"http://{tv_ip}/remote/play"
                alt_payload = {
                    "uri": url,
                    "title": title
                }
                alt_response = requests.post(alt_url, json=alt_payload, timeout=5)
                return alt_response.status_code == 200
            except:
                return False


class TVPlatformHandler:
    """Handle TV-specific platforms like VIDAA OS, Android TV, etc."""
    
    def __init__(self):
        self.dlna_caster = DLNACaster()
    
    def detect_platform(self, ip: str) -> Optional[str]:
        """Detect the TV platform"""
        # Check for VIDAA OS
        vidaa_tvs = self.dlna_caster.discover_vidaa_tvs()
        for tv in vidaa_tvs:
            if tv.get('ip') == ip:
                return 'vidaa'
        
        # Check for Android TV
        # Check for Samsung Tizen
        # Check for LG webOS
        # Check for Roku
        
        # For now, return generic DLNA
        return 'dlna'
    
    def get_vidaa_tvs(self) -> List[Dict]:
        """Get all VIDAA OS TVs on the network"""
        return self.dlna_caster.discover_vidaa_tvs()
    
    def cast_to_tv(self, tv_ip: str, url: str, title: str = "Movie", platform: Optional[str] = None) -> bool:
        """Cast to a TV based on platform"""
        if not platform:
            platform = self.detect_platform(tv_ip)
        
        if platform == 'vidaa':
            return self.dlna_caster.cast_to_vidaa(tv_ip, url, title)
        else:
            return self.dlna_caster.cast_to_device(tv_ip, url, title)
    
    def get_all_tvs(self) -> List[Dict]:
        """Get all TVs on the network"""
        return self.dlna_caster.get_devices()


# Audio quality presets
AUDIO_PRESETS = {
    "raw": {
        "name": "Raw Passthrough",
        "description": "Direct audio passthrough (5.1, 7.1)",
        "codecs": ["ac3", "eac3", "dts", "dtshd", "truehd", "flac"],
        "channels": [6, 8],  # 5.1, 7.1
    },
    "5.1": {
        "name": "5.1 Surround",
        "description": "5.1 channel audio",
        "codecs": ["ac3", "eac3", "dts"],
        "channels": 6,
    },
    "7.1": {
        "name": "7.1 Surround",
        "description": "7.1 channel audio",
        "codecs": ["dtshd", "truehd"],
        "channels": 8,
    },
    "stereo": {
        "name": "Stereo",
        "description": "2.0 stereo audio",
        "codecs": ["aac", "mp3", "pcm"],
        "channels": 2,
    },
    "best": {
        "name": "Best Available",
        "description": "Highest quality available",
        "codecs": None,
        "channels": None,
    },
}


class EnhancedPlayerManager:
    """Enhanced player manager with audio passthrough support"""
    
    def __init__(self, config=None):
        self.config = config
        self.tv_handler = TVPlatformHandler()
    
    def play_with_audio_passthrough(self, url: str, audio_quality: str = "raw", 
                                     player: Optional[str] = None, 
                                     tv_ip: Optional[str] = None):
        """Play with specific audio quality and passthrough"""
        
        # If TV IP is specified, cast to TV
        if tv_ip:
            return self.tv_handler.cast_to_tv(tv_ip, url, "Movie", self.tv_handler.detect_platform(tv_ip))
        
        # Otherwise, play locally with audio passthrough
        player_config = self._get_player_config(player)
        command = player_config["command"]
        
        # Add audio passthrough flags based on quality
        audio_flags = self._get_audio_flags(audio_quality, player_config.get("type", "vlc"))
        
        args = player_config["args"].format(url=url)
        full_command = f"{command} {args} {audio_flags}"
        
        print(f"Playing: {url}")
        print(f"Using: {player_config['name']}")
        print(f"Audio Quality: {audio_quality}")
        print(f"Command: {full_command}")
        
        try:
            import shlex
            import subprocess
            parsed_command = shlex.split(full_command)
            subprocess.run(parsed_command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            return False
        except FileNotFoundError:
            print(f"Player not found: {player_config['name']}")
            return False
    
    def _get_player_config(self, player_name: Optional[str] = None) -> Dict:
        """Get player configuration with enhanced audio support"""
        players = {
            "vlc": {
                "name": "VLC Media Player",
                "command": "vlc",
                "args": "{url}",
                "type": "vlc",
                "audio_flags": "",
            },
            "mpv": {
                "name": "MPV Player",
                "command": "mpv",
                "args": "{url}",
                "type": "mpv",
                "audio_flags": "",
            },
            "mxplayer": {
                "name": "MX Player",
                "command": "am start -a android.intent.action.VIEW -d {url} -n com.mxtech.videoplayer.ad/.ActivityScreen",
                "args": "",
                "type": "mxplayer",
                "audio_flags": "",
            },
        }
        
        player_name = player_name or (self.config.config.get("preferred_player", "vlc") if self.config else "vlc")
        return players.get(player_name, players["vlc"])
    
    def _get_audio_flags(self, audio_quality: str, player_type: str) -> str:
        """Get audio passthrough flags for player"""
        
        if audio_quality == "raw" or audio_quality == "best":
            if player_type == "vlc":
                return "--spdif --audio-filter normvol --audio-sync 0"
            elif player_type == "mpv":
                return "--audio-device=alsa/default --audio-channels=auto --audio-format=s16le"
        
        elif audio_quality == "5.1":
            if player_type == "vlc":
                return "--audio-channels=6 --spdif"
            elif player_type == "mpv":
                return "--audio-channels=5.1 --audio-device=alsa/default"
        
        elif audio_quality == "7.1":
            if player_type == "vlc":
                return "--audio-channels=8 --spdif"
            elif player_type == "mpv":
                return "--audio-channels=7.1 --audio-device=alsa/default"
        
        elif audio_quality == "stereo":
            if player_type == "vlc":
                return "--audio-channels=2"
            elif player_type == "mpv":
                return "--audio-channels=2.0"
        
        return ""
    
    def list_tvs(self) -> List[Dict]:
        """List all TVs on the network"""
        return self.tv_handler.get_all_tvs()
    
    def list_vidaa_tvs(self) -> List[Dict]:
        """List all VIDAA OS TVs on the network"""
        return self.tv_handler.get_vidaa_tvs()


def main():
    """Main function for Plex integration testing"""
    
    print("Mwatcher Plex Integration Test")
    print("=" * 40)
    
    # Test Plex server discovery
    plex_manager = PlexManager()
    
    print("\n1. Discovering Plex servers on network...")
    servers = plex_manager.discover_servers()
    print(f"   Found {len(servers)} Plex servers")
    for server in servers:
        print(f"   - {server.get('url')}")
    
    # Test DLNA discovery
    print("\n2. Discovering DLNA/UPnP devices...")
    dlna_caster = DLNACaster()
    devices = dlna_caster.get_devices()
    print(f"   Found {len(devices)} DLNA devices")
    for device in devices:
        print(f"   - {device.get('friendly_name', 'Unknown')} ({device.get('ip')}) - {device.get('type')}")
    
    # Test VIDAA discovery
    print("\n3. VIDAA OS TVs:")
    vidaa_tvs = dlna_caster.discover_vidaa_tvs()
    print(f"   Found {len(vidaa_tvs)} VIDAA TVs")
    for tv in vidaa_tvs:
        print(f"   - {tv.get('friendly_name', 'Unknown')} ({tv.get('ip')})")
    
    # Test audio presets
    print("\n4. Available Audio Presets:")
    for preset_name, preset in AUDIO_PRESETS.items():
        print(f"   - {preset_name}: {preset['description']}")


if __name__ == "__main__":
    main()
