#!/usr/bin/env python3
"""Enforce the no-game-secrets invariant: zero game IDs in agent-visible surfaces.

The strongest answer to "your harness smuggles in knowledge about specific games"
is an invariant a reviewer can re-run, not a promise. Kepler makes that boundary
a release gate rather than a prose claim.

Agent-visible surfaces = everything the game-playing agent can read inside its
workspace: the directive (copied in as AGENTS.md/CLAUDE.md) and every file under
harness/ws_tools/ (copied in as tools/). Harness orchestration code (daemon,
run_game, sweep, score) legitimately handles game IDs and is NOT scanned.

Exits 0 when clean, 1 with per-hit lines when any game ID appears.
Wired into scripts/verify.py; run standalone any time:
  python3 scripts/check_no_game_ids.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

from score import GAMES  # noqa: E402

AGENT_VISIBLE = [ROOT / "harness" / "directive.md", ROOT / "harness" / "ws_tools"]


def main() -> int:
    pat = re.compile("|".join(GAMES), re.IGNORECASE)
    hits: list[str] = []
    for target in AGENT_VISIBLE:
        files = [target] if target.is_file() else sorted(target.rglob("*"))
        for f in files:
            if not f.is_file() or f.suffix == ".pyc":
                continue
            for n, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                m = pat.search(line)
                if m:
                    hits.append(f"{f.relative_to(ROOT)}:{n}: contains game ID "
                                f"{m.group(0)!r}: {line.strip()[:100]}")
    if hits:
        print("GAME-SECRETS CHECK FAILED — game IDs in agent-visible surfaces:")
        print("\n".join(hits))
        return 1
    n_files = sum(1 if t.is_file() else sum(1 for f in t.rglob("*") if f.is_file()
                                            and f.suffix != ".pyc")
                  for t in AGENT_VISIBLE)
    print(f"PASS: no game ID in any of the {n_files} agent-visible files "
          f"(directive.md + ws_tools/), {len(GAMES)} IDs checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
