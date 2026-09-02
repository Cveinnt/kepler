# Kepler

**100% on ARC-AGI-3 at one-fourth the cost. One frozen configuration.**

Kepler is an open-source agent harness for the 25 public ARC-AGI-3 games. One
frozen Claude Opus 5 configuration scored **100.00**, with every game
re-executed to 100 by ARC Prize's official server replay. There was no per-game
model selection and no score-conditioned rerun. The cost headline compares
$777.72 at current standard API list-equivalent rates with Retrodict's $2,986
API-equivalent estimate for Tycho; Tycho did not publish a bill.

| Model | Score | Evidence | Resource record |
|---|---:|---|---:|
| Claude Opus 5 | **100.00** | [Server-verified exact](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1) | 8,256 retained-board-run actions; 858.0M tokens; $777.72 current API list-equivalent |
| GPT-5.6 Sol (max) | **95.97** | [Server-verified exact](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685) | 35,896 actions; 2,429.1M tokens; $1,312.14 current API list-equivalent |

This repository has one public release identity: **Kepler 1.0**. Earlier
experimental configurations remain in [`RESULTS.md`](RESULTS.md) as ablation
evidence, not as competing product versions. Canonical release facts live in
[`release.json`](release.json).

## What is different

Three claims define the release:

1. **The result was selected before the score.** One model, one commit-frozen
   harness, one pass over 25 games, no score-conditioned reruns.
2. **The result has an official receipt.** ARC Prize re-executed every game to
   100.00. The [public final-board trace release](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces)
   includes human baselines and dependency-free scorers so both boards can be
   recomputed from their action records.
3. **The audit is allowed to win.** A source-reading 100 and a contaminated
   control were voided. A dead planner is reported even though agents repaired
   around it and kept scoring well.

[Inspect the full evidence matrix](#full-evidence-matrix) or
[run the verification path](#verify-it).

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

The exact 100.00 campaign used 858,041,926 tokens, 97.37% cache reads, and
costs $777.72 when its uncached input, cache reads, one-hour cache writes,
and output are priced at current Opus 5 API rates. That is 74.0% below the
$2,986 API-equivalent estimate Retrodict published for Tycho. Tycho does not
publish a cost figure of its own, and AVO and VISTA disclose none, so this is
a comparison against one third-party estimate rather than a ranking of the
field.

The GPT board used 2,429.1M raw tokens. An earlier footer-based estimate was
incomplete: provider session records show that the footers omitted most cached-
input traffic and one long-running workspace. At current GPT-5.6
Sol rates the complete board is $1,312.14 list-equivalent. We corrected the
claim rather than preserving a flattering denominator.

The retained Opus board runs used 8,256 environment actions, with 7,292 in
scored levels. That is not the complete campaign count. The local ledgers
contain at least 13,688 non-reset actions and omit 22 prefix events whose reset
status cannot yet be recovered. We therefore do not call 8,256
learning-inclusive or publish a first-time-human percentage. Published action
counts from AVO, VISTA, and Retrodict also cover different stages and
definitions, so ranking them would compare unlike quantities.

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

## Full evidence matrix

| Wedge | Measured claim |
|---|---|
| Server-verified on two models | Claude Opus 5 at 100.00 and GPT-5.6 Sol at 95.97, both exact on ARC Prize's official replay. On the Opus board, 181 of 183 completed levels used no more actions than the median-human baseline; two used more, while capped gains elsewhere preserved the 100.00 composite. |
| One frozen configuration, no cherry-picking | One model, one commit-frozen harness registered before results existed, one pass over 25 games, no score-conditioned reruns. The GPT board keeps its same-configuration collapse. |
| Action accounting without a flattering denominator | 8,256 actions in the retained board runs and 7,292 in scored levels. Full campaign logs contain at least 13,688 non-reset actions plus 22 unavailable prefix events, so we do not call 8,256 learning-inclusive or compare it with another system's campaign total. |
| Lower comparable cost | $777.72 at current Opus 5 API list rates, 74.0% below Retrodict's $2,986 API-equivalent estimate for Tycho. Tycho publishes no cost figure of its own; AVO and VISTA disclose none. |
| Convergence across final boards | Certify/replay added 2.35 board points. Across the two release boards, 48 of 50 game-model cells reach 100. This is within-system convergence on the public set, not independent replication. |
| Audit discipline | Six adversarial checks run over the retained session record before release. A source-reading win and a contaminated control were voided, and a dead planner exposed a separate tool-integrity blind spot. The audit is evidence-bounded: it cannot detect events the client did not retain. |
| Reward hacking, disclosed | An agent read 2,172 lines of game source inside its workspace and returned a natural-looking 100.00. That run was voided and quarantined, and it is not part of the release board. |
| Human-like interaction design | Observe, hypothesize, run a discriminating experiment, revise on the first counterexample, then act. Every belief is executable code, retrodicted against the full history, and every committed action carries a checked prediction. |
| Saturation points at the evaluator | With 48 of 50 cells at 100, peak RHAE no longer separates systems. Our own hardest game turned on what the observation channel discarded, which suggests observation-channel and evaluator quality now carry the signal. |

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

`scripts/verify.py` replays the bundled worked trace. To verify both public
boards from their 50 run ledgers, download the
[trace dataset](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces):

```bash
hf download cveinnt/kepler-arc-agi-3-traces --repo-type dataset --local-dir traces
python3 traces/score_trajectories.py traces
python3 traces/verify_scores.py --traces-dir traces
python3 traces/audit_integrity.py --traces-dir traces
```

The dataset contains the two final 25-game boards: 50 run records and 58,098
environment events, plus final notebooks, world models, and captured CLI logs.
The export also includes captured CLI output for every final-board workspace.
A clean behavioral scan applies to those retained records and its published
pattern set; it cannot prove that a client retained every event or that every
possible violation is detectable. Earlier stages, failures, and
superseded runs remain documented in [`RESULTS.md`](RESULTS.md) and
[`incidents/`](incidents/); they are not in this final-board dataset.

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
