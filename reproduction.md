# Reproducing the boards

The release is reproducible at two levels. Level one is free and takes minutes
once the trace dataset is present; level two replays a new campaign and costs
real model quota.

## Level one: verify the published numbers (no API key, no model calls)

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e .
python3 scripts/verify.py # replays the bundled fixture
.venv/bin/python scripts/verify_scores.py --traces-dir traces
.venv/bin/python scripts/audit_integrity.py --traces-dir traces
python3 scripts/check_no_game_ids.py # checks agent-visible files for game IDs
```

Every number in RESULTS.md and the paper comes from these ledgers, and the
official scorecards were produced by replaying the same ledgers through ARC's
competition API (`scripts/replay_submit.py`). The repository intentionally
reports `VACUOUS` when corpus-wide checks find no run data. Until
`release.json` contains a trace-dataset URL, full independent verification is
pending.

## Level two: run a board yourself

Requirements: an `ARC_API_KEY` in `.env` (free from three.arcprize.org), plus a
Claude Code or Codex CLI login for the model you want to drive.

```bash
# one game
.venv/bin/python harness/run_game.py --game ft09 --model opus --visual

# a full 25-game board using the Kepler release configuration
.venv/bin/python harness/sweep.py --model opus --runs-root runs-mine --visual --parallel 4
```

`--visual` enables the release observation channel; the daemon saves every
frame as a PNG. Runs are resumable after any interruption with `--resume`; the ledger is
append-only and survives everything. Score a finished board with
`scripts/verify_scores.py`, and submit it for an official card with
`scripts/replay_submit.py --model opus --games all --runs-root runs-mine`.

Bit-for-bit reproduction of live runs is not expected (sampling, provider
drift). Reproduction of every score from its ledger is expected, mechanical,
and gated in CI.
