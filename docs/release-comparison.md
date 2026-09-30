# Kepler release comparison

Comparison scope corrected September 13, 2026. The original table is a
September 1 snapshot, with Tycho's first-party resource disclosure updated below;
other external entries were not re-audited in this revision. Scores, actions, costs, model
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
| Kepler | **100.00** | **8,256 retained-board-run actions; 7,292 in original local scored-level results; 7,202 on the public replay card; at least 13,688 campaign actions observed** | **$777.72 September 1, 2026 API list-equivalent** | one frozen configuration; one retained run per game |
| VISTA | 100.00 | 7,542 game actions | not disclosed | vision-first harness |
| Tycho | 100.00 | see first-party run counters; no normalized comparison here | approximately $2,986 API-equivalent for its selected Opus 5 full run | multiple model/policy results |
| Retrodict | 99.86 | 7,703 campaign actions | $654 | single public board with trace disclosure |
| baseline1 | 99.0 | not reported here | $400 | public scorecard |
| Prime Agent | 95.5 best single run | not reported here | $944 to $1,288 across published runs | three-run evidence; best@3 also reported |

**The action column is not a ranking.** AVO counts environment actions, VISTA
counts game actions, and Retrodict counts campaign actions. None of those is
defined the same way as Kepler's scored-level, retained-run, or full-campaign
counts, and published materials do not give enough detail to convert between
them. Kepler's full campaign ledger is itself incomplete by 22 prefix events,
so this release makes no external action-count ranking.

Kepler does not lead every column. Retrodict and baseline1 report lower cost estimates at
lower scores. Prime publishes stronger run-to-run variance evidence. Kepler's
defensible position is the combination:

- exact 100.00 across all 25 public games, plus a second server-exact board at
  95.97 on a different model;
- 8,256 actions in retained board runs, 7,292 in original local scored-level
  results, and 7,202 on the public replay card, with at least 13,688 non-reset
  campaign actions reported separately;
- $777.72 at September 1, 2026 API list rates, 74.0% below Retrodict's $2,986
  API-equivalent estimate for Tycho;
- one frozen configuration with no score-conditioned reruns;
- CI scanning for literal game identifiers in agent-visible files, not a test
  for semantic priors or model training exposure;
- conditional prediction checks and mechanical scored replay;
- audits that voided a source-reading win and contaminated control;
- negative results, withdrawn claims, replay seams, and tool-health failures
  retained in the release record.

## Eleven-axis evidence matrix

| Axis | Kepler release evidence |
|---|---|
| Score | Exact 100.00 on official replay |
| Human-relative performance | 181/183 Opus levels at or above median-human action efficiency; two below, with capped gains elsewhere preserving the 100.00 composite |
| Final-attempt action accounting | 7,292 actions in original local scored-level results; 7,202 on the public replay card; not a learning-speed measure |
| Campaign actions | At least 13,688 observed non-reset actions, plus 22 unavailable prefix events |
| Release-run cost estimate | $777.72 September 1, 2026 API list-equivalent, 74.0% below Retrodict's $2,986 estimate for Tycho; not a bill or total research spend |
| Selection | One frozen configuration, one run per game, failures retained |
| Priors | No literal game IDs detected in scanned agent-visible files; semantic priors and model training exposure are not excluded |
| Reaction loop | Prediction attempted before non-reset actions; usable mismatches stop the remaining plan. Exceptions and zero coverage do not block action |
| Mechanism evidence | Descriptive certify/replay stage change +2.35, not isolated causal lift; visual continuation inherited earlier learning |
| Audits | Source-read and contaminated-control claims invalidated |
| Negative results | Regression, reward hacking, replay seams, dead planner published |

## Claim boundaries

- Tycho now reports approximately $2,986 for its selected Opus 5 full run,
  consistent with Retrodict's earlier estimate. Kepler's $777.72 is 74.0% lower
  on that pricing basis. Exact counters and cache sensitivity are in the
  [resource comparison](resource-comparison.md). These unmatched retained runs
  establish neither a lowest bill nor the cheapest system at every score.
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
- The later [six-probe discovery test](research-followups.md) produced no useful
  counterexample or level progress. It adds no faster-convergence or new-method claim.
