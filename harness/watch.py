#!/usr/bin/env python3
"""Emit one line per per-game milestone (level up / win / game over / result)."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "runs"
seen: dict[str, tuple] = {}
done: set[str] = set()

while True:
    for ev in sorted(ROOT.glob("*/*/events.jsonl")):
        key = f"{ev.parent.parent.name}/{ev.parent.name}"
        if key in done:
            continue
        res = ev.parent / "result.json"
        if res.exists():
            r = json.loads(res.read_text())
            print(f"{key} FINISHED: score={r.get('score')} state={r.get('state')} "
                  f"levels={r.get('levels_completed')}/{r.get('win_levels')} "
                  f"actions={r.get('actions')} ({r.get('note')})", flush=True)
            done.add(key)
            continue
        try:
            last = json.loads(ev.read_text().splitlines()[-1])
        except Exception:
            continue
        sig = (last["level"], last["state"])
        if seen.get(key) != sig:
            if key in seen:  # suppress the initial state line, only report changes
                print(f"{key}: level {last['level']}/{last['win_levels']} "
                      f"state={last['state']} after {last['i']} steps", flush=True)
            seen[key] = sig
    if len(done) >= len(list(ROOT.glob('*/*/events.jsonl'))) and done:
        # all known runs finished; keep going anyway in case new ones start
        pass
    time.sleep(30)
