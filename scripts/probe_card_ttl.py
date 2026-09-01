#!/usr/bin/env python3
"""Find the server-side lifetime of competition scorecards on an anonymous key.

Pilot evidence: runs of 0.84h and 0.78h closed their scorecards fine; a 4.95h
run got `404 scorecard/close` twice, despite never exceeding the client's
15-minute idle rule. So something expires server-side between ~1h and ~5h —
either the anonymous API key or the open card. This measures which and when,
with zero model spend: open N cards up front on one anonymous key, give each
one reset so it is non-empty, then close card k after k hours.

Writes progress to stdout (redirect to a log). Total runtime: --hours hours.

Usage:
  python3 scripts/probe_card_ttl.py --hours 4
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

logging.disable(logging.INFO)

from arc_agi import Arcade, OperationMode  # noqa: E402

SHARED = Path(__file__).resolve().parent.parent / ".arc-private"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=4)
    ap.add_argument("--game", default="ft09")
    args = ap.parse_args()

    a = Arcade(operation_mode=OperationMode.COMPETITION,
               environments_dir=str(SHARED / "environment_files"),
               recordings_dir=str(SHARED / "recordings"))
    try:
        a.scorecard_manager.set_idle_for(24 * 60)
    except Exception:
        pass
    gid = [e for e in a.get_environments() if e.game_id.startswith(args.game)][0].game_id

    cards = []
    for k in range(1, args.hours + 1):
        cid = a.open_scorecard(tags=["kepler-ttl-probe", f"close-at-{k}h"])
        env = a.make(gid, scorecard_id=cid)
        env.reset()
        cards.append((k, cid))
        print(f"opened card {k}h: {cid}", flush=True)

    t0 = time.time()
    results = {}
    for k, cid in cards:
        wait = k * 3600 - (time.time() - t0)
        if wait > 0:
            time.sleep(wait)
        try:
            card = a.close_scorecard(cid)
            ok = card is not None
            results[k] = "CLOSED OK" if ok else "close returned None"
        except Exception as exc:
            results[k] = f"FAILED: {type(exc).__name__}: {str(exc)[:90]}"
        print(f"[{k}h] {cid}: {results[k]}", flush=True)

    print(json.dumps(results, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
