#!/usr/bin/env python3
"""
telestream_to_plex.py -- bridge your Stremio addons (via Fast Combo) into a Plex library.

Plex has no addon/plugin system any more, so it cannot play a remote HTTP stream the way
Stremio does. This script is the glue between the two: it asks Fast Combo
(https://github.com/AfzalAshraf/stremio-addons) -- which queries all of your addons at
once, filters out CAM copies, dead links, duplicates and files too big to stream
smoothly, live-probes the rest and ranks them -- takes the SINGLE BEST downloadable
link, fetches it into a staging folder, renames it the way Plex expects, and drops it
into your library so every Plex client in the world can play it.

If the chosen link dies part-way it automatically falls back to the next-best one.

Three ways to drive it
----------------------
1) Web dashboard (search a title, see the ranked streams, press "Fetch best"):

     python3 telestream_to_plex.py serve        # then open http://127.0.0.1:8889/

2) One-shot CLI (good for cron / scripts):

     python3 telestream_to_plex.py --title "Dune" --year 2021 --prefer fastest
     python3 telestream_to_plex.py --imdb tt0903747 --kind show --episode S01E02
     python3 telestream_to_plex.py --list-streams --imdb tt1160419   # rank, don't download
     python3 telestream_to_plex.py --url https://host/file.mkv --title "Dune"  # direct link

3) HTTP API (what an addon, shortcut or other service should call):

     curl -X POST http://127.0.0.1:8889/fetch -H 'Content-Type: application/json' \
       -d '{"title":"Dune","year":2021,"kind":"movie","prefer":"fastest"}'

     GET /search?q=dune        title -> IMDb matches (Cinemeta)
     GET /streams?id=tt1160419 ranked candidates from all your addons, best one flagged
     GET /jobs                 progress + which stream was picked and why
     GET /config               effective configuration
     GET /healthz              ok
     GET /seerr                is Seerr reachable + what is queued for download
     GET /plays                every play-through pointer, and whether it is cached
     GET /cache                cache dir, size vs cap, oldest-first eviction
     POST /request             ask Seerr to fetch a title (Radarr/Sonarr download it)
     POST /add                 add a title WITHOUT downloading it (play-through .strm)

PLAY-THROUGH -- add titles without downloading them (action=strm):

     POST /add   -d '{"title":"Dune","year":2021}'      # 0 bytes downloaded, 45-byte .strm
     GET /play/<key>.mkv                                # what Plex then asks for

  Instead of a file, the library gets a tiny .strm pointer at this bridge. When Plex plays
  it, the bridge scrapes a FRESH link from your addons at that moment, opens it with the
  headers the host demands, and streams it through -- Range-aware, so seeking works --
  while keeping a capped cache (oldest evicted first). A host serving a captcha/HTML wall
  is detected BEFORE the first byte is committed and the next link is tried.
  TELESTREAM_PUBLIC_BASE_URL is the address written into the .strm and MUST be reachable
  from your Plex clients, not from this server -- loopback there means s1001 everywhere.

SEERR -- request it instead of streaming it (no debrid service needed):

     POST /request  -d '{"title":"Dune","year":2021}'
     POST /fetch    -d '{"title":"Dune","action":"both"}'    # request AND stream now

  Seerr does not download anything itself: it hands the request to Radarr/Sonarr, which
  use Prowlarr (indexers) and a download client (qBittorrent/SABnzbd) to put real files
  in your library. So the chain is  Seerr -> Radarr/Sonarr -> qBittorrent -> ~/media ->
  Plex. What that buys you over streaming from an addon: no debrid subscription, the
  file is yours forever, proper quality profiles and subtitles, and no link rot.
  Set SEERR_URL + SEERR_API_KEY (Seerr -> Settings -> General; treat it as an admin
  credential) and SEERR_MODE=off|request|both.

Configuration is by environment variable so the systemd unit stays the single source of
truth (see services/mwatcher-bridge.service and config/bridge.env.example):

  FASTCOMBO_BASE_URL          Your Fast Combo server            (default http://127.0.0.1:7000)
  FASTCOMBO_ACCESS_KEY        Secret part of your addon link    (required for addon lookups)
  FASTCOMBO_TOKEN             Optional profile token from a personalised install link
  FASTCOMBO_PREFER            best | fastest | smallest | 4kfirst | 1080first (default best)
                              "fastest" = the link that starts soonest = "single best speed"
  FASTCOMBO_MAX_FALLBACKS     How many next-best links to try if one fails   (default 4)
  CINEMETA_URL                Title -> IMDb metadata (default https://v3-cinemeta.strem.io)
  TELESTREAM_DOWNLOAD_CMD     Shell command that fetches a link. {stream} {out} {headers}
                              are substituted ALREADY SHELL-QUOTED, so use them bare.
                              Default: yt-dlp if present, else curl, else ffmpeg.
  TELESTREAM_STAGING          Where partial downloads go          (default ~/media/staging)
  TELESTREAM_MOVIES_DIR       Finished movies                    (default ~/media/Movies)
  TELESTREAM_TV_DIR           Finished episodes                  (default ~/media/TV Shows)
  TELESTREAM_RESOLVER_URL     Optional legacy hook: template that turns a --url into a
                              direct media link ({url}/{title} substituted). Default off --
                              Fast Combo is the source now.
  BRIDGE_HOST / BRIDGE_PORT   Endpoint bind address              (default 127.0.0.1:8889)
  TELESTREAM_ACTION           stream | strm | seerr | both       (default stream)
  TELESTREAM_PUBLIC_BASE_URL  Address CLIENTS reach this bridge at (default: LAN IP)
  TELESTREAM_CACHE_DIR        Play-through cache                 (default ~/media/cache)
  TELESTREAM_CACHE_MAX_GB     Cache cap, oldest evicted first    (default 20)
  TELESTREAM_RESOLVE_TTL      Seconds before a link is re-scraped (default 300)
  SEERR_URL                   Seerr base url                     (default off)
  SEERR_API_KEY               Seerr -> Settings -> General       (admin credential!)
  SEERR_MODE                  off | request | both               (default off)
  SEERR_IS4K                  request the 4K variant             (default 0)
  SEERR_TV_SEASONS            all | missing | "1,2"              (default all)

Keep the endpoint and Fast Combo on 127.0.0.1 -- expose them with a reverse proxy (and
auth) only if you must. Torrent links (infoHash, no url) cannot be downloaded directly;
they need a debrid service, so the bridge skips them and says so.

Testing with no real addons: run demo/fake_stremio_addon.py (a pretend addon AND a
pretend Cinemeta), point Fast Combo at it, and the whole pipeline runs offline.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# stremio_source.py lives next to this file; make sure it is importable however we are run.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import stremio_source
except ImportError:  # pragma: no cover - bridge still works for direct URLs without it
    stremio_source = None
try:
    import seerr_source
except ImportError:  # pragma: no cover - Seerr support is optional
    seerr_source = None

# The service gets its config from EnvironmentFile= in mwatcher-bridge.service. A shell does
# not, so without this the CLI reports "FASTCOMBO_ACCESS_KEY is not set" while the key sits
# in a file the installer wrote -- and `install.sh status` says everything is fine. Values
# already in the environment win, so an explicit override still works.
try:
    import envfile
    ENV_FILE = envfile.load()
except ImportError:  # pragma: no cover - still runs, just without the env file
    ENV_FILE = None

# --------------------------------------------------------------------------- config

HOME = os.path.expanduser("~")

# --- Fast Combo / Stremio addons (https://github.com/AfzalAshraf/stremio-addons) -------
# Fast Combo queries all of your addons at once and returns them ranked best-first, so
# "the single best stream" is simply the first one that we can actually download.
FASTCOMBO_BASE_URL = os.environ.get("FASTCOMBO_BASE_URL", "http://127.0.0.1:7000").rstrip("/")
FASTCOMBO_ACCESS_KEY = os.environ.get("FASTCOMBO_ACCESS_KEY", "")
FASTCOMBO_TOKEN = os.environ.get("FASTCOMBO_TOKEN", "")
FASTCOMBO_PREFER = os.environ.get("FASTCOMBO_PREFER", "best")
FASTCOMBO_MAX_FALLBACKS = int(os.environ.get("FASTCOMBO_MAX_FALLBACKS", "4"))
FASTCOMBO_TIMEOUT = float(os.environ.get("FASTCOMBO_TIMEOUT", "60"))
CINEMETA_URL = os.environ.get("CINEMETA_URL", stremio_source.DEFAULT_CINEMETA if stremio_source else "")

# --- Seerr: request it, and your own server downloads it (no debrid) -------------------
# Seerr is the request/approval layer; it delegates to Radarr/Sonarr, which use Prowlarr
# (indexers) and a download client (qBittorrent/SABnzbd) to put real files in ~/media.
# That is the "browse -> request -> it lands on my server" path, and it needs no debrid
# subscription -- torrents/NZBs do the fetching.
#
# SEERR_MODE:
#   off     never touch Seerr (default; stream via Fast Combo as before)
#   request only create a Seerr request -- nothing is downloaded by the bridge
#   both    create the Seerr request AND stream now, so you can watch immediately
#           while the permanent copy is fetched in the background
SEERR_URL = os.environ.get("SEERR_URL", "").rstrip("/")
SEERR_API_KEY = os.environ.get("SEERR_API_KEY", "")
SEERR_MODE = os.environ.get("SEERR_MODE", "off").strip().lower()
if SEERR_MODE not in ("off", "request", "both"):
    SEERR_MODE = "off"
SEERR_IS4K = os.environ.get("SEERR_IS4K", "0").lower() in ("1", "true", "yes")
SEERR_TV_SEASONS = os.environ.get("SEERR_TV_SEASONS", "all")   # all | missing | "1,2"


def seerr_ready() -> bool:
    """Can we actually talk to Seerr? (module present + URL + API key)"""
    return bool(seerr_source is not None and SEERR_URL and SEERR_API_KEY)

RESOLVER_URL = os.environ.get("TELESTREAM_RESOLVER_URL", "")
STAGING = os.environ.get("TELESTREAM_STAGING", os.path.join(HOME, "media", "staging"))
MOVIES_DIR = os.environ.get("TELESTREAM_MOVIES_DIR", os.path.join(HOME, "media", "Movies"))
TV_DIR = os.environ.get("TELESTREAM_TV_DIR", os.path.join(HOME, "media", "TV Shows"))
BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8889"))

DEFAULT_EXT = os.environ.get("TELESTREAM_EXT", ".mkv")
RESOLVE_TIMEOUT = int(os.environ.get("TELESTREAM_RESOLVE_TIMEOUT", "30"))
DOWNLOAD_TIMEOUT = int(os.environ.get("TELESTREAM_DOWNLOAD_TIMEOUT", "7200"))
DOWNLOAD_CMD = os.environ.get("TELESTREAM_DOWNLOAD_CMD", "")

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
MAX_JOBS = int(os.environ.get("TELESTREAM_MAX_JOBS", "200"))


def log(msg: str) -> None:
    # stderr, not stdout: the CLI prints a job as JSON on stdout, so logging there
    # would corrupt it for anything piping the output (jq, cron, scripts). journald
    # captures both, so the systemd service is unaffected.
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def default_download_cmd(stream_url: str = "") -> str:
    """
    Pick a downloader we actually have. Placeholders {stream}/{out}/{headers} are
    substituted with shell-quoted values, so use them BARE (no extra quotes).

      yt-dlp  -- best: handles HLS/DASH, fragments and --add-header
      curl    -- plain progressive files from a file host
      ffmpeg  -- HLS/DASH remux when yt-dlp is missing (cannot send custom headers)
    """
    playlist = bool(re.search(r"\.(m3u8|mpd)(\?|$)", (stream_url or "").lower()))
    if shutil.which("yt-dlp"):
        return 'yt-dlp {headers} -f "bv*+ba/b" --merge-output-format mkv --restrict-filenames -o {out} {stream}'
    if playlist:
        return "ffmpeg -hide_banner -loglevel error -y -i {stream} -c copy {out}"
    if shutil.which("curl"):
        return "curl -fsSL --retry 3 --retry-delay 2 {headers} -o {out} {stream}"
    return "wget -q --tries=3 {headers} -O {out} {stream}"


def _tool_of(cmd: str) -> str:
    head = cmd.strip().split()[0] if cmd.strip() else ""
    return os.path.basename(head)


def header_flags(headers: dict, cmd: str) -> str:
    """Custom request headers (Fast Combo forwards some hosts' required headers)."""
    if not headers:
        return ""
    tool = _tool_of(cmd)
    pairs = [f"{k}: {v}" for k, v in headers.items()]
    if tool == "yt-dlp":
        return " ".join(f"--add-header {shlex.quote(p)}" for p in pairs)
    if tool == "curl":
        return " ".join(f"-H {shlex.quote(p)}" for p in pairs)
    if tool == "wget":
        return " ".join(f"--header={shlex.quote(p)}" for p in pairs)
    if pairs:
        log(f"  note: {_tool_of(cmd) or 'the downloader'} gets no custom headers "
            f"({len(pairs)} required by this host); set TELESTREAM_DOWNLOAD_CMD to yt-dlp if it fails")
    return ""


# --------------------------------------------------------------------------- naming

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean(name: str) -> str:
    """Make a string safe to use as a file/directory name."""
    name = _ILLEGAL.sub(" ", name or "").strip()
    name = re.sub(r"\s+", " ", name)
    return name or "Unknown"


def sxxexx(episode: str) -> str:
    """Normalise '1x02', 's1e2', 'S01E02' -> 'S01E02'."""
    m = re.search(r"(\d{1,2})\s*[xe]\s*(\d{1,3})", (episode or "").lower())
    if not m:
        return ""
    return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"


def destination(kind: str, title: str, year, episode: str, dest_override: str | None):
    """Return (directory, basename) using Plex naming conventions."""
    if dest_override:
        return os.path.abspath(os.path.expanduser(dest_override)), clean(title)

    if kind in ("show", "series"):
        code = sxxexx(episode)
        show_dir = os.path.join(TV_DIR, clean(title))
        if code:
            season_dir = os.path.join(show_dir, f"Season {code[1:3]}")
            base = f"{clean(title)} - {code}"
        else:
            season_dir = show_dir
            base = clean(title)
        return season_dir, base

    folder = f"{clean(title)} ({year})" if year else clean(title)
    return os.path.join(MOVIES_DIR, folder), folder


# --------------------------------------------------------------------------- fetch

def resolve_stream(url: str, title: str) -> str:
    """Turn a Telestream page/id/stream URL into a direct media URL."""
    if not RESOLVER_URL:
        return url
    if RESOLVER_URL.startswith("exec:"):
        cmd = RESOLVER_URL[5:].format(url=shlex.quote(url), title=shlex.quote(title))
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=RESOLVE_TIMEOUT)
        if out.returncode != 0:
            raise RuntimeError(f"resolver command failed: {out.stderr.strip()[:400]}")
        return out.stdout.strip().splitlines()[-1].strip()

    api = RESOLVER_URL.format(url=urllib.parse.quote(url, safe=""), title=urllib.parse.quote(title))
    with urllib.request.urlopen(api, timeout=RESOLVE_TIMEOUT) as resp:  # nosec - local resolver
        body = resp.read().decode("utf-8", "replace").strip()

    # Accept JSON ({...}) with a common stream-ish key, or a bare URL.
    if body.startswith("{") or body.startswith("["):
        data = json.loads(body)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("stream", "url", "file", "src", "videoUrl", "playUrl", "hls", "m3u8"):
                value = item.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
        raise RuntimeError(f"no stream URL found in resolver response: {body[:300]}")
    return body


def pick_extension(stream_url: str) -> str:
    path = urllib.parse.urlparse(stream_url).path.lower()
    for ext in (".mkv", ".mp4", ".m4v", ".avi", ".webm", ".ts", ".mov"):
        if path.endswith(ext):
            return ext
    return DEFAULT_EXT  # .m3u8 and friends get remuxed into a container


def download(stream_url: str, out_path: str, headers: dict | None = None) -> None:
    cmd_template = DOWNLOAD_CMD or default_download_cmd(stream_url)
    cmd = cmd_template.format(
        stream=shlex.quote(stream_url),
        out=shlex.quote(out_path),
        headers=header_flags(headers or {}, cmd_template),
    )
    log(f"  exec: {cmd}")
    proc = subprocess.run(cmd, shell=True, timeout=DOWNLOAD_TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"download command exited {proc.returncode}")
    if not os.path.exists(out_path):
        raise RuntimeError(f"download produced no file at {out_path}")


# ------------------------------------------------------- is it actually video?

# Web pages saved with a .mkv extension are the classic cause of Plex error s1001:
# the filename matches so the title appears in the library, but there is nothing
# playable inside. Catch it here instead of letting Plex discover it.
_HTML_MARKERS = (
    b"<!doctype html", b"<html", b"<head", b"<script", b"<?xml",
    b'"error"', b'"errors"', b"cloudflare", b"access denied", b"forbidden",
    b"not found", b"captcha", b"please enable javascript", b"just a moment",
)
def sniff_html(data: bytes) -> str | None:
    """
    Return a marker if these bytes are a web page / JSON error rather than a video, else
    None. Used both after a download and BEFORE a play-through response is committed, so
    a captcha wall never reaches Plex as "media" (which is what produces error s1001).
    """
    head = (data or b"")[:2048].lower()
    hit = next((m for m in _HTML_MARKERS if m in head), None)
    return hit.decode() if hit else None


MIN_BYTES = int(os.environ.get("TELESTREAM_MIN_BYTES", str(20 * 1024 * 1024)))
MIN_DURATION = float(os.environ.get("TELESTREAM_MIN_DURATION", "30"))
VERIFY_MEDIA = os.environ.get("TELESTREAM_VERIFY_MEDIA", "1").lower() not in ("0", "false", "no")


def validate_media(path: str, stream_url: str = "") -> dict:
    """
    Make sure what we downloaded is real, playable video. Raises on anything that
    would show up in Plex as a title that refuses to play (error s1001).

    Checks, cheapest first:
      1. big enough to be an episode/movie
      2. not an HTML/JSON error page wearing a video extension
      3. ffprobe: has a video or audio stream, and is not a truncated stub
    """
    size = os.path.getsize(path)
    if size < MIN_BYTES:
        raise RuntimeError(
            f"downloaded only {size} bytes (minimum {MIN_BYTES}); the host most likely "
            f"returned an error page or the link died immediately"
        )

    with open(path, "rb") as fh:
        head = fh.read(2048)
    marker = sniff_html(head)
    if marker:
        snippet = head[:120].decode("utf-8", "replace").strip()
        raise RuntimeError(
            f"downloaded a web page, not a video (found {marker!r}: {snippet!r}). "
            f"The host is behind a login/captcha/403 wall -- trying the next stream"
        )

    info = {"size_bytes": size}
    ffprobe = shutil.which("ffprobe")
    if not (VERIFY_MEDIA and ffprobe):
        if VERIFY_MEDIA and not ffprobe:
            log("  note: ffprobe missing (sudo apt install ffmpeg) -- skipping deep media check")
        return info

    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, timeout=120,
        )
        data = json.loads(out.stdout or "{}")
    except Exception as exc:  # noqa: BLE001 - a probe failure must not lose a good file
        log(f"  note: ffprobe could not run ({exc}); accepting the file")
        return info

    streams = data.get("streams") or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    fmt = (data.get("format") or {})
    duration = float(fmt.get("duration") or 0)

    if not video and not audio:
        raise RuntimeError(
            f"ffprobe found no video and no audio stream (format={fmt.get('format_name')}). "
            f"This file would appear in Plex but fail with s1001 -- trying the next stream"
        )
    if duration and duration < MIN_DURATION:
        raise RuntimeError(
            f"file is only {duration:.0f}s long (minimum {MIN_DURATION:.0f}s) -- truncated download"
        )

    v = video[0] if video else {}
    info.update({
        "video_codec": v.get("codec_name") or "",
        "audio_codec": (audio[0].get("codec_name") if audio else "") or "",
        "width": v.get("width") or 0,
        "height": v.get("height") or 0,
        "duration_seconds": round(duration),
        "container": fmt.get("format_name") or "",
        "verified": True,
    })
    log(f"  verified: {info.get('width')}x{info.get('height')} {info.get('video_codec')} "
        f"/ {info.get('audio_codec')} · {duration / 60:.0f} min")
    return info


# --------------------------------------------------------------------------- jobs

# =============================================================================
#  Play-through: scrape the link, cache it, let Plex play it -- no download
# =============================================================================
# Instead of saving a permanent copy, the library gets a tiny .strm file pointing at this
# bridge. When Plex plays it, the bridge asks your addons for a FRESH link right then,
# opens it with whatever headers the host demands, and streams the bytes through
# (Range-aware) while keeping a capped cache on disk. So:
#
#   * nothing is downloaded up front -- a title costs a few hundred bytes in the library
#   * links never go stale, because they are scraped at play time, not at add time
#   * hosts that need special headers work, which a bare .strm URL cannot do
#   * the cache is capped and self-evicting, so it cannot eat your disk
#
# THE ONE THING THAT BREAKS IT: the .strm URL must be reachable from the CLIENT, not just
# from the server. A .strm containing 127.0.0.1 gives every remote device Plex error
# s1001. Set TELESTREAM_PUBLIC_BASE_URL to the address your clients actually use (your LAN
# IP, or your tunnel/Tailscale URL). `install.sh doctor` flags .strm files that point at
# loopback.

PLAY: dict[str, dict] = {}
PLAY_LOCK = threading.Lock()
MAX_PLAYS = int(os.environ.get("TELESTREAM_MAX_PLAYS", "500"))

# The play table MUST survive a restart, and it did not. Keys are random and used to live
# only in RAM, so a reboot -- or the `systemctl restart mwatcher-bridge` that the installer
# itself tells you to run -- orphaned every .strm already sitting in the library. Plex then
# gets a 404 from a pointer that looks perfectly valid, which presents exactly like s1001.
PLAY_FILE = os.environ.get(
    "TELESTREAM_PLAY_FILE",
    os.path.join(os.path.expanduser("~"), ".local", "share", "mwatcher", "plays.json"))

CACHE_DIR = os.environ.get("TELESTREAM_CACHE_DIR", os.path.join(HOME, "media", "cache"))
CACHE_MAX_BYTES = int(float(os.environ.get("TELESTREAM_CACHE_MAX_GB", "20")) * 1024 ** 3)
CACHE_ENABLED = os.environ.get("TELESTREAM_CACHE", "1").lower() not in ("0", "false", "no")
RESOLVE_TTL = float(os.environ.get("TELESTREAM_RESOLVE_TTL", "300"))
PLAY_TIMEOUT = float(os.environ.get("TELESTREAM_PLAY_TIMEOUT", "30"))
PUBLIC_BASE_URL = os.environ.get("TELESTREAM_PUBLIC_BASE_URL", "").rstrip("/")
DEFAULT_ACTION = os.environ.get("TELESTREAM_ACTION", "").strip().lower()
CHUNK = 256 * 1024
ACTIONS = ("stream", "strm", "seerr", "both")


def lan_ip() -> str:
    """The address this box uses to reach the internet -- what LAN clients should use."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("1.1.1.1", 80))   # nothing is sent; this only picks the route
            return probe.getsockname()[0]
        finally:
            probe.close()
    except OSError:
        return "127.0.0.1"


def play_base_url() -> str:
    """Base URL written into .strm files. It must be reachable from the CLIENT."""
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    host = BRIDGE_HOST if BRIDGE_HOST not in ("", "0.0.0.0") else ""
    if not host or host in ("127.0.0.1", "localhost"):
        host = lan_ip()
    return f"http://{host}:{BRIDGE_PORT}"


def play_save() -> None:
    """Persist the play table atomically.

    Candidates are deliberately NOT written: addon links expire within minutes, so the first
    play after a restart re-scrapes anyway. Only the payload is needed to do that.
    """
    try:
        with PLAY_LOCK:
            data = {k: {"payload": e.get("payload") or {}, "created": e.get("created", 0),
                        "hits": e.get("hits", 0)} for k, e in PLAY.items()}
        parent = os.path.dirname(PLAY_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = PLAY_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "plays": data}, fh)
        os.replace(tmp, PLAY_FILE)
    except (OSError, TypeError, ValueError) as exc:
        log(f"could not save the play table to {PLAY_FILE}: {exc}")


def play_load() -> int:
    """Restore the play table. Called at import, so a one-shot CLI run cannot overwrite the
    table a running server depends on -- it adds to it instead."""
    try:
        with open(PLAY_FILE, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, ValueError):
        return 0
    plays = blob.get("plays") if isinstance(blob, dict) else None
    if not isinstance(plays, dict):
        return 0
    restored = 0
    with PLAY_LOCK:
        for key, e in plays.items():
            if not isinstance(e, dict) or not isinstance(e.get("payload"), dict):
                continue
            if key in PLAY:
                continue
            try:
                created = float(e.get("created") or time.time())
                hits = int(e.get("hits") or 0)
            except (TypeError, ValueError):
                created, hits = time.time(), 0
            PLAY[key] = {"payload": e["payload"], "created": created, "resolved": 0.0,
                         "candidates": [], "plan": {}, "hits": hits}
            restored += 1
    return restored


def new_play_key(payload: dict) -> str:
    key = uuid.uuid4().hex[:10]
    with PLAY_LOCK:
        PLAY[key] = {"payload": payload, "created": time.time(), "resolved": 0.0,
                     "candidates": [], "plan": {}, "hits": 0}
        if len(PLAY) > MAX_PLAYS:
            for stale in sorted(PLAY, key=lambda k: PLAY[k]["created"])[: len(PLAY) - MAX_PLAYS]:
                PLAY.pop(stale, None)
    play_save()          # outside the lock: play_save takes it
    return key


def play_entry(key: str) -> dict:
    with PLAY_LOCK:
        entry = PLAY.get(key)
    if not entry:
        raise KeyError(key)
    return entry


def resolve_for_play(key: str) -> list:
    """
    Fresh addon links for a play key. Re-scraped whenever the last scrape is older than
    RESOLVE_TTL seconds, because addon links expire -- that is the whole reason the
    resolution happens at play time instead of at add time.
    """
    entry = play_entry(key)
    now = time.time()
    if entry["candidates"] and (now - entry["resolved"]) < RESOLVE_TTL:
        return entry["candidates"]
    plan = fastcombo_plan(entry["payload"])
    slim = {k: plan.get(k) for k in ("imdb", "stype", "sid", "title", "year", "kind",
                                     "episode", "season", "prefer", "total", "downloadable")}
    with PLAY_LOCK:
        entry["candidates"] = plan["ordered"]
        entry["plan"] = slim
        entry["resolved"] = time.time()
        entry["hits"] = entry.get("hits", 0) + 1
    return plan["ordered"]


def cache_path(key: str, final: bool = True) -> str:
    return os.path.join(CACHE_DIR, key + (".mkv" if final else ".part"))


def evict_cache() -> int:
    """Drop the oldest finished cache files until we are back under the cap."""
    if not CACHE_ENABLED:
        return 0
    try:
        names = os.listdir(CACHE_DIR)
    except OSError:
        return 0
    files = []
    for name in names:
        path = os.path.join(CACHE_DIR, name)
        if not os.path.isfile(path) or name.endswith(".part"):
            continue                        # never evict a stream still in progress
        try:
            files.append((os.path.getmtime(path), os.path.getsize(path), path))
        except OSError:
            pass
    total = sum(size for _, size, _ in files)
    if total <= CACHE_MAX_BYTES:
        return 0
    removed = 0
    for _, size, path in sorted(files):     # oldest first
        if total <= CACHE_MAX_BYTES:
            break
        try:
            os.remove(path)
            total -= size
            removed += 1
        except OSError:
            pass
    if removed:
        log(f"cache: evicted {removed} file(s) to stay under "
            f"{CACHE_MAX_BYTES / 1024 ** 3:.1f} GB (now {total / 1024 ** 3:.2f} GB)")
    return removed


def cache_stats() -> dict:
    items = []
    try:
        for name in sorted(os.listdir(CACHE_DIR)):
            path = os.path.join(CACHE_DIR, name)
            if os.path.isfile(path):
                items.append({"name": name, "bytes": os.path.getsize(path),
                              "age_seconds": int(time.time() - os.path.getmtime(path)),
                              "complete": not name.endswith(".part")})
    except OSError:
        pass
    used = sum(i["bytes"] for i in items)
    return {"cache_dir": CACHE_DIR, "enabled": CACHE_ENABLED,
            "max_gb": round(CACHE_MAX_BYTES / 1024 ** 3, 2),
            "used_gb": round(used / 1024 ** 3, 3), "files": len(items),
            "percent_full": round(100 * used / CACHE_MAX_BYTES, 1) if CACHE_MAX_BYTES else 0.0,
            "resolve_ttl_seconds": RESOLVE_TTL, "items": items[-20:]}


def play_list() -> list[dict]:
    with PLAY_LOCK:
        out = []
        for key, entry in PLAY.items():
            plan = entry.get("plan") or {}
            payload = entry.get("payload") or {}
            out.append({
                "key": key,
                "title": plan.get("title") or payload.get("title") or "",
                "year": plan.get("year") or payload.get("year") or "",
                "kind": plan.get("kind") or payload.get("kind") or "",
                "episode": plan.get("episode") or payload.get("episode") or "",
                "imdb": plan.get("imdb") or payload.get("imdb") or "",
                "play_url": f"{play_base_url()}/play/{key}.mkv",
                "cached": os.path.exists(cache_path(key, True)),
                "candidates": len(entry.get("candidates") or []),
                "created": entry["created"], "resolved": entry.get("resolved") or 0,
            })
    return sorted(out, key=lambda d: d["created"], reverse=True)


STRM_TARGET_RE = re.compile(r"/play/([0-9a-fA-F]{6,40})\.(?:mkv|mp4|webm|avi)$")
MOVIE_NAME_RE = re.compile(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)$")
EPISODE_NAME_RE = re.compile(r"^(?P<show>.+?)\s*-\s*S(?P<season>\d{1,2})E(?P<episode>\d{1,3})$",
                             re.IGNORECASE)


def parse_strm_path(path: str) -> dict:
    """Recover what a pointer was for, from the library path this bridge wrote it to.

    The naming is ours and deterministic, so this is reliable for anything we created:
        Movies/<Title> (<Year>)/<Title> (<Year>).strm
        TV Shows/<Show>/Season 01/<Show> - S01E02.strm
    """
    name = os.path.splitext(os.path.basename(path))[0]
    parent = os.path.basename(os.path.dirname(path))
    m = EPISODE_NAME_RE.match(name)
    if m:
        return {"title": m.group("show").strip(), "kind": "show", "year": "", "imdb": "",
                "episode": f"S{int(m.group('season')):02d}E{int(m.group('episode')):02d}"}
    m = MOVIE_NAME_RE.match(name)
    if m:
        return {"title": m.group("title").strip(), "kind": "movie", "year": m.group("year"),
                "imdb": "", "episode": ""}
    if parent.lower().startswith("season"):
        # An episode file whose name we do not recognise: the show folder still tells us.
        show = os.path.basename(os.path.dirname(os.path.dirname(path)))
        return {"title": show, "kind": "show", "year": "", "imdb": "", "episode": ""}
    return {"title": name, "kind": "movie", "year": "", "imdb": "", "episode": ""}


def repoint_library(dry_run: bool = False) -> int:
    """Re-create every play-through pointer whose key this bridge no longer knows.

    Pointers written before the play table was persisted are orphaned: the .strm looks
    perfectly healthy, Plex asks for it, and gets a 404. Nothing on disk says which are
    dead, so walk the library, keep the ones pointing at us, and re-add any whose key is
    gone. Re-adding writes a fresh .strm with a key that will now survive a restart.
    """
    mine: list[str] = []
    dead: list[str] = []
    fixed, failed, skipped = 0, 0, []
    for root_dir in (MOVIES_DIR, TV_DIR):
        if not os.path.isdir(root_dir):
            continue
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for fn in sorted(filenames):
                if not fn.lower().endswith(".strm"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        target = fh.read(600).strip()
                except OSError:
                    skipped.append(path)
                    continue
                m = STRM_TARGET_RE.search(target)
                if not m:
                    continue                     # a hand-written pointer to somewhere else
                mine.append(path)
                key = m.group(1)
                with PLAY_LOCK:
                    known = key in PLAY
                if known:
                    continue
                dead.append(path)
                if dry_run:
                    continue
                payload = parse_strm_path(path)
                try:
                    res = add_strm(payload)
                except Exception as exc:         # noqa: BLE001 - report and carry on
                    failed += 1
                    log(f"repoint FAILED {path}: {exc}")
                    continue
                fixed += 1
                new_path = res.get("strm") or ""
                log(f"repointed {payload.get('title')}: {key} -> {res.get('key')}")
                # If the recovered title produced a different path, the old file is a stray
                # duplicate that Plex would still list. Remove it.
                if new_path and os.path.abspath(new_path) != os.path.abspath(path):
                    try:
                        os.remove(path)
                        log(f"  removed the stale pointer {path}")
                    except OSError:
                        warn = f"  could not remove the stale pointer {path}"
                        log(warn)
    report = {
        "play_file": PLAY_FILE,
        "known_keys": len(PLAY),
        "strm_files_pointing_at_this_bridge": len(mine),
        "orphaned": len(dead),
        "recreated": fixed,
        "failed": failed,
        "unreadable": len(skipped),
        "dry_run": dry_run,
    }
    if dead:
        report["orphaned_paths"] = dead[:50]
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


def add_strm(payload: dict) -> dict:
    """
    Put a title in the library WITHOUT downloading it: resolve once now (so a title with
    no working link fails immediately instead of at play time), then write a .strm that
    points at this bridge. Plex reads the pointer, asks us, and we scrape + stream.
    """
    key = new_play_key(payload)
    try:
        candidates = resolve_for_play(key)
    except Exception:
        with PLAY_LOCK:
            PLAY.pop(key, None)
        play_save()
        raise
    entry = play_entry(key)
    plan = entry["plan"]
    kind = plan.get("kind") or payload.get("kind") or "movie"
    title = plan.get("title") or payload.get("title") or key
    year = plan.get("year") or payload.get("year") or ""
    episode = plan.get("episode") or payload.get("episode") or ""
    target_dir, base = destination(kind, title, year, episode, payload.get("dest"))
    os.makedirs(target_dir, exist_ok=True)

    override = (payload.get("public_url") or "").strip().rstrip("/")
    root = override or play_base_url()
    url = f"{root}/play/{key}.mkv"
    path = os.path.join(target_dir, base + ".strm")
    # The temp name has to be unique per add, not per title. Two adds of the same title at
    # once (easy: two dashboard clicks, or a re-run while one is in flight) used to share
    # "<Title>.strm.tmp"; the first os.replace moved it away and the second died with
    # [Errno 2] No such file or directory: '...strm.tmp'. The key is already random.
    tmp = f"{path}.{key}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(url + "\n")
        os.chmod(tmp, 0o644)                 # the plex user must be able to read it
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)                   # never leave a stray .tmp for Plex to scan
        except OSError:
            pass
        raise
    log(f"strm: {path} -> {url} ({len(candidates)} live candidate link(s))")
    return {
        "key": key, "strm": path, "play_url": url, "title": title, "year": year,
        "kind": kind, "episode": episode, "imdb": plan.get("imdb") or "",
        "candidates": len(candidates),
        "picked": candidates[0].summary if candidates else "",
        "bytes_written": len(url) + 1,
        "downloaded_bytes": 0,
        "warning": ("the .strm points at loopback -- only THIS machine can play it. Set "
                    "TELESTREAM_PUBLIC_BASE_URL to an address your Plex clients can reach."
                    if ("127.0.0.1" in url or "localhost" in url) else ""),
    }


def run_strm_job(job_id: str, payload: dict, label: str = "strm") -> None:
    """The no-download job: scrape, write the .strm, done in about a second."""
    try:
        update_job(job_id, status="searching", action=label)
        info = add_strm(payload)
        update_job(job_id, status="done", action=label, file=info["strm"], strm=info,
                   source={"mode": "strm", "candidates": info["candidates"],
                           "host": play_base_url()})
        if info.get("warning"):
            update_job(job_id, warning=info["warning"])
    except Exception as exc:  # noqa: BLE001
        log(f"job {job_id}: strm FAILED - {exc}")
        update_job(job_id, status="failed", action=label, error=str(exc))


def new_job(payload: dict) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "status": "queued",
        "payload": payload,
        "created": time.time(),
        "updated": time.time(),
        "error": None,
        "file": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
        # crude ring buffer so memory does not grow forever
        if len(JOBS) > MAX_JOBS:
            oldest = sorted(JOBS.values(), key=lambda j: j["created"])[: len(JOBS) - MAX_JOBS]
            for stale in oldest:
                JOBS.pop(stale["id"], None)
    return job_id


def update_job(job_id: str, **fields) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated"] = time.time()


def parse_episode_numbers(episode: str, season) -> tuple[int, int]:
    """('S01E02'|'1x02'|'2', 3) -> (season, episode) ints."""
    code = sxxexx(episode)
    if code:
        return int(code[1:3]), int(code[4:])
    m = re.search(r"(\d+)", str(episode or ""))
    return int(season or 1), int(m.group(1)) if m else 1


def fastcombo_plan(payload: dict) -> dict:
    """
    Ask your Stremio addons (through Fast Combo) for a title/episode and decide which
    single stream to fetch. Fast Combo has already filtered and ranked; we keep the best
    link that is actually downloadable and hold the rest as fallbacks.

    Accepts: imdb (tt...) and/or title, kind (movie|show), year, season, episode.
    """
    if stremio_source is None:
        raise RuntimeError("stremio_source.py is missing next to this script")
    if not FASTCOMBO_ACCESS_KEY:
        raise RuntimeError(
            "FASTCOMBO_ACCESS_KEY is not set (the secret part of your Fast Combo link). "
            f"Looked in the environment{f' and {ENV_FILE}' if ENV_FILE else ''}; the file is "
            "normally ~/.config/mwatcher/bridge.env. Repair it with "
            "`sudo bash install.sh`, or set FASTCOMBO_ACCESS_KEY=... for this one run."
        )

    imdb = str(payload.get("imdb") or "").strip()
    title = str(payload.get("title") or "").strip()
    kind = str(payload.get("kind") or "").strip().lower()
    year = str(payload.get("year") or "").strip()

    # --- title text -> IMDb id (Cinemeta, the same free addon Fast Combo uses) --------
    if not imdb and title:
        matches = stremio_source.search_titles(title, CINEMETA_URL)
        if not matches:
            raise RuntimeError(f"no IMDb match for {title!r} via Cinemeta ({CINEMETA_URL})")
        want = "series" if kind in ("show", "series") else ("movie" if kind == "movie" else None)
        best = None
        for m in matches:                      # 1) right type AND right year
            if year and m.get("year") and year in m["year"] and (not want or m["type"] == want):
                best = m
                break
        if not best:                           # 2) right type
            best = next((m for m in matches if not want or m["type"] == want), matches[0])
        imdb = best["id"]
        title = title or best.get("name", "")
        year = year or (best.get("year") or "")[:4]
        kind = kind or ("show" if best["type"] == "series" else "movie")
        log(f"  matched {title!r} -> {imdb} ({best.get('type')}, {best.get('year')})")
    if not imdb:
        raise RuntimeError("need 'imdb' (tt...) or a 'title' to search for")

    # --- canonical metadata so the Plex filename matches properly --------------------
    info = {}
    try:
        info = stremio_source.title_info(imdb, CINEMETA_URL)
    except Exception as exc:  # noqa: BLE001 - offline is fine, fall back to what we were given
        log(f"  Cinemeta lookup unavailable ({exc}); using supplied title/year")
    if info.get("ok"):
        title = info.get("name") or title
        year = year or info.get("year") or ""
        kind = kind or ("show" if info.get("type") == "series" else "movie")

    kind = kind or "movie"
    stype = "series" if kind in ("show", "series") else "movie"
    season, episode = parse_episode_numbers(payload.get("episode"), payload.get("season"))
    sid = stremio_source.episode_id(imdb, season, episode) if stype == "series" else imdb
    ep_code = f"S{season:02d}E{episode:02d}" if stype == "series" else ""

    prefer = str(payload.get("prefer") or FASTCOMBO_PREFER)
    candidates = stremio_source.fetch_streams(
        FASTCOMBO_BASE_URL, FASTCOMBO_ACCESS_KEY, stype, sid, FASTCOMBO_TOKEN, FASTCOMBO_TIMEOUT
    )
    best, ordered = stremio_source.pick(candidates, prefer, FASTCOMBO_MAX_FALLBACKS)
    log(f"  Fast Combo: {len(candidates)} streams, {len(ordered)} downloadable, prefer={prefer}")
    if not candidates:
        raise RuntimeError(f"Fast Combo returned no streams for {stype}/{sid} "
                           f"(are your addons switched on at {FASTCOMBO_BASE_URL}?)")
    if not best:
        raise RuntimeError(f"Fast Combo returned {len(candidates)} streams but none are directly "
                           f"downloadable (torrent/debrid-only links need a debrid service)")

    return {
        "imdb": imdb, "stype": stype, "sid": sid, "title": title, "year": year,
        "kind": kind, "episode": ep_code, "season": season, "prefer": prefer,
        "total": len(candidates), "downloadable": len(ordered),
        "best": best, "ordered": ordered, "candidates": candidates,
        "meta_ok": bool(info.get("ok")),
    }


def run_job(job_id: str, payload: dict) -> None:
    url = (payload.get("url") or "").strip()
    kind = (payload.get("kind") or "movie").strip().lower()
    year = payload.get("year") or ""
    episode = payload.get("episode") or ""
    title = (payload.get("title") or "").strip()
    part = None

    try:
        # ---- build the list of things to try, best first ----------------------------
        attempts: list[dict] = []
        if url:
            # Direct/Telestream mode: one link (optionally via the local resolver).
            if not title:
                raise RuntimeError("'title' is required when you pass a direct 'url'")
            update_job(job_id, status="resolving")
            log(f"job {job_id}: resolving '{title}' <- {url}")
            stream_url = resolve_stream(url, title)
            log(f"job {job_id}: stream = {stream_url}")
            attempts.append({"url": stream_url, "headers": {}, "info": {"mode": "direct url"}})
        else:
            # Fast Combo mode: ask all your addons, take the single best stream.
            if not (payload.get("imdb") or title):
                raise RuntimeError("pass 'url' (direct link) or 'imdb'/'title' (Fast Combo lookup)")
            update_job(job_id, status="searching")
            log(f"job {job_id}: asking Fast Combo for '{title or payload.get('imdb')}'")
            plan = fastcombo_plan(payload)
            title, year, kind, episode = plan["title"], plan["year"], plan["kind"], plan["episode"]
            update_job(
                job_id, imdb=plan["imdb"], stype=plan["stype"], sid=plan["sid"],
                prefer=plan["prefer"], total_streams=plan["total"],
                downloadable=plan["downloadable"], meta_ok=plan["meta_ok"],
            )
            for c in plan["ordered"]:
                attempts.append({
                    "url": c.url,
                    "headers": c.headers,
                    "info": {
                        "mode": "fastcombo", "rank": c.index, "resolution": c.res_label,
                        "size_bytes": c.size_bytes, "bitrate_mbps": c.bitrate_mbps,
                        "codec": c.codec, "hdr": c.hdr, "source": c.source,
                        "host": c.host, "addon": c.addon, "status": c.status,
                        "start_seconds": c.start_seconds, "filename": c.filename,
                    },
                })
            log(f"job {job_id}: best = {plan['best'].summary}")

        # ---- where it lands in the library ------------------------------------------
        target_dir, base = destination(kind, title, year, episode, payload.get("dest"))
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(STAGING, exist_ok=True)

        ext = pick_extension(attempts[0]["url"])
        final_path = os.path.join(target_dir, base + ext)
        if os.path.exists(final_path):
            log(f"job {job_id}: already present -> {final_path}")
            update_job(job_id, status="done", file=final_path, skipped=True)
            return

        # ---- download, failing over to the next-best stream -------------------------
        tried, errors = [], []
        media_info: dict = {}
        for n, attempt in enumerate(attempts, start=1):
            stream_url = attempt["url"]
            part = os.path.join(STAGING, f"{job_id}-{base}.part{ext}")
            update_job(job_id, status="downloading", stream=stream_url,
                       target=final_path, source=attempt["info"], attempt=n,
                       attempts_total=len(attempts), tried=tried)
            log(f"job {job_id}: attempt {n}/{len(attempts)} -> {part}")
            try:
                download(stream_url, part, attempt.get("headers"))
                # Verify it is real video BEFORE it lands in the library -- a bad file
                # in Plex shows up as a title that fails with "s1001 (Network)".
                media_info = validate_media(part, stream_url)
            except Exception as exc:  # noqa: BLE001 - try the next candidate
                if part and os.path.exists(part):
                    try:
                        os.remove(part)
                    except OSError:
                        pass
                part = None
                errors.append(f"attempt {n}: {exc}")
                tried.append({"rank": attempt["info"].get("rank", n), "url": stream_url,
                              "error": str(exc)})
                log(f"job {job_id}: attempt {n} failed ({exc})")
                continue

            try:
                os.chmod(part, 0o644)  # readable by the plex user
            except OSError:
                pass
            shutil.move(part, final_path)
            part = None
            log(f"job {job_id}: done -> {final_path}")
            update_job(job_id, status="done", file=final_path, source=attempt["info"],
                       media=media_info, attempt=n, tried=tried)
            return

        raise RuntimeError("every stream failed: " + " | ".join(errors[-3:]))
    except Exception as exc:  # noqa: BLE001 - report everything back to the caller
        if part and os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
        log(f"job {job_id}: FAILED - {exc}")
        update_job(job_id, status="failed", error=str(exc))


def run_seerr_job(job_id: str, payload: dict, terminal: bool = True) -> dict | None:
    """
    Ask Seerr to get this title -- Radarr/Sonarr then download it to your server, so no
    debrid service and no bridge-side download is involved.

    terminal=True  -> this is the whole job; set the final status.
    terminal=False -> "both" mode: record the outcome on the job and let the stream
                      download continue even if Seerr is down or unhappy.
    """
    try:
        if seerr_source is None:
            raise RuntimeError("seerr_source.py is not importable (is scripts/ next to the bridge?)")
        if not seerr_ready():
            raise RuntimeError(
                "Seerr is not configured. Set SEERR_URL and SEERR_API_KEY in "
                "~/.config/mwatcher/bridge.env -- the key is in Seerr -> Settings -> General.")
        title = (payload.get("title") or "").strip()
        imdb = (payload.get("imdb") or "").strip()
        if not (title or imdb):
            raise RuntimeError("need 'title' or 'imdb' to request a title in Seerr")
        kind = (payload.get("kind") or "").strip().lower() or None
        if kind == "series":
            kind = "tv"
        # Seerr wants season numbers for TV; accept the bridge's "season" or an explicit list.
        seasons = payload.get("seasons")
        if not seasons and payload.get("season"):
            try:
                seasons = [int(payload["season"])]
            except (TypeError, ValueError):
                seasons = None
        is4k = payload.get("is4k")
        if is4k is None:
            is4k = SEERR_IS4K or None
        update_job(job_id, status="searching", action="seerr")
        log(f"job {job_id}: asking Seerr for '{title or imdb}'")
        result = seerr_source.request_title(
            title=title, year=payload.get("year"), imdb=imdb, kind=kind,
            seasons=seasons, is4k=is4k, base_url=SEERR_URL, api_key=SEERR_API_KEY)
        log(f"job {job_id}: seerr -> {result.get('title')} "
            f"tmdb={result.get('tmdb_id')} {result.get('status_label')}")
        if terminal:
            update_job(job_id, action="seerr", seerr=result, status="done",
                       skipped=bool(result.get("already_available")),
                       file=None)
        else:
            update_job(job_id, seerr=result)
        return result
    except Exception as exc:  # noqa: BLE001 - surface it on the job/dashboard
        log(f"job {job_id}: seerr FAILED - {exc}")
        if terminal:
            update_job(job_id, action="seerr", status="failed", error=str(exc))
        else:
            update_job(job_id, seerr_error=str(exc))
        return None


def instant_runner(action: str) -> str:
    """Which no-Seerr path gives you the picture fastest: a download or a play-through?"""
    return "strm" if action == "strm" or DEFAULT_ACTION == "strm" else "stream"


def dispatch_job(job_id: str, payload: dict, action: str) -> None:
    """Route a job: download it, point at it (no download), request it, or request+play."""
    if action == "seerr":
        run_seerr_job(job_id, payload)
        return
    if action == "strm":
        run_strm_job(job_id, payload)
        return
    if action == "both":
        # Request first: it is the cheap call, and it is the one that gets you a permanent
        # copy. If Seerr is unavailable we say so on the job but still make it watchable.
        run_seerr_job(job_id, payload, terminal=False)
        update_job(job_id, action="both", status="queued")
        if instant_runner("both") == "strm":
            run_strm_job(job_id, payload, label="both")   # no download: play through
        else:
            run_job(job_id, payload)
        update_job(job_id, action="both")
        return
    run_job(job_id, payload)


def resolve_action(payload: dict, action: str = "") -> str:
    """Per-request 'action' wins, then TELESTREAM_ACTION, then SEERR_MODE."""
    act = (action or payload.get("action") or "").strip().lower()
    if act in ACTIONS:
        return act
    if DEFAULT_ACTION in ACTIONS:
        return DEFAULT_ACTION
    if SEERR_MODE == "request":
        return "seerr"
    if SEERR_MODE == "both":
        return "both"
    return "stream"


def enqueue(payload: dict, action: str = "") -> str:
    job_id = new_job(payload)
    act = resolve_action(payload, action)
    payload = {**payload, "action": act}
    update_job(job_id, action=act)
    threading.Thread(target=dispatch_job, args=(job_id, payload, act), daemon=True).start()
    return job_id


def dashboard_html() -> str:
    """Self-contained control panel: search a title, see the ranked streams, fetch the best."""
    e = html.escape
    fc_ready = bool(FASTCOMBO_BASE_URL and FASTCOMBO_ACCESS_KEY)
    rows = {
        "Fast Combo": (f"{FASTCOMBO_BASE_URL} · key {'set' if FASTCOMBO_ACCESS_KEY else 'MISSING'}"
                       if fc_ready else "not configured"),
        "Ranking": f"prefer={FASTCOMBO_PREFER} · up to {FASTCOMBO_MAX_FALLBACKS} fallbacks",
        "Title search": CINEMETA_URL or "(Cinemeta)",
        "Play-through": (f"{play_base_url()}/play/&lt;key&gt;.mkv · cache "
                         f"{CACHE_DIR} ({CACHE_MAX_BYTES / 1024 ** 3:.0f} GB cap)"),
        "Staging": STAGING,
        "Movies library": MOVIES_DIR,
        "TV library": TV_DIR,
        "Downloader": _tool_of(DOWNLOAD_CMD or default_download_cmd()),
        "Legacy resolver": RESOLVER_URL or "(off — Fast Combo is the source)",
        "Seerr": (f"{SEERR_URL} · key set · mode={SEERR_MODE}" if seerr_ready() else
                  ("not configured — set SEERR_URL + SEERR_API_KEY in bridge.env"
                   if seerr_source is not None else "unavailable (seerr_source.py missing)")),
    }
    cfg = "".join(
        f'<div class="cfg"><span>{e(k)}</span><code>{e(str(v))}</code></div>'
        for k, v in rows.items()
    )
    warn = "" if fc_ready else (
        '<p class="warn">Fast Combo is not configured yet. Set <code>FASTCOMBO_BASE_URL</code> and '
        '<code>FASTCOMBO_ACCESS_KEY</code>, or use the direct-URL form below.</p>')
    return (_PAGE.replace("{{CONFIG}}", cfg).replace("{{WARN}}", warn)
            .replace("{{SEERR}}", "true" if seerr_ready() else "false")
            .replace("{{SEERRURL}}", SEERR_URL or ""))


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mwatcher &middot; Stremio addons &rarr; Plex</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:#0d1117; color:#e6edf3; }
  .wrap { max-width:1000px; margin:0 auto; padding:24px 18px 60px; }
  h1 { font-size:22px; margin:0 0 2px; }
  .sub { color:#8b949e; margin:0 0 22px; font-size:14px; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%;
         background:#3fb950; margin-right:7px; box-shadow:0 0 8px #3fb950; }
  .card { background:#161b22; border:1px solid #21262d; border-radius:12px;
          padding:18px; margin-bottom:20px; }
  .card h2 { font-size:13px; text-transform:uppercase; letter-spacing:.08em;
             color:#8b949e; margin:0 0 14px; }
  .cfg { display:flex; gap:12px; padding:6px 0; border-bottom:1px dashed #21262d; font-size:13.5px; }
  .cfg:last-child { border-bottom:0; }
  .cfg span { flex:0 0 140px; color:#8b949e; }
  .cfg code { flex:1; word-break:break-all; color:#79c0ff; font-size:12.5px; }
  form { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  form.inline { grid-template-columns:1fr auto; }
  label { font-size:12.5px; color:#8b949e; display:block; margin-bottom:4px; }
  input,select { width:100%; padding:9px 11px; border-radius:8px; font-size:14px;
                 background:#0d1117; border:1px solid #30363d; color:#e6edf3; }
  input:focus,select:focus { outline:none; border-color:#58a6ff; }
  .full { grid-column:1 / -1; }
  button { padding:10px 14px; border:0; border-radius:8px; background:#238636; color:#fff;
           font-size:14px; font-weight:600; cursor:pointer; }
  button:hover { background:#2ea043; }
  button:disabled { background:#30363d; color:#8b949e; cursor:default; }
  button.ghost { background:#21262d; color:#e6edf3; }
  button.ghost:hover { background:#30363d; }
  button.sm { padding:5px 10px; font-size:12.5px; }
  table { width:100%; border-collapse:collapse; font-size:13.5px; }
  th,td { text-align:left; padding:9px 8px; border-bottom:1px solid #21262d; vertical-align:top; }
  th { color:#8b949e; font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:.05em; }
  td code { color:#79c0ff; font-size:12px; word-break:break-all; }
  .badge { padding:2px 9px; border-radius:20px; font-size:11.5px; font-weight:600; white-space:nowrap; }
  .queued,.resolving,.searching,.downloading { background:#1f2d3d; color:#79c0ff; }
  .done { background:#12261e; color:#3fb950; }
  .failed { background:#2d1618; color:#f85149; }
  .best { background:#12261e; color:#3fb950; }
  .skip { background:#21262d; color:#8b949e; }
  .fb { background:#1f2d3d; color:#79c0ff; }
  .empty { color:#8b949e; padding:16px 0; text-align:center; font-size:13.5px; }
  .note { font-size:12.5px; color:#8b949e; margin:10px 0 0; }
  .warn { background:#2d2410; border:1px solid #5c4a17; color:#e3b341; padding:10px 12px;
          border-radius:8px; font-size:13px; margin:0 0 14px; }
  .row { display:flex; gap:10px; align-items:center; justify-content:space-between;
         padding:9px 0; border-bottom:1px dashed #21262d; }
  .row:last-child { border-bottom:0; }
  .row .t { font-weight:600; }
  .row .m { color:#8b949e; font-size:12.5px; }
  .pill { display:inline-block; padding:1px 8px; border-radius:20px; background:#21262d;
          color:#8b949e; font-size:11.5px; margin-left:6px; }
  .hidden { display:none; }
  .toast { position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background:#161b22;
           border:1px solid #30363d; padding:10px 16px; border-radius:8px; font-size:13.5px;
           opacity:0; transition:opacity .2s; pointer-events:none; max-width:90vw; }
  .toast.show { opacity:1; }
</style>
</head>
<body>
<div class="wrap">
  <h1><span class="dot"></span>Mwatcher &mdash; Stremio addons &rarr; Plex</h1>
  <p class="sub">Search a title, let <b>Fast Combo</b> ask all your addons at once, then download the
     single best stream into your Plex library. API: <code>GET /search</code> &middot;
     <code>GET /streams</code> &middot; <code>POST /fetch</code> &middot; <code>GET /jobs</code>.</p>

  <div class="card">
    <h2>Server configuration</h2>
    {{WARN}}
    {{CONFIG}}
  </div>

  <div class="card">
    <h2>1 &middot; Find a title</h2>
    <form id="search" class="inline">
      <div><label>Search your addons' catalogues (Cinemeta)</label>
        <input name="q" placeholder="Dune, Breaking Bad, The Matrix&hellip;" autocomplete="off"></div>
      <div style="align-self:end"><button type="submit">Search</button></div>
    </form>
    <div id="results"></div>
  </div>

  <div class="card hidden" id="streamcard">
    <h2>2 &middot; Streams from your addons <span id="sinfo" class="pill"></span></h2>
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
      <label style="margin:0">Rank by
        <select id="prefer" style="width:auto;margin-left:6px">
          <option value="best">best (Fast Combo's order)</option>
          <option value="fastest">fastest start</option>
          <option value="smallest">smallest file</option>
          <option value="4kfirst">4K first</option>
          <option value="1080first">1080p first</option>
        </select>
      </label>
      <label style="margin:0">Season <input id="season" type="number" value="1" min="1" style="width:70px"></label>
      <label style="margin:0">Episode <input id="episode" type="number" value="1" min="1" style="width:70px"></label>
      <button class="ghost sm" id="reload" type="button">Re-query</button>
      <button class="ghost sm" id="reqseerr" type="button"
              title="Ask Seerr to have Radarr/Sonarr download this to your server (no debrid)">Request in Seerr</button>
      <span style="margin-left:auto;display:flex;gap:6px">
        <button class="ghost sm" id="addstrm" type="button"
                title="No download: add a pointer that scrapes a fresh link and streams it through the bridge cache">Add without downloading</button>
        <button class="sm" id="fetchbest" type="button">Fetch best into Plex</button>
      </span>
    </div>
    <table><thead><tr><th>Pick</th><th>Quality</th><th>Size</th><th>Speed</th><th>From</th><th></th></tr></thead>
      <tbody id="srows"></tbody></table>
    <div id="sempty" class="empty hidden">No streams.</div>
    <p class="note">Fast Combo has already removed CAM/TS copies, dead links, duplicates and files too big
      to stream smoothly. Rows marked <span class="badge skip">skip</span> are torrents &mdash; they need a
      debrid service, so the bridge cannot download them directly.</p>
  </div>

  <div class="card">
    <h2>Fetch directly (skip the search)</h2>
    <form id="direct">
      <div><label>IMDb id &mdash; or a direct stream URL</label>
        <input name="imdb" placeholder="tt1160419"></div>
      <div><label>Direct URL (optional, bypasses addons)</label>
        <input name="url" placeholder="http://127.0.0.1:8888/stream/tt1160419"></div>
      <div><label>Title</label><input name="title" placeholder="Dune"></div>
      <div><label>Year</label><input name="year" placeholder="2021"></div>
      <div><label>Kind</label><select name="kind">
        <option value="">auto</option><option value="movie">Movie</option><option value="show">TV show</option>
      </select></div>
      <div><label>Episode (S01E02)</label><input name="episode" placeholder="S01E02"></div>
      <div class="full"><button type="submit">Fetch into Plex</button></div>
    </form>
  </div>

  <div class="card">
    <h2>Jobs <span id="count" class="pill"></span></h2>
    <table><thead><tr><th>Status</th><th>Title</th><th>Source picked</th><th>Result / error</th><th>Updated</th></tr></thead>
      <tbody id="rows"></tbody></table>
    <div id="empty" class="empty">No jobs yet.</div>
  </div>
</div>
<div id="toast" class="toast"></div>

<script>
const $ = id => document.getElementById(id);
let chosen = null;   // the title picked from search results
const SEERR_ON = {{SEERR}};          // is Seerr configured? (injected by the bridge)
const SEERR_URL = "{{SEERRURL}}";

function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function ago(t){ const s=Math.max(0,(Date.now()/1000-t)|0); return s<60? s+'s ago' : (s/60|0)+'m ago'; }
function gb(b){ if(!b) return ''; return b>=1e9 ? (b/1e9).toFixed(2)+' GB' : Math.round(b/1e6)+' MB'; }
function ping(m){ const t=$('toast'); t.textContent=m; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2600); }
async function getJSON(u){ const r=await fetch(u); const d=await r.json(); if(!r.ok) throw new Error(d.error||r.status); return d; }

// ---- 1. search -------------------------------------------------------------------
$('search').addEventListener('submit', async ev=>{
  ev.preventDefault();
  const q = ev.target.q.value.trim(); if(!q) return;
  $('results').innerHTML = '<div class="empty">Searching&hellip;</div>';
  try{
    const d = await getJSON('/search?q='+encodeURIComponent(q));
    if(!d.metas.length){ $('results').innerHTML='<div class="empty">No matches.</div>'; return; }
    $('results').innerHTML = d.metas.map(m=>
      '<div class="row"><div><span class="t">'+esc(m.name)+'</span>'
      +'<span class="pill">'+esc(m.year||'?')+'</span>'
      +'<span class="pill">'+esc(m.type)+'</span>'
      +'<div class="m">'+esc(m.id)+'</div></div>'
      +'<span style="display:flex;gap:6px;flex-wrap:wrap">'
      +'<button class="ghost sm" data-act="streams" data-id="'+esc(m.id)+'" data-type="'+esc(m.type)+'" data-name="'
      +esc(m.name)+'" data-year="'+esc((m.year||'').slice(0,4))+'">Show streams</button>'
      +(SEERR_ON ? '<button class="ghost sm" data-act="request" data-id="'+esc(m.id)+'" data-type="'+esc(m.type)+'" data-name="'
      +esc(m.name)+'" data-year="'+esc((m.year||'').slice(0,4))+'" title="Download to my server via Seerr">Request</button>' : '')
      +'</span></div>'
    ).join('');
    $('results').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
      if(b.dataset.act==='request') return requestSeerr(b.dataset);
      select(b.dataset);
    }));
  }catch(e){ $('results').innerHTML='<div class="empty">Search failed: '+esc(e.message)+'</div>'; }
});

// ---- 2. streams ------------------------------------------------------------------
function select(d){
  chosen = { id:d.id, type:d.type==='series'?'show':'movie', name:d.name, year:d.year };
  $('streamcard').classList.remove('hidden');
  $('season').parentElement.style.display = chosen.type==='show' ? '' : 'none';
  $('episode').parentElement.style.display = chosen.type==='show' ? '' : 'none';
  $('sinfo').textContent = d.name+' ('+(d.year||'?')+')';
  loadStreams();
  $('streamcard').scrollIntoView({behavior:'smooth', block:'start'});
}
async function loadStreams(){
  if(!chosen) return;
  const stype = chosen.type==='show' ? 'series' : 'movie';
  let u = '/streams?type='+stype+'&id='+encodeURIComponent(chosen.id)
        + '&prefer='+encodeURIComponent($('prefer').value);
  if(stype==='series') u += '&season='+($('season').value||1)+'&episode='+($('episode').value||1);
  $('srows').innerHTML = '<tr><td colspan="6" class="empty">Asking all your addons&hellip;</td></tr>';
  try{
    const d = await getJSON(u);
    $('sinfo').textContent = chosen.name+' · '+d.total+' streams · '+d.downloadable+' downloadable';
    $('sempty').classList.toggle('hidden', d.streams.length>0);
    $('fetchbest').disabled = !d.streams.some(s=>s.best);
    $('srows').innerHTML = d.streams.map(s=>{
      const tag = s.best ? '<span class="badge best">BEST</span>'
                : s.fallback ? '<span class="badge fb">fallback</span>'
                : '<span class="badge skip">skip</span>';
      const q = [s.resolution, s.codec, s.hdr, s.source].filter(Boolean).join(' · ')||'—';
      const sp = (s.start_seconds!=null? s.start_seconds.toFixed(1)+'s start · ':'')+(s.status||'');
      const from = [s.host, s.addon].filter(Boolean).join(' · ')||'—';
      return '<tr><td>'+tag+' <span class="m">#'+s.index+'</span></td><td>'+esc(q)+'</td>'
           + '<td>'+esc(gb(s.size_bytes))+(s.bitrate_mbps?'<div class="m">'+s.bitrate_mbps.toFixed(1)+' Mbps</div>':'')+'</td>'
           + '<td>'+esc(sp)+'</td><td>'+esc(from)+'</td>'
           + '<td>'+(s.downloadable?'<button class="ghost sm" data-url="'+esc(s.url)+'">Fetch this</button>':'<span class="m">torrent</span>')+'</td></tr>';
    }).join('');
    $('srows').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>fetchNow({url:b.dataset.url})));
  }catch(e){
    $('srows').innerHTML = '<tr><td colspan="6" class="empty">Failed: '+esc(e.message)+'</td></tr>';
    $('fetchbest').disabled = true;
  }
}
$('prefer').addEventListener('change', loadStreams);
$('reload').addEventListener('click', loadStreams);
$('season').addEventListener('change', loadStreams);
$('episode').addEventListener('change', loadStreams);
$('fetchbest').addEventListener('click', ()=>fetchNow({}));
$('addstrm').addEventListener('click', ()=>fetchNow({action:'strm'}));
if(SEERR_ON){
  $('reqseerr').addEventListener('click', ()=>requestSeerr(chosen
    ? {id:chosen.id, type:chosen.type, name:chosen.name, year:chosen.year} : {}));
}else{
  $('reqseerr').classList.add('hidden');
}

// ---- 3. fetch --------------------------------------------------------------------
async function fetchNow(extra){
  const body = Object.assign({
    imdb: chosen? chosen.id : '', title: chosen? chosen.name : '', year: chosen? chosen.year : '',
    kind: chosen? chosen.type : '', prefer: $('prefer').value,
    season: chosen&&chosen.type==='show' ? parseInt($('season').value||1,10) : undefined,
    episode: chosen&&chosen.type==='show' ? 'S'+String($('season').value||1).padStart(2,'0')
             +'E'+String($('episode').value||1).padStart(2,'0') : '',
  }, extra||{});
  Object.keys(body).forEach(k=>{ if(body[k]===undefined||body[k]==='') delete body[k]; });
  try{
    const r = await fetch('/fetch',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    const d = await r.json();
    ping(r.ok ? 'Queued job '+d.job : 'Error: '+(d.error||r.status));
    setTimeout(refreshJobs, 400);
  }catch(e){ ping('Request failed'); }
}
$('direct').addEventListener('submit', ev=>{
  ev.preventDefault();
  const fd = new FormData(ev.target), body = {};
  for(const [k,v] of fd.entries()) if(v.trim()) body[k]=v.trim();
  if(!body.title && !body.imdb){ ping('Give a title or an IMDb id'); return; }
  chosen = null;
  fetch('/fetch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(r=>r.json()).then(d=>ping('Queued job '+d.job)).catch(()=>ping('Request failed'));
  setTimeout(refreshJobs, 400);
});

// ---- 3b. request in Seerr (download to my server, no debrid) ----------------------
async function requestSeerr(d){
  if(!SEERR_ON){ ping('Seerr is not configured - set SEERR_URL and SEERR_API_KEY'); return; }
  const isShow = (d.type==='series'||d.type==='show');
  const body = { title:d.name||'', year:d.year||'', imdb:d.id||'', kind:isShow?'tv':'movie' };
  if(isShow && $('season')) body.season = parseInt($('season').value||1,10);
  Object.keys(body).forEach(k=>{ if(body[k]===undefined||body[k]==='') delete body[k]; });
  ping('Asking Seerr…');
  try{
    const r = await fetch('/request',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    const j = await r.json();
    if(r.ok && j.seerr){
      ping('Seerr: '+(j.seerr.title||body.title||'')+' → '+j.seerr.status_label
           +(j.seerr.already_available?' (already in your library)':''));
    }else{
      ping('Seerr: '+String(j.error||r.status).slice(0,140));
    }
    setTimeout(refreshJobs, 400);
  }catch(e){ ping('Seerr request failed: '+e.message); }
}

// ---- 4. jobs ---------------------------------------------------------------------
async function refreshJobs(){
  try{
    const d = await getJSON('/jobs');
    $('count').textContent = d.count? d.count+' total' : '';
    $('empty').style.display = d.jobs.length? 'none':'block';
    $('rows').innerHTML = d.jobs.map(j=>{
      const p=j.payload||{}, s=j.source||{};
      const t = (p.title||j.imdb||'?')+(p.year?' ('+p.year+')':'')+(p.episode?' '+p.episode:'');
      const isSeerr = j.action==='seerr';
      const isStrm = s.mode==='strm';
      const src = s.mode==='fastcombo'
        ? [s.resolution, gb(s.size_bytes), s.start_seconds!=null?s.start_seconds.toFixed(1)+'s':'',
           s.source, s.addon].filter(Boolean).join(' · ')
        : isSeerr ? 'Seerr → Radarr/Sonarr'
        : isStrm ? 'play-through · '+s.candidates+' live link(s)'
        : (s.mode||'—');
      const seerrTxt = j.seerr
        ? '<div class="m">seerr: '+esc(j.seerr.title||'')+(j.seerr.tmdb_id?' tmdb '+esc(j.seerr.tmdb_id):'')
          +' · '+esc(j.seerr.status_label||'')+(j.seerr.message?' · '+esc(j.seerr.message):'')+'</div>'
        : j.seerr_error ? '<div class="m">seerr failed: '+esc(String(j.seerr_error).slice(0,140))+'</div>' : '';
      const res = j.status==='done'
                ? (isSeerr ? '<span class="pill">requested in Seerr</span>'
                  : isStrm ? '<code>'+esc(j.file||'')+'</code>'
                           +' <span class="pill">no download</span>'
                           +'<div class="m">plays via '+esc((j.strm||{}).play_url||'')+'</div>'
                           +(j.warning?'<div class="m">'+esc(j.warning)+'</div>':'')
                           : '<code>'+esc(j.file||'')+'</code>')
                + (j.skipped?' <span class="pill">'+(isSeerr?'already in library':'already had it')+'</span>':'')
                + (j.attempt>1?' <span class="pill">used fallback #'+j.attempt+'</span>':'')
                + (j.media&&j.media.verified?' <span class="pill">verified video</span>':'')
                + (j.tried||[]).map(t=>'<div class="m">rejected #'+(t.rank!=null?t.rank:'?')
                     +': '+esc(String(t.error||'').slice(0,140))+'</div>').join('')
                + seerrTxt
                : j.status==='failed' ? esc(j.error||'')
                + (j.tried||[]).map(t=>'<div class="m">rejected #'+(t.rank!=null?t.rank:'?')
                     +': '+esc(String(t.error||'').slice(0,140))+'</div>').join('')
                : esc(j.stream||j.status);
      return '<tr><td><span class="badge '+esc(j.status)+'">'+esc(j.status)+'</span></td>'
           + '<td>'+esc(t)+(j.imdb?'<div class="m">'+esc(j.imdb)+'</div>':'')+'</td>'
           + '<td class="m">'+esc(src)+'</td><td>'+res+'</td><td>'+ago(j.updated)+'</td></tr>';
    }).join('');
  }catch(e){}
}
refreshJobs(); setInterval(refreshJobs, 3000);
</script>
</body></html>
"""


# --------------------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    server_version = "mwatcher-telestream-bridge/1.0"

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, code: int, page: str) -> None:
        raw = page.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    # ---- play-through streaming ----------------------------------------------
    def _send_cached(self, path: str) -> None:
        """Serve a finished cache file, honouring Range like any media server would."""
        size = os.path.getsize(path)
        start, end, status = 0, size - 1, 200
        match = re.match(r"\s*bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        if match and (match.group(1) or match.group(2)):
            status = 206
            if match.group(1):
                start = int(match.group(1))
                if match.group(2):
                    end = min(int(match.group(2)), size - 1)
            else:                                   # suffix range: the last N bytes
                start = max(0, size - int(match.group(2)))
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", "video/x-matroska")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        remaining, sent = length, 0
        with open(path, "rb") as handle:
            handle.seek(start)
            while remaining > 0:
                block = handle.read(min(CHUNK, remaining))
                if not block:
                    break
                self.wfile.write(block)
                remaining -= len(block)
                sent += len(block)
        log(f"play: served {sent / 1024 ** 2:.1f} MB from cache ({os.path.basename(path)})")

    def _stream_upstream(self, key: str) -> None:
        """
        Scrape a fresh link and stream it straight through to Plex, caching as we go.
        Fails over to the next candidate if a host will not open -- all of that happens
        BEFORE any header is sent, so the client never sees a half-formed response.
        """
        entry = play_entry(key)
        candidates = entry["candidates"]
        want_range = (self.headers.get("Range") or "").strip()
        from_zero = (not want_range) or bool(re.match(r"bytes=0-$", want_range))
        final, part = cache_path(key, True), cache_path(key, False)
        errors: list[str] = []

        for n, cand in enumerate(candidates, start=1):
            request = urllib.request.Request(cand.url)
            for header, value in (getattr(cand, "headers", None) or {}).items():
                request.add_header(header, value)
            if want_range:
                request.add_header("Range", want_range)
            request.add_header("User-Agent",
                               "Mozilla/5.0 (X11; Linux x86_64) Mwatcher-playthrough/1.0")
            try:
                upstream = urllib.request.urlopen(request, timeout=PLAY_TIMEOUT)
            except Exception as exc:  # noqa: BLE001 - try the next candidate
                errors.append(f"#{n} {getattr(cand, 'res_label', '') or ''}: {exc}")
                log(f"play {key}: candidate {n}/{len(candidates)} would not open ({exc})")
                continue

            with upstream:
                code = upstream.status if upstream.status in (200, 206) else 200
                length_header = upstream.headers.get("Content-Length") or ""
                content_range = upstream.headers.get("Content-Range") or ""

                # Sniff before committing a single header: if this host is serving a
                # captcha/login/error page instead of video, we can still fail over to the
                # next candidate. Once headers go out, that option is gone and Plex would
                # happily try to play HTML -- which is exactly error s1001.
                first = upstream.read(CHUNK)
                upstream_type = (upstream.headers.get("Content-Type") or "").lower()
                marker = sniff_html(first) if from_zero else None
                if marker or (from_zero and upstream_type.startswith(("text/html",
                                                                     "application/json"))):
                    why = (f"content-type {upstream_type}" if not marker
                           else f"found {marker!r} in the first bytes")
                    errors.append(f"#{n} {getattr(cand, 'res_label', '') or ''}: "
                                  f"not a video ({why})")
                    log(f"play {key}: candidate {n}/{len(candidates)} served a web page, "
                        f"not a video ({why}) -- trying the next one")
                    continue

                self.send_response(code)
                self.send_header("Content-Type",
                                 upstream.headers.get("Content-Type") or "video/x-matroska")
                self.send_header("Accept-Ranges", "bytes")
                if length_header:
                    self.send_header("Content-Length", length_header)
                if content_range:
                    self.send_header("Content-Range", content_range)
                self.send_header("X-Mwatcher-Stream",
                                 f"scraped live, candidate {n}/{len(candidates)}")
                self.end_headers()

                caching = bool(CACHE_ENABLED and from_zero and code in (200, 206))
                handle = None
                if caching:
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    handle = open(part, "wb")
                total = 0
                try:
                    if first:                      # the chunk we sniffed is real media
                        if handle:
                            handle.write(first)
                        self.wfile.write(first)
                        total += len(first)
                    while True:
                        block = upstream.read(CHUNK)
                        if not block:
                            break
                        if handle:
                            handle.write(block)
                        self.wfile.write(block)
                        total += len(block)
                except (BrokenPipeError, ConnectionResetError):
                    log(f"play {key}: client stopped after {total / 1024 ** 2:.1f} MB")
                    if handle:
                        handle.close()
                        handle = None
                        try:
                            os.remove(part)     # a partial cache cannot be resumed safely
                        except OSError:
                            pass
                    return
                if handle:
                    handle.close()
                    complete = length_header.isdigit() and total >= int(length_header)
                    if complete:
                        os.replace(part, final)
                        os.chmod(final, 0o644)
                        evict_cache()
                        log(f"play {key}: streamed {total / 1024 ** 2:.1f} MB and cached it")
                    else:
                        try:
                            os.remove(part)
                        except OSError:
                            pass
                        log(f"play {key}: streamed {total / 1024 ** 2:.1f} MB "
                            f"(incomplete, not cached)")
                else:
                    log(f"play {key}: streamed {total / 1024 ** 2:.1f} MB")
                return

        raise RuntimeError("every scraped link failed: " + " | ".join(errors[-3:]))

    def _serve_play(self, path: str) -> None:
        key = re.sub(r"\.(mkv|mp4|webm|avi)$", "", os.path.basename(path))
        try:
            play_entry(key)
        except KeyError:
            self._send(404, {
                "error": f"unknown play key '{key}'",
                "detail": ("this pointer is not in the play table. Either it was never created "
                           "by this bridge, or it was dropped by TELESTREAM_MAX_PLAYS. Re-add "
                           "the title with POST /add and replace the .strm."),
                "play_file": PLAY_FILE,
                "known_plays": len(PLAY),
            })
            return
        final = cache_path(key, True)
        if os.path.exists(final):
            try:
                self._send_cached(final)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        try:
            resolve_for_play(key)          # scrape a fresh link at play time
            self._stream_upstream(key)
        except Exception as exc:  # noqa: BLE001
            log(f"play {key}: FAILED - {exc}")
            try:
                self._send(502, {"error": f"could not play '{key}': {exc}"})
            except Exception:              # headers may already be gone; nothing to do
                pass

    def do_HEAD(self) -> None:  # noqa: N802
        """Answer HEAD. `curl -I` and some clients probe with it; without this the bridge
        replies 501 Unsupported method, which reads like a broken stream rather than an
        unhandled verb."""
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/play/"):
            key = re.sub(r"\.(mkv|mp4|webm|avi)$", "", os.path.basename(path))
            try:
                play_entry(key)
            except KeyError:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            final = cache_path(key, True)
            size = os.path.getsize(final) if os.path.exists(final) else 0
            self.send_response(200)
            self.send_header("Content-Type", "video/x-matroska")
            self.send_header("Accept-Ranges", "bytes")
            if size:
                self.send_header("Content-Length", str(size))
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

        if path in ("/", "/index.html", "/ui"):
            self._send_html(200, dashboard_html())
        elif path.startswith("/play/"):
            # Plex asks for this: scrape a fresh link and stream it through (with cache).
            self._serve_play(path)
        elif path == "/cache":
            self._send(200, cache_stats())
        elif path == "/plays":
            self._send(200, {"count": len(PLAY), "base_url": play_base_url(),
                             "plays": play_list()})
        elif path == "/healthz":
            self._send(200, {"ok": True, "fastcombo": bool(FASTCOMBO_ACCESS_KEY),
                            "stremio_source": stremio_source is not None,
                            "seerr": seerr_ready(), "seerr_mode": SEERR_MODE})
        elif path == "/jobs":
            with JOBS_LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j["created"], reverse=True)
            self._send(200, {"count": len(jobs), "jobs": jobs[:50]})
        elif path == "/config":
            self._send(200, {
                "fastcombo_base_url": FASTCOMBO_BASE_URL,
                "fastcombo_access_key": ("*" * 6 + FASTCOMBO_ACCESS_KEY[-4:]) if FASTCOMBO_ACCESS_KEY else "",
                "fastcombo_ready": bool(FASTCOMBO_BASE_URL and FASTCOMBO_ACCESS_KEY),
                "prefer": FASTCOMBO_PREFER, "max_fallbacks": FASTCOMBO_MAX_FALLBACKS,
                "cinemeta_url": CINEMETA_URL, "staging": STAGING,
                "movies_dir": MOVIES_DIR, "tv_dir": TV_DIR,
                "downloader": _tool_of(DOWNLOAD_CMD or default_download_cmd()),
                "resolver_url": RESOLVER_URL,
                "seerr_url": SEERR_URL, "seerr_ready": seerr_ready(),
                "seerr_mode": SEERR_MODE, "seerr_is4k": SEERR_IS4K,
                "default_action": resolve_action({}),
                "play_base_url": play_base_url(),
                "cache_dir": CACHE_DIR, "cache_enabled": CACHE_ENABLED,
                "cache_max_gb": round(CACHE_MAX_BYTES / 1024 ** 3, 2),
                "cache_used_gb": round(cache_stats()["used_gb"], 3),
                "resolve_ttl_seconds": RESOLVE_TTL,
            })
        elif path == "/seerr":
            # Is Seerr reachable, and what is queued for download right now?
            if not seerr_ready():
                self._send(200, {
                    "ok": False, "configured": False,
                    "error": "SEERR_URL / SEERR_API_KEY not set",
                    "hint": "key is in Seerr -> Settings -> General; put both in "
                            "~/.config/mwatcher/bridge.env (chmod 600)",
                })
                return
            try:
                info = seerr_source.server_status(base_url=SEERR_URL, api_key=SEERR_API_KEY)
                recent = seerr_source.pending_requests(20, base_url=SEERR_URL, api_key=SEERR_API_KEY)
                self._send(200, {"ok": True, "configured": True, "url": SEERR_URL,
                                 "version": info.get("version"), "mode": SEERR_MODE,
                                 "requests": recent})
            except Exception as exc:  # noqa: BLE001
                self._send(502, {"ok": False, "configured": True, "url": SEERR_URL,
                                 "error": str(exc)})
        elif path == "/search":
            # Title text -> IMDb matches (Cinemeta), so the dashboard can offer a picker.
            q = (qs.get("q") or "").strip()
            if not q:
                self._send(400, {"error": "need ?q=<title>"})
            elif stremio_source is None:
                self._send(500, {"error": "stremio_source.py not importable"})
            else:
                try:
                    metas = stremio_source.search_titles(q, CINEMETA_URL)
                    self._send(200, {"ok": True, "query": q, "count": len(metas), "metas": metas})
                except Exception as exc:  # noqa: BLE001
                    self._send(502, {"ok": False, "error": f"Cinemeta search failed: {exc}"})
        elif path == "/streams":
            # Ranked Fast Combo candidates for one title/episode, best one flagged.
            stype = (qs.get("type") or "movie").strip().lower()
            sid = (qs.get("id") or "").strip()
            if not sid:
                self._send(400, {"error": "need ?id=tt1234567 (and ?type=series&season=1&episode=2)"})
            elif stremio_source is None:
                self._send(500, {"error": "stremio_source.py not importable"})
            else:
                try:
                    stype = "series" if stype in ("series", "show") else stype
                    if stype == "series":
                        sid = stremio_source.episode_id(sid.split(":")[0], qs.get("season", 1), qs.get("episode", 1))
                    prefer = (qs.get("prefer") or FASTCOMBO_PREFER)
                    cands = stremio_source.fetch_streams(
                        FASTCOMBO_BASE_URL, FASTCOMBO_ACCESS_KEY, stype, sid, FASTCOMBO_TOKEN)
                    best, ordered = stremio_source.pick(cands, prefer, FASTCOMBO_MAX_FALLBACKS)
                    ranked = stremio_source.rank(cands, prefer)
                    streams = []
                    for c in ranked:
                        d = c.to_dict()
                        d["best"] = bool(best and c.index == best.index)
                        d["fallback"] = any(o.index == c.index for o in ordered)
                        streams.append(d)
                    self._send(200, {
                        "ok": True, "stype": stype, "sid": sid, "prefer": prefer,
                        "total": len(cands), "downloadable": len(ordered),
                        "best_index": best.index if best else None, "streams": streams,
                    })
                except Exception as exc:  # noqa: BLE001
                    self._send(502, {"ok": False, "error": str(exc)})
        else:
            self._send(404, {"error": "try GET /jobs, /plays, /cache, /seerr, /search?q=, "
                                     "/streams?id=tt... or POST /fetch, /add, /request"})

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path not in ("/fetch", "/request", "/add"):
            self._send(404, {"error": "POST /fetch (download), POST /add (play-through .strm, "
                                      "no download) or POST /request (ask Seerr)"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            if not isinstance(payload, dict):
                raise ValueError("body must be a JSON object")
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"error": f"bad JSON: {exc}"})
            return

        if path == "/add":
            # Play-through: no download. Writes a .strm that Plex plays via /play/<key>.
            try:
                info = add_strm(payload)
            except Exception as exc:  # noqa: BLE001
                self._send(502, {"ok": False, "error": str(exc)})
                return
            self._send(200, {"ok": True, "action": "strm", "downloaded_bytes": 0, **info})
            return

        if path == "/request":
            # Seerr path: resolve the title, create the request, answer synchronously.
            # It is two short HTTP calls, so callers get a real yes/no instead of a job id.
            job_id = new_job(payload)
            result = run_seerr_job(job_id, payload)
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id) or {})
            if job.get("status") == "done":
                self._send(200, {
                    "ok": True, "job": job_id, "action": "seerr", "seerr": result,
                    "note": ("Seerr handed this to Radarr/Sonarr; watch the request in "
                             f"{SEERR_URL}/requests" if result and not result.get("already_available")
                             else (result or {}).get("message", "")),
                })
            else:
                err = str(job.get("error") or "")
                # Only point at configuration when the failure actually looks like it.
                looks_like_config = any(k in err.lower() for k in (
                    "not configured", "api key", "http 401", "http 403", "cannot reach seerr",
                    "permission"))
                self._send(502, {"ok": False, "job": job_id, "error": err,
                                 "hint": ("check SEERR_URL / SEERR_API_KEY, and that Seerr -> "
                                          "Settings -> Servers has Radarr/Sonarr attached"
                                          if looks_like_config else
                                          "pass a title (and year/kind) that Seerr can match "
                                          "to a TMDB entry")})
            return

        job_id = enqueue(payload)
        act = resolve_action(payload)
        self._send(202, {"job": job_id, "status": "queued", "action": act,
                         "poll": "/jobs",
                         "what": {"stream": "downloading the best stream from your addons",
                                  "seerr": "creating a request in Seerr",
                                  "both": "requesting in Seerr and streaming now"}.get(act, "")})

    def log_message(self, fmt: str, *args) -> None:  # keep journald tidy
        log(f"{self.address_string()} {fmt % args}")


# Restore pointers written by earlier runs. This happens at IMPORT, not inside serve(), so a
# one-shot `--add` from a shell merges into the existing table instead of replacing it with a
# single entry and silently killing every other .strm in the library.
RESTORED_PLAYS = play_load()


def serve() -> None:
    for directory in (STAGING, MOVIES_DIR, TV_DIR):
        os.makedirs(directory, exist_ok=True)
    httpd = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), Handler)
    log(f"listening on http://{BRIDGE_HOST}:{BRIDGE_PORT} (POST /fetch, GET /jobs)")
    log(f"staging={STAGING} movies={MOVIES_DIR} tv={TV_DIR}")
    if RESTORED_PLAYS:
        log(f"restored {RESTORED_PLAYS} play-through pointer(s) from {PLAY_FILE}")
    else:
        log(f"play-through table: {PLAY_FILE}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


# --------------------------------------------------------------------------- cli

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch the best stream from your Stremio addons (Fast Combo) into a Plex library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Configuration is by environment variable")[0],
    )
    parser.add_argument("serve", nargs="?", help="run the HTTP bridge/dashboard instead of a one-shot fetch")
    # what to fetch
    parser.add_argument("--title", help="movie or show title (searched on Cinemeta if no --imdb)")
    parser.add_argument("--imdb", help="IMDb id, e.g. tt1375666 (skips the search)")
    parser.add_argument("--year", help="4-digit year, disambiguates remakes")
    parser.add_argument("--kind", choices=["movie", "show", "series"], help="default: auto-detected")
    parser.add_argument("--season", type=int, default=1, help="season number (shows)")
    parser.add_argument("--episode", help="episode code (S01E02 / 1x02) or number (shows)")
    parser.add_argument("--prefer", choices=list(stremio_source.PREFER_ORDER) if stremio_source else None,
                        help="how to rank Fast Combo's list (default: best)")
    # direct-link mode (the old Telestream behaviour)
    parser.add_argument("--url", help="direct/Telestream stream URL instead of an addon lookup")
    parser.add_argument("--stream", help="same as --url but skip the local resolver")
    parser.add_argument("--dest", help="override destination folder (skips Plex naming rules)")
    # repair: pointers written before the play table was persisted point at keys nothing
    # knows about any more, and Plex 404s on them
    parser.add_argument("--repoint", action="store_true",
                        help="re-create every play-through .strm whose key this bridge no "
                             "longer knows, then report what it did")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --repoint: list the orphaned pointers, change nothing")
    # Seerr: request a title so Radarr/Sonarr download it to your server
    parser.add_argument("--action", choices=list(ACTIONS),
                        help="stream (download the best addon stream), strm (NO download: "
                             "write a .strm that plays through this bridge's cache), seerr "
                             "(create a Seerr request only), or both (Seerr request plus the "
                             "instant path). Default: TELESTREAM_ACTION, else SEERR_MODE.")
    parser.add_argument("--add", action="store_true",
                        help="same as --action strm: add the title without downloading it")
    parser.add_argument("--public-url",
                        help="base URL your Plex CLIENTS can reach this bridge at, written "
                             "into .strm files (overrides TELESTREAM_PUBLIC_BASE_URL)")
    parser.add_argument("--seasons", help='for a Seerr TV request: "all", "missing", or "1,3"')
    parser.add_argument("--4k", dest="is4k", action="store_true",
                        help="request the 4K variant in Seerr (needs a 4K server configured there)")
    # inspect instead of fetching
    parser.add_argument("--seerr-status", action="store_true",
                        help="is Seerr reachable, and what is queued for download?")
    parser.add_argument("--search", action="store_true", help="just list IMDb matches for --title")
    parser.add_argument("--list-streams", action="store_true",
                        help="just list the ranked candidates Fast Combo returns, download nothing")
    args = parser.parse_args(argv)

    if args.serve == "serve":
        serve()
        return 0
    if args.repoint:
        return repoint_library(dry_run=args.dry_run)

    if args.add:
        args.action = "strm"
    # Use the shared resolver. This line used to re-implement it and left out
    # TELESTREAM_ACTION entirely, so a box configured for play-through still downloaded a
    # full file when you used the CLI -- while --help promised "Default: TELESTREAM_ACTION".
    want_action = resolve_action({}, args.action or "")
    if stremio_source is None and not (args.url or args.stream) and want_action != "seerr":
        parser.error("stremio_source.py is missing, so only --url/--stream mode is available")

    # --- inspect: Seerr --------------------------------------------------------------
    if args.seerr_status:
        if not seerr_ready():
            print("Seerr is not configured. Set SEERR_URL and SEERR_API_KEY "
                  "(Seerr -> Settings -> General).", file=sys.stderr)
            return 2
        try:
            info = seerr_source.server_status(base_url=SEERR_URL, api_key=SEERR_API_KEY)
            print(f"Seerr {info.get('version')} at {info.get('base_url')}  (mode={SEERR_MODE})")
            for r in seerr_source.pending_requests(20, base_url=SEERR_URL, api_key=SEERR_API_KEY):
                print(f"  [{r['status_label']:>20}] {r['media_type']:<5} tmdb={r['tmdb_id']} "
                      f"request#{r['id']} by {r.get('requested_by') or '?'}")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"seerr error: {exc}", file=sys.stderr)
            return 2

    # --- inspect: title search -------------------------------------------------------
    if args.search:
        if not args.title:
            parser.error("--search needs --title")
        print(json.dumps(stremio_source.search_titles(args.title, CINEMETA_URL), indent=2))
        return 0

    # --- inspect: ranked candidates, no download -------------------------------------
    if args.list_streams:
        if not (args.imdb or args.title):
            parser.error("--list-streams needs --imdb or --title")
        plan = fastcombo_plan(vars(args) | {"kind": args.kind or ""})
        print(f"{plan['title']} ({plan['year']}) {plan['imdb']} -> {plan['stype']}/{plan['sid']}")
        print(f"{plan['total']} streams from Fast Combo, {plan['downloadable']} downloadable, "
              f"prefer={plan['prefer']}\n")
        for c in stremio_source.rank(plan["candidates"], plan["prefer"])[:20]:
            flag = "BEST" if plan["best"].index == c.index else ("    " if c.downloadable else "skip")
            print(f"[{flag}] #{c.index:<3} {c.summary or '(no details)'}")
        return 0 if plan["best"] else 1

    # --- fetch -----------------------------------------------------------------------
    direct = args.stream or args.url
    if direct and not args.title and not args.imdb:
        parser.error("--url/--stream needs --title (for the Plex filename)")
    if not direct and not (args.imdb or args.title):
        parser.error("need --imdb or --title (Fast Combo lookup), or --url/--stream (direct link), "
                     "or the 'serve' subcommand")
    if want_action in ("seerr",) and not seerr_ready():
        parser.error("--action seerr needs SEERR_URL and SEERR_API_KEY "
                     "(the key is in Seerr -> Settings -> General)")
    if want_action == "both" and not seerr_ready():
        parser.error("--action both needs SEERR_URL and SEERR_API_KEY "
                     "(the key is in Seerr -> Settings -> General)")
    if want_action in ("strm", "both") and instant_runner(want_action) == "strm":
        global PUBLIC_BASE_URL  # noqa: PLW0603
        if args.public_url:
            PUBLIC_BASE_URL = args.public_url.rstrip("/")
        if "127.0.0.1" in play_base_url() or "localhost" in play_base_url():
            print("warning: .strm will point at loopback, so only THIS machine can play it.\n"
                  "         Set TELESTREAM_PUBLIC_BASE_URL (or --public-url) to the address\n"
                  "         your Plex clients use, e.g. http://192.168.0.34:8889",
                  file=sys.stderr)

    payload = {
        "title": args.title or "",
        "imdb": args.imdb or "",
        "url": direct or "",
        "year": args.year or "",
        "kind": args.kind or "",
        "season": args.season,
        "episode": args.episode or "",
        "prefer": args.prefer or "",
        "dest": args.dest,
        "action": want_action,
        "seasons": args.seasons or "",
        "public_url": args.public_url or "",
        "is4k": True if args.is4k else None,
    }
    if args.stream:
        # --stream means the URL is already direct: bypass the resolver for this job only
        global RESOLVER_URL  # noqa: PLW0603
        RESOLVER_URL = ""

    job_id = new_job(payload)
    dispatch_job(job_id, payload, want_action)  # foreground: exit code is useful in cron
    with JOBS_LOCK:
        job = dict(JOBS[job_id])
    print(json.dumps(job, indent=2))
    return 0 if job.get("status") == "done" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
