#!/usr/bin/env python3
"""Verify the harness mechanics offline against a bundled trace, in under a minute.

No model calls, no network, no API keys, stdlib only. This does two things:

1. Replays the trace's final world_model.py over its entire recorded
   events.jsonl using the REAL certification tool (harness/ws_tools/backtest.py,
   staged into a temp workspace exactly as run_game.py stages it into live
   workspaces). This is the same GREEN/RED gate the agent had to pass during the run.
2. Independently cross-checks the append-only ledger against the reported
   result.json (action count, levels completed, terminal state, per-level
   action split, monotonic event indices).

Usage:
  python3 scripts/verify.py                              # bundled examples/gpt-xhigh/ft09
  python3 scripts/verify.py --trace runs/opus/ft09       # any completed run (read-only)
  python3 scripts/verify.py --keep                       # keep the temp workspace around
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS_TOOLS = ROOT / "harness" / "ws_tools"
DEFAULT_TRACE = ROOT / "examples" / "gpt-xhigh" / "ft09"


def fail(msg: str) -> None:
    print(f"VERIFY: FAIL: {msg}")
    sys.exit(1)


def check(name: str, ok: bool, detail: str) -> None:
    print(f"  [{'ok' if ok else 'XX'}] {name}: {detail}")
    if not ok:
        fail(name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=str(DEFAULT_TRACE),
                    help="trace directory with events.jsonl + world_model.py + result.json")
    ap.add_argument("--keep", action="store_true",
                    help="keep the temp replay workspace instead of deleting it")
    args = ap.parse_args()

    # Invariant gate first: no game IDs in agent-visible surfaces.
    gate = subprocess.run([sys.executable, str(Path(__file__).parent / "check_no_game_ids.py")],
                          capture_output=True, text=True)
    check("no game secrets in agent-visible files", gate.returncode == 0,
          gate.stdout.strip().splitlines()[-1] if gate.stdout.strip() else "no output")

    trace = Path(args.trace).resolve()
    for name in ("events.jsonl", "world_model.py", "result.json"):
        if not (trace / name).exists():
            fail(f"{trace / name} not found")
    result = json.loads((trace / "result.json").read_text())
    print(f"trace: {trace}")
    print(f"claimed: {result['game']} / {result['model']}, state={result['state']}, "
          f"levels={result['levels_completed']}/{result['win_levels']}, "
          f"actions={result['actions']}, score={result['score']}")

    # ---- 1. Ledger consistency (independent of the world model) ----------------
    events = [json.loads(line) for line in
              (trace / "events.jsonl").read_text().splitlines() if line.strip()]
    print(f"\nledger: {len(events)} events")
    check("event indices monotonic",
          all(e["i"] == i for i, e in enumerate(events)),
          "i == 0..N-1 with no gaps (append-only)")
    actions = sum(1 for e in events if not e["reset"])
    check("action count", actions == result["actions"],
          f"{actions} non-reset events == result.actions {result['actions']}")
    check("levels completed", events[-1]["level"] == result["levels_completed"],
          f"final ledger level {events[-1]['level']} == result {result['levels_completed']}")
    check("terminal state", events[-1]["state"] == result["state"],
          f"final ledger state {events[-1]['state']} == result {result['state']}")
    if result.get("level_actions"):
        s = sum(result["level_actions"])
        check("per-level action split", s == result["actions"],
              f"sum(level_actions) {s} == total actions {result['actions']}")

    # ---- 2. Replay through the real backtest tool ------------------------------
    tmp = Path(tempfile.mkdtemp(prefix="kepler-verify-"))
    try:
        (tmp / "tools").mkdir()
        for f in WS_TOOLS.glob("*.py"):
            shutil.copy(f, tmp / "tools" / f.name)
        shutil.copy(trace / "events.jsonl", tmp / "events.jsonl")
        shutil.copy(trace / "world_model.py", tmp / "world_model.py")
        print(f"\nreplaying world_model.py over the full history with the real "
              f"harness/ws_tools/backtest.py (workspace: {tmp}) ...")
        proc = subprocess.run([sys.executable, str(tmp / "tools" / "backtest.py")],
                              cwd=tmp, capture_output=True, text=True, timeout=300)
        out = (proc.stdout + proc.stderr).strip()
        print("  " + "\n  ".join(out.splitlines()))
        check("backtest verdict", proc.returncode == 0 and "GREEN" in out,
              "world model reproduces every recorded transition (GREEN)")
    finally:
        if args.keep:
            print(f"(kept {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\nVERIFY: PASS. The recorded history is internally consistent, matches the "
          "reported result, and is fully reproduced by the agent's final world model.")


if __name__ == "__main__":
    main()
