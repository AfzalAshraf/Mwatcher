#!/usr/bin/env python3
"""
fake_stremio_addon.py -- a pretend Stremio addon + file host, for testing without addons.

Fast Combo (https://github.com/AfzalAshraf/stremio-addons) ships empty: you add addons on
its control panel. This script stands in for one, so you can exercise the whole pipeline
locally -- Fast Combo's filtering, dedup, live probing and ranking, and then Mwatcher's
"pick the single best stream" logic -- without depending on any real scraper.

It serves three things on one port:

    GET /manifest.json                  a Stremio manifest declaring the stream resource
    GET /stream/movie/tt1375666.json    a ranked-ish list of streams (Stremio protocol)
    GET /stream/series/tt0903747:1:2.json
    GET /files/<name>?ms=<delay>        synthetic video bytes, WITH Range support

Range support matters: Fast Combo probes every link with `Range: bytes=0-1` and rejects
anything that is not 200/206, is a text/html page, or is under 500 KB without a video/*
content type. The `?ms=` delay simulates a slow file host so start-speed ranking is real.

The stream list deliberately includes entries Fast Combo should THROW AWAY (720p, a CAM
copy, a duplicate of the fastest link from a slower host, a torrent with no url) so you
can see the filtering working.

Run it:
    python3 demo/fake_stremio_addon.py                    # port 9912
    DEMO_PORT=9912 python3 demo/fake_stremio_addon.py

Then point Fast Combo at it:
    FC_ACCESS_KEY=testkey FC_ADMIN_PASSWORD=testpass PORT=7000 \
      FC_UPSTREAMS=http://127.0.0.1:9912/manifest.json node server.js
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

PORT = int(os.environ.get("DEMO_PORT", "9912"))
FILE_BYTES = int(os.environ.get("DEMO_FILE_BYTES", str(4 * 1024 * 1024)))  # > probe's 500 KB floor
PUBLIC = os.environ.get("DEMO_PUBLIC_URL", f"http://127.0.0.1:{PORT}")

# --- a tiny stand-in for Cinemeta (title search + metadata) -------------------------
# Real one: https://v3-cinemeta.strem.io  -- unreachable from some networks, and you do
# not want the demo depending on the internet. Point CINEMETA_URL here instead.
TITLES = {
    "tt1160419": dict(type="movie", name="Dune", year="2021", runtime=155),
    "tt1375666": dict(type="movie", name="Inception", year="2010", runtime=148),
    "tt0133093": dict(type="movie", name="The Matrix", year="1999", runtime=136),
    "tt0816692": dict(type="movie", name="Interstellar", year="2014", runtime=169),
    "tt0903747": dict(type="series", name="Breaking Bad", year="2008", runtime=47,
                       eps=[(1, 1, "Pilot"), (1, 2, "Cat's in the Bag..."), (1, 3, "...And the Bag's in the River"),
                            (2, 1, "Seven Thirty-Seven"), (2, 2, "Grilled")]),
    "tt0944947": dict(type="series", name="Game of Thrones", year="2011", runtime=57,
                       eps=[(1, 1, "Winter Is Coming"), (1, 2, "The Kingsroad")]),
}

# name, filename, size, host, start delay (ms), kind
# "direct" = http url we can download; "torrent" = infoHash only (a debrid service would be needed)
CATALOG = [
    dict(tag="4k",     fname="{slug}.2160p.UHD.BluRay.x265.HEVC.HDR10.mkv", size=12.0e9, host="MegaHost",   ms=900, kind="direct"),
    dict(tag="fast",   fname="{slug}.1080p.WEB-DL.H264.AC3.mkv",            size=2.10e9, host="FastCDN",    ms=120, kind="direct"),
    dict(tag="big",    fname="{slug}.1080p.BluRay.x264.DTS.mkv",            size=6.00e9, host="SlowMirror", ms=400, kind="direct"),
    dict(tag="dup",    fname="{slug}.1080p.WEB-DL.H264.AC3.mkv",            size=2.10e9, host="SecondBest", ms=700, kind="direct"),
    dict(tag="sd",     fname="{slug}.720p.WEBRip.x264.mkv",                 size=1.10e9, host="FastCDN",    ms=150, kind="direct"),
    dict(tag="cam",    fname="{slug}.HDCAM.x264.mkv",                       size=1.80e9, host="JunkHost",   ms=200, kind="direct"),
    dict(tag="torrent", fname="{slug}.1080p.BluRay.x264.SPARKS",            size=6.50e9, host="",           ms=0,   kind="torrent"),
]

INFOHASH = "a" * 20 + "deadbeef" + "b" * 12  # 40 hex chars, like a real torrent


def fmt_size(b: float) -> str:
    return f"{b / 1e9:.2f} GB" if b >= 1e9 else f"{round(b / 1e6)} MB"


def slug_for(imdb: str, year: str = "") -> str:
    t = TITLES.get(imdb, {})
    name = (t.get("name") or "Unknown.Title").replace(" ", ".")
    return f"{name}.{year or t.get('year') or ''}".strip(".")


def build_streams(imdb: str, title: str, episode_tag: str = "") -> list[dict]:
    """A Stremio-style stream list, with the junk entries Fast Combo is meant to drop."""
    slug = slug_for(imdb)
    out = []
    for i, c in enumerate(CATALOG):
        fname = c["fname"].format(slug=slug)
        head = f"{title}{(' ' + episode_tag) if episode_tag else ''}"
        desc = f"{head}\n{fmt_size(c['size'])} · {fname}\n{c['host'] or 'torrent'}"
        s = {
            "name": f"{c['host'] or 'Torrent'} {c['tag'].upper()}",
            "title": desc,
            "description": desc,
            "behaviorHints": {"filename": fname, "videoSize": int(c["size"]), "notWebReady": True},
        }
        if c["kind"] == "torrent":
            s["infoHash"] = INFOHASH
            s["fileIdx"] = 0
            s["name"] = "Torrent 1080p (needs debrid)"
            s["description"] = f"{head}\n{fmt_size(c['size'])}\n12 seeders"
        else:
            s["url"] = f"{PUBLIC}/files/{i}-{c['tag']}.mkv?ms={c['ms']}"
        out.append(s)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "fake-stremio-addon/1.0"
    protocol_version = "HTTP/1.1"  # needed so Range/206 + keep-alive behave

    # ---- helpers -----------------------------------------------------------
    def _json(self, code: int, body) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _serve_file(self, delay_ms: int) -> None:
        # DEMO_TRAP simulates the nastiest real-world failure: a host that answers the
        # Range probe like a video (so Fast Combo keeps it) but serves an HTML error page
        # when you actually ask for the content. This is what makes Plex show a title that
        # fails with "s1001 (Network)" -- and what the bridge's validation now catches.
        # The probe (bytes=0-1) passes; anything that wants real bytes gets the wall,
        # which is how these hosts behave whether you download or stream through.
        trap = os.environ.get("DEMO_TRAP", "")
        wanted_range = (self.headers.get("Range") or "").strip()
        is_probe = wanted_range in ("bytes=0-1", "bytes=0-0", "bytes=0-2")
        if trap and f"-{trap}." in self.path and not is_probe:
            body = (b"<!DOCTYPE html>\n<html><head><title>Just a moment...</title></head>\n"
                    b"<body><h1>Checking your browser</h1><p>Please enable JavaScript to continue.</p>"
                    b"</body></html>\n")
            # 200, not 403: the downloader "succeeds" and saves a web page as the movie.
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return

        total = FILE_BYTES
        rng = self.headers.get("Range") or ""
        start, end = 0, total - 1
        partial = False
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        if m:
            partial = True
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), total - 1)
            if start >= total:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{total}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        if delay_ms:
            time.sleep(min(delay_ms, 5000) / 1000)  # simulate a slow file host
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", "video/x-matroska")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.end_headers()
        if self.command == "HEAD":
            return
        # write real bytes so a downloader gets a genuine file
        chunk = b"\x1a\x45\xdf\xa3" + os.urandom(60 * 1024)  # EBML-ish header + noise
        sent = 0
        while sent < length:
            take = min(len(chunk), length - sent)
            try:
                self.wfile.write(chunk[:take])
            except (BrokenPipeError, ConnectionResetError):
                return  # Fast Combo cancels the body right after probing -- expected
            sent += take

    # ---- routes ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        seg = [s for s in u.path.split("/") if s]

        if u.path == "/manifest.json":
            return self._json(200, {
                "id": "community.mwatcher.fake",
                "version": "1.0.0",
                "name": "Fake Demo Addon",
                "description": "Synthetic streams for testing Mwatcher + Fast Combo locally",
                "resources": ["stream"],
                "types": ["movie", "series"],
                "idPrefixes": ["tt"],
                "behaviorHints": {"configurable": True, "configurationRequired": False},
            })

        if len(seg) >= 3 and seg[0] == "stream":
            stype, sid = seg[1], seg[2].replace(".json", "")
            imdb = sid.split(":")[0]
            t = TITLES.get(imdb)
            if imdb.startswith("tt") and (not t or t["type"] == ("series" if stype == "series" else "movie")):
                ep = ""
                if stype == "series" and ":" in sid:
                    parts = sid.split(":")
                    ep = f"S{int(parts[1] or 1):02d}E{int(parts[2] or 1):02d}"
                title = (t or {}).get("name") or "Unknown Title"
                return self._json(200, {"streams": build_streams(imdb, title, ep)})
            return self._json(200, {"streams": []})

        # --- Cinemeta stand-in: title search -----------------------------------------
        # real: https://v3-cinemeta.strem.io/catalog/movie/top/search=dune.json
        if len(seg) >= 4 and seg[0] == "catalog" and seg[3].startswith("search="):
            stype = seg[1]
            q = unquote(seg[3][len("search="):].replace(".json", "")).strip().lower()
            metas = [
                {"id": imdb, "imdb_id": imdb, "type": t["type"], "name": t["name"],
                 "releaseInfo": t["year"], "year": t["year"],
                 "poster": f"{PUBLIC}/logo.png", "runtime": f"{t.get('runtime', 120)} min"}
                for imdb, t in TITLES.items()
                if t["type"] == ("series" if stype == "series" else "movie")
                and (not q or q in t["name"].lower())
            ]
            return self._json(200, {"metas": metas})

        # --- Cinemeta stand-in: metadata + episode list ------------------------------
        # real: https://v3-cinemeta.strem.io/meta/series/tt0903747.json
        if len(seg) >= 3 and seg[0] == "meta":
            imdb = seg[2].replace(".json", "")
            t = TITLES.get(imdb)
            # The real Cinemeta answers only for the correct type -- mirror that, otherwise
            # callers that probe "series" then "movie" get the wrong one back.
            if not t or t["type"] != ("series" if seg[1] == "series" else "movie"):
                return self._json(404, {"meta": None})
            meta = {"id": imdb, "imdb_id": imdb, "type": t["type"], "name": t["name"],
                    "year": t["year"], "releaseInfo": t["year"],
                    "runtime": f"{t.get('runtime', 120)} min", "poster": f"{PUBLIC}/logo.png"}
            if t["type"] == "series":
                meta["videos"] = [
                    {"id": f"{imdb}:{s}:{e}", "title": name, "name": name, "season": s, "episode": e}
                    for s, e, name in t.get("eps", [])
                ]
            return self._json(200, {"meta": meta})

        if len(seg) >= 2 and seg[0] == "files":
            return self._serve_file(int((parse_qs(u.query).get("ms") or ["0"])[0]))

        if u.path == "/logo.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        return self._json(404, {"err": "not found", "path": u.path})

    do_HEAD = do_GET  # noqa: N815

    def log_message(self, fmt: str, *args) -> None:
        print(f"[fake-addon] {self.address_string()} {fmt % args}", flush=True)


class QuietServer(ThreadingHTTPServer):
    """Fast Combo cancels the response body right after probing a link; that is normal."""
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def main() -> None:
    print(f"[fake-addon] manifest:  {PUBLIC}/manifest.json", flush=True)
    print(f"[fake-addon] streams:   {PUBLIC}/stream/movie/tt1160419.json", flush=True)
    print(f"[fake-addon] cinemeta:  {PUBLIC}/catalog/movie/top/search=dune.json", flush=True)
    print(f"[fake-addon] metadata:  {PUBLIC}/meta/series/tt0903747.json", flush=True)
    print(f"[fake-addon] {len(TITLES)} demo titles, {len(CATALOG)} fake streams each "
          f"(1 torrent, 1 CAM, 1 duplicate, 1 sub-1080p -> Fast Combo drops the junk)", flush=True)
    QuietServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
