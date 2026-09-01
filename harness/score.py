"""Aggregate per-game results into the benchmark RHAE with the fallback pairing.

Pairing rule (the per-game fallback used by early ~99% reports; retired here): the primary model runs every game; games
scoring below 80 are rerun with the secondary model and the higher per-game
score is retained. Benchmark score = mean of the 25 per-game scores.

Usage:
  .venv/bin/python harness/score.py --primary gpt-xhigh --secondary gpt-max
  .venv/bin/python harness/score.py --primary opus --secondary fable
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GAMES = [
    "lp85", "cd82", "sb26", "tr87", "sc25", "s5i5", "dc22", "sp80", "ls20",
    "ka59", "re86", "g50t", "sk48", "vc33", "tn36", "wa30", "ar25", "su15",
    "cn04", "r11l", "bp35", "tu93", "lf52", "ft09", "m0r0",
]

FALLBACK_THRESHOLD = 80.0


def load(runs_root: Path, model: str, game: str) -> dict | None:
    p = runs_root / model / game / "result.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True)
    ap.add_argument("--secondary", default=None)
    ap.add_argument("--runs-root", default=str(ROOT / "runs"))
    args = ap.parse_args()
    root = Path(args.runs_root)

    rows = []
    total = 0.0
    counted = 0
    pending_primary, pending_fallback = [], []
    for game in GAMES:
        prim = load(root, args.primary, game)
        sec = load(root, args.secondary, game) if args.secondary else None
        p_score = prim.get("score") if prim else None
        s_score = sec.get("score") if sec else None
        if p_score is None:
            pending_primary.append(game)
            rows.append((game, None, s_score, None, "primary run missing"))
            continue
        retained, src = p_score, args.primary
        if p_score < FALLBACK_THRESHOLD:
            if s_score is None:
                pending_fallback.append(game)
                note = f"NEEDS fallback rerun (primary {p_score:.2f} < {FALLBACK_THRESHOLD})"
            elif s_score > p_score:
                retained, src = s_score, args.secondary
                note = ""
            else:
                note = ""
        else:
            note = ""
        total += retained
        counted += 1
        rows.append((game, p_score, s_score, f"{retained:.2f} ({src})", note))

    w = max(len(args.primary), len(args.secondary or ""), 8)
    print(f"{'game':<6} {args.primary:>{w}} {(args.secondary or '-'):>{w}}  retained")
    for game, p, s, ret, note in rows:
        ps = f"{p:.2f}" if p is not None else "-"
        ss = f"{s:.2f}" if s is not None else "-"
        print(f"{game:<6} {ps:>{w}} {ss:>{w}}  {ret or '-'} {note}")
    if counted:
        print(f"\nRHAE over {counted}/{len(GAMES)} games: {total / counted:.2f}")
        if counted < len(GAMES):
            print(f"(projected only; {len(GAMES) - counted} game(s) missing count as absent, "
                  f"not zero — run them)")
    if pending_primary:
        print(f"missing primary runs: {', '.join(pending_primary)}")
    if pending_fallback:
        print(f"needing fallback reruns: {', '.join(pending_fallback)}")


if __name__ == "__main__":
    main()
