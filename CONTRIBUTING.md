# Contributing

This is a small research harness repo, not a product; the bar is "clear enough
that someone else can rerun the numbers and trust what they get," not enterprise
process. Still, a few rules keep it that way.

## Before you start

- Read `DESIGN.md` for the architecture and `AGENTS.md` for what not to touch, in
  particular, `runs/` is generated experiment data (never hand-edited, never committed),
  and `harness/ws_tools/` is copied into live workspaces rather than imported.
- Check `ps aux` for running `run_game.py` / `sweep.py` / `daemon.py` before changing
  anything under `harness/`. Sweeps run for hours unattended; don't change harness
  behavior out from under one.
- Changes that affect scoring, the world-model contract, or `harness/directive.md`
  affect what a "this harness" means, call that out explicitly rather than folding it
  into an unrelated diff.

## Making a change

1. Small, focused commits. Docs/packaging changes and harness behavior changes should
   not share a commit.
2. If you touch `harness/*.py` behavior (not just formatting), update `DESIGN.md` if the
   architecture moved, and say in the commit message what changed and why, future runs
   in `runs/` need to be interpretable against the code that produced them.
3. Don't run a sweep or invoke `codex`/`claude` to "test" a docs or packaging change -
   those cost tokens. Read the code instead; if you genuinely need a live run to verify
   a harness change, say so and get confirmation first.
4. No new third-party dependencies without a reason in the commit message, `ws_tools/`
   in particular must stay stdlib-only since it runs inside agent workspaces, not this
   repo's own venv.

## Commit messages

Say what changed and why, not just what. "Fix score.py fallback tie-break" over "update
score.py." If a change affects reproducibility of prior results, say that too.

## Reporting issues

Include: the exact command you ran, the model, the game code, and, if it's a scoring
question, the relevant `runs/<model>/<game>/result.json` (or scorecard) rather than a
paraphrase.
