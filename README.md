# Mwatcher

Turn your **Stremio addons** into a **Plex** library.

Plex has no addon system, so it can't play a remote stream the way Stremio does — it plays
*files*. Mwatcher is the bridge: your addons (merged and ranked by
[Fast Combo](https://github.com/AfzalAshraf/stremio-addons)) find the video, Mwatcher
downloads the single best link into your Plex library, and Plex serves it to every client
you own, anywhere in the world.

```text
your Stremio addons ──▶ Fast Combo ──▶ Mwatcher bridge ──▶ staging ──▶ Plex library ──▶ any Plex app
   (scrapers)            :7000             :8889                       Movies / TV Shows
                          │                   │
                   asks them all at      picks the best downloadable link,
                   once, drops CAM/      downloads it (failing over if it dies),
                   dead/dupes/too-big,   names it Plex-style from Cinemeta
                   live-probes, ranks    metadata, moves it into the library
```

## What's here

| Path | What it is |
|---|---|
| `docs/PLEX_GLOBAL_ACCESS.md` | **The full guide** — installing Plex on Lubuntu, running Fast Combo + the bridge, how the "best stream" is chosen, and reaching it all from anywhere (port forwarding, Cloudflare Tunnel, Tailscale/CGNAT) |
| `install.sh` | **One command** — `auto` installs everything *and* finishes the Plex side after you sign in; plus `status`, `doctor` (diagnoses playback failures), `seerr` and `uninstall` |
| `scripts/telestream_to_plex.py` | The bridge: dashboard + HTTP API + CLI. Resolve → download **or** stream through a cache → name → library |
| `scripts/stremio_source.py` | Fast Combo / Cinemeta client: parses and ranks addon streams, picks the best |
| `scripts/seerr_source.py` | Seerr client: search → TMDB id → create a request, plus `--doctor` for the request path |
| `scripts/telestream_to_plex.py --repoint` | Repairs `.strm` pointers whose key the bridge no longer knows — see `docs/WORKLOG.md` trap 28 |
| `scripts/envfile.py` | Loads `~/.config/mwatcher/bridge.env` so the CLI works from a plain shell, not just under systemd |
| `scripts/plex_setup.py` | Plex automation: waits for your Google sign-in, creates both libraries via the API, enables auto-scan, verifies |
| `demo/fake_plex.py` | A pretend Plex Media Server, strict about the things real Plex is strict about, so the above is testable with no Plex install |
| `services/seerr-stack/docker-compose.yml` | Seerr + Radarr + Sonarr + Prowlarr + qBittorrent, all sharing one media path |
| `services/fastcombo.service` | Runs your addons (Fast Combo) on `127.0.0.1:7000` |
| `services/fastcombo-tunnel.service.example` | Keeps an SSH tunnel to a **remote** Fast Combo alive, so the access key never crosses a public interface |
| `services/mwatcher-bridge.service` | Runs the bridge on `127.0.0.1:8889` |
| `config/*.env.example` | Secret files for the two services (access key, admin password) |
| `demo/fake_stremio_addon.py` | A pretend addon **and** pretend Cinemeta, so you can test the whole pipeline offline |
| `docs/WORKLOG.md` | Engineering log: decisions taken and why, measured results, the traps that cost time, and the exact demo restart recipe |
| `demo/fake_seerr.py` | A pretend Seerr (same API, same auth errors), so the request path is testable with no Docker |

## Quick start — one command

```bash
cd ~/Mwatcher
sudo bash install.sh auto
```

That does everything: installs Plex, Node, ffmpeg/yt-dlp and Fast Combo, creates your library folders,
reuses any access key that already exists, writes both systemd units with your real paths, starts
everything — then **waits for you to sign in to Plex with Google** and finishes the rest by itself:
both libraries created through the Plex API, automatic scanning on, and a verification pass.

The sign-in is the only manual step. It prints a URL; open it on any device on your network, sign in,
and walk away. On a headless box over SSH, use a claim token instead:

```bash
sudo bash install.sh auto --claim-token claim-XXXXXXXX    # from https://plex.tv/claim, valid ~5 min
```

Prefer to do the Plex clicking yourself? Plain `sudo bash install.sh` installs and stops there.

**Both are safe to re-run** — they repair instead of resetting, never overwrite an existing key,
password or addon list, and never duplicate a library.

```bash
sudo bash install.sh status                  # what's installed and running? changes nothing
sudo bash install.sh doctor                  # why won't things play?
sudo bash install.sh doctor "The Uprising"   # diagnose one title end to end
sudo bash install.sh seerr                   # Seerr + Radarr/Sonarr + Prowlarr + qBittorrent
sudo bash install.sh uninstall               # remove services, keep your media
```

`doctor` is the fix-first tool for **"Playback error — Error code: s1001 (Network)"**: it ffprobes the
actual file (the usual culprit is a download that saved an HTML error page instead of a video), catches
`.strm` pointers aimed at `127.0.0.1`, checks the `plex` user's permissions, reads Plex's own log for
`MDE:` errors, and inspects Secure connections / custom URLs / pre-roll / CGNAT.

### Manual setup

```bash
# 1. Plex
sudo apt install -y plexmediaserver                  # details in the guide, §1
mkdir -p ~/media/Movies ~/media/"TV Shows" ~/media/staging

# 2. Fast Combo = your addons, merged and ranked
sudo apt install -y nodejs
git clone https://github.com/AfzalAshraf/stremio-addons ~/stremio-addons
mkdir -p ~/.config/mwatcher && cp config/fastcombo.env.example ~/.config/mwatcher/fastcombo.env
$EDITOR ~/.config/mwatcher/fastcombo.env && chmod 600 ~/.config/mwatcher/fastcombo.env

# 3. The bridge
pipx install yt-dlp                                  # or: sudo apt install ffmpeg
cp config/bridge.env.example ~/.config/mwatcher/bridge.env
$EDITOR ~/.config/mwatcher/bridge.env && chmod 600 ~/.config/mwatcher/bridge.env

sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plexmediaserver fastcombo mwatcher-bridge
```

Add your addons at `http://127.0.0.1:7000/<FC_ACCESS_KEY>/configure`, then open the
dashboard at **`http://127.0.0.1:8889/`**, search a title, and press **Fetch best into Plex**.

From the shell:

```bash
python3 scripts/telestream_to_plex.py --title "Dune" --year 2021 --prefer fastest
python3 scripts/telestream_to_plex.py --imdb tt0903747 --kind show --episode S01E02
python3 scripts/telestream_to_plex.py --list-streams --imdb tt1160419   # rank, don't download
```

## Choosing the "single best speed"

`FASTCOMBO_PREFER` (or `prefer` per request) decides which of Fast Combo's ranked links
gets fetched:

| Mode | Picks |
|---|---|
| `best` | Fast Combo's order — tested-working first, best picture for the smallest file |
| `fastest` | **The link that starts soonest**, then the smaller file |
| `smallest` | Smallest file first |
| `4kfirst` / `1080first` | Highest quality first / 1080p before 4K |

Torrent links (`infoHash`, no `url`) are skipped — they need a debrid service. If the
chosen link dies mid-download, the bridge automatically tries the next-best one, up to
`FASTCOMBO_MAX_FALLBACKS`.

## Try it with no addons at all

```bash
python3 demo/fake_stremio_addon.py &            # pretend addon + pretend Cinemeta, :9912
python3 demo/fake_seerr.py &                    # pretend Seerr, :5055

FC_ACCESS_KEY=testkey123456 FC_ADMIN_PASSWORD=testpass1234 PORT=7000 \
  FC_UPSTREAMS=http://127.0.0.1:9912/manifest.json node ~/stremio-addons/server.js &

CINEMETA_URL=http://127.0.0.1:9912 FASTCOMBO_BASE_URL=http://127.0.0.1:7000 \
  FASTCOMBO_ACCESS_KEY=testkey123456 FASTCOMBO_PREFER=fastest \
  SEERR_URL=http://127.0.0.1:5055 SEERR_API_KEY=testkey \
  python3 scripts/telestream_to_plex.py serve   # dashboard on :8889
```

The fake addon serves 7 streams per title including a CAM copy, a 720p, a duplicate on a
slower host and a torrent — so you can watch Fast Combo filter them and the bridge rank
what is left, with real link probing (the fake files answer `Range` requests).

Two traps worth running:

```bash
# a host that looks like video to Fast Combo's probe but serves an HTML wall on the real
# download -- the silent success that produces Plex error s1001. The bridge rejects it and
# fails over to the next-best stream.
DEMO_TRAP=4k python3 demo/fake_stremio_addon.py

# a fresh Seerr with nothing attached, so you can see doctor say exactly what is missing
SEERR_NO_SERVERS=1 SEERR_NO_PLEX=1 python3 demo/fake_seerr.py
python3 scripts/seerr_source.py --doctor --url http://127.0.0.1:5055 --api-key testkey
```

## Requirements

- Python 3.8+ (bridge: standard library only), Node 18+ (Fast Combo)
- A downloader on `PATH`: `yt-dlp` (preferred), `ffmpeg`, or `curl`
- Plex Media Server, plus **Plex Pass** for remote playback in mobile/TV apps
  (remote playback in a web browser works without it)

## Three ways to get a title

| | **Play through**<br>`action=strm` | **Download**<br>`action=stream` | **Request**<br>`action=seerr` |
|---|---|---|---|
| What lands in the library | a 45-byte `.strm` pointer | the video file | nothing yet — Seerr queues it |
| Who fetches the bytes | the bridge, at play time | the bridge, now | Radarr/Sonarr → qBittorrent |
| Disk used | a capped cache (default 20 GB, evicts oldest) | the whole title, forever | the whole title, forever |
| Debrid needed | no | only for torrent-only links (skipped) | **no** — torrents/NZBs fetch it |
| Time to watching | seconds | as long as the download takes | as long as the download takes |
| Survives link rot | links are re-scraped every play | no — re-fetch if a host dies | yes, the file is yours |

Play-through is the "don't download anything" mode: Plex asks the bridge, the bridge scrapes
a **fresh** link from your addons right then, opens it with whatever headers the host needs,
and streams it through (Range-aware, so seeking works) into a capped cache. A host serving a
captcha page is caught before the first byte reaches Plex and the next link is tried — the
same protection the download path has.

```bash
curl -X POST localhost:8889/add    -d '{"title":"Dune","year":2021}'   # pointer, 0 bytes
curl -X POST localhost:8889/fetch  -d '{"title":"Dune","year":2021}'   # download it
curl -X POST localhost:8889/request -d '{"title":"Dune","year":2021}'  # Seerr gets it
curl -X POST localhost:8889/fetch  -d '{"title":"Dune","action":"both"}'  # watch now + own it
curl -s  localhost:8889/plays      # pointers + what is cached
curl -s  localhost:8889/cache      # cache size vs cap
```

`TELESTREAM_ACTION=strm` makes play-through the default, and `SEERR_MODE=both` makes every
fetch also create a Seerr request. `TELESTREAM_PUBLIC_BASE_URL` is the address written into
the `.strm` — it must be reachable from your **Plex clients**, not from the server; loopback
there means s1001 on every other device.

```bash
sudo bash install.sh seerr                        # one command for the whole stack

curl -X POST localhost:8889/request -H 'Content-Type: application/json' \
     -d '{"title":"Dune","year":2021}'            # request it
curl -X POST localhost:8889/fetch -H 'Content-Type: application/json' \
     -d '{"title":"Dune","year":2021,"action":"both"}'   # watch now AND own it
curl -s localhost:8889/seerr                      # reachable? what's queued?
```

Note that Seerr itself never downloads — it delegates to Radarr/Sonarr, which is why the
installer brings up that stack too. Details, configuration order and "my request never
became a file" in `docs/PLEX_GLOBAL_ACCESS.md` §4.7.

## Trade-off, plainly

This **downloads** media rather than streaming it on demand: budget disk space and fetch
time (a 4K movie is 15-25 GB). In exchange you get the best available copy, correctly
named, playable on every Plex client, with Plex's own transcoding, subtitles, resume
positions and sharing. See `docs/PLEX_GLOBAL_ACCESS.md` §4.5.

Do not want files at all? Use play-through (§4.6) — a 45-byte pointer and a capped cache.
Want them fetched properly instead of scraped? Use Seerr (§4.7): request a title
and Radarr/Sonarr fetch it via your own indexers — no debrid subscription, and the release
is chosen by quality profile rather than by whatever an addon happens to have.
