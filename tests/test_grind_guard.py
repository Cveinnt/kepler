#!/usr/bin/env python3
"""Replay the grind guard over recorded timelines.

The guard added to commit.py must do two things, and both need evidence:

  1. FIRE on the tn36 pathology (12,287 actions on one level, brute-forced
     coordinate sweep) early enough to matter.
  2. STAY SILENT on healthy runs, or it would break games we already win.

This walks each timeline action-by-action and asks the guard whether it would
have blocked the action the agent actually took next.

Usage:  python3 scripts/test_grind_guard.py
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness" / "ws_tools"))

from commit import (  # noqa: E402
    DISTINCT_ACTION_MIN,
    GRIND_HARD_CAP,
    GRIND_MIN_LEVEL_ACTIONS,
    RESET_THRASH_MAX,
    COARSE_REPEAT_MAX,
    EXACT_REPEAT_MAX,
    GRIND_PLAN_FRACTION,
    _coarse_key,
    _exact_key,
)


# v5: NOTHING refuses while learning; the hard cap became advisory after a
# >3,000-action level produced a legitimate 100 (lf52), and the real cost cap
# moved to run_game's ledger-derived run budget. This test now simulates the
# WARNING tier: it must stay silent on efficient wins and still FLAG the
# degenerate coordinate-sweep fixture.
def would_block(all_past: list[dict], proposed: list[dict]) -> bool:
    """Mirror of commit.check_not_grinding, without the daemon/timeline coupling."""
    proposed_raw = list(proposed)
    past = [a for a in all_past if a.get("name") != "RESET"]
    if len(past) < GRIND_MIN_LEVEL_ACTIONS:
        return False
    if len(past) >= GRIND_HARD_CAP and any(a.get("name") != "RESET" for a in proposed_raw):
        return True
    resets = sum(1 for a in all_past if a.get("name") == "RESET")
    distinct = len({_exact_key(a) for a in past})
    if resets >= RESET_THRASH_MAX and distinct <= DISTINCT_ACTION_MIN:
        return True  # demoted to warning in v3
    proposed = [a for a in proposed if a.get("name") != "RESET"]
    if not proposed:
        return False
    exact = Counter(_exact_key(a) for a in past)
    coarse = Counter(_coarse_key(a) for a in past)
    stale = [
        a for a in proposed
        if (exact[_exact_key(a)] >= EXACT_REPEAT_MAX or coarse[_coarse_key(a)] >= COARSE_REPEAT_MAX)
    ]
    return len(stale) >= GRIND_PLAN_FRACTION * len(proposed)


def first_block(events: list[dict]) -> tuple[int, int, int] | None:
    """Return (level, actions_into_level, actions_saved) at the first block, or None."""
    seg: list[dict] = []
    cur = events[0].get("level")
    for e in events:
        if e.get("level") != cur:
            cur, seg = e.get("level"), []
        act = e.get("action")
        if isinstance(act, dict):
            if would_block(seg, [act]):
                remaining = sum(1 for x in events if x.get("level") == cur) - len(seg)
                return (cur, len(seg), remaining)
            seg.append(act)
    return None


def main() -> int:
    rows = []
    ledgers = sorted(glob.glob(str(ROOT / "runs*/*/*/events.jsonl")))
    if not ledgers:
        print("VACUOUS: no run ledgers present; the grind-guard regression replays "
              "local run data that is not tracked in git. Refusing to report success "
              "on nothing.")
        return 2
    for ev_path in ledgers:
        ws = Path(ev_path).parent
        events = [json.loads(l) for l in open(ev_path) if l.strip()]
        if not events:
            continue
        rj = ws / "result.json"
        score = None
        if rj.exists():
            try:
                score = json.loads(rj.read_text()).get("score")
            except Exception:
                pass
        rows.append((str(ws.relative_to(ROOT)), len(events), score, first_block(events)))

    fired = [r for r in rows if r[3]]
    quiet = [r for r in rows if not r[3]]

    print(f"{'run':40} {'events':>7} {'score':>7}  guard")
    for name, n, score, blk in sorted(rows, key=lambda r: -(r[1])):
        s = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
        if blk:
            lvl, into, saved = blk
            print(f"{name:40} {n:7} {s:>7}  FIRES at level {lvl} after {into} actions (~{saved} wasted)")
        elif n > 400:
            print(f"{name:40} {n:7} {s:>7}  silent")
    if not rows:
        print("VACUOUS: no recorded timelines found under runs*/; this regression\n"
              "checked NOTHING. Fetch the trace dataset first (see README > Traces).")
        return 2
    print(f"\nfires on {len(fired)} run(s), silent on {len(quiet)}")

    # Regression assertions.
    ok = True
    healthy = [r for r in rows if isinstance(r[2], (int, float)) and r[2] >= 100.0]
    flagged = [r for r in healthy if r[3]]
    # Advisory tier: a warning on a winning marathon (a level legitimately
    # >3,000 actions) is correct behavior, not a regression; it costs no
    # refusal. Report them; fail only if MOST wins would be flagged, which
    # would mean the threshold is mis-tuned.
    if len(flagged) > max(2, len(healthy) // 10):
        ok = False
        print(f"\nFAIL: advisory fires on {len(flagged)}/{len(healthy)} runs that scored 100; threshold mis-tuned:")
        for r in flagged:
            print("   ", r[0])
    else:
        print(f"PASS: advisory silent on {len(healthy)-len(flagged)}/{len(healthy)} "
              f"runs that scored 100 (flagged marathons: "
              f"{', '.join(r[0] for r in flagged) or 'none'})")

    tn36 = [r for r in rows if r[0].endswith("gpt-max/tn36") and r[3]]
    # v3 note: the retry ledger's full resets keep each attempt-segment under the
    # hard cap, so only the primary 13.8k-event grind is required to fire.
    if not tn36:
        ok = False
        print("FAIL: guard did NOT fire on any tn36 grind ledger")
    else:
        lvl, into, saved = tn36[0][3]
        print(f"PASS: fires on tn36 grind at level {lvl} after {into} actions (~{saved} wasted)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
