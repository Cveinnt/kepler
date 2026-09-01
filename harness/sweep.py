"""Run the full 25-game sweep for one model with bounded parallelism.

Skips games that already have a result.json (or a live workspace unless --force).
With --fallback-of PRIMARY, only runs games whose PRIMARY result scored < 80
(the per-game fallback rule; retired for headline boards).

Usage:
  .venv/bin/python harness/sweep.py --model gpt-xhigh --parallel 3
  .venv/bin/python harness/sweep.py --model gpt-max --fallback-of gpt-xhigh --parallel 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"

from score import FALLBACK_THRESHOLD, GAMES  # noqa: E402

sys.path.insert(0, str(HARNESS))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--runs-root", default=str(ROOT / "runs"))
    ap.add_argument("--fallback-of", default=None)
    ap.add_argument("--games", default=None, help="comma-separated subset")
    ap.add_argument("--max-hours", type=float, default=8.0)
    ap.add_argument("--max-sessions", type=int, default=None)
    ap.add_argument("--visual", action="store_true",
                    help="pass --visual to every run_game lane")
    ap.add_argument("--baseline", action="store_true",
                    help="ablation control: no methodology. Point --runs-root OUTSIDE "
                         "the repo so the agent cannot find harness/ws_tools and "
                         "rebuild what it is meant to be a control for.")
    args = ap.parse_args()

    root = Path(args.runs_root)
    games = args.games.split(",") if args.games else list(GAMES)

    todo = []
    for g in games:
        if (root / args.model / g / "result.json").exists():
            continue
        if (root / args.model / g / "events.jsonl").exists():
            print(f"skip {g}: workspace exists without result (in progress or crashed)")
            continue
        if args.fallback_of:
            p = root / args.fallback_of / g / "result.json"
            if not p.exists():
                print(f"skip {g}: primary result missing")
                continue
            score = json.loads(p.read_text()).get("score")
            if score is not None and score >= FALLBACK_THRESHOLD:
                continue
        todo.append(g)

    print(f"{len(todo)} game(s) to run with {args.model}: {', '.join(todo) or '-'}")
    running: dict[str, subprocess.Popen] = {}
    while todo or running:
        while todo and len(running) < args.parallel:
            g = todo.pop(0)
            (root / args.model).mkdir(parents=True, exist_ok=True)
            log = open(root / args.model / f"{g}.sweep.log", "w")
            p = subprocess.Popen(
                [str(VENV_PY), str(HARNESS / "run_game.py"),
                 "--game", g, "--model", args.model,
                 "--runs-root", str(root), "--max-hours", str(args.max_hours)]
                + (["--baseline"] if args.baseline else [])
                + (["--visual"] if args.visual else [])
                + (["--max-sessions", str(args.max_sessions)] if args.max_sessions else []),
                stdout=log, stderr=subprocess.STDOUT,
            )
            running[g] = p
            print(f"started {g} (pid {p.pid}); {len(running)} running, {len(todo)} queued", flush=True)
        time.sleep(20)
        for g, p in list(running.items()):
            if p.poll() is not None:
                res = root / args.model / g / "result.json"
                summary = "?"
                if res.exists():
                    r = json.loads(res.read_text())
                    summary = f"score={r.get('score')} state={r.get('state')} actions={r.get('actions')}"
                print(f"finished {g}: exit={p.returncode} {summary}", flush=True)
                del running[g]
    print("sweep complete")


if __name__ == "__main__":
    main()
