# Harness improvements — what the systems that beat us on the same model do differently

Comparative study, 2026-08-26. Sources: Retrodict v2.0 release traces + `experiments.md`,
arc-skill SKILL.md, baseline1 (ewma_sv v1.6) papers, Tycho repo/paper, Strands README,
GKM PR #37. Our data: `runs-v5/` ledgers + Claude/Codex session transcripts.

## Where our points went (v5)

| board | game | score | cause (from ledger) |
|---|---|---|---|
| GPT | sp80 | 4.5 | 15,915 actions, 9,783 on one level, **0 resets**; full restart refused 139× (bug, below) |
| GPT | bp35 | 56.4 | `--max-hours 8` killed the run at 8/9 with L9 underway (299 actions in) |
| GPT | cd82 / s5i5 / ka59 | 95.8 / 96.3 / 98.1 | won live with ONE over-baseline level; no clean run because `--clean-run-min 95` |
| GPT | cn04 | 98.8 | clean run executed; residual on two levels |
| Opus | sp80 | 71.4 | L6 missing mechanic; exhaustive search proved the rule set incomplete; operator deadline |

Retrodict (GPT-5.6 Sol, same model): sp80 253 actions 6/6, bp35 582 actions 9/9, cd82 74, s5i5 312, ka59 333.

## Ranked mechanisms

1. **Bug: `full_reset` stripped before the consecutive-RESET guard** (`commit.py` plan normalization).
   The documented escape hatch was unreachable in every v5 run. Fixed. Expected effect: removes a
   trap that turned "restart and replay certified levels" into "grind the current level forever".
2. **Clean-run trigger at 95 → 100.** Three GPT games sat 2–4 points under 100 with a cheap one-level
   repair and never entered the optimization phase. Fixed (`--clean-run-min 100`). Zero cost on
   perfect games (the certifier fails closed if no shorter program exists). Expected: +~0.4 composite
   on the GPT board, and it generalizes to every future board.
3. **Binding escalation injected into every session prompt** (Retrodict's ladder). Ours prints
   ESCALATION_TEXT from commit.py; theirs re-injects the directive into every model invocation until
   the level completes, with par-free triggers (≥2 self-resets OR ≥300 actions on a level). Their
   measured effect: bp35 L8 ~800 → 59 actions; lf52 reset-thrash → model-first. Our sp80 GPT run is
   the exact failure shape (live "assumed → ruled out" loops, 0 resets, one level, 9,783 actions).
   Implementation: run_game.py reads the level's action/reset counters from the ledger and prepends
   the directive to the session prompt while stuck. Game-agnostic.
4. **Finish-the-game wall-clock policy.** Never kill a run that is on its final level; `--max-hours`
   becomes a soft limit that extends while levels are still completing. bp35 alone: 56 → likely 100
   (completion cap 80 → 100 as Retrodict documented on the same game).
5. **Gate stuck-level prose behind the escalation state** (Retrodict's regression finding: always-on
   anti-pruning text doubled early-level cost). Our 227-line directive is always-on. Split into a base
   doctrine + an escalation tier delivered only when stuck. Expected: cheaper early levels (our GPT
   bp35 L1/L2 scored 60/40 RHAE vs Retrodict's 115/104 on the same deterministic levels).
6. **"Residual-first" rule for exhausted state graphs** (generic; from the Opus sp80 post-mortem and
   Retrodict's trace). When search proves the goal unreachable under the current rules, the missing
   mechanic is almost always an affordance of an object already treated as passive, and the tell is an
   animation residual the model does not reproduce. Direct the agent to frame-diff residuals before
   any further placement enumeration. (No game-specific content enters the harness — the CI gate
   stays the arbiter.)
7. **Orchestrator split** (Tycho: actor delegates world-model building to a subagent; +3 RHAE over a
   single actor on Opus 4.8). Larger change, uncertain transfer to CLI agents; park behind 1–6.

## Experiment plan (needs approval — paid quota)

- v6 = 1 + 2 + 3 + 4 (+5 if time). Freeze hash registered in RESULTS.md before any board result.
- Validation first, labeled as validation: GPT on sp80, bp35, cd82, s5i5, ka59 (the five sub-100).
- If validation converts ≥3 of 5, run the full 25-game GPT board (single config, ~18–25M tokens) and
  the Opus board. Both stay single-config; v5 boards stay published; no score-conditioned reruns.

## Second pass (2026-08-26): what the other five harnesses have that we still don't

Read in full: baseline1/ewma_sv v1.6 (prompts + controller), Tycho (actor/builder
prompts), Strands (PRO-LONG + log-access analysis), Prime Agent, NOOA (nooa ARC
example). Ranked by expected value to us:

1. **Scheduled world-model SIMPLIFICATION (baseline1 — the standout).** ewma_sv's
   controller periodically injects a dedicated simplification pass: "Assume the
   real game mechanics are simpler than the current implementation... Do not
   defend the current model... Replace case-by-case behaviour with shared
   parameterised rules... ask what simpler mechanic would make the special
   handling unnecessary." Three escalating step prompts + a light level-1 pass.
   This is the exact counter-move to our sp80 failure mode: our agent built an
   ever-more-baroque rule set and then exhaustively proved it unsolvable —
   nothing in our directive ever pushes it to COMPRESS the model. baseline1
   scores 99.0 on GPT-5.6 with this as a headline treatment (their paper02 title
   is literally about world models + simplification + verification).
2. **The "assume simple" prior in trouble interventions (baseline1).** Their
   stuck prompt leads with "every level should be solvable in a single attempt;
   the solution is likely simple; you may be overthinking" — the opposite
   emphasis from our escalation text, which pushes MORE machinery (simulate,
   search, inventory). Both are right in different failure modes; ours lacks the
   simplicity direction entirely.
3. **Outcome as a first-class inference (Tycho).** The builder prompt: infer the
   objective "from what changed at the moments a level ended, not from whatever
   changes"; typed evidence (death_events, terminal_events, per-attempt archives)
   makes level-end frames a distinguished evidence class. Our directive never
   explicitly says "derive the goal from level_up/GAME_OVER diffs."
4. Already parked: Tycho's actor/builder orchestration (+3 RHAE in their ablation).
5. Validating-but-not-adoptable: Strands' access-pattern analysis shows `compare`
   (predicted-vs-actual) in only 5% of their agent's scripts — i.e. the thing our
   guarded channel enforces on every action is what their agent almost never does
   voluntarily. Keep as evidence for the prediction-gating norm, not a to-do.

Adoption discipline: nothing changes while round-2 validation is in flight.
Candidates 1-3 are prompt-level, cheap, and testable by ledger replay + a small
validation before any board.
