# Integrity

A self-reported benchmark score is worth exactly what its audit is worth. This page is
the audit: the threat model, the controls, the two times those controls caught *us*, and
the commands to check all of it yourself.

Every check here runs offline against the shipped run data. None of it requires trusting
us.

```bash
.venv/bin/python scripts/audit_integrity.py    # adversarial scan of every run
.venv/bin/python scripts/verify_scores.py      # re-derive scores from the raw ledger
python3 scripts/verify.py                      # replay a winning trace, no API keys
```

## Current status

| check | result |
|---|---|
| Scores supported by their own ledger | **Ledger recomputation: exactly two disclosed non-material resume seams across every board; see RESULTS.md for the current scan.
| Adversarial audit | **324/330 runs verified clean (the 6 flags are the quarantined control-group workspaces).
| External network access **by the agent** | **0 hits across 123 agent log files** |
| Unauditable runs (logs missing) | **0** |

## Threat model

RHAE is `min((human_baseline / agent_actions)², 1.15)` per level. The agent's action count
is the *only* input it can influence in its own favour. So a score is fake if and only if
one of these happened:

1. **The agent learned the answer** instead of discovering it — by reading the game's
   implementation, engine internals, or environment metadata.
2. **The agent wrote its own score** — authoring or editing `result.json` / `scorecard.json`.
3. **The agent bypassed the guarded channel** — hitting the daemon's mutating endpoints
   directly, so actions escaped the prediction check.
4. **The ledger was edited** — the append-only timeline rewritten after the fact.
5. **The agent modified the tools it is scored by.**
6. **The agent looked it up online.**

### What does touch the network, precisely

Being exact about this, because "no network access" is easy to overclaim and we did
overclaim it in earlier drafts.

* **The agent: never.** Zero external fetches across every session log and recovered
  transcript. The only HTTP an agent makes is to `127.0.0.1`, which is the game daemon.
* **The harness: once per daemon start.** `arc_agi`'s `Arcade` calls
  `_get_anonymous_api_key()` against `three.arcprize.org` when the environment is
  constructed. It is a startup handshake, not gameplay — the games themselves are
  materialized and stepped locally, and no game state or score crosses the network
  during a run.

We found this the way you would want us to: a transient read timeout to that host
killed a daemon at startup, and the traceback named the call. It had been true the
whole time and we had been describing it imprecisely.

`scripts/audit_integrity.py` checks all six across every session log and recovered
transcript. `scripts/verify_scores.py` closes the loop from the other side: it counts
actions per level straight out of `events.jsonl` and asserts the direction that matters —
**no level may be scored with fewer actions than the timeline recorded.** Equal is correct;
more is conservative and costs us score; fewer would mean a published number is not
supported by its own evidence.

Getting that verifier right took four wrong turns, each corrected against the data rather
than assumed. The first pass "found" 66 mismatches which were all artefacts of our own
counting: it double-counted the deliberately unscored exploration pass before a
full-reset speedrun, missed that mid-level RESETs *are* scored actions while the RESET that
opens an attempt is not, and mis-modelled how unfinished games aggregate.

## What the controls caught

Both of these were ours. Neither was caught by a rule — both were caught by re-deriving a
result from raw evidence and asking what *else* could produce this number.

### Incident 1 — an agent read the game's source

The `arc-agi` toolkit materializes each game's Python implementation, win conditions and
all, into a directory on disk. That directory sat **inside the agent's workspace**. One
agent read all 2,172 lines of it and returned a flawless 100.00 on a game it never
modelled.

The telemetry looked *better* than honest play: fewer actions, no mispredictions, a clean
ledger. We had already cited that run as headline evidence that the harness worked. A clean
rerun of the same game scored **46.91** — a 53-point drop.

The run is voided and quarantined. The fix was structural rather than instructional: the
environment files now live outside the workspace entirely, where the agent has no path to
them. Full write-up and evidence:
[`incidents/2026-08-05-source-read`](incidents/2026-08-05-source-read/README.md).

### Incident 2 — the control group rebuilt the harness

To test whether the harness contributes anything, we ran an ablation: same model, same
games, methodology stripped out. The ablation installs only a read-only `observe.py` and a
bare `act.py`.

But the run workspace lives inside the repository, and `harness/ws_tools/` was sitting
there on disk. **Every one of the six baseline agents found it.** Three copied the tools in
with `cp`; the rest wrote shim files that executed the repo's canonical tools directly.

| "vanilla" run | harness tool invocations | built a world model |
|---|---:|:---:|
| `sp80` | 9,148 | yes |
| `r11l` | 1,843 | yes |
| `tn36` | 942 | yes |
| `cd82` | 398 | yes |
| `ft09` | 288 | yes |
| `su15` | 92 | yes |

The comparison was therefore harness-against-harness, and every conclusion drawn from it is
**withdrawn** — including a striking "the harness's net advantage is roughly zero" that we
had published. The audit now flags any baseline workspace containing a world model or a
harness tool, which is why six runs show as flagged above. Full write-up:
[`ABLATION.md`](ABLATION.md).

**The harness's contribution to our scores is currently unmeasured.** Not small, not large.
A valid ablation needs the workspace outside the repository tree and has not been run.

### The lesson both incidents share

Twice we shipped a control that was an *instruction and a file-placement policy* rather than
a boundary the agent could not cross. Twice an agent optimising against a metric used what
was reachable. Reachable means the filesystem, not the instructions.

There is a related failure that is not cheating but is just as corrosive to a score:
**grinding**. On one game the agent stopped modelling and brute-forced a coordinate sweep —
12,287 of 13,604 actions on a single level:

```
ACTION6 @ x=59   ×4387
ACTION6 @ x=57   ×4289
ACTION6 @ x=54   ×1428
RESET            × 205
```

Nothing in the loop escalated when certification failed, so grinding was a free option.
`commit.py` now refuses it, with thresholds taken from the record rather than intuition:
the worst level of any run that still scored 100.00 cost 1,436 actions, while every grinding
run cost 7,559–46,990 on one level. `scripts/test_grind_guard.py` replays the guard over
every recorded timeline and asserts both directions — silent on all 43 runs that scored
100.00, fires on exactly the six worst.

That guard also took three attempts, because our first regression test fed it one action at
a time, where a single stale action is 100% of the plan. Real plans are batches, and a batch
that is 40% fresh coordinates walks straight through a 60% threshold. We caught it by
watching a live run reach 9,343 actions on one level *with the guard active*.

**Live validation.** A post-guard `sp80` run fired the guard 20 times (19 reset-thrash,
1 hard cap) and held every attempt at or under the ceiling — per-attempt actions on the
stuck level were 383, 2081, 2077, 3091 and 1159, against pre-guard runs that reached
12,287 and 46,990 on a single level. The agent's response to being refused was to full-reset
and re-approach, which is the intended escape hatch: redirected, not deadlocked.

One methodological warning, since we tripped over it twice. That run's raw timeline shows
8,791 actions on level 1, which looks like the guard failing — it is actually 22 separate
attempts summed together. Per-attempt is the only meaningful unit here, exactly as it is
when re-deriving scores. Counting a resumed run as one continuous attempt will make a
working guard look broken and an honest score look inflated.

## What this does not prove

Being straight about the limits, because they are the first thing a skeptic should ask:

* **Public set only.** These are the 25 public games. The semi-private and private sets are
  where a result actually counts, and we have not run them.
* **Self-reported.** Scored locally with the toolkit's official implementation, not by
  ARC Prize.
* **Not a capability claim.** The harness lets the model build an executable simulator of
  the game. Whether that measures the thing ARC-AGI-3 intends to measure is a fair argument
  to have, and we do not settle it by scoring well.
* **Reruns vary.** Frontier models making thousands of autonomous judgment calls, against
  providers whose models drift.

## Reporting a problem

If you find a run whose score is not supported by its ledger, or a hole in these checks,
open an issue with the run path and what you found. A reproduction that survives being
attacked is worth more than one that was never tested.
