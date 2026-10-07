#!/usr/bin/env bash
# =============================================================================
#  Mwatcher -- one command to set up (or repair) Plex + Fast Combo + the bridge
# =============================================================================
#
#   sudo bash install.sh                     install / repair, then show status
#   sudo bash install.sh status              change nothing, just report
#   sudo bash install.sh doctor              why won't things play? (s1001 etc.)
#   sudo bash install.sh doctor "The Uprising"    diagnose ONE title
#   sudo bash install.sh uninstall           remove services (keeps your media)
#
#  Safe to re-run: it detects what is already installed, never overwrites your
#  existing access key / password / addon list, and only adds what is missing.
#
#  Ubuntu 20.04+ / Debian 11+ / Lubuntu. Needs sudo.
# =============================================================================
set -euo pipefail

# --------------------------------------------------------------- who / where
if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
  RUN_USER="$SUDO_USER"
else
  RUN_USER="${USER:-$(id -un)}"
fi
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
[ -n "$RUN_HOME" ] || { echo "Could not resolve a home directory for $RUN_USER"; exit 1; }

# Where this script's repo lives (units point here).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/scripts/telestream_to_plex.py" ]; then
  REPO_DIR="$SCRIPT_DIR"
elif [ -f "$RUN_HOME/Mwatcher/scripts/telestream_to_plex.py" ]; then
  REPO_DIR="$RUN_HOME/Mwatcher"
else
  REPO_DIR=""
fi

FC_DIR="${FC_DIR:-$RUN_HOME/stremio-addons}"
CONFIG_DIR="$RUN_HOME/.config/mwatcher"
MEDIA_DIR="${MEDIA_DIR:-$RUN_HOME/media}"
PLEX_DATA="/var/lib/plexmediaserver/Library/Application Support/Plex Media Server"
PLEX_PREFS="$PLEX_DATA/Preferences.xml"
PLEX_LOG="$PLEX_DATA/Logs/Plex Media Server.log"

FC_PORT="${FC_PORT:-7000}"
BRIDGE_PORT="${BRIDGE_PORT:-8889}"

# --------------------------------------------------------------- pretty print
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'
  G=$'\033[32m'; Y=$'\033[33m'; E=$'\033[31m'; C=$'\033[36m'
else
  B=""; D=""; R=""; G=""; Y=""; E=""; C=""
fi
ok()   { printf '  %s✓%s %s\n' "$G" "$R" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$R" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$E" "$R" "$*"; }
info() { printf '  %s·%s %s\n' "$D" "$R" "$*"; }
hdr()  { printf '\n%s%s%s\n' "$B$C" "$*" "$R"; }
die()  { printf '\n%sERROR:%s %s\n' "$B$E" "$*" >&2; exit 1; }

need_root() {
  [ "$(id -u)" = "0" ] || die "this needs sudo:  sudo bash install.sh $1"
}
as_user() { sudo -u "$RUN_USER" -H bash -c "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3>&- 3<&-; return 0; } || return 1; }
svc_active() { systemctl is-active --quiet "$1" 2>/dev/null; }

# =============================================================================
#  status
# =============================================================================
do_status() {
  hdr "Mwatcher status  (user: $RUN_USER)"

  printf '\n%sServices%s\n' "$B" "$R"
  for s in plexmediaserver fastcombo mwatcher-bridge; do
    if svc_active "$s"; then
      ok "$s  $(systemctl show -p ActiveEnterTimestamp --value "$s" 2>/dev/null | sed 's/^/since /')"
    elif systemctl list-unit-files 2>/dev/null | grep -q "^$s.service"; then
      bad "$s  installed but NOT running  →  sudo journalctl -u $s -n 30 --no-pager"
    else
      warn "$s  not installed"
    fi
  done

  printf '\n%sListening ports%s\n' "$B" "$R"
  port_open 32400     && ok "32400  Plex Media Server"        || bad "32400  Plex is not listening"
  port_open "$FC_PORT"    && ok "$FC_PORT  Fast Combo (your addons)"  || bad "$FC_PORT  Fast Combo is not listening"
  port_open "$BRIDGE_PORT" && ok "$BRIDGE_PORT  Mwatcher bridge + dashboard" || bad "$BRIDGE_PORT  bridge is not listening"

  printf '\n%sPaths%s\n' "$B" "$R"
  [ -n "$REPO_DIR" ] && ok "repo:      $REPO_DIR" || warn "repo:      not found"
  [ -d "$FC_DIR" ]   && ok "Fast Combo: $FC_DIR"  || warn "Fast Combo: $FC_DIR missing"
  for d in "$MEDIA_DIR/Movies" "$MEDIA_DIR/TV Shows" "$MEDIA_DIR/staging"; do
    [ -d "$d" ] && ok "library:   $d" || warn "library:   $d missing"
  done
  for f in "$CONFIG_DIR/fastcombo.env" "$CONFIG_DIR/bridge.env"; do
    if [ -f "$f" ]; then
      local perm; perm="$(stat -c '%a' "$f" 2>/dev/null || echo '?')"
      [ "$perm" = "600" ] && ok "config:    $f  (mode 600)" || warn "config:    $f  (mode $perm — should be 600)"
    else
      warn "config:    $f missing"
    fi
  done

  printf '\n%sTools%s\n' "$B" "$R"
  have node    && ok "node $(node --version)"                     || bad "node missing (Fast Combo needs 18+)"
  have python3 && ok "python3 $(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')" || bad "python3 missing"
  if have yt-dlp;   then ok "yt-dlp $(yt-dlp --version 2>/dev/null | head -1 || echo installed)"
  elif have ffmpeg; then warn "ffmpeg present but yt-dlp is better:  pipx install yt-dlp"
  else bad "no downloader (need yt-dlp or ffmpeg)"; fi
  have ffprobe && ok "ffprobe (used by doctor)" || warn "ffprobe missing — doctor cannot verify media files"

  printf '\n%sKeys%s\n' "$B" "$R"
  local key=""
  [ -f "$CONFIG_DIR/fastcombo.env" ] && key="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" | head -1 | cut -d= -f2- || true)"
  if [ -n "$key" ]; then
    ok "Fast Combo access key set (${#key} chars)"
    info "control panel:  http://127.0.0.1:$FC_PORT/$key/configure"
    info "dashboard:      http://127.0.0.1:$BRIDGE_PORT/"
    if port_open "$FC_PORT"; then
      local n
      n="$(curl -s -m 8 "http://127.0.0.1:$FC_PORT/$key/manifest.json" 2>/dev/null | grep -o '"Addon [0-9]*"' | wc -l || echo 0)"
      curl -s -m 8 "http://127.0.0.1:$FC_PORT/$key/manifest.json" 2>/dev/null | grep -q '"id"' \
        && ok "Fast Combo answers with that key" \
        || bad "Fast Combo rejects that key — bridge.env and fastcombo.env disagree"
      info "addons merged into the manifest description: ${n:-0}"
    fi
  else
    bad "no FC_ACCESS_KEY in $CONFIG_DIR/fastcombo.env"
  fi

  local bkey=""
  [ -f "$CONFIG_DIR/bridge.env" ] && bkey="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" | head -1 | cut -d= -f2- || true)"
  if [ -n "$bkey" ] && [ -n "$key" ]; then
    [ "$bkey" = "$key" ] && ok "bridge uses the same access key" \
                         || bad "MISMATCH: bridge.env key ≠ fastcombo.env key — lookups will 404"
  fi

  printf '\n%sLibrary contents%s\n' "$B" "$R"
  local nmovies ntv
  nmovies="$(find "$MEDIA_DIR/Movies" -type f \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' \) 2>/dev/null | wc -l || echo 0)"
  ntv="$(find "$MEDIA_DIR/TV Shows" -type f \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' \) 2>/dev/null | wc -l || echo 0)"
  info "${nmovies:-0} movie file(s), ${ntv:-0} episode file(s)"
  local nstrm
  nstrm="$(find "$MEDIA_DIR" -type f -iname '*.strm' 2>/dev/null | wc -l || echo 0)"
  [ "${nstrm:-0}" -gt 0 ] && bad "$nstrm .strm pointer file(s) — these commonly cause s1001, see doctor" || true
  local npart
  npart="$(find "$MEDIA_DIR/staging" -type f 2>/dev/null | wc -l || echo 0)"
  [ "${npart:-0}" -gt 0 ] && warn "$npart unfinished file(s) in staging/" || true
  echo
}

# =============================================================================
#  doctor -- why won't it play?
# =============================================================================
do_doctor() {
  local title="${1:-}"
  hdr "Mwatcher doctor"
  [ -n "$title" ] && info "looking into: \"$title\""
  local problems=0

  # ---- 1. services & ports --------------------------------------------------
  hdr "1. Services"
  for s in plexmediaserver fastcombo mwatcher-bridge; do
    svc_active "$s" && ok "$s running" || { bad "$s NOT running"; problems=$((problems+1)); }
  done
  port_open 32400 && ok "Plex listening on 32400" || { bad "nothing on 32400"; problems=$((problems+1)); }

  # ---- 2. Plex itself answers ----------------------------------------------
  hdr "2. Plex server"
  if curl -s -m 8 http://127.0.0.1:32400/identity >/dev/null 2>&1; then
    ok "Plex answers on localhost"
  else
    bad "Plex does not answer on 127.0.0.1:32400"; problems=$((problems+1))
  fi

  if [ -r "$PLEX_PREFS" ] || sudo test -r "$PLEX_PREFS" 2>/dev/null; then
    local prefs; prefs="$(sudo cat "$PLEX_PREFS" 2>/dev/null || cat "$PLEX_PREFS" 2>/dev/null || true)"
    if [ -n "$prefs" ]; then
      local sec custom manport preroll
      sec="$(printf '%s' "$prefs"      | grep -o 'secureConnections="[0-9]*"'          | head -1 | grep -o '[0-9]*' || true)"
      custom="$(printf '%s' "$prefs"   | grep -o 'customConnections="[^"]*"'           | head -1 | sed 's/.*="//;s/"$//' || true)"
      manport="$(printf '%s' "$prefs"  | grep -o 'ManualPortMappingPort="[0-9]*"'      | head -1 | grep -o '[0-9]*' || true)"
      preroll="$(printf '%s' "$prefs"  | grep -oi '[A-Za-z]*preroll[A-Za-z]*="[^"]*"'  | head -1 || true)"

      case "$sec" in
        2) bad "Secure connections = REQUIRED. Behind a proxy/tunnel with a custom domain this
       breaks playback with s1001. Set it to 'Preferred' (Settings → Network)."; problems=$((problems+1));;
        1) ok "Secure connections = Preferred";;
        0) warn "Secure connections = Disabled (fine on LAN, remote apps may refuse)";;
        *) info "secureConnections not set (default Preferred)";;
      esac

      if [ -n "$custom" ]; then
        info "Custom server access URLs: $custom"
        case "$custom" in
          *127.0.0.1*|*localhost*)
            bad "A custom URL points at 127.0.0.1/localhost. A phone/TV outside the server
       cannot reach that — browsing works but playback fails with s1001.
       Use the LAN IP (e.g. http://192.168.0.34:32400) and/or your public hostname."
            problems=$((problems+1));;
        esac
        # first entry should be the LAN one so local clients do not hairpin
        case "$(printf '%s' "$custom" | cut -d, -f1)" in
          http://192.168.*|http://10.*|http://172.*) ok "LAN URL is first (good)";;
          *) warn "Put the LAN URL first so devices at home stay local: http://<server-ip>:32400,https://your-domain";;
        esac
      else
        info "No custom server access URLs set (normal if you use Plex Remote Access)"
      fi
      [ -n "$manport" ] && info "Manual public port: $manport (must match your router's external port)"
      if [ -n "$preroll" ]; then
        bad "Found a pre-roll/Extras setting: $preroll
       A dead Movie Pre-Roll URL is a classic cause of s1001 on EVERY title.
       Clear it: Settings → General → Extras → Movie pre-roll video."
        problems=$((problems+1))
      fi
    fi
  else
    warn "cannot read $PLEX_PREFS"
  fi

  # ---- 3. find the file ----------------------------------------------------
  hdr "3. The file itself (the #1 cause of s1001 with this setup)"
  local found=""
  if [ -n "$title" ]; then
    found="$(find "$MEDIA_DIR" -type f \( -iname "*${title}*" \) 2>/dev/null | head -5 || true)"
    [ -z "$found" ] && found="$(find / -xdev -type f -iname "*${title}*" \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' -o -iname '*.avi' \) 2>/dev/null | grep -v '/staging/' | head -5 || true)"
  fi
  if [ -z "$found" ]; then
    warn "no file matching \"$title\" under $MEDIA_DIR — Plex may be pointed at a different folder"
    info "recently added files:"
    find "$MEDIA_DIR" -type f \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' \) -printf '       %TY-%Tm-%Td %10s  %p\n' 2>/dev/null | sort -r | head -8 || true
  else
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      local size ext
      size="$(stat -c '%s' "$f" 2>/dev/null || echo 0)"
      ext="${f##*.}"
      printf '\n  %s%s%s  (%s bytes)\n' "$B" "$f" "$R" "$(numfmt --to=iec "$size" 2>/dev/null || echo "$size")"

      # .strm = a text pointer, the usual s1001 trap
      if [ "$ext" = "strm" ]; then
        local target; target="$(head -c 500 "$f" | tr -d '\r\n')"
        bad ".strm pointer file → $target"
        case "$target" in
          *127.0.0.1*|*localhost*|*192.168.*)
            bad "  It points at a private/localhost address. Your Plex CLIENT (phone/TV)
  cannot reach that, so playback fails with s1001 even though the item is listed.
  Fix: delete the .strm and let the bridge download the real file instead:
       rm \"$f\"
       curl -X POST http://127.0.0.1:$BRIDGE_PORT/fetch -H 'Content-Type: application/json' -d '{\"title\":\"$title\"}'"
            ;;
          *)
            warn "  Remote .strm: Plex support is patchy and remote/transcoded playback often
  fails with s1001. Prefer a real downloaded file."
            ;;
        esac
        problems=$((problems+1))
        continue
      fi

      # tiny file = failed/partial download
      if [ "$size" -lt 10000000 ]; then
        bad "only $(numfmt --to=iec "$size" 2>/dev/null || echo "$size")B — that is not a movie.
       Almost certainly a failed download (an HTML error page, a redirect, or a truncated file).
       Plex lists it because the FILENAME matched, but there is no video inside → s1001."
        problems=$((problems+1))
      fi

      # is it secretly a web page?
      if head -c 300 "$f" 2>/dev/null | grep -qiE '<!doctype html|<html|<\?xml|"error"|cloudflare'; then
        bad "This file starts with HTML/JSON, not video. The download saved a web page
       (login wall, captcha, 403/404, or a Cloudflare challenge) instead of the movie."
        problems=$((problems+1))
      fi

      # the definitive check
      if have ffprobe; then
        local vstreams astreams dur fmt
        vstreams="$(ffprobe -v error -select_streams v -show_entries stream=codec_name -of csv=p=0 "$f" 2>/dev/null | head -1 || true)"
        astreams="$(ffprobe -v error -select_streams a -show_entries stream=codec_name -of csv=p=0 "$f" 2>/dev/null | head -1 || true)"
        dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null || true)"
        fmt="$(ffprobe -v error -show_entries format=format_name -of csv=p=0 "$f" 2>/dev/null || true)"
        if [ -z "$vstreams" ] && [ -z "$astreams" ]; then
          bad "ffprobe: NO video stream and NO audio stream (format: ${fmt:-unknown}).
       This is exactly what makes Plex say s1001 — the library entry exists but there
       is nothing playable inside. Delete it and re-fetch:
            rm \"$f\"
            curl -X POST http://127.0.0.1:$BRIDGE_PORT/fetch -H 'Content-Type: application/json' -d '{\"title\":\"$title\"}'"
          problems=$((problems+1))
        else
          ok "ffprobe: video=${vstreams:-none} audio=${astreams:-none} format=${fmt:-?} duration=${dur%.*}s"
          [ -z "$astreams" ] && warn "no audio stream — plays silent or fails on some clients"
          if [ -n "${dur%.*}" ] && [ "${dur%.*}" -lt 60 ] 2>/dev/null; then
            warn "duration is only ${dur%.*}s — truncated download"
            problems=$((problems+1))
          fi
        fi
      else
        warn "ffprobe not installed — cannot verify the file is real video.
       Install it:  sudo apt install -y ffmpeg"
      fi

      # can the plex user read it?
      if [ "$(id -u)" != "0" ]; then
        warn "run doctor with sudo to verify the 'plex' user can read this file"
      elif id plex >/dev/null 2>&1; then
        if sudo -u plex test -r "$f" 2>/dev/null; then
          ok "the 'plex' user can read it"
        else
          bad "the 'plex' user CANNOT read this file → Plex lists it but cannot stream it (s1001).
       Fix:  sudo chmod -R a+rX \"$(dirname "$f")\"
             sudo usermod -aG \"$RUN_USER\" plex   # then: sudo systemctl restart plexmediaserver"
          problems=$((problems+1))
        fi
      else
        info "no 'plex' user on this machine (Plex not installed?)"
      fi
    done <<< "$found"
  fi

  # ---- 4. what Plex logged at the moment it failed -------------------------
  hdr "4. Plex's own log (the definitive answer)"
  if [ -f "$PLEX_LOG" ] || sudo test -f "$PLEX_LOG" 2>/dev/null; then
    local hits
    hits="$(sudo grep -iE "MDE:|s1001|no video stream|neither a video|Error opening|does not exist|Permission denied" "$PLEX_LOG" 2>/dev/null | tail -12 || true)"
    if [ -n "$hits" ]; then
      printf '%s\n' "$hits" | sed 's/^/    /'
      printf '\n'
      echo "$hits" | grep -qiE "neither a video|no video stream|MDE:" && {
        bad "Plex could not find a video stream → the FILE is the problem (see §3), not your network."
        problems=$((problems+1)); }
      echo "$hits" | grep -qi "permission denied" && {
        bad "Permission denied → the plex user cannot read the file (see §3)."
        problems=$((problems+1)); }
    else
      ok "no media-analysis errors in the current log"
      info "last 5 log lines:"
      sudo tail -5 "$PLEX_LOG" 2>/dev/null | sed 's/^/    /' || true
    fi
  else
    warn "cannot read $PLEX_LOG"
  fi

  # ---- 5. remote path (only matters away from home) ------------------------
  hdr "5. Remote playback path"
  local pub wan
  pub="$(curl -s -m 8 https://ifconfig.me 2>/dev/null || echo '')"
  if [ -n "$pub" ]; then
    info "public IP: $pub"
    case "$pub" in
      100.6[4-9].*|100.[7-9][0-9].*|100.1[01][0-9].*|100.12[0-7].*)
        bad "That is a CGNAT range (100.64.0.0/10). Port forwarding CANNOT work.
       Browsing may still work via Plex Relay, but media will fail or crawl.
       Use Tailscale or a Cloudflare Tunnel — see docs/PLEX_GLOBAL_ACCESS.md §5d."; problems=$((problems+1));;
      10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*)
        warn "public IP is a private address → double NAT"; problems=$((problems+1));;
      *) ok "looks like a real public IPv4";;
    esac
    wan="$(ip route get 1.1.1.1 2>/dev/null | grep -o 'src [0-9.]*' | awk '{print $2}' || true)"
    [ -n "$wan" ] && info "this box's LAN IP: $wan (must match your router's port-forward target)"
  else
    warn "could not determine the public IP (no internet from this box?)"
  fi
  if pgrep -x cloudflared >/dev/null 2>&1; then
    info "cloudflared is running — remember: WebSockets ON, caching/Rocket Loader OFF for the Plex
       hostname, Secure connections = Preferred, and the LAN URL first in Custom server access URLs."
  fi

  # ---- verdict -------------------------------------------------------------
  hdr "Verdict"
  if [ "$problems" -eq 0 ]; then
    ok "no obvious problem found on the server side."
    info "If it still fails on one device only, that device cannot reach the media URL:
       - test in a browser on the SAME device: http://<server-ip>:32400/web
       - Plex app → Settings → Advanced → 'Allow insecure connections' = Always
       - try another client; if only one fails, it is that client's network/DNS"
  else
    bad "$problems problem(s) found — fix the ✗ lines above, then:"
    info "sudo systemctl restart plexmediaserver mwatcher-bridge"
    info "then in Plex: Settings → Library → Scan Library Files, and re-test playback."
  fi
  echo
}

# =============================================================================
#  install
# =============================================================================
gen_key() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c "${1:-16}"; }

do_install() {
  need_root "install"
  hdr "Installing Mwatcher (idempotent — existing config is preserved)"
  info "user: $RUN_USER   home: $RUN_HOME"

  # ---- 0. repo -------------------------------------------------------------
  if [ -z "$REPO_DIR" ]; then
    warn "Mwatcher sources not found — cloning"
    as_user "git clone --depth 1 https://github.com/AfzalAshraf/Mwatcher.git '$RUN_HOME/Mwatcher'" \
      || die "could not clone Mwatcher. Run this script from inside the repo instead."
    REPO_DIR="$RUN_HOME/Mwatcher"
  fi
  ok "sources: $REPO_DIR"

  # ---- 1. packages ---------------------------------------------------------
  hdr "1. System packages"
  local need=()
  have curl    || need+=(curl)
  have git     || need+=(git)
  have ffprobe || need+=(ffmpeg)
  have python3 || need+=(python3)
  if [ ${#need[@]} -gt 0 ]; then
    info "installing: ${need[*]}"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}"
    ok "installed ${need[*]}"
  else
    ok "curl, git, ffmpeg, python3 already present"
  fi

  # node (Fast Combo needs 18+)
  if have node && [ "$(node -e 'console.log(process.versions.node.split(".")[0])')" -ge 18 ]; then
    ok "node $(node --version)"
  else
    info "installing Node 20 LTS"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs
    ok "node $(node --version)"
  fi

  # yt-dlp (best downloader; ffmpeg alone cannot do everything)
  if have yt-dlp; then
    ok "yt-dlp $(yt-dlp --version 2>/dev/null | head -1 || echo installed)"
  else
    info "installing yt-dlp"
    if have pipx; then as_user "pipx install yt-dlp" || true
    elif python3 -m pip --version >/dev/null 2>&1; then as_user "python3 -m pip install --user --break-system-packages -q yt-dlp" || true
    else DEBIAN_FRONTEND=noninteractive apt-get install -y -qq pipx && as_user "pipx install yt-dlp" || true; fi
    have yt-dlp && ok "yt-dlp installed" || warn "yt-dlp install failed — ffmpeg will be used instead"
  fi

  # ---- 2. Plex -------------------------------------------------------------
  hdr "2. Plex Media Server"
  if dpkg -l plexmediaserver 2>/dev/null | grep -q '^ii'; then
    ok "already installed ($(dpkg-query -W -f='${Version}' plexmediaserver 2>/dev/null | cut -d- -f1 || echo unknown))"
  else
    info "adding the official Plex repo"
    install -d -m 0755 /etc/apt/keyrings
    curl -L https://downloads.plex.tv/plex-keys/PlexSign.v2.key \
      | gpg --yes --dearmor -o /etc/apt/keyrings/plexmediaserver.v2.gpg
    echo "deb [signed-by=/etc/apt/keyrings/plexmediaserver.v2.gpg] https://repo.plex.tv/deb/ public main" \
      > /etc/apt/sources.list.d/plex.list
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq plexmediaserver
    ok "Plex installed"
  fi
  systemctl enable --now plexmediaserver >/dev/null 2>&1 || true
  svc_active plexmediaserver && ok "plexmediaserver running" || warn "plexmediaserver not running yet"
  # let the bridge read files inside the user's home
  if id plex >/dev/null 2>&1; then
    usermod -aG "$RUN_USER" plex 2>/dev/null || true
    ok "added 'plex' to the $RUN_USER group (so it can read $MEDIA_DIR)"
  fi

  # ---- 3. library folders --------------------------------------------------
  hdr "3. Library folders"
  as_user "mkdir -p '$MEDIA_DIR/Movies' '$MEDIA_DIR/TV Shows' '$MEDIA_DIR/staging'"
  chmod -R a+rX "$MEDIA_DIR" 2>/dev/null || true
  ok "$MEDIA_DIR/{Movies,TV Shows,staging}"
  info "staging must be on the SAME filesystem as the libraries (rename, not copy)"

  # ---- 4. Fast Combo -------------------------------------------------------
  hdr "4. Fast Combo (your Stremio addons)"
  if [ -d "$FC_DIR/.git" ]; then
    ok "already cloned: $FC_DIR  (update with: cd $FC_DIR && git pull)"
  else
    info "cloning AfzalAshraf/stremio-addons"
    as_user "git clone --depth 1 https://github.com/AfzalAshraf/stremio-addons.git '$FC_DIR'"
    ok "cloned to $FC_DIR"
  fi

  as_user "mkdir -p '$CONFIG_DIR' '$RUN_HOME/.local/share/fastcombo'"
  if [ -f "$CONFIG_DIR/fastcombo.env" ]; then
    ok "keeping your existing $CONFIG_DIR/fastcombo.env (access key unchanged)"
  else
    local k p
    k="$(gen_key 16)"; p="$(gen_key 12)"
    cat > "$CONFIG_DIR/fastcombo.env" <<EOF
FC_ACCESS_KEY=$k
FC_ADMIN_PASSWORD=$p
EOF
    chown "$RUN_USER:$RUN_USER" "$CONFIG_DIR/fastcombo.env"
    chmod 600 "$CONFIG_DIR/fastcombo.env"
    ok "created $CONFIG_DIR/fastcombo.env (mode 600)"
    printf '\n  %sWrite these down:%s\n' "$B$Y" "$R"
    printf '    access key:      %s%s%s\n' "$B" "$k" "$R"
    printf '    admin password:  %s%s%s\n' "$B" "$p" "$R"
  fi

  # ---- 5. bridge config ----------------------------------------------------
  hdr "5. Bridge config"
  local fckey
  fckey="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  if [ -f "$CONFIG_DIR/bridge.env" ]; then
    ok "keeping your existing $CONFIG_DIR/bridge.env"
    local bk; bk="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" | head -1 | cut -d= -f2- || true)"
    if [ "$bk" != "$fckey" ]; then
      warn "bridge.env key does not match fastcombo.env — fixing it"
      sed -i "s|^FASTCOMBO_ACCESS_KEY=.*|FASTCOMBO_ACCESS_KEY=$fckey|" "$CONFIG_DIR/bridge.env"
      ok "keys now match"
    fi
  else
    cat > "$CONFIG_DIR/bridge.env" <<EOF
FASTCOMBO_ACCESS_KEY=$fckey
EOF
    chown "$RUN_USER:$RUN_USER" "$CONFIG_DIR/bridge.env"
    chmod 600 "$CONFIG_DIR/bridge.env"
    ok "created $CONFIG_DIR/bridge.env (mode 600)"
  fi

  # ---- 6. systemd units ----------------------------------------------------
  hdr "6. Services"
  for unit in fastcombo mwatcher-bridge; do
    local src="$REPO_DIR/services/$unit.service" dst="/etc/systemd/system/$unit.service"
    [ -f "$src" ] || die "missing $src"
    # rewrite the paths/user for THIS machine instead of the documented example ones
    sed -e "s|/home/afine/Mwatcher|$REPO_DIR|g" \
        -e "s|/home/afine/stremio-addons|$FC_DIR|g" \
        -e "s|/home/afine/.config/mwatcher|$CONFIG_DIR|g" \
        -e "s|/home/afine/.local/share/fastcombo|$RUN_HOME/.local/share/fastcombo|g" \
        -e "s|/home/afine/media|$MEDIA_DIR|g" \
        -e "s|^User=afine|User=$RUN_USER|" \
        -e "s|^Group=afine|Group=$RUN_USER|" \
        -e "s|ExecStart=/usr/bin/node |ExecStart=$(command -v node) |" \
        -e "s|ExecStart=/usr/bin/python3 |ExecStart=$(command -v python3) |" \
        "$src" > "$dst"
    ok "wrote $dst"
  done
  systemctl daemon-reload
  systemctl enable --now fastcombo mwatcher-bridge >/dev/null 2>&1 || true
  sleep 2
  for s in fastcombo mwatcher-bridge; do
    svc_active "$s" && ok "$s running" || bad "$s failed to start → sudo journalctl -u $s -n 30 --no-pager"
  done

  # ---- 7. firewall ---------------------------------------------------------
  hdr "7. Firewall"
  if have ufw && ufw status 2>/dev/null | grep -qi active; then
    ufw allow from 192.168.0.0/16 to any >/dev/null 2>&1 || true
    ok "LAN allowed (Fast Combo and the bridge stay loopback-only on purpose)"
    info "Plex remote access: forward TCP 32400 on your router, or use Tailscale (§5d of the guide)"
  else
    info "ufw not active — nothing to do"
  fi

  do_status

  local fckey2
  fckey2="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  hdr "Next steps"
  cat <<EOF
  1. Add your addons to Fast Combo (each is live-tested before it is added):
       ${B}http://127.0.0.1:$FC_PORT/$fckey2/configure${R}
     password: $(grep -E '^FC_ADMIN_PASSWORD=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | cut -d= -f2- || echo "(see $CONFIG_DIR/fastcombo.env)")

  2. Claim Plex (first run only): ${B}http://127.0.0.1:32400/web${R}
     then add libraries for:  $MEDIA_DIR/Movies   and   $MEDIA_DIR/TV Shows

  3. Open the bridge dashboard and fetch something:
       ${B}http://127.0.0.1:$BRIDGE_PORT/${R}
     or from a shell:
       python3 $REPO_DIR/scripts/telestream_to_plex.py --title "Dune" --year 2021 --prefer fastest

  4. Remote access (phone/TV away from home): see
       $REPO_DIR/docs/PLEX_GLOBAL_ACCESS.md   §5

  Anything won't play?   ${B}sudo bash $REPO_DIR/install.sh doctor "title"${R}
EOF
}

do_uninstall() {
  need_root uninstall
  hdr "Removing Mwatcher services (your media and Plex libraries are kept)"
  for s in mwatcher-bridge fastcombo; do
    systemctl disable --now "$s" >/dev/null 2>&1 || true
    rm -f "/etc/systemd/system/$s.service"
    ok "removed $s"
  done
  systemctl daemon-reload
  info "kept: Plex, $MEDIA_DIR, $FC_DIR, $CONFIG_DIR"
  info "to remove those too: sudo apt remove plexmediaserver && rm -rf '$FC_DIR' '$CONFIG_DIR'"
}

# =============================================================================
usage() {
  cat <<EOF
Mwatcher installer

  sudo bash install.sh                    install / repair, then show status
  sudo bash install.sh status             report only, change nothing
  sudo bash install.sh doctor [title]     diagnose playback problems (s1001 etc.)
  sudo bash install.sh uninstall          remove the services (keeps media)

Safe to re-run: existing keys, passwords and addon lists are preserved.
EOF
}

case "${1:-install}" in
  install|"")  do_install ;;
  status)      do_status ;;
  doctor)      shift; do_doctor "${1:-}" ;;
  uninstall)   do_uninstall ;;
  -h|--help|help) usage ;;
  *)           usage; exit 1 ;;
esac
