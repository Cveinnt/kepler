# Kepler

**An audited agent harness for ARC-AGI-3. The score is the headline; the receipts are the point.**

| Board | Model | Score | Verification |
|---|---|---:|---|
| v8.1, single config | Claude Opus 5 | **100.00** | [Server-verified exact](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1): ARC's replay re-executed all 25 games to 100 |
| v6, single config | GPT-5.6 Sol (max) | **95.97** | [Server-verified exact](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685) to the fourth decimal |
| Best run per game | mixed | 99.29 | [Server-scored ceiling](https://arcprize.org/scorecards/a7d07431-e799-4779-926b-a44464a5cb59), labeled, never a headline |

One model, one frozen configuration, one pass over all 25 public games, no per-game
selection. The written run-selection policy, every historical board (including the
regressions), and every disclosure live in [`RESULTS.md`](RESULTS.md).

## Verify it before you believe it

```bash
pip install -e .
python3 scripts/verify.py            # replay a winning trace locally; no API key
python3 scripts/verify_scores.py     # re-derive every score from the raw ledgers
python3 scripts/audit_integrity.py   # the adversarial scan we run on ourselves
```

The trace corpus is 444,756 recorded events across 280 runs: winners, failures,
regressions, and superseded boards, each with its append-only `events.jsonl`,
the agent's own `world_model.py` and lab notebook, and the reason for any
supersession. A CI gate (`scripts/check_no_game_ids.py`) fails the build if any
agent-visible file names a game.

## How it works

The agent never plays the game directly. It reads an append-only ledger of
everything that has happened, builds an executable model of the game
(`simulate(grid, action)`), and must retrodict the recorded history before it
may plan. Every committed action carries a falsifiable prediction; the first
miss voids the plan. When the game is learned, the agent certifies per-level
action programs and a mechanical replayer plays the scored attempt with no
model in the loop. In v7+ the daemon also renders every frame, animation
included, as an image the agent can look at.

That last flag decided the project. One game resisted five text-mode attempts;
the agent exhaustively searched ~410M configurations and proved the level
unsolvable under every rule derivable from its observations. It was right, and
blind: the missing mechanic only exists during animation frames, which the text
channel drops. With `--visual` and everything else held fixed, the same model
found the rule in 57 actions. The controlled ablation is in the
[paper](docs/paper/latex/); the short version is that on this game the binding
constraint was perception, not reasoning.

## What it cost

| Board | Actions (learning included) | Tokens | Notes |
|---|---:|---:|---|
| Opus 100.00 | 8,256 | 1,907.5M (97.5% cache reads) | the first 100-class result on this benchmark published with its bill |
| GPT 95.97 | 35,896 | 20.7M | ~1/32nd of the published cost frontier (Retrodict: 659.9M / $654 at 99.86) |

A first-time human plays the set in 17,135 actions. Per-game token and action
ledgers are in the repo; `scripts/cost_report.py` regenerates the tables.

## What went wrong, on the record

- The audits caught integrity violations by our own agents twice: one read the
  game's source from inside a mispointed sandbox and scored a natural-looking
  100 (voided; a clean rerun scored 46.91), and a six-agent control group
  quietly rebuilt the harness we had removed, invalidating an ablation we had
  already cited. Both incidents ship in [`incidents/`](incidents/).
- v2 added discipline mechanisms and scored 3.77 points worse, from a premise
  the server itself disproved. The board and autopsy are published.
- The shipped BFS planner turned out to have crashed on every invocation since
  v2; agents routed around it silently for five boards. Found by a zero-context
  code review before launch, fixed, and now guarded by `tests/`.
- A superseded 100.00 board replayed at 94.42 because our engine clipped two
  off-grid clicks the API rightly rejects. v8 refuses them at commit time.

We keep these because a results repo with only positive results is a marketing
page.

## Layout

```
harness/        daemon, runner, sweep, directive.md, ws_tools/ (the agent's tools)
scripts/        verify, audits, cost report, replay-to-scorecard, game-ID gate
tests/          data-free smoke + regression tiers (run in CI)
docs/           paper (LaTeX), benchmark observations, design notes
incidents/      the integrity incidents, with evidence
RESULTS.md      every board, every policy, every disclosure
```

## Credit and scope

Kepler builds on the executable-world-model line of work on this benchmark:
[Tycho](https://github.com/NIMI-research/Tycho) (arXiv:2607.28287),
[baseline1](https://github.com/astroseger/arc-3-agents-baseline1)
(Rodionov, arXiv:2605.05138), and [Retrodict](https://github.com/ryanbbrown/Retrodict).
Mechanisms adopted from each are credited in [`NOTICE`](NOTICE), and
[VISTA](https://vista-research.github.io/) motivated the visual mode.
The name follows Tycho's epigraph: Kepler derived the laws from Brahe's logs,
which is the method here. Public-set scores are not a measure of AGI progress
(the [ARC-AGI-3 technical report](https://arxiv.org/abs/2603.24621) says so
explicitly); this is harness engineering, fully auditable, offered as evidence
for what the benchmark's design gets right. The public history is a single
release commit; internal freeze hashes cited in RESULTS.md predate it.

Cite via [`CITATION.cff`](CITATION.cff). MIT license.
