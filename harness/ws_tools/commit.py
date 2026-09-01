#!/usr/bin/env python3
"""commit_actions — the ONLY channel from thinking to real game actions.

Each action is first predicted with world_model.simulate, then executed for real.
Every real transition is appended to the timeline by the daemon. On the FIRST
misprediction the remaining plan is voided (execution stops) and the mismatch is
reported as a counterexample: fix world_model.py, re-run backtest, re-plan.
Execution also stops (without error) on level_up / win / game_over, since the
next grid is a new situation your plan did not see.

Every executed action costs score. RHAE per level = min((human/yours)^2, 1.15).

Usage:
  python tools/commit.py --actions '[{"name":"ACTION1"},{"name":"ACTION6","x":3,"y":40}]'
  python tools/commit.py --plan plan.json
  python tools/commit.py --actions '[{"name":"RESET"}]'      # restart current level
Optional: --reasoning "why this batch"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _lib import (
    WS,
    action_str,
    daemon,
    diff_cells,
    load_world_model,
    normalize_action,
    read_events,
    simulate_safe,
)

# --- degenerate-grinding guard -------------------------------------------------
# RHAE scores ACTIONS, not wall-clock. The failure mode this catches is an agent
# that stops modelling and starts sweeping coordinates: on one game a run spent
# 12,287 of its 13,604 actions on a single level (ACTION6 @x=59 x4387, @x=57
# x4289, plus 205 mid-level RESETs) and scored 81.39, while the same model with
# no harness at all won the game in 160 actions. Nothing in the loop escalated.
#
# The guard blocks only the OVERUSED actions, never the level as a whole, so a
# genuinely new plan always gets through and the agent can never be deadlocked.
# Thresholds are set from the recorded runs, not guessed. Across every run in this
# repo, the worst level of a run that still scored 100.00 cost 1,436 actions; every
# grinding run cost 7,559-46,990 on a single level. A 2,000-action floor sits in that
# gap, so the guard cannot fire on a game we already win.
# Verify with: python3 scripts/test_grind_guard.py
GRIND_MIN_LEVEL_ACTIONS = 2000
EXACT_REPEAT_MAX = 25    # same (name, x, y) on this level — one cell re-clicked 25x is not information
COARSE_REPEAT_MAX = 200  # same 4x4 cell block — catches raster sweeps that vary y
GRIND_PLAN_FRACTION = 0.6
RESET_THRASH_MAX = 60     # RESETs on one level; healthy runs never approach this
DISTINCT_ACTION_MIN = 40  # ...while cycling this few distinct actions = a dead end, not exploration
# Any rule that inspects the PROPOSED plan can be diluted: a batch that is 40% fresh
# coordinates passes the fraction test, and a raster sweep over a 64x64 grid supplies
# fresh cells almost indefinitely. Observed live -- with the fraction rule active, a
# one retry still reached 9,343 actions on one level. The ceiling below is the only
# composition-independent stop. Its escape hatch is the full reset the methodology
# already prescribes: that moves the game to level 0, which starts a fresh segment,
# so the agent is redirected, never deadlocked.
GRIND_HARD_CAP = 3000  # absolute fallback when the human baseline is unknown
# Baseline-relative ladder (after Retrodict's 300-action/2-reset escalation and
# Tycho's 5x-baseline hard stop; see reference/ for both, credited in NOTICE).
# By 2,000 actions on a 60-baseline level the score was gone ~1,900 actions ago;
# escalation has to fire while the level is still worth points.
ESCALATE_T1 = 1.5   # x this level's human baseline, or 2 self-RESETs
ESCALATE_T2 = 3.0
SCORE_FLOOR = 5.0   # x baseline: the level's score is ~gone past here (min((h/a)^2,1.15)
                    # at 5x is ~4%). v2 refused actions here, believing the official eval
                    # cut levels off at 5x. It does not: the server scored a 6,881-action
                    # run without complaint. Score here is a floor, not a wall — so v3
                    # informs and lets the agent keep learning. Efficiency on a learning
                    # attempt is worth nothing; only the final attempt is scored.
CLEANRUN_SLACK = 1.3  # planned actions per level must be <= this x baseline to restart after a WIN

ESCALATION_TEXT = """ESCALATION (level has cost {spent} actions vs human baseline {base}):
A human solves this level in {base} actions, so the rule you are missing is likely
SIMPLE — before adding machinery, ask what simpler mechanic would explain the
evidence, and do not defend your current model.
this level is not yielding to the current approach. Binding directive until it
completes, in priority order:
 1. Inventory in notes.md BOTH what the log leaves unexplained AND the reachable
    places or states you have never visited. Unexplored territory outranks new
    mechanic hypotheses.
 2. Promote your checked rules into world_model.py and verify it retrodicts every
    recorded frame of THIS level (python tools/backtest.py --level {level}).
 3. Search the certified model (bounded) for a route to the goal. A timed-out
    search was too big — never evidence that no route exists. If the search
    exhausts the space, something real is missing: frame-diff the animation
    residuals your model does not reproduce before enumerating more placements.
 4. If the rule you are missing is observable on an EARLIER level, go back for
    ground truth: a deliberate full restart (RESET with full_reset true, after a
    RESET) lets you replay modelled levels nearly free and run the decisive
    experiment where the answer is visible.
Do not repeat actions whose outcome you can already compute."""


def _level_baseline() -> tuple[int, int, int, int]:
    """(current level, this level's human baseline, actions spent on it, resets)."""
    st = daemon("/status")
    lvl = st.get("level", 0)
    bases = st.get("human_baseline_actions") or []
    base = bases[lvl] if lvl < len(bases) else 0
    evs = list(read_events())
    # Only the CURRENT attempt counts: a full reset starts a fresh scored run, so
    # it must also clear the ladder's counters — otherwise the hard stop re-fires
    # on the new attempt and the escape hatch escapes nothing (learned from a run
    # that proved the resulting deadlock exhaustively from the inside).
    start = 0
    for i, e in enumerate(evs):
        if e.get("full_reset"):
            start = i
    spent = resets = 0
    for e in evs[start:]:
        if e.get("prev_level", e.get("level")) == lvl and isinstance(e.get("action"), dict):
            spent += 1
            if e["action"].get("name") == "RESET":
                resets += 1
    return lvl, base, spent, resets


def _exact_key(a: dict):
    return (a.get("name"), a.get("x"), a.get("y"))


def _coarse_key(a: dict):
    x, y = a.get("x"), a.get("y")
    if x is None or y is None:
        return (a.get("name"), None, None)
    return (a.get("name"), x // 4, y // 4)


def _current_level_actions() -> list[dict]:
    """Actions executed since the last level change (the segment RHAE charges)."""
    evs = list(read_events())
    if not evs:
        return []
    cur = evs[-1]["level"]
    seg = []
    for e in reversed(evs):
        if e.get("level") != cur:
            break
        seg.append(e)
    seg.reverse()
    return [e["action"] for e in seg if isinstance(e.get("action"), dict)]


def check_not_grinding(plan: list[dict]) -> None:
    """Refuse a plan that is mostly re-running actions already proven fruitless."""
    from collections import Counter

    # Baseline-relative escalation: constructive, and only when stuck (always-on
    # anti-pruning text measurably taxes easy levels — Retrodict's own regression).
    try:
        lvl, base, spent, resets = _level_baseline()
    except Exception:
        lvl, base, spent, resets = 0, 0, 0, 0
    # Consecutive-RESET guard (Tycho: invalid, costs nothing, actionable message).
    # Bypassed by an explicit {"full_reset": true} on the RESET — a DELIBERATE
    # double-RESET is the engine's full-game restart and is always legal (v2 only
    # unlocked it past the hard stop, so agents burned doomed levels just to
    # reach the escape). Guards must never cover the whole action space between
    # them: the flagged reset is the permanent gap.
    last = None
    for e in read_events():
        if isinstance(e.get("action"), dict):
            last = e["action"].get("name")
    deliberate = bool(plan and plan[0].get("name") == "RESET"
                      and plan[0].get("full_reset"))
    if (plan and plan[0].get("name") == "RESET" and last == "RESET"
            and not deliberate):
        raise SystemExit(
            "REFUSED (no action charged): the previous committed action was already "
            "a RESET. A second consecutive RESET replays the same fresh state at "
            "full price — and resetting an already-fresh level restarts the ENTIRE "
            "game. If that is what you want, say so explicitly: commit "
            '[{"name": "RESET", "full_reset": true}]. Otherwise observe and commit '
            "something else.")

    # Post-WIN restart gate: restarting after a WIN is the one-shot repair whose
    # efficiency IS the final score, so it must be certified first. Write
    # cleanrun.json = {"programs": [[action, ...], ...]} — the FULL action list
    # per level, not just counts. v3 checked only counts and an agent certified
    # numbers its world model could not deliver (planned 162, executed a 40.3);
    # v4 verifies the plan itself: lengths within CLEANRUN_SLACK x baseline AND,
    # when the world model exposes the threaded-state API (init_state/step_state,
    # optional outcome), each level's program must simulate to level_up/win/level_complete in
    # the certified model. Writing the file is free and ungated, so no
    # action-space coverage issue.
    try:
        st_now = daemon("/status")
    except Exception:
        st_now = {}
    if plan and plan[0].get("name") == "RESET" and st_now.get("state") == "WIN":
        bases_all = st_now.get("human_baseline_actions") or []
        import math
        try:
            _cr = json.loads((WS / "cleanrun.json").read_text())
            programs = _cr.get("programs")
            if programs is None and isinstance(_cr.get("planned_actions"), list):
                programs = "COUNTS_ONLY"
        except Exception:
            programs = None
        problems = []
        if programs == "COUNTS_ONLY":
            problems.append("cleanrun.json now needs programs (the full action list "
                            "per level), not planned_actions counts — a count "
                            "certifies ambition, a program certifies a plan")
        elif not isinstance(programs, list) or len(programs) != len(bases_all):
            problems.append(f"cleanrun.json must contain programs: a list of "
                            f"{len(bases_all)} action lists (one per level)")
        else:
            for i, (prog, b) in enumerate(zip(programs, bases_all)):
                cap = math.ceil(CLEANRUN_SLACK * b)
                if not isinstance(prog, list) or not all(isinstance(a, dict) for a in prog):
                    problems.append(f"level {i}: program must be a list of action dicts")
                elif len(prog) > cap:
                    problems.append(f"level {i}: program has {len(prog)} actions > cap "
                                    f"{cap} (baseline {b} x {CLEANRUN_SLACK})")
            if not problems:
                # Correctness pass: simulate each program in the certified model
                # when the threaded-state API exists. A program that does not
                # reach level_up/win in your OWN model cannot be worth the run.
                try:
                    mod = load_world_model()
                except Exception:
                    mod = None
                if (mod is not None and hasattr(mod, "init_state")
                        and hasattr(mod, "step_state") and hasattr(mod, "outcome")):
                    # Ground each simulation in the OBSERVED level-start grid
                    # from the ledger — an imagined start certifies nothing.
                    starts = {}
                    prev = None
                    for e in read_events():
                        lv = e.get("level")
                        if lv is not None and lv != prev and e.get("grid") is not None:
                            starts.setdefault(lv, e["grid"])
                            prev = lv
                    for i, prog in enumerate(programs):
                        try:
                            g0 = starts.get(i)
                            state = mod.init_state(
                                [r[:] for r in g0] if g0 else None, i)
                            reached = False
                            for a in prog:
                                state = mod.step_state(state, dict(a))
                                out = mod.outcome(state)
                                if out in ("level_up", "win", "level_complete"):
                                    reached = True
                                    break
                            if not reached:
                                problems.append(
                                    f"level {i}: program does not reach level_up/win "
                                    "in YOUR OWN world model — fix the model or the plan")
                        except Exception as exc:
                            problems.append(f"level {i}: simulation crashed "
                                            f"({type(exc).__name__}: {exc}) — a plan "
                                            "your model cannot even run is not certified")
                else:
                    print("cleanrun gate: world model lacks init_state/step_state/"
                          "outcome — length checks only. Consider adding the threaded "
                          "API so your plan can be verified before you spend the run.",
                          flush=True)
        if problems:
            raise SystemExit(
                "REFUSED (no action charged): you have WON — restarting now begins "
                "the attempt that becomes your score, and your plan is not yet "
                "efficient enough to spend it. Fix and retry:\n  " +
                "\n  ".join(problems) +
                "\nDerive tighter programs from your world model first; the score "
                "per level is min((baseline/actions)^2, 1.15).")
        print(f"CLEAN RUN ARMED: all {len(bases_all)} level programs certified "
              f"within {CLEANRUN_SLACK}x baseline. Execute exactly what you "
              "certified.", flush=True)

    if base > 0:
        if spent >= SCORE_FLOOR * base:
            print(f"SCORE FLOOR: {spent} actions on level {lvl} vs baseline {base} — "
                  "this attempt's score on this level is effectively gone (~4% at 5x). "
                  "That is fine: only your FINAL attempt is scored. Stop protecting "
                  "this attempt, learn whatever the level still has to teach, and "
                  "plan the certified clean run that will replace it. A deliberate "
                  'full restart is [{"name": "RESET", "full_reset": true}] after a RESET.',
                  flush=True)
        if spent >= ESCALATE_T2 * base or (spent >= ESCALATE_T1 * base and resets >= 4):
            print(ESCALATION_TEXT.format(spent=spent, base=base, level=lvl), flush=True)
            print("(tier 2: also assume one of your rules is WRONG — prefer plans that "
                  "reach never-before-seen board configurations.)", flush=True)
        elif spent >= ESCALATE_T1 * base or resets >= 2:
            print(ESCALATION_TEXT.format(spent=spent, base=base, level=lvl), flush=True)

    all_past = _current_level_actions()
    past = [a for a in all_past if a.get("name") != "RESET"]
    if len(past) < GRIND_MIN_LEVEL_ACTIONS:
        return
    exact = Counter(_exact_key(a) for a in past)
    coarse = Counter(_coarse_key(a) for a in past)

    # Reset thrash is its own grind, and stripping RESET before the fraction test
    # left it an open escape: a RESET-only plan filtered down to nothing and was
    # waved through. Observed live -- the guard fired once at 2,003 actions
    # and the level still reached 3,082, cycling 21 distinct actions and 237 RESETs.
    if len(past) >= GRIND_HARD_CAP and any(a.get("name") != "RESET" for a in plan):
        print(
            f"GRIND GUARD (hard cap): this level has cost {len(past)} actions, past the "
            f"{GRIND_HARD_CAP} ceiling. Learning is free score-wise (only the final "
            "attempt is scored) but NOT budget-wise — the run's action budget is "
            "finite, and coordinate-sweeping at this volume has never produced a "
            "model. This is the only cost-based refusal in the harness.\n"
            "Mid-level RESET will not help either — it replays the same dead end.\n"
            "Do a FULL reset and go back for ground truth: replay the levels you DO "
            "understand to re-observe how this mechanic is introduced, fix "
            "world_model.py, re-run tools/backtest.py until it is green, and only then "
            "come back to this level with a plan you can predict.",
            flush=True)

    resets = sum(1 for a in all_past if a.get("name") == "RESET")
    distinct = len({_exact_key(a) for a in past})
    if resets >= RESET_THRASH_MAX and distinct <= DISTINCT_ACTION_MIN:
        print(
            f"GRIND WARNING (reset thrash): this level has already cost {len(all_past)} "
            f"actions including {resets} RESETs, cycling only {distinct} distinct "
            f"actions. Restarting the level again replays the same dead end.\n"
            "Stop and re-theorize: the level is not explained by your world model. "
            "Update world_model.py against the counterexamples already in the "
            "timeline, re-run tools/backtest.py, and plan inside the corrected "
            "model. If you cannot explain it, full-reset and replay the levels you "
            "DO understand to re-observe how this mechanic is introduced.",
            flush=True)

    proposed = [a for a in plan if a.get("name") != "RESET"]
    if not proposed:
        return
    stale = [
        a for a in proposed
        if exact[_exact_key(a)] >= EXACT_REPEAT_MAX or coarse[_coarse_key(a)] >= COARSE_REPEAT_MAX
    ]
    if len(stale) < GRIND_PLAN_FRACTION * len(proposed):
        return

    worst = exact.most_common(3)
    detail = ", ".join(f"{n[0]}@({n[1]},{n[2]})x{c}" for n, c in worst)
    print(
        f"GRIND WARNING: {len(stale)}/{len(proposed)} proposed actions repeat moves already "
        f"tried on this level, which has already cost {len(past)} actions.\n"
        f"Most repeated so far: {detail}.\n"
        "Repeating them cannot produce new information, and every one costs score "
        "(RHAE counts actions, not time). Do ONE of these instead:\n"
        "  1. Re-theorize: this level is not explained by your world model. Update "
        "world_model.py against the counterexamples already in the timeline, re-run "
        "tools/backtest.py, and plan inside the corrected model.\n"
        "  2. Go back for ground truth: full-reset and replay the levels you DO "
        "understand to re-observe how this mechanic is introduced.\n"
        "  3. Propose genuinely different actions — any plan that is not mostly "
        "repeats is accepted immediately.\n"
        "Brute-forcing coordinates is never the answer; a bare agent with no harness "
        "beats a grinding one on exactly these games.",
        flush=True)


def build_plan(raw: list[dict]) -> list[dict]:
    """Normalize a committed plan. A RESET keeps its deliberate full_reset flag:
    v5 rebuilt every RESET as a bare {"name": "RESET"}, which silently dropped
    the flag and made the documented consecutive-RESET escape hatch unreachable
    (139 refusals in a single run)."""
    return [normalize_action(a) if a.get("name") != "RESET"
            else ({"name": "RESET", "full_reset": True} if a.get("full_reset") else {"name": "RESET"})
            for a in raw]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--actions", type=str, default=None)
    ap.add_argument("--plan", type=str, default=None)
    ap.add_argument("--reasoning", type=str, default="")
    args = ap.parse_args()

    if bool(args.actions) == bool(args.plan):
        raise SystemExit("provide exactly one of --actions or --plan")
    raw = json.loads(args.actions if args.actions else Path(args.plan).read_text())
    if not isinstance(raw, list) or not raw:
        raise SystemExit("actions must be a non-empty JSON list")
    plan = build_plan(raw)
    # Transport safety: the local engine clips an off-grid ACTION6, but the
    # competition API rejects it with a 400 — so an off-grid click makes the whole
    # trace non-replayable. Refuse it here, before anything is charged. (Found the
    # hard way: two otherwise-perfect board traces replayed at 33/27 because of
    # one such click each.)
    for i, a in enumerate(plan):
        if a.get("name") == "ACTION6":
            x, y = a.get("x"), a.get("y")
            if not (isinstance(x, int) and isinstance(y, int) and 0 <= x <= 63 and 0 <= y <= 63):
                raise SystemExit(
                    f"REFUSED (no action charged): plan[{i}] ACTION6 x={x} y={y} is "
                    "outside the 64x64 grid (valid 0..63). The local engine would clip "
                    "this but the official replay path rejects it, making the recorded "
                    "trace non-replayable. Click a real cell.")


    check_not_grinding(plan)

    mod = load_world_model()
    st = daemon("/status")
    if st["state"] == "WIN":
        if not (plan and plan[0].get("name") == "RESET"):
            raise SystemExit("game already WON — nothing to do")

    if st["state"] == "GAME_OVER" and plan[0]["name"] != "RESET":
        raise SystemExit(
            "state is GAME_OVER: the game only accepts RESET now. Any other action "
            "wastes score for a junk frame. Commit a RESET first (it restarts the "
            "current level)."
        )
    grid = st["grid"]

    executed = 0
    for idx, act in enumerate(plan):
        if act["name"] == "RESET":
            ev = daemon("/reset", {})
            executed += 1
            print(f"[{idx}] RESET -> level {ev['level']}, state {ev['state']}")
            grid = ev["grid"]
            continue

        pred = None
        if grid is not None:
            try:
                pred = simulate_safe(mod, grid, act)
            except Exception as exc:
                print(
                    f"[{idx}] {action_str(act)}: world_model.simulate raised "
                    f"{type(exc).__name__}: {exc} — executing without prediction"
                )

        ev = daemon("/act", dict(act, reasoning=args.reasoning))
        if "error" in ev:
            raise SystemExit(f"[{idx}] {action_str(act)}: daemon error: {ev['error']}")
        executed += 1
        real_grid = ev["grid"]

        if ev["win"]:
            print(f"[{idx}] {action_str(act)} -> *** WIN *** all {ev['win_levels']} levels complete")
            break
        if ev["level_up"]:
            predicted = " (predicted)" if pred and pred["level_up"] else " (NOT predicted by model)"
            print(
                f"[{idx}] {action_str(act)} -> LEVEL UP{predicted}: now level "
                f"{ev['level']}/{ev['win_levels']}. Remaining plan discarded — observe the new level."
            )
            break
        if ev["game_over"]:
            predicted = " (predicted)" if pred and pred["game_over"] else " (SURPRISE)"
            print(
                f"[{idx}] {action_str(act)} -> GAME OVER{predicted}. Remaining plan discarded. "
                f"Commit a RESET to retry the level; update the model with what killed you."
            )
            break

        if pred is not None:
            from _lib import claimed_fraction
            cov = claimed_fraction(pred["grid"]) if pred.get("grid") else 0.0
            if cov == 0.0:
                # Vacuous prediction: abstaining everywhere proves nothing (Tycho
                # grades this as "not evidence of a correct model"). Execute, but
                # say so — the agent should know it is flying blind.
                print(f"[{idx}] {action_str(act)}: prediction abstains on every cell "
                      f"(coverage 0%) — executing UNVERIFIED")
                pred = None
        if pred is not None:
            if pred["level_up"] or pred["game_over"] or pred["win"]:
                print(
                    f"[{idx}] {action_str(act)} -> SURPRISE: model predicted "
                    f"level_up={pred['level_up']} game_over={pred['game_over']} "
                    f"win={pred['win']} but none happened. Plan voided at step {idx}; "
                    f"{len(plan) - idx - 1} action(s) not executed."
                )
                print("Fix world_model.py, re-run backtest, re-plan.")
                raise SystemExit(2)
            d = diff_cells(pred["grid"], real_grid)  # abstained (None) cells never mismatch
            if d:
                sample = ", ".join(f"({x},{y}) pred={a} real={b}" for x, y, a, b in d[:15])
                more = f" (+{len(d) - 15} more)" if len(d) > 15 else ""
                print(
                    f"[{idx}] {action_str(act)} -> SURPRISE: {len(d)} cells mispredicted: "
                    f"{sample}{more}"
                )
                print(
                    f"Plan voided at step {idx}; {len(plan) - idx - 1} action(s) not "
                    f"executed. This transition is now event {ev['i']} in the timeline — "
                    f"a counterexample. Fix world_model.py, re-run backtest, re-plan."
                )
                raise SystemExit(2)

        changed = ev.get("prev_grid_changed_cells")
        cov_note = ""
        if pred is not None:
            from _lib import claimed_fraction
            c = claimed_fraction(pred["grid"])
            cov_note = " (predicted exactly)" if c >= 0.999 else f" (claimed cells correct, coverage {c:.0%})"
        note = ""
        if changed == 0:
            # Hedged no-op message (Tycho): absence of visible change is not
            # absence of effect — hidden counters/state can still move.
            note = ", no visible change (hidden state may still have changed)"
        print(f"[{idx}] {action_str(act)} -> ok{cov_note}"
              + (f", {changed} cells changed" if changed else note))
        grid = real_grid

    st = daemon("/status")
    print(
        f"executed {executed}/{len(plan)} action(s). state={st['state']} "
        f"level={st['level']}/{st['win_levels']} total_actions={st['action_count']}"
    )


if __name__ == "__main__":
    main()
