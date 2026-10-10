# Work log

Engineering log for this branch: what was decided, what was verified, what
broke and how. Written so the next session — or the next person — does not
re-derive any of it.

Session memory does not survive a sandbox recycle. This file is committed, so
it does.

---

## 1. Where things stand

| | |
|---|---|
| Branch | `arena/e20948b7-mwatcher` |
| Pushed HEAD | `7daed62` — verify with `git ls-remote --heads origin arena/e20948b7-mwatcher` |
| History | `32c014c` initial → `d46ab5a` bridge+installer → `caf563e` Seerr → `bceb51e` play-through → `7daed62` split topology |
| Deploy target | **Lubuntu box** `afine@192.168.0.34` (Plex + library + bridge). Addons run on a **separate VPS** `ubuntu@stremio-vnic`. |

The installer is the entry point: `sudo bash ~/Mwatcher/install.sh`.
Subcommands: `status`, `doctor [title]`, `seerr`, `uninstall`, `--help`.

### Sandbox quirks (why work keeps looking lost)

These are environment artefacts, not code bugs. Confirm before "fixing" anything:

- **Every process dies between turns.** All four demo services must be
  restarted each session (recipe in §5). Probe first:
  `(exec 3<>/dev/tcp/127.0.0.1/8889) 2>/dev/null && echo up`
- **Local git rewinds to `32c014c`** while the working tree keeps the new
  files. Recovery, never `git reset --hard`:
  ```
  git fetch -q origin arena/e20948b7-mwatcher && git reset --soft FETCH_HEAD
  ```
- `/home/user/sa-tmp`, `/tmp/*`, and site-packages are wiped on recycle
  (PyYAML disappears; `pip install` needs `--break-system-packages`).
- `nohup … &` hangs to the bash timeout — always use `start_process`.
- Egress is allowlisted: `github.com` works, `raw.githubusercontent.com` and
  `v3-cinemeta.strem.io` mostly do not. `ffprobe`/`ffmpeg` and `xxd` are
  absent (use `od -An -tx1`), and there is no Docker.

---

## 2. Decision record

Ruled out — do not re-propose:

| Rejected | Why |
|---|---|
| Stremio-style addon install URL for Plex | Plex has no plugin framework since 2018; sources must be *files* |
| Plex `.bundle` plugins | Dead framework |
| Cloudflare **quick** tunnel for Plex | No stable hostname; breaks `*.plex.direct` certs |
| Seerr as a downloader | Seerr only creates requests; Radarr/Sonarr fulfil them |
| Hooking Stremio's Play button to fire a Seerr request | Not reachable from the client |
| `.strm` as the main path | Was rejected, then **explicitly reversed by the user** — scrape-and-play-through is what was asked for |

Standing constraints from the user:

- One command, and it must **check what is already installed** rather than
  blindly reinstall.
- **Never regenerate an existing secret env file** — that would rotate
  `FC_ACCESS_KEY`.
- Commands must be **paste-safe**: no bare `install.sh` (auto-links), no `>`
  redirects (arrive as `&gt;`). Prefer `sudo bash ~/Mwatcher/install.sh status`.
- Seerr must remove the need for a debrid service.
- Do **not** permanently download on the Stremio path — cache and play through.

---

## 3. Verified results

Numbers actually measured, not asserted.

### Play-through (`bceb51e`)

| Check | Result |
|---|---|
| `.strm` size | **45 bytes** |
| `Range: bytes=0-` on `/play/<key>.mkv` | `206`, `Content-Range: bytes 0-4194303/4194304`, `Accept-Ranges: bytes`, `X-Mwatcher-Stream: scraped live, candidate 2/3` |
| Bytes returned | 4194304, magic `1a45dfa3` (Matroska — not HTML) |
| Replay | cache hit, `cmp`-identical |
| Seek `Range: bytes=2000000-2000999` | exactly 1000 bytes |
| HTML-wall rejection | attempt 1 refused (`downloaded a web page, not a video (found '<!doctype html'`), attempt 2 succeeded |
| `action=both` | Seerr `pending` **and** file downloaded |

**The key fix:** play-through cannot validate after headers are sent — once
`send_response` runs, failover is impossible and Plex will happily play HTML,
which *is* error s1001. Read the first `CHUNK`, run `sniff_html()` plus a
`Content-Type` check for `text/html`/`application/json`, and only then commit.
`continue` inside `with upstream:` closes it cleanly.

### Split topology (`7daed62`)

| Check | Result |
|---|---|
| Remote unreachable | `status` → `· Fast Combo is remote: http://203.0.113.7:7000 (not a local port)`; `doctor` §1 prints the `ssh -N -L` fix |
| Loopback URL | `FC_BASE_URL=http://127.0.0.1:7000` correctly still treated as **local** |
| Unit rewrite | `Environment=FASTCOMBO_BASE_URL=` sed yields the remote URL when set, `http://127.0.0.1:7000` by default |
| `fastcombo-tunnel.service` | `systemd-analyze verify` clean |
| `gen_key` under `set -Eeuo pipefail` | 16/12/24 chars, no SIGPIPE, no silent exit |
| `ERR` trap | fires on an injected failure naming line + command; silent on success |
| `bridge.env` repair | key appended when absent · corrected when wrong · no-op on re-run · 664 → 600 |
| play-through reachability | 12 helper checks + 4 end-to-end: bind widened, LAN IP derived, idempotent, untouched when off |
| `plex_setup.py` vs `demo/fake_plex.py` | claim → libraries → scan → verify, all green; idempotent re-run; not-signed-in fails cleanly; agent-worded 400 surfaces Plex's real sentence *and* the restart hint; language-worded 400 surfaces the sentence and suppresses the hint |
| `install.sh auto` | end-to-end against the fake Plex, exit 0; unknown args warned and ignored; `AUTO_MODE` suppresses the manual Next-steps block |
| `envfile` + the CLI | the user's exact failing command now resolves and downloads with the key present **only** in `bridge.env`; an explicit env var still overrides it; spaces in `TELESTREAM_TV_DIR` preserved; matched quotes stripped from `TELESTREAM_DOWNLOAD_CMD` with its inner quoting intact; comments, `export `, and empty values handled |
| `status` addon count | old expression yielded `0\|0\|` (two lines) under `pipefail`, new yields `0\|` |
| play-table persistence | keys survive a fresh process; reloaded at import; a CLI `--add` merges (2 → 3) instead of overwriting |
| duplicate libraries | joins the existing section (2 folders, no duplicate names), warns about the old path, idempotent on re-run, `--separate-libraries` still creates a second one |
| claim when already signed in | exit 0 with "the claim token was not needed"; `do_auto` no longer trips the ERR trap |

### Adopting an existing Fast Combo (layout C — all on the VPS)

Reinstalling on a box whose addons already work is destructive: a second clone gets a fresh
`FC_ACCESS_KEY`, breaking the addon URL saved in Stremio, and rewriting `fastcombo.service`
repoints the *running* service at that unconfigured clone. `fc_detect_existing` prevents it.
Verified by sourcing the script's functions and running seven fixtures:

| Fixture | Result |
|---|---|
| Nothing installed | no adoption, clones as before |
| Clone at `~/stremio-addons` + `.env` | adopted; key **and** admin password recovered |
| Clone at `~/fastcombo` instead | adopted, `FC_DIR` repointed to the real directory |
| Our `fastcombo.env` already present | ours wins over the clone's `.env` |
| `FC_ACCESS_KEY=<key>` given | override wins over everything detected |
| `FC_BASE_URL=https://…` (remote) | never adopts — layout B unaffected |
| `FC_BASE_URL=http://127.0.0.1:7000` | loopback = local, so adoption still applies |

Detection asks systemd rather than guessing paths: `fc_find_unit` confirms the conventional
names through `systemctl show -p FragmentPath`, then falls back to scanning
`/etc/systemd/system`, `*.target.wants`, `/usr/lib/systemd/system` and `/lib/systemd/system`
for a unit pointing at a stremio-addons or fastcombo tree. `fc_unit_dir` reads
`WorkingDirectory`, then the `.js` path out of `ExecStart`. Credentials come from our env
file, the clone's `.env`, then the unit's `EnvironmentFiles` — **before** its inline
`Environment=`, because systemd lets `EnvironmentFile=` override `Environment=`, so the
inline value is usually the stale one. `fc_is_clone` accepts `server.js`, `index.js`,
`app.js`, `src/server.js` or `src/index.js`; requiring `server.js` alone is what made the
first version miss a live install and offer to re-clone over it. When adopting, only
`mwatcher-bridge.service` is installed and the existing unit is never written.

**Field report — `afine@adblock`, Ubuntu 26.04.1, the run that found three bugs.** Plex
1.43.4 already installed and running, `fastcombo` service up since Oct 3, `~/stremio-addons`
already cloned. The install printed sections 1–4 and then **stopped with no message at all**,
leaving no `fastcombo.env`, no `bridge.env`, no `mwatcher-bridge.service`:

```
4. Fast Combo (your Stremio addons)
  ✓ already cloned: /home/afine/stremio-addons
afine@adblock:~$            <- script gone, exit status swallowed
```

Cause was `gen_key` (trap 14). It also showed the first adoption pass failing to recognise a
machine that plainly had a working Fast Combo, and `yt-dlp` reporting failure immediately
after installing successfully (trap 16). All three are fixed; the ERR trap (trap 15) means a
fourth would at least announce itself.

### Gates run every change

`bash -n install.sh` · `python3 -m py_compile scripts/*.py demo/*.py` ·
`systemd-analyze verify` on each unit (a `.example` must be copied to a
`.service` name first) · dashboard HTTP 200 · all 7 GET routes 200 ·
bogus `/play/deadbeef00.mkv` → 404 · `status`/`doctor`/`--help` exit 0.

---

## 4. Traps that cost real time

1. **`rm -rf /tmp/mwatcher-demo/{Movies,TV Shows,cache}/*` silently
   under-deletes.** Brace expansion yields `…/TV Shows/*`, which word-splits
   into `…/TV` and `Shows/*`. Quote paths with spaces separately, and verify
   cleanups with mtimes: `find … -printf '%TH:%TM:%TS %p'`.
   This caused a false alarm — two "duplicate" library files were stale
   leftovers from before a restart, not a defect.
2. **`curl -s $B/plays | …['plays'][0]` returns the NEWEST entry** (created
   DESC), not the one just added. A test assuming otherwise mislabelled a
   Breaking Bad play as Dune.
3. **`DEMO_TRAP` did not fire** because its condition was
   `not self.headers.get("Range")` — but Plex and curl send `Range: bytes=0-`.
   A trap keyed on "no Range" cannot exercise any streaming path. Now it
   whitelists only 1–3 byte probes. The trap must answer **200, not 403**, and
   its ~150 B body needs `TELESTREAM_MIN_BYTES=100`.
4. **A pre-existing output file masks the failover demo** — `run_job`
   short-circuits on `os.path.exists(final_path)` → `skipped=True`. Same for a
   cached play file making `/play` skip upstream. Clear before re-testing.
5. **`log()` wrote to stdout**, corrupting CLI JSON. Now stderr.
6. **`set -euo pipefail` + `find` inside `$( )`** dies silently on a missing
   dir. Use `2>/dev/null | wc -l || echo 0`, `[ cond ] && cmd || true`,
   `cmd || n=$?`, and end functions on a zero-status statement.
7. **`sed '/PAT/,/^$/p'` on `--help` truncates misleadingly** — verify with `tail`.
8. **systemd `Environment=` with an unquoted space** → `Invalid environment
   assignment`. In the bridge unit, `EnvironmentFile=` (line 64) wins over
   `Environment=` (line 54).
9. **Seerr enums are not interchangeable.** RequestStatus: 1 pending,
   2 approved, 3 declined, 4 processing, 5 failed. MediaStatus: 1 unknown,
   2 pending, 3 processing, 4 partially available, 5 available.
10. **An empty `find` result is not proof a file is missing** — the path or the
    filesystem may be out of scope (`-xdev` skips other mounts).
11. **Seerr keys requests by TMDB id, never IMDb**, and a 404 is ambiguous —
    parse `{"errors":[{"message":…}]}`. `request()` must probe `media_status()`
    first. The API key is an **admin credential**: chmod 600, never sent to the
    browser, masked by `/config`.
12. **Wrong-type metadata made a movie look like a series** — the fake addon now
    mirrors Cinemeta's 404 on `/meta/series/<movie-id>`.
13. **An installer that "repairs" can destroy a working install.** On the box where Fast
    Combo already runs, generating a new key and rewriting the unit breaks the addon URL in
    the user's Stremio app and repoints the live service at an unconfigured clone. "Safe to
    re-run" has to mean *adopt what is there*, not just *don't overwrite the env file*. See
    §3 for the detection order.
14. **`gen_key` killed the installer silently on a real machine.** It was
    `tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$n"`. `head` closes the pipe early, `tr`
    takes SIGPIPE and exits **141**, `pipefail` makes that the pipeline's status, and
    `set -e` then aborts on `k="$(gen_key 16)"` — a failing command substitution inside an
    assignment *does* trigger `set -e`. No output, no exit message, install stops mid-way.
    Reproduced: `bash gk.sh` prints "before" and never "after", exit 141. Fixed by reading a
    bounded chunk (`head -c 512 /dev/urandom | tr -dc …`) in a loop, so nothing is ever
    interrupted. **Never pipe an endless source into `head` under `pipefail`.**
15. **`set -e` exits without saying anything.** A half-finished install with no error is far
    worse than an error, because the user cannot tell what is missing. `install.sh` now runs
    `set -Eeuo pipefail` with an `ERR` trap printing `install.sh:<line> failed (exit N)`, the
    failing `$BASH_COMMAND`, and a note that the install is incomplete and safe to re-run.
    `-E` (errtrace) is required or the trap is not inherited by functions. Watch the quoting:
    the trap body must be single-quoted so `$LINENO`/`$?`/`$BASH_COMMAND` expand when it
    *fires*, and the inner `printf` format must therefore be double-quoted — nesting single
    quotes inside is a syntax error that `bash -n` catches.
16. **`~/.local/bin` is not in sudo's `secure_path`.** `pip install --user yt-dlp` succeeds,
    then `have yt-dlp` fails and the installer reports "yt-dlp install failed" for a tool
    that is present — and the bridge, started by systemd, would not find it either. `PATH`
    now gains `$RUN_HOME/.local/bin` right after `RUN_HOME` is resolved, which fixes both the
    report and the service.
17. **`sed 's|^KEY=.*|value|'` silently does nothing when the line is absent** — and the
    installer then printed "keys now match". A hand-made `bridge.env` (created with `nano`
    after a failed run) has no `FASTCOMBO_ACCESS_KEY` line at all, so the "fix" was a no-op
    that claimed success. Now: append when absent, substitute when wrong, warn when no key
    can be determined, and tighten the file to mode 600 — `nano` leaves 664, which leaks an
    access key to every local user. Verified on all four paths, including that a re-run
    changes nothing.
18. **`BRIDGE_HOST=127.0.0.1` silently defeats play-through.** The unit binds loopback, but
    `.strm` files carry `TELESTREAM_PUBLIC_BASE_URL` and Plex clients on other machines must
    reach it. Result: a title plays on the server and gives s1001 on every phone and TV — the
    most confusing possible failure, because the machine you test on works. Doctor caught it
    *after* a `.strm` existed; nothing caught it at install time, and the unit even shipped a
    commented `TELESTREAM_PUBLIC_BASE_URL=http://192.168.0.34:8889` sitting right next to
    `Environment=BRIDGE_HOST=127.0.0.1`. §5b now widens the bind when play-through is on and
    derives the LAN address if unset. `EnvironmentFile=` comes *after* `Environment=` in the
    unit, so writing `BRIDGE_HOST` into `bridge.env` overrides it and survives the unit being
    rewritten — no `override.conf` needed.
19. **`printf '%s' "'{\"title\":\"Dune\"}'"` eats the quotes.** Inside a double-quoted bash
    argument, `\"` becomes `"`, which then terminates the surrounding double-quoted string, so
    the printed curl example came out as `-d '{title:Dune,year:2021}'` — a command the user
    would paste and get a 400 from. Whole example on one `printf` with the format string
    double-quoted and the JSON escaped once, not twice.
20. **`global X` must precede any read of `X` in that function**, including a read in an
    `argparse` default — otherwise `SyntaxError: name 'X' is used prior to global declaration`.
21. **`and` binds tighter than `or`.** `if problems and "agent" in e or "scanner" in e:` parsed
    as `(problems and "agent" in e) or ("scanner" in e)`, so the restart hint would have fired
    on any error mentioning a scanner even with zero problems. Parenthesise.
22. **systemd's `EnvironmentFile=` does not exist for a shell.** The bridge worked perfectly
    as a service while the identical CLI call failed with "FASTCOMBO_ACCESS_KEY is not set" —
    and `install.sh status` said the key was set and Fast Combo answered with it, so the two
    outputs flatly contradicted each other. The installer's own Next-steps block printed that
    broken command. `scripts/envfile.py` now loads `bridge.env` at import for every CLI entry
    point, with real environment variables still winning. **Verified against the user's real
    box:** their Fast Combo turned out to live in `/opt/fastcombo`, not `~/stremio-addons` —
    adoption via `systemctl show -p WorkingDirectory` found it where path-guessing could not.
23. **`grep | wc -l || echo 0` prints two zeros under `pipefail`** when grep matches nothing:
    `wc` emits its own `0`, then pipefail fails the pipeline and `|| echo 0` adds a second
    line, so `${n:-0}` rendered a bare `0` on its own line in `status`. Wrap the grep in
    `{ grep … || true; }` instead of rescuing the pipeline.
24. **The play-through table lived only in RAM, so every restart orphaned the library.**
    Keys are random (`uuid4().hex[:10]`) and `PLAY` was a module-level dict, so a reboot — or
    the `systemctl restart mwatcher-bridge` the installer itself recommends after editing
    `bridge.env` — left every `.strm` pointing at a key nothing knew about. Plex gets a 404
    from a pointer that looks perfectly valid, which is indistinguishable from s1001. Now
    persisted atomically to `TELESTREAM_PLAY_FILE` and reloaded **at import**, so a one-shot
    CLI `--add` merges into the table instead of replacing it with one entry. Candidates are
    deliberately not saved: addon links expire in minutes, so the first play after a restart
    re-scrapes, which is the behaviour you want.
25. **`return "$rc"` with a non-zero rc trips the ERR trap.** `do_auto` finished a complete
    install, returned 1 because a claim token was refused, and the trap printed "the install
    is INCOMPLETE" over an install that was fine. Keep the real status in a global and let the
    dispatcher `exit` with it.
26. **Plex answers a claim token with 401 once it already belongs to an account.** That is the
    outcome the caller wanted, not a failure — check `is_claimed()` first and say so.
27. **Two libraries called "Movies" is worse than one library with two folders.** A previous
    project on the same box had already created `Movies` and `TV Shows` pointing at
    `/opt/stremio-plex-bridge/media`, so the automation made a second pair: Plex shows
    duplicates and it is easy to click the wrong one and play unrelated media. `PUT
    /library/sections/<id>` now joins the existing section, sending existing paths *plus* the
    new one because PUT replaces the whole list. `--separate-libraries` restores the old
    behaviour.
28. **Test fixtures that share a scratch directory must not clean each other's.** Two
    regression scripts both used `/tmp/fc`; the second deleted it on entry, so the first
    "failed" when run afterwards. Ordering artefacts look exactly like regressions — run each
    suite in isolation before believing a failure.

---

## 5. Demo restart recipe

Four services. Fast Combo is the real upstream; the addon, Cinemeta and Seerr
are local fakes. Start the two fakes first, then Fast Combo, then the bridge.

```
# deps (wiped on recycle)
cd /home/user
git clone --depth 1 https://github.com/AfzalAshraf/stremio-addons sa-tmp
mkdir -p /tmp/mwatcher-demo/staging /tmp/mwatcher-demo/Movies "/tmp/mwatcher-demo/TV Shows" /tmp/mwatcher-demo/cache
```

All four via `start_process`, each with an `exec` prefix:

| Name | cwd | Command |
|---|---|---|
| Fake addon + Cinemeta | `Mwatcher` | `DEMO_PORT=9912 DEMO_TRAP=4k exec python3 demo/fake_stremio_addon.py` |
| Fake Seerr | `Mwatcher` | `SEERR_HOST=127.0.0.1 DEMO_PORT=5055 SEERR_API_KEY=testkey exec python3 demo/fake_seerr.py` |
| Fast Combo (real) | `sa-tmp` | `PORT=7000 HOST=127.0.0.1 FC_ACCESS_KEY=testkey123456 FC_ADMIN_PASSWORD=testpass1234 FC_UPSTREAMS=http://127.0.0.1:9912/manifest.json FC_NO_STORAGE=1 FC_ADDON_NAME="Fast Combo (demo)" exec node server.js` |
| Bridge + dashboard | `Mwatcher` | see below |

Bridge env (one line, space-separated):

```
BRIDGE_HOST=0.0.0.0 BRIDGE_PORT=8889 FASTCOMBO_PREFER=best
FASTCOMBO_BASE_URL=http://127.0.0.1:7000 FASTCOMBO_ACCESS_KEY=testkey123456
CINEMETA_URL=http://127.0.0.1:9912
TELESTREAM_STAGING=/tmp/mwatcher-demo/staging
TELESTREAM_MOVIES_DIR=/tmp/mwatcher-demo/Movies
TELESTREAM_TV_DIR='/tmp/mwatcher-demo/TV Shows'
TELESTREAM_CACHE_DIR=/tmp/mwatcher-demo/cache TELESTREAM_CACHE_MAX_GB=50
TELESTREAM_PUBLIC_BASE_URL=http://192.168.0.34:8889
TELESTREAM_DOWNLOAD_CMD='curl -fsSL --retry 1 {headers} -o {out} {stream}'
TELESTREAM_MIN_BYTES=100
SEERR_URL=http://127.0.0.1:5055 SEERR_API_KEY=testkey SEERR_MODE=off
```

then `exec python3 scripts/telestream_to_plex.py serve`.

**Bind to `0.0.0.0`** — the preview is proxied, and `127.0.0.1` gives a broken
preview.

### Seed the three modes

```
B=http://127.0.0.1:8889
curl -s -X POST $B/add   -H 'Content-Type: application/json' -d '{"title":"Dune","year":2021,"imdb":"tt1160419"}'
curl -s -X POST $B/fetch -H 'Content-Type: application/json' -d '{"title":"Breaking Bad","imdb":"tt0903747","kind":"show","episode":"S01E01","action":"strm"}'
curl -s -X POST $B/fetch -H 'Content-Type: application/json' -d '{"title":"Interstellar","year":2014,"imdb":"tt0816692","action":"both"}'
```

Wait ~13 s for the download job, then confirm the pointer really streams:

```
curl -s -o /tmp/d.bin -w '%{http_code} %{size_download}\n' -H 'Range: bytes=0-' "$B/play/<key>.mkv"
head -c 4 /tmp/d.bin | od -An -tx1     # want: 1a45dfa3
```

Expected library: Interstellar `.mkv` at 4194304 B, Dune `.strm` at 45 B,
Breaking Bad `.strm` at 45 B under `TV Shows/Breaking Bad/Season 01/`.

---

## 6. Open items

- [ ] `TELESTREAM_PUBLIC_BASE_URL` must be reachable from Plex **clients**;
      loopback ⇒ s1001 on every device but the server itself.
- [ ] Play-through puts an **unauthenticated** media endpoint (`/play/<key>`) in
      the playback path. Remote clients need Tailscale or an authed reverse
      proxy — not a bare public `:8889`.
- [ ] The VPS side of layout B needs `ssh-copy-id` before
      `fastcombo-tunnel.service` can start unattended.
- [ ] Seerr is only ever tested against `demo/fake_seerr.py`; the compose stack
      is YAML-validated only (no Docker in the sandbox).
- [ ] Away from home, play-through needs `TELESTREAM_PUBLIC_BASE_URL` pointed at a Tailscale
      IP; the installer cannot know that address, so it only ever derives the LAN one.
- [ ] `TELESTREAM_CACHE_MAX_GB` default is 20 in code; the demo runs 50.
      Undecided whether 50 should become the shipped default.

---

## 7. Reference material condensed here

Full detail lives in `docs/PLEX_GLOBAL_ACCESS.md`; these are the load-bearing facts.

**Plex s1001 (network error).** Top cause per the accepted forum answer: server
log `MDE: video has neither a video stream nor an audio stream` → the file is
not a video file. Verify in VLC / force **Analyze** / check Media Info. Also: a
dead **Settings → Extras → Movie pre-roll video** URL breaks *every* title;
corrupt DB (delete `com.plexapp.plugins.library.db-shm`/`-wal`, restart,
`VACUUM;`, or PlexDBRepair); `secureConnections="2"` with a non-`*.plex.direct`
cert; a custom URL containing `127.0.0.1`; the ~2 Mbps Relay cap; CGNAT
(`100.64.0.0/10`); the `plex` user unable to read the file; rclone-mount I/O
errors.

**Seerr.** Auth header `X-Api-Key`; key from Settings → General. Base
`/api/v1`, port 5055, image `fallenbagel/seerr:latest`, health
`/api/v1/settings/about`. `POST /api/v1/request` with
`{"mediaType":"movie","mediaId":<TMDB>}`; TV all seasons adds
`"seasons":"all"`, specific ones `"seasons":[1,3]`. Optional pass-throughs:
`is4k`, `serverId`, `profileId`, `rootFolder`, `tags`, `languageProfileId`,
`userId`. `GET /api/v1/search?query=` returns `{page,results,totalCount}` with
`mediaType`, `id` (TMDB), `title`/`name`, `releaseDate`/`firstAirDate`,
`mediaInfo.status`. Reference compose ports: radarr 7878, sonarr 8989,
prowlarr 9696, qbittorrent 8080 (+6881 tcp/udp), bazarr 6767. Wiring order:
qBittorrent (change `admin/adminadmin`) → Prowlarr → link Prowlarr to
Radarr/Sonarr → Download Clients (host = docker service name, category
`sonarr`/`radarr`).

**Fast Combo** (`github.com/AfzalAshraf/stremio-addons`, v2.1.0). Per request:
parallel ask → drop CAM/TS/REMUX/download-only/ads/error cards → dedupe fastest
→ hide wrong episodes → live-probe → hide soon-expiring → sort tested-working
then best-picture-per-byte. **Each install generates its own `FC_ACCESS_KEY`
and `FC_ADMIN_PASSWORD`.** Stremio needs https for non-local addons; set
`FC_PUBLIC_URL` behind a proxy. `/api/*` is admin-gated, so the bridge uses
`/{key}/stream/...`. Silently dropping large files is *by design*
(`filterReason()` bitrate caps). Env: `FC_SECRET`, `FC_MAX_ADDONS` (50/15),
`FC_UPSTREAMS`, `FC_ADDON_NAME`, `FC_FRESH_SECONDS` 120, `FC_CACHE_MINUTES` 15,
`FC_NEW_HOURS` 24, `FC_MAX_PROBES`/`FC_PROBE_CONCURRENCY`/`FC_PROBE_TIMEOUT_MS`,
`FC_AI_CATALOG`, `FC_LLM_*`, `FC_DATA_FILE`/`FC_NO_STORAGE=1`, `FC_PRIVATE_HOST`.

**Plex install/networking.** apt repo `https://repo.plex.tv/deb/ public main`,
key `https://downloads.plex.tv/plex-keys/PlexSign.v2.key` →
`/etc/apt/keyrings/plexmediaserver.v2.gpg` with `signed-by=`. Remote access
needs one inbound TCP path to internal **32400** ("Manually specify public
port"). Plex-over-cloudflared: named tunnel, `originServerName: "*.plex.direct"`,
`noTLSVerify: true`, LAN-first custom URLs, WebSockets on, caching/Rocket
Loader off. Tailscale for CGNAT: `serve --bg --https=443` + `funnel --bg 443 on`.
