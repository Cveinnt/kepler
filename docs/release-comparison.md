# How Tycho and Retrodict released their harnesses — and where Kepler stands

Research memo, 2026-08-14. Sources: the read-only clones under `reference/tycho/` and
`reference/retrodict/`, plus their public posts. `arclog` is Retrodict's in-workspace
helper (`workspace_template/arclog.py`); `wmlib` is Tycho's (`tycho/workspace/wmlib_template.py`).
Retrodict's `docs/arc-agi-3-harness-comparison.md` publicly critiques the earliest ~99% release
that inspired this project; Kepler's launch is, in effect, the answer to that review.

## 1. Release engineering

### Tycho — "paper artifact" release (Apache-2.0, CITATION.cff, CI)

- Packaged project: agent, Jinja prompt templates, sandbox, harness, replay viewer,
  six frozen `configs/paper/` run configs (one per reported result), ~50 test files,
  `docs/{ARCHITECTURE,REPRODUCING,PAPER_RESULTS}.md`.
- **Published**: harness, prompts, configs, scorecard evidence JSONs (per-game/per-level
  actions, baselines, scores, resets, scorecard URL each), and
  `artifacts/evaluation_integrity.json` binding each policy to a `canonical_trace_sha256`,
  scorecard id/URL, and `closed_competition_replay: true`.
- **Withheld**: the actual traces (`results/`, `ws/` gitignored; hash-anchored but not
  inspectable), raw diagnostics, source revisions (enforced by `validate_public.py`).
- `docs/REPRODUCING.md`: states bit-for-bit reproduction is not expected (sampling,
  provider drift), then a validation ladder — credential-free `make validate`; one paid
  call behind `--confirm-paid-call`; bounded smoke with a hard two-call ceiling and
  $0.50 guard; full run command. Env vars override config so safety bounds can't be
  weakened by shell state.
- Replay disclosure: thin — rationale plus `submission_replay.py --help`.
- Release integrity mechanized: `PUBLIC_RELEASE_MANIFEST.json` (SHA-256 per tracked
  file) verified in CI, plus a secret/home-path scanner.

### Retrodict — "solo builder with radical trace transparency" (NO LICENSE file — the hole to avoid)

- Small `src/arc3/` package + `workspace_template/` + scripts + a **committed dev
  journal `experiments.md`** with commit-hashed provenance for every prompt change.
- **Published**: everything evidentiary. Full traces (logs, transcripts, playbook,
  per-request tokens) on GitHub releases, including the two superseded first attempts
  disclosed in the README; the archived worse scorecard (`docs/official-scorecard-8d734689.json`);
  per-game token/cost ledgers with per-column sources.
- Replay disclosure: best in class. `scripts/replay_runs.py` docstring documents the
  whole procedure; per-action verification against the recorded trajectory ("a verified
  re-execution of the recorded runs, not a new attempt"); archive doc reports honestly
  that 24/25 re-executed exactly (lf52 the exception).
- Credit named inline (RGB-Agent, Tufa Labs' Duck harness, baseline1, ThinHarness).

## 2. The game-secrets question

Both keep agent-visible surfaces game-agnostic — verified by grep, not just claimed.
Tycho: one game-ID hit in the whole package, an operator CLI default
(`run_parallel.py:906`). Retrodict: two non-agent-visible hits (a comment, a help string).

- Tycho: prompt assembly uses visible `{% if %}` conditionals ("no Python lookup
  table"); priors are hedged and **test-enforced** (`test_actor_prompt_contracts.py`
  asserts the hedge is present and the overclaim absent); agent code runs in a
  network-disabled container.
- Retrodict: README states the ~2,500-token system prompt "contains no game-specific
  information", and discloses the author's own exposure ("most of the 25 I have never
  viewed"). Every run writes `containment.json` proving engine imports fail. Gray zones
  are disclosed rather than hidden: the HUD heuristic is credited to its source; the
  double-RESET warning traces to a disclosed failure; one harness (not prompt) behavior
  was tuned around lf52's nondeterministic sparkle animation, written up in the archive.
- **Neither ships an automated game-ID gate.** Kepler's `scripts/check_no_game_ids.py`
  (see repo) makes the invariant checkable: zero game IDs in agent-visible surfaces,
  enforced, not promised.

## 3. PR shape

- **Tycho**: paper + repo, no thread. Headline 100.00 RHAE; every results row links its
  official scorecard; ablation policies (79–88) structurally separated from selected
  runs. No cost accounting anywhere — their transparency gap.
- **Retrodict**: README + blog + X thread. Headline is concede-and-reframe: "99.86% at
  $654 ... Only Tycho scores higher ... 100.00% at an estimated $2,986" — cedes the
  crown in sentence two, wins on the cost-performance frontier. Dedicated Validity
  section; rerun forensics with prompt-hash verification; superseded results kept
  public.
- **The cautionary tale is our lineage**: the earliest report led with ~99% from a fixed
  fallback-rerun rule and self-reported numbers; Retrodict's comparison doc flagged
  both. Kepler leads with single-config + verified URLs for exactly this reason.

## 4. Where Kepler stands

| Dimension | Tycho | Retrodict | Kepler |
|---|---|---|---|
| Per-action ledgers published | hashes only | winners + disclosed reruns | **every run incl. failures** |
| Post-hoc reward-hacking audits shipped | no | no (preventive only) | **yes, run against raw ledgers** |
| Scorecard URL beside every headline | yes | yes | yes (parity — table stakes) |
| Replay procedure disclosed | thin | best in class | full (match Retrodict's "verified re-execution" language) |
| Single-config beside best-of | yes | single-run by design | yes — and it's our load-bearing fix |
| Zero game IDs in agent-visible files | true, unenforced | true, unenforced | **true and enforced by check** |
| Cost/token transparency | absent | best in class | cost_report.py — publish per-game ledgers at launch |

### Adoption queue (ranked, from the memo)

1. ~~Game-ID gate as an enforced check~~ (`scripts/check_no_game_ids.py`) — DONE.
2. Concede-and-reframe headline discipline in the blog post — DONE.
3. Release manifest + validate_public-style CI (per-file SHA-256, secret scan).
4. Trace-hash ↔ scorecard binding (canonical SHA-256 per run bound to card id).
5. Publish per-game token/cost ledgers incl. failed runs (closes that critique).
6. Comparison-methodology doc that includes our own caveats in the same table.
7. Committed experiments journal (we have git history + incidents/; surface it).
8. Per-run containment-style proof artifact alongside the audits.
9. Credential-free validation ladder for reproducers (`make validate` equivalent).
10. Keep superseded results public with their own disclosures (we already keep all
    ledgers; add the narrative doc).

### v3 harness candidates (field reports from v2 runs)
- **Deliberate full-reset path.** v2 only unlocks the RESET→RESET full-game
  restart while hard-stopped, so an agent wanting a fresh scored run early must
  burn a doomed level up to 5x baseline to trigger the escape (reported from
  inside an sp80 run). v3: honor an explicit `{"name":"RESET","full_reset":true}`
  commit at any time — deliberate, so the accidental-double-RESET guard keeps
  its purpose.
- **Efficiency gate on the clean-run reset.** Five v2 games (tr87, sc25, g50t,
  su15, tn36) spent their one clean run on programs that were correct but not
  action-optimal on 1–2 levels. v3: before permitting the clean-run reset,
  require the planned action count per level to be within ~1.3x baseline, else
  keep consolidating. Game-agnostic; uses only the baselines the ladder already
  reads.
