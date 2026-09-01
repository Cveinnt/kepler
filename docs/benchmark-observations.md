# What harness saturation reveals about ARC-AGI-3 evaluation

Notes offered to the ARC Prize community, written from the inside of building a
competitive entry. Not a critique of the benchmark — the opposite: ARC-AGI-3's
design is sound enough that seven independent teams converged on the *same* way
of beating its public set, and that convergence is itself a measurement result
worth acting on. Everything below is drawn from the public code and scorecards
of Tycho, Retrodict, baseline1, arc-skill, GKM, Strands, and our own runs.

## 1. Every serious harness has stopped playing the game and started replaying it

The single strongest commonality across the top of the leaderboard is not a
model, a prompt, or a search algorithm. It is a *segmentation trick* that the
metric permits and therefore every entry adopts:

- learn the game across an unbounded number of actions and attempts (unscored),
- then emit a clean, minimal action sequence and **replay it as the scored attempt.**

Tycho ships a "replay viewer" and scores competition-mode replays. Retrodict's
own words for its scorecard: a *"verified re-execution of the recorded runs, not
a new attempt."* GKM states plainly that **"at scoring time no model runs"** —
a frozen `final_path` is sent to the API. arc-skill's scorecard *"was produced
by replaying the recorded runs."* Our own v5 does the same: an agent certifies
per-level programs and a 176-line executor replays them.

RHAE scores only the final attempt. So learning efficiency is worth exactly
nothing, and the rational entry spends thousands of actions learning and a
baseline-minimal number scoring. This is not cheating — it is the dominant
strategy the rules define. But it means **the public-set RHAE number measures
"can a frontier model eventually build a correct world model of this game,"
not "can an agent play efficiently."** Those are different capabilities, and the
headline number is now reporting the first while appearing to report the second.

## 2. The public set is saturated; the discriminating axis silently became cost

Nine entries are at or above 95, five at or above 99, two at 100. Under one
frozen harness we see 43 of 50 game-model cells at a perfect 100. When the score
stops separating entries, whatever *does* separate them becomes the real
benchmark — and right now that is **cost, which is unstandardized and often
unreported.** Same public set, comparable scores:

| entry | RHAE | reported cost |
|---|---:|---:|
| baseline1 | 99.0 | $400 |
| Retrodict | 99.86 | $654 |
| arc-skill | 100.0 | $728 |
| Strands | 99.95 | $830 |
| Tycho | 100.0 | ~$2,986 (est.) |

A 7x cost spread at the same score, and the figures are self-reported dollars
with no shared definition — some include cached input, some estimate, some omit
tokens entirely. The leaderboard shows a verified score badge and no cost badge,
so the axis that now carries all the signal is the one nobody is required to
report comparably.

## 3. Prediction-before-action emerged as a norm nobody specified

arc-skill refuses any press without a falsifiable prediction and grades it.
Retrodict requires a stated `expect` per action. Ours voids a plan on the first
misprediction. GKM admits programs only after independent replay verification.
Four teams independently arrived at "the harness must force the agent to state
and grade a prediction before every action" — a concrete, transferable finding
about *how to make a coding agent reliable on interactive tasks* that the
benchmark neither requires nor measures, but which its top entries all discovered.

## Recommendations, offered not asserted

These would make the community leaderboard measure the capability ARC-AGI-3 was
built to probe, now that harnesses saturate the proxy for it:

1. **Report a cost-conditioned score, not just a peak score.** A small RHAE-at-
   fixed-budget frontier (e.g. score at $50 / $500 / unbounded) would restore
   discrimination that the raw number has lost, and it rewards the efficiency the
   benchmark says it cares about. This is the highest-value change and the cheapest.
2. **Standardize and require a cost triple** — total tokens, dollars at stated
   list prices, and wall-clock — with cached input reported separately. A cost
   badge beside the score badge.
3. **Consider a bounded-learning or first-attempt track.** If replay-of-a-clean-
   trace is the dominant strategy, an explicit track that scores the *first* full
   attempt (or caps total learning actions) would measure efficient play directly
   instead of world-model-construction wearing efficiency's clothes. Keep the
   current track too — the contrast between them is itself informative.
4. **Make verification a submission requirement, not an honor system.** Scorecard
   replay plus published traces should be mandatory, because a self-reported score
   cannot distinguish a derived answer from a looked-up one — the exact failure our
   own audits caught twice in our own runs.
5. **Move the headline to the held-out sets.** Public-set numbers no longer
   measure generalization; several teams say so explicitly (baseline1 calls its
   result "saturation of the public set — not evidence ARC-AGI-3 is solved"). The
   semi-private/private sets are where a number still means what the benchmark
   intends.

The through-line: ARC-AGI-3 succeeded at forcing a specific, sophisticated
solution shape into existence. The evaluation can now be updated to score the
part of that shape that is the actual capability — reliable discovery under a
real budget — rather than the part harnesses have learned to make free.
