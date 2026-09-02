#!/usr/bin/env python3
"""Separate retained-board, scored-level, and full-campaign action counts.

The official result files describe retained board runs. They do not include
every earlier attempt visible in the append-only campaign ledgers. This report
keeps those denominators separate and fails closed when a ledger prefix is
missing.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OPUS = ROOT / "release-runs" / "opus"


def main() -> int:
    workspaces = sorted(path.parent for path in OPUS.glob("*/result.json"))
    if not workspaces:
        raise SystemExit(f"no release results under {OPUS}")

    retained_actions = 0
    scored_level_actions = 0
    observed_nonreset = 0
    observed_resets = 0
    missing_prefix_events = 0

    for workspace in workspaces:
        result = json.loads((workspace / "result.json").read_text())
        events_path = workspace / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text().splitlines()
                  if line.strip()]
        if not events:
            raise SystemExit(f"empty campaign ledger: {events_path}")

        indices = [event.get("i") for event in events]
        if not all(isinstance(index, int) for index in indices):
            raise SystemExit(f"missing event index in {events_path}")
        first = indices[0]
        if indices != list(range(first, first + len(indices))):
            raise SystemExit(f"non-contiguous observed ledger in {events_path}")

        retained_actions += int(result["actions"])
        scored_level_actions += sum(int(value) for value in result["level_actions"])
        observed_nonreset += sum(not bool(event.get("reset")) for event in events)
        observed_resets += sum(bool(event.get("reset")) for event in events)
        missing_prefix_events += first

    print("Kepler 1.0 Opus action accounting")
    print(f"  games:                              {len(workspaces):,}")
    print(f"  retained-board-run actions:         {retained_actions:,}")
    print(f"  scored-level actions:               {scored_level_actions:,}")
    print(f"  observed campaign non-reset actions:{observed_nonreset:>10,}")
    print(f"  observed reset events:              {observed_resets:>10,}")
    print(f"  unavailable prefix events:          {missing_prefix_events:>10,}")
    if missing_prefix_events:
        print("  exact campaign actions:              UNAVAILABLE")
        print("  reason: missing prefix-event reset flags prevent an exact non-reset total")
        return 2
    print(f"  exact campaign actions:             {observed_nonreset:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
