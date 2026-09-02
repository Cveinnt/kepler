# Kepler design

Kepler treats each ARC-AGI-3 game as experimental science. The agent observes
the environment, writes an executable theory, tests that theory against the
entire recorded history, and certifies an action program. A mechanical executor
then plays the scored attempt without a model in the loop.

This document describes **Kepler 1.0.0**. Earlier experiments are named stages
in [`RESULTS.md`](RESULTS.md), not separate public software releases.

## Release contract

- One frozen configuration per model.
- One retained run per game. No score-conditioned reruns.
- Zero game-specific priors in every agent-visible source file, enforced in CI.
- Append-only action ledgers and adversarial session-log audits.
- Exact official replay scorecards for both release boards.
- Public-set results only. No held-out or private-set claim.

Canonical scores, cards, action counts, and token totals live in
[`release.json`](release.json). The trace dataset is a required part of the
release contract but is not public yet.

## Environment

Kepler uses the `arc-agi` Python toolkit to run the 25 public ARC-AGI-3 games.
Each environment exposes a 64 by 64 grid, legal actions, animation frames,
level state, and human baseline action counts. RHAE scores completed levels by
relative action efficiency, weights later levels more heavily, and applies a
completion cap.

The games run locally after a disclosed startup handshake by the toolkit. The
agent's only HTTP traffic is to Kepler's localhost daemon.

## Architecture

```text
harness/
  daemon.py        owns the environment and append-only event ledger
  run_game.py      creates workspaces and drives agent sessions
  sweep.py         schedules a full board
  score.py         aggregates official per-game scorecards
  directive.md     agent method and behavioral contract
  ws_tools/
    observe.py     reads state without acting
    render.py      exposes saved visual and animation frames
    backtest.py    replays the world model against recorded history
    bfs.py         searches inside the executable model
    commit.py      prediction-checks every real action
    cleanrun.py    certifies and mechanically executes the scored program
    escalation.py detects stuck learning attempts

workspace/<game>/
  world_model.py   agent-authored executable theory
  notes.md         checked claims, assumptions, and experiment record
  cleanrun.json    certified per-level action programs
  events.jsonl     append-only environment ground truth
  sessions/        raw agent session record
  tools/           frozen copy of the workspace tools
```

## Core loop

1. **Observe.** `observe.py` returns current state and ledger-derived diffs.
   Visual mode also preserves every animation frame as a rendered image.
2. **Model.** The agent records checked and assumed claims in `notes.md` and
   implements the current theory in `world_model.py`.
3. **Retrodict.** `backtest.py` replays the theory over the recorded history.
   A green backtest means the claimed model reproduces those transitions. It
   does not prove the model is complete.
4. **Plan.** The agent searches the executable model with `bfs.py` or its own
   bounded search.
5. **Act.** `commit.py` predicts each proposed transition, sends the real
   action, and voids the remaining plan at the first mismatch.
6. **Certify.** After learning, the agent writes full per-level programs to
   `cleanrun.json`.
7. **Replay.** `cleanrun.py` checks the program and executes it mechanically.
   A mismatch stops the run rather than allowing the model to improvise inside
   the scored attempt.

Each agent session runs in its own process group. The outer loop samples the
aggregate resident memory of the session process tree every 0.5 seconds and
stops the group if it exceeds the default 8 GB limit. It also stops the whole
group on timeout. If memory monitoring itself fails, the run aborts without a
result so an unenforced safety control cannot be mistaken for a working one.
This protects the host from a repeated runaway search, but it is not OS-level
containment and does not change the scoring or agent-visible method.

## World-model contract

```python
def simulate(grid, action) -> {
    "grid": next_grid,
    "level_up": bool,
    "game_over": bool,
    "win": bool,
}

def is_goal(grid) -> bool
def candidate_actions(grid) -> list[dict]
```

`is_goal` and `candidate_actions` are optional. Models with hidden state can
expose the threaded-state interface documented in `harness/directive.md`.
Partial pixel predictions are allowed, but vacuous coverage is rejected.

## Integrity boundaries

- The daemon alone writes `events.jsonl`.
- Agent-visible files contain no public game IDs or per-game hints.
- Environment implementations live outside the agent workspace.
- Mutating actions must pass through `commit.py` or the certified mechanical
  executor.
- `scripts/audit_integrity.py` scans session records for source reads, direct
  daemon mutation, score writes, tool edits, ledger anomalies, and external
  network use.
- `scripts/verify_scores.py` recomputes scored action counts from the ledger and
  rejects any level charged fewer actions than its history records.
- `tests/test_tool_smoke.py` invokes every workspace tool. This exists because
  a broken planner was previously masked by agents that wrote replacement
  searches and continued winning.

Outcome integrity and tool integrity are separate claims. Kepler checks both.

## Reproduction boundary

Official replay establishes that the recorded action programs still produce
the reported public-set scores on ARC Prize's replay path. It is not an
independent rerun of stochastic agent learning. Fresh agent campaigns may vary
because models, providers, and sampling drift.

See [`reproduction.md`](reproduction.md) for exact commands and
[`INTEGRITY.md`](INTEGRITY.md) for the threat model, incidents, and known
limits.
