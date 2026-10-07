#!/usr/bin/env python3
"""
fake_seerr.py -- a stand-in Seerr for testing the Mwatcher -> Seerr flow with no
Docker, no Radarr/Sonarr and no internet.

It implements exactly the surface seerr_source.py uses, with the same shapes and the
same auth behaviour as the real thing:

    GET  /api/v1/settings/about                 version/liveness
    GET  /api/v1/search?query=<title|tt-id>     {page,results[],totalCount}
    GET  /api/v1/movie/{tmdb|tt}                {..., mediaInfo:{status,requests[]}}
    GET  /api/v1/tv/{tmdb|tt}                   same
    POST /api/v1/request                        create a request
    GET  /api/v1/request?take=&skip=&sort=      {results[]}

Auth mirrors Seerr: no X-Api-Key -> 401, wrong key -> 401. That matters because it is
how the real failure shows up, and the bridge should report it clearly.

State is in memory and seeded from CATALOG below. A request goes to status 2 (pending)
unless SEERR_AUTO_APPROVE=1, in which case it goes straight to 3 (processing) like a
Seerr user with AUTO_APPROVE. Set SEERR_STATUS=5 on a title to simulate "already in
the library".

    DEMO_PORT=5055 SEERR_API_KEY=testkey python3 demo/fake_seerr.py
    SEERR_AUTO_APPROVE=1 python3 demo/fake_seerr.py     # skip the approval step
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("SEERR_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEMO_PORT") or os.environ.get("SEERR_PORT") or "5055")
API_KEY = os.environ.get("SEERR_API_KEY", "testkey")
AUTO_APPROVE = os.environ.get("SEERR_AUTO_APPROVE", "0").lower() in ("1", "true", "yes")
# SEERR_NO_SERVERS=1 simulates a fresh Seerr with nothing attached -- the #1 reason a
# request never turns into a file. SEERR_NO_PLEX=1 drops the Plex link too.
NO_SERVERS = os.environ.get("SEERR_NO_SERVERS", "0").lower() in ("1", "true", "yes")
NO_PLEX = os.environ.get("SEERR_NO_PLEX", "0").lower() in ("1", "true", "yes")
VERSION = os.environ.get("SEERR_VERSION", "2.7.0-fake")

# tmdb_id, type, title, year, imdb, initial mediaInfo.status (None = never requested)
CATALOG = [
    (693134, "movie", "Dune: Part Two", "2024", "tt15239678", None),
    (438631, "movie", "Dune", "2021", "tt1160419", 5),          # already in library
    (157336, "movie", "Interstellar", "2014", "tt0816692", None),
    (985617, "movie", "The Uprising", "2023", "tt27503384", 3),  # stuck processing
    (1396,   "tv",    "Breaking Bad", "2008", "tt0903747", None),
    (66732,  "tv",    "Stranger Things", "2016", "tt4574334", 4),
]
STATUS_LABELS = {1: "unknown", 2: "pending", 3: "processing", 4: "partially available", 5: "available"}

LOCK = threading.Lock()
REQUESTS: list[dict] = []
NEXT_REQUEST_ID = 100


def _rows():
    with LOCK:
        return list(CATALOG)


def _row_by(key: str, value):
    for row in _rows():
        if str(row[key]) == str(value):
            return row
    return None


def _hit(row: tuple, extra_status: int | None = None) -> dict:
    tmdb, mtype, title, year, imdb, status = row
    status = extra_status if extra_status is not None else status
    hit = {
        "id": tmdb,
        "mediaType": mtype,
        "title": title if mtype == "movie" else None,
        "name": title if mtype == "tv" else None,
        "releaseDate": year if mtype == "movie" else None,
        "firstAirDate": year if mtype == "tv" else None,
        "overview": f"Fake {mtype} entry for {title} ({year}).",
        "externalIds": {"imdbId": imdb, "tmdbId": tmdb},
        "posterPath": "",
    }
    if status is not None:
        hit["mediaInfo"] = {"status": status, "mediaType": mtype, "tmdbId": tmdb,
                            "requests": _requests_for(tmdb)}
    return hit


def _requests_for(tmdb_id) -> list[dict]:
    with LOCK:
        return [{"id": r["id"], "status": r["status"],
                 "seasons": [{"seasonNumber": s} for s in r.get("seasons") or []]}
                for r in REQUESTS if r.get("tmdbId") == tmdb_id]


def _detail(row: tuple) -> dict:
    tmdb, mtype, title, year, imdb, status = row
    body = {"id": tmdb, "imdbId": imdb, "overview": f"Fake {title}.",
            "externalIds": {"imdbId": imdb, "tmdbId": tmdb}}
    if mtype == "movie":
        body.update({"title": title, "releaseDate": f"{year}-01-01"})
    else:
        body.update({"name": title, "firstAirDate": f"{year}-01-01",
                     "seasons": [{"seasonNumber": n, "id": n} for n in range(1, 4)],
                     "numberOfSeasons": 3})
    if status is not None:
        body["mediaInfo"] = {"status": status, "mediaType": mtype, "tmdbId": tmdb,
                             "requests": _requests_for(tmdb)}
    return body


def _set_status(tmdb_id: int, status: int) -> None:
    global CATALOG
    with LOCK:
        CATALOG = [r if r[0] != tmdb_id else (r[0], r[1], r[2], r[3], r[4], status)
                   for r in CATALOG]


def _search(query: str) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for row in _rows():
        tmdb, mtype, title, year, imdb, status = row
        if q == imdb.lower() or q == str(tmdb):
            out.append((0, row))                     # exact id match wins
        elif q in title.lower():
            out.append((1, row))
        elif re.sub(r"[^a-z0-9]", "", q) and re.sub(r"[^a-z0-9]", "", q) in \
                re.sub(r"[^a-z0-9]", "", title.lower()):
            out.append((2, row))
    out.sort(key=lambda pair: pair[0])
    return [_hit(row) for _, row in out]


class QuietServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    server_version = "fake-seerr/1.0"
    protocol_version = "HTTP/1.1"

    # --- plumbing -----------------------------------------------------------
    def _send(self, code: int, body) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authed(self) -> bool:
        key = self.headers.get("X-Api-Key") or ""
        if key != API_KEY:
            self._send(401, {"errors": [{"message": "You do not have permission to access this endpoint"}]})
            return False
        return True

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[fake-seerr] %s\n" % (fmt % args))

    # --- routes -------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path, qs = parsed.path, urllib.parse.parse_qs(parsed.query)
        if not self._authed():
            return
        if path == "/api/v1/settings/about":
            self._send(200, {"version": VERSION, "timezone": "Etc/UTC",
                             "apiEnabled": True, "applicationUrl": f"http://{HOST}:{PORT}"})
        elif path == "/api/v1/search":
            results = _search((qs.get("query") or [""])[0])
            self._send(200, {"page": 1, "results": results, "totalPages": 1,
                             "totalCount": len(results)})
        elif path == "/api/v1/settings/radarr":
            self._send(200, [] if NO_SERVERS else [
                {"id": 0, "name": "Radarr", "baseUrl": "http://radarr:7878",
                 "apiKey": "x", "active": True, "is4k": False,
                 "externalUrl": "http://radarr:7878"}])
        elif path == "/api/v1/settings/sonarr":
            self._send(200, [] if NO_SERVERS else [
                {"id": 0, "name": "Sonarr", "baseUrl": "http://sonarr:8989",
                 "apiKey": "x", "active": True, "is4k": False,
                 "externalUrl": "http://sonarr:8989"}])
        elif path == "/api/v1/settings/plex":
            self._send(200, {"ip": "", "port": 32400} if NO_PLEX else
                       {"ip": "host.docker.internal", "port": 32400, "useSsl": False,
                        "library": [{"id": "1", "name": "Movies", "type": "movie"}]})
        elif path == "/api/v1/request":
            take = int((qs.get("take") or ["20"])[0])
            with LOCK:
                items = list(reversed(REQUESTS))[:take]
            self._send(200, {"pageInfo": {"page": 1, "pages": 1, "results": len(items), "total": len(REQUESTS)},
                             "results": items})
        elif re.fullmatch(r"/api/v1/(movie|tv)/[^/]+", path):
            mtype, ident = path.split("/")[-2:]
            row = None
            if ident.startswith("tt"):
                row = _row_by(4, ident)
            else:
                row = _row_by(0, ident)
            if not row or row[1] != mtype:
                self._send(404, {"errors": [{"message": "Media not found"}]})
                return
            self._send(200, _detail(row))
        else:
            self._send(404, {"errors": [{"message": f"no such route: {path}"}]})

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if not self._authed():
            return
        if path != "/api/v1/request":
            self._send(404, {"errors": [{"message": f"no such route: {path}"}]})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode() or "{}")
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"errors": [{"message": f"bad JSON: {exc}"}]})
            return

        mtype = body.get("mediaType")
        tmdb = body.get("mediaId")
        if mtype not in ("movie", "tv") or not tmdb:
            self._send(400, {"errors": [{"message": "mediaType and mediaId are required"}]})
            return
        row = _row_by(0, tmdb)
        if not row or row[1] != mtype:
            self._send(404, {"errors": [{"message": "Media not found"}]})
            return

        seasons = body.get("seasons")
        if mtype == "tv" and seasons in (None, "", []):
            self._send(400, {"errors": [{"message": "At least one season must be requested"}]})
            return
        season_numbers = None
        if mtype == "tv":
            if isinstance(seasons, str) and seasons.lower() in ("all", "missing"):
                season_numbers = [1, 2, 3] if seasons.lower() == "all" else [1]
            else:
                season_numbers = [int(s) for s in seasons]

        global NEXT_REQUEST_ID
        # Two DIFFERENT enums, easy to mix up -- which is exactly why doctor() checks both:
        #   RequestStatus (the request itself): 1 pending approval, 2 approved,
        #                                       3 declined, 4 processing, 5 failed
        #   MediaStatus  (the media record)  : 2 pending, 3 processing, 5 available
        req_status = 4 if AUTO_APPROVE else 1
        media_status = 3 if AUTO_APPROVE else 2
        with LOCK:
            rid = NEXT_REQUEST_ID
            NEXT_REQUEST_ID += 1
            rec = {"id": rid, "status": req_status, "media": {
                       "id": row[0], "tmdbId": row[0], "mediaType": mtype,
                       "status": media_status},
                   "requestedBy": {"id": 1, "displayName": "admin", "email": "admin@local"},
                   "type": mtype}
            REQUESTS.append(rec)
        _set_status(row[0], media_status)

        label = "approved+processing" if AUTO_APPROVE else "pending approval"
        sys.stderr.write(f"[fake-seerr] REQUEST {mtype} {row[2]} ({row[0]}) "
                         f"seasons={season_numbers} -> id={rid} {label}\n")
        self._send(201, rec)


def main() -> int:
    httpd = QuietServer((HOST, PORT), Handler)
    sys.stderr.write(
        f"[fake-seerr] Seerr {VERSION} stand-in on http://{HOST}:{PORT}\n"
        f"[fake-seerr] api key: {API_KEY}   auto-approve: {AUTO_APPROVE}\n"
        f"[fake-seerr] {len(CATALOG)} titles seeded; requests are held in memory\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
