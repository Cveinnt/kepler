#!/usr/bin/env python3
"""Execute the certified clean run MECHANICALLY — no model in the loop.

Why this exists: the score is the final attempt, and v3/v4 trusted a live agent
to execute the programs it certified. Forensics on the sub-100 boards showed
that is exactly where the points died: agents certified tight programs, then
played worse ones. The two 99-class open harnesses never let a model touch the
scored attempt — the scorecard is a fail-closed replay of a recorded/certified
trace (Tycho's submission_replay, Retrodict's replay_runs; credited in NOTICE).
This tool is our version of that: the agent's job ends at certification, and
the scored attempt is this executor walking cleanrun.json through the daemon.

Contract (enforced by commit.py's gate before this will run):
  cleanrun.json = {"programs": [[action, ...], ...]}  one list per level, each
  within CLEANRUN_SLACK x that level's human baseline, and — when the world
  model exposes init_state/step_state/outcome — each simulating to level_up.

Fail-closed execution: before each action we simulate it in the certified
model (when possible) and compare the settled grid after the real step against
the model's prediction on every cell the model claims. First divergence STOPS
the executor immediately — a falsified premise must not spend more actions.
The stop leaves the game mid-attempt; the caller (run_game) may re-certify and
try again while budget allows, because a mechanical replay of a certified
program can only be improved by fixing the certificate, never by 'playing
better' live.

Usage (from the workspace root, like every other tool):
  python tools/cleanrun.py            # execute, print verdict
  python tools/cleanrun.py --dry-run  # validate the file against the gate only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import WS, daemon, load_world_model, read_events, simulate_safe  # noqa: E402


def _level_start_grids() -> dict[int, list[list[int]]]:
    """Observed first grid of each level, from the append-only ledger."""
    grids: dict[int, list[list[int]]] = {}
    prev_level = None
    for e in read_events():
        lvl = e.get("level")
        if lvl is not None and lvl != prev_level and e.get("grid") is not None:
            grids.setdefault(lvl, e["grid"])
            prev_level = lvl
    return grids


def _transport_check(programs):
    """A certified program must be replayable through the official API: the local
    engine clips off-grid ACTION6 clicks, the API 400s them."""
    bad = []
    for li, prog in enumerate(programs):
        for ai, a in enumerate(prog):
            if isinstance(a, dict) and a.get("name") == "ACTION6":
                x, y = a.get("x"), a.get("y")
                if not (isinstance(x, int) and isinstance(y, int) and 0 <= x <= 63 and 0 <= y <= 63):
                    bad.append(f"level {li} action {ai}: ACTION6 x={x} y={y}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="validate cleanrun.json without touching the game")
    args = ap.parse_args()

    try:
        programs = json.loads((WS / "cleanrun.json").read_text())["programs"]
    except Exception as exc:
        print(f"NO CERTIFICATE: cleanrun.json unreadable ({exc})")
        return 2

    st = daemon("/status")
    bases = st.get("human_baseline_actions") or []
    if not isinstance(programs, list) or len(programs) != len(bases):
        print(f"BAD CERTIFICATE: need {len(bases)} programs, got "
              f"{len(programs) if isinstance(programs, list) else type(programs)}")
        return 2

    try:
        mod = load_world_model()
    except Exception:
        mod = None

    # Certification, self-contained (do not trust that commit.py's gate ran):
    # lengths within slack, and — when the threaded-state API exists — each
    # program must simulate to level_up from the RECORDED level-start grid
    # (grounded, not an imagined start; ungrounded certification is how a
    # 162-action promise executed as a 40.3).
    import math
    SLACK = 1.3
    problems = []
    for i, (prog, b) in enumerate(zip(programs, bases)):
        cap = math.ceil(SLACK * b)
        if not isinstance(prog, list) or len(prog) > cap:
            problems.append(f"level {i}: {len(prog) if isinstance(prog,list) else '?'} "
                            f"actions > cap {cap}")
    if (mod is not None and hasattr(mod, "init_state")
            and hasattr(mod, "step_state") and hasattr(mod, "outcome")):
        starts = _level_start_grids()
        _bad = _transport_check(programs)
        if _bad:
            problems.extend(f"{b} — off-grid click; the official replay path rejects it "
                            "(the local engine clips it), so this program is not "
                            "transportable" for b in _bad)
        for i, prog in enumerate(programs):
            g0 = starts.get(i)
            try:
                state = mod.init_state([r[:] for r in g0] if g0 else None, i)
                reached = False
                for a in prog:
                    state = mod.step_state(state, dict(a))
                    if mod.outcome(state) in ("level_up", "win", "level_complete"):
                        reached = True
                        break
                if not reached:
                    problems.append(f"level {i}: program does not reach level_up "
                                    "in the certified model (grounded start)")
            except Exception as exc:
                problems.append(f"level {i}: simulation crashed ({type(exc).__name__})")
    if problems:
        print("CERTIFICATE REFUSED:\n  " + "\n  ".join(problems))
        return 2

    if args.dry_run:
        print(f"certificate: {len(programs)} programs, "
              f"lengths {[len(p) for p in programs]}, baselines {bases}")
        return 0

    # Fresh attempt. If a level is in progress, one RESET restarts the level;
    # if the game is fresh or WON, RESET starts the new run. Two resets from
    # mid-level = full restart (engine semantics recorded in the ledger).
    out = daemon("/act", {"name": "RESET"})
    if out.get("level", 0) != 0 or out.get("state") == "WIN":
        out = daemon("/act", {"name": "RESET"})
    if out.get("level", 0) != 0:
        print(f"CANNOT START FRESH: level {out.get('level')} after double RESET")
        return 3

    total = 0
    for lvl, prog in enumerate(programs):
        grid = out.get("grid")
        for i, action in enumerate(prog):
            # Predict before acting, on whatever the model claims.
            pred = None
            if mod is not None and grid is not None:
                sim = simulate_safe(mod, grid, action)
                pred = sim.get("grid") if isinstance(sim, dict) else None
            out = daemon("/act", {k: v for k, v in action.items()
                                  if k in ("name", "x", "y")})
            if out.get("error"):
                print(f"HALT level {lvl} step {i}: daemon error {out['error']}")
                return 4
            total += 1
            real = out.get("grid")
            if pred is not None and real is not None:
                for y, (pr, rr) in enumerate(zip(pred, real)):
                    bad = next((x for x, (pc, rc) in enumerate(zip(pr, rr))
                                if pc is not None and pc != rc), None)
                    if bad is not None:
                        print(f"HALT level {lvl} step {i}: model predicted "
                              f"{pr[bad]} at ({bad},{y}), game shows {rr[bad]} — "
                              "certificate falsified; fix world_model.py and "
                              "cleanrun.json, then rerun.")
                        return 5
            grid = real
            state = str(out.get("state", ""))
            if out.get("level", lvl) > lvl or state.endswith("WIN"):
                break  # level cleared (possibly early) — next program
        else:
            # Program exhausted without clearing the level.
            if out.get("level", lvl) <= lvl and not str(out.get("state", "")).endswith("WIN"):
                print(f"HALT level {lvl}: program of {len(prog)} actions ran dry "
                      f"without level_up — certificate incomplete.")
                return 6
        if str(out.get("state", "")).endswith("WIN"):
            break

    state = str(out.get("state", ""))
    print(f"CLEAN RUN {'WIN' if state.endswith('WIN') else state}: "
          f"{total} actions across {len(programs)} levels "
          f"(baseline total {sum(bases)}).")
    return 0 if state.endswith("WIN") else 7


if __name__ == "__main__":
    raise SystemExit(main())
