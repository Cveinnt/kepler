# Bundled example trace

One complete, winning run of the harness, copied verbatim from
`runs/gpt-xhigh/ft09/` (GPT-5.6 Sol at `model_reasoning_effort=xhigh` on game
`ft09`): 6/6 levels, 75 actions, RHAE 100.0, ~31 minutes wall clock.

| File             | What it is                                                            |
|------------------|-----------------------------------------------------------------------|
| `events.jsonl`   | Append-only ground truth: every real transition (action, 64×64 grid, flags), written only by the daemon |
| `world_model.py` | The agent's final executable theory of the game (`simulate`, `is_goal`, `candidate_actions`) |
| `notes.md`       | The agent's lab notebook, as it left it                               |
| `result.json`    | Final outcome: state, per-level actions/scores, RHAE                  |
| `scorecard.json` | The official local `arc_agi` scorecard for the run                    |

Verify it offline (no model calls, no network):

```bash
python3 scripts/verify.py
```

which replays `world_model.py` over the entire `events.jsonl` with the real
`harness/ws_tools/backtest.py` and cross-checks the ledger against
`result.json`. All grids are retained (the trace is small); larger traces
exported by `scripts/export_traces.py` can strip grids with `--compact`.
