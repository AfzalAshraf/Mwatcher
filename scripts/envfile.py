#!/usr/bin/env python3
"""
Load ~/.config/mwatcher/bridge.env into the process environment.

systemd already does this for the service through EnvironmentFile=, so the bridge running
under mwatcher-bridge.service has always been fine. Running the same code from a shell has
no such mechanism, and the result is baffling:

    $ python3 scripts/telestream_to_plex.py --title Dune --year 2021
    FAILED - FASTCOMBO_ACCESS_KEY is not set

...while `install.sh status` happily reports that the key is set and Fast Combo answers
with it. The key is in a file the installer wrote; the CLI simply never looked. Worse, the
installer's own "Next steps" block prints that exact command.

Values already in the environment always win, so an explicit override still does what was
asked:

    FASTCOMBO_ACCESS_KEY=something-else python3 scripts/telestream_to_plex.py --title Dune

Set MWATCHER_ENV to point at a different file.
"""

from __future__ import annotations

import os

DEFAULT_PATH = "~/.config/mwatcher/bridge.env"

#: The file actually loaded, or None. Useful in error messages.
LOADED_FROM: str | None = None


def default_path() -> str:
    """The env file this looks for, after $MWATCHER_ENV and ~ expansion."""
    return os.path.expanduser(os.environ.get("MWATCHER_ENV") or DEFAULT_PATH)


def parse(text: str) -> dict[str, str]:
    """Parse env-file text. Tolerates comments, blank lines, `export `, and quoting.

    systemd's EnvironmentFile= takes the whole rest of the line as the value, so an
    unquoted path containing spaces is normal here -- do not split on whitespace.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, val = line.partition("=")
        key = key.strip()
        if not key or key.startswith("#"):
            continue
        val = val.strip()
        # Strip one matched pair of surrounding quotes, as systemd does. Only matched, so a
        # download command like 'curl ... -o {out} {stream}' keeps its inner quoting intact.
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key] = val
    return out


def load(path: str | None = None, override: bool = False) -> str | None:
    """Put the env file into os.environ. Returns the path read, or None if there is none.

    Never raises: a missing or unreadable file is the normal case on a fresh checkout.
    """
    global LOADED_FROM
    p = os.path.expanduser(path) if path else default_path()
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            values = parse(fh.read())
    except OSError:
        return None
    for key, val in values.items():
        if override or key not in os.environ:
            os.environ[key] = val
    LOADED_FROM = p
    return p


if __name__ == "__main__":
    import sys

    loaded = load(override=True)
    if not loaded:
        print(f"no env file at {default_path()}")
        sys.exit(1)
    print(f"{loaded}:")
    for k in sorted(os.environ):
        if k.startswith(("FASTCOMBO_", "TELESTREAM_", "SEERR_", "BRIDGE_", "CINEMETA_")):
            v = os.environ[k]
            if "KEY" in k or "PASSWORD" in k or "TOKEN" in k:
                v = f"{v[:3]}…({len(v)} chars)" if v else "(empty)"
            print(f"  {k}={v}")
