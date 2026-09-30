# Kepler: what the evidence establishes

Public clarification, September 30, 2026. This revises interpretation and
documentation, not the frozen harness or reported scorecards.

## Evaluation mode matters

The [ARC-AGI-3 technical report, v2, April 17, 2026](https://arxiv.org/html/2603.24621v2)
imposes a five-times-human-baseline per-level action budget in Section 4.3.
Section 5 describes first-exposure human testing. Our earlier statement that
the official cutoff did not exist was wrong. A server accepting a replay does
not refute the evaluation-run budget.

Kepler developed on the 25 public games and submitted final solution segments
for replay. Successful replay confirms those recorded solutions and scores;
it does not establish first-exposure efficiency, official leaderboard
eligibility, private-set performance, or held-out generalization. The open
[community leaderboard PR](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/53)
is not an accepted listing. Historical experiment notes retain their original
language; this clarification supersedes their benchmark-rule interpretation.

## Failure, check, and blind spot

| Observed failure | Relevant check | What it cannot establish |
|---|---|---|
| Source-reading invalid perfect run | Retained-log access-pattern scan and workspace boundary audit | Missing logs and unrecognized access cannot be ruled out; file placement is not isolation |
| Control agents reconstructed removed harness | Filesystem/tool-call evidence; invalidate comparison | No causal harness effect can be inferred from the contaminated control |
| Broken planner silently replaced by agents | Direct bundled-tool smoke tests | A high score alone does not prove intended tools ran or worked |
| Predicted transition mismatch | Conditional interruption in commit/replay paths | Exceptions and zero coverage can permit action; no unconditional fail-closed guarantee |
| Off-grid click rejected during server replay | Coordinate checks and server replay | Clean-run certification checks coordinates only in its threaded-model branch |
| Missing or reconstructed certification start | Inspect actual recorded starts and model API | A model-created start is not a verified environment start |
| Missing campaign accounting | Distinct retained-run, final-segment, and provider usage records | Final replay actions are not full learning cost |

Retrodict, Tycho and other systems already use executable models, replay and
prediction checks. Kepler's contribution is the auditable release and concrete
evaluation failure analysis, not invention of those mechanisms, true internal
belief recovery, or a demonstrated causal reliability improvement.

## Reproduction and resource limits

The [public dataset](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces)
contains 50 final-board run records, 58,098 environment events, human baselines,
and 95 captured CLI logs. Log depth is uneven. It does not include every
historical development run, internal event, or private provider-session record.
Offline scorers reproduce final-board scores; fixed-pattern integrity checks
apply only to retained evidence. The IAB review submission was PDF-only, a
separate packaging limitation from public data availability.

The $777.72 Opus estimate uses September 1, 2026 API list prices and retained
release-run usage, not actual subscription bills or total research spending.
Retrodict's $2,986 estimate for Tycho is consistent with Tycho's later reported
approximately $2.99k. The roughly four-fold cost difference and 61.7% fewer
output tokens are unmatched aggregate comparisons, not isolated harness effects.

Later exploratory work has not established a new adaptation or generalization
gain. No negative result is relabeled as a positive contribution in this release.

## Paper and workshop status

The paper was accepted to the non-archival Interpreting Agent Behavior workshop
at NeurIPS 2026. This is not main-conference acceptance, an award, or a confirmed
presentation format. This public revision is not a camera-ready submission
receipt. See the [paper and citation record](https://kepler-harness.vercel.app/paper/).
