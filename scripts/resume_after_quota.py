#!/usr/bin/env python3
"""Wait for the provider quota window, then resume every unfinished v2 lane.

Lanes that abort on quota exit 3 WITHOUT writing result.json (so score.py sees
"not run", not a zero) and stay resumable. This runner sleeps until the reset
time, then drives every unfinished game through run_game --resume with bounded
parallelism, printing one line per completion for the monitor to pick up.

Usage:
  python3 scripts/resume_after_quota.py --at 08:21 --parallel 3
  python3 scripts/resume_after_quota.py --at now          # resume immediately
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"
sys.path.insert(0, str(ROOT / "harness"))
from score import GAMES  # noqa: E402


def unfinished(runs_root: Path, model: str) -> list[str]:
    out = []
    for g in GAMES:
        ws = runs_root / model / g
        if not (ws / "result.json").exists():
            out.append(g)
    return out


def run_one(runs_root: Path, model: str, game: str, hours: float, sessions: int) -> str:
    ws = runs_root / model / game
    cmd = [str(VENV_PY), str(ROOT / "harness" / "run_game.py"),
           "--game", game, "--model", model, "--runs-root", str(runs_root),
           "--max-hours", str(hours), "--max-sessions", str(sessions)]
    if (ws / "events.jsonl").exists():
        cmd.append("--resume")
    log = runs_root / model / f"{game}-quota-resume.log"
    with open(log, "w") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
    res = ws / "result.json"
    if res.exists():
        import json
        r = json.loads(res.read_text())
        return f"RESUMED DONE {game}: {round(r.get('score') or -1, 2)} {r.get('state')} | {r.get('note','')}"
    return f"RESUMED EXIT {game}: rc={rc} no result (quota again? see {log})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", default="now", help='local HH:MM to start, or "now"')
    ap.add_argument("--model", default="opus")
    ap.add_argument("--runs-root", default=str(ROOT / "runs-v2"))
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--max-hours", type=float, default=6.0)
    ap.add_argument("--max-sessions", type=int, default=16)
    args = ap.parse_args()

    if args.at != "now":
        h, m = map(int, args.at.split(":"))
        now = dt.datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        wait = (target - now).total_seconds()
        print(f"sleeping {wait/60:.0f}m until {target}", flush=True)
        time.sleep(wait)

    runs_root = Path(args.runs_root)
    todo = unfinished(runs_root, args.model)
    print(f"resuming {len(todo)} unfinished games: {', '.join(todo)}", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(run_one, runs_root, args.model, g,
                          args.max_hours, args.max_sessions): g for g in todo}
        for f in as_completed(futs):
            print(f.result(), flush=True)
    print("QUOTA-RESUME SWEEP COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
