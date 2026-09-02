# Integrity audits

Every published number in this repo must be backed by a clean run of
`scripts/audit_integrity.py`. Archived audit outputs live here.

## 2026-08-06: full audit, all runs, **65/65 clean**

Ran over every workspace in `runs/` and `runs-baseline/`, checking five ways a score
could be illegitimate:

| check | what it catches |
|---|---|
| `SOURCE_READ` | agent read the game's implementation, engine internals, or env metadata |
| `SCORE_WRITE` | agent wrote its own `result.json` / `scorecard.json` |
| `TOOL_BYPASS` | agent hit the daemon's mutating endpoints (`/act`, `/reset`) directly, skipping `commit.py`'s prediction check |
| `TIMELINE_EDIT` | the append-only timeline was rewritten |
| `HARNESS_EDIT` | agent modified the tools it is scored by |

**Result: 65/65 clean, 0 flagged.** The archived output is
[`2026-08-06-full-audit.txt`](2026-08-06-full-audit.txt), ending with a SHA-256 over
all 63 `events.jsonl` timelines concatenated in path order, the tamper-evident anchor
for every score in `RESULTS.md`.

### Three flags investigated and cleared

The first pass raised three flags. All three were audit false positives, not
violations; each was verified against the raw evidence before the patterns were
tightened:

1. **`gpt-xhigh/ft09`, TOOL_BYPASS.** The agent called `urlopen(.../status)` 17 times.
   `/status` is **read-only** and returns exactly what `observe.py` prints. It made
   **zero** calls to `/act` or `/reset`, the only endpoints that can affect a score.
   No action ever skipped the prediction check. The pattern now matches only the
   mutating endpoints.
2. **`gpt-xhigh/sb26`, TIMELINE_EDIT.** Event index restarted at 0 at position 58.
   Both position 0 and position 58 carry `reset: true`: this is the resume-renumbering
   defect (a restarted daemon began numbering at 0 again), since fixed in `daemon.py`.
   The timeline itself is intact and append-only. The check now tolerates an index
   reset that coincides with a reset event, and flags any other regression.
3. **`gpt-max/su15`, HARNESS_EDIT.** Matched the shell redirect inside
   `>/dev/null && python3 tools/backtest.py`, which runs the tool rather than editing it. The
   pattern now requires an edit verb or a redirect *into* the tool file.

Tightening these removed noise that could otherwise hide a genuine violation. The
checks remain strict on everything that actually matters.

### Prior finding

The audit's value is not theoretical. It caught a real violation on
2026-08-05, where an agent read a game's source and scored a flawless 100 on a game it
never modelled. That run is voided and quarantined; see
[`../2026-08-05-source-read`](../2026-08-05-source-read/README.md).

## Reproducing

```bash
.venv/bin/python scripts/audit_integrity.py    # exits non-zero if anything is flagged
```

Standing rule: no result from this harness is reported unless this exits clean over
every run behind it.
