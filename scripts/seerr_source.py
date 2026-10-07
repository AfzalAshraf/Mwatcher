#!/usr/bin/env python3
"""
seerr_source.py -- talk to Seerr (https://github.com/fallenbagel/seerr) so a title you
browse can be *requested* and downloaded by your own server, with no debrid service.

What Seerr is, and is not
-------------------------
Seerr is the request/approval layer. It does NOT download anything itself:

    you  ->  Seerr (5055)  ->  Radarr (7878) / Sonarr (8989)
                                    |
                                    +-> Prowlarr (9696)   find the release (torrent/NZB)
                                    +-> qBittorrent (8080) download it
                                    +-> import into  ~/media/...  -> Plex picks it up

So the chain needs Radarr/Sonarr + a download client behind Seerr. What you get for
that is: no debrid subscription, requests are owned by your server forever, quality
profiles/subtitles/monitoring are handled properly, and it survives link rot.

API notes (verified against docs.seerr.dev, Seerr API v1.0.0)
--------------------------------------------------------------
* Every call needs the header  ``X-Api-Key: <key>``  -- key from
  Seerr -> Settings -> General.  Treat it as an ADMIN credential: anyone holding it
  can change server settings, so keep it in a chmod 600 file and never expose it to
  a browser.
* Requests are keyed by **TMDB id**, not IMDb. ``search()`` bridges the gap and
  accepts an IMDb id (``tt1234567``) or free text as the query.
* ``POST /api/v1/request`` body: ``{"mediaType": "movie"|"tv", "mediaId": <tmdb>}``,
  plus ``seasons`` ("all" or [1,2,3]) for TV and optional ``is4k``, ``serverId``,
  ``profileId``, ``rootFolder``, ``tags``. The caller needs REQUEST permission;
  ADMIN or AUTO_APPROVE makes it go straight to Radarr/Sonarr.
* ``mediaInfo.status`` on search/media results: 1 unknown, 2 pending, 3 processing,
  4 partially available, 5 available. Absent when never requested.

CLI (handy for testing without the bridge):

    python3 scripts/seerr_source.py --status
    python3 scripts/seerr_source.py --search "The Uprising"
    python3 scripts/seerr_source.py --search tt1234567
    python3 scripts/seerr_source.py --request movie --tmdb 693134
    python3 scripts/seerr_source.py --request-title "Dune" --year 2021
    python3 scripts/seerr_source.py --status-of movie --tmdb 693134
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SEERR_URL = os.environ.get("SEERR_URL", "http://127.0.0.1:5055").rstrip("/")
SEERR_API_KEY = os.environ.get("SEERR_API_KEY", "")
SEERR_TIMEOUT = float(os.environ.get("SEERR_TIMEOUT", "20"))
# How TV requests behave when you do not say otherwise.
SEERR_TV_SEASONS = os.environ.get("SEERR_TV_SEASONS", "all")  # "all", "missing", or "1,2"
SEERR_IS4K = os.environ.get("SEERR_IS4K", "0").lower() in ("1", "true", "yes")

STATUS_LABELS = {
    1: "unknown",
    2: "pending",          # requested, waiting for approval
    3: "processing",       # approved, Radarr/Sonarr is fetching it
    4: "partially available",
    5: "available",        # in your library already
}


class SeerrError(RuntimeError):
    """Seerr refused, is unreachable, or answered with something unexpected."""

    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def configured() -> bool:
    """True when we have both a URL and an API key to work with."""
    return bool(SEERR_URL and SEERR_API_KEY)


# --------------------------------------------------------------------------- http

def _request(method: str, path: str, body: dict | None = None,
             base_url: str = "", api_key: str = "", timeout: float | None = None) -> dict:
    url = (base_url or SEERR_URL).rstrip("/") + "/api/v1" + path
    key = api_key or SEERR_API_KEY
    if not key:
        raise SeerrError(
            "SEERR_API_KEY is not set. Get it from Seerr -> Settings -> General, then put "
            "it in ~/.config/mwatcher/bridge.env (chmod 600).")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Api-Key", key)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout or SEERR_TIMEOUT) as resp:
            raw = resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")[:800]
        # Seerr wraps its own explanation in {"errors":[{"message": "..."}]} -- that text
        # beats a generic HTTP hint, so prefer it when it is there.
        detail = ""
        try:
            msgs = [e.get("message") for e in (json.loads(raw).get("errors") or []) if isinstance(e, dict)]
            detail = "; ".join(m for m in msgs if m)
        except Exception:  # noqa: BLE001
            pass
        hint = {
            401: "Seerr rejected the API key (Settings -> General -> API Key)",
            403: "this user lacks the REQUEST permission in Seerr",
            404: "Media not found" if "not found" in detail.lower() else
                 f"Seerr has no route {path} (older version?)",
            429: "Seerr is rate-limiting you -- try again shortly",
            500: "Seerr blew up on this request -- check its logs",
        }.get(exc.code, "")
        text = detail or hint
        raise SeerrError(f"Seerr {method} {path} -> HTTP {exc.code}" + (f": {text}" if text else ""),
                         status=exc.code, body=raw) from None
    except urllib.error.URLError as exc:
        raise SeerrError(
            f"cannot reach Seerr at {url}: {exc.reason}. Is it running? "
            f"(docker compose ps seerr, or systemctl status seerr)") from None
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SeerrError(f"Seerr answered {path} with non-JSON ({raw[:120]!r})") from exc


def _get(path: str, **kw) -> dict:
    return _request("GET", path, None, **kw)


def _post(path: str, body: dict, **kw) -> dict:
    return _request("POST", path, body, **kw)


# ------------------------------------------------------------------------- status

def server_status(**kw) -> dict:
    """
    Cheap liveness + version check. Returns {"ok", "version", "base_url"} and raises
    SeerrError with a useful message when Seerr is not reachable or the key is wrong.
    """
    about = _get("/settings/about", **kw)
    return {
        "ok": True,
        "version": about.get("version") or "?",
        "base_url": (kw.get("base_url") or SEERR_URL),
        "timezone": about.get("timezone") or "",
    }


# ------------------------------------------------------------------------- search

def _norm_hit(hit: dict) -> dict:
    """Flatten one Seerr search result into what the bridge cares about."""
    mtype = hit.get("mediaType") or ""
    status = (hit.get("mediaInfo") or {}).get("status")
    year = ""
    for field in ("releaseDate", "firstAirDate"):
        if hit.get(field):
            year = str(hit[field])[:4]
            break
    return {
        "tmdb_id": hit.get("id"),
        "media_type": "movie" if mtype == "movie" else ("tv" if mtype in ("tv", "series") else mtype),
        "title": hit.get("title") or hit.get("name") or "",
        "year": year,
        "overview": hit.get("overview") or "",
        "status": status,
        "status_label": STATUS_LABELS.get(status, "not requested"),
        "imdb_id": (hit.get("externalIds") or {}).get("imdbId") or "",
        "poster": hit.get("posterPath") or "",
    }


def search(query: str, limit: int = 10, **kw) -> list[dict]:
    """
    Search Seerr (which proxies TMDB). Accepts an IMDb id like tt0816692 or free text.
    Returns only movie/tv hits -- Seerr also returns people, which are useless here.
    """
    q = (query or "").strip()
    if not q:
        raise SeerrError("empty search query")
    data = _get("/search?query=" + urllib.parse.quote(q), **kw)
    hits = [_norm_hit(h) for h in (data.get("results") or [])]
    playable = [h for h in hits if h["media_type"] in ("movie", "tv") and h.get("tmdb_id")]
    return playable[:limit]


def _year_of(value) -> str:
    return str(value or "")[:4]


def find(title: str = "", year=None, imdb: str = "", kind: str | None = None,
         **kw) -> dict:
    """
    Resolve a title (and optional IMDb id / year / kind) to one Seerr/TMDB hit.

    IMDb first -- it is exact. Then title, filtered by year and kind if given, and
    finally the top title match. Raises SeerrError when nothing credible is found.
    """
    want_kind = {"series": "tv", "show": "tv", "tv": "tv", "movie": "movie"}.get(
        (kind or "").lower(), (kind or "").lower() or None)
    candidates: list[dict] = []
    tried: list[str] = []

    if imdb:
        tried.append(f"imdb={imdb}")
        try:
            candidates = search(imdb, **kw)
        except SeerrError:
            candidates = []
        # Seerr's search may not index by IMDb id on every version -- the /movie and
        # /tv lookups below also accept an IMDb id, so fall through to those.
        if not candidates:
            for probe in ("movie", "tv"):
                try:
                    data = _get(f"/{probe}/{imdb}", **kw)
                except SeerrError:
                    continue
                if data.get("id"):
                    hit = _norm_hit({**data, "mediaType": probe})
                    hit["tmdb_id"] = data["id"]
                    candidates = [hit]
                    break

    if not candidates and title:
        tried.append(f"title={title!r}")
        candidates = search(title, **kw)

    if not candidates:
        raise SeerrError(f"Seerr found nothing for {' / '.join(tried) or 'that query'}")

    year = _year_of(year)
    exact = candidates
    if want_kind:
        exact = [c for c in candidates if c["media_type"] == want_kind] or candidates
    if year:
        dated = [c for c in exact if c["year"] == year]
        if dated:
            return dated[0]
    if imdb:
        for c in exact:
            if c.get("imdb_id") == imdb:
                return c
    if title:
        tl = title.strip().lower()
        for c in exact:
            if c["title"].strip().lower() == tl:
                return c
    return exact[0]


# ----------------------------------------------------------------------- requests

def request(media_type: str, tmdb_id, seasons=None, is4k: bool | None = None,
            root_folder: str = "", profile_id=None, server_id=None,
            tags: list | None = None, **kw) -> dict:
    """
    Create a request in Seerr. This is the "download it to my server, no debrid" step:
    Seerr hands it to Radarr/Sonarr, which find and download the release.

    Returns {"ok", "request_id", "status", "status_label", "media_type", "tmdb_id",
             "already_available", "message"}.
    """
    mtype = "tv" if (media_type or "").lower() in ("tv", "series", "show") else "movie"
    if not tmdb_id:
        raise SeerrError("request() needs a TMDB id (use find() first)")

    body: dict = {"mediaType": mtype, "mediaId": int(tmdb_id)}
    if mtype == "tv":
        if seasons in (None, "", "all"):
            body["seasons"] = "all" if SEERR_TV_SEASONS == "all" else seasons or "all"
        elif isinstance(seasons, str) and seasons.lower() == "missing":
            body["seasons"] = "missing"
        else:
            numbers = seasons if isinstance(seasons, list) else [
                int(n) for n in str(seasons).replace(" ", "").split(",") if n.isdigit()]
            body["seasons"] = sorted({int(n) for n in numbers})
    flag = SEERR_IS4K if is4k is None else bool(is4k)
    if flag:
        body["is4k"] = True
    if root_folder:
        body["rootFolder"] = root_folder
    if profile_id is not None:
        body["profileId"] = int(profile_id)
    if server_id is not None:
        body["serverId"] = int(server_id)
    if tags:
        body["tags"] = list(tags)

    # Ask first: if it is already in the library, do not create noise.
    existing = media_status(mtype, tmdb_id, **kw)
    if existing.get("status") == 5:
        return {"ok": True, "request_id": None, "status": 5, "status_label": "available",
                "media_type": mtype, "tmdb_id": int(tmdb_id), "already_available": True,
                "message": "already in your library -- nothing to request"}

    data = _post("/request", body, **kw)
    status = (data.get("media") or {}).get("status") or data.get("status")
    rid = data.get("id") or (data.get("media") or {}).get("id")
    return {
        "ok": True,
        "request_id": rid,
        "status": status,
        "status_label": STATUS_LABELS.get(status, "requested"),
        "media_type": mtype,
        "tmdb_id": int(tmdb_id),
        "already_available": False,
        "message": _request_message(status, mtype, body.get("seasons")),
        "requested": data.get("requestedBy", {}).get("displayName") if isinstance(data.get("requestedBy"), dict) else None,
    }


def _request_message(status, mtype: str, seasons) -> str:
    if status == 2:
        return ("requested -- waiting for approval in Seerr (Settings -> Users -> "
                "Auto-Approve to skip this step)")
    if status == 3:
        return f"approved -- Radarr/Sonarr is fetching this {mtype} now"
    if status in (4, 5):
        return "already (partly) in your library"
    where = f" seasons={seasons}" if mtype == "tv" and seasons else ""
    return f"request sent to Seerr for {mtype}{where}"


def request_title(title: str = "", year=None, imdb: str = "", kind: str | None = None,
                  seasons=None, is4k: bool | None = None, **kw) -> dict:
    """Convenience: resolve a human query, then request it. One call from the bridge."""
    hit = find(title=title, year=year, imdb=imdb, kind=kind, **kw)
    out = request(hit["media_type"], hit["tmdb_id"], seasons=seasons, is4k=is4k, **kw)
    out["title"] = hit["title"]
    out["year"] = hit["year"]
    out["imdb_id"] = hit.get("imdb_id") or imdb or ""
    return out


def media_status(media_type: str, tmdb_id, **kw) -> dict:
    """
    Is this in the library, requested, or nothing yet? Cheap enough to poll while a
    job runs, so the dashboard can show "downloading via Radarr".
    """
    mtype = "tv" if (media_type or "").lower() in ("tv", "series", "show") else "movie"
    try:
        data = _get(f"/{mtype}/{tmdb_id}", **kw)
    except SeerrError as exc:
        if exc.status in (404,):
            return {"status": None, "status_label": "not requested"}
        raise
    info = data.get("mediaInfo") or {}
    status = info.get("status")
    reqs = info.get("requests") or []
    return {
        "status": status,
        "status_label": STATUS_LABELS.get(status, "not requested"),
        "tmdb_id": data.get("id"),
        "media_type": mtype,
        "title": data.get("title") or data.get("name") or "",
        "requests": [{
            "id": r.get("id"),
            "status": r.get("status"),
            "seasons": sorted({s.get("seasonNumber") for s in (r.get("seasons") or [])
                               if s.get("seasonNumber")}),
        } for r in reqs],
    }


def pending_requests(take: int = 20, **kw) -> list[dict]:
    """Newest requests, so the dashboard can show what is queued for download."""
    data = _get(f"/request?take={int(take)}&skip=0&sort=added", **kw)
    out = []
    for r in data.get("results") or []:
        media = r.get("media") or {}
        out.append({
            "id": r.get("id"),
            "status": r.get("status"),
            "media_type": media.get("mediaType"),
            "tmdb_id": media.get("tmdbId"),
            "status_label": STATUS_LABELS.get(media.get("status"), "?"),
            "requested_by": (r.get("requestedBy") or {}).get("displayName"),
        })
    return out


# ------------------------------------------------------------------------- doctor

# Seerr's *request* status enum (different from the media status enum above).
REQUEST_STATUS = {1: "pending approval", 2: "approved", 3: "declined",
                  4: "processing", 5: "failed"}


def doctor(base_url: str = "", api_key: str = "", verbose: bool = True) -> tuple[list[str], int]:
    """
    Health-check the whole request path -- the thing that decides whether "I requested
    it" ever becomes "the file is on my server".

    Returns (lines, problem_count). Called by install.sh doctor so the logic lives in
    one testable place instead of being re-implemented in bash.
    """
    kw = {"base_url": (base_url or SEERR_URL).rstrip("/"), "api_key": api_key or SEERR_API_KEY}
    lines: list[str] = []
    problems = 0
    warned = False

    def ok(msg: str) -> None:
        lines.append(f"  \033[32m✓\033[0m {msg}" if verbose else f"  OK   {msg}")

    def bad(msg: str) -> None:
        nonlocal problems
        problems += 1
        lines.append(f"  \033[31m✗\033[0m {msg}" if verbose else f"  FAIL {msg}")

    def warn(msg: str) -> None:
        nonlocal warned
        warned = True
        lines.append(f"  \033[33m!\033[0m {msg}" if verbose else f"  WARN {msg}")

    def note(msg: str) -> None:
        lines.append(f"  \033[2m·\033[0m {msg}" if verbose else f"       {msg}")

    if not kw["api_key"]:
        bad("SEERR_API_KEY is not set -- copy it from Seerr -> Settings -> General\n"
            "       and put it in ~/.config/mwatcher/bridge.env (chmod 600)")
        return lines, problems

    # 1. Is Seerr there, and does it like our key?
    try:
        about = _get("/settings/about", **kw)
        ok(f"Seerr {about.get('version', '?')} answers at {kw['base_url']} and accepts the API key")
    except SeerrError as exc:
        # A 401/403 means Seerr IS running and answered -- the credential is the problem,
        # so do not send them off to restart containers.
        hint = ("the API key is wrong or was regenerated -- Seerr -> Settings -> General,\n"
                "       then update SEERR_API_KEY in ~/.config/mwatcher/bridge.env"
                if exc.status in (401, 403) else
                "is the container running?  cd ~/mwatcher-seerr && docker compose up -d\n"
                "       (and check SEERR_URL -- it must be reachable from THIS machine)")
        bad(f"Seerr is not usable at {kw['base_url']}: {exc}\n       {hint}")
        return lines, problems

    # 2. Something has to actually download. This is the #1 reason requests never arrive.
    for app, port in (("radarr", 7878), ("sonarr", 8989)):
        try:
            servers = _get(f"/settings/{app}", **kw)
        except SeerrError as exc:
            warn(f"cannot read Seerr's {app} settings ({exc})")
            continue
        servers = servers if isinstance(servers, list) else [servers]
        live = [s for s in servers if isinstance(s, dict) and s.get("baseUrl")]
        inactive = [s for s in live if s.get("active") is False]
        if not live:
            bad(f"no {app.capitalize()} server is attached to Seerr -- requests for "
                f"{'movies' if app == 'radarr' else 'TV shows'} will sit there forever\n"
                f"       Fix: Seerr -> Settings -> Servers -> Add {app.capitalize()} "
                f"(host: {app}, port: {port}, plus that app's API key)")
        elif inactive:
            warn(f"{app.capitalize()} is attached but switched OFF -- re-enable it in "
                 f"Seerr -> Settings -> Servers")
        else:
            ok(f"{app.capitalize()} attached: " + ", ".join(
                str(s.get("name") or s.get("baseUrl")) for s in live))

    # 3. Seerr needs Plex to know what you already have, and to mark things available.
    try:
        plex = _get("/settings/plex", **kw)
        ip = plex.get("ip") or ""
        if ip:
            ok(f"Plex attached ({ip}:{plex.get('port', 32400)})")
        else:
            warn("no Plex server configured in Seerr -- it cannot tell what is already "
                 "in your library, so availability never updates\n"
                 "       Fix: Seerr -> Settings -> Media Server -> Plex "
                 "(hostname host.docker.internal, port 32400 when Plex is on the host)")
    except SeerrError as exc:
        warn(f"cannot read Seerr's Plex settings ({exc})")

    # 4. Requests stuck waiting on a human.
    try:
        data = _get("/request?take=50&skip=0&sort=added", **kw)
        results = data.get("results") or []
        waiting = [r for r in results if r.get("status") == 1]
        failed = [r for r in results if r.get("status") == 5]
        declined = [r for r in results if r.get("status") == 3]
        if waiting:
            warn(f"{len(waiting)} request(s) are waiting for approval -- nothing downloads "
                 f"until they are approved\n"
                 f"       Fix: approve them at {kw['base_url']}/requests, or Seerr -> "
                 f"Settings -> Users -> enable Auto-Approve so this never happens")
        if failed:
            bad(f"{len(failed)} request(s) FAILED -- open {kw['base_url']}/requests to see why "
                f"(usually no indexer has that release, or the download client is unreachable)")
        if declined:
            note(f"{len(declined)} request(s) were declined")
        if not (waiting or failed or declined):
            ok(f"{len(results)} recent request(s), none stuck")
    except SeerrError as exc:
        warn(f"cannot list requests ({exc})")

    if problems:
        note(f"{problems} problem(s) with the request path -- fix the ✗ lines above")
    elif warned:
        note("Seerr is wired up correctly; the warnings above are why a request has not "
             "turned into a file yet")
    else:
        note("the request path looks healthy -- if a title still has not arrived, the "
             "release is probably not on your indexers (check Prowlarr)")
    return lines, problems


# ---------------------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ask Seerr to request a title so your own server downloads it.",
        epilog="Environment: SEERR_URL (http://127.0.0.1:5055), SEERR_API_KEY (required), "
               "SEERR_TV_SEASONS (all|missing|1,2), SEERR_IS4K (0).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="is Seerr reachable, and what version?")
    ap.add_argument("--search", metavar="QUERY", help="search by title or tt-id, print TMDB ids")
    ap.add_argument("--request", choices=("movie", "tv"), help="request a TMDB id you already know")
    ap.add_argument("--tmdb", help="TMDB id for --request / --status-of")
    ap.add_argument("--seasons", help="for --request tv: all, missing, or 1,3")
    ap.add_argument("--4k", dest="is4k", action="store_true", help="request the 4K variant")
    ap.add_argument("--request-title", metavar="TITLE", help="resolve a title, then request it")
    ap.add_argument("--year")
    ap.add_argument("--imdb", help="prefer this tt-id when resolving --request-title")
    ap.add_argument("--kind", choices=("movie", "tv"), help="disambiguate --request-title")
    ap.add_argument("--status-of", choices=("movie", "tv"), help="library/request state of --tmdb")
    ap.add_argument("--pending", action="store_true", help="list recent requests")
    ap.add_argument("--doctor", action="store_true",
                    help="health-check the whole request path (Seerr -> Radarr/Sonarr -> Plex)")
    ap.add_argument("--no-color", action="store_true", help="plain text for --doctor")
    ap.add_argument("--no-summary", action="store_true",
                    help="with --doctor: skip the trailing tally (the caller prints its own)")
    ap.add_argument("--url", help="override SEERR_URL")
    ap.add_argument("--api-key", help="override SEERR_API_KEY")
    args = ap.parse_args(argv)

    kw = {}
    if args.url:
        kw["base_url"] = args.url.rstrip("/")
    if args.api_key:
        kw["api_key"] = args.api_key

    def show(obj) -> int:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return 0

    try:
        if args.status:
            return show(server_status(**kw))
        if args.search:
            return show({"query": args.search, "results": search(args.search, **kw)})
        if args.pending:
            return show({"requests": pending_requests(**kw)})
        if args.doctor:
            lines, problems = doctor(verbose=not args.no_color, **kw)
            print("\n".join(lines))
            if not args.no_summary:
                print(f"\n  {'no problems found' if not problems else f'{problems} problem(s) found'}")
            # exit code carries the count so callers (install.sh doctor) can tally it
            return min(problems, 100)
        if args.status_of:
            if not args.tmdb:
                ap.error("--status-of needs --tmdb")
            return show(media_status(args.status_of, args.tmdb, **kw))
        if args.request:
            if not args.tmdb:
                ap.error("--request needs --tmdb")
            return show(request(args.request, args.tmdb, seasons=args.seasons,
                                is4k=True if args.is4k else None, **kw))
        if args.request_title:
            return show(request_title(args.request_title, year=args.year, imdb=args.imdb,
                                      kind=args.kind, seasons=args.seasons,
                                      is4k=True if args.is4k else None, **kw))
    except SeerrError as exc:
        print(f"seerr error: {exc}", file=sys.stderr)
        if exc.body:
            print(f"  body: {exc.body[:400]}", file=sys.stderr)
        return 2
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
