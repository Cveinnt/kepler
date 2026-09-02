#!/usr/bin/env python3
"""Disable kimi's web search/fetch tools for the duration of a benchmark run.

Why this exists
---------------
kimi ships `moonshot_search` and `moonshot_fetch` enabled by default. On an
unseen-game benchmark those are a direct route to looking the answer up, and no
other CLI we drive (codex, claude, opencode) has them on. Detecting the tool
call afterwards is not good enough: this project has twice shipped a control
that was a rule rather than a boundary, and twice an agent walked through it.

Why not a host allowlist
------------------------
kimi exposes KIMI_CODE_ALLOWED_HOSTS, which looks like the right knob, but the
model provider and the search/fetch services share one host (api.kimi.com), so
any allowlist permitting the model also permits the lookup tools. The only
separation available is per-service, so this repoints the two service base URLs
at a closed local port. They fail; the model keeps working.

The edit is to the user's global config, so it is backed up first and is fully
reversible. Always restore when the run is done.

Usage:
  python3 scripts/kimi_lockdown.py --disable
  python3 scripts/kimi_lockdown.py --status
  python3 scripts/kimi_lockdown.py --restore
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

CONFIG = Path.home() / ".kimi-code" / "config.toml"
BACKUP = CONFIG.with_suffix(".toml.harness-backup")
# Port 1 is reserved and nothing listens on it: connections are refused
# immediately rather than hanging, so a blocked tool fails fast and visibly.
DEAD = "http://127.0.0.1:1/blocked-by-kepler-harness"
SERVICES = ("moonshot_search", "moonshot_fetch")


def _service_urls(text: str) -> dict[str, str]:
    out = {}
    for svc in SERVICES:
        m = re.search(rf'\[services\.{svc}\]\s*\nbase_url\s*=\s*"([^"]*)"', text)
        if m:
            out[svc] = m.group(1)
    return out


def status() -> int:
    if not CONFIG.exists():
        print(f"no kimi config at {CONFIG}")
        return 1
    urls = _service_urls(CONFIG.read_text())
    if not urls:
        print("no moonshot_search / moonshot_fetch services found; nothing to lock down")
        return 0
    for svc, url in urls.items():
        state = "BLOCKED" if url.startswith("http://127.0.0.1:1") else "LIVE (can reach the internet)"
        print(f"  {svc:18s} {state}\n{'':20s}{url}")
    print(f"\nbackup present: {BACKUP.exists()}")
    return 0


def disable() -> int:
    text = CONFIG.read_text()
    if not BACKUP.exists():
        shutil.copy2(CONFIG, BACKUP)
        print(f"backed up -> {BACKUP}")
    for svc in SERVICES:
        text = re.sub(rf'(\[services\.{svc}\]\s*\nbase_url\s*=\s*")[^"]*(")',
                      rf'\g<1>{DEAD}\g<2>', text)
    CONFIG.write_text(text)
    print("web search/fetch repointed at a closed port")
    return status()


def restore() -> int:
    if not BACKUP.exists():
        print("no backup to restore from")
        return 1
    shutil.copy2(BACKUP, CONFIG)
    BACKUP.unlink()
    print(f"restored {CONFIG} from backup")
    return status()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--disable", action="store_true")
    g.add_argument("--restore", action="store_true")
    g.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.disable:
        return disable()
    if a.restore:
        return restore()
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
