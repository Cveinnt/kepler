#!/usr/bin/env python3
"""Re-derive every reported score's action counts from the raw event timeline.

`result.json` copies its score out of the `arc_agi` toolkit's official scorecard.
That is the right source, but it means every published number rests on values we
did not compute. This closes that loop from the other side: it counts actions per
level straight out of the append-only `events.jsonl` and diffs them against the
per-level action counts the scorecard used.

Why action counts and not the aggregate: RHAE is
`min((human_baseline / agent_actions) ** 2, 1.15)` per level, so the ONLY input an
agent could manipulate in its favour is the action count. A score is inflated iff
the scorecard believes the agent spent fewer actions than the ledger records. The
aggregate itself is the toolkit's business — and empirically its formula for
*unfinished* games does not reduce to a single closed form we can restate here,
so re-deriving it would test our guess rather than their arithmetic.

The assertion this makes is therefore directional and strict:

    no level may be scored with FEWER actions than the timeline recorded.

Equal is correct. More is conservative (it costs us score). Fewer would mean a
published number is not supported by its own ledger.

Three timeline subtleties, each learned by getting it wrong first:

  * A full reset starts a fresh attempt at the whole game. The directive's
    learn-then-speedrun rule deliberately burns a long unscored exploration pass
    and then full-resets to play clean, so counting the whole file double-counts
    every level. Only the final attempt is scored.
  * A resume restarts the daemon and the environment, which also begins a fresh
    attempt (and, before the numbering fix, restarted event indices at 0).
  * The RESET that opens an attempt is not a scored action, but every later
    mid-level RESET is. Restarting a level is not free.

Usage:  python3 scripts/verify_scores.py
"""

from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def scored_actions_per_level(events: list[dict]) -> Counter:
    """Actions per level for the attempt the scorecard actually scores."""
    start = 0
    for i, e in enumerate(events):
        if e.get("full_reset") or (i > 0 and e.get("i") == 0 and e.get("reset")):
            start = i
    seg = events[start:]
    if seg and seg[0].get("reset"):
        seg = seg[1:]
    per = Counter()
    for e in seg:
        if isinstance(e.get("action"), dict):
            per[e.get("prev_level", e.get("level"))] += 1
    return per


def main() -> int:
    exact = conservative = inflated = 0
    runs = 0
    bad: list[str] = []

    for ev_path in sorted(glob.glob(str(ROOT / "runs*/*/*/events.jsonl"))):
        ws = Path(ev_path).parent
        rj = ws / "result.json"
        if not rj.exists():
            continue
        result = json.loads(rj.read_text())
        rep = result.get("level_actions")
        if not rep:
            continue
        runs += 1
        events = [json.loads(l) for l in open(ev_path) if l.strip()]
        counted = scored_actions_per_level(events)
        rel = str(ws.relative_to(ROOT))

        for i in range(min(result.get("levels_completed", 0), len(rep))):
            timeline, scorecard = counted.get(i, 0), rep[i]
            if scorecard == timeline:
                exact += 1
            elif scorecard > timeline:
                conservative += 1
            else:
                inflated += 1
                bad.append(f"{rel} L{i}: scorecard {scorecard} < timeline {timeline}")

    total = exact + conservative + inflated
    if runs == 0 or total == 0:
        print("VACUOUS: no scored runs found under runs*/ — this check verified NOTHING.\n"
              "Fetch the trace dataset first (see README > Traces), or run a game.")
        return 2
    print(f"{runs} scored runs, {total} completed levels checked\n")
    print(f"  exact match to the ledger          {exact}")
    print(f"  scorecard charged MORE (costs us)  {conservative}")
    print(f"  scorecard charged FEWER (inflates) {inflated}")
    if bad:
        print("\nINFLATED — a published score is not supported by its own timeline:")
        for b in bad:
            print("   ", b)
        return 1
    print("\nPASS: no level is scored with fewer actions than the append-only "
          "ledger recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
