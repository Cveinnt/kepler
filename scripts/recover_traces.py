#!/usr/bin/env python3
"""Recover agent transcripts for runs whose session logs were lost.

The harness tees each CLI-agent session to runs/<model>/<game>/sessions/*.log, but
those files are large and can be pruned (ours were, during a disk-full incident).
Both CLIs keep their own copy of every session, so the record is recoverable:

  codex   ~/.codex/sessions/**/*.jsonl      (rollout files; cwd recorded inside)
  claude  ~/.claude/projects/<slugified-cwd>/*.jsonl

This copies the matching transcripts into runs/<model>/<game>/transcripts/ so the
integrity audit and any public release have the full behavioural record.

Usage:
  python3 scripts/recover_traces.py            # recover for every run missing logs
  python3 scripts/recover_traces.py --all      # recover for every run
  python3 scripts/recover_traces.py --dry-run
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODEX = Path.home() / ".codex" / "sessions"
CLAUDE = Path.home() / ".claude" / "projects"


def claude_dir_for(ws: Path) -> Path:
    """claude stores transcripts under a slugified absolute cwd."""
    return CLAUDE / str(ws).replace("/", "-").replace(".", "-")


def codex_files_for(ws: Path) -> list[Path]:
    """codex rollout files record their cwd; scan for ones matching this workspace."""
    out = []
    target = str(ws)
    for p in CODEX.rglob("*.jsonl"):
        try:
            with open(p, "r", errors="ignore") as fh:
                head = fh.read(40000)  # cwd appears in the session meta near the top
        except OSError:
            continue
        if target in head:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="recover for every run, not just those missing logs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    runs = [Path(p).parent for p in glob.glob(str(ROOT / "runs*/*/*/events.jsonl"))]
    todo = []
    for ws in sorted(runs):
        has_logs = bool(glob.glob(str(ws / "sessions" / "*.log")))
        has_recovered = bool(glob.glob(str(ws / "transcripts" / "*.jsonl")))
        if args.all or (not has_logs and not has_recovered):
            todo.append(ws)

    print(f"{len(runs)} runs; {len(todo)} to recover")
    total = 0
    for ws in todo:
        model = ws.parent.name
        srcs: list[Path] = []
        if model in ("opus", "fable"):
            d = claude_dir_for(ws)
            srcs = sorted(d.glob("*.jsonl")) if d.is_dir() else []
        else:
            srcs = codex_files_for(ws)
        if not srcs:
            print(f"  {ws.relative_to(ROOT)}: no transcript found")
            continue
        dest = ws / "transcripts"
        size = sum(p.stat().st_size for p in srcs)
        print(f"  {ws.relative_to(ROOT)}: {len(srcs)} transcript(s), {size/1e6:.1f} MB")
        if not args.dry_run:
            dest.mkdir(exist_ok=True)
            for p in srcs:
                shutil.copy2(p, dest / p.name)
            total += size
    if not args.dry_run:
        print(f"recovered {total/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
