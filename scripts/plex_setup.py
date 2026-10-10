#!/usr/bin/env python3
"""
Plex automation for Mwatcher -- the "sit and relax" half of the install.

Everything else in install.sh is unattended already. The two things that normally need a
human are signing in to Plex and clicking through "Add Library" twice. This removes the
second one entirely and reduces the first to a single Google login in a browser.

What it does
------------
  --wait-signin      poll until this server is signed in to a plex.tv account
  --claim-token T    hand a claim-xxxx token to the server (headless / SSH path)
  --libraries        create the Movies and TV Shows libraries, then scan them
  --verify           report what Plex actually has, and whether it can play

Sign-in is detected by reading PlexOnlineToken out of Preferences.xml -- that is where
Plex itself records a successful claim -- and then confirming it against the server, so a
stale token from a previous account is not mistaken for a working one.

Libraries are created through POST /library/sections. The agent and scanner names are
DISCOVERED from the running server rather than hardcoded: Plex rejects a mismatched pair
with "'agent' is missing or invalid ... new scanner needs to be paired with new agent",
and the valid names have changed across versions. Discovery is what makes this work on
whatever version is actually installed.

Nothing here is destructive. Existing libraries are detected and left alone; a section is
only created when one covering that path does not already exist.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PLEX_PORT = int(os.environ.get("PLEX_PORT", "32400"))
BASE = os.environ.get("PLEX_BASE_URL", f"http://127.0.0.1:{PLEX_PORT}").rstrip("/")
MEDIA_DIR = os.environ.get("MEDIA_DIR", os.path.expanduser("~/media"))
SIGNIN_TIMEOUT = int(os.environ.get("PLEX_SIGNIN_TIMEOUT", "600"))

# Preferred agent/scanner per library type, newest first. Used only as a hint: whatever the
# server reports as available wins, because these strings have changed between versions.
PREFERRED = {
    "movie": {
        "agents": ["tv.plex.agents.movie", "com.plexapp.agents.imdb",
                   "com.plexapp.agents.themoviedb", "com.plexapp.agents.none"],
        "scanners": ["Plex Movie", "Plex Movie Scanner", "Plex Video Files Scanner"],
    },
    "show": {
        "agents": ["tv.plex.agents.series", "com.plexapp.agents.thetvdb",
                   "com.plexapp.agents.none"],
        "scanners": ["Plex TV Series", "Plex TV Show", "Plex Series Scanner",
                     "Plex Video Files Scanner"],
    },
}

# "Scan my library automatically" and friends. Best-effort: if a name is wrong on this
# version the call is simply ignored, and --libraries still triggers an explicit scan.
SERVER_PREFS = {
    "FSEventLibraryUpdatesEnabled": "1",       # scan automatically
    "FSEventLibraryPartialScanEnabled": "1",   # partial scan on change
    "allowMediaDeletion": "0",
}

C = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def out(sym: str, msg: str, colour: str = "") -> None:
    """One status line, matching install.sh's format."""
    if C:
        codes = {"g": "\033[32m", "y": "\033[33m", "e": "\033[31m",
                 "d": "\033[2m", "b": "\033[1m", "c": "\033[36m"}
        print(f"  {codes.get(colour, '')}{sym}\033[0m {msg}", flush=True)
    else:
        print(f"  {sym} {msg}", flush=True)


def ok(m: str) -> None: out("✓", m, "g")
def warn(m: str) -> None: out("!", m, "y")
def bad(m: str) -> None: out("✗", m, "e")
def info(m: str) -> None: out("·", m, "d")
def hdr(m: str) -> None:
    print(("\n\033[1m\033[36m%s\033[0m" % m) if C else f"\n{m}", flush=True)


# --------------------------------------------------------------------------- preferences

def prefs_candidates() -> list[str]:
    """Preferences.xml lives wherever this distro puts Plex's application support."""
    home = os.path.expanduser("~")
    run_user = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
    alt = f"/home/{run_user}" if run_user else home
    roots = [
        "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server",
        os.path.expanduser("~/Library/Application Support/Plex Media Server"),
        f"{alt}/Library/Application Support/Plex Media Server",
        "/config/Plex Media Server",
        "/opt/plexmediasever/Library/Application Support/Plex Media Server",
    ]
    extra = os.environ.get("PLEX_PREFS_DIR")
    if extra:
        roots.insert(0, extra)
    return [os.path.join(r, "Preferences.xml") for r in roots]


def prefs_path() -> str | None:
    for p in prefs_candidates():
        if os.path.isfile(p):
            return p
    return None


def read_pref(name: str) -> str:
    """One attribute out of Preferences.xml. Empty when absent or unreadable."""
    p = prefs_path()
    if not p:
        return ""
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.read(1 << 20)
    except OSError:
        # Root-owned on most installs; fall back to sudo rather than giving up.
        try:
            data = subprocess.run(["sudo", "-n", "cat", p], capture_output=True,
                                  text=True, timeout=15).stdout
        except Exception:
            return ""
    m = re.search(rf'{name}="([^"]*)"', data)
    return m.group(1) if m else ""


def err_text(body) -> str:
    """Plex wraps errors inconsistently: sometimes top-level, sometimes inside
    MediaContainer, sometimes a list of {message: ...}. A bare "HTTP 400" tells the user
    nothing, so dig the real sentence out."""
    if isinstance(body, str):
        return body[:300]
    if isinstance(body, dict):
        for k in ("error", "errors", "message"):
            v = body.get(k)
            if isinstance(v, str) and v:
                return v[:300]
            if isinstance(v, list) and v:
                parts = []
                for e in v:
                    parts.append(str(e.get("message") or e.get("error") or e)
                                 if isinstance(e, dict) else str(e))
                return "; ".join(parts)[:300]
        mc = body.get("MediaContainer")
        if isinstance(mc, dict):
            return err_text(mc)
    return ""


def server_token() -> str:
    return read_pref("PlexOnlineToken")


# --------------------------------------------------------------------------------- HTTP

def api(path: str, token: str = "", method: str = "GET", timeout: int = 20,
        params: dict | None = None):
    """Talk to Plex asking for JSON. Returns (status, parsed) -- parsed is {} on failure."""
    q = dict(params or {})
    if token:
        q["X-Plex-Token"] = token
    url = BASE + path
    if q:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("X-Plex-Product", "Mwatcher")
    req.add_header("X-Plex-Provides", "controller")
    req.add_header("X-Plex-Client-Identifier", read_pref("ProcessedMachineIdentifier") or "mwatcher")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body[:400]}
    except Exception as e:
        return 0, {"error": str(e)}


def server_up() -> bool:
    st, _ = api("/identity", timeout=8)
    return st in (200, 401)


def is_claimed(token: str = "") -> bool:
    """True only when the server accepts a token, not merely when one is on disk."""
    t = token or server_token()
    if not t:
        return False
    st, body = api("/identity", t, timeout=10)
    if st == 200:
        mc = (body or {}).get("MediaContainer", {})
        # Plex reports claimed="1" here; a bad token gives 401 instead.
        if str(mc.get("claimed", "")).lower() in ("1", "true"):
            return True
        # Some versions omit the attribute -- a 200 with a token is good enough.
        return True
    return False


# ------------------------------------------------------------------------------ sign-in

def wait_for_signin(timeout: int = SIGNIN_TIMEOUT, quiet: bool = False) -> str:
    """Block until the server is signed in. Returns the token, or '' on timeout."""
    shown = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        tok = server_token()
        if tok and is_claimed(tok):
            if not quiet:
                acct = read_pref("PlexOnlineUsername") or read_pref("PlexOnlineMail")
                ok(f"signed in to Plex" + (f" as {acct}" if acct else ""))
            return tok
        if not shown and not quiet:
            shown = True
            hdr("Sign in to Plex  (this is the only manual step)")
            info(f"open this on any device on your network, then choose Sign In -> Google:")
            url = web_url()
            print(f"      \033[1m{url}\033[0m" if C else f"      {url}", flush=True)
            info("no browser on this network? get a token instead:")
            print("      1. on any signed-in device open  https://plex.tv/claim", flush=True)
            print(f"      2. run  sudo bash install.sh auto --claim-token claim-XXXXXXXX", flush=True)
            info(f"waiting up to {timeout // 60} min for you to sign in…", )
        if not server_up() and not quiet:
            warn("Plex is not answering yet — is plexmediaserver running?")
        time.sleep(4)
    return ""


def claim(claim_token: str) -> bool:
    """POST /myplex/claim -- the server exchanges the token itself and stores the result."""
    if not claim_token.startswith("claim-"):
        warn("that does not look like a claim token (it should start with 'claim-')")
    if not server_up():
        bad(f"Plex is not answering on {BASE}")
        return False
    st, body = api("/myplex/claim", method="POST", timeout=30, params={"token": claim_token})
    if st in (200, 201):
        ok("claim accepted — waiting for the server to finish signing in")
        for _ in range(20):
            time.sleep(2)
            if is_claimed():
                acct = read_pref("PlexOnlineUsername") or read_pref("PlexOnlineMail")
                ok("signed in to Plex" + (f" as {acct}" if acct else ""))
                return True
        warn("the server took the token but is not reporting signed-in yet; re-run --verify")
        return is_claimed()
    bad(f"Plex refused the claim token (HTTP {st}) {err_text(body)}".rstrip())
    info("claim tokens expire after about 5 minutes — get a fresh one from https://plex.tv/claim")
    return False


def base_port() -> str:
    """The port BASE actually uses -- hardcoding 32400 prints the wrong URL when the
    server is elsewhere, which is exactly how someone ends up staring at a dead page."""
    try:
        pr = urllib.parse.urlparse(BASE)
        if pr.port:
            return str(pr.port)
    except ValueError:
        pass
    return str(PLEX_PORT)


def web_url() -> str:
    ip = lan_ip() or "<this-machine>"
    return f"http://{ip}:{base_port()}/web"


def lan_ip() -> str:
    try:
        r = subprocess.run(["ip", "route", "get", "1.1.1.1"], capture_output=True,
                           text=True, timeout=10)
        m = re.search(r"src (\d+\.\d+\.\d+\.\d+)", r.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------- discovery

def _names(payload, keys: tuple[str, ...]) -> list[str]:
    """Pull names/keys out of whatever shape Plex returned."""
    got: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k in keys:
                v = node.get(k)
                if isinstance(v, str) and v:
                    got.append(v)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    seen, ordered = set(), []
    for g in got:
        if g not in seen:
            seen.add(g)
            ordered.append(g)
    return ordered


def discover(kind: str, libtype: str, token: str) -> list[str]:
    """Ask the running server what it supports, so we never guess a stale name."""
    path = f"/system/library/scanners/{libtype}" if kind == "scanner" else "/system/library/agents"
    st, body = api(path, token, timeout=15,
                   params=None if kind == "scanner" else {"type": libtype})
    if st != 200:
        return []
    keys = ("key", "name", "title") if kind == "scanner" else ("identifier", "name")
    return _names(body, keys)


def pick(libtype: str, token: str) -> tuple[str, str, bool]:
    """Choose an agent/scanner pair. Returns (agent, scanner, discovered)."""
    pref = PREFERRED[libtype]
    agents = discover("agent", libtype, token)
    scanners = discover("scanner", libtype, token)
    agent = next((a for a in pref["agents"] if a in agents), "")
    scanner = next((s for s in pref["scanners"] if s in scanners), "")
    if agent and scanner:
        return agent, scanner, True
    # Discovery unavailable or incomplete: fall back to the modern defaults and let the
    # server's own error message tell us if the pairing is wrong for this version.
    return (agent or pref["agents"][0], scanner or pref["scanners"][0], bool(agents or scanners))


# ---------------------------------------------------------------------------- libraries

def sections(token: str) -> list[dict]:
    st, body = api("/library/sections", token, timeout=15)
    if st != 200:
        return []
    mc = (body or {}).get("MediaContainer", {})
    dirs = mc.get("Directory") or []
    return dirs if isinstance(dirs, list) else [dirs]


def section_covers(sec: dict, path: str) -> bool:
    for loc in sec.get("Location") or []:
        p = (loc or {}).get("path", "")
        if p and (os.path.normpath(p) == os.path.normpath(path)
                  or os.path.normpath(path).startswith(os.path.normpath(p) + os.sep)):
            return True
    return False


def create_section(token: str, name: str, libtype: str, location: str,
                   language: str = "en-US") -> tuple[bool, str]:
    agent, scanner, discovered = pick(libtype, token)
    params = {
        "name": name,
        "type": libtype,
        "agent": agent,
        "scanner": scanner,
        "language": language,
        "location": location,
        "includeAdult": "0",
        "enableAutoPhotoTags": "0",
    }
    st, body = api("/library/sections", token, method="POST", timeout=30, params=params)
    if st in (200, 201):
        note = "" if discovered else " (server did not report its scanners, used defaults)"
        return True, f"{name}: agent {agent}, scanner {scanner}{note}"
    return False, f"HTTP {st} {err_text(body)}".strip()


def refresh_section(token: str, sec_id) -> bool:
    st, _ = api(f"/library/sections/{sec_id}/refresh", token, timeout=20)
    return st in (200, 201, 202)


def set_server_prefs(token: str) -> list[str]:
    applied = []
    for k, v in SERVER_PREFS.items():
        st, _ = api("/:/prefs", token, method="PUT", timeout=15, params={k: v})
        if st in (200, 201, 202):
            applied.append(k)
    return applied


def do_libraries(token: str, language: str = "en-US") -> int:
    hdr("Plex libraries")
    if not token:
        bad("no Plex token — sign in first (see above)")
        return 1
    if not os.path.isdir(MEDIA_DIR):
        warn(f"{MEDIA_DIR} does not exist yet")

    wanted = [("Movies", "movie", os.path.join(MEDIA_DIR, "Movies")),
              ("TV Shows", "show", os.path.join(MEDIA_DIR, "TV Shows"))]
    existing = sections(token)
    problems = 0
    last_err = ""

    for name, libtype, path in wanted:
        os.makedirs(path, exist_ok=True)
        hit = next((s for s in existing if section_covers(s, path)), None)
        if hit:
            ok(f"'{hit.get('title', name)}' already covers {path} — left alone")
            continue
        good, detail = create_section(token, name, libtype, path, language)
        if good:
            ok(f"created library '{name}' → {path}")
            info(detail)
        else:
            bad(f"could not create '{name}': {detail}")
            last_err = detail
            problems += 1

    if problems and ("agent" in last_err.lower() or "scanner" in last_err.lower()):
        # Plex has a long-standing quirk where the first POST /library/sections after a
        # start returns 400 with "'agent' is missing or invalid"; a restart clears it.
        # Only suggest that when the error actually blames the agent, or the advice is
        # noise on top of an unrelated failure such as a bad language code.
        info("that wording is a known Plex quirk on the first call after a start — restart it once:")
        print("      sudo systemctl restart plexmediaserver", flush=True)
        print("      sudo bash install.sh auto", flush=True)

    applied = set_server_prefs(token)
    if applied:
        ok(f"automatic scanning enabled ({', '.join(applied)})")
    else:
        warn("could not set the auto-scan preference; the bridge triggers scans explicitly")

    existing = sections(token)
    for s in existing:
        sid = s.get("key") or s.get("id")
        if refresh_section(token, sid):
            ok(f"scanning '{s.get('title', sid)}'")
    return problems


# ------------------------------------------------------------------------------- verify

def do_verify(token: str) -> int:
    hdr("Verify")
    problems = 0
    if not server_up():
        bad(f"Plex is not answering on {BASE}")
        return 1
    ok(f"Plex answers on {BASE}")

    if token and is_claimed(token):
        acct = read_pref("PlexOnlineUsername") or read_pref("PlexOnlineMail") or "your account"
        ok(f"signed in as {acct}")
    else:
        bad("this server is not signed in to a plex.tv account")
        problems += 1

    secs = sections(token) if token else []
    if not secs:
        warn("no libraries yet")
        problems += 1
    for s in secs:
        locs = ", ".join((l or {}).get("path", "?") for l in (s.get("Location") or []))
        ok(f"library '{s.get('title', '?')}' ({s.get('type', '?')}) → {locs}")
        info(f"agent {s.get('agent', '?')} · scanner {s.get('scanner', '?')}")

    st, _ = api("/identity", token, timeout=8)
    info(f"this box on your LAN: {web_url()}")
    if st == 200:
        ok("reachable locally")
    return problems


def main() -> int:
    # Declared before any use below: `global` after a read of the same name is a SyntaxError.
    global C, BASE, MEDIA_DIR, SIGNIN_TIMEOUT
    ap = argparse.ArgumentParser(description="Plex automation for Mwatcher")
    ap.add_argument("--wait-signin", action="store_true",
                    help="block until this server is signed in to plex.tv")
    ap.add_argument("--claim-token", metavar="claim-XXXX",
                    help="hand a token from https://plex.tv/claim to the server")
    ap.add_argument("--libraries", action="store_true",
                    help="create the Movies and TV Shows libraries, then scan them")
    ap.add_argument("--verify", action="store_true", help="report Plex's actual state")
    ap.add_argument("--language", default=os.environ.get("PLEX_LANG", "en-US"))
    ap.add_argument("--timeout", type=int, default=SIGNIN_TIMEOUT)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--media-dir", default=None)
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.no_color:
        C = False
    if a.base_url:
        BASE = a.base_url.rstrip("/")
    if a.media_dir:
        MEDIA_DIR = a.media_dir
    SIGNIN_TIMEOUT = a.timeout

    rc = 0
    if a.claim_token:
        rc += 0 if claim(a.claim_token) else 1

    token = server_token()
    if a.wait_signin and not (token and is_claimed(token)):
        token = wait_for_signin(a.timeout, quiet=a.quiet)
        if not token:
            bad(f"still not signed in after {a.timeout // 60} min")
            rc += 1
    elif token and is_claimed(token):
        if not a.quiet:
            ok("already signed in to Plex")

    if a.libraries:
        rc += do_libraries(token, a.language)
    if a.verify:
        rc += do_verify(token)

    if not (a.claim_token or a.wait_signin or a.libraries or a.verify):
        ap.print_help()
    return 1 if rc else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
