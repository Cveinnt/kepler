#!/usr/bin/env python3
"""Plan inside the certified world model (costs no actions).

Breadth-first search from the CURRENT grid using world_model.simulate.
Goal: predicted level_up or win, or world_model.is_goal(grid) if defined.
Action set per state: world_model.candidate_actions(grid) if defined, else the
game's currently available basic actions (ACTION6 requires candidate_actions,
since clicks need coordinates).

The model does NOT need a perfect backtest. ~90% replay accuracy is normally
enough to plan on (published traces from prior harnesses plan at ~90% coverage); use the
backtest mismatches to know which situations to route around.

Usage:
  python tools/bfs.py [--max-nodes 200000] [--max-depth 120] [--all-goals]
Writes the found plan to plan.json and prints it.
"""

from __future__ import annotations

import argparse
import json
from collections import deque

from _lib import WS, action_str, daemon, load_world_model, normalize_action, simulate_safe


def key(grid: list[list[int]]) -> tuple:
    return tuple(tuple(r) for r in grid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-nodes", type=int, default=200_000)
    ap.add_argument("--max-depth", type=int, default=120)
    args = ap.parse_args()

    mod = load_world_model()
    st = daemon("/status")
    start = st["grid"]
    if start is None:
        raise SystemExit("no current grid")

    # ── threaded hidden state (Tycho: "a fresh init_state on the current grid
    # would lose it") ────────────────────────────────────────────────────────
    # If world_model defines init_state/step_state, the search runs in STATE
    # space: init_state on this level's first frame, then step_state threaded
    # over every action observed since, so hidden counters/phases/carried
    # objects survive into planning. render(state) (optional) maps a state back
    # to a grid for goal checks; outcome(state) (optional) may return
    # "level_complete"/"game_over"/"ongoing".
    threaded = hasattr(mod, "init_state") and hasattr(mod, "step_state")
    state0 = None
    if threaded:
        from _lib import read_events
        evs = list(read_events())
        lvl = evs[-1]["level"] if evs else 0
        seg = []
        for e in reversed(evs):
            if e.get("level") != lvl:
                break
            seg.append(e)
        seg.reverse()
        first_grid = next((e["grid"] for e in seg if e.get("grid") is not None), start)
        try:
            state0 = mod.init_state([r[:] for r in first_grid], lvl)
            for e in seg[1:]:
                a = e.get("action")
                if isinstance(a, dict) and a.get("name") != "RESET":
                    state0 = mod.step_state(state0, dict(a))
        except Exception as exc:
            print(f"threaded-state replay failed ({type(exc).__name__}: {exc}) — "
                  f"falling back to grid-space search")
            threaded = False

    if hasattr(mod, "candidate_actions"):
        def actions_for(g):
            return [normalize_action(a) for a in mod.candidate_actions([r[:] for r in g])]
    else:
        base = [{"name": f"ACTION{i}"} for i in st["available_actions"] if i != 6]
        if not base:
            raise SystemExit(
                "only ACTION6 available but world_model.candidate_actions() is not "
                "defined — define it to enumerate useful clicks"
            )
        def actions_for(g):
            return base

    has_goal = hasattr(mod, "is_goal")

    def is_goal_state(pred: dict, grid) -> bool:
        if pred is not None and (pred["level_up"] or pred["win"]):
            return True
        return has_goal and bool(mod.is_goal([r[:] for r in grid]))

    root = state0 if threaded else start
    # NOTE: this fallback was broken from v2 through v8.0 — the nested `def key`
    # made `key` function-local, so the first `key(root)` raised UnboundLocalError
    # and bfs.py crashed on every invocation. Agents routed around it by writing
    # their own searches. Fixed by binding the fallback to a distinct name.
    import json as _json
    def _key(s):
        try:
            return key(s)
        except TypeError:
            return _json.dumps(s, sort_keys=True, default=repr)
    seen = {_key(root)}
    q: deque = deque([(root, [])])
    expanded = 0
    sim_errors = 0
    n_actions_tried = 0
    n_effective = 0  # actions whose predicted successor differed from the source state
    while q:
        grid, path = q.popleft()
        if len(path) >= args.max_depth:
            continue
        expanded += 1
        if expanded > args.max_nodes:
            print(f"BFS: node budget exhausted ({args.max_nodes}); no goal found. "
                  f"{len(seen)} distinct states seen.")
            raise SystemExit(1)
        for act in actions_for(grid):
            n_actions_tried += 1
            try:
                if threaded:
                    ns = mod.step_state(grid, dict(act))  # 'grid' holds a STATE here
                    out = mod.outcome(ns) if hasattr(mod, "outcome") else "ongoing"
                    render = mod.render(ns) if hasattr(mod, "render") else None
                    pred = {"grid": ns, "level_up": out == "level_complete",
                            "game_over": out == "game_over", "win": False,
                            "_render": render}
                else:
                    pred = simulate_safe(mod, grid, act)
            except Exception:
                sim_errors += 1
                if sim_errors > 50:
                    raise SystemExit("too many simulate() errors — fix world_model.py")
                continue
            if pred["grid"] != grid:
                n_effective += 1
            if pred["game_over"]:
                continue
            new_path = path + [act]
            if is_goal_state(pred, pred["grid"]):
                plan = [normalize_action(a) for a in new_path]
                (WS / "plan.json").write_text(json.dumps(plan, indent=1))
                print(
                    f"BFS: goal in {len(plan)} step(s); expanded {expanded} nodes, "
                    f"{len(seen)} distinct states. Plan written to plan.json:"
                )
                print(" -> ".join(action_str(a) for a in plan))
                print('execute with: python tools/commit.py --plan plan.json')
                raise SystemExit(0)
            k = _key(pred["grid"])
            if k not in seen:
                seen.add(k)
                q.append((pred["grid"], new_path))
    print(
        f"BFS: search space exhausted with NO goal state reachable "
        f"({expanded} nodes, {len(seen)} distinct states; {n_actions_tried} action "
        f"applications, {n_effective} of which changed the grid)."
    )
    # Distinguish a degenerate model from a genuinely closed state graph — they need
    # completely different repairs, and the generic message conflates them.
    if n_effective == 0:
        print(
            "  DIAGNOSIS: your simulate() is a NO-OP — not one candidate action changes "
            "the grid. This is a modeling bug, not an unreachable goal. The search could "
            "never have succeeded. Fix simulate() so actions have effects (check that it "
            "reads the action dict correctly and returns a NEW grid), re-run backtest, "
            "then re-plan."
        )
    elif len(seen) <= 30:
        print(
            f"  DIAGNOSIS: the model admits only {len(seen)} reachable state(s) — the "
            f"state graph is nearly closed. Most likely your action set is too narrow "
            f"(define/extend candidate_actions) or simulate() treats legal moves as "
            f"blocked. Compare against the timeline: actions you really took should be "
            f"reproducible here."
        )
    else:
        print(
            "  DIAGNOSIS: the graph is genuinely explored and closed. Something real is "
            "missing from the model — an object, a state variable, or a transition "
            "(a portal, a carry/occupancy state, a composition of two mechanisms). "
            "Search cannot invent it. Design an experiment that would make the missing "
            "affordance observable: probe the things you assumed were decoration, and "
            "test mechanisms at their exact composing geometry."
        )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
