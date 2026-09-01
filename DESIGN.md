# Kepler — Design

> Historical note: Kepler began as an independent implementation of the
> executable-world-model approach and has since diverged substantially (v5 certify-then-replay,
> v7 visual mode, v8 transport safety). Sections below describe the v1-era
> design; see RESULTS.md for the current architecture ladder.

An independently designed harness that has frontier
models play ARC-AGI-3 like physicists — encode the game mechanism as an executable
`step()` program, certify it against the full recorded interaction history, plan inside
it with BFS, and act only through a single guarded channel.

Targets (self-reported on the 25 public games, RHAE):
- Claude Opus + Fable fallback pairing: **98.98**
- GPT-5.6 Sol xhigh + max fallback pairing: **95.35**
- Fallback rule: primary model runs every game; games scoring < 80 are rerun with the
  secondary model; the higher per-game score is retained (= `max` across runs, which is
  exactly how the local scorecard aggregates multiple runs of one game).

## Environment

`arc-agi` PyPI toolkit (same one `arcprize/ARC-AGI-3-Agents` v0.9.3 uses):
- Runs all 25 public games **locally** (`LocalEnvironmentWrapper`), anonymous API key OK.
- `env.step(GameAction, data={x,y})`, `env.reset()` → `FrameDataRaw`
  (`frame`: list of 64×64 grids (animation), `state`, `levels_completed`, `win_levels`,
  `available_actions`).
- Official RHAE scoring implemented locally in `arc_agi.scorecard`
  (per-level `min((baseline/actions)² × 100, 115)`, level-index weights 1..n,
  completion cap, per-game max across runs). Human `baseline_actions` per level ship in
  environment metadata.

## Architecture

```
harness/
  daemon.py      # per-run HTTP daemon: owns the env + append-only events.jsonl timeline
  run_game.py    # outer loop: workspace setup, daemon, CLI-agent sessions, result.json
  score.py       # cross-game RHAE aggregation + fallback pairing
  directive.md   # the agent's system directive
  ws_tools/      # tools copied into each workspace
    observe.py   # current grid (hex render), diff vs previous, status  [read-only]
    backtest.py  # replay world_model.simulate over the ENTIRE events.jsonl
    bfs.py       # search inside the certified model (simulate + is_goal)
    commit.py    # THE ONLY channel to the env; per-step predict-check; voids plan on
                 # first mismatch and reports the counterexample
workspace/<game>-<model>/   # the CLI agent's cwd
  world_model.py  # agent-edited theory: simulate(grid, action) -> {grid, level_up, ...}
  notes.md        # agent-edited lab notebook ("the agent's weights")
  events.jsonl    # append-only ground truth (written only by the daemon)
  tools/ -> ws_tools copied in
```

### The core loop (as enforced here)

- **observe → deliberate → execute → record**: the CLI agent (codex exec / claude -p)
  runs inside the workspace. It edits `world_model.py` + `notes.md`, runs
  `python tools/backtest.py` (certify), `python tools/bfs.py` (plan), and
  `python tools/commit.py` (execute). The daemon appends every real transition to
  `events.jsonl` — the agent cannot alter history.
- **Reality outranks the model**: `commit.py` predicts each next grid with the current
  `world_model.py` before sending the action; on the first mismatched cell set, the
  remaining plan is discarded and the mismatch is returned as a counterexample.
- **Backtest semantics** (matches the site): exact grid match on non-terminal steps;
  `level_up` / `game_over` / `win` flags on every step; level-transition and reset steps
  compare flags only (the model cannot know the next level's layout).

### World-model contract (documented in the directive)

```python
def simulate(grid, action) -> {"grid": g2, "level_up": bool, "game_over": bool, "win": bool}
def is_goal(grid) -> bool            # optional; default BFS goal = predicted level_up
def candidate_actions(grid) -> [..] # optional; needed for click (ACTION6) games
```

### Model driver

- GPT: `codex exec -m gpt-5.6-sol -c model_reasoning_effort=xhigh` (fallback: `max`),
  sessions continued with `codex exec resume`.
- Claude: `claude -p --model opus / fable`, continued with `--continue`.
- One long-lived session per game; the outer loop re-invokes with current status until
  WIN or budget (actions / wall-clock / sessions) is exhausted.

### Scoring

Per-run scorecards come from the local `arc_agi` ScorecardManager (official formula).
`score.py` merges runs per game (max), applies the <80 fallback rule, and reports the
benchmark average across all 25 games for each pairing.
