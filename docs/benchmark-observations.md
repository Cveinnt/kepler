# What harness saturation reveals about ARC-AGI-3 evaluation

Notes offered to the ARC Prize community, written from the inside of building a
competitive entry. Similar public-set scores can conceal different discovery
methods, budgets and observation channels. Distinguishing those stages would
make the results more useful. These notes draw on public code and scorecards
of Tycho, Retrodict, baseline1, arc-skill, GKM, Strands, and our own runs.

## 1. Several leading harnesses separate learning from scored replay

Kepler separates learning, final-attempt execution and server verification.
Learning can include exploration and failed attempts before a short final
solution. Its scorecard then verifies a replay of that solution. These stages
answer different questions and should have separate resource accounts.

Tycho ships a "replay viewer" and scores competition-mode replays. Retrodict's
own words for its scorecard: a *"verified re-execution of the recorded runs, not
a new attempt."* GKM states plainly that **"at scoring time no model runs"** -
a frozen `final_path` is sent to the API. arc-skill's scorecard *"was produced
by replaying the recorded runs."* The Kepler release does the same: an agent certifies
per-level programs and a fail-closed executor replays them.

RHAE scores the final attempt, not superseded attempts. So the rational entry
can spend thousands of actions learning and a baseline-minimal number scoring.
This is not cheating. It is a strategy the rules permit. But final-attempt
efficiency does not reveal how efficiently the agent discovered the solution.
A replayed scorecard also does not prove that the original solver built a world
model or removed the language model from its final attempt. Direct-interaction
systems produce replayable traces too.

## 2. The public set is saturated; the discriminating axis silently became cost

Multiple systems now report 100.00 on the public set. Across Kepler's two final
boards, 48 of 50 game-model cells score a perfect 100. When the score
stops separating entries, whatever *does* separate them becomes the real
benchmark, and right now that is **cost, which is unstandardized and often
unreported.** Same public set, comparable scores:

| entry | RHAE | reported cost |
|---|---:|---:|
| baseline1 | 99.0 | $400 |
| Retrodict | 99.86 | $654 |
| Tycho | 100.0 | none disclosed; Retrodict estimates ~$2,986 API-equivalent |
| VISTA | 100.0 | not disclosed |
| NVIDIA AVO | 100.0 | not disclosed |
| Kepler, GPT board | 95.97 | $1,312.14 September 1, 2026 API list-equivalent |
| Kepler, Opus board | 100.0 | $777.72 September 1, 2026 API list-equivalent |

A large cost spread at similar scores, and the figures are self-reported or list-equivalent dollars
with no shared definition. Some include cached input, some estimate, some omit
tokens entirely. The leaderboard shows a verified score badge and no cost badge,
so the axis that now carries all the signal is the one nobody is required to
report comparably.

Kepler's retained-run API-equivalent estimate is 74.0% below the $2,986 estimate that
Retrodict published for Tycho. Tycho itself discloses no cost, and neither do
AVO or VISTA, which is the point of this section: the comparison exists only
because a third party did the estimating. It is not a claim that Kepler is
cheapest at every score, since Retrodict and baseline1 occupy lower-cost,
lower-scoring points.

## 3. Prediction-before-action emerged as a norm nobody specified

arc-skill refuses any press without a falsifiable prediction and grades it.
Retrodict requires a stated `expect` per action. Ours voids a plan on the first
misprediction. GKM admits programs only after independent replay verification.
These are related verification mechanisms, not identical contracts or a matched
reliability experiment. A useful next measurement is what happens after a
counterexample: how many actions, tokens and seconds pass before a model repair
survives another test? Kepler's sp80 case motivates that question because large
searches continued under rules that did not explain all the available evidence.
We propose measuring this response cost; we have not established a faster rate
than other systems.

## Recommendations, offered not asserted

These would make the community leaderboard measure the capability ARC-AGI-3 was
built to probe, now that harnesses saturate the proxy for it:

1. **Report a cost-conditioned score, not just a peak score.** A small RHAE-at-
   fixed-budget frontier (e.g. score at $50 / $500 / unbounded) would restore
   discrimination that the raw number has lost, and it rewards the efficiency the
   benchmark says it cares about. This is the highest-value change and the cheapest.
2. **Standardize and require a token triple:** cached input, uncached input, and
   output tokens. Report dollars at stated list prices and wall-clock beside it.
   Add a cost badge beside the score badge.
3. **Consider a bounded-learning or first-attempt track.** If replay-of-a-clean-
   trace is the dominant strategy, an explicit track that scores the *first* full
   attempt (or caps total learning actions) would measure efficient play directly
   instead of world-model-construction wearing efficiency's clothes. Keep the
   current track too. The contrast between them is itself informative.
4. **Make verification a submission requirement, not an honor system.** Scorecard
   replay plus published traces should be mandatory, because a self-reported score
   cannot distinguish a derived answer from a looked-up one. That is the exact failure our
   own audits caught twice in our own runs.
5. **Move the headline to the held-out sets.** Public-set numbers no longer
   measure generalization; several teams say so explicitly (baseline1 calls its
   result "saturation of the public set, not evidence ARC-AGI-3 is solved"). The
   semi-private/private sets are where a number still means what the benchmark
   intends.

The through-line: ARC-AGI-3 succeeded at forcing a specific, sophisticated
solution shape into existence. The evaluation can now be updated to score the
part of that shape that is the actual capability: reliable discovery under a
real budget, rather than the part harnesses have learned to make free.
