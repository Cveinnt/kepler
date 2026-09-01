#!/usr/bin/env python3
"""Observe the current game state (read-only; costs no actions).

Usage:
  python tools/observe.py             # status + current grid + diff vs previous step
  python tools/observe.py --event 12  # render the grid recorded at timeline step 12
  python tools/observe.py --no-grid   # status only
"""

from __future__ import annotations

import argparse
import json

from _lib import WS, action_str, daemon, diff_cells, read_events, render_grid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", type=int, default=None)
    ap.add_argument("--no-grid", action="store_true")
    args = ap.parse_args()

    if args.event is not None:
        ev = next((e for e in read_events() if e["i"] == args.event), None)
        if ev is None:
            raise SystemExit(f"no event {args.event}")
        print(
            f"event {ev['i']}: action={action_str(ev['action'])} state={ev['state']} "
            f"level={ev['level']}/{ev['win_levels']} level_up={ev['level_up']}"
        )
        if ev["grid"]:
            print(render_grid(ev["grid"]))
        return

    st = daemon("/status")
    baselines = st.get("human_baseline_actions") or []
    print(
        f"game={st['title']} state={st['state']} "
        f"level={st['level']}/{st['win_levels']} "
        f"actions_used={st['action_count']} "
        f"available={st['available_actions']}"
    )
    if baselines:
        lvl = st["level"]
        cur_base = baselines[lvl] if lvl < len(baselines) else None
        # Actions spent on the CURRENT level = every event after the last level_up.
        # Event 0 is the opening RESET and costs nothing; every other event is one action.
        # Count by position in the file, not by the "i" field: a resumed run restarts
        # the environment, so only events after the last reset belong to this attempt.
        # Count by position in the file. The current level began at the later of: the
        # last level_up, or the last FULL reset (a fresh run restarts the whole game).
        # A mid-level RESET does not reset the count — those actions still count.
        evs = list(read_events())
        last_full = max((n for n, e in enumerate(evs) if e.get("full_reset")), default=0)
        last_up = max((n for n, e in enumerate(evs) if e["level_up"]), default=0)
        spent_here = len(evs) - 1 - max(last_up, last_full)
        print(f"human_baseline per level: {baselines} (total {sum(baselines)})")
        if cur_base:
            ratio = spent_here / cur_base if cur_base else 0
            best = min((cur_base / spent_here) ** 2, 1.15) if spent_here else 1.15
            verdict = (
                "still at/above human efficiency" if ratio <= 1.0
                else "below human efficiency — this level's score is decaying quadratically"
                if ratio < 3 else
                "THIS LEVEL'S SCORE IS ALREADY MOSTLY LOST — completing it still matters "
                "(the completion cap needs every level), but stop probing and finish; "
                "spend your thinking on a model that makes LATER levels cheap"
            )
            print(
                f"current level {lvl + 1}: {spent_here} actions spent vs human {cur_base} "
                f"({ratio:.1f}x) -> best score still achievable for it: {best * 100:.0f}/115. "
                f"{verdict}"
            )
    if args.no_grid or not st.get("grid"):
        return

    events = list(read_events())
    if len(events) >= 2 and events[-2]["grid"] and not events[-1]["reset"]:
        d = diff_cells(events[-2]["grid"], events[-1]["grid"])
        if d:
            sample = ", ".join(f"({x},{y}) {a}->{b}" for x, y, a, b in d[:20])
            more = f" (+{len(d) - 20} more)" if len(d) > 20 else ""
            print(f"diff vs previous step: {len(d)} cells: {sample}{more}")
        else:
            print("diff vs previous step: none")
    print("current grid (hex colors, '.'=0):")
    print(render_grid(st["grid"]))


if __name__ == "__main__":
    main()
