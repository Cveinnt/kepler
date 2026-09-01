# Reproducing the boards

The scores are reproducible at two levels. Level one is free and takes minutes;
level two replays the full campaign and costs real model quota.

## Level one: verify the published numbers (no API key, no model calls)

```bash
pip install -e .
python3 scripts/verify.py            # replays a bundled winning trace through the backtest
python3 scripts/verify_scores.py     # re-derives every board score from raw events.jsonl
python3 scripts/audit_integrity.py   # adversarial scan over every published run
python3 scripts/check_no_game_ids.py # proves no agent-visible file names a game
```

Every number in RESULTS.md and the paper comes from these ledgers, and the
official scorecards were produced by replaying the same ledgers through ARC's
competition API (`scripts/replay_submit.py`).

## Level two: run a board yourself

Requirements: an `ARC_API_KEY` in `.env` (free from three.arcprize.org), plus a
Claude Code or Codex CLI login for the model you want to drive.

```bash
# one game
.venv/bin/python harness/run_game.py --game ft09 --model opus --visual

# a full 25-game board, the v8.1 configuration
.venv/bin/python harness/sweep.py --model opus --runs-root runs-mine --visual --parallel 4
```

`--visual` is the v7+ observation channel (the daemon saves every frame as a
PNG). Runs are resumable after any interruption with `--resume`; the ledger is
append-only and survives everything. Score a finished board with
`scripts/verify_scores.py`, and submit it for an official card with
`scripts/replay_submit.py --model opus --games all --runs-root runs-mine`.

Bit-for-bit reproduction of live runs is not expected (sampling, provider
drift). Reproduction of every score from its ledger is expected, mechanical,
and gated in CI.
