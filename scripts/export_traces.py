#!/usr/bin/env python3
"""Package completed runs into a HuggingFace-ready traces/ dataset. Stdlib only.

Reads runs/<model>/<game>/ (never writes there) for every run that has a
result.json, and produces:

  traces/
    README.md                     dataset card (schema description + counts)
    runs.jsonl                    one row per run: result + scorecard + the
                                  agent's full notes.md and world_model.py text
    events/<model>/<game>.jsonl.gz  one row per recorded transition, with
                                    model/game columns added

Both jsonl files load directly with `datasets.load_dataset("json", ...)` or
plain gzip+json. Grids are 64x64 int lists and dominate the size; --compact N
keeps the grid only on every Nth event plus all "interesting" events (resets,
level_up, game_over, win, and each run's final event) and sets it to null
elsewhere (grid_stripped=true), while always keeping every action and flag.

Usage:
  python3 scripts/export_traces.py                          # all completed runs
  python3 scripts/export_traces.py --model gpt-xhigh --game ft09 --game lp85
  python3 scripts/export_traces.py --compact 10             # slim grids
  python3 scripts/export_traces.py --out /tmp/traces --runs-root runs
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATASET_CARD = """\
---
license: mit
pretty_name: Kepler — ARC-AGI-3 agent trace corpus
tags:
  - arc-agi-3
  - agents
  - world-models
  - game-playing
  - reasoning
configs:
  - config_name: runs
    data_files: runs.jsonl
  - config_name: events
    data_files: events/*/*.jsonl.gz
---

# Kepler — ARC-AGI-3 agent trace corpus

Complete, replayable traces from Kepler, an open-source agent harness, on the 25 public
[ARC-AGI-3](https://arcprize.org/arc-agi/3/) games, inspired by
published executable-world-model work (Tycho, baseline1) and
independently implemented: a CLI coding agent
(codex / claude) that encodes its theory of each game as an executable
`world_model.py`, certifies it against the full recorded interaction history,
plans with BFS inside the certified model, and acts through a single guarded
channel that voids the plan on the first misprediction.

Self-reported RHAE (official local `arc-agi` scorecard): **98.30** (Claude
Opus + Fable pairing) and **95.51** (GPT-5.6 Sol xhigh + max pairing), vs the
post's 98.98 / 95.35. Not independently verified; see the harness repository
for methodology and caveats.

**Both numbers use a per-game best-of-2 fallback** (a game scoring under 80 is
re-run with a second model and the higher score kept), which ARC Prize's
president has publicly criticised as feeding score information back into the
system. Without it, single-config scores are **97.78** (Claude Opus) and
**84.20** (GPT-5.6 Sol xhigh). Use the single-config numbers when comparing
systems.

**Public-set scores are not a measure of AGI progress.** The ARC-AGI-3
technical report (§4.3.1) says so explicitly and ships a human-replay harness
scoring 100% to make the point. This dataset supports a reproduction question —
does a published result hold up — not a capability claim.

**The ablation is RETRACTED — read this before citing anything about the
harness's contribution.** We ran the same model with the methodology stripped
out, but the control workspaces lived inside the repository, so every one of the
six baseline agents found `harness/ws_tools/` on disk and rebuilt the
methodology they were meant to be a control for (9,148 tool invocations on the
worst one). That measured harness against harness. Every conclusion drawn from
it is withdrawn, including a "net advantage is roughly zero" headline we had
published. Those runs ship here under the `baseline-*` labels so the
contamination is inspectable. **The harness's contribution is currently
unmeasured** — not small, not large.

## Layout

- `runs.jsonl` — one row per (run_root, model, game) run.
- `events/<label>/<game>.jsonl.gz` — one row per recorded environment
  transition of that run, in order. This is the append-only ground-truth
  ledger written by the harness daemon; the agent could read but never write
  it.
- `agent_logs/<label>/<game>/sessions/*.log.gz` — the harness's tee of each CLI
  agent session: everything the agent thought, ran, and saw.
- `agent_logs/<label>/<game>/transcripts/*.jsonl.gz` — the same sessions as
  recorded by the CLIs themselves, recovered after our tees were lost in a
  disk-full incident. Kept alongside rather than merged: neither is derived from
  the other.

### Labels

| label prefix | meaning |
|---|---|
| *(none)* | the scored runs behind the reported RHAE (`runs/`) |
| `baseline-` | **ablation**: same model, methodology stripped out (no world model, no certification, no planning, no guarded channel) |
| `retry-` | re-runs kept out of the scored set so they can never inflate a reported number |

Runs that were aborted (provider quota, stopped by hand) are included with
`score: null` and `complete: false`. Their timelines are real and are part of the
record; they are simply not scored.

## `runs.jsonl` schema

| field | type | description |
|---|---|---|
| `model` | str | harness model id (`gpt-xhigh`, `gpt-max`, `opus`, `fable`) |
| `game` | str | 4-char public ARC-AGI-3 game id (e.g. `ft09`) |
| `game_id` | str | full versioned environment id |
| `state` | str | terminal state of the run (`WIN`, `NOT_FINISHED`, ...) |
| `levels_completed` / `win_levels` | int | levels cleared / levels needed to win |
| `actions` | int | real actions committed to the environment |
| `elapsed_hours` | float | wall-clock duration of the run |
| `score` | float | official per-game RHAE score (0..100) |
| `level_scores` / `level_actions` | list | per-level score / action count |
| `note` | str | how the run ended (`win`, budget exhaustion reason, ...) |
| `notes_md` | str | the agent's final lab notebook, verbatim |
| `world_model_py` | str | the agent's final executable world model, verbatim |
| `scorecard` | json str | the official local `arc_agi` scorecard for the run |
| `n_events` | int | number of rows in the matching events file |
| `events_file` | str | relative path to the matching events file |
| `grids_compacted` | int/null | `--compact N` used at export time, if any |
| `run_root` | str | `runs` (scored), `runs-baseline` (ablation), `runs-retry` |
| `base_model` | str | model id without the label prefix |
| `complete` | bool | false for aborted runs (`score` is null) |
| `n_log_files` / `log_bytes_gz` | int | archived agent session files and their gzipped size |

## `events/*/*.jsonl.gz` schema

One JSON object per line, fields as recorded live by the harness daemon:

| field | type | description |
|---|---|---|
| `model`, `game` | str | added at export time (join keys to `runs.jsonl`) |
| `i` | int | event index, 0-based, contiguous (append-only ledger) |
| `ts` | float | unix timestamp |
| `action` | obj | `{"name": "RESET"\\|"ACTION1".."ACTION7", ["x","y" for ACTION6]}` |
| `reset` | bool | this event is a reset, not a scored action |
| `full_reset` | bool | reset restarted the whole game (vs the current level) |
| `prev_level` / `level` | int | levels completed before / after the event |
| `level_up` | bool | this action completed a level |
| `state` | str | `NOT_FINISHED` / `WIN` / `GAME_OVER` ... |
| `win` / `game_over` | bool | terminal flags |
| `win_levels` | int | levels needed to win the game |
| `available_actions` | list[int] | action ids the env accepts here |
| `n_anim_frames` | int | animation frames the env returned (last one is `grid`) |
| `grid` | 64x64 list[int] or null | the observed frame after the action (null only when exported with `--compact`) |
| `grid_stripped` | bool | present+true when `--compact` removed this row's grid |
| `prev_grid_changed_cells` | int/null | cells changed vs the previous grid |

## Provenance & license

Produced by `scripts/export_traces.py` in the harness repository from the raw
run workspaces. Environments are the 25 public ARC-AGI-3 games run locally via
the [`arc-agi`](https://pypi.org/project/arc-agi/) toolkit. MIT.

Generated: @DATE@ — @N_RUNS@ runs, @N_EVENTS@ events, models: @MODELS@.
"""


def export_agent_logs(run_dir: Path, out_dir: Path) -> dict:
    """Gzip the agent's own behavioural record next to the timeline.

    Two sources, both real: sessions/*.log are the harness's tee of each CLI
    session, transcripts/*.jsonl are what scripts/recover_traces.py pulled back
    from the CLIs' own session storage after ours were lost in a disk-full
    incident. Neither is derived from the other, so both ship.
    """
    n_files = n_bytes = 0
    for sub, pattern in (("sessions", "*.log"), ("transcripts", "*.jsonl")):
        for src in sorted((run_dir / sub).glob(pattern)) if (run_dir / sub).is_dir() else []:
            dst = out_dir / sub / (src.name + ".gz")
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(src, "rb") as fi, gzip.open(dst, "wb") as fo:
                shutil.copyfileobj(fi, fo, length=1 << 20)
            n_files += 1
            n_bytes += dst.stat().st_size
    return {"n_log_files": n_files, "log_bytes_gz": n_bytes}


def export_run(run_dir: Path, model: str, game: str, out_events: Path,
               compact: int | None) -> dict:
    """Write one events/<model>/<game>.jsonl.gz; return the runs.jsonl row."""
    events_in = run_dir / "events.jsonl"
    lines = [l for l in events_in.read_text().splitlines() if l.strip()]
    out_events.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(out_events, "wt", encoding="utf-8") as f:
        for idx, line in enumerate(lines):
            e = json.loads(line)
            row = {"model": model, "game": game, **e}
            if compact:
                interesting = (e.get("reset") or e.get("level_up") or
                               e.get("game_over") or e.get("win") or
                               idx == len(lines) - 1 or idx % compact == 0)
                if not interesting:
                    row["grid"] = None
                    row["grid_stripped"] = True
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
            n += 1

    rj = run_dir / "result.json"
    # Aborted runs (provider quota, stopped by hand) never get a result.json, but
    # their timeline is real and belongs in the archive — carry score=null.
    result = json.loads(rj.read_text()) if rj.exists() else {"score": None, "state": None}
    row = {"model": model, "game": game}
    row.update(result)
    row["notes_md"] = (run_dir / "notes.md").read_text() \
        if (run_dir / "notes.md").exists() else None
    row["world_model_py"] = (run_dir / "world_model.py").read_text() \
        if (run_dir / "world_model.py").exists() else None
    row["scorecard"] = (run_dir / "scorecard.json").read_text() \
        if (run_dir / "scorecard.json").exists() else None
    row["n_events"] = n
    row["events_file"] = str(out_events.relative_to(out_events.parent.parent.parent))
    row["grids_compacted"] = compact
    return row


def verify_loads(out_dir: Path) -> tuple[int, int]:
    """Re-read everything we wrote; raise on any parse error."""
    n_runs = sum(1 for line in (out_dir / "runs.jsonl").read_text().splitlines()
                 if line.strip() and json.loads(line))
    n_events = 0
    for gz in sorted(out_dir.glob("events/*/*.jsonl.gz")):
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            for line in f:
                json.loads(line)
                n_events += 1
    return n_runs, n_events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", action="append", default=None,
                    help="repeatable; default: runs/ runs-baseline/ runs-retry/. "
                         "Runs from a non-default root are labelled <root>-<model> "
                         "(e.g. baseline-gpt-xhigh) so they never collide.")
    ap.add_argument("--include-incomplete", action="store_true",
                    help="also export runs with no result.json (quota-aborted / "
                         "stopped). Their timeline is still real and belongs in the "
                         "archive; they carry score=null.")
    ap.add_argument("--out", default=str(ROOT / "traces"))
    ap.add_argument("--with-agent-logs", action="store_true",
                    help="also archive sessions/*.log and recovered transcripts/*.jsonl "
                         "(gzipped) — the agent's own behavioural record")
    ap.add_argument("--model", action="append", default=None,
                    help="only these models (repeatable; default: all)")
    ap.add_argument("--game", action="append", default=None,
                    help="only these games (repeatable; default: all)")
    ap.add_argument("--compact", type=int, default=None, metavar="N",
                    help="keep grids only on every Nth event plus resets/"
                         "level_up/game_over/win/final; null elsewhere")
    args = ap.parse_args()

    roots = [Path(r) for r in (args.runs_root or [
        ROOT / "runs", ROOT / "runs-baseline", ROOT / "runs-retry"])]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for runs_root in roots:
        if not runs_root.is_dir():
            continue
        # runs -> "", runs-baseline -> "baseline", runs-retry -> "retry"
        prefix = runs_root.name[5:] if runs_root.name.startswith("runs-") else ""
        for model_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
            model = model_dir.name
            if args.model and model not in args.model:
                continue
            label = f"{prefix}-{model}" if prefix else model
            for run_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                game = run_dir.name
                if args.game and game not in args.game:
                    continue
                if not (run_dir / "events.jsonl").exists():
                    continue
                if not (run_dir / "result.json").exists() and not args.include_incomplete:
                    print(f"skip {label}/{game}: no result.json (in-flight or aborted)")
                    continue
                out_events = out_dir / "events" / label / f"{game}.jsonl.gz"
                row = export_run(run_dir, label, game, out_events, args.compact)
                row["run_root"] = runs_root.name
                row["base_model"] = model
                row["complete"] = (run_dir / "result.json").exists()
                if args.with_agent_logs:
                    row.update(export_agent_logs(
                        run_dir, out_dir / "agent_logs" / label / game))
                rows.append(row)
                print(f"exported {label}/{game}: {row['n_events']} events -> "
                      f"{out_events.relative_to(out_dir)} "
                      f"({out_events.stat().st_size / 1024:.0f} KiB)")

    if not rows:
        raise SystemExit("no completed runs matched")

    with open(out_dir / "runs.jsonl", "w") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    n_runs, n_events = verify_loads(out_dir)
    assert n_runs == len(rows), (n_runs, len(rows))

    card = (DATASET_CARD
            .replace("@DATE@", date.today().isoformat())
            .replace("@N_RUNS@", str(n_runs))
            .replace("@N_EVENTS@", str(n_events))
            .replace("@MODELS@", ", ".join(sorted({r["model"] for r in rows}))))
    (out_dir / "README.md").write_text(card)
    print(f"\nwrote {out_dir}/runs.jsonl ({n_runs} runs), README.md; "
          f"re-read OK ({n_events} events total)")
    print("upload later with: HF_TOKEN=... python3 scripts/upload_hf.py "
          "--repo <user>/<dataset>")


if __name__ == "__main__":
    main()
