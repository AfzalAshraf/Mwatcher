# Stremio addons → Plex Edition

Access your **Plex Media Server** (on Lubuntu, `192.168.0.34`) from anywhere in the world — mobile data,
outside the house, devices not on your Wi-Fi — and play the videos your **Stremio addons** find
(merged and ranked by [Fast Combo](https://github.com/AfzalAshraf/stremio-addons)) **inside the Plex app**.

Two things changed compared to the old Stremio setup, and they matter:

| | Stremio Master Hub (old) | Plex (new) |
|---|---|---|
| Port | `8888` | `32400` (TCP) |
| "Install" URL | `https://host/manifest.json` | You don't install anything — you **sign in to your Plex account** on each device |
| HTTPS | Required by Stremio clients | Handled by Plex itself (`*.plex.direct` certs) |
| Addons | Stremio addons stream HTTP directly | **Plex has no addon system** — Fast Combo ranks them, the bridge downloads the best into a Plex library (see §4) |
| Ports | `8888` only | `32400` Plex · `7000` Fast Combo · `8889` bridge |
| Random `trycloudflare.com` URL | Fine | **Does not work** — the URL must be stable and typed into Plex settings (see §5c) |

> ⚠️ **One paid caveat up front:** streaming your own server's media from mobile/TV apps away from home
> requires **Plex Pass** (one-time or subscription). Without Plex Pass, remote playback only works in a
> **web browser** at `https://app.plex.tv`. Remote *access* itself is free; remote *app playback* is the paid bit.

---

## 0. Prerequisites

- Lubuntu box reachable on the LAN at `192.168.0.34` (keep this IP — reserve it in your router's DHCP table).
- A Plex account (free): <https://app.plex.tv/auth>
- Node 18+ and your [Fast Combo](https://github.com/AfzalAshraf/stremio-addons) addons working locally.
- A downloader: `yt-dlp` (best), `ffmpeg`, or `curl`.
- Disk space: this **downloads** what you ask for — ~2 GB per 1080p movie, 15-25 GB for 4K.

---

## 0.5 One command (do this instead of §1-§4)

`install.sh` installs everything, is **safe to re-run**, and never overwrites an access key,
password or addon list that already exists — so running it again repairs rather than resets.

```bash
cd ~/Mwatcher
sudo bash install.sh
```

It installs Plex + Node + ffmpeg/yt-dlp, clones Fast Combo, creates `~/media/{Movies,TV Shows,staging}`,
generates the keys (only if they do not exist yet), writes both systemd units with **your** paths and
username, starts everything, and prints a status table plus the two URLs you need.

Other modes — you will use `doctor` a lot:

```bash
sudo bash install.sh status                  # what is installed/running? change nothing
sudo bash install.sh doctor                  # why won't things play?
sudo bash install.sh doctor "The Uprising"   # diagnose ONE title end to end
sudo bash install.sh uninstall               # remove the services, keep your media
```

The rest of this document explains what the installer does and how to do it by hand.

---

## 1. Install Plex Media Server on Lubuntu

```bash
sudo apt update
sudo apt install -y curl gnupg ca-certificates

# Official Plex repo + signing key (repo.plex.tv is current; downloads.plex.tv/repo/deb is deprecated)
curl -L https://downloads.plex.tv/plex-keys/PlexSign.v2.key \
  | sudo gpg --yes --dearmor -o /etc/apt/keyrings/plexmediaserver.v2.gpg

echo "deb [signed-by=/etc/apt/keyrings/plexmediaserver.v2.gpg] https://repo.plex.tv/deb/ public main" \
  | sudo tee /etc/apt/sources.list.d/plex.list

sudo apt update
sudo apt install -y plexmediaserver
```

If you previously added the old repo, remove it first: `sudo rm -f /etc/apt/sources.list.d/plexmediaserver.list`

## 2. Run it as a 24/7 background service

The `.deb` already ships a systemd unit (`plexmediaserver.service`) — unlike the Stremio tunnel, you do
**not** need to hand-write one. Just make sure it is enabled:

```bash
sudo systemctl enable --now plexmediaserver
systemctl status plexmediaserver --no-pager
sudo journalctl -u plexmediaserver -n 25 --no-pager
```

Handy facts:

```bash
# Config file (Preferences.xml), service unit, library data
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Preferences.xml
/lib/systemd/system/plexmediaserver.service
/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/

# Restart after config edits, and confirm it is listening
sudo systemctl restart plexmediaserver
sudo ss -tlnp | grep 32400
```

Plex runs as the dedicated `plex` user — that user must be able to **read** your media folders:

```bash
sudo usermod -aG afine plex          # let plex read files inside /home/afine
chmod -R a+rX /home/afine/media      # or put the library somewhere plex can already read
```

## 3. First-run setup + library layout

1. On the Lubuntu box (or any LAN device) open **`http://192.168.0.34:32400/web`**.
2. Sign in with your Plex account → **claim the server** → name it (e.g. `MasterHub`).
3. Create the library folders and add them as libraries:

```bash
mkdir -p /home/afine/media/Movies \
         "/home/afine/media/TV Shows" \
         /home/afine/media/staging
```

`staging/` is where the bridge writes partial downloads before moving them into the library — keep it on
the **same filesystem** as `Movies/` and `TV Shows/`, otherwise the move becomes a slow copy instead of a
rename. Do not add `staging/` to Plex as a library.

Plex naming rules — get these right or metadata matching fails:

```text
/home/afine/media/Movies/Inception (2010)/Inception (2010).mkv
/home/afine/media/TV Shows/Breaking Bad/Season 01/Breaking Bad - S01E01.mkv
```

4. **Settings → Libraries → Add Library → Movies**, browse to `/home/afine/media/Movies`. Repeat for TV Shows.
5. Enable **Settings → Library → "Scan my library automatically"** and **"Run a partial scan when changes are detected"**.
6. The bridge writes straight into `Movies/` and `TV Shows/`, so with auto-scan on, a fetched title appears
   in Plex within a minute. To force it: **Settings → Library → Scan Library Files**. See §4.

---

## 4. The "addons" part: your Stremio addons → Plex

Plex **removed its plugin/channel framework**, so it cannot play a remote HTTP stream the way Stremio does —
Plex plays **files from its libraries**. So your addons stay the *finder* and Plex becomes the *player*, with
this repo's bridge in between:

```text
your Stremio addons ──▶ Fast Combo ──▶ Mwatcher bridge ──▶ staging ──▶ Plex library ──▶ any Plex app
   (scrapers)          :7000            :8889                          Movies / TV Shows
                        │                 │
                 asks them all at     picks the single best
                 once, filters,       downloadable link,
                 live-probes,         downloads it, names it
                 ranks best-first     Plex-style, moves it in
```

### 4.1 Run Fast Combo (your addons, merged and ranked)

[Fast Combo](https://github.com/AfzalAshraf/stremio-addons) is the addon side. For every title it asks all
your addons at once, keeps only working fast-starting 1080p/4K streams, removes duplicates (keeping the
fastest host), hides CAM/TS copies, ads and dead links, and sorts the result.

```bash
sudo apt install -y nodejs                       # needs Node 18+
git clone https://github.com/AfzalAshraf/stremio-addons /home/afine/stremio-addons

mkdir -p /home/afine/.config/mwatcher /home/afine/.local/share/fastcombo
cd /home/afine/Mwatcher
cp config/fastcombo.env.example /home/afine/.config/mwatcher/fastcombo.env
nano /home/afine/.config/mwatcher/fastcombo.env  # set FC_ACCESS_KEY + FC_ADMIN_PASSWORD
chmod 600 /home/afine/.config/mwatcher/fastcombo.env

sudo cp services/fastcombo.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now fastcombo
sudo journalctl -u fastcombo -f
```

Then open the control panel and add your addons (each is live-tested before it is added):

```text
http://127.0.0.1:7000/<FC_ACCESS_KEY>/configure
```

Fast Combo is bound to `127.0.0.1` — only the bridge can reach it. If you *also* want it inside the Stremio
app on your phone/TV, put it behind your own HTTPS reverse proxy and set `FC_PUBLIC_URL` (Stremio requires
HTTPS for addons that are not on the same device).

**Settings on the control panel that change what the bridge can fetch:**

| Setting | Default | Effect on the bridge |
|---|---|---|
| Qualities kept (`res`) | `2160,1080` | Add `,720` if you want smaller/faster files on a slow line |
| Max 1080p bitrate (`max1080`) | 8 Mbps | ≈7 GB per 2 h movie; bigger files are dropped as *"too big for fast streaming"* |
| Max 4K bitrate (`max4k`) | 20 Mbps | ≈18 GB per 2 h movie; set **No limit** if you want the huge ones |
| Sort | balanced | Fast Combo's own order; the bridge can re-rank anyway (see 4.3) |
| Live-test links | on | Keep it on — untested links are the ones that die mid-download |
| REMUX | off | Off is right for Plex: those files are enormous |

### 4.2 Run the bridge

```bash
sudo apt install -y python3                       # bridge itself: standard library only
pipx install yt-dlp                               # best downloader (or: sudo apt install ffmpeg)

cd /home/afine/Mwatcher
cp config/bridge.env.example /home/afine/.config/mwatcher/bridge.env
nano /home/afine/.config/mwatcher/bridge.env      # paste the SAME FC_ACCESS_KEY
chmod 600 /home/afine/.config/mwatcher/bridge.env

sudo cp services/mwatcher-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now mwatcher-bridge
sudo journalctl -u mwatcher-bridge -f
```

Make sure the library folders in the unit (`TELESTREAM_MOVIES_DIR`, `TELESTREAM_TV_DIR`) are the same
folders your Plex libraries point at (§3), and that the `plex` user can read them (§2).

### 4.3 Which stream gets picked — "single best speed"

Fast Combo returns a list that is already ranked. The bridge then:

1. **Keeps only links it can actually download.** Torrent entries (`infoHash`, no `url`) are skipped —
   they need a debrid service. If *all* your addons return torrents, the bridge reports that clearly
   instead of failing silently.
2. **Re-ranks** by `FASTCOMBO_PREFER` (or per-request `prefer`):

   | Mode | Picks |
   |---|---|
   | `best` | Fast Combo's order: tested-working first, then best picture for the smallest file |
   | `fastest` | **The link that starts soonest**, then the smaller file — this is "single best speed" |
   | `smallest` | Smallest file first (fastest to download, least disk) |
   | `4kfirst` | 4K when there is one |
   | `1080first` | 1080p before 4K (smaller, more compatible with Plex transcoding) |

3. **Fails over.** If the chosen link dies part-way, it automatically tries the next-best one, up to
   `FASTCOMBO_MAX_FALLBACKS` (default 4). The job record keeps every attempt and why it failed.
4. **Sends the host's required headers** when Fast Combo forwards them (`behaviorHints.proxyHeaders`).
5. **Names the file from Cinemeta metadata**, not from what you typed, so Plex matches artwork properly:
   `Movies/Dune (2021)/Dune (2021).mkv`, `TV Shows/Breaking Bad/Season 01/Breaking Bad - S01E02.mkv`.

What that looks like in practice (real output, `prefer=fastest`, 7 raw addon streams in):

```text
Fast Combo dropped: 720p not wanted (1) · CAM/TS cinema recording (1) · duplicate, other host (1)
4 streams, 3 downloadable

 BEST  #1  1080p 2.10 GB  2.3 Mbps AVC WEB-DL  | starts in 0.1s
   fb  #2  1080p 6.00 GB  6.7 Mbps AVC BLURAY | starts in 0.4s
   fb  #0  4K   12.00 GB 13.0 Mbps HEVC HDR   | starts in 0.9s
  skip #3  1080p 6.50 GB  7.2 Mbps AVC BLURAY | torrent (needs debrid)
```

> **Cinemeta matters more than it looks.** Fast Combo estimates bitrate from file size ÷ runtime, and it
> gets the runtime from Cinemeta (`v3-cinemeta.strem.io`, hardcoded). If that is unreachable, it falls back
> to 120 min for a movie / 45 min for an episode, the estimated bitrate inflates, and perfectly good big
> files get dropped as *"too big for fast streaming"*. If your 4K streams keep vanishing, check that the
> server can reach Cinemeta, or raise the bitrate caps on the control panel.

### 4.4 Using it

**Web dashboard** — `http://127.0.0.1:8889/`: search a title → see the ranked streams with size, bitrate,
codec, start time, host and which addon produced it → press **Fetch best into Plex** (or fetch a specific
row). The Jobs table shows live progress and exactly which stream was chosen.

**HTTP** (what an addon, script or shortcut should call):

```bash
# by title (searched on Cinemeta first)
curl -X POST http://127.0.0.1:8889/fetch -H 'Content-Type: application/json' \
  -d '{"title":"Dune","year":2021,"kind":"movie","prefer":"fastest"}'

# by IMDb id, a specific episode
curl -X POST http://127.0.0.1:8889/fetch -H 'Content-Type: application/json' \
  -d '{"imdb":"tt0903747","kind":"show","season":1,"episode":"S01E02"}'

curl -s "http://127.0.0.1:8889/search?q=dune"                      # title -> IMDb matches
curl -s "http://127.0.0.1:8889/streams?id=tt1160419&prefer=fastest" # ranked candidates
curl -s  http://127.0.0.1:8889/jobs                                 # progress + provenance
```

**CLI** (good for cron, or "fetch tonight's episode"):

```bash
python3 scripts/telestream_to_plex.py --title "Dune" --year 2021 --prefer fastest
python3 scripts/telestream_to_plex.py --imdb tt0903747 --kind show --episode S01E02
python3 scripts/telestream_to_plex.py --list-streams --imdb tt1160419   # rank without downloading
python3 scripts/telestream_to_plex.py --search "dune"                   # just the IMDb matches
python3 scripts/telestream_to_plex.py --url http://host/file.mkv --title "Dune"  # direct link, no addons
```

**Testing without any real addon** — `demo/fake_stremio_addon.py` is a pretend addon *and* a pretend
Cinemeta. Point Fast Combo at it (`FC_UPSTREAMS=http://127.0.0.1:9912/manifest.json`) and the bridge at
that Fast Combo, and the whole pipeline runs offline — including Fast Combo's real filtering, dedup and
live link probing (the fake files answer `Range` requests, which is what it probes with).

### 4.5 What this does NOT do (be honest about the trade-off)

- **It downloads, it does not stream on demand.** Unlike Stremio, the file lands on disk before Plex can
  play it. Budget disk space and the time to fetch it (a 4K movie is 15-25 GB). Instant "press play on
  anything" is not what this gives you; "the best copy of what you asked for, playable on every Plex
  client forever" is.
- **Torrent/debrid links are skipped.** Addons that return `infoHash` need Real-Debrid/TB/alldebrid-style
  resolution first. If that is most of your addons, prefer addons that return direct HTTP links, or add a
  debrid step in front of the downloader.
- **Plex plugins are dead.** `WebTools.bundle`, `FreeboxTV.bundle`, IPTV-style `.m3u` plugins and the old
  Unsupported AppStore do not load on a current Plex server, so there is no way to bolt an addon *inside*
  Plex itself. If playing live HTTP sources without downloading is a hard requirement, run **Jellyfin** or
  **Emby** alongside Plex — both still have working plugin systems.
- **`.strm` pointer files** (a text file containing a URL, placed in the library) are the only way to make
  Plex reference a remote link, and support is patchy: many clients ignore them and remote/transcoded
  playback breaks. Experiment only:

  ```bash
  echo "https://files.example.com/Dune.2021.1080p.mkv" > "/home/afine/media/Movies/Dune (2021)/Dune (2021).strm"
  ```

### 4.6 Seerr — request a title and your own server downloads it (no debrid)

§4.1–4.5 pull a file down on demand. The other way to build a library is to **request** a
title and let your server fetch it properly, once, and keep it. That is what
[Seerr](https://github.com/fallenbagel/seerr) does — and it needs no debrid subscription,
because torrents/NZBs do the fetching instead.

```bash
sudo bash install.sh seerr
```

One command: installs Docker, starts Seerr + Radarr + Sonarr + Prowlarr + qBittorrent with
`services/seerr-stack/docker-compose.yml`, creates the folders, and adds `SEERR_URL` to your
bridge config. Safe to re-run — an existing `.env` (ports, timezone, paths) is kept.

**Be clear about what Seerr is.** It never downloads anything itself; it is the
request/approval layer:

```
you  →  Seerr (5055)  →  Radarr (7878) movies  /  Sonarr (8989) TV
                              │
                              ├→ Prowlarr (9696)     find a release on your indexers
                              ├→ qBittorrent (8080)  download it
                              └→ import into ~/media/…  →  Plex sees the file
```

So Seerr replaces **debrid**, not Radarr/Sonarr. If you want the single-command path, that
stack is exactly what `install.sh seerr` sets up.

**Configure in this order** (the installer prints it again at the end):

1. qBittorrent `:8080` — set a real password now (default `admin`/`adminadmin`)
2. Prowlarr `:9696` — add your indexers; Settings → Apps → add Radarr and Sonarr
3. Radarr `:7878` — Download Clients → qBittorrent (host `qbittorrent`, port `8080`);
   Media Management → root folder `/media/Movies`
4. Sonarr `:8989` — same client; root folder `/media/TV Shows`
5. Seerr `:5055` — wizard → Plex at `host.docker.internal:32400` → add the Radarr and
   Sonarr servers → copy the API key from Settings → General into `SEERR_API_KEY` in
   `~/.config/mwatcher/bridge.env`, then `sudo systemctl restart mwatcher-bridge`

> **Security.** Seerr's API key is an **admin credential** — anyone holding it can change
> your server settings. It lives in the chmod 600 env file and is only ever used
> server-side by the bridge; the dashboard never receives it.

Every container mounts your library at the **same** path (`/media`) and downloads at
`/downloads`, so Radarr, Sonarr and qBittorrent all agree where a file is. That is what
prevents the classic "downloaded but import failed / path does not exist".

#### Browsing and requesting

Stremio's **Play** button cannot call Seerr — an addon may only return catalogs, metadata
and streams, so there is no hook for "send this to Seerr". What you get instead covers the
same ground:

- **Seerr's own UI** (`http://<server>:5055`) — trending/popular/search catalogs with a
  **Request** button on every title. The natural browse-and-request surface.
- **The Mwatcher dashboard** (`http://<server>:8889`) — one search box, both actions:
  *Show streams* → *Fetch best into Plex* (stream now), or *Request* (Seerr downloads it).
- **One call**, if you drive it yourself:

```bash
# ask Seerr to get it — the bridge downloads nothing
curl -X POST http://127.0.0.1:8889/request -H 'Content-Type: application/json' \
     -d '{"title":"Dune","year":2021,"kind":"movie"}'

# watch it NOW *and* request the permanent copy at the same time
curl -X POST http://127.0.0.1:8889/fetch -H 'Content-Type: application/json' \
     -d '{"title":"Dune","year":2021,"action":"both"}'

# from the CLI
python3 scripts/telestream_to_plex.py --title "Dune" --year 2021 --action seerr
python3 scripts/telestream_to_plex.py --seerr-status
```

`action` is `stream` (default), `seerr` (request only) or `both`. Set `SEERR_MODE=both` in
`bridge.env` to make that the default for every request, and `SEERR_MODE=request` to turn
the bridge into a pure Seerr front-end that never downloads anything itself.

`both` is the combination that replaces debrid for most people: the addon stream gets you
watching in seconds while Radarr/Sonarr fetch a proper release that stays in your library
forever and survives link rot.

#### When a request never becomes a file

`sudo bash install.sh doctor` checks this path too (section 6). Usual causes:

| Symptom | Cause | Fix |
|---|---|---|
| Request stays *Pending* | auto-approve is off | Seerr → Settings → Users → Auto-Approve, or approve at `/requests` |
| Approved, nothing downloads | no Radarr/Sonarr attached to Seerr | Seerr → Settings → Servers → add them |
| "No releases found" | no indexer carries it | add indexers in Prowlarr — or accept it is not available |
| Downloaded but not imported | path mismatch with qBittorrent | use the compose file here: everything sees `/media` and `/downloads` |
| *Available* never updates | Seerr has no Plex server | Seerr → Settings → Media Server → Plex |
| Bridge says `Seerr is not configured` | `SEERR_URL`/`SEERR_API_KEY` missing | add both to `bridge.env`, restart the bridge |

---

## 5. Global access — pick ONE

### a) Plex native Remote Access (default, free, encrypted)

**Settings → Server → Remote Access → Enable Remote Access.** Plex tries UPnP/NAT-PMP first. If it stays
red, do (b) and then come back and tick **"Manually specify public port"** and enter your external port —
this is the single most common reason a working port forward looks broken.

If it works but says **"Indirect"/"Relay"**, you're being bounced through Plex's relay, which is capped at
**~2 Mbps** — fine for SD, not for HD. That means no inbound path exists; use (b) or (d).

### b) Traditional public IP + router port forwarding

```bash
curl -s https://ifconfig.me; echo      # your public IPv4
ip -4 addr show                        # confirm the box really is 192.168.0.34
```

Router admin panel (`http://192.168.0.1` / `http://192.168.1.1`) → **Port Forwarding / Virtual Server**:

| Field | Value |
|---|---|
| Internal IP | `192.168.0.34` |
| Internal Port | `32400` |
| External Port | `32400` (or e.g. `45678` — less scanner noise) |
| Protocol | **TCP** |

Only 32400/tcp needs to be public. Leave the companion ports alone (3005, 8324, 32469, 1900/udp,
32410-32414/udp are LAN discovery/DLNA/Roku things).

Local firewall:

```bash
sudo ufw allow from 192.168.0.0/24 to any       # LAN
sudo ufw allow 32400/tcp comment 'Plex'         # WAN, only if you port-forward
sudo ufw status numbered
```

Then in Plex: **Settings → Server → Remote Access → Show Advanced → Manually specify public port** →
type the **external** port → **Retry**. It should turn green: *"Fully accessible outside your network."*

Your address is now `http://YOUR_PUBLIC_IP:32400/web` — but you never need to share it. People just install
the Plex app and sign in; the server appears in their list.

**If your ISP uses CGNAT this will not work** (see how to check below) → use (c) or (d).

```bash
# CGNAT check: if these two differ, or the public IP is in 100.64.0.0 – 100.127.255.255, you are behind CGNAT
curl -s https://ifconfig.me; echo
# compare with the WAN IP shown on your router's status page
```

### c) Cloudflare Tunnel on your OWN domain (the "Option 1" equivalent — read the warnings)

Two important differences from the Stremio version:

1. **A random `trycloudflare.com` quick tunnel is useless for Plex.** The hostname changes on every restart,
   and Plex needs a permanent hostname typed into *Custom server access URLs*. You need a real domain on
   Cloudflare (a `.com`/`.xyz`/etc., free-ish) and a **named** tunnel.
2. **Cloudflare's ToS discourages proxying video through their network** (that's what their CDN is not for,
   and accounts have been actioned for it). It works technically; decide for yourself. If you don't want that
   risk, use (b) or (d).

```bash
# install cloudflared
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# log in (opens a browser to authorise your domain zone)
cloudflared tunnel login
cloudflared tunnel create plex
cloudflared tunnel route dns plex plex.example.com
```

`/home/afine/.cloudflared/config.yml` (`cloudflared tunnel create` prints the credential file + tunnel UUID):

```yaml
tunnel: <TUNNEL-UUID>
credentials-file: /home/afine/.cloudflared/<TUNNEL-UUID>.json

originRequest:
  originServerName: "*.plex.direct"   # lets cloudflared talk TLS to Plex's own cert
  noTLSVerify: true
  http2Origin: true

ingress:
  - hostname: plex.example.com
    service: https://localhost:32400
  - service: http_status:404
```

```bash
sudo cloudflared service install       # installs cloudflared.service
sudo systemctl enable --now cloudflared
sudo journalctl -u cloudflared -n 30 --no-pager
```

Now the Plex side — **all four of these are required or playback breaks in weird ways**:

1. **Settings → Server → Network → Custom server access URLs** (click *Show Advanced*):
   ```text
   http://192.168.0.34:32400,https://plex.example.com:443
   ```
   Put the **LAN URL first** so devices at home stay local instead of hairpinning through Cloudflare.
2. **Settings → Server → Network → Secure connections = Preferred** (not *Required* — Plex's cert is issued
   for `*.plex.direct`, not your domain).
3. **Settings → Server → Remote Access**: keep *Manually specify public port* = `443`, and **disable
   "Enable Relay"** so you can tell whether the tunnel is really carrying traffic.
4. Cloudflare dashboard for that hostname: **WebSockets ON**, caching/**Rocket Loader OFF** (a Page Rule or
   config rule for `plex.example.com`), and don't enable HSTS while debugging.

Test from a phone on **mobile data**: open `https://plex.example.com/web`, sign in, play something.

### d) CGNAT-proof, no domain, no port forwarding: Tailscale

The pragmatic winner if you're behind CGNAT and don't want to buy a domain or push video through Cloudflare.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4            # e.g. 100.101.102.103
```

- **Private (best):** install the Tailscale app on your phone/laptop too, then in Plex
  **Custom server access URLs** add `http://100.101.102.103:32400`. Everything is WireGuard-encrypted,
  free, and works from anywhere. Downside: each viewing device must run Tailscale.
- **Public without ports (Funnel):** in the Tailscale admin console enable **HTTPS Certificates** and
  **Funnel**, then:
  ```bash
  sudo tailscale serve --bg --https=443 http://127.0.0.1:32400
  sudo tailscale funnel --bg 443 on
  sudo tailscale funnel status
  ```
  Your address is `https://<machine>.<tailnet>.ts.net` → put that in *Custom server access URLs*.
  Funnel only listens on 443/8443/10000 and has non-configurable bandwidth limits.

---

## 6. Watching it from anywhere

1. Install **Plex** on the device (iOS/Android/Android TV/Fire TV/Roku/web/smart TV).
2. **Sign in with the same Plex account** that claimed the server. No URL, no manifest, no QR code needed —
   `MasterHub` shows up in the server picker.
3. Pick a title the bridge fetched and press play. Check **Settings → "Now Playing"/Dashboard** on the server
   to see whether the session is **Direct** (good) or **Relay/Indirect** (2 Mbps cap → go back to §5b/5c/5d).
4. Sharing with family: **Settings → Users & Sharing → Invite** by email; no need to hand out IPs or URLs.

---

## 7. Troubleshooting

### "Playback error — Error code: s1001 (Network)"

The title is in your library, Plex offers to play it from your home server, and then it fails. Run:

```bash
sudo bash install.sh doctor "The Uprising"
```

That checks, in the order these actually break:

| # | Cause | How `doctor` proves it | Fix |
|---|---|---|---|
| 1 | **The file is not a video.** The download saved an HTML error page (CDN wall, "Just a moment…", 403/404, login redirect) or a truncated stub. Plex lists it because the *filename* matched; there is nothing inside to play | `ffprobe` reports *no video and no audio stream*; file is a few KB; first bytes contain `<!doctype html` | Delete the file and re-fetch — the bridge now validates before it enters the library and fails over to the next stream: `rm "…/The Uprising (2023).mkv"` then `curl -X POST localhost:8889/fetch -d '{"title":"The Uprising"}'` |
| 2 | **A `.strm` pointer file** containing `http://127.0.0.1:…` or a LAN IP. Your phone/TV cannot reach that address, so browsing works but playback does not | `doctor` prints the .strm target and flags private addresses | Delete it and let the bridge download the real file (§4.5 explains why `.strm` is a dead end) |
| 3 | **`plex` user cannot read the file** | `sudo -u plex test -r <file>` fails | `sudo chmod -R a+rX ~/media && sudo usermod -aG $USER plex && sudo systemctl restart plexmediaserver` |
| 4 | **Secure connections = Required** together with a proxy/tunnel whose certificate is not Plex's `*.plex.direct` | `secureConnections="2"` in Preferences.xml | Set **Preferred** (Settings → Server → Network) |
| 5 | **Custom server access URL points at localhost**, or the public URL is missing | `customConnections` contains `127.0.0.1`/`localhost` | `http://192.168.0.34:32400,https://plex.yourdomain.com` — LAN first (§5c) |
| 6 | **Dead Movie Pre-Roll URL** in Extras — fails *every* title, classic s1001 | a `…preroll…` key in Preferences.xml | Clear Settings → General → Extras → Movie pre-roll video |
| 7 | **CGNAT / double NAT** — browsing works via Plex Relay, media cannot | public IP is in `100.64.0.0/10`, or is a private range | Tailscale (§5d) or a tunnel (§5c); port forwarding cannot work |
| 8 | **Corrupt Plex database** | log shows `database disk image is malformed` | <https://support.plex.tv/articles/repair-a-corrupted-database/> — or `PlexDBRepair` |

Prevention is already built in: the bridge refuses to move a download into your library until it has
checked the size, sniffed the first bytes for HTML/JSON, and (when `ffprobe` is installed) confirmed a
real video **and** audio stream of a sane duration. A rejected link is recorded in `/jobs` under `tried`
and the next-best stream is tried automatically — so a bad host costs you a retry, not a broken title.

If every stream for a title keeps getting rejected, the problem is upstream: that addon's host is
walling you. Check `curl -s localhost:8889/jobs` for the reasons, and try `--prefer fastest` or a
different addon.

### Everything else

| Symptom | Fix |
|---|---|
| `:32400/web` won't load on LAN | `systemctl status plexmediaserver`; check `sudo ss -tlnp \| grep 32400`; check ufw |
| Remote Access red after forwarding | *Manually specify public port* not ticked, or external port ≠ what you typed |
| Turns green, then red | LAN IP changed (reserve it in DHCP), or duplicate UPnP + manual rules fighting |
| Plays at home, "Indirect/Relay" away | No inbound path → CGNAT or firewall; use §5c/§5d |
| Web works, apps won't connect | Missing *Custom server access URLs* entry, or *Secure connections = Required* |
| Playback stalls only through Cloudflare | Caching/Rocket Loader on for that hostname; WebSockets off; HTTP/3 → try disabling |
| Title appears with no artwork/wrong match | Filename doesn't follow `Movie (Year)` / `Show - S01E01` (§3) |
| Plex can't see the files | `plex` user lacks read permission on the folder (§2) |
| Title never shows up in Plex | `journalctl -u mwatcher-bridge -f`; `curl -s localhost:8889/jobs`; look for `.part` files in `staging/` |
| `Fast Combo returned no streams` | Addons not added/switched on at `http://127.0.0.1:7000/<key>/configure`, or wrong `FASTCOMBO_ACCESS_KEY`, or `fastcombo` not running |
| `none are directly downloadable` | Every addon returned torrents (`infoHash`). You need a debrid service or addons that return direct HTTP links |
| Good 4K/big files keep disappearing | Fast Combo's bitrate caps (`max1080` 8 Mbps / `max4k` 20 Mbps) or Cinemeta unreachable → runtime falls back to 120/45 min → estimated bitrate inflates (§4.3) |
| Search returns nothing | `CINEMETA_URL` unreachable from the server: `curl -s "$CINEMETA_URL/catalog/movie/top/search=dune.json"`. Pass `--imdb` instead |
| Download starts then dies | Expected — the bridge fails over to the next-best link. Check `attempt`/`tried` in `/jobs`; raise `FASTCOMBO_MAX_FALLBACKS` |
| Every download rejected as "too small" | `TELESTREAM_MIN_BYTES` (default 20 MB) is above your content's size — lower it for short/low-bitrate material |
| Good short clips rejected as "truncated" | Lower `TELESTREAM_MIN_DURATION` (default 30 s) |
| Deep media check never runs | `ffprobe` missing: `sudo apt install -y ffmpeg` (or set `TELESTREAM_VERIFY_MEDIA=0` to skip it) |
| `download command exited N` | No downloader installed (`pipx install yt-dlp`), or the host needs headers the tool can't send (use yt-dlp, not ffmpeg) |
| `journalctl` says `Invalid environment assignment` | A systemd `Environment=` value contains a space. Quote the **whole** assignment: `Environment="TELESTREAM_TV_DIR=/home/afine/media/TV Shows"` |
| `{stream}`/`{url}` reaches the shell literally | Expected — systemd does not expand them (only `$VAR`/`${VAR}`). The *Python* bridge substitutes them. To write a literal `${url}` in a unit, use `$${url}` |
| `EnvironmentFile` ignored / key empty | The file must exist and be readable by the service user; `chmod 600` and `chown afine:afine` it. Verify with `systemctl show mwatcher-bridge -p Environment` |
| Remote app playback demands payment | Plex Pass required for remote mobile/TV streaming (see top of doc) |

---

## Quick command cheat sheet

```bash
sudo systemctl status plexmediaserver fastcombo mwatcher-bridge cloudflared tailscaled --no-pager
sudo journalctl -u mwatcher-bridge -f              # what the bridge is fetching, and why
sudo journalctl -u fastcombo -f                    # addon queries + link probing
sudo ss -tlnp | grep -E '32400|7000|8889'

curl -s http://127.0.0.1:32400/identity            # Plex alive?
curl -s http://127.0.0.1:8889/healthz              # bridge + Fast Combo configured?
curl -s http://127.0.0.1:8889/config               # effective settings
curl -s "http://127.0.0.1:8889/search?q=dune"      # title -> IMDb id
curl -s "http://127.0.0.1:8889/streams?id=tt1160419&prefer=fastest"   # ranked candidates
curl -s http://127.0.0.1:8889/jobs                 # queue + provenance
curl -s http://127.0.0.1:8889/seerr                # Seerr reachable? what is queued?
curl -s -X POST http://127.0.0.1:8889/request -H 'Content-Type: application/json' \
  -d '{"title":"Dune","year":2021}'                # request it -> Radarr/Sonarr fetch it
curl -s -X POST http://127.0.0.1:8889/fetch -H 'Content-Type: application/json' \
  -d '{"title":"Dune","year":2021,"action":"both"}'  # watch now AND own it

sudo bash install.sh seerr                         # bring the Seerr stack up
sudo bash install.sh doctor                        # includes the Seerr request path (§6)
cd ~/mwatcher-seerr && docker compose ps           # Seerr/Radarr/Sonarr/qBittorrent health
cd ~/mwatcher-seerr && docker compose logs -f seerr
curl -s -H "x-admin-key: $FC_ADMIN_PASSWORD" \
  "http://127.0.0.1:7000/$FC_ACCESS_KEY/api/try/movie/tt1160419?fresh=1"   # why streams were dropped

sudo apt update && sudo apt install -y plexmediaserver   # upgrade Plex
cd ~/stremio-addons && git pull && sudo systemctl restart fastcombo        # upgrade Fast Combo
```
