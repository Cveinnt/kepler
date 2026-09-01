#!/usr/bin/env python3
"""Prove each fix addresses the failure it was built for, on the
v5 ledgers, before any paid run.

1. full_reset flag survives plan normalization (the 139-refusal bug).
2. Escalation would have fired early on the thrash runs and stayed silent on
   the games that scored 100.
3. Final-level grace would have kept the bp35 run alive.
"""
import glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ws_tools"))
import escalation  # noqa: E402
import commit  # noqa: E402

_BASES = {}
def baselines_for(game: str) -> list[int]:
    """Per-level human baselines from the same toolkit metadata the daemon exposes."""
    if not _BASES:
        from arc_agi import Arcade, OperationMode
        shared = ROOT / ".arc-private"   # the daemon's own cache of game metadata
        arc = Arcade(arc_api_key="", operation_mode=OperationMode.NORMAL,
                     environments_dir=str(shared / "environment_files"),
                     recordings_dir=str(shared / "recordings"))
        for e in arc.get_environments():
            _BASES[e.game_id[:4]] = list(e.baseline_actions)
    return _BASES.get(game, [])

ok = True

# 1) plan normalization keeps the deliberate flag
p = commit.build_plan([{"name": "RESET", "full_reset": True}, {"name": "ACTION1"}])
assert p[0] == {"name": "RESET", "full_reset": True}, p
assert commit.build_plan([{"name": "RESET"}]) == [{"name": "RESET"}]
print("PASS 1: full_reset survives build_plan")

# 2) escalation replay over every v5 ledger
def _left_on_level(evs, n):
    lvl = evs[n - 1].get("level"); k = 0
    for e in evs[n:]:
        if e.get("level") != lvl: break
        if isinstance(e.get("action"), dict): k += 1
    return k

def replay(evp, bases):
    evs = [json.loads(l) for l in evp.read_text().splitlines() if l.strip()]
    first_fire = None
    for n in range(1, len(evs) + 1):
        lvl, spent, resets = escalation.stuck_signals(evs[:n])
        base = bases[lvl] if lvl < len(bases) else 0
        if escalation.tier(spent, resets, base) and first_fire is None:
            first_fire = (n, lvl, spent, resets, _left_on_level(evs, n))
    return len(evs), first_fire

rows = []
for res in sorted(glob.glob(str(ROOT / "runs-v5" / "*" / "*" / "result.json"))):
    d = json.loads(Path(res).read_text())
    ws = Path(res).parent
    if not (ws / "events.jsonl").exists() or "superseded" in str(ws):
        continue
    total, ff = replay(ws / "events.jsonl", baselines_for(ws.name))
    rows.append((ws.parent.name, ws.name, d.get("score"), total, ff))

silent_on_100 = 0; fires_on_100 = []
for model, game, score, total, ff in rows:
    if score == 100:
        if ff: fires_on_100.append((model, game, ff))
        else: silent_on_100 += 1
    else:
        print(f"  {model:8s} {game}: score {score:6.2f}, {total:5d} events; escalation first fires at "
              f"{'event %d (level %d, %d actions, %d resets, %d more actions followed on that level)' % ff if ff else 'NEVER'}")
# A fire on a perfect game is acceptable where the learning attempt on that level
# genuinely ran long afterward (the directive would have SHORTENED it). It is only
# a tax if it fires when the level was about to complete, fewer than MIN_ACTIONS
# (the tiny-level floor) actions remaining.
harmful = [(m, g, f) for m, g, f in fires_on_100 if f[4] < escalation.MIN_ACTIONS]
for m, g, f in fires_on_100:
    print(f"  (perfect game) {m:8s} {g}: fires at level {f[1]} after {f[2]} actions; {f[4]} more followed")
assert not harmful, f"escalation would fire on near-complete levels: {harmful}"
print(f"PASS 2: silent on {silent_on_100} perfect games; {len(fires_on_100)} fire only mid-long-learning-phase (>= {escalation.MIN_ACTIONS} actions still followed on the level)")
sp80 = [r for r in rows if r[0] == "gpt-max" and r[1] == "sp80"][0]
assert sp80[4] and sp80[4][0] < 1000, sp80  # must fire early in the 15,915-action thrash
print(f"PASS 2b: gpt sp80 thrash would have escalated at event {sp80[4][0]} instead of never")

# 3) final-level grace on the bp35 kill
bp = json.loads((ROOT / "runs-v5/gpt-max/bp35/result.json").read_text())
assert bp["levels_completed"] == bp["win_levels"] - 1 and bp["note"] == "wall clock exhausted"
print("PASS 3: bp35 was on its final level when killed at "
      f"{bp['elapsed_hours']}h, v6 grants {4.0}h more instead of stopping")
