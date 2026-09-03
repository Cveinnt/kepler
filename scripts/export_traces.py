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
  python3 scripts/export_traces.py --release --with-agent-logs  # Kepler 1.0 boards
  python3 scripts/export_traces.py --all-history --with-agent-logs
  python3 scripts/export_traces.py --runs-root runs         # selected history
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

ROOT_LABELS = {
    "runs": "initial",
    "runs-baseline": "baseline",
    "runs-competition": "competition",
    "runs-free": "exploratory-free",
    "runs-retry": "retry",
}

DATASET_CARD = """\
---
license: mit
pretty_name: Kepler 1.0 ARC-AGI-3 trace corpus
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

# Kepler 1.0 ARC-AGI-3 trace corpus

Run artifacts from Kepler 1.0, an open-source agent harness for the 25 public
[ARC-AGI-3](https://arcprize.org/arc-agi/3/) games. A stock CLI coding agent
encodes its theory of each game as an executable `world_model.py`, certifies it
against the full recorded interaction history, plans inside the certified
model, and acts through a guarded channel that voids the plan on the first
misprediction.

[Project page](https://kepler-harness.vercel.app/) ·
[Code](https://github.com/Cveinnt/kepler) ·
[Paper](https://github.com/Cveinnt/kepler/blob/main/docs/paper/latex/main.pdf) ·
[Integrity record](https://github.com/Cveinnt/kepler/blob/main/INTEGRITY.md)

The canonical release contains two single-configuration boards:

- **Claude Opus 5: 100.00.** One frozen configuration, one run per game, no
  score-conditioned reruns. ARC Prize's official server replay re-executed all
  25 games to 100. Scorecard:
  [91aa2f10](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1).
- **GPT-5.6 Sol (max): 95.97.** One frozen configuration, with the two
  non-perfect games retained. Scorecard:
  [c9f087f3](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685).

Token and cost accounting was recovered from provider-side session records
retained locally on the execution host and deduplicated by provider message ID.
Those provider records are not part of this dataset; only the captured CLI
session logs are. They put the Opus campaign at 858,041,926 raw tokens,
97.37% cache reads, and $777.72 at current API list-equivalent rates. That is
74.0% below the $2,986 API-equivalent estimate Retrodict published for Tycho.
Tycho discloses no cost of its own, and neither do AVO or VISTA, so this is a
comparison against one third-party estimate and not a ranking of the field.
Retrodict's lower-scoring 99.86 costs less at $654. The GPT board is $1,312.14
current API list-equivalent.

The retained Opus board runs used 8,256 environment actions, with 7,292 in the
original local scored-level results and 7,202 on ARC's public replay card. The
GPT equivalents are 8,400 and 8,220. Replay selects the last full-reset-to-end
ledger segment and counts a new opening reset, so these are different recorded
denominators rather than score disagreements. Full campaign logs contain at
least 13,688 non-reset actions and omit 22 prefix events, so 8,256 is not
labeled learning-inclusive. None of these counts is ranked against other
systems, whose action counts cover different stages and definitions.

**Public-set scores are not a measure of AGI progress.** The ARC-AGI-3
technical report (§4.3.1) says so explicitly and ships a human-replay harness
scoring 100% to make the point. This dataset supports a reproduction question:
does a published result hold up? It does not support a general capability claim.

**The ablation is retracted. Read this before citing anything about the
harness's contribution.** We ran the same model with the methodology stripped
out, but the control workspaces lived inside the repository, so every one of the
six baseline agents found `harness/ws_tools/` on disk and rebuilt the
methodology they were meant to be a control for (9,148 tool invocations on the
worst one). That measured harness against harness. Every conclusion drawn from
it is withdrawn, including a "net advantage is roughly zero" headline we had
published. When historical roots are selected, those runs appear under
`baseline-*` labels so the contamination is inspectable. **The harness's contribution is currently
unmeasured**, not small and not large.

The source repository separately preserves a source-reading incident that produced a
natural-looking 100 before scoring 46.91 in a clean rerun, plus evidence that a
bundled planner was broken across five experimental boards while agents silently
routed around it. High outcome scores therefore do not establish tool health.

This dataset is narrower than the full development archive. It contains exactly
the two final 25-game boards. Earlier stages, failed experiments, quarantined
incidents, and superseded runs remain documented in the source repository and
are not part of this 50-run export.

## Layout

- `runs.jsonl`, one row per (run_root, model, game) run.
- `events/<label>/<game>.jsonl.gz`, one row per recorded environment
  transition of that run, in order. This is the append-only ground-truth
  ledger written by the harness daemon; the agent could read but never write
  it.
- `agent_logs/<label>/<game>/sessions/*.log.gz`, the harness's captured CLI
  output: @N_LOGS@ gzipped session logs, the only agent behavioural records in
  this dataset. Across this export, @N_RUNS_WITH_LOGS@ of @N_RUNS@ runs have at
  least one retained log, but coverage depth is uneven. Some Claude tee files
  contain only final summaries or quota markers. These are the captured CLI
  records available on the execution host, not a platform attestation that
  every event was retained.
- `arc_agi_3_human_baseline_actions.csv`, the per-level human action baselines
  used to recompute RHAE.
- `score_trajectories.py`, `verify_scores.py`, and `audit_integrity.py`,
  dependency-free verification programs copied into the dataset.

### Labels

| label prefix | meaning |
|---|---|
| `release-opus` | canonical Claude Opus 5 board: 100.00, exact official replay |
| `release-gpt` | canonical GPT-5.6 Sol board: 95.97, exact official replay |

Internal run-root names are provenance identifiers, not public release
versions. The public software and paper have one identity: Kepler 1.0.

## `runs.jsonl` schema

| field | type | description |
|---|---|---|
| `model` | str | exported board label, such as `release-opus` or `release-gpt` |
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
| `run_root` | str | internal source directory retained as provenance, not a public version |
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

## Verify the export

From the downloaded dataset directory:

```bash
python3 score_trajectories.py .
python3 verify_scores.py --traces-dir .
python3 audit_integrity.py --traces-dir .
```

`score_trajectories.py` independently recomputes both board scores from the
event ledgers and the human baselines. `verify_scores.py` checks that no level
was scored with fewer actions than its ledger records. `audit_integrity.py`
scans the captured CLI session-log bytes for known leakage signatures.
A clean result applies to the records present here; it does not prove that the
client preserved every event or that the pattern set detects every possible
violation. An export without `agent_logs/` is reported as unauditable and exits
nonzero.

## Provenance & license

Produced by `scripts/export_traces.py` in the harness repository from the raw
run workspaces. Environments are the 25 public ARC-AGI-3 games run locally via
the [`arc-agi`](https://pypi.org/project/arc-agi/) toolkit. MIT.

Generated: @DATE@. @N_RUNS@ runs, @N_EVENTS@ events, @N_LOGS@ session logs,
labels: @MODELS@.
"""


def export_agent_logs(run_dir: Path, out_dir: Path) -> dict:
    """Gzip captured CLI session output next to the timeline.

    Provider-side transcripts stay local. Besides carrying a much broader
    privacy surface, they are not uniformly available across the release runs.
    A sessions-only export keeps the published evidence boundary deterministic
    and consistent with the generated dataset card.
    """
    n_files = n_bytes = 0
    sources = (sorted((run_dir / "sessions").glob("*.log"))
               if (run_dir / "sessions").is_dir() else [])
    for src in sources:
        dst = out_dir / "sessions" / (src.name + ".gz")
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
    # their timeline is real and belongs in the archive, carry score=null.
    result = json.loads(rj.read_text()) if rj.exists() else {"score": None, "state": None}
    row = dict(result)
    # Export labels are part of the public dataset contract. result.json keeps
    # the provider-facing model id, which would otherwise overwrite them.
    row["model"] = model
    row["game"] = game
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


def iter_release_runs() -> list[tuple[str, str, str, Path]]:
    """Return (label, base_model, game, run_dir) for the two release boards.

    The Opus campaign resumed five games from its preserved abort snapshot.
    That storage detail remains provenance; the exported labels expose one
    public release board, not an internal harness version.
    """
    selected: list[tuple[str, str, str, Path]] = []

    release_root = ROOT / "release-runs"
    gpt_root = release_root / "gpt-max"
    for run_dir in sorted(p for p in gpt_root.iterdir() if p.is_dir()):
        selected.append(("release-gpt", "gpt-max", run_dir.name, run_dir))

    opus_root = release_root / "opus"
    opus_resume = release_root / "aborted-opus"
    games = sorted({p.name for p in opus_root.iterdir() if p.is_dir()} |
                   {p.name for p in opus_resume.iterdir() if p.is_dir()})
    for game in games:
        primary = opus_root / game
        run_dir = primary if (primary / "result.json").exists() else opus_resume / game
        selected.append(("release-opus", "opus", game, run_dir))

    return selected


def main() -> None:
    ap = argparse.ArgumentParser()
    selection = ap.add_mutually_exclusive_group()
    selection.add_argument("--release", action="store_true",
                           help="export the two canonical Kepler 1.0 boards under "
                                "release-opus and release-gpt labels")
    selection.add_argument("--all-history", action="store_true",
                           help="export every local runs*/ root, including failures, "
                                "superseded stages, and quarantined controls")
    selection.add_argument("--runs-root", action="append", default=None,
                           help="repeatable; default: runs/ runs-baseline/ runs-retry/")
    ap.add_argument("--include-incomplete", action="store_true",
                    help="also export runs with no result.json (quota-aborted / "
                         "stopped). Their timeline is still real and belongs in the "
                         "archive; they carry score=null.")
    ap.add_argument("--out", default=str(ROOT / "traces"))
    ap.add_argument("--with-agent-logs", action="store_true",
                    help="also archive captured sessions/*.log output (gzipped); "
                         "provider-side transcripts remain local")
    ap.add_argument("--model", action="append", default=None,
                    help="only these models (repeatable; default: all)")
    ap.add_argument("--game", action="append", default=None,
                    help="only these games (repeatable; default: all)")
    ap.add_argument("--compact", type=int, default=None, metavar="N",
                    help="keep grids only on every Nth event plus resets/"
                         "level_up/game_over/win/final; null elsewhere")
    args = ap.parse_args()

    if args.all_history:
        roots = sorted(path for path in ROOT.glob("runs*") if path.is_dir())
    else:
        roots = [Path(root) for root in (args.runs_root or [
            ROOT / "runs", ROOT / "runs-baseline", ROOT / "runs-retry"])]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected: list[tuple[str, str, str, Path]] = []
    if args.release:
        selected = iter_release_runs()
    else:
        for runs_root in roots:
            if not runs_root.is_dir():
                continue
            prefix = ROOT_LABELS.get(
                runs_root.name,
                runs_root.name[5:] if runs_root.name.startswith("runs-") else "initial",
            )
            for model_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
                model = model_dir.name
                model_label = "aborted-opus" if model.startswith("_") and "aborted" in model else model
                label = f"{prefix}-{model_label}"
                for run_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                    selected.append((label, model, run_dir.name, run_dir))

    rows = []
    for label, model, game, run_dir in selected:
        if args.model and model not in args.model:
            continue
        if args.game and game not in args.game:
            continue
        if not (run_dir / "events.jsonl").exists():
            continue
        if not (run_dir / "result.json").exists() and not args.include_incomplete:
            print(f"skip {label}/{game}: no result.json (in-flight or aborted)")
            continue
        out_events = out_dir / "events" / label / f"{game}.jsonl.gz"
        row = export_run(run_dir, label, game, out_events, args.compact)
        row["run_root"] = str(run_dir.parent.parent.relative_to(ROOT))
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
            .replace("@MODELS@", ", ".join(sorted({r["model"] for r in rows})))
            .replace("@N_RUNS_WITH_LOGS@", str(sum(
                1 for row in rows if row.get("n_log_files", 0) > 0)))
            # Counted from what was actually written, never from intent, so the
            # card can never again document files the package does not contain.
            .replace("@N_LOGS@", str(sum(
                1 for _ in (out_dir / "agent_logs").rglob("sessions/*.log.gz")))))
    (out_dir / "README.md").write_text(card)
    release_files = [
        (ROOT / "data" / "arc_agi_3_human_baseline_actions.csv",
         out_dir / "arc_agi_3_human_baseline_actions.csv"),
        (ROOT / "scripts" / "score_trajectories.py",
         out_dir / "score_trajectories.py"),
        (ROOT / "scripts" / "verify_scores.py", out_dir / "verify_scores.py"),
        (ROOT / "scripts" / "audit_integrity.py", out_dir / "audit_integrity.py"),
    ]
    for source, destination in release_files:
        shutil.copy2(source, destination)
    print(f"\nwrote {out_dir}/runs.jsonl ({n_runs} runs), README.md, "
          "human baselines, and standalone verifiers; "
          f"re-read OK ({n_events} events total)")
    print(f"score with: python3 {out_dir}/score_trajectories.py {out_dir}")
    print(f"verify with: python3 {out_dir}/verify_scores.py --traces-dir {out_dir}")
    print(f"audit with: python3 {out_dir}/audit_integrity.py --traces-dir {out_dir}")
    print("upload later with: HF_TOKEN=... python3 scripts/upload_hf.py "
          "--repo <user>/<dataset>")


if __name__ == "__main__":
    main()
