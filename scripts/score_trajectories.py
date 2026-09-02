#!/usr/bin/env python3
"""Recompute ARC-AGI-3 RHAE scores from a Kepler trace export.

This dependency-free script uses per-level agent action counts in
``runs.jsonl`` and ARC Prize human baselines in
``arc_agi_3_human_baseline_actions.csv``. It does not trust stored level or
board scores when calculating them.

The formula matches the ARC-AGI-3 scorer used for official scorecards:

    level = min((human_actions / agent_actions) ** 2 * 100, 115)
    game  = weighted mean by 1-indexed level, capped by completion weight
    board = unweighted mean across games

Usage:
  python3 score_trajectories.py .
  python3 scripts/score_trajectories.py /path/to/traces
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

LEVEL_SCORE_CAP = 115.0
TOLERANCE = 1e-8


def load_baselines(path: Path) -> dict[str, list[int]]:
    rows: dict[str, dict[int, int]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["game"]][int(row["level"])] = int(row["baseline_actions"])
    baselines: dict[str, list[int]] = {}
    for game, levels in rows.items():
        expected = list(range(1, max(levels) + 1))
        if sorted(levels) != expected:
            raise ValueError(f"{game}: non-contiguous baseline levels")
        baselines[game] = [levels[level] for level in expected]
    return baselines


def game_score(run: dict, baselines: list[int]) -> float:
    actions = run.get("level_actions") or []
    completed = int(run.get("levels_completed") or 0)
    if completed > len(baselines) or completed > len(actions):
        raise ValueError(
            f"{run.get('model')}/{run.get('game')}: completed-level count exceeds data"
        )
    denominator = sum(range(1, len(baselines) + 1))
    weighted_score = 0.0
    completed_weight = 0
    for level_index in range(1, completed + 1):
        agent_actions = int(actions[level_index - 1])
        if agent_actions <= 0:
            raise ValueError(
                f"{run.get('model')}/{run.get('game')} L{level_index}: "
                "non-positive action count"
            )
        human_actions = baselines[level_index - 1]
        level_score = min(
            (human_actions / agent_actions) ** 2 * 100.0,
            LEVEL_SCORE_CAP,
        )
        weighted_score += level_index * level_score
        completed_weight += level_index
    return min(
        weighted_score / denominator,
        100.0 * completed_weight / denominator,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces_dir", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.traces_dir)
    index = root / "runs.jsonl"
    baseline_path = root / "arc_agi_3_human_baseline_actions.csv"
    if not index.exists() or not baseline_path.exists():
        parser.error(
            f"expected {index} and {baseline_path}; pass the trace dataset directory"
        )

    baselines = load_baselines(baseline_path)
    board_scores: dict[str, list[float]] = defaultdict(list)
    mismatches: list[str] = []
    checked = 0
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        run = json.loads(line)
        if run.get("score") is None:
            continue
        game = run["game"]
        if game not in baselines:
            mismatches.append(f"{run.get('model')}/{game}: baseline missing")
            continue
        computed = game_score(run, baselines[game])
        reported = float(run["score"])
        checked += 1
        board_scores[run["model"]].append(computed)
        if abs(computed - reported) > TOLERANCE:
            mismatches.append(
                f"{run['model']}/{game}: computed {computed:.12f}, "
                f"reported {reported:.12f}"
            )

    if checked == 0:
        print("FAIL: no scored runs found")
        return 2
    for model in sorted(board_scores):
        scores = board_scores[model]
        print(f"{model}: {sum(scores) / len(scores):.12f} across {len(scores)} games")
    print(f"checked {checked} run scores from human baselines and action counts")
    if mismatches:
        print("FAIL:")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        return 1
    print("PASS: every stored game score matches independent RHAE recomputation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
