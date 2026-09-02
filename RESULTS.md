> Note on commit hashes: harness freeze hashes recorded below (d37660e, eac9af2,
> 4d37aa7, dc4e702, 6fc1fdf, ...) refer to the private development history. The
> public repository starts from a squashed release commit; the hashes are kept
> verbatim as the internal registration record.

# Results ledger

Started 2026-08-07; appended through launch from `runs/*/*/result.json`.
Self-reported on the 25 public ARC-AGI-3 games, scored with the official local
RHAE implementation from the `arc-agi` toolkit.

> **Release identity.** This project has one public release, **Kepler 1.0.0**.
> The names below describe experimental stages, not software releases. Legacy
> `runs-v*` strings remain only where they identify an exact internal directory
> or freeze record. Canonical release facts live in [`release.json`](release.json).

| Kepler 1.0 board | score | exact replay | retained-board-run actions | scored-level actions | provider-record tokens | current API list-equivalent |
|---|---:|---|---:|---:|---:|---:|
| Claude Opus 5 | **100.00** | [91aa2f10](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1) | 8,256 | 7,292 | 858.0M, 97.37% cache reads | **$777.72** |
| GPT-5.6 Sol (max) | **95.97** | [c9f087f3](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685) | 35,896 | 8,400 | 2,429.1M, 98.0% cached input | $1,312.14 |

The [public companion dataset](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces)
contains the two final 25-game boards: 50 run records, 58,098 environment
events, human baselines, final notebooks and world models, captured CLI output,
and standalone verification programs. It does not contain the
complete development archive. Historical failures and superseded stages remain
documented below and under [`incidents/`](incidents/), but their raw ledgers are
not part of the final-board dataset.

> **On the margins.** Every cell below is **n = 1**. Run-to-run variance on this
> benchmark is roughly ±1 to 2 points at the pairing level. In our own data `su15` scored
> 46.91 and 81.19 on two runs of the same configuration. Neither the +0.16 nor the -0.68
> is distinguishable from noise. Read both pairings as *reproducing* the published
> figures, not beating or missing them.

Pairing rule (as used in the prior art): the primary model runs every game; a game
scoring under 80 is rerun with the secondary, and the higher per-game score is kept.

| pairing | this harness | prior art | delta |
|---|---:|---:|---:|
| Claude: Opus, Fable fallback | **98.30** | 98.98 | -0.68 (within noise) |
| GPT-5.6 Sol: xhigh, max fallback | **95.51** | 95.35 | +0.16 (within noise) |

## Single config vs. the fallback rule

The pairing rule is a **per-game best-of-2 with score feedback**: a game scoring under 80
is re-run with the second model and the higher score kept. Greg Kamradt (President, ARC
Prize) [criticised exactly this](https://x.com/GregKamradt/status/2077949388673151332) in
the original ~99% report: *"If you get feedback about which games did well/poor then
the human and environment are injecting knowledge into the process."*

That criticism applies to us too, so here is the number without it. Single config means one
model, one pass, all 25 games, no re-runs and no selection:

| configuration | single config | with fallback | fallback contributes |
|---|---:|---:|---:|
| Claude Opus (→ Fable) | **97.78** | 98.30 | **+0.52** |
| GPT-5.6 Sol xhigh (→ max) | **84.20** | 95.51 | **+11.31** |

Read that honestly in both directions. The Claude result barely uses the fallback and is
effectively a single-config number. **The GPT result depends on it heavily**, 11.31 of
those points come from re-running the 9 games that scored under 80 and keeping the better
outcome. Anyone comparing systems should use the single-config column.

(`fable` and `gpt-max` were only ever run as fallbacks, on 2 and 9 games respectively -
so they have no single-config number of their own.)

## Release resource accounting

Chollet's stated condition for a harness result being legitimate is that *"the settings and
the cost are clearly reported"*. Release accounting comes from retained local provider-session
session records, not workspace CLI footers:

| board | uncached input | cached/read input | cache write | output | raw total | current API list-equivalent |
|---|---:|---:|---:|---:|---:|---:|
| Claude Opus 5, 100.00 | 11,464 | 835,488,978 | 13,574,918 (1h) | 8,966,566 | 858,041,926 | **$777.72** |
| GPT-5.6 Sol, 95.97 | 39,262,504 | 2,379,659,648 | 0 | 10,161,281 | 2,429,083,433 | $1,312.14 |

The Opus conversion uses $5/M uncached input, $0.50/M cache reads, $10/M one-hour
cache writes, and $25/M output. The GPT conversion uses $4/M uncached input,
$0.40/M cached input, and $20/M output. Prices are current on 2026-09-01. Actual
Opus execution used Claude subscription quota; the dollar figure is a
list-equivalent comparison, not a billed charge.

An earlier draft undercounted the GPT release board by summing incomplete
workspace CLI footer counters. The retained provider sessions show that
the footer path omitted most cached traffic and one long workspace. The earlier
raw-token comparison and cost estimate are withdrawn. Reproduce the
corrected release totals with `.venv/bin/python scripts/cost_report.py --release`.

An earlier Opus draft also overcounted cost by treating each transcript row as
a separate provider response. Claude Code repeats one provider message across
its thinking, text, and tool-use content-block rows. The corrected total counts
each provider message ID once and fails closed if duplicate rows disagree.

**Integrity.** Every final-board number can be recomputed from the public
companion dataset; see [`INTEGRITY.md`](INTEGRITY.md). The recorded agent logs
contain no external requests, while the harness made its disclosed startup
handshake. Six historical controls are flagged and excluded because they
rebuilt the removed harness ([`ABLATION.md`](ABLATION.md)). This audit covers
the records retained by the execution clients; it cannot prove that a client
retained every event it generated.

```bash
hf download cveinnt/kepler-arc-agi-3-traces --repo-type dataset \
  --local-dir kepler-traces
python3 kepler-traces/score_trajectories.py kepler-traces
python3 kepler-traces/verify_scores.py --traces-dir kepler-traces
python3 kepler-traces/audit_integrity.py --traces-dir kepler-traces
```

## Initial-loop GPT pairing: early reports cited 95.35

| game | primary | fallback | retained | from |
|---|---:|---:|---:|---|
| `lp85` | 100.00 |  | **100.00** | gpt-xhigh |
| `cd82` | 100.00 |  | **100.00** | gpt-xhigh |
| `sb26` | 98.63 | 100.00 | **98.63** | gpt-xhigh |
| `tr87` | 100.00 |  | **100.00** | gpt-xhigh |
| `sc25` | 68.55 | 97.11 | **97.11** | gpt-max |
| `s5i5` | 100.00 |  | **100.00** | gpt-xhigh |
| `dc22` | 71.43 | 100.00 | **100.00** | gpt-max |
| `sp80` | 5.50 | 39.84 | **39.84** | gpt-max |
| `ls20` | 100.00 |  | **100.00** | gpt-xhigh |
| `ka59` | 95.80 |  | **95.80** | gpt-xhigh |
| `re86` | 100.00 |  | **100.00** | gpt-xhigh |
| `g50t` | 100.00 |  | **100.00** | gpt-xhigh |
| `sk48` | 77.78 | 100.00 | **100.00** | gpt-max |
| `vc33` | 100.00 |  | **100.00** | gpt-xhigh |
| `tn36` | 75.00 | 81.39 | **81.39** | gpt-max |
| `wa30` | 25.01 | 96.02 | **96.02** | gpt-max |
| `ar25` | 100.00 |  | **100.00** | gpt-xhigh |
| `su15` | 46.91 | 81.19 | **81.19** | gpt-max |
| `cn04` | 100.00 |  | **100.00** | gpt-xhigh |
| `r11l` | 100.00 |  | **100.00** | gpt-xhigh |
| `bp35` | 42.66 | 100.00 | **100.00** | gpt-max |
| `tu93` | 100.00 |  | **100.00** | gpt-xhigh |
| `lf52` | 97.71 |  | **97.71** | gpt-xhigh |
| `ft09` | 100.00 |  | **100.00** | gpt-xhigh |
| `m0r0` | 100.00 |  | **100.00** | gpt-xhigh |

**RHAE over 25/25 games: 95.51**

## Initial-loop Claude pairing: early reports cited 98.98

| game | primary | fallback | retained | from |
|---|---:|---:|---:|---|
| `lp85` | 100.00 |  | **100.00** | opus |
| `cd82` | 100.00 |  | **100.00** | opus |
| `sb26` | 100.00 |  | **100.00** | opus |
| `tr87` | 100.00 |  | **100.00** | opus |
| `sc25` | 74.92 | 87.91 | **87.91** | fable |
| `s5i5` | 100.00 |  | **100.00** | opus |
| `dc22` | 100.00 |  | **100.00** | opus |
| `sp80` | 82.16 | 0.00 | **82.16** | opus |
| `ls20` | 100.00 |  | **100.00** | opus |
| `ka59` | 100.00 |  | **100.00** | opus |
| `re86` | 100.00 |  | **100.00** | opus |
| `g50t` | 100.00 |  | **100.00** | opus |
| `sk48` | 100.00 |  | **100.00** | opus |
| `vc33` | 100.00 |  | **100.00** | opus |
| `tn36` | 90.04 |  | **90.04** | opus |
| `wa30` | 100.00 |  | **100.00** | opus |
| `ar25` | 100.00 |  | **100.00** | opus |
| `su15` | 100.00 |  | **100.00** | opus |
| `cn04` | 100.00 |  | **100.00** | opus |
| `r11l` | 100.00 |  | **100.00** | opus |
| `bp35` | 97.43 |  | **97.43** | opus |
| `tu93` | 100.00 |  | **100.00** | opus |
| `lf52` | 100.00 |  | **100.00** | opus |
| `ft09` | 100.00 |  | **100.00** | opus |
| `m0r0` | 100.00 |  | **100.00** | opus |

**RHAE over 25/25 games: 98.30**

## Run-selection policy for the added-discipline sweep (2026-08-15+)

Adopted before the added-discipline stage sweep completed, applied uniformly, and stated here so the
selection process is auditable rather than trusted:

1. **Frozen harness.** Every added-discipline stage sweep run uses the harness at commits
   `d37660e`+`6c3a38d` (guard-deadlock fix, automatic clean-run phase).
   `50561e2` landed mid-sweep but changes code comments only; behavior is
   byte-identical. The authoritative tool code for any run is the copy inside
   its own retained workspace, not the repo tip.
2. **One run per game per config.** No per-game retries, no score-conditioned
   restarts.
3. **Clean-run rule, uniform.** A WIN scoring below 95 grants exactly one fresh
   attempt (`--max-clean-runs 1`), automatically. RHAE scores only the final
   attempt by design; this is the same learn-then-execute mechanic other
   verified harnesses use, applied by rule rather than by operator judgment.
4. **Resume policy.** A run may be resumed only after infrastructure failure
   (host restart/sleep, provider outage, provider quota), never because a
   completed score looked bad. Resumes under this rule: `dc22`, `ls20`, `s5i5`,
   `sp80` on 2026-08-15 after a host restart killed all lanes at 01:19.
5. **Superseded runs are retained locally and documented.** Anything replaced is moved to
   `runs-v2/superseded/<game>-<date>-<reason>/` with its full ledger.
   First entry: tn36's initial added-discipline stage run won at 59.31 and was then resumed *by the
   operator, in reaction to the score*, producing a 100.0 clean run. That
   score-conditioned intervention is exactly what this policy forbids, so the
   run is superseded and tn36 reruns from scratch under the frozen harness.
   Whatever it scores is the number we report.
   Second entry: sp80's added-discipline stage run had the guard-deadlock fix patched into its live
   workspace mid-run (2026-08-14, commit d37660e), it played under two guard
   regimes, violating rule 1. It ended at 17.17 (budget exhausted). Superseded
   for the freeze violation, not the score; the fresh run's result stands
   either way.
6. **No game secrets.** Agent-visible surfaces contain zero game IDs, enforced
   by `scripts/check_no_game_ids.py` (gates `scripts/verify.py`). Caveat for
   the record: lanes launched before `50561e2` carry a tools copy whose code
   *comments* mentioned one game name in a cost anecdote; no gameplay
   information. Those historical copies remain local and are not part of the
   public final-board trace dataset.
7. **Best-of is a ceiling, not a headline.** The best-run-per-game card
   (99.29, `docs/best-of-manifest.json`, attempt pools disclosed) answers "what
   is the harness capable of", never "what does one configuration score".

## Added-discipline sweep (completed 2026-08-16)

Single config, Claude Opus, frozen added-discipline stage harness, all 25 games: **composite 94.01**,
18 games at 100. Sub-100: bp35 97.92, tn36 94.84, tr87 94.81, g50t 87.35,
sc25 81.93, su15 79.03, sp80 14.29 (wall clock exhausted, partial final attempt).

The added-discipline stage mechanisms (baseline-relative escalation ladder, partial predictions,
automatic one-shot clean run) were built to push past initial loop's 97.78. They did not:
initial loop cleared 21 games at 100 organically, while added-discipline stage's single clean-run repair
locked in sub-cap executions on five games and its attempt-reset discipline
collapsed sp80 from 82.16 to 14.29. Both sweeps are retained in full. The
headline remains initial loop's verified 97.77 because it is the best *complete* single
configuration, not because added-discipline stage is hidden. The next frozen
stage addressed these failure modes directly.

## Guard-correction sweeps (launched 2026-08-17)

Frozen harness: commits e61f9ad + d422ab3 (score-floor notice replaces the
forced-reset hard stop; deliberate full-reset flag; post-WIN restart gated on a
cleanrun.json certified within 1.3x baseline per level; fraction grind guards
demoted to warnings, 3,000-action hard cap remains the sole cost refusal;
action budget 20x total baseline). Two single configs, run in parallel on
separate provider quotas: Claude Opus and GPT-5.6 Sol (max). Results land here
when the sweeps complete.

### Guard-correction verification notes (2026-08-19)

- Audit: 212/218 runs verified clean; the 6 flags are the historical
  runs-baseline control set, none in runs-v3.
- Ledger recomputation: one seam on `runs-v3/opus/sp80`, after a quota-forced
  resume the fresh engine's scorecard counted only post-resume actions on
  level 3 (63) while the stitched append-only ledger records 96. NOT
  score-material: both counts are under the level's human baseline of 148, so
  the level scores 1.15 (the cap) either way and the published 47.62 is
  unchanged. Disclosed for the same reason the numbers are published at all.
- Same resume semantics reset the 20x action-budget denominator on every
  resumed lane (both boards, uniformly): the budget is enforced per process,
  not per ledger. Frozen-harness behavior, applied equally; a next guard revision fix is queued.

## Certify/replay boards (launched 2026-08-19)

Frozen harness: commit eac9af2 ("mechanical scored attempts"). The scored
repair is executed by tools/cleanrun.py, a fail-closed replay of the agent's
certified per-level programs, grounded in recorded level-start grids; the
agent's job ends at certification. WIN short-circuit bug fixed (guard-correction stage's clean-run
gate was dead code, the forensic report is in the commit message). Run budget
derived from the append-only ledger. Validation before the board: sc25
84->100, g50t 92->100 under certify/replay stage. Single config, Claude Opus; sp80 runs with an
explicit 30k action budget documented here before its result exists (its
physics demonstrably needs ~10k+ probes; all other games use the default).

- 2026-08-25: operator-ordered rerun of gpt-max/tr87 after a variance collapse
  (100 under guard-correction stage -> 47.6 under certify/replay stage, a 19k-action discovery failure). This rerun is
  SCORE-CONDITIONED and therefore outside the clean single-config policy; the
  first run is retained under `runs-v5/superseded/`, and the GPT
  certify/replay board is
  labeled "with one disclosed rerun" wherever its composite appears.

## Certify/replay Opus board: complete (2026-08-25)

Single config, Claude Opus, frozen at eac9af2: **composite 98.86** over all 25
games. Twenty-four games at 100.0; sp80 at 71.43 (5/6 levels; the run was
ended by an operator deadline after ~2 days of level-6 discovery, score
computed from the append-only ledger with the verify_scores segmentation and
that provenance written into its result.json). This is the new best complete
single configuration, +1.09 over the verified initial loop headline (97.77), with every
prior sub-100 game converted by the certify/replay stage certify-then-mechanically-execute
design. Verification stack results recorded below when complete.

certify/replay stage board verification (2026-08-25): audit 250/256 clean (6 flags are the
quarantined ablation controls), zero certify/replay stage inflations (the single ledger flag is
the disclosed, non-material guard-correction stage sp80 resume seam), game-ID gate passes.
Official-scorecard replay of the 98.86 board submitted; URL recorded here when
the card closes.

certify/replay stage Opus official replay (2026-08-25): card 455e4374 scored 96.38 server-side.
24/25 games re-executed exactly; lf52 diverged mid-replay (a recorded ACTION6
rejected by the engine on the replay path, the same single game Retrodict
documented as their only non-exact replay) and is credited partially on the
card. Local audited composite remains 98.86; both numbers are published, the
card certifies what re-executed. One fresh replay attempted since divergence
is nondeterministic.

Second replay (card 1045a78c) reproduced 96.38 exactly, same lf52 divergence
at the same recorded action, so the cause is deterministic engine-version skew
on one ACTION6, not animation randomness. Settled verified matrix:
- Best fully-re-executed verified single config: 97.77 (initial loop Opus, card 00c90840).
- Best audited single config at that stage: 98.86 (certify/replay Opus,
  ledgers retained locally); its server
  replay scores 96.38 (cards 455e4374, 1045a78c) with lf52 credited partially
  due to the disclosed skew. lf52 traces from other runs replay exactly, so the
  skew is specific to this trace, not the game or the procedure.
- Best-of ceiling: 99.29 (card a7d07431).

## Certify/replay GPT board: complete (2026-08-26)

Single config, GPT-5.6 Sol (max), frozen at eac9af2, with one disclosed
score-conditioned rerun (tr87, policy note above): **composite 93.99** over 25
games, nineteen at 100.0, the best GPT board yet (initial loop: 93.95 with the fallback
era harness; guard-correction stage: 91.46). Sub-100: sp80 4.5 (GAME_OVER final attempt), bp35
56.4 (wall clock at level 8/9), cd82 95.8, s5i5 96.3, ka59 98.1, cn04 98.8.
Convergence result across the two certify/replay stage boards: 43 of 50 games at 100 under the
identical frozen harness with two different labs' frontier models.

gpt-max certify/replay stage verification (2026-08-26): audit 270/276 clean (6 flags are the
quarantined ablation controls; the single ledger flag remains the disclosed
guard-correction stage sp80 seam). Official-scorecard replay submitted; URL recorded on close.

gpt-max certify/replay stage official replay (2026-08-26): card f5f64ae7 scored 93.97, matches
the local 93.99 within rounding, all 25 games re-executed exactly (no lf52-class
divergence on this board). The verified artifact set is complete.

## Scorecard index (full URLs)

Cards were cited by 8-character prefix throughout this file, which is not
independently openable. Full URLs, recorded here so every claim is checkable:

- `00c90840`, https://arcprize.org/scorecards/00c90840-2610-4402-88dc-b7d24257756e
- `fd4733fb`, https://arcprize.org/scorecards/fd4733fb-859c-44a5-a10b-f15e34210654
- `a7d07431`, https://arcprize.org/scorecards/a7d07431-e799-4779-926b-a44464a5cb59
- `455e4374`, https://arcprize.org/scorecards/455e4374-e66b-479f-8ebc-94eadecd1629
- `1045a78c`, https://arcprize.org/scorecards/1045a78c-4296-40ea-a4ca-69dfc69fbea3
- `f5f64ae7`, https://arcprize.org/scorecards/f5f64ae7-7445-4767-8498-ae2ca2b35b9a

## Recovery-correction stage (built 2026-08-26)

Frozen at 4d37aa7. A comment-only touch to `escalation.py` followed the initial
d3e01af freeze and changed no behavior. Four changes were validated against the
certify/replay ledgers by `tests/test_recovery_paths.py` before any paid run:

1. **full_reset bug fix** (`commit.py build_plan`): the prior stage rebuilt every RESET as a
   bare `{"name":"RESET"}`, dropping the deliberate flag, so the documented
   consecutive-RESET escape hatch was unreachable. The GPT sp80 run was
   refused it 139 times while grinding one level for 9,783 actions. Test PASS 1.
2. **Clean-run trigger 95 -> 100** (`run_game.py --clean-run-min`): three gpt
   near-misses (cd82 95.8, s5i5 96.3, ka59 98.1) won live with one over-baseline
   level and never entered the optimization phase. Fail-closed, so perfect games
   cost nothing.
3. **Binding escalation injected into the session prompt** (`ws_tools/escalation.py`):
   baseline-relative triggers (>=3x a level's human baseline, or >=4 self-resets
   past 1.5x; MIN_ACTIONS=40 floor for tiny levels). Replayed over every certify/replay
   ledger: silent on all 35 perfect games where a fire could have taxed a nearly
   done level; fires within ~130 actions on the sp80 thrash that ran to 15,915.
   Test PASS 2 / 2b.
4. **Final-level wall-clock grace** (`--final-level-grace-hours 4`): never kill a
   run on its last level. bp35 (56.4) was killed at 8h with L9 underway;
   completing it lifts the completion cap 80->100. Test PASS 3.

Also: stuck-level prose moved OUT of the always-on directive into the escalation
tier (Retrodict's documented regression: always-on anti-pruning text ~doubled
early-level cost). directive.md 227 -> 215 lines.

Validation round 1 (6h caps, gpt-max): clean-run fix converted all three
near-misses (cd82 95.76->100, s5i5 96.31->100, ka59 98.06->100). The hard games
did not convert: sp80 4.47->20.59 (further, unfinished), bp35 56.35->27.55.
The apparent regression is confounded by a 6h cap versus the certify/replay
run's 8h, an operator setup error disclosed here. Forensics: the session-boundary escalation injection fired once
across five runs (codex sessions span 500-800 actions), so it was shelved; its
residual-first and ground-truth lines moved into commit.py's per-action
escalation text, which does reach the agent. Round 2 (bp35 + sp80, 8h matched budget): INTERRUPTED by the Codex provider
usage limit (resets 2026-09-01); both ledgers preserved and resumable with
--resume. Progress at interruption: bp35 at level 6/9 after 1,683 actions -
stuck on L6 again, same wall as round 1, which is early evidence the bp35 gap
is the L6 discovery wall, not the wall-clock; sp80 at level 2/6 after 5,217
actions (the thrash pattern persists on this model). Board decision deferred
until the resumed runs complete. During the quota window the harness gained the
simplification treatment (candidate freeze 6b625cf, adopted from baseline1's
ewma_sv: a no-live-actions maintenance session that compresses the world model,
fired once per level stalled past 2x baseline; plus an assume-simple prior in
the escalation text and an objective-from-level-end-frames directive line).
The resumed bp35/sp80 runs will mix pre/post-update sessions, disclosed here;
they are validation runs, not board rows.

## Recovery-correction validation: final verdict (2026-08-27)

Two rounds, both budgets, simplification treatment included. Conclusion: the
clean-run fix is the only robust win; the discovery machinery does not crack the
hard walls.

- **Clean-run-at-100 fix: VALIDATED.** cd82 95.76->100, s5i5 96.31->100,
  ka59 98.06->100 (round 1). Deterministic, fail-closed, safe. This is the stage's real
  contribution to the GPT board (~+0.4 composite).
- **Discovery machinery (escalation, simplification, full_reset, grace): does
  NOT reliably help.** bp35 GPT round-2 (8h, resumed, simplification armed) spent
  **3,014 actions on level 6** and never passed it (final attempt 6/9, score
  46.67). sp80 GPT improved 4.47->14.29 but stalled at level 2. The bp35 "-9.68
  vs certify/replay" is not a clean regression: the earlier single attempt happened to clear L6-L7
  (8/9) while the fresh recovery-correction attempt, forced by `--resume`'s full reset, walled at L6.
  L6 is high-variance for GPT and neither harness reliably solves it.
- **sp80 Opus: no verdict.** Four attempts, each died before sustained L6 time -
  Claude provider quota (shared with the interactive session), a session restart,
  and a machine reboot. Never a capability signal; the run replays L1-L5 in ~137
  actions every time and dies on L6's doorstep.

Read: once execution is handled (the clean-run fix), what remains is discovery
reliability on two specific walls (bp35 L6, sp80 L6), a model-capability
frontier the harness nudges but does not guarantee. Consistent with the paper's
claim (3). The honest headline stays: Opus 98.86, GPT 93.99 (or ~94.4 with a
fresh clean-run-fix board). No score-conditioned reruns entered any board.

## Visual-observation intervention: sp80 reaches 100.0 (2026-08-28)

The within-system observation intervention has its answer. Same workspace, same model
(claude-opus-5), same tools, budgets, and audits; one flag (--visual) changed
the observation channel from text grids to rendered PNG frames (every frame,
animation frames included, the text ledger provably drops them).

- 19 text-mode sessions across 6 attempts inferred physics from settled grids +
  animation-frame COUNTS, exhaustively proved L6 "unsolvable under known rules,"
  and isolated an unexplained animation residual they could never decode.
- Visual session 20 read the frames and found the missing mechanic within one
  session: a blocked flight DEFLECTS around pieces and resumes course (the
  agent's notes: "the thing 19 sessions missed... water round a rock"), plus two
  visual affordances invisible in the settled grid (cups blink white when unfed;
  the border flashes green on the death side).
- Result: level 6 in 57 actions; final attempt 4/7/20/73/32/57 vs baselines
  39/58/25/148/96/152, every level at the 1.15 cap; **score 100.0** (result.json,
  runs-v6-validation/opus/sp80).

Provenance: this is an intervention, not a board row. The run resumed the
certify/replay workspace, inheriting 19 sessions of its own text-mode learning,
then continued under the visual-observation freeze. It establishes that sp80 is
solvable by this system and that the observation channel was the binding
constraint for this run. It does not establish a benchmark-wide effect. The
discovery narrative remains verbatim in the workspace notes.

## Visual-observation board (launched 2026-08-28)

Frozen at dc4e702: recovery-correction stage plus visual mode (`--visual`). Single config, Claude Opus 5,
all 25 games, fresh workspaces in the local provenance archive. Registered before results existed.

## Kepler GPT board: complete (2026-08-29): 95.97

Single config, GPT-5.6 Sol (max), frozen at 4d37aa7: **composite 95.97**
over 25 games, twenty-three at 100.0. The prior certify/replay board scored 93.99. The
board was interrupted three times by provider quota and once by a host restart;
every interruption is a clean resumable abort in the ledgers (disclosed; the
per-lane resume preserves the append-only timeline).
- Converted by the clean-run-at-100 fix: cd82 100 (previously 95.76), s5i5 100
  (96.31), ka59 100 (98.06), cn04 100 (98.76).
- bp35 100.0 (previously 56.35). The level-6 wall fell with a certified clean run.
- Sub-100: sp80 33.8 (previously 4.47, wall-clocked at level 4/6) and tn36
  65.38 (previously 100, a same-config variance collapse at 14,344 actions; kept, no
  score-conditioned rerun, per policy).
Official replay: [c9f087f3](https://arcprize.org/scorecards/c9f087f3-b9de-452d-9520-d4d0597b0685).

## Pre-release Opus board: complete (2026-08-29): 100.00

**Single configuration, Claude Opus 5, frozen at dc4e702 with visual mode,
all 25 public games, fresh workspaces: composite 100.00.** First 100 in this
project; achieved the run
after the modality ablation identified vision as sp80's binding constraint.
Notes: (1) result.json stamps record docs-only later commits (31afb86/9419db9);
`git diff dc4e702..HEAD -- harness/` is empty, the harness that played every
game is the frozen one. (2) The board absorbed provider-quota interruptions and
one host restart; every resume is a clean abort/append in the ledgers,
disclosed per policy. (3) The official scorecard replay is
[91aa2f10](https://arcprize.org/scorecards/91aa2f10-5dc3-4471-80e5-9e8895db5de1).

## Verification stack after the pre-release boards (2026-08-29)

- Audit: 274/280 runs clean, and with the two headline boards included,
  324/330, the 6 flags are unchanged (the historical quarantined
  ablation-control workspaces), i.e. **all 50 board runs audit clean**.
  Game-ID gate passes (12 agent-visible files).
- Ledger recomputation: two INFLATED flags, both resume seams, both
  non-material, both disclosed: the known runs-v3 sp80 L3 seam (63 vs 96,
  level at cap either way), and a new one in the runs-v6-validation gpt sp80
  run, L1 scorecard 15 vs timeline 16 (a resume-boundary off-by-one; baseline
  39, so the level is at cap under either count). Neither run is a board row.
- Both boards (GPT 95.97 and pre-release Opus 100.00) recompute clean.

## Official scorecard replays before transport hardening (2026-08-30)

- **GPT board: exact server verification.** Card c9f087f3 scored 95.9672,
  matching the local composite to the fourth decimal. All 25 games re-executed;
  the only sub-100 rows are the board's own (sp80 33.80, tn36 65.38). Transient
  API 429s during replay were retried through successfully.
- Pre-release Opus board, first replay (card 0c6c0990): 94.42. 23/25 games re-executed
  exactly at 100. The two divergences are disclosed and distinct: bp35 hit API
  rate limiting (429s; the two boards were replayed in parallel, an operator
  error, retryable, not a trace defect), and lf52 hit the known deterministic
  ACTION6 engine-version skew documented since certify/replay stage. A solo sequential replay was
  run to test the rate-limit theory.

- Pre-release Opus solo replay (card 2779000b): **94.42 again, with identical per-game
  values, zero 429s.** The rate-limit theory for bp35 is falsified: both bp35
  and lf52 diverge on a recorded ACTION6 rejected with a 400 by the replay-path
  engine, the same deterministic engine-version skew documented since certify/replay stage
  (lf52 is also the one game Retrodict reported as their only non-exact
  replay). Final verified matrix for the pre-release board: **local audited 100.00**
  (every run audit-clean, full ledgers retained locally); **server replay 94.42**
  (cards 0c6c0990 + 2779000b, 23/25 games re-executed exactly; bp35 and lf52
  credited partially, divergence deterministic and disclosed). Both numbers
  are published; the card certifies what re-executed.

## Superseded pre-release Opus token accounting (2026-08-31)

The Claude CLI emits no usage in `-p` mode, but Claude Code session transcripts
record per-message usage. Complete historical accounting exists for this
superseded visual board, whose official replay diverged on two games. It is not
the Kepler 1.0 release board and is omitted from the release comparison. The
canonical provider-record accounting is the table at the top of this document.

## Measured convergence (2026-08-31, 30-minute gap cap)

- Pre-release Opus (100.00): median 2.3h active per game, fastest 17min (sb26),
  slowest 4.6h (bp35); whole board ~57 active hours.
- GPT (95.97): median 2.3h, fastest 42min, slowest 12.7h (lf52);
  ~88 active hours. No other published system reports per-game timing.

## Convergence in actions (2026-08-31)

- Pre-release Opus (100.00): scored trace 6,921 actions; total interaction
  including every learning step: 7,514. This is a historical board, not the
  Kepler 1.0 action count.
- GPT (95.97): scored 8,400; total including learning 35,896.
Wall-clock numbers above remain as secondary, disclosure-only stats.

## Transport-hardening board (launched 2026-08-31)

Frozen at cf1b1a7: visual observation plus transport safety. Off-grid ACTION6
was refused at commit and certification, making every trace replayable by construction. Single config,
Claude Opus 5, visual, all 25 games, fresh workspaces in the local provenance archive.
Registered before results exist. Goal: a public scorecard that reads the
board's composite with zero transport divergence.

## Aborted release candidate and clean restart (2026-08-31)

The release candidate was aborted ~30 minutes in (workspaces retained in the
local provenance archive; no results existed) after a zero-context code review
found two defects in the frozen harness: cleanrun.py's transport-check helper
was defined below the script entry point (every scored attempt would have
crashed with NameError), and bfs.py has crashed with UnboundLocalError on
every invocation across five internal stages. A nested key() shadowed the module-level one; five
boards' agents silently routed around the broken planner by writing their own
searches, which is why the tools table always said "or agent-written
searches". Rather than patch a frozen board mid-flight, the board restarts
clean. Frozen at 6fc1fdf. This entry is the disclosure.

## Kepler 1.0 Opus board: complete and server-verified exact (2026-09-01): 100.00

**Single configuration, Claude Opus 5, frozen at 6fc1fdf (visual observation +
transport safety), all 25 public games, fresh workspaces: composite 100.00,
and the official ARC Prize replay card reads 100.0 with every game re-executed
to 100.** Card: 91aa2f10-5dc3-4471-80e5-9e8895db5de1. This is the number the
project set out for: a maximum public-set score, single-config, no
cherry-picking, with the public link reading the same value as the local
ledger. The board absorbed multiple provider-quota interruptions (each a clean
resumable abort, driven to completion by the local supervisor); one
16-hour orphaned agent search from a completed lane was killed and is noted
here. The transport gate did its job: the two games whose off-grid clicks sank
the earlier replay (bp35, lf52) replayed exactly this time. The retained board
runs used 8,256 environment actions, with 7,292 in scored levels. Under official
The board completed 183 levels; 181 used no more actions than the median-human
baseline and two used more. Capped gains elsewhere preserved the 100.00
composite, so exact 100.00 is not a per-level efficiency guarantee. These are
not full-campaign actions: local
ledgers contain at least 13,688 non-reset actions and omit 22 prefix events.
We do not rank either count against AVO's 6,624
environment actions, VISTA's 7,542 game actions, or Retrodict's 7,703 campaign
actions, because those are different denominators. The retained provider record,
deduplicated by provider message ID, totals 858,041,926 raw tokens, 97.37% cache
reads, or $777.72 at current API list-equivalent rates. That is 74.0% below the $2,986 API-equivalent
estimate Retrodict published for Tycho; Tycho discloses no cost of its own, and
neither do AVO or VISTA. Actual execution used Claude subscription quota.
