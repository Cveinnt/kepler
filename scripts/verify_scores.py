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
aggregate itself is the toolkit's business, and empirically its formula for
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

import argparse
import glob
import gzip
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


def check_result(result: dict, events: list[dict], rel: str,
                 counts: dict[str, int], bad: list[str]) -> bool:
    """Compare one result row with its ledger; return whether levels were checked."""
    reported = result.get("level_actions")
    if not reported:
        return False
    counted = scored_actions_per_level(events)
    for level in range(min(result.get("levels_completed", 0), len(reported))):
        timeline, scorecard = counted.get(level, 0), reported[level]
        if scorecard == timeline:
            counts["exact"] += 1
        elif scorecard > timeline:
            counts["conservative"] += 1
        else:
            counts["inflated"] += 1
            bad.append(
                f"{rel} L{level}: scorecard {scorecard} < timeline {timeline}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--traces-dir",
        help="exported trace dataset containing runs.jsonl and events/**/*.jsonl.gz; "
             "when omitted, inspect local runs*/ workspaces",
    )
    args = ap.parse_args()

    exact = conservative = inflated = 0
    runs = 0
    bad: list[str] = []

    counts = {"exact": 0, "conservative": 0, "inflated": 0}
    if args.traces_dir:
        traces = Path(args.traces_dir)
        index = traces / "runs.jsonl"
        if not index.exists():
            print(f"VACUOUS: {index} is missing; no exported traces were checked.")
            return 2
        for line in index.read_text().splitlines():
            if not line.strip():
                continue
            result = json.loads(line)
            event_path = traces / result["events_file"]
            if not event_path.exists():
                bad.append(f"{event_path.relative_to(traces)}: event ledger missing")
                continue
            with gzip.open(event_path, "rt", encoding="utf-8") as handle:
                events = [json.loads(event) for event in handle if event.strip()]
            rel = f"{result.get('model')}/{result.get('game')}"
            if check_result(result, events, rel, counts, bad):
                runs += 1
    else:
        for ev_path in sorted(glob.glob(str(ROOT / "runs*/*/*/events.jsonl"))):
            ws = Path(ev_path).parent
            rj = ws / "result.json"
            if not rj.exists():
                continue
            result = json.loads(rj.read_text())
            events = [json.loads(line) for line in open(ev_path) if line.strip()]
            rel = str(ws.relative_to(ROOT))
            if check_result(result, events, rel, counts, bad):
                runs += 1

    exact = counts["exact"]
    conservative = counts["conservative"]
    inflated = counts["inflated"]

    total = exact + conservative + inflated
    if runs == 0 or total == 0:
        print("VACUOUS: no scored runs were found; this check verified nothing.\n"
              "Download the trace dataset and pass --traces-dir, or run a game.")
        return 2
    print(f"{runs} scored runs, {total} completed levels checked\n")
    print(f"  exact match to the ledger          {exact}")
    print(f"  scorecard charged MORE (costs us)  {conservative}")
    print(f"  scorecard charged FEWER (inflates) {inflated}")
    if bad:
        print("\nINFLATED, a published score is not supported by its own timeline:")
        for b in bad:
            print("   ", b)
        return 1
    print("\nPASS: no level is scored with fewer actions than the append-only "
          "ledger recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
