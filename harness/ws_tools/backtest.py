#!/usr/bin/env python3
"""Certify world_model.py against the ENTIRE recorded history (costs no actions).

Replays every recorded transition through world_model.simulate and reports exact
grid matches on non-terminal steps plus level_up/game_over/win flags on every step.
Steps following a reset, and grids after a level_up, are flag-checked only.

Usage:
  python tools/backtest.py                 # full history
  python tools/backtest.py --level 2       # only transitions that started on level 2
  python tools/backtest.py --tail 40       # only the last 40 transitions
  python tools/backtest.py --show 3        # detail for first 3 mismatches (default 3)
"""

from __future__ import annotations

import argparse

from _lib import action_str, diff_cells, load_world_model, read_events, simulate_safe


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=None)
    ap.add_argument("--tail", type=int, default=None)
    ap.add_argument("--show", type=int, default=3)
    args = ap.parse_args()

    mod = load_world_model()
    events = list(read_events())

    transitions = []
    for prev, cur in zip(events, events[1:]):
        if cur["reset"] or prev["grid"] is None:
            continue  # a reset has no predictable prior transition
        if args.level is not None and prev["level"] != args.level:
            continue
        transitions.append((prev, cur))
    if args.tail:
        transitions = transitions[-args.tail:]

    total = len(transitions)
    skipped = len(events) - 1 - total if args.level is None and not args.tail else None
    ok = 0
    mismatches = []
    errors = []
    for prev, cur in transitions:
        try:
            pred = simulate_safe(mod, prev["grid"], cur["action"])
        except Exception as exc:
            errors.append((cur["i"], f"{type(exc).__name__}: {exc}"))
            continue
        flag_bad = []
        if pred["level_up"] != cur["level_up"]:
            flag_bad.append(f"level_up pred={pred['level_up']} real={cur['level_up']}")
        if pred["game_over"] != cur["game_over"]:
            flag_bad.append(f"game_over pred={pred['game_over']} real={cur['game_over']}")
        if pred["win"] != cur["win"]:
            flag_bad.append(f"win pred={pred['win']} real={cur['win']}")
        grid_diff = []
        if not cur["level_up"] and not cur["win"] and cur["grid"] is not None:
            grid_diff = diff_cells(pred["grid"], cur["grid"])
        if not flag_bad and not grid_diff:
            ok += 1
        else:
            mismatches.append((prev, cur, flag_bad, grid_diff))

    verdict = "GREEN" if ok == total and not errors else "RED"
    extra = f", {len(errors)} simulate() error(s)" if errors else ""
    skip_note = f", {skipped} skipped (resets)" if skipped else ""
    print(
        f"backtest [{'all' if args.level is None else f'level {args.level}'}"
        f"{f', tail {args.tail}' if args.tail else ''}]: {ok}/{total} transitions fully "
        f"correct (grid on non-terminal steps + level_up/dead/win flags on every step); "
        f"{len(mismatches)} mismatch(es){extra}{skip_note} -> {verdict}"
    )
    for i, msg in errors[: args.show]:
        print(f"  ERROR at event {i}: {msg}")
    for prev, cur, flag_bad, grid_diff in mismatches[: args.show]:
        print(
            f"  MISMATCH event {cur['i']} (level {prev['level']}, "
            f"action {action_str(cur['action'])}):"
        )
        for fb in flag_bad:
            print(f"    flag: {fb}")
        if grid_diff:
            sample = ", ".join(
                f"({x},{y}) pred={a} real={b}" for x, y, a, b in grid_diff[:15]
            )
            more = f" (+{len(grid_diff) - 15} more)" if len(grid_diff) > 15 else ""
            print(f"    grid: {len(grid_diff)} cells mispredicted: {sample}{more}")
        print(
            f"    inspect with: python tools/observe.py --event {prev['i']} "
            f"and --event {cur['i']}"
        )
    if len(mismatches) > args.show:
        print(f"  ... {len(mismatches) - args.show} more mismatch(es) not shown")
    raise SystemExit(0 if verdict == "GREEN" else 1)


if __name__ == "__main__":
    main()
