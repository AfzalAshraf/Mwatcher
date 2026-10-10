#!/usr/bin/env python3
"""
A pretend Plex Media Server, so scripts/plex_setup.py can be tested end to end without a
real Plex install (there is not one in CI, and claiming a real server needs a real account).

It implements the parts the automation touches, and it is deliberately strict about the
things real Plex is strict about:

  * a request without a valid token gets 401 once the server is claimed;
  * POST /library/sections rejects a scanner/agent pair that does not belong together, with
    the exact error text real Plex returns ("'agent' is missing or invalid ... new scanner
    needs to be paired with new agent") -- so a script that hardcodes stale names fails here
    the same way it fails on a real server;
  * DEMO_QUIRK=first400 reproduces the long-standing bug where the first library POST after
    a start returns 400 and a restart clears it, to prove the guidance is worth printing.

Env:
  DEMO_PORT      port to listen on                     (default 32400)
  DEMO_CLAIMED   start already signed in               (default 0)
  DEMO_TOKEN     the token to accept                   (default plexTokenDemo123)
  DEMO_QUIRK     "" | "first400"
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("DEMO_PORT", "32400"))
TOKEN = os.environ.get("DEMO_TOKEN", "plexTokenDemo123")
QUIRK = os.environ.get("DEMO_QUIRK", "")

# What this pretend server supports. New-style pairs first, exactly as a current Plex does.
SCANNERS = {"movie": ["Plex Movie", "Plex Video Files Scanner"],
            "show": ["Plex TV Series", "Plex Video Files Scanner"]}
AGENTS = {"movie": ["tv.plex.agents.movie", "com.plexapp.agents.none"],
          "show": ["tv.plex.agents.series", "com.plexapp.agents.none"]}
# The only pairings this server will accept.
VALID = {("tv.plex.agents.movie", "Plex Movie"),
         ("tv.plex.agents.series", "Plex TV Series"),
         ("com.plexapp.agents.none", "Plex Video Files Scanner")}

LOCK = threading.Lock()
STATE = {
    "claimed": os.environ.get("DEMO_CLAIMED", "0") == "1",
    "sections": [],
    "prefs": {},
    "next_id": 1,
    "posts": 0,
}


def container(**kw) -> bytes:
    body = {"MediaContainer": kw}
    return json.dumps(body).encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "FakePlex/1.43"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    # ---- plumbing -----------------------------------------------------------
    def _send(self, code: int, body: bytes = b"", ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Plex-Protocol", "1.0")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _token(self, qs) -> str:
        t = (qs.get("X-Plex-Token") or [""])[0]
        if not t:
            t = self.headers.get("X-Plex-Token", "")
        return t

    def _authed(self, qs) -> bool:
        with LOCK:
            claimed = STATE["claimed"]
        if not claimed:
            return True                      # unclaimed server accepts local requests
        return self._token(qs) == TOKEN

    def _route(self):
        u = urlparse(self.path)
        return u.path, parse_qs(u.query)

    # ---- GET ----------------------------------------------------------------
    def do_GET(self):
        path, qs = self._route()

        if path == "/identity":
            with LOCK:
                claimed = STATE["claimed"]
            if claimed and self._token(qs) != TOKEN:
                return self._send(401, container(error="missing or invalid token"))
            return self._send(200, container(
                size=0, claimed="1" if claimed else "0",
                machineIdentifier="fake-machine-id-0001",
                version="1.43.4.10903-fake"))

        if path == "/system/library/scanners/movie" or path == "/system/library/scanners/show":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            libtype = "movie" if path.endswith("movie") else "show"
            return self._send(200, container(
                size=len(SCANNERS[libtype]),
                Directory=[{"key": s, "type": libtype} for s in SCANNERS[libtype]]))

        if path == "/system/library/agents":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            libtype = (qs.get("type") or ["movie"])[0]
            names = AGENTS.get(libtype, AGENTS["movie"])
            return self._send(200, container(
                size=len(names),
                Directory=[{"identifier": a, "name": a.split(".")[-1].title(),
                            "type": libtype} for a in names]))

        if path == "/library/sections":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            with LOCK:
                secs = json.loads(json.dumps(STATE["sections"]))
            return self._send(200, container(size=len(secs), Directory=secs))

        m = re.match(r"^/library/sections/([^/]+)/refresh$", path)
        if m:
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            with LOCK:
                for s in STATE["sections"]:
                    if str(s.get("key")) == m.group(1):
                        s["refreshing"] = True
                        return self._send(200, container(size=0))
            return self._send(404, container(error="no such section"))

        if path == "/:/prefs":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            with LOCK:
                p = dict(STATE["prefs"])
            return self._send(200, container(size=len(p), Setting=[
                {"id": k, "value": v} for k, v in p.items()]))

        if path in ("/", "/healthz"):
            return self._send(200, container(size=0, fakePlex=True))

        return self._send(404, container(error=f"not found: {path}"))

    # ---- POST ---------------------------------------------------------------
    def do_POST(self):
        path, qs = self._route()
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)

        if path == "/myplex/claim":
            tok = (qs.get("token") or [""])[0]
            if not tok.startswith("claim-"):
                return self._send(400, container(error="invalid claim token"))
            with LOCK:
                STATE["claimed"] = True
            return self._send(200, container(size=0, claimed="1"))

        if path == "/library/sections":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            agent = (qs.get("agent") or [""])[0]
            scanner = (qs.get("scanner") or [""])[0]
            libtype = (qs.get("type") or [""])[0]
            name = (qs.get("name") or [""])[0]
            location = (qs.get("location") or [""])[0]
            language = (qs.get("language") or ["en-US"])[0]

            with LOCK:
                STATE["posts"] += 1
                first = STATE["posts"] == 1
                if QUIRK == "first400" and first:
                    # real Plex's actual wording, verbatim from a user's server log
                    return self._send(400, container(
                        error=("'agent' is missing or invalid, 'language' is invalid, "
                               "new scanner needs to be paired with new agent")))
                if libtype not in ("movie", "show", "artist", "photo"):
                    return self._send(400, container(error=f"invalid type: {libtype}"))
                if (agent, scanner) not in VALID:
                    return self._send(400, container(
                        error=("'agent' is missing or invalid, new scanner needs to be "
                               "paired with new agent")))
                if language not in ("en-US", "en", "fr-FR", "de-DE", "es-ES", "ar-AE"):
                    return self._send(400, container(error=f"'language' is invalid: {language}"))
                for s in STATE["sections"]:
                    for loc in s.get("Location") or []:
                        if loc.get("path") == location:
                            return self._send(400, container(
                                error=f"location already in section {s.get('key')}"))
                sid = str(STATE["next_id"]); STATE["next_id"] += 1
                sec = {"agent": agent, "scanner": scanner, "language": language,
                       "type": libtype, "title": name, "key": sid, "id": sid,
                       "uuid": f"fake-uuid-{sid}", "refreshing": False, "hidden": 0,
                       "Location": [{"id": int(sid), "path": location}]}
                STATE["sections"].append(sec)
            return self._send(201, container(size=1, Directory=[sec]))

        return self._send(404, container(error=f"not found: {path}"))

    # ---- DELETE -------------------------------------------------------------
    def do_DELETE(self):
        path, qs = self._route()
        m = re.match(r"^/library/sections/([^/]+)$", path)
        if m:
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            with LOCK:
                before = len(STATE["sections"])
                STATE["sections"] = [s for s in STATE["sections"]
                                     if str(s.get("key")) != m.group(1)]
                if len(STATE["sections"]) == before:
                    return self._send(404, container(error="no such section"))
            return self._send(200, container(size=0))
        return self._send(404, container(error=f"not found: {path}"))

    # ---- PUT ----------------------------------------------------------------
    def do_PUT(self):
        path, qs = self._route()
        m = re.match(r"^/library/sections/([^/]+)$", path)
        if m:
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            with LOCK:
                for sec in STATE["sections"]:
                    if str(sec.get("key")) != m.group(1):
                        continue
                    locs = qs.get("location") or []
                    if locs:
                        sec["Location"] = [{"id": i + 1, "path": p} for i, p in enumerate(locs)]
                    for field in ("title", "agent", "scanner", "language", "type"):
                        if qs.get(field):
                            sec[field] = qs[field][0]
                    return self._send(200, container(size=1, Directory=[sec]))
            return self._send(404, container(error="no such section"))

        if path == "/:/prefs":
            if not self._authed(qs):
                return self._send(401, container(error="unauthorized"))
            known = {"FSEventLibraryUpdatesEnabled", "FSEventLibraryPartialScanEnabled",
                     "allowMediaDeletion", "FriendlyName", "autoEmptyTrash"}
            with LOCK:
                for k, v in qs.items():
                    if k in known:
                        STATE["prefs"][k] = v[0]
            return self._send(200, container(size=0))
        return self._send(404, container(error=f"not found: {path}"))


def main() -> int:
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[fake-plex] Plex Media Server stand-in on http://127.0.0.1:{PORT}")
    print(f"[fake-plex] token: {TOKEN}   starts claimed: {STATE['claimed']}   quirk: {QUIRK or 'none'}")
    print("[fake-plex] scanners/agents are advertised, and mismatched pairs are rejected")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
