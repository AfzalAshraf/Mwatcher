#!/usr/bin/env python3
"""
stremio_source.py -- ask Stremio addons (via Fast Combo) for the single best stream.

Fast Combo (https://github.com/AfzalAshraf/stremio-addons) already does the hard part:
it queries every addon you configured at once, drops CAM/TS copies, dead links, ads,
duplicates, huge REMUX files and links that expire mid-movie, live-probes what is left,
and returns them sorted best-first. This module consumes that list and picks ONE stream
to hand to the Plex bridge -- preferring links that start fast and are actually
downloadable (a plain HTTP/HLS url, not a torrent infoHash).

Protocol notes (verified against fastcombo.js v2.1.0)
----------------------------------------------------
Public, needs only the access key:
    GET {base}/{access_key}[/{token}]/stream/{movie|series}/{id}.json   -> {"streams": [...]}
    GET {base}/{access_key}[/{token}]/manifest.json
Series ids use the Stremio convention  tt1234567:1:2  (imdb:season:episode).

Admin only (needs the control-panel password, so we do NOT use these):
    /api/search, /api/title, /api/try, /api/health, /api/ai

Each returned stream looks like:
    {"url": "https://host/file.mkv",              # or "infoHash": "..." for torrents
     "name": "\u26a1 1080p\\n\U0001F4E6 2.10 GB",
     "description": "\U0001F3AC Title\\n\U0001F4E6 2.10 GB \u00b7 \U0001F4CA 5.2 Mbps \u00b7 \U0001F39E\ufe0f HEVC\\n"
                    "\U0001F3A5 BluRay \u00b7 \U0001F3A7 AC3\\n"
                    "\u26a1 Tested OK \u00b7 starts in 0.8s \u00b7 \U0001F310 host \u00b7 \U0001F50D addon",
     "behaviorHints": {"videoSize": 2100000000, "bingeGroup": "fastcombo|1080p|BluRay",
                       "proxyHeaders": {"request": {"User-Agent": "..."}}}}

So everything we want to rank on is parseable from name/description/behaviorHints.

Title -> IMDb id uses Cinemeta (the same free addon Fast Combo itself calls):
    GET {cinemeta}/catalog/{movie|series}/top/search={query}.json
    GET {cinemeta}/meta/{movie|series}/{tt...}.json
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict

DEFAULT_CINEMETA = "https://v3-cinemeta.strem.io"
DEFAULT_TIMEOUT = float(os.environ.get("FASTCOMBO_TIMEOUT", "45"))

# Anything Fast Combo calls a "page" rather than a file cannot be downloaded by us.
PREFER_ORDER = ("best", "fastest", "smallest", "4kfirst", "1080first")


# --------------------------------------------------------------------------- http

def _get_json(url: str, timeout: float = DEFAULT_TIMEOUT, headers: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": "mwatcher/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - user-configured endpoints
        return json.loads(resp.read().decode("utf-8", "replace"))


# --------------------------------------------------------------------------- model

@dataclass
class Candidate:
    """One stream from Fast Combo, normalised for ranking and display."""
    index: int = 0                 # position in Fast Combo's own (already ranked) list
    url: str = ""                  # direct HTTP/HLS link -- empty for torrents
    info_hash: str = ""            # torrent magnet hash -- needs a debrid, we skip these
    file_idx: int | None = None
    downloadable: bool = False
    resolution: int = 0            # 2160 / 1080 / 720 ...
    res_label: str = ""            # "4K", "1080p"
    size_bytes: int = 0
    bitrate_mbps: float = 0.0
    codec: str = ""
    hdr: str = ""
    source: str = ""               # BluRay / WEB-DL / HDTV ...
    audio: str = ""
    langs: str = ""
    host: str = ""                 # file host label
    addon: str = ""                # which of your addons produced it
    status: str = "unknown"        # ok / instant / p2p / slow / untested / expiring
    start_seconds: float | None = None   # "starts in 0.8s" -- the speed signal
    seeders: int | None = None
    expires_minutes: int | None = None
    filename: str = ""
    name: str = ""
    description: str = ""
    headers: dict = field(default_factory=dict)   # required request headers, if any
    raw: dict = field(default_factory=dict)

    @property
    def summary(self) -> str:
        bits = [self.res_label, _fmt_size(self.size_bytes), _fmt_rate(self.bitrate_mbps),
                self.codec, self.hdr, self.source]
        line = " ".join(b for b in bits if b)
        if self.start_seconds is not None:
            line += f" | starts in {self.start_seconds:.1f}s"
        if self.host:
            line += f" | {self.host}"
        if self.addon:
            line += f" | via {self.addon}"
        return line.strip(" |")

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        d["summary"] = self.summary
        return d


def _fmt_size(b: int) -> str:
    if not b:
        return ""
    if b >= 1e9:
        return f"{b / 1e9:.2f} GB"
    return f"{round(b / 1e6)} MB"


def _fmt_rate(r: float) -> str:
    if not r:
        return ""
    return f"{r:.0f} Mbps" if r >= 10 else f"{r:.1f} Mbps"


# --------------------------------------------------------------------------- parsing

_SIZE = re.compile(r"([\d.]+)\s*(TB|GB|MB)\b", re.I)
_RATE = re.compile(r"([\d.]+)\s*Mbps", re.I)
_RES = re.compile(r"\b(2160p|1080p|720p|480p|4k|8k)\b", re.I)
_CODEC = re.compile(r"\b(HEVC|H\.?265|AV1|AVC|H\.?264|XviD|DivX)\b", re.I)
_HDR = re.compile(r"\b(HDR10\+|HDR10|DoVi|DV|HDR)\b")
_SRC = re.compile(r"\b(Blu-?Ray|BDRip|BRRip|WEB-?DL|WEBRip|WEB|HDTV|DVDRip|HDRip|REMUX)\b", re.I)
_START = re.compile(r"starts in\s*([\d.]+)\s*s", re.I)
_SEEDERS = re.compile(r"([\d,]+)\s*seeders", re.I)
_EXPIRY = re.compile(r"expires in\s*([\d,]+)\s*min", re.I)
_HOST = re.compile(r"\U0001F310\s*([^\u00b7\n]+)")          # globe emoji -> file host
_ADDON = re.compile(r"\U0001F50D\s*([^\n]+)")                # magnifier -> source addon
_LANGS = re.compile(r"\U0001F5E3\ufe0f\s*([^\n]+)")          # speaking head -> languages

_RES_MAP = {"8k": 4320, "4k": 2160, "2160p": 2160, "1080p": 1080, "720p": 720, "480p": 480}


def _size_to_bytes(value: str, unit: str) -> int:
    n = float(value)
    return int(n * {"TB": 1e12, "GB": 1e9, "MB": 1e6}[unit.upper()])


def parse_candidate(raw: dict, index: int = 0) -> Candidate:
    """Turn one Fast Combo stream object into a Candidate."""
    if not isinstance(raw, dict):
        return Candidate(index=index)
    bh = raw.get("behaviorHints") or {}
    name = str(raw.get("name") or "")
    desc = str(raw.get("description") or raw.get("title") or "")
    blob = f"{name}\n{desc}"

    url = raw.get("url") if isinstance(raw.get("url"), str) else ""
    info_hash = raw.get("infoHash") if isinstance(raw.get("infoHash"), str) else ""

    c = Candidate(
        index=index,
        url=url,
        info_hash=info_hash,
        file_idx=raw.get("fileIdx"),
        downloadable=bool(url) and url.startswith("http"),
        name=name,
        description=desc,
        raw=raw,
    )

    m = _RES.search(blob)
    if m:
        label = m.group(1).lower()
        res = _RES_MAP.get(label, 0)
        c.resolution = res
        c.res_label = "4K" if res >= 2160 and res < 4320 else ("8K" if res >= 4320 else (f"{res}p" if res else label))

    # behaviorHints.videoSize is exact when the addon supplied it; else parse the text.
    if isinstance(bh.get("videoSize"), (int, float)) and bh["videoSize"] > 0:
        c.size_bytes = int(bh["videoSize"])
    else:
        m = _SIZE.search(blob)
        if m:
            c.size_bytes = _size_to_bytes(m.group(1), m.group(2))

    m = _RATE.search(blob)
    if m:
        c.bitrate_mbps = float(m.group(1))
    m = _CODEC.search(blob)
    if m:
        c.codec = m.group(1).upper().replace(".", "")
    m = _HDR.search(blob)
    if m:
        c.hdr = m.group(1)
    m = _SRC.search(blob)
    if m:
        c.source = m.group(1).upper()
    m = _START.search(blob)
    if m:
        c.start_seconds = float(m.group(1))
    m = _SEEDERS.search(blob)
    if m:
        c.seeders = int(m.group(1).replace(",", ""))
    m = _EXPIRY.search(blob)
    if m:
        c.expires_minutes = int(m.group(1).replace(",", ""))
    m = _HOST.search(blob)
    if m:
        c.host = m.group(1).strip()
    m = _ADDON.search(blob)
    if m:
        c.addon = m.group(1).strip()
    m = _LANGS.search(blob)
    if m:
        c.langs = m.group(1).strip()

    low = blob.lower()
    if "tested ok" in low:
        c.status = "ok"
    elif "instant" in low:
        c.status = "instant"
    elif "torrent" in low or c.info_hash:
        c.status = "p2p"
    elif "slow to start" in low:
        c.status = "slow"
    else:
        c.status = "untested"
    if "expires in" in low:
        c.status = "expiring"

    # Headers some file hosts require (Fast Combo forwards them from the upstream addon).
    req_headers = ((bh.get("proxyHeaders") or {}).get("request")) or {}
    if isinstance(req_headers, dict):
        c.headers = {str(k): str(v) for k, v in req_headers.items()}

    if isinstance(bh.get("filename"), str):
        c.filename = bh["filename"].split("|^|")[0].strip()
    elif "\U0001F4C4" in blob:
        c.filename = blob.split("\U0001F4C4")[-1].strip().splitlines()[0].strip()

    return c


# --------------------------------------------------------------------------- ranking

def rank(candidates: list[Candidate], prefer: str = "best") -> list[Candidate]:
    """
    Order candidates for downloading.

    Fast Combo already sorted them best-first, so "best" keeps that order and simply
    puts downloadable links ahead of torrents/debrid-only entries. The other modes
    re-sort for a specific taste; ties always fall back to Fast Combo's own order.
    """
    usable = [c for c in candidates if c.downloadable]
    rest = [c for c in candidates if not c.downloadable]

    def key(c: Candidate):
        if prefer == "fastest":
            # quick start first, then smaller file, then higher resolution
            return (c.start_seconds if c.start_seconds is not None else 999.0,
                    c.size_bytes or 1 << 40, -c.resolution)
        if prefer == "smallest":
            return (c.size_bytes or 1 << 40,
                    c.start_seconds if c.start_seconds is not None else 999.0)
        if prefer == "4kfirst":
            return (0 if c.resolution >= 2160 else 1, c.index)
        if prefer == "1080first":
            return (0 if c.resolution == 1080 else (1 if c.resolution >= 2160 else 2), c.index)
        return (c.index,)  # "best" -> trust Fast Combo's order

    return sorted(usable, key=key) + sorted(rest, key=lambda c: c.index)


def pick(candidates: list[Candidate], prefer: str = "best", max_fallbacks: int = 5):
    """Return (best_candidate_or_None, ordered_fallbacks)."""
    ordered = [c for c in rank(candidates, prefer) if c.downloadable][:max_fallbacks]
    return (ordered[0] if ordered else None), ordered


# --------------------------------------------------------------------------- fast combo

def stream_path(base: str, access_key: str, token: str, stype: str, sid: str) -> str:
    base = (base or "").rstrip("/")
    parts = [p for p in (access_key, token) if p]
    return f"{base}/{'/'.join(parts)}/stream/{stype}/{urllib.parse.quote(sid, safe=':')}.json"


def episode_id(imdb: str, season, episode) -> str:
    """Stremio series id: tt1234567:1:2"""
    s = int(season or 1)
    e = int(episode or 1)
    return f"{imdb}:{s}:{e}"


def fetch_streams(base: str, access_key: str, stype: str, sid: str, token: str = "",
                  timeout: float = DEFAULT_TIMEOUT) -> list[Candidate]:
    """Ask Fast Combo for a title/episode and return normalised, ranked-ready candidates."""
    if not base:
        raise RuntimeError("FASTCOMBO_BASE_URL is not set")
    if not access_key:
        raise RuntimeError("FASTCOMBO_ACCESS_KEY is not set (it is the secret part of your addon link)")
    if stype not in ("movie", "series", "tv", "channel", "anime"):
        raise RuntimeError(f"unsupported type {stype!r} (use movie or series)")

    url = stream_path(base, access_key, token, stype, sid)
    data = _get_json(url, timeout=timeout)
    streams = data.get("streams") if isinstance(data, dict) else None
    if not isinstance(streams, list):
        raise RuntimeError(f"unexpected reply from Fast Combo: {str(data)[:200]}")
    return [parse_candidate(s, i) for i, s in enumerate(streams)]


# --------------------------------------------------------------------------- cinemeta

def search_titles(query: str, cinemeta: str = "", limit: int = 12,
                  timeout: float = DEFAULT_TIMEOUT) -> list[dict]:
    """Title text -> IMDb matches (movies + series), via Cinemeta."""
    base = (cinemeta or os.environ.get("CINEMETA_URL") or DEFAULT_CINEMETA).rstrip("/")
    q = (query or "").strip()[:80]
    if not q:
        return []
    out: list[dict] = []
    for stype in ("movie", "series"):
        url = f"{base}/catalog/{stype}/top/search={urllib.parse.quote(q)}.json"
        try:
            data = _get_json(url, timeout=timeout)
        except Exception:  # noqa: BLE001 - one type failing should not kill the search
            continue
        for m in (data.get("metas") or [])[:10]:
            mid = m.get("imdb_id") or m.get("id") or ""
            if not re.fullmatch(r"tt\d+", str(mid)):
                continue
            out.append({
                "id": mid,
                "type": stype,
                "name": str(m.get("name") or ""),
                "year": str(m.get("releaseInfo") or m.get("year") or "")[:9],
                "poster": m.get("poster") if isinstance(m.get("poster"), str) else "",
            })
    # interleave movies/series like Fast Combo does, then trim
    movies = [m for m in out if m["type"] == "movie"]
    series = [m for m in out if m["type"] == "series"]
    merged: list[dict] = []
    for i in range(max(len(movies), len(series))):
        if i < len(movies):
            merged.append(movies[i])
        if i < len(series):
            merged.append(series[i])
    return merged[:limit]


def title_info(imdb: str, cinemeta: str = "", timeout: float = DEFAULT_TIMEOUT) -> dict:
    """IMDb id -> {name, year, type, eps:[(s,e,title)]}. Used for Plex-correct naming."""
    base = (cinemeta or os.environ.get("CINEMETA_URL") or DEFAULT_CINEMETA).rstrip("/")
    if not re.fullmatch(r"tt\d{5,10}", imdb or ""):
        return {"ok": False, "error": "not an IMDb id (expected tt1234567)"}
    for stype in ("series", "movie"):
        try:
            data = _get_json(f"{base}/meta/{stype}/{imdb}.json", timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        m = (data or {}).get("meta") or {}
        if not m.get("name"):
            continue
        # Trust the type the server reports over the one we asked for, if it says.
        reported = str(m.get("type") or "").lower()
        if reported in ("movie", "series"):
            stype = reported
        eps = []
        if stype == "series":
            for v in (m.get("videos") or []):
                try:
                    s, e = int(v.get("season")), int(v.get("episode"))
                except (TypeError, ValueError):
                    continue
                if s > 0 and e > 0:
                    eps.append({"season": s, "episode": e,
                                "title": str(v.get("name") or v.get("title") or "")[:60]})
            eps.sort(key=lambda x: (x["season"], x["episode"]))
        return {"ok": True, "id": imdb, "type": stype, "name": str(m["name"]),
                "year": str(m.get("releaseInfo") or m.get("year") or "")[:4],
                "poster": m.get("poster") if isinstance(m.get("poster"), str) else "",
                "eps": eps}
    return {"ok": False, "error": "title not found on Cinemeta"}


# --------------------------------------------------------------------------- self-test

if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Query Fast Combo / Cinemeta from the shell.")
    ap.add_argument("action", choices=["search", "streams", "meta"])
    ap.add_argument("query", help="search text, or an IMDb id (tt...) for streams/meta")
    ap.add_argument("--type", default="movie", choices=["movie", "series"])
    ap.add_argument("--season", type=int, default=1)
    ap.add_argument("--episode", type=int, default=1)
    ap.add_argument("--base", default=os.environ.get("FASTCOMBO_BASE_URL", "http://127.0.0.1:7000"))
    ap.add_argument("--key", default=os.environ.get("FASTCOMBO_ACCESS_KEY", ""))
    ap.add_argument("--token", default=os.environ.get("FASTCOMBO_TOKEN", ""))
    ap.add_argument("--prefer", default="best", choices=list(PREFER_ORDER))
    a = ap.parse_args()

    if a.action == "search":
        print(json.dumps(search_titles(a.query), indent=2))
    elif a.action == "meta":
        print(json.dumps(title_info(a.query), indent=2))
    else:
        sid = episode_id(a.query, a.season, a.episode) if a.type == "series" else a.query
        cands = fetch_streams(a.base, a.key, a.type, sid, a.token)
        best, fallbacks = pick(cands, a.prefer)
        print(f"{len(cands)} streams from Fast Combo; {len(fallbacks)} downloadable\n")
        for c in rank(cands, a.prefer)[:15]:
            flag = "BEST" if best and c.index == best.index else ("    " if c.downloadable else "skip")
            print(f"[{flag}] #{c.index:<3} {c.summary or '(no details)'}")
        if best:
            print(f"\npick: {best.url}")
        sys.exit(0 if best else 1)
