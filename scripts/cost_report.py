#!/usr/bin/env python3
"""Token accounting for every run, recovered from the CLI session logs.

Why this exists
---------------
François Chollet's stated condition for a harness result being legitimate is
that "the settings and the cost are clearly reported". Most harness results
report neither. Separately, an unsourced claim that running this benchmark costs
$25,000 has been circulating; the only measured figure in public is far lower, so
publishing ours either corrects the record or confirms it.

What is measurable, and what is not
-----------------------------------
The codex CLI prints a running "tokens used" total per session, so GPT-side runs
can be accounted exactly. The claude CLI does not emit usage in `-p` mode, so
Claude-side runs are **unmeasured** — that is stated rather than estimated. We
report tokens, not dollars, because per-token prices change and a stale price is
worse than none: multiply by whatever the current rate is.

Usage:
  .venv/bin/python scripts/cost_report.py
  .venv/bin/python scripts/cost_report.py --markdown   # table for RESULTS.md
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# codex prints the cumulative total for the session, e.g. "tokens used\n310,025".
TOKENS = re.compile(r"tokens used\s*\n?\s*([\d,]+)", re.I)


USAGE = re.compile(r'"total_token_usage":\{([^}]*)\}')


def _field(blob: str, name: str) -> int:
    m = re.search(rf'"{name}":(\d+)', blob)
    return int(m.group(1)) if m else 0


def run_tokens(ws: Path) -> dict:
    """Token usage for one run, from whichever record survives.

    Preference order: the CLI's own recovered transcript, which carries a
    structured total_token_usage including the cached-input split, then the
    session tee, which only has a running total. Cached input is tracked
    separately because it is priced very differently — reporting one blended
    number would overstate cost several-fold.
    """
    fresh = {"total": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0, "n": 0}
    for f in sorted(glob.glob(str(ws / "transcripts" / "*.jsonl"))):
        try:
            text = Path(f).read_text(errors="ignore")
        except OSError:
            continue
        blobs = USAGE.findall(text)
        if not blobs:
            continue
        last = blobs[-1]  # cumulative for that session
        fresh["total"] += _field(last, "total_tokens")
        fresh["input"] += _field(last, "input_tokens")
        fresh["cached"] += _field(last, "cached_input_tokens")
        fresh["output"] += _field(last, "output_tokens")
        fresh["reasoning"] += _field(last, "reasoning_output_tokens")
        fresh["n"] += 1
    if fresh["n"]:
        return fresh
    for f in sorted(glob.glob(str(ws / "sessions" / "*.log"))):
        try:
            text = Path(f).read_text(errors="ignore")
        except OSError:
            continue
        vals = [int(m.group(1).replace(",", "")) for m in TOKENS.finditer(text)]
        if vals:
            fresh["total"] += max(vals)
            fresh["n"] += 1
    return fresh


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")

    ap.add_argument("root", nargs="?", default="runs")
    args = ap.parse_args()

    by_model: dict[str, dict] = defaultdict(lambda: {"tok": 0, "runs": 0, "measured": 0})
    rows = []
    for rj in sorted(glob.glob(str(ROOT / f"{args.root}/*/*/result.json"))):
        ws = Path(rj).parent
        model, game = ws.parent.name, ws.name
        u = run_tokens(ws)
        score = json.loads(Path(rj).read_text()).get("score")
        b = by_model[model]
        b["runs"] += 1
        b["tok"] += u["total"]
        b["cached"] = b.get("cached", 0) + u["cached"]
        b["output"] = b.get("output", 0) + u["output"]
        if u["n"]:
            b["measured"] += 1
        rows.append((model, game, score, u["total"], u["n"]))

    if args.markdown:
        print("| model | runs | runs with usage data | total tokens |")
        print("|---|---:|---:|---:|")
        for m, b in sorted(by_model.items()):
            tok = f"{b['tok']:,}" if b["measured"] else "not emitted by the CLI"
            print(f"| `{m}` | {b['runs']} | {b['measured']} | {tok} |")
        return 0

    print(f"{'model':12} {'runs':>5} {'measured':>9} {'total tok':>15} {'of which cached':>17} {'output tok':>13}")
    for m, b in sorted(by_model.items()):
        tok = f"{b['tok']:,}" if b["measured"] else "—"
        cac = f"{b.get('cached',0):,}" if b["measured"] else "—"
        out = f"{b.get('output',0):,}" if b["measured"] else "—"
        print(f"{m:12} {b['runs']:5d} {b['measured']:9d} {tok:>15} {cac:>17} {out:>13}")
    grand = sum(b["tok"] for b in by_model.values())
    meas = sum(b["measured"] for b in by_model.values())
    runs = sum(b["runs"] for b in by_model.values())
    print(f"\n{meas}/{runs} runs have usage data; {grand:,} tokens accounted.")
    if meas < runs:
        print("The claude CLI does not emit token usage in -p mode, so those runs are\n"
              "unmeasured. Reported as unmeasured rather than estimated.")
    print("\nTokens, not dollars: multiply by the current per-token rate. A stale price\n"
          "is worse than no price.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
