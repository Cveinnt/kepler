# Kepler

**100.00. Every level at or above median-human action efficiency. One frozen
configuration.**

Kepler is an open-source agent harness for the 25 public ARC-AGI-3 games. One
frozen Claude Opus 5 configuration scored **100.00**, with every game
re-executed to 100 by ARC Prize's official server replay. There was no per-game
model selection and no score-conditioned rerun.

| Model | Score | Evidence | Resource record |
|---|---:|---|---:|
| Claude Opus 5 | **100.00** | [Server-verified exact](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1) | 8,256 actions including learning; 1,641.2M tokens; $1,568.50 current API list-equivalent |
| GPT-5.6 Sol (max) | **95.97** | [Server-verified exact](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685) | 35,896 actions; 2,429.1M tokens; $1,312.14 current API list-equivalent |

This repository has one public release identity: **Kepler 1.0**. Earlier
experimental configurations remain in [`RESULTS.md`](RESULTS.md) as ablation
evidence, not as competing product versions. Canonical release facts live in
[`release.json`](release.json).

## What is different

Kepler has nine defensible wedges. None requires combining metrics from
different boards.

| Wedge | Measured claim |
|---|---|
| Human-relative performance | ARC Prize defines 100.00 as beating every level at or above median-human action efficiency. Kepler does that on all 25 public games. |
| Scored-action convergence | 7,292 scored actions, 3.3% below VISTA's 7,542 and 5.3% below Retrodict's 7,703. AVO remains lower at 6,624. |
| Learning-inclusive action economy | 8,256 total environment actions, 2.08x fewer than the 17,135-action first-time-human reference. |
| Lowest disclosed perfect-score bill | $1,568.50 at current Opus 5 API list rates, 47.5% below Tycho's leaderboard cost of $2,986. AVO and VISTA do not disclose comparable bills. |
| Single-configuration durability | One frozen configuration and one retained result per game. The GPT board keeps its same-configuration collapse rather than rerolling it. |
| Zero game priors, enforced | CI fails if any agent-visible file names a public game. |
| Mechanisms with deltas | Certify/replay added 2.35 board points; the clean-run-at-100 trigger converted four GPT games; every committed action carries a checked prediction. |
| Audits that changed the paper | A source-reading win and a contaminated control were voided. A dead planner exposed a separate tool-integrity blind spot. |
| Negative results and benchmark reform | Regressions, failed mechanisms, withdrawn claims, and five concrete evaluation changes are retained rather than edited out. |

### One result, selected before the score

The headline uses one model, one frozen harness, and one run per game. A same-
configuration GPT variance collapse is retained rather than rerolled. Historical
best-of and superseded boards remain available, but never substitute for the
single-configuration result.

### Audits that caught our own agents

One agent found a game's 2,172-line implementation inside its workspace and
returned a natural-looking 100.00 without learning the game. A clean rerun
scored 46.91. In a second incident, all six agents in a supposed control group
found and rebuilt the harness that the experiment had removed. We voided both
claims, preserved the evidence, changed the boundaries, and added adversarial
checks over the raw session record. See [`INTEGRITY.md`](INTEGRITY.md) and
[`incidents/`](incidents/).

### A failure high scores could not reveal

A bundled planner crashed on every invocation across five experimental boards.
Agents silently wrote replacement searches and kept solving games, so score and
ledger audits stayed green. That finding separates outcome integrity from tool
integrity: autonomous self-repair can make broken infrastructure look healthy.
Kepler now executes every workspace tool in a dedicated smoke tier.

### Resource accounting, recovered from provider records

The exact 100.00 board used 1,641.2M tokens, 97.15% cache reads, and costs
$1,568.50 when its uncached input, cache reads, one-hour cache writes, and
output are priced at current Opus 5 API rates. That is 47.5% below Tycho's
$2,986 community-leaderboard cost, making Kepler the lowest disclosed bill
among the public 100.00 systems reviewed. AVO and VISTA do
not publish comparable bills.

The GPT board used 2,429.1M raw tokens. An earlier footer-based estimate was
incomplete: provider session records show that the footers omitted most cached-
input traffic and one long-running workspace. At current GPT-5.6
Sol rates the complete board is $1,312.14 list-equivalent. We corrected the
claim rather than preserving a flattering denominator.

The Opus board used 8,256 actions including learning and 7,292 in scored
attempts. The learning-inclusive count is 2.08 times fewer than the 17,135-action
first-time-human reference. The scored count is 3.3% below VISTA and 5.3% below
Retrodict; AVO remains lower at 6,624.

### A perception finding from the last resistant game

One game resisted every text-observation attempt. The agent searched roughly
410 million configurations under a model that fit more than 4,600 recorded
transitions and concluded the final level was unsolvable. The missing mechanic
existed only in transient animation frames. Exposing rendered frames, while
keeping the model, tools, and harness policy fixed, let the same model find the
rule in 57 actions. We report this as a single-game within-system intervention,
not a benchmark-wide causal result.

### A proposal for evaluation after public-set saturation

Across the two final boards, 48 of 50 game-model cells reached 100. Peak RHAE
therefore hides the remaining differences among systems. We propose reporting
cost-conditioned scores, a standardized cached-input / uncached-input / output
token triple plus dollar and wall-clock reporting, an optional first-attempt or
bounded-learning track, and replay plus trace evidence beside every community
result. See
[`docs/benchmark-observations.md`](docs/benchmark-observations.md).

## How it works

The design deliberately follows a human scientific loop: observe, hypothesize,
run a discriminating experiment, revise the theory, then act. The difference is
that every belief becomes executable evidence. The agent records every
transition, writes an executable world model, and must
retrodict the interaction history before planning. Every committed action carries
a prediction; the first mismatch voids the remaining plan and returns the
counterexample. Once a game is learned, the agent certifies per-level action
programs. A fail-closed mechanical executor, with no model in the loop, plays the
scored attempt.

A CI gate, [`scripts/check_no_game_ids.py`](scripts/check_no_game_ids.py), rejects
game IDs in agent-visible files. The intent is to enforce zero game-specific
priors mechanically instead of promising them in prose.

## Verify it

Requires Python 3.13 or newer.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e .
python3 scripts/verify.py
python3 scripts/check_no_game_ids.py
```

`scripts/verify.py` replays the bundled worked trace. Full-board verification
requires the trace dataset:

```bash
python3 scripts/verify_scores.py --traces-dir traces
python3 scripts/audit_integrity.py --traces-dir traces
```

**Dataset status:** publication is pending. Until [`release.json`](release.json)
contains a `trace_dataset` URL, a fresh clone does not contain the full run
corpus and both full-board commands intentionally exit `VACUOUS`. We state this
explicitly because the auditability claim is not complete until the data is
downloadable.

## Layout

```text
harness/        daemon, runner, directive, and agent workspace tools
scripts/        replay, integrity, score, cost, and release checks
tests/          smoke and regression tests
docs/           paper, benchmark proposal, and design notes
incidents/      integrity failures and preserved evidence
RESULTS.md      experimental history and run-selection policy
release.json    canonical public-release facts
```

## Scope and credit

Kepler builds on the executable-world-model lineage established by
[Tycho](https://github.com/NIMI-research/Tycho),
[baseline1](https://github.com/astroseger/arc-3-agents-baseline1), and
[Retrodict](https://github.com/ryanbbrown/Retrodict). Adopted mechanisms are
credited in [`NOTICE`](NOTICE). [VISTA](https://vista-research.github.io/)
motivated the observation-channel intervention.

These are public-set harness results, not evidence that ARC-AGI-3 or AGI is
solved. The semi-private and private sets remain untested. Cite via
[`CITATION.cff`](CITATION.cff). MIT license.
