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
| `scripts/telestream_to_plex.py` | The bridge: dashboard + HTTP API + CLI. Resolve → download → name → library |
| `scripts/stremio_source.py` | Fast Combo / Cinemeta client: parses and ranks addon streams, picks the best |
| `services/fastcombo.service` | Runs your addons (Fast Combo) on `127.0.0.1:7000` |
| `services/mwatcher-bridge.service` | Runs the bridge on `127.0.0.1:8889` |
| `config/*.env.example` | Secret files for the two services (access key, admin password) |
| `demo/fake_stremio_addon.py` | A pretend addon **and** pretend Cinemeta, so you can test the whole pipeline offline |

## Quick start — one command

```bash
cd ~/Mwatcher
sudo bash install.sh
```

That installs Plex, Node, ffmpeg/yt-dlp and Fast Combo, creates your library folders, generates the
access keys (only if they don't already exist), writes both systemd units with your real paths, starts
everything, and prints the two URLs you need. **It is safe to re-run** — it repairs instead of resetting,
and never overwrites an existing key, password or addon list.

```bash
sudo bash install.sh status                  # what's installed and running? changes nothing
sudo bash install.sh doctor                  # why won't things play?
sudo bash install.sh doctor "The Uprising"   # diagnose one title end to end
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

FC_ACCESS_KEY=testkey123456 FC_ADMIN_PASSWORD=testpass1234 PORT=7000 \
  FC_UPSTREAMS=http://127.0.0.1:9912/manifest.json node ~/stremio-addons/server.js &

CINEMETA_URL=http://127.0.0.1:9912 FASTCOMBO_BASE_URL=http://127.0.0.1:7000 \
  FASTCOMBO_ACCESS_KEY=testkey123456 FASTCOMBO_PREFER=fastest \
  python3 scripts/telestream_to_plex.py serve   # dashboard on :8889
```

The fake addon serves 7 streams per title including a CAM copy, a 720p, a duplicate on a
slower host and a torrent — so you can watch Fast Combo filter them and the bridge rank
what is left, with real link probing (the fake files answer `Range` requests).

## Requirements

- Python 3.8+ (bridge: standard library only), Node 18+ (Fast Combo)
- A downloader on `PATH`: `yt-dlp` (preferred), `ffmpeg`, or `curl`
- Plex Media Server, plus **Plex Pass** for remote playback in mobile/TV apps
  (remote playback in a web browser works without it)

## Trade-off, plainly

This **downloads** media rather than streaming it on demand: budget disk space and fetch
time (a 4K movie is 15-25 GB). In exchange you get the best available copy, correctly
named, playable on every Plex client, with Plex's own transcoding, subtitles, resume
positions and sharing. See `docs/PLEX_GLOBAL_ACCESS.md` §4.5.
