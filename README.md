# Kepler

**100% on ARC-AGI-3 at one-fourth the cost.**

**Scores can stay green while an experiment breaks.** Kepler pairs executable
world models with replay evidence, tool checks, and documented evaluation failures.
The paper was accepted to the non-archival Interpreting Agent Behavior workshop
at NeurIPS 2026, not the NeurIPS main conference. The September 30 public revision
corrects protocol and enforcement claims; it does not add a new performance result.
Read the [paper and citation record](https://kepler-harness.vercel.app/paper/)
and [evidence boundaries](docs/evidence-boundaries.md).

Our scores concern public-development and final replay segments, not official
first-exposure evaluation. ARC Prize's report does impose a 5× human-baseline
per-level evaluation budget; server replay acceptance does not disprove it.

Kepler is an open-source agent harness for the 25 public ARC-AGI-3 games. One
frozen Claude Opus 5 configuration scored **100.00**, with every game
re-executed to 100 by ARC Prize's official server replay. There was no per-game
model selection and no score-conditioned rerun. The cost headline compares
$777.72 at September 1, 2026 API list-equivalent rates with Retrodict's $2,986
API-equivalent estimate for Tycho; Tycho did not publish a bill.

| Model | Score | Evidence | Resource record |
|---|---:|---|---:|
| Claude Opus 5 | **100.00** | [Server-verified exact](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1) | 8,256 retained-board-run actions; 858.0M tokens; $777.72 September 1, 2026 API list-equivalent |
| GPT-5.6 Sol (max) | **95.97** | [Server-verified exact](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685) | 35,896 actions; 2,429.1M tokens; $1,312.14 September 1, 2026 API list-equivalent |

**Start here:** [Project page](https://kepler-harness.vercel.app/) ·
[Paper](docs/paper/latex/main.pdf) · [Reproduce the result](#verify-it) ·
[Trace dataset](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces) ·
[Integrity record](INTEGRITY.md)

This repository has one public release identity: **Kepler 1.0**. Earlier
experimental configurations remain in [`RESULTS.md`](RESULTS.md) as ablation
evidence, not as competing product versions. Canonical release facts live in
[`release.json`](release.json).

## What is different

Five facts define the release:

1. **100.00 with one setup.** One model, one commit-frozen harness, one
   retained run per public game, no score-conditioned reruns.
2. **Lower cost and fewer generated tokens in the retained run.** $777.72
   list-equivalent cost versus Tycho's reported $2,986; 9.0M output tokens
   versus 23.4M, a 61.7% reduction. These are unmatched retained runs, not
   research bills or a controlled harness comparison. See the
   [resource comparison](docs/resource-comparison.md).
3. **Short final solutions.** On 181 of 183 completed Opus levels, the final
   attempt used no more actions than the median-human baseline. Discovery and
   retries still cost work; this is not a faster-learning result.
4. **A simulator you can inspect.** The commit tool attempts a prediction from the
   executable world model before acting. A usable prediction's first mismatch
   stops the plan and becomes a counterexample. Prediction failures and zero
   coverage are logged but do not prevent action. Score replay, trajectory integrity, tool health, selection,
   and resource accounting remain separate checks.
5. **Failures included.** A source-reading 100 and a contaminated control were
   voided. A dead planner is reported even though agents repaired around it and
   kept scoring well. The missing-animation case shows how extensive search can
   stall under incomplete rules. Read the
   [game walkthrough and engineering story](https://www.wensenwu.com/thoughts/kepler).

Across both frozen boards, 48 of 50 game-model cells reached 100. These are
public-set results, not held-out evidence. Executable world models are an
established approach; the release combines this result with inspectable models,
trajectories, accounting, and documented failure cases.

ARC Prize re-executed every game in the Opus release board to 100.00. The
[public final-board trace release](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces)
includes human baselines and dependency-free scorers so both boards can be
recomputed from their action records.

[Inspect the full evidence matrix](#full-evidence-matrix) or
[run the verification path](#verify-it).

The release does not establish faster rule discovery or an autonomous
self-improving harness. A later six-probe native test found no useful new rule
or level progress; it does not change the release scores or cost totals.
[Follow-up result and scope](docs/research-followups.md).

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

### The experimental subject was also the lab technician

A bundled planner crashed on every invocation across five experimental boards.
Agents silently wrote replacement searches and kept solving games, so score and
ledger audits stayed green. That finding separates outcome integrity from tool
integrity: autonomous self-repair can make broken infrastructure look healthy.
Kepler now executes every workspace tool in a dedicated smoke tier.

This is not an autonomous self-improving harness. The outer harness did not
choose and retain its own revisions. The narrower result is more useful:
capable agents improved their working artifacts and repaired around broken
infrastructure, making the system more successful while making the intended
experiment less informative.

### Resource accounting, recovered from provider records

The retained Opus release runs used 858,041,926 tokens, 97.37% cache reads,
and cost $777.72 when their uncached input, cache reads, one-hour cache writes,
and output are priced at September 1, 2026 Opus 5 API rates. This is a list-equivalent
reconstruction, not cash spend or the cost of the full research campaign. It is
74.0% below the
$2,986 API-equivalent estimate Retrodict published for Tycho. [Tycho's own
paper](https://arxiv.org/html/2607.28287) now reports approximately $2.99k for
its Opus 5 run, with token accounting and budget curves. These estimates are
not bills or a controlled harness comparison, and do not rank the whole field.

The GPT board used 2,429.1M raw tokens. An earlier footer-based estimate was
incomplete: provider session records show that the footers omitted most cached-
input traffic and one long-running workspace. At September 1, 2026 GPT-5.6
Sol rates the complete board is $1,312.14 list-equivalent. We corrected the
claim rather than preserving a flattering denominator.

The retained Opus board runs used 8,256 environment actions, with 7,292 in
the original local scored-level results. ARC's public replay card reports 7,202
actions. The GPT equivalents are 8,400 local scored-level actions and 8,220 on
the public replay card. These are different recorded denominators, not score
disagreements: replay uses the last full-reset-to-end ledger segment and counts
a new opening reset. Three runs contain a later, shorter certified segment than
the original result file. Both final server scores match exactly.

None of those figures is the complete campaign count. The local ledgers
contain at least 13,688 non-reset actions and omit 22 prefix events whose reset
status cannot yet be recovered. We therefore do not call 8,256
learning-inclusive or publish a first-time-human percentage. Published action
counts from AVO, VISTA, and Retrodict also cover different stages and
definitions, so ranking them would compare unlike quantities.

### A perception finding from the last resistant game

On sp80, nineteen text-mode sessions left the final level unsolved. The agent
reported searching roughly 410 million configurations under incomplete rules.
A visual continuation inherited its notes and identified a deflection mechanic
visible during animation. Its final successful attempt used 57 actions, not
counting discovery. Earlier animation counts also contained clues, so this does
not establish that images were necessary. The
[interactive walkthrough](https://www.wensenwu.com/thoughts/kepler) shows the
retained winning drop and the mechanic the agent had missed.

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
| Score and human-relative execution | Claude Opus 5 at 100.00 and GPT-5.6 Sol at 95.97, both exact on ARC Prize's official replay. On the Opus board, 181 of 183 completed levels used no more actions than the median-human baseline; two used more. This is final-attempt action efficiency, not discovery efficiency or human-like cognition. |
| Frozen selection policy | One model, one commit-frozen harness registered before the 25-run release board, one retained run per game, no score-conditioned reruns. The GPT board keeps its same-configuration collapse. |
| Action accounting without a flattering denominator | 8,256 actions in the retained board runs, 7,292 in the original local scored-level results, and 7,202 on ARC's public replay card. Full campaign logs contain at least 13,688 non-reset actions plus 22 unavailable prefix events, so we do not call 8,256 learning-inclusive or compare it with another system's campaign total. |
| Scoped cost comparison | $777.72 at September 1, 2026 Opus 5 API list rates, 74.0% below Retrodict's $2,986 estimate for Tycho. Tycho's own paper reports approximately $2.99k. Different accounting and runs, not a controlled harness comparison. |
| Public-set score saturation | Across the two frozen release configurations, 48 of 50 game-model cells reach 100. This is concentration at the public-set ceiling, not faster learning, causal harness lift, or independent replication. The certify/replay stage's +2.35-point change remains a descriptive stage delta because adjacent changes were not held constant. |
| Audit regression and incident record | A deterministic code-level suite detects 11 of 13 hand-built threat fixtures and flags none of five benign controls. Separately, a source-reading win and a contaminated control were voided, and a dead planner exposed a tool-integrity blind spot. The suite is not a field sensitivity estimate and cannot detect events the client did not retain. |
| Reward hacking, disclosed | An agent read 2,172 lines of game source inside its workspace and returned a natural-looking 100.00. That run was voided and quarantined, and it is not part of the release board. |
| Human-style scientific loop | Observe, hypothesize, test, revise, then act. Executable world models support full-history backtests and prediction-based plan interruption. Prediction failures and zero coverage do not block action, so this is not universal verified execution. |
| Saturation points at the evaluator | With 48 of 50 cells at 100, peak RHAE no longer separates systems. Our own hardest game turned on what the observation channel discarded, which suggests observation-channel and evaluator quality now carry the signal. |

## How it works

The design deliberately follows a human scientific loop: observe, hypothesize,
run a discriminating experiment, revise the theory, then act. The difference is
that selected hypotheses become executable artifacts. The daemon records
transitions; the agent writes a model and is instructed to backtest the
interaction history before planning, not mechanically forced to rerun that
backtest before every commit. For non-reset actions, the
commit tool attempts a prediction; a usable prediction's first mismatch voids
the remaining plan and returns the counterexample. If prediction fails or covers
no cells, the action still executes with a warning. Once a game is learned, the agent certifies per-level action
programs. A mechanical executor with conditional checks, with no model in the loop, plays the
scored attempt.

A CI gate, [`scripts/check_no_game_ids.py`](scripts/check_no_game_ids.py), rejects
literal game IDs in agent-visible files. It does not prove the absence of encoded
game knowledge or model-training exposure.

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

These are public-set harness results, and the public games were both development
material and evaluation surface. They are not evidence that ARC-AGI-3 or AGI is
solved. The semi-private and private sets remain untested. We cannot inspect
provider training corpora, so we do not claim the models had no prior exposure
to the public games. Cite via
[`CITATION.cff`](CITATION.cff). MIT license.
