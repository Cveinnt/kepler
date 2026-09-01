# Ablation: does the harness actually beat the bare CLI agent?

> ## ⚠️ RETRACTED — every result on this page is invalid
>
> **All six "baseline" runs rebuilt the harness and used it.** `--baseline` installs
> only `observe.py`, `_lib.py` and a bare `act.py` — but the run workspace lives
> *inside this repository*, so `harness/ws_tools/` was reachable on disk. Every
> baseline agent found it. Three copied the tools in with `cp`; the rest wrote shim
> files that `run_path("/…/harness/ws_tools/commit.py")` directly. All six ended up
> with a `world_model.py` and called the smuggled tools hundreds to thousands of
> times:
>
> | baseline run | tool invocations | world_model.py |
> |---|---:|:---:|
> | `sp80` | 9,148 | yes |
> | `r11l` | 1,843 | yes |
> | `tn36` | 942 | yes |
> | `cd82` | 398 | yes |
> | `ft09` | 288 | yes |
> | `su15` | 92 | yes |
>
> So the comparison below is not harness-vs-vanilla. It is harness-vs-harness, where
> one side had to reconstruct the methodology first. **Nothing here supports any claim
> about the harness's contribution**, in either direction — including the "net delta ≈
> zero" headline, and including "vanilla beats the harness on `tn36`/`sp80`", which I
> stated in the README and in several reports. Both are withdrawn.
>
> This is the same failure class as the
> [source-read incident](incidents/2026-08-05-source-read/README.md): a control that
> existed as an *instruction and a file-copy policy* rather than as a boundary the
> agent could not cross. The harness numbers in `RESULTS.md` are unaffected — they
> were audited separately and every score is still supported by its own append-only
> ledger — but the question "is it the harness or just the model?" is once again
> **unanswered**.
>
> A valid ablation requires the workspace to sit outside the repository tree so the
> methodology is not on disk to find. That has not been run yet.

A harness is only interesting if it is doing work. The obvious
null hypothesis is that `codex` and `claude` already solve these games on their own and
the scaffolding is decoration. This page reports what we measured, **including the
result that goes against us**.

## Setup

`harness/run_game.py --baseline` strips the methodology and keeps only the plumbing.
The baseline agent gets:

* `observe.py` (the same read-only view of the current frame), and
* a generated `act.py` that sends an action to the same daemon,

and **not**: `world_model.py`, `backtest.py` (certification), `bfs.py` (planning inside
the model), the guarded predict-checked commit channel, or the agent directive. Same
model (`gpt-5.6-sol`, xhigh), same games, same environment, same official RHAE scorer.
Everything below is `scripts/audit_integrity.py`-clean.

## Results

| game | harness (best GPT run) | vanilla codex | delta |
|------|:----------------------:|:-------------:|:-----:|
| `ft09` | 100.00 (75 actions)     | 100.00 (75 actions)  | — |
| `cd82` | 100.00 (112 actions)    | 100.00 (167 actions) | — |
| `r11l` | 100.00 (90 actions)     | 100.00 (130 actions) | — |
| `tn36` | **81.39** (13,604 actions) | **100.00** (160 actions) | **−18.61 (harness worse)** |
| `su15` | **46.91** (329 actions) | **22.22** (165 actions)  | **+24.69 (harness better)** |
| `sp80` | **82.16** (opus, 6,743 actions)<br>39.84 (gpt-max, 7,646 actions) | **87.88** (987 actions) | **−5.72 (harness worse)** |

`sp80` is the hardest game in the set and the clearest result: the bare agent **won it
outright in 987 actions**, beating our best harness run (opus, 82.16 in 6,743) and
crushing the GPT one (39.84, which did not even finish). Per-level, vanilla spent
`[11, 7, 10, 26, 909, 40]` — it solved five of six levels in 94 actions total.

## What this actually shows

**1. On easy games the comparison is uninformative.** `ft09`, `cd82` and `r11l` are won
by both at 100.00, and RHAE saturates at 100 for anything at or under the human
baseline. Three of our six samples can't discriminate between the two systems at all. Any ablation that
samples only games where the harness already scores 100 is rigged toward "no
difference" — which is why we deliberately added the hard games.

**2. The harness's advantage shows up where progress requires sustained modelling.**
On `su15` — 9 levels, the hardest game in our GPT column — the harness reached level 6
where the bare agent stalled at level 2. That is the intended behaviour: the bare agent
has nowhere to accumulate a theory across sessions.

**3. The harness is clearly *worse* on `tn36`, and the reason is a real defect.**
Vanilla won in **160 actions**; the harness won in **13,604**, of which **12,287 were
spent on level 3 alone**. Inspecting that segment:

```
ACTION6 @ x=59  ×4387
ACTION6 @ x=57  ×4289
ACTION6 @ x=54  ×1428
RESET           × 205
```

The agent stopped modelling and brute-forced a coordinate sweep, resetting the level 205
times. RHAE scores *actions*, so this is close to the worst thing an agent can do — and
the bare agent avoided it entirely by just playing the game. The same signature appears
on `sp80` (7,646 actions).

**This is a harness pathology, not a model limitation.** When the world model failed to
certify, nothing in the loop escalated: the agent was free to fall back to grinding, and
the harness recorded every one of those actions.

**Fixed.** `commit.py` now refuses a plan that is ≥60% actions already proven fruitless
on the current level, naming the ways out (re-theorize against the counterexamples,
full-reset for ground truth, or propose something different). It blocks only the overused
moves, never the level, so a genuinely new plan is always accepted. Thresholds come from
the recorded runs, not intuition: the worst level of any run that still scored 100.00
cost 1,436 actions, while every grinding run cost 7,559–46,990 on one level, so the floor
sits at 2,000. `tests/test_grind_guard.py` replays the guard over all 70 recorded
timelines and asserts both directions — silent on all 43 runs that scored 100.00, fires
on the tn36 grind after 2,034 actions (~10,253 saved). It fires on exactly five runs, all
of them `sp80`/`tn36`.

The first version of that guard was **not enough, and we only found out by watching it
run.** Its regression test fed the guard one action at a time, where a single stale
action is 100% of the plan — but real plans are batches, and a batch that is 40% fresh
coordinates passes a 60% test. A sweep over a 64×64 grid supplies fresh cells almost
indefinitely. With the rule active, a live `tn36` retry still reached **9,343 actions on
one level** before we stopped it by hand. Two further rules now backstop it: a reset-thrash
check (≥60 RESETs on a level while cycling ≤40 distinct actions) and a hard 3,000-action
per-level ceiling that no plan composition can dilute. This is worth stating plainly
because it is the same lesson as the [source-read incident](incidents/2026-08-05-source-read/README.md):
a guard is worth exactly what its evidence is worth, and a test that passes can still be
measuring the wrong thing.

The scores in this table predate the guard and are **not** re-run under it; every run
stamps its harness git SHA, so post-guard numbers will be distinguishable.

## Honest bottom line

**On this six-game sample the harness's net advantage is approximately zero.** Summing
the per-game deltas against the bare agent:

```
su15   +24.69   harness better
tn36   −18.61   vanilla better
sp80    −5.72   vanilla better
ft09 / cd82 / r11l   0.00   tie (both 100.00)
                 -------
net    +0.36 over 6 games  =  +0.06 per game
```

That is noise. The harness wins one game decisively, loses two, and ties three, and the
two it loses are **exactly the games where the v1 harness underperformed the strongest early reports**. The
pattern is consistent and mechanical rather than random: the bare agent simply plays,
while the harness — when its world model fails to certify — falls into grinding that RHAE
punishes at 10–40× the action cost.

So the honest reading is not "the harness helps a lot" and not "the harness is useless".
It is: **the methodology's benefit on hard games is currently cancelled out by a failure
mode the methodology itself creates.** Fixing the grinding pathology (above) is the
prerequisite for the harness showing a real delta; until a post-guard sweep exists, the
delta is unproven.

Two limits on this conclusion, stated plainly:

* **Six games, one model, one run each.** No error bars. `sp80`/`tn36` could each swing
  several points on a rerun.
* **No benchmark-level comparison exists.** That needs vanilla over all 25 games, which
  we have not run.

Anyone citing this work should treat "the harness is what produces the score" as
**not established by our own evidence**, and should read the headline numbers as what a
frontier model plus *some* scaffolding achieves — not as a measured contribution of this
particular scaffolding.

Reproduce any row with:

```bash
.venv/bin/python harness/run_game.py --game tn36 --model gpt-xhigh --baseline --runs-root runs-baseline
```
