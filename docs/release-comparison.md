# Kepler release comparison

Public-source comparison refreshed 2026-09-01. Scores, actions, costs, model
access, and run-selection methods are not interchangeable. This document keeps
each denominator explicit.

Sources:

- [ARC Prize community leaderboard](https://arcprize.org/leaderboard/community)
- [ARC-AGI-3 methodology](https://docs.arcprize.org/methodology)
- [NVIDIA AVO](https://developer.nvidia.com/blog/nvidia-avo-reaches-100-on-arc-agi-3-demonstrating-a-frontier-level-general-purpose-architecture-for-long-horizon-autonomous-agents/)
- [VISTA](https://vista-research.github.io/)
- [Tycho](https://github.com/NIMI-research/Tycho)
- [Retrodict](https://github.com/ryanbbrown/Retrodict)
- [Prime Agent](https://www.primeintellect.ai/blog/prime-agent)

## Headline comparison

| System | Public result | Actions | Disclosed cost | Run-selection note |
|---|---:|---:|---:|---|
| NVIDIA AVO | 100.00 | 6,624 | not disclosed | general-purpose transfer evaluation |
| Kepler | **100.00** | **7,292 scored; 8,256 incl. learning** | **$1,568.50 current API list-equivalent** | one frozen configuration; one retained run per game |
| VISTA | 100.00 | 7,542 | not disclosed | vision-first harness |
| Tycho | 100.00 | not reported in compared materials | $2,986 estimate | multiple model/policy results |
| Retrodict | 99.86 | 7,703 | $654 | single public board with trace disclosure |
| baseline1 | 99.0 | not reported here | $400 | public scorecard |
| Prime Agent | 95.5 best single run | not reported here | $944 to $1,288 across published runs | three-run evidence; best@3 also reported |

Kepler does not lead every column. AVO reports fewer actions. Retrodict and
baseline1 report lower bills at lower scores. Prime publishes stronger
run-to-run variance evidence. Kepler's defensible position is the combination:

- exact 100.00, meaning every public level at or above median-human action
  efficiency;
- 7,292 scored actions, 3.3% below VISTA and 5.3% below Retrodict;
- the lowest disclosed bill among the public 100.00 systems reviewed, 47.5%
  below Tycho's estimate;
- one frozen configuration with no score-conditioned reruns;
- zero game priors enforced in CI;
- prediction-gated actions and mechanical scored replay;
- audits that voided a source-reading win and contaminated control;
- negative results, withdrawn claims, replay seams, and tool-health failures
  retained in the release record.

## Eleven-axis evidence matrix

| Axis | Kepler release evidence |
|---|---|
| Score | Exact 100.00 on official replay |
| Human-relative performance | Every level at or above median-human action efficiency |
| Scored convergence | 7,292 actions |
| Learning-inclusive actions | 8,256, 51.8% below first-time-human 17,135 |
| Perfect-score bill | $1,568.50 current API list-equivalent |
| Selection | One frozen configuration, one run per game, failures retained |
| Priors | Zero game-specific priors on agent-visible surfaces, CI-enforced |
| Reaction loop | Prediction on every committed action; first mismatch stops plan |
| Mechanism evidence | Certify/replay stage +2.35; scoped visual intervention |
| Audits | Source-read and contaminated-control claims invalidated |
| Negative results | Regression, reward hacking, replay seams, dead planner published |

## Claim boundaries

- "Lowest disclosed perfect-score bill" is supported. "Cheapest ARC system" is
  not.
- "Faster scored convergence than VISTA and Retrodict" is supported. "Fewest
  actions" is not because AVO reports 6,624.
- "Median-human-or-better action efficiency on every level" is the meaning of
  exact 100.00 under RHAE. It is not human equivalence or held-out
  generalization.
- The rendered-frame result is a single-game within-system intervention, not a
  benchmark-wide modality ablation.
- Complete traces remain pending. Until the dataset URL is live, the release is
  not independently auditable end to end from a fresh clone.
