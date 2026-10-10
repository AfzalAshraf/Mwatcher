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
set -Eeuo pipefail   # -E so the ERR trap below is inherited by functions

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

# pip --user and pipx install into ~/.local/bin, which sudo's secure_path does not include.
# Without this a perfectly good yt-dlp looks missing and the installer reports a failure
# that did not happen -- and systemd would not find it for the bridge either.
case ":$PATH:" in
  *":$RUN_HOME/.local/bin:"*) ;;
  *) PATH="$RUN_HOME/.local/bin:$PATH"; export PATH ;;
esac

AUTO_RC=0      # do_auto's real exit status, kept out of the ERR trap's way
AUTO_MODE=""   # set by do_auto: suppresses the manual "Next steps" it is about to do for you
FC_DIR="${FC_DIR:-$RUN_HOME/stremio-addons}"
CONFIG_DIR="$RUN_HOME/.config/mwatcher"
MEDIA_DIR="${MEDIA_DIR:-$RUN_HOME/media}"
PLEX_DATA="/var/lib/plexmediaserver/Library/Application Support/Plex Media Server"
PLEX_PREFS="$PLEX_DATA/Preferences.xml"
PLEX_LOG="$PLEX_DATA/Logs/Plex Media Server.log"

FC_PORT="${FC_PORT:-7000}"
BRIDGE_PORT="${BRIDGE_PORT:-8889}"

# Fast Combo does NOT have to run on this machine. The common split is: addons on a VPS,
# Plex + the library at home. Point the bridge at the remote one and this installer skips
# cloning Fast Combo and skips the local fastcombo.service:
#
#   sudo FC_BASE_URL=https://addons.example.com bash install.sh
#   sudo FC_BASE_URL=http://203.0.113.7:7000 FC_REMOTE_ACCESS_KEY=xxxx bash install.sh
#
# Reaching a VPS over the public internet exposes your addon key. The safer route is an
# SSH tunnel, which makes the remote look local -- the installer prints that recipe.
FC_BASE_URL="${FC_BASE_URL:-}"
# The key of a Fast Combo that is ALREADY installed here (see fc_detect_existing below).
# Only needed when the installer cannot find it on its own.
FC_ACCESS_KEY="${FC_ACCESS_KEY:-}"
if [ -z "$FC_BASE_URL" ] && [ -f "$RUN_HOME/.config/mwatcher/bridge.env" ]; then
  FC_BASE_URL="$(grep -E '^FASTCOMBO_BASE_URL=' "$RUN_HOME/.config/mwatcher/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
fi

fc_is_remote() {
  [ -n "$FC_BASE_URL" ] || return 1
  case "$FC_BASE_URL" in
    *//127.0.0.1*|*//localhost*|*//\[::1\]*) return 1 ;;
  esac
  return 0
}

fc_target() {
  if fc_is_remote; then printf '%s' "$FC_BASE_URL"; else printf 'http://127.0.0.1:%s' "$FC_PORT"; fi
}

# Fast Combo may ALREADY be installed on this machine. That is the normal case on the box
# where your addons have been running all along -- a VPS set up with stremio-addons' own
# installer, say. Reinstalling blindly would be actively destructive there:
#
#   * a second clone in ~/stremio-addons gets a freshly generated FC_ACCESS_KEY, and the
#     addon URL already saved in your Stremio app stops resolving;
#   * rewriting /etc/systemd/system/fastcombo.service repoints the running service at that
#     new clone and new key, so your working install is replaced by an unconfigured one.
#
# So find what is already here, adopt it, and only install our own when nothing is.
FC_UNIT=""            # systemd unit that already runs Fast Combo on this box
FC_ADOPTED=""         # non-empty once we are reusing an existing install
FC_EXISTING_KEY=""    # the access key that install already uses
FC_EXISTING_ADMIN=""  # and its admin password

fc_is_clone() {
  # Any plausible Fast Combo entry point. The repo has moved it before, and a stale or
  # partial clone may have no server.js at all -- requiring that one file is what made the
  # first version of this miss a live install and offer to re-clone over it.
  local d="$1"
  [ -n "$d" ] && [ -d "$d" ] || return 1
  [ -f "$d/server.js" ] || [ -f "$d/index.js" ] || [ -f "$d/app.js" ] \
    || [ -f "$d/src/server.js" ] || [ -f "$d/src/index.js" ] || return 1
  return 0
}

fc_show() {  # one systemctl property; empty when systemd cannot answer
  local u="$1" prop="$2"
  [ -n "$u" ] || return 1
  systemctl show "$u" -p "$prop" --value 2>/dev/null | head -1 || true
}

fc_find_unit() {
  local u fp
  # 1. the conventional names, confirmed through systemd itself -- cheap and reliable, and
  #    it finds a unit whatever directory or filename the original installer chose
  for u in fastcombo stremio-addons fastcombo-addons stremio-fastcombo; do
    fp="$(fc_show "$u" FragmentPath)"
    if [ -n "$fp" ] && [ -f "$fp" ]; then printf '%s' "$u"; return 0; fi
  done
  # 2. anything on disk that points at a stremio-addons / fastcombo tree
  for fp in /etc/systemd/system/*.service /etc/systemd/system/*.target.wants/*.service \
            /usr/lib/systemd/system/*.service /lib/systemd/system/*.service; do
    [ -f "$fp" ] || continue
    grep -qE '^(ExecStart|WorkingDirectory)=.*(stremio-addons|fastcombo)' "$fp" 2>/dev/null || continue
    basename "$fp" .service; return 0
  done
  return 1
}

fc_unit_dir() {
  local u="$1" d="" js=""
  [ -n "$u" ] || return 1
  d="$(fc_show "$u" WorkingDirectory)"; d="${d#-}"
  if [ -n "$d" ] && [ -d "$d" ]; then printf '%s' "$d"; return 0; fi
  js="$(fc_show "$u" ExecStart | grep -oE '/[^ ;]*\.js' | head -1 || true)"
  if [ -n "$js" ] && [ -f "$js" ]; then dirname "$js"; return 0; fi
  return 1
}

# Every file systemd loads for this unit (EnvironmentFiles=) plus the fragment itself,
# which carries any inline Environment= lines.
fc_unit_envfiles() {
  local u="$1" fp=""
  [ -n "$u" ] || return 1
  # Dedicated secret files first: systemd applies Environment= and then lets
  # EnvironmentFile= override it, so the file is the value actually in effect. An inline
  # Environment=FC_ACCESS_KEY= in the fragment is the stale one more often than not.
  fc_show "$u" EnvironmentFiles | grep -oE '/[^ (]+' || true
  fp="$(fc_show "$u" FragmentPath)"
  [ -n "$fp" ] && printf '%s\n' "$fp"
  return 0
}

# VAR=value out of an env file or a unit fragment. Empty (and exit 0) when absent.
fc_var_from() {
  local f="$1" v="$2"
  [ -n "$f" ] && [ -r "$f" ] || return 1   # -r, not -f: callers pass process substitutions
  grep -E "^[[:space:]]*(Environment=)?(export[[:space:]]+)?$v=" "$f" 2>/dev/null | tail -1 \
    | sed -E "s/^[[:space:]]*(Environment=)?(export[[:space:]]+)?$v=//" \
    | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/' || true
}

# Play-through (action=strm) writes the bridge's own address into every .strm, and Plex
# clients on OTHER machines have to reach it. The loopback bind in the unit is right for
# downloading, but with play-through on it produces a particularly confusing failure: the
# title plays on the server itself and gives s1001 on every phone and TV.
pt_enabled() {
  local f="$CONFIG_DIR/bridge.env" act="" pub=""
  [ -f "$f" ] || return 1
  act="$(fc_var_from "$f" TELESTREAM_ACTION 2>/dev/null || true)"
  [ "$act" = "strm" ] && return 0
  pub="$(fc_var_from "$f" TELESTREAM_PUBLIC_BASE_URL 2>/dev/null || true)"
  case "$pub" in
    ""|*127.0.0.1*|*localhost*|*0.0.0.0*) return 1 ;;
    *) return 0 ;;
  esac
}

# Is the bridge listening beyond loopback? bridge.env wins over the unit, because
# EnvironmentFile= comes after Environment= in mwatcher-bridge.service.
bridge_lan_bound() {
  local h=""
  h="$(fc_var_from "$CONFIG_DIR/bridge.env" BRIDGE_HOST 2>/dev/null || true)"
  if [ -z "$h" ]; then
    h="$(sed -n 's/^Environment=BRIDGE_HOST=//p' /etc/systemd/system/mwatcher-bridge.service 2>/dev/null | head -1 || true)"
  fi
  case "$h" in ""|127.0.0.1|localhost) return 1 ;; esac
  return 0
}

lan_ip() { ip route get 1.1.1.1 2>/dev/null | grep -o 'src [0-9.]*' | awk '{print $2}' | head -1 || true; }

# What the RUNNING process is bound to, as opposed to what the config file says. These
# disagree whenever bridge.env was edited without a restart, and the config-reading check
# alone then reports a healthy setup that no client can reach.
bridge_bind_reality() {
  local port="${1:-$BRIDGE_PORT}" addrs=""
  if have ss; then
    addrs="$(ss -ltnH 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $4}')"
  elif have netstat; then
    addrs="$(netstat -ltn 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $4}')"
  fi
  [ -n "$addrs" ] || return 1
  # Report EVERY listener on that port, not the first one. A port can have several lines,
  # and `exit` on the first match is how a loopback-only bridge gets declared reachable.
  printf '%s' "$addrs" | tr '\n' ',' | sed 's/,$//'
  # Reachable from the LAN iff at least one listener is a wildcard or a non-loopback address.
  printf '%s\n' "$addrs" | grep -qvE '^(127\.|\[::1\]:)' && return 0
  return 1
}

# Set VAR in bridge.env -- replace the line (even a commented one) or append it.
bridge_env_set() {
  local v="$1" val="$2" f="$CONFIG_DIR/bridge.env"
  [ -f "$f" ] || return 1
  if grep -qE "^[[:space:]]*#?[[:space:]]*$v=" "$f" 2>/dev/null; then
    sed -i -E "s|^[[:space:]]*#?[[:space:]]*$v=.*|$v=$val|" "$f"
  else
    printf '%s=%s\n' "$v" "$val" >> "$f"
  fi
  return 0
}

fc_detect_existing() {
  FC_ADOPTED=""; FC_UNIT=""; FC_EXISTING_KEY=""; FC_EXISTING_ADMIN=""
  # Addons served from another machine: nothing local to adopt, and probing this box's
  # units would only produce a misleading "already installed".
  fc_is_remote && return 0

  local d f k
  FC_UNIT="$(fc_find_unit || true)"
  if [ -n "$FC_UNIT" ]; then
    d="$(fc_unit_dir "$FC_UNIT" || true)"
    if [ -n "$d" ] && [ -d "$d" ]; then FC_DIR="$d"; fi
  fi

  # no unit (or it points nowhere readable): look for a clone in the obvious places
  if ! fc_is_clone "$FC_DIR"; then
    for d in "$RUN_HOME/stremio-addons" "$RUN_HOME/fastcombo" "$RUN_HOME/stremio-fastcombo" \
             /opt/stremio-addons /opt/fastcombo /srv/stremio-addons; do
      if fc_is_clone "$d"; then FC_DIR="$d"; break; fi
    done
  fi

  # credentials, most authoritative first
  for f in "$CONFIG_DIR/fastcombo.env" "$FC_DIR/.env" "$FC_DIR/config.env" \
           "$RUN_HOME/.config/fastcombo.env" "$RUN_HOME/.config/fastcombo/fastcombo.env" \
           "$RUN_HOME/.config/stremio-addons/env"; do
    if [ -z "$FC_EXISTING_KEY" ]; then
      k="$(fc_var_from "$f" FC_ACCESS_KEY 2>/dev/null || true)"
      [ -z "$k" ] && k="$(fc_var_from "$f" FASTCOMBO_ACCESS_KEY 2>/dev/null || true)"
      [ -n "$k" ] && FC_EXISTING_KEY="$k"
    fi
    if [ -z "$FC_EXISTING_ADMIN" ]; then
      k="$(fc_var_from "$f" FC_ADMIN_PASSWORD 2>/dev/null || true)"
      [ -n "$k" ] && FC_EXISTING_ADMIN="$k"
    fi
  done

  # then whatever the running service itself was started with
  if [ -n "$FC_UNIT" ]; then
    [ -z "$FC_EXISTING_KEY" ]   && FC_EXISTING_KEY="$(fc_var_from <(fc_show "$FC_UNIT" Environment | tr ' ' '\n') FC_ACCESS_KEY 2>/dev/null || true)"
    [ -z "$FC_EXISTING_ADMIN" ] && FC_EXISTING_ADMIN="$(fc_var_from <(fc_show "$FC_UNIT" Environment | tr ' ' '\n') FC_ADMIN_PASSWORD 2>/dev/null || true)"
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      if [ -z "$FC_EXISTING_KEY" ]; then
        k="$(fc_var_from "$f" FC_ACCESS_KEY 2>/dev/null || true)"
        [ -z "$k" ] && k="$(fc_var_from "$f" FASTCOMBO_ACCESS_KEY 2>/dev/null || true)"
        [ -n "$k" ] && FC_EXISTING_KEY="$k"
      fi
      if [ -z "$FC_EXISTING_ADMIN" ]; then
        k="$(fc_var_from "$f" FC_ADMIN_PASSWORD 2>/dev/null || true)"
        [ -n "$k" ] && FC_EXISTING_ADMIN="$k"
      fi
    done < <(fc_unit_envfiles "$FC_UNIT" 2>/dev/null || true)
  fi

  if [ -n "$FC_UNIT" ] || fc_is_clone "$FC_DIR"; then FC_ADOPTED="yes"; fi
  return 0
}

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

# set -e exits SILENTLY. That cost a real install: it stopped dead after "4. Fast Combo"
# with no message at all, leaving Plex configured but no bridge, no keys and no unit, and
# nothing on screen to say why. If a command fails, say which one and where.
trap 'printf "\n%sERROR:%s install.sh:%s failed (exit %s)\n  command: %s\n  the install is INCOMPLETE -- fix the above and re-run it; it picks up where it left off\n" "$B$E" "$R" "$LINENO" "$?" "$BASH_COMMAND" >&2' ERR

need_root() {
  [ "$(id -u)" = "0" ] || die "this needs sudo:  sudo bash install.sh $1"
}
as_user() { sudo -u "$RUN_USER" -H bash -c "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3>&- 3<&-; return 0; } || return 1; }
svc_active() { systemctl is-active --quiet "$1" 2>/dev/null; }

fc_detect_existing

# =============================================================================
#  status
# =============================================================================
do_status() {
  hdr "Mwatcher status  (user: $RUN_USER)"

  printf '\n%sServices%s\n' "$B" "$R"
  local svc_list="plexmediaserver ${FC_UNIT:-fastcombo} mwatcher-bridge"
  fc_is_remote && svc_list="plexmediaserver mwatcher-bridge"
  for s in $svc_list; do
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
  if fc_is_remote; then
    info "Fast Combo is remote: $FC_BASE_URL (not a local port)"
  else
    port_open "$FC_PORT"    && ok "$FC_PORT  Fast Combo (your addons)"  || bad "$FC_PORT  Fast Combo is not listening"
  fi
  port_open "$BRIDGE_PORT" && ok "$BRIDGE_PORT  Mwatcher bridge + dashboard" || bad "$BRIDGE_PORT  bridge is not listening"

  printf '\n%sPaths%s\n' "$B" "$R"
  [ -n "$REPO_DIR" ] && ok "repo:      $REPO_DIR" || warn "repo:      not found"
  [ -d "$FC_DIR" ]   && ok "Fast Combo: $FC_DIR"  || warn "Fast Combo: $FC_DIR missing"
  [ -n "$FC_ADOPTED" ] && info "             pre-existing install, adopted — unit ${FC_UNIT:-not found}, left as it is"
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
  local key="" fcbase
  fcbase="$(fc_target)"
  if [ -f "$CONFIG_DIR/bridge.env" ]; then
    key="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  fi
  if [ -z "$key" ] && [ -f "$CONFIG_DIR/fastcombo.env" ]; then
    key="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  fi
  if [ -n "$key" ]; then
    ok "Fast Combo access key set (${#key} chars)"
    info "addon source:   $fcbase"
    info "control panel:  $fcbase/$key/configure"
    info "dashboard:      http://127.0.0.1:$BRIDGE_PORT/"
    local n
    # `grep | wc -l || echo 0` prints TWO zeros when grep matches nothing: wc emits its own
    # 0, then pipefail makes the pipeline fail and the `|| echo 0` adds a second line.
    n="$(curl -s -m 10 "$fcbase/$key/manifest.json" 2>/dev/null | { grep -o '"Addon [0-9]*"' || true; } | wc -l)"
    if curl -s -m 10 "$fcbase/$key/manifest.json" 2>/dev/null | grep -q '"id"'; then
      ok "Fast Combo answers with that key"
      info "addons merged into the manifest description: ${n:-0}"
    else
      bad "Fast Combo at $fcbase did not answer with that key
       (unreachable, wrong key, or it needs https from this network)"
    fi
  elif [ -n "$FC_EXISTING_KEY" ]; then
    # The key exists, just not in a file we own yet -- installing would reuse it.
    warn "no access key in $CONFIG_DIR/bridge.env or $CONFIG_DIR/fastcombo.env"
    ok "but the Fast Combo already installed here uses one (${#FC_EXISTING_KEY} chars)"
    info "'sudo bash install.sh' reuses that key instead of generating a new one"
  else
    bad "no access key in $CONFIG_DIR/bridge.env or $CONFIG_DIR/fastcombo.env"
  fi

  local bkey=""
  [ -f "$CONFIG_DIR/bridge.env" ] && bkey="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" | head -1 | cut -d= -f2- || true)"
  if [ -n "$bkey" ] && [ -n "$key" ]; then
    [ "$bkey" = "$key" ] && ok "bridge uses the same access key" \
                         || bad "MISMATCH: bridge.env key ≠ fastcombo.env key — lookups will 404"
  fi

  printf '\n%sSeerr  (request a title -> your server downloads it)%s\n' "$B" "$R"
  local surl="" skey=""
  if [ -f "$CONFIG_DIR/bridge.env" ]; then
    surl="$(grep -E '^SEERR_URL=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    skey="$(grep -E '^SEERR_API_KEY=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  fi
  if [ -z "$surl" ]; then
    info "not configured (optional) — 'sudo bash install.sh seerr' sets up Seerr + Radarr/Sonarr"
    info "                                  + Prowlarr + qBittorrent, so requests download locally"
  else
    local sport="5055"
    case "$surl" in *:*) sport="${surl##*:}"; sport="${sport%%/*}" ;; esac
    [[ "$sport" =~ ^[0-9]+$ ]] || sport="5055"
    ok "SEERR_URL=$surl"
    if [ -n "$skey" ]; then ok "SEERR_API_KEY set (${#skey} chars)"
    else bad "SEERR_API_KEY is empty — copy it from Seerr -> Settings -> General"; fi
    if port_open "$sport"; then
      ok "Seerr is listening on port $sport"
      if [ -n "$skey" ]; then
        curl -s -m 8 -H "X-Api-Key: $skey" "$surl/api/v1/settings/about" 2>/dev/null | grep -q '"version"' \
          && ok "Seerr accepts that API key" \
          || bad "Seerr rejected the API key — Settings -> General -> API Key"
      fi
    else
      bad "nothing listening on port $sport"
      info "cd \$HOME/mwatcher-seerr && docker compose up -d   (or: sudo bash install.sh seerr)"
    fi
    if have docker; then
      local up
      up="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E '^(seerr|radarr|sonarr|prowlarr|qbittorrent)$' | sort | tr '\n' ' ' || true)"
      if [ -n "${up// /}" ]; then
        ok "stack containers running: ${up% }"
        local missing
        for d in seerr radarr sonarr prowlarr qbittorrent; do
          echo "$up" | grep -qw "$d" || missing="$missing $d"
        done
        [ -n "${missing:-}" ] && warn "not running:$missing" || true
      else
        warn "no Seerr-stack containers are running"
      fi
    fi
  fi

  printf '\n%sLibrary contents%s\n' "$B" "$R"
  local nmovies ntv
  nmovies="$(find "$MEDIA_DIR/Movies" -type f \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' \) 2>/dev/null | wc -l || echo 0)"
  ntv="$(find "$MEDIA_DIR/TV Shows" -type f \( -iname '*.mkv' -o -iname '*.mp4' -o -iname '*.strm' \) 2>/dev/null | wc -l || echo 0)"
  info "${nmovies:-0} movie file(s), ${ntv:-0} episode file(s)"
  local nstrm
  nstrm="$(find "$MEDIA_DIR" -type f -iname '*.strm' 2>/dev/null | wc -l || echo 0)"
  if [ "${nstrm:-0}" -gt 0 ]; then
    info "$nstrm .strm pointer file(s) — play-through mode: the bridge scrapes a fresh link"
    info "                                    and streams it, so nothing is downloaded"
    info "                                    (doctor checks each one is client-reachable)"
  fi
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
  local svc_list="plexmediaserver ${FC_UNIT:-fastcombo} mwatcher-bridge"
  fc_is_remote && svc_list="plexmediaserver mwatcher-bridge"
  for s in $svc_list; do
    svc_active "$s" && ok "$s running" || { bad "$s NOT running"; problems=$((problems+1)); }
  done
  if fc_is_remote; then
    info "Fast Combo runs elsewhere: $FC_BASE_URL"
    if curl -s -m 10 -o /dev/null "$FC_BASE_URL" 2>/dev/null; then
      ok "this machine can reach it"
    else
      bad "this machine CANNOT reach $FC_BASE_URL → every lookup fails.
       Fix: check the VPS firewall, or tunnel it so it looks local:
            ssh -N -L $FC_PORT:127.0.0.1:$FC_PORT <user>@<vps>   (then FC_BASE_URL=http://127.0.0.1:$FC_PORT)"
      problems=$((problems+1))
    fi
  fi
  port_open 32400 && ok "Plex listening on 32400" || { bad "nothing on 32400"; problems=$((problems+1)); }

  # Play-through readiness. Worth checking before any .strm exists, because the failure
  # mode is bizarre: the title plays on the server and nowhere else.
  if pt_enabled; then
    local pt_pub
    pt_pub="$(fc_var_from "$CONFIG_DIR/bridge.env" TELESTREAM_PUBLIC_BASE_URL 2>/dev/null || true)"
    local real=""
    real="$(bridge_bind_reality "$BRIDGE_PORT" 2>/dev/null || true)"
    if [ -n "$real" ] && ! bridge_bind_reality "$BRIDGE_PORT" >/dev/null 2>&1 \
       && bridge_lan_bound; then
      # The config and the live socket disagree -- bridge.env was edited but the service was
      # never restarted. Reporting the config alone says "healthy" while every client fails.
      bad "play-through: bridge.env says BRIDGE_HOST beyond loopback, but the RUNNING bridge
       is bound to ${real}. Clients cannot reach it, so every .strm title gives s1001 and
       Plex's log says 'video has neither a video stream nor an audio stream'.
       Fix:  sudo systemctl restart mwatcher-bridge"
      problems=$((problems+1))
    elif bridge_lan_bound; then
      if [ -n "$real" ]; then
        ok "play-through: the RUNNING bridge is bound to ${real}, so clients can reach it"
      else
        ok "play-through: the bridge is configured to listen beyond loopback"
        info "could not read the live socket (no ss/netstat), so that is the config, not proof"
      fi
    else
      bad "play-through is enabled but the bridge only listens on 127.0.0.1: every .strm plays
       on THIS box and fails with s1001 on every other client.
       Fix: echo 'BRIDGE_HOST=0.0.0.0' | sudo tee -a $CONFIG_DIR/bridge.env
            sudo systemctl restart mwatcher-bridge"
      problems=$((problems+1))
    fi
    case "$pt_pub" in
      "")   warn "play-through: TELESTREAM_PUBLIC_BASE_URL is unset, so .strm files get this box's
       LAN address — fine at home, s1001 away from it";;
      *127.0.0.1*|*localhost*|*0.0.0.0*)
          bad "play-through: TELESTREAM_PUBLIC_BASE_URL=$pt_pub is loopback, so only this machine
       can play .strm titles. Set it to the address your clients use for this box."
          problems=$((problems+1));;
      *)    ok "play-through: TELESTREAM_PUBLIC_BASE_URL=$pt_pub";;
    esac
  fi

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

      # .strm = a text pointer. This is a SUPPORTED mode (play-through: the bridge scrapes
      # a fresh link at play time and streams it, so nothing is downloaded). It only goes
      # wrong when the CLIENT cannot reach the URL inside -- which is what s1001 means.
      if [ "$ext" = "strm" ]; then
        local target; target="$(head -c 500 "$f" | tr -d '\r\n')"
        info ".strm pointer → $target"
        if printf '%s' "$target" | grep -q ":$BRIDGE_PORT/play/"; then
          # ---- our own play-through pointer -------------------------------------
          case "$target" in
            *127.0.0.1*|*localhost*|*0.0.0.0*)
              bad "  It points at loopback, so only THIS machine can play it; every other
  Plex client fails with s1001.
  Fix: tell the bridge the address your clients use, then re-add the title:
       echo 'TELESTREAM_PUBLIC_BASE_URL=http://<lan-ip-or-tunnel-host>:$BRIDGE_PORT' \\
         | sudo tee -a /etc/systemd/system/mwatcher-bridge.service.d/override.conf
       sudo systemctl daemon-reload && sudo systemctl restart mwatcher-bridge"
              problems=$((problems+1))
              ;;
            *)
              bad "  this is a .strm pointer, and PLEX CANNOT PLAY .strm FILES.
       Plex dropped .strm support years ago. Depending on version the scanner either
       ignores the file (your library shows as EMPTY) or indexes it and then fails to
       play it with s1001, because a 46-byte text file is not a video. Emby, Jellyfin
       and Kodi do support .strm; Plex does not. This is not a misconfiguration -- no
       firewall, bind address or permission change can make Plex play one.
       Fix: add the title as a real download instead:
         curl -X POST localhost:$BRIDGE_PORT/add -H 'Content-Type: application/json' \\
           -d '{"title":"TITLE","year":YYYY,"action":"stream"}'
       and make that the default:
         sudo sed -i 's/^TELESTREAM_ACTION=.*/TELESTREAM_ACTION=stream/' $CONFIG_DIR/bridge.env
         sudo systemctl restart mwatcher-bridge"
              problems=$((problems+1))
              local tpath code code2
              tpath="$(printf '%s' "$target" | sed -E 's#^[a-zA-Z]+://[^/]+##')"
              # Probe with HEAD, never GET. A GET on /play/<key> makes the bridge scrape a
              # fresh link first, which routinely takes 10-20s (Dune measured 14s), so an 8s
              # timeout reported "the bridge does not answer that URL at all" on a perfectly
              # healthy setup that was listening on 0.0.0.0:8889. HEAD answers straight from
              # the play table without touching the network, so it tests exactly what this
              # section is about: can a client reach this address, and is the key known.
              #   200 = reachable and the key is live
              #   404 = reachable but the pointer is orphaned
              #   000 = nothing answered; the connection never happened
              code="$(curl -s -m 10 -o /dev/null -w '%{http_code}' -I "$target" 2>/dev/null || true)"
              code2="$(curl -s -m 10 -o /dev/null -w '%{http_code}' -I "http://127.0.0.1:$BRIDGE_PORT$tpath" 2>/dev/null || true)"
              [ -n "$code" ] || code="000"
              [ -n "$code2" ] || code2="000"
              if [ "$code" = "000" ] && [ "$code2" != "000" ]; then
                warn "  the bridge answers locally (HTTP $code2) but NOT at that address — clients
  on other machines get s1001. Check the firewall and the IP:
       sudo ufw allow from 192.168.0.0/16 to any port $BRIDGE_PORT"
                problems=$((problems+1))
              elif [ "$code" = "000" ]; then
                bad "  nothing answers that URL (neither address) — s1001.
  Fix: sudo systemctl restart mwatcher-bridge, then re-test playback"
                problems=$((problems+1))
              elif [ "$code" = "404" ]; then
                bad "  the bridge is reachable but does not know that play key, so the pointer is
  orphaned. Fix: python3 $REPO_DIR/scripts/telestream_to_plex.py --repoint
       then:      sudo systemctl restart mwatcher-bridge"
                problems=$((problems+1))
              elif [ "${code#2}" != "$code" ]; then
                ok "  the bridge answers that URL (HTTP $code) and knows that play key"
                info "  that proves reachability only — a real play also needs the scrape to
  succeed, which takes 10-20s. To watch one happen:
       curl -s -m 60 -r 0-1000 -o /dev/null -w '%{http_code} %{size_download}b' \"$target\""
              else
                bad "  the bridge answered that URL with HTTP $code, which is neither healthy
  nor a missing key. Check what it said:
       sudo journalctl -u mwatcher-bridge -n 40 --no-pager"
                problems=$((problems+1))
              fi
              case "$target" in
                *192.168.*|*10.*|*172.1[6-9].*|*172.2[0-9].*|*172.3[01].*)
                  info "  LAN address: fine at home. Away from home set
  TELESTREAM_PUBLIC_BASE_URL to your tunnel/Tailscale URL, or clients get s1001."
                  ;;
              esac
              ;;
          esac
        elif printf '%s' "$target" | grep -qE "127\.0\.0\.1|localhost"; then
          bad "  Points at loopback and is NOT this bridge → your Plex client cannot reach it.
  Fix: rm \"$f\"   then let the bridge serve it:
       curl -X POST http://127.0.0.1:$BRIDGE_PORT/add -H 'Content-Type: application/json' \\
            -d '{\"title\":\"$title\"}'"
          problems=$((problems+1))
        else
          warn "  A direct link to someone else's host. Those expire (often within minutes),
  cannot carry the headers some hosts demand, and Plex's .strm support is patchy —
  that combination is a classic intermittent s1001.
  Better: let the bridge scrape a fresh link at play time and stream it through:
       rm \"$f\"
       curl -X POST http://127.0.0.1:$BRIDGE_PORT/add -H 'Content-Type: application/json' \\
            -d '{\"title\":\"$title\"}'"
          problems=$((problems+1))
        fi
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

  # ---- 6. Seerr request path (only when it is configured) ------------------
  local surl="" skey=""
  if [ -f "$CONFIG_DIR/bridge.env" ]; then
    surl="$(grep -E '^SEERR_URL=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    skey="$(grep -E '^SEERR_API_KEY=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  fi
  if [ -n "$surl" ]; then
    hdr "6. Seerr (request a title -> your server downloads it)"
    if [ -n "$REPO_DIR" ] && [ -f "$REPO_DIR/scripts/seerr_source.py" ] && have python3; then
      local n=0
      SEERR_URL="$surl" SEERR_API_KEY="$skey" \
        python3 "$REPO_DIR/scripts/seerr_source.py" --doctor --no-summary || n=$?
      problems=$((problems + n))
    else
      warn "cannot run the Seerr check (need python3 and the Mwatcher repo)"
      port_open "$(printf '%s' "$surl" | sed -E 's#.*:([0-9]+).*#\1#')" \
        && ok "Seerr answers on that port" || bad "Seerr is not listening on that port"
      problems=$((problems + 1))
    fi
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
gen_key() {
  # head -c closing an endless `tr </dev/urandom` sends SIGPIPE, pipefail turns that into a
  # failed pipeline, and set -e then kills the installer mid-run with NO message at all --
  # which is exactly what happened on a real box: it stopped after "4. Fast Combo". Read a
  # bounded chunk instead, so nothing is ever interrupted.
  local n="${1:-16}" out=""
  while [ "${#out}" -lt "$n" ]; do
    out="$out$(head -c 512 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9')"
  done
  printf '%s' "${out:0:n}"
}

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
  if fc_is_remote; then
    ok "using a REMOTE Fast Combo: $FC_BASE_URL"
    info "skipping the clone and the local fastcombo.service — your addons stay on that box"
    if printf '%s' "$FC_BASE_URL" | grep -q '^http://'; then
      warn "that is plain http over a non-loopback network: your access key travels in the
       clear. Use https, or tunnel it:  ssh -N -L $FC_PORT:127.0.0.1:$FC_PORT <user>@<vps>"
    fi
    if [ -z "${FC_REMOTE_ACCESS_KEY:-}" ]; then
      warn "FC_REMOTE_ACCESS_KEY was not given, so the bridge has no key to use yet.
       Add the secret part of your addon link to $CONFIG_DIR/bridge.env:
            FASTCOMBO_ACCESS_KEY=<the key from your VPS Fast Combo>"
    fi
  elif [ -n "$FC_ADOPTED" ]; then
    ok "Fast Combo is ALREADY installed here — adopting it, not reinstalling"
    [ -n "$FC_UNIT" ] && info "running as:  $FC_UNIT  (left exactly as it is)"
    info "directory:   $FC_DIR"
    if [ -n "$FC_EXISTING_KEY" ]; then
      info "access key:  reused (${#FC_EXISTING_KEY} chars) — your Stremio addon URL keeps working"
    else
      warn "could not find the access key that install uses, so the bridge has none yet.
       It is the secret part of your addon link (between the domain and /manifest.json):
            sudo FC_ACCESS_KEY=<key> bash install.sh"
    fi
    if port_open "$FC_PORT"; then
      ok "answering on 127.0.0.1:$FC_PORT right now"
    else
      warn "nothing is listening on $FC_PORT yet — start it with:
            sudo systemctl start ${FC_UNIT:-fastcombo}"
    fi
  elif [ -d "$FC_DIR/.git" ]; then
    ok "already cloned: $FC_DIR  (update with: cd $FC_DIR && git pull)"
  else
    info "cloning AfzalAshraf/stremio-addons"
    as_user "git clone --depth 1 https://github.com/AfzalAshraf/stremio-addons.git '$FC_DIR'"
    ok "cloned to $FC_DIR"
  fi

  as_user "mkdir -p '$CONFIG_DIR' '$RUN_HOME/.local/share/fastcombo'"
  local reuse=""
  [ -n "$FC_ACCESS_KEY" ] && reuse="$FC_ACCESS_KEY"
  [ -z "$reuse" ] && [ -n "$FC_EXISTING_KEY" ] && reuse="$FC_EXISTING_KEY"

  if [ -f "$CONFIG_DIR/fastcombo.env" ]; then
    ok "keeping your existing $CONFIG_DIR/fastcombo.env (access key unchanged)"
  elif [ -n "$reuse" ]; then
    # An install already answers with this key. Generating a fresh one here would leave the
    # bridge holding a key Fast Combo has never heard of -- every lookup 404s.
    local p="$FC_EXISTING_ADMIN"
    [ -n "$p" ] || p="$(gen_key 12)"
    cat > "$CONFIG_DIR/fastcombo.env" <<EOF
FC_ACCESS_KEY=$reuse
FC_ADMIN_PASSWORD=$p
EOF
    chown "$RUN_USER:$RUN_USER" "$CONFIG_DIR/fastcombo.env"
    chmod 600 "$CONFIG_DIR/fastcombo.env"
    ok "created $CONFIG_DIR/fastcombo.env reusing the key this install already uses (mode 600)"
    [ -n "$FC_ADOPTED" ] && info "your existing Fast Combo and its addon list are untouched"
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
  if fc_is_remote; then
    fckey="${FC_REMOTE_ACCESS_KEY:-}"
    if [ -z "$fckey" ] && [ -f "$CONFIG_DIR/bridge.env" ]; then
      fckey="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    fi
  else
    fckey="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    # Adopting an install whose key lives somewhere we do not write to.
    [ -z "$fckey" ] && fckey="${FC_ACCESS_KEY:-$FC_EXISTING_KEY}"
  fi
  if [ -f "$CONFIG_DIR/bridge.env" ]; then
    ok "keeping your existing $CONFIG_DIR/bridge.env"
    local bk; bk="$(grep -E '^FASTCOMBO_ACCESS_KEY=' "$CONFIG_DIR/bridge.env" | head -1 | cut -d= -f2- || true)"
    if [ -z "$bk" ]; then
      # A hand-made or half-finished file has no key line at all, and `sed s|^KEY=.*|...|`
      # matches nothing -- so it would change nothing and then report "keys now match".
      if [ -n "$fckey" ]; then
        printf 'FASTCOMBO_ACCESS_KEY=%s\n' "$fckey" >> "$CONFIG_DIR/bridge.env"
        ok "added the missing FASTCOMBO_ACCESS_KEY"
      else
        warn "bridge.env has no FASTCOMBO_ACCESS_KEY and none could be determined"
      fi
    elif [ -n "$fckey" ] && [ "$bk" != "$fckey" ]; then
      warn "bridge.env key does not match the one Fast Combo actually uses — fixing it"
      sed -i "s|^FASTCOMBO_ACCESS_KEY=.*|FASTCOMBO_ACCESS_KEY=$fckey|" "$CONFIG_DIR/bridge.env"
      ok "keys now match"
    fi
    local bm; bm="$(stat -c '%a' "$CONFIG_DIR/bridge.env" 2>/dev/null || echo '')"
    if [ -n "$bm" ] && [ "$bm" != "600" ]; then
      chmod 600 "$CONFIG_DIR/bridge.env"
      chown "$RUN_USER:$RUN_USER" "$CONFIG_DIR/bridge.env" 2>/dev/null || true
      ok "tightened bridge.env from mode $bm to 600 — it holds your access key"
    fi
  else
    {
      echo "FASTCOMBO_ACCESS_KEY=$fckey"
      fc_is_remote && echo "FASTCOMBO_BASE_URL=$FC_BASE_URL"
    } > "$CONFIG_DIR/bridge.env"
    chown "$RUN_USER:$RUN_USER" "$CONFIG_DIR/bridge.env"
    chmod 600 "$CONFIG_DIR/bridge.env"
    ok "created $CONFIG_DIR/bridge.env (mode 600)"
  fi
  if fc_is_remote && ! grep -q "^FASTCOMBO_BASE_URL=" "$CONFIG_DIR/bridge.env" 2>/dev/null; then
    echo "FASTCOMBO_BASE_URL=$FC_BASE_URL" >> "$CONFIG_DIR/bridge.env"
    ok "recorded the remote addon URL in bridge.env"
  fi

  # ---- 5b. play-through must be reachable from clients, not just from here ---
  if pt_enabled; then
    # This has to be said out loud, before anyone builds a library of pointers that cannot
    # play. Plex dropped .strm support years ago: depending on version the scanner either
    # ignores the file, so the library shows as EMPTY, or indexes it and then fails with
    # s1001 because a 46-byte text file is not a video. No bind address, firewall rule or
    # permission change fixes that -- it is the container, not the config.
    bad "TELESTREAM_ACTION=strm is set, but PLEX CANNOT PLAY .strm FILES. Your library will
     show as empty, or every title will fail with s1001. Emby, Jellyfin and Kodi support
     .strm; Plex dropped it years ago. Use real downloads instead:
       sudo sed -i 's/^TELESTREAM_ACTION=.*/TELESTREAM_ACTION=stream/' $CONFIG_DIR/bridge.env
       sudo systemctl restart mwatcher-bridge
     Everything below still applies if you move to Emby/Jellyfin/Kodi."
    if bridge_lan_bound; then
      ok "bridge listens beyond loopback, as play-through needs"
    else
      bridge_env_set BRIDGE_HOST 0.0.0.0 || true
      warn "play-through is on, so the bridge must answer your LAN — added BRIDGE_HOST=0.0.0.0
       to bridge.env (which overrides the unit's loopback default). Without it every .strm
       plays on THIS box and fails with s1001 on every phone and TV."
    fi
    local pub ip
    pub="$(fc_var_from "$CONFIG_DIR/bridge.env" TELESTREAM_PUBLIC_BASE_URL 2>/dev/null || true)"
    case "$pub" in
      ""|*127.0.0.1*|*localhost*|*0.0.0.0*)
        ip="$(lan_ip)"
        if [ -n "$ip" ]; then
          bridge_env_set TELESTREAM_PUBLIC_BASE_URL "http://$ip:$BRIDGE_PORT" || true
          ok "TELESTREAM_PUBLIC_BASE_URL=http://$ip:$BRIDGE_PORT (this box's LAN address)"
          info "that is what gets written into the .strm files, so it must be an address your
       Plex clients can reach — away from home, use your Tailscale IP instead"
        else
          warn "play-through is on but this box's LAN address could not be determined.
       Set TELESTREAM_PUBLIC_BASE_URL in $CONFIG_DIR/bridge.env to the address your
       Plex clients use for this machine."
        fi
        ;;
      *) ok "TELESTREAM_PUBLIC_BASE_URL=$pub" ;;
    esac
  fi

  # ---- 6. systemd units ----------------------------------------------------
  hdr "6. Services"
  local units="fastcombo mwatcher-bridge"
  if fc_is_remote; then
    units="mwatcher-bridge"
    info "not installing fastcombo.service — addons are served from $FC_BASE_URL"
  elif [ -n "$FC_ADOPTED" ]; then
    # Overwriting this unit would repoint a working service at a clone it was not
    # configured for. The existing install keeps running under its own unit.
    units="mwatcher-bridge"
    info "not touching ${FC_UNIT:-fastcombo.service} — your existing Fast Combo keeps running as it is"
  fi
  for unit in $units; do
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
        -e "s|^Environment=FASTCOMBO_BASE_URL=.*|Environment=FASTCOMBO_BASE_URL=$(fc_target)|" \
        "$src" > "$dst"
    ok "wrote $dst"
  done
  systemctl daemon-reload
  # shellcheck disable=SC2086
  systemctl enable $units >/dev/null 2>&1 || true
  # `enable --now` is a NO-OP for a unit that is already running, so the BRIDGE_HOST=0.0.0.0
  # that §5b just wrote into bridge.env would not take effect until someone restarted by
  # hand. The bridge stayed bound to loopback while its config said otherwise: doctor
  # reported "listens beyond loopback" from the file, every client got s1001, and Plex's log
  # said "video has neither a video stream nor an audio stream" because the fetch was
  # refused. Restart unconditionally. $units excludes fastcombo whenever it was adopted.
  for s in $units; do
    systemctl restart "$s" >/dev/null 2>&1 || true
  done
  sleep 2
  for s in $units; do
    svc_active "$s" && ok "$s running" || bad "$s failed to start → sudo journalctl -u $s -n 30 --no-pager"
  done

  # ---- 7. firewall ---------------------------------------------------------
  hdr "7. Firewall"
  if have ufw && ufw status 2>/dev/null | grep -qi active; then
    ufw allow from 192.168.0.0/16 to any >/dev/null 2>&1 || true
    if bridge_lan_bound; then
      ufw allow from 192.168.0.0/16 to any port "$BRIDGE_PORT" proto tcp >/dev/null 2>&1 || true
      ok "LAN allowed, including $BRIDGE_PORT for play-through"
      info "Fast Combo stays loopback-only; the bridge is LAN-only and NOT reachable from the
       internet — /play/<key> has no authentication, so keep it that way"
    else
      ok "LAN allowed (Fast Combo and the bridge stay loopback-only on purpose)"
    fi
    info "Plex remote access: forward TCP 32400 on your router, or use Tailscale (§5d of the guide)"
  else
    info "ufw not active — nothing to do"
    if bridge_lan_bound; then
      warn "no firewall is active while the bridge listens on the LAN. On a box with a public
       interface that exposes /play/<key>, which has no authentication. Enable ufw:
            sudo ufw allow from 192.168.0.0/16 to any port $BRIDGE_PORT proto tcp
            sudo ufw enable
       or keep it private with Tailscale instead (§5d)."
    fi
  fi

  do_status

  local fckey2
  fckey2="$(grep -E '^FC_ACCESS_KEY=' "$CONFIG_DIR/fastcombo.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  if [ -n "$AUTO_MODE" ]; then return 0; fi
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

# =============================================================================
#  auto -- the "sit and relax" path. Installs everything, then waits for the one
#          step only a human can do (sign in with Google) and finishes the Plex
#          side by itself: claim detection, both libraries, auto-scan, verify.
#
#    sudo bash install.sh auto
#    sudo bash install.sh auto --claim-token claim-XXXXXXXX     # headless / SSH
# =============================================================================
do_auto() {
  need_root auto
  local claim="" timeout="${PLEX_SIGNIN_TIMEOUT:-900}" pport="${PLEX_PORT:-32400}"
  while [ $# -gt 0 ]; do
    case "$1" in
      --claim-token)   claim="${2:-}"; shift 2 ;;
      --claim-token=*) claim="${1#*=}"; shift ;;
      --timeout)       timeout="${2:-900}"; shift 2 ;;
      --timeout=*)     timeout="${1#*=}"; shift ;;
      --plex-port)     pport="${2:-32400}"; shift 2 ;;
      *) warn "ignoring unknown argument: $1"; shift ;;
    esac
  done
  [ -n "$claim" ] || claim="${PLEX_CLAIM:-}"

  hdr "Mwatcher automatic setup"
  info "everything below is unattended except one thing: signing in to Plex with Google."
  info "when it asks, open the URL on any device on your network and sign in. Then relax."

  AUTO_MODE=1
  do_install

  local py="$REPO_DIR/scripts/plex_setup.py"
  [ -f "$py" ] || die "missing $py"
  have python3 || die "python3 is required for the Plex automation"

  hdr "8. Plex sign-in, libraries and scan"
  local args=(--base-url "http://127.0.0.1:$pport" --media-dir "$MEDIA_DIR" --timeout "$timeout")
  [ -n "$claim" ] && args+=(--claim-token "$claim")
  args+=(--wait-signin --libraries --verify)

  local rc=0
  python3 "$py" "${args[@]}" || rc=$?

  hdr "Done"
  if [ "$rc" = "0" ]; then
    ok "Plex is signed in, both libraries exist, and automatic scanning is on"
    printf '\n  %sOpen the dashboard and add something:%s\n' "$B$Y" "$R"
    printf '    %shttp://%s:%s/%s\n' "$B" "$(lan_ip_cli)" "$BRIDGE_PORT" "$R"
    printf '\n  or from a shell:\n'
    printf "    %scurl -X POST localhost:%s/add -H 'Content-Type: application/json' -d '{\"title\":\"Dune\",\"year\":2021}'%s\\n" "$B" "$BRIDGE_PORT" "$R"
    printf '\n  Anything will not play?  %ssudo bash %s/install.sh doctor "title"%s\n' "$B" "$REPO_DIR" "$R"
  else
    warn "the Plex side did not finish cleanly (exit $rc). The install itself is complete and
     nothing is broken -- re-run just that part any time; it is idempotent and will not touch
     your existing libraries:
          ${B}sudo bash $REPO_DIR/install.sh auto${R}"
    info "if it timed out waiting for sign-in, either open the URL it printed and sign in,
     or use the headless route: get a token from https://plex.tv/claim (valid ~5 min) and run
          ${B}sudo bash $REPO_DIR/install.sh auto --claim-token claim-XXXXXXXX${R}"
  fi
  # Deliberately return 0: a non-zero `return` is a failing command under set -e, so the ERR
  # trap fires and prints "the install is INCOMPLETE" over an install that finished fine. The
  # real status travels in AUTO_RC and the dispatcher exits with it.
  AUTO_RC="$rc"
  return 0
}

# This box's LAN address, for the closing summary. Never fatal.
lan_ip_cli() {
  ip route get 1.1.1.1 2>/dev/null | grep -o 'src [0-9.]*' | awk '{print $2}' | head -1 || true
}

# =============================================================================
#  update -- pull the latest code and apply it, in one command.
#
#  A private box behind NAT with no port forwarding cannot be pushed to: nothing
#  outside can reach it. So updates have to be PULLED from the box itself. This
#  does the whole sequence that otherwise takes six commands and is easy to get
#  half-right -- pull, reload systemd, restart the bridge (which is what makes a
#  changed bridge.env take effect), repair any orphaned pointers, then reconcile
#  the Plex libraries.
# =============================================================================
do_update() {
  need_root update
  hdr "Update Mwatcher"
  cd "$REPO_DIR" || die "cannot enter $REPO_DIR"
  if [ -d .git ] && have git; then
    local before after
    before="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
    if git pull --ff-only 2>&1 | sed 's/^/  /'; then :; else
      warn "git pull did not complete cleanly; continuing with what is on disk"
    fi
    after="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
    if [ "$before" = "$after" ]; then
      ok "already up to date ($after)"
    else
      ok "updated $before → $after"
    fi
  else
    warn "$REPO_DIR is not a git checkout — nothing to pull"
  fi

  systemctl daemon-reload >/dev/null 2>&1 || true
  # A restart is not optional: enable --now does nothing to a running unit, so a
  # bridge.env change silently never takes effect. See docs/WORKLOG.md trap 32.
  if systemctl restart mwatcher-bridge >/dev/null 2>&1; then
    ok "restarted mwatcher-bridge"
    local real=""
    real="$(bridge_bind_reality "$BRIDGE_PORT" 2>/dev/null || true)"
    if [ -n "$real" ]; then
      if bridge_bind_reality "$BRIDGE_PORT" >/dev/null 2>&1; then
        ok "the running bridge is bound to ${real} — reachable from your LAN"
      else
        bad "the running bridge is bound to ${real} — play-through will fail on other devices"
      fi
    fi
  else
    bad "mwatcher-bridge did not restart → sudo journalctl -u mwatcher-bridge -n 30 --no-pager"
  fi

  hdr "Repairing play-through pointers"
  if as_user python3 "$REPO_DIR/scripts/telestream_to_plex.py" --repoint 2>&1 \
       | grep -E '"orphaned"|"recreated"|"failed"|^\[' | tail -12 | sed 's/^/  /'; then :; fi

  hdr "Plex libraries"
  python3 "$REPO_DIR/scripts/plex_setup.py" \
    --media-dir "$MEDIA_DIR" --libraries --verify || true
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
# =============================================================================
#  seerr -- request a title and let your own server download it (no debrid)
# =============================================================================
#  Brings up Seerr + Radarr + Sonarr + Prowlarr + qBittorrent with Docker, all
#  sharing ONE media path so imports never fail on path mismatches.
do_seerr() {
  need_root "seerr"
  hdr "Seerr stack  (browse -> request -> your server downloads it)"
  info "Seerr itself never downloads: it hands requests to Radarr/Sonarr, which use"
  info "Prowlarr (indexers) + qBittorrent. That is what replaces a debrid service."

  local STACK_SRC=""
  if [ -n "$REPO_DIR" ] && [ -f "$REPO_DIR/services/seerr-stack/docker-compose.yml" ]; then
    STACK_SRC="$REPO_DIR/services/seerr-stack/docker-compose.yml"
  fi
  [ -n "$STACK_SRC" ] || die "cannot find services/seerr-stack/docker-compose.yml -- run this from inside the Mwatcher repo"

  local STACK_DIR="${SEERR_STACK_DIR:-$RUN_HOME/mwatcher-seerr}"
  local DL_DIR="${DOWNLOADS_DIR:-$MEDIA_DIR/downloads}"
  local COMPOSE=""

  # ---- 1. docker -------------------------------------------------------------
  hdr "1. Docker"
  if have docker; then
    ok "docker $(docker --version 2>/dev/null | sed 's/^Docker version //;s/,.*//')"
  else
    warn "docker not installed -- installing (Seerr/Radarr/Sonarr only ship as images)"
    apt-get update -qq || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io >/dev/null 2>&1 || true
    systemctl enable --now docker >/dev/null 2>&1 || true
    have docker && ok "docker installed" || die "docker install failed -- install it manually, then re-run"
  fi
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
    ok "docker compose $(docker compose version --short 2>/dev/null)"
  elif have docker-compose; then
    COMPOSE="docker-compose"
    warn "using the standalone docker-compose binary (the plugin is missing)"
  else
    warn "installing the compose plugin"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-compose-v2 >/dev/null 2>&1 \
      || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-compose-plugin >/dev/null 2>&1 || true
    if docker compose version >/dev/null 2>&1; then
      COMPOSE="docker compose"; ok "docker compose $(docker compose version --short 2>/dev/null)"
    else
      die "no docker compose available -- install docker-compose-plugin, then re-run"
    fi
  fi

  # ---- 2. folders ------------------------------------------------------------
  hdr "2. Folders"
  mkdir -p "$MEDIA_DIR/Movies" "$MEDIA_DIR/TV Shows" "$DL_DIR" "$STACK_DIR"
  local d
  for d in seerr radarr sonarr prowlarr qbittorrent; do mkdir -p "$STACK_DIR/$d/config"; done
  chown -R "$RUN_USER":"$RUN_USER" "$MEDIA_DIR" "$DL_DIR" "$STACK_DIR" 2>/dev/null || true
  chmod -R a+rX "$MEDIA_DIR" "$DL_DIR" 2>/dev/null || true
  ok "library:   $MEDIA_DIR/Movies  and  $MEDIA_DIR/TV Shows"
  ok "downloads: $DL_DIR"
  ok "configs:   $STACK_DIR/<app>/config"
  info "every container mounts the library at the SAME path (/media) and downloads at"
  info "/downloads, so Radarr/Sonarr/qBittorrent agree and no path mapping is needed."

  # ---- 3. compose file + .env ------------------------------------------------
  hdr "3. Compose file"
  cp "$STACK_SRC" "$STACK_DIR/docker-compose.yml"
  ok "wrote $STACK_DIR/docker-compose.yml"
  if [ -f "$STACK_DIR/.env" ]; then
    ok ".env already exists -- keeping your ports, timezone and paths"
  else
    local tz; tz="$(cat /etc/timezone 2>/dev/null || echo Etc/UTC)"
    cat > "$STACK_DIR/.env" <<EOF
PUID=$(id -u "$RUN_USER")
PGID=$(id -g "$RUN_USER")
TZ=$tz
MEDIA_DIR=$MEDIA_DIR
DOWNLOADS_DIR=$DL_DIR
STACK_DIR=$STACK_DIR
SEERR_PORT=${SEERR_PORT:-5055}
RADARR_PORT=${RADARR_PORT:-7878}
SONARR_PORT=${SONARR_PORT:-8989}
PROWLARR_PORT=${PROWLARR_PORT:-9696}
QBT_PORT=${QBT_PORT:-8080}
QBT_TORRENT_PORT=${QBT_TORRENT_PORT:-6881}
EOF
    chown "$RUN_USER":"$RUN_USER" "$STACK_DIR/.env" 2>/dev/null || true
    ok "wrote $STACK_DIR/.env  (uid=$(id -u "$RUN_USER") gid=$(id -g "$RUN_USER") tz=$tz)"
  fi

  # ---- 4. up -----------------------------------------------------------------
  hdr "4. Starting containers"
  if (cd "$STACK_DIR" && $COMPOSE up -d); then
    ok "containers up"
  else
    die "docker compose up failed -- cd $STACK_DIR && $COMPOSE up -d   to see why"
  fi
  sleep 4
  (cd "$STACK_DIR" && $COMPOSE ps) 2>/dev/null || true

  # ---- 5. point the bridge at Seerr ------------------------------------------
  hdr "5. Bridge wiring"
  local BRIDGE_ENV="$CONFIG_DIR/bridge.env"
  if [ -f "$BRIDGE_ENV" ]; then
    if grep -q '^SEERR_URL=' "$BRIDGE_ENV" 2>/dev/null; then
      ok "bridge.env already has SEERR_URL"
    else
      {
        echo ""
        echo "# --- Seerr: request titles so Radarr/Sonarr download them (no debrid) ---"
        echo "SEERR_URL=http://127.0.0.1:${SEERR_PORT:-5055}"
        echo "SEERR_MODE=${SEERR_MODE:-off}"
        echo "# Get the key from Seerr -> Settings -> General AFTER the first-run wizard."
        echo "# It is an ADMIN credential: keep this file chmod 600."
        echo "SEERR_API_KEY="
      } >> "$BRIDGE_ENV"
      chmod 600 "$BRIDGE_ENV" 2>/dev/null || true
      ok "added SEERR_URL + SEERR_API_KEY to $BRIDGE_ENV"
      warn "SEERR_API_KEY is still empty -- fill it in after step 2 below, then:"
      info "sudo systemctl restart mwatcher-bridge"
    fi
    if grep -q '^SEERR_API_KEY=..*' "$BRIDGE_ENV" 2>/dev/null; then
      ok "SEERR_API_KEY is set"
    fi
  else
    warn "$BRIDGE_ENV does not exist yet -- run: sudo bash install.sh"
    info "then add SEERR_URL=http://127.0.0.1:${SEERR_PORT:-5055} and SEERR_API_KEY=<key>"
  fi

  # ---- 6. what to do next ----------------------------------------------------
  local lan; lan="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' || true)"
  lan="${lan:-<this-server-ip>}"
  hdr "Next: configure in this order (it matters)"
  cat <<EOF
  1. qBittorrent  http://$lan:${QBT_PORT:-8080}
       Set a real password immediately (default admin/adminadmin).
  2. Prowlarr     http://$lan:${PROWLARR_PORT:-9696}
       Add your indexers, then Settings -> Apps -> add Radarr and Sonarr
       (host: radarr / sonarr -- the compose service names).
  3. Radarr       http://$lan:${RADARR_PORT:-7878}
       Settings -> Download Clients -> add qBittorrent (host: qbittorrent, port ${QBT_PORT:-8080}).
       Settings -> Media Management -> Add Root Folder -> /media/Movies
  4. Sonarr       http://$lan:${SONARR_PORT:-8989}
       Same download client; root folder /media/TV Shows
  5. Seerr        http://$lan:${SEERR_PORT:-5055}
       First-run wizard -> media server: Plex at http://host.docker.internal:32400
       -> add the Radarr and Sonarr servers -> Settings -> General -> copy the API key
       -> paste it into SEERR_API_KEY in $BRIDGE_ENV
       -> sudo systemctl restart mwatcher-bridge

  Then either browse Seerr's own UI and hit Request, or from the Mwatcher dashboard:
       curl -X POST http://127.0.0.1:$BRIDGE_PORT/request -H 'Content-Type: application/json' \\
            -d '{"title":"Dune","year":2021}'
  And to watch something now WHILE the permanent copy downloads:
       curl -X POST http://127.0.0.1:$BRIDGE_PORT/fetch -H 'Content-Type: application/json' \\
            -d '{"title":"Dune","year":2021,"action":"both"}'

  Useful:  cd $STACK_DIR && $COMPOSE ps        (or: logs -f seerr)
           sudo bash install.sh status         (shows Seerr reachability)
EOF
  echo
}

usage() {
  cat <<EOF
Mwatcher installer

  sudo bash install.sh auto               EVERYTHING: install, then wait for you to sign in
                                          to Plex with Google, then create both libraries,
                                          turn on automatic scanning and verify
  sudo bash install.sh auto --claim-token claim-XXXX
                                          the same, for a box with no browser: get the token
                                          from https://plex.tv/claim (valid ~5 minutes)
  sudo bash install.sh                    install / repair, then show status
  sudo bash install.sh update             git pull + restart the bridge + repair pointers
                                          + reconcile the Plex libraries, in one command
  sudo bash install.sh status             report only, change nothing
  sudo bash install.sh doctor [title]     diagnose playback problems (s1001 etc.)
  sudo bash install.sh seerr              Seerr + Radarr/Sonarr + Prowlarr + qBittorrent
                                          (request a title, your server downloads it)
  sudo bash install.sh uninstall          remove the services (keeps media)

Safe to re-run: existing keys, passwords and addon lists are preserved.

Everything on one machine -- including the box your addons already run on:
  sudo bash install.sh
  An existing Fast Combo is detected and adopted: no second clone, no new access key,
  and its systemd unit is left alone, so the addon URL in your Stremio app keeps working.
  If the key cannot be found automatically:  sudo FC_ACCESS_KEY=<key> bash install.sh

Addons on another machine (e.g. a VPS), Plex here:
  sudo FC_BASE_URL=https://addons.example.com FC_REMOTE_ACCESS_KEY=<key> bash install.sh
EOF
}

case "${1:-install}" in
  install|"")  do_install ;;
  auto)        shift; do_auto "$@"; exit "$AUTO_RC" ;;
  update|upgrade) do_update ;;
  status)      do_status ;;
  doctor)      shift; do_doctor "${1:-}" ;;
  seerr)       do_seerr ;;
  uninstall)   do_uninstall ;;
  -h|--help|help) usage ;;
  *)           usage; exit 1 ;;
esac
