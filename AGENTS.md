# AGENTS.md

Conventions for coding agents (and humans) working in this repo. This file is about
*this* repository's own development — not to be confused with
`harness/directive.md`, which is the system directive the harness copies into each
*game-playing* workspace as that workspace's own `AGENTS.md`/`CLAUDE.md`. Don't conflate
the two: changes here affect the harness's developers; changes to `harness/directive.md`
change what every future game-playing agent is told to do.

## Layout, at a glance

- `harness/` — the harness itself (daemon, outer loop, sweep/score orchestration, watch).
  See `DESIGN.md` for architecture.
- `harness/ws_tools/` — **copied verbatim** into every run's workspace as `tools/` by
  `run_game.py:setup_workspace()`. These are not imported as a library; they are files
  that get literally copied out of the repo at run start. If you edit one mid-sweep, the
  already-running workspaces keep their stale copy — new runs get the new version. Keep
  them stdlib-only (see `ws_tools/_lib.py`'s own docstring) since they run inside the
  agent's workspace, not this repo's venv.
- `harness/directive.md` — the game-playing agent's prompt/contract. Treat edits here as
  changing the *methodology itself*, not a docs tweak — it defines the
  observe/deliberate/plan/execute/record loop and the tool contracts. Changes here
  invalidate comparisons with prior runs.
- `runs/` — **generated experiment data, not source.** One directory per
  `<model>/<game>/`: workspace files the agent wrote (`world_model.py`, `notes.md`),
  the append-only ground-truth `events.jsonl`, `scorecard.json`, `result.json`, and logs.
  Git-ignored; never hand-edit or delete run output, and never commit it. If you need to
  inspect a run, read it — `harness/watch.py` and `harness/score.py` are the intended
  tools for that.
- `environment_files/`, `.venv/`, `reference/`, `*.log` — also git-ignored. `reference/`
  holds vendored clones of adjacent projects (`ARC-AGI-3-Agents`, the original site,
  etc.) kept for study; it isn't part of this codebase and shouldn't be edited or cited
  as if it were.

## Hard rules

- **Never modify files under an active run's workspace** (`runs/<model>/<game>/`) except
  through the harness's own tools. `events.jsonl` is append-only ground truth written
  only by `daemon.py`; hand-editing it invalidates that run's backtest/score.
- **Before editing anything under `harness/`, check for live processes first**
  (`ps aux | grep -E 'run_game|sweep|daemon.py|watch.py'`). Sweeps run unattended for
  hours; `sweep.py` and `run_game.py` invoke the *installed* module at process start, so
  editing `harness/*.py` while a sweep is running can affect subsequently-spawned
  sessions of that same run in surprising ways. When in doubt, let in-flight sweeps
  finish (or confirm with whoever started them) before changing harness behavior.
- **Functional changes to `harness/` are high-stakes**: they change what "the Kepler
  harness reproduction" means and break comparability with prior `runs/`. Prefer
  formatting/doc-only changes unless a behavior change is explicitly requested; if you
  do change behavior, say so plainly (commit message + `DESIGN.md` if the architecture
  moved) rather than letting it look like a no-op.
- **Do not run the harness, a sweep, or anything that invokes `codex`/`claude` as part
  of a docs/packaging/hygiene task.** Those calls cost real tokens/provider quota. If a
  task genuinely requires a live run, say so and get explicit confirmation first.
- **Secrets**: no API keys belong in this repo. The `arc-agi` toolkit runs games locally
  with an anonymous key; `codex`/`claude` CLI auth lives outside the repo. If you ever
  see a credential in a diff, stop and flag it instead of committing it.

## Conventions

- Python: stdlib-first in `harness/` and especially in `ws_tools/` (copied into
  workspaces that don't get the repo's venv). `arc-agi` + `requests` are the only
  pinned third-party deps (`pyproject.toml`).
- Scripts are argparse CLIs with a usage example in the module docstring — follow that
  pattern for new tools (see any file under `harness/` for the shape).
- Game IDs are the 4-character public-set codes in `harness/score.py:GAMES`; that list
  is the single source of truth for "which 25 games."
- See `CONTRIBUTING.md` for the change-review workflow and `reproduction.md` for how the
  headline numbers are meant to be reproduced end to end.
