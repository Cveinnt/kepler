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

| System | Public result | Reported actions | Disclosed cost | Run-selection note |
|---|---:|---:|---:|---|
| NVIDIA AVO | 100.00 | 6,624 environment actions | not disclosed | general-purpose transfer evaluation |
| Kepler | **100.00** | **8,256 retained-board-run actions; 7,292 in scored levels; at least 13,688 campaign actions observed** | **$777.72 current API list-equivalent** | one frozen configuration; one retained run per game |
| VISTA | 100.00 | 7,542 game actions | not disclosed | vision-first harness |
| Tycho | 100.00 | not reported in compared materials | none disclosed; Retrodict estimates $2,986 API-equivalent | multiple model/policy results |
| Retrodict | 99.86 | 7,703 campaign actions | $654 | single public board with trace disclosure |
| baseline1 | 99.0 | not reported here | $400 | public scorecard |
| Prime Agent | 95.5 best single run | not reported here | $944 to $1,288 across published runs | three-run evidence; best@3 also reported |

**The action column is not a ranking.** AVO counts environment actions, VISTA
counts game actions, and Retrodict counts campaign actions. None of those is
defined the same way as Kepler's scored-level, retained-run, or full-campaign
counts, and published materials do not give enough detail to convert between
them. Kepler's full campaign ledger is itself incomplete by 22 prefix events,
so this release makes no external action-count ranking.

Kepler does not lead every column. Retrodict and baseline1 report lower bills at
lower scores. Prime publishes stronger run-to-run variance evidence. Kepler's
defensible position is the combination:

- exact 100.00 across all 25 public games, plus a second server-exact board at
  95.97 on a different model;
- 8,256 actions in retained board runs and 7,292 in scored levels, with at least
  13,688 non-reset campaign actions reported separately;
- $777.72 at current API list rates, 74.0% below Retrodict's $2,986
  API-equivalent estimate for Tycho;
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
| Human-relative performance | 181/183 Opus levels at or above median-human action efficiency; two below, with capped gains elsewhere preserving the 100.00 composite |
| Scored convergence | 7,292 actions in scored levels |
| Campaign actions | At least 13,688 observed non-reset actions, plus 22 unavailable prefix events |
| Perfect-score bill | $777.72 current API list-equivalent, 74.0% below Retrodict's $2,986 estimate for Tycho |
| Selection | One frozen configuration, one run per game, failures retained |
| Priors | Zero game-specific priors on agent-visible surfaces, CI-enforced |
| Reaction loop | Prediction on every committed action; first mismatch stops plan |
| Mechanism evidence | Certify/replay stage +2.35; scoped visual intervention |
| Audits | Source-read and contaminated-control claims invalidated |
| Negative results | Regression, reward hacking, replay seams, dead planner published |

## Claim boundaries

- "74.0% below Retrodict's $2,986 API-equivalent estimate for Tycho" is
  supported. "Tycho disclosed $2,986" is not; Retrodict produced that estimate.
  "Lowest disclosed bill" and "cheapest ARC system" are not supported either,
  since AVO and VISTA disclose no cost at all.
- "8,256 learning-inclusive actions" and "51.8% fewer than a first-time human"
  are not supported by the full campaign logs. Any ranking of Kepler's action
  counts against AVO, VISTA, Retrodict, or the human reference is withheld until
  the missing campaign prefix events are recovered.
- Exact 100.00 is a capped composite, not a guarantee that every level beats
  the median-human action count. The Opus board has 181 of 183 levels at or
  above that threshold. This is not human equivalence or held-out generalization.
- The rendered-frame result is a single-game within-system intervention, not a
  benchmark-wide modality ablation.
- The public companion dataset contains both final 25-game boards: 50 run
  records, 58,098 environment events, baselines, final artifacts, captured CLI
  output, and standalone verifiers. It does not contain
  the complete historical development archive.
