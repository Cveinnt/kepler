#!/usr/bin/env python3
"""Replay recorded runs through ARC Prize competition mode → a shareable scorecard.

Why this exists
---------------
Live competition runs kept losing their scorecards: cards that stayed open past
roughly a couple of hours 404'd on close (registered key or not, idle or not;
we measured max action gaps of 9.6m on a run that still failed). The harnesses
with verified URLs (Tycho, Retrodict) never fight that clock: they play against
the local engine, then replay the recorded action sequence through the API in
competition mode. No LLM in the loop, seconds per action, the card closes long
before whatever expires expires.

This does the same for our runs. Input is the append-only events.jsonl each run
already has; the replayed segment is exactly "the attempt the scorecard scores"
(same extraction as scripts/verify_scores.py): the final full-reset-to-end
segment, opening RESET excluded, mid-level RESETs included.

The resulting scorecard certifies the ACTIONS, not live play. We disclose that
wherever the URL is published, as the others do.

Usage:
  # one game, its own card (validation)
  .venv/bin/python scripts/replay_submit.py --model gpt-xhigh --games ft09
  # one card spanning many games (the flagship URL)
  .venv/bin/python scripts/replay_submit.py --model opus --games all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

logging.disable(logging.INFO)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

from arc_agi import Arcade, OperationMode  # noqa: E402
from arcengine import GameAction  # noqa: E402
from score import GAMES  # noqa: E402

ACTION_BY_NAME = {a.name: a for a in GameAction}


def final_attempt_actions(events_path: Path) -> list[dict]:
    """The action sequence of the attempt the scorecard scores."""
    ev = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]
    start = 0
    for i, e in enumerate(ev):
        if e.get("full_reset") or (i > 0 and e.get("i") == 0 and e.get("reset")):
            start = i
    seg = ev[start:]
    if seg and seg[0].get("reset"):
        seg = seg[1:]                      # the opening RESET is the env's, not ours
    return [e["action"] for e in seg if isinstance(e.get("action"), dict)]


def _retry(fn, what, tries=6):
    """The API times out transiently; a replay must ride through it."""
    for k in range(tries):
        try:
            out = fn()
            if out is not None:
                return out
            raise RuntimeError(f"{what} returned None")
        except Exception as exc:
            if "400" in str(exc) or "VALIDATION_ERROR" in str(exc):
                raise  # permanent: the server rejects this action in this state
            if k == tries - 1:
                raise
            wait = min(2 ** k * 2, 30)
            print(f"  {what}: {type(exc).__name__}, retry {k+1}/{tries-1} in {wait}s",
                  flush=True)
            time.sleep(wait)


def replay_game(arcade: Arcade, card_id: str, game_prefix: str,
                actions: list[dict]) -> dict:
    matches = [e for e in arcade.get_environments()
               if e.game_id.startswith(game_prefix)]
    assert len(matches) == 1, f"{game_prefix} matched {len(matches)} envs"
    env = _retry(lambda: arcade.make(matches[0].game_id, scorecard_id=card_id),
                 f"make({game_prefix})")
    frame = _retry(lambda: env.reset(), f"reset({game_prefix})")
    n = 0
    t0 = time.time()
    for a in actions:
        name = a.get("name")
        if name == "RESET":
            frame = _retry(lambda: env.reset(), "reset")
        else:
            ga = ACTION_BY_NAME[name]
            data = None
            if name == "ACTION6":
                data = {"x": int(a["x"]), "y": int(a["y"])}
            frame = _retry(lambda ga=ga, data=data: env.step(ga, data=data), "step")
        n += 1
        state = getattr(frame, "state", None) or (frame.get("state") if isinstance(frame, dict) else None)
        if str(state) .endswith("WIN"):
            break
    return {"game": matches[0].game_id, "replayed": n,
            "state": str(state), "seconds": round(time.time() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="which runs/<model>/ ledgers to replay")
    ap.add_argument("--games",
                    help="comma-separated game prefixes, or 'all' for the 25-game set")
    ap.add_argument("--runs-root", default=str(ROOT / "runs"))
    ap.add_argument("--manifest",
                    help="JSON of {game: {events: path, ...}}: replay one explicit "
                         "ledger per game (e.g. best clean run per game); overrides "
                         "--model/--runs-root")
    ap.add_argument("--label", default=None,
                    help="name for the output file when using --manifest")
    ap.add_argument("--tag", action="append", default=None)
    args = ap.parse_args()

    manifest = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text())
        games = sorted(manifest)
    else:
        if not (args.model and args.games):
            ap.error("--model and --games are required without --manifest")
        games = list(GAMES) if args.games == "all" else args.games.split(",")
    shared = ROOT / ".arc-private"
    arcade = Arcade(operation_mode=OperationMode.COMPETITION,
                    environments_dir=str(shared / "environment_files"),
                    recordings_dir=str(shared / "recordings"))
    key = getattr(arcade, "arc_api_key", "") or ""
    print(f"key: {'registered ' + key[:8] if key else 'ANONYMOUS'}", flush=True)

    card = arcade.open_scorecard(
        tags=args.tag or ["kepler", "replay", args.model or args.label or "manifest"])
    print(f"card: {card}", flush=True)
    for g in games:
        evp = (Path(manifest[g]["events"]) if manifest
               else Path(args.runs_root) / args.model / g / "events.jsonl")
        if not evp.exists():
            print(f"{g}: NO LEDGER, skipped", flush=True)
            continue
        acts = final_attempt_actions(evp)
        try:
            out = replay_game(arcade, card, g, acts)
            print(f"{g}: {out['state']} after {out['replayed']} actions "
                  f"({out['seconds']}s)", flush=True)
        except Exception as exc:
            # Keep whatever progress reached the card; a nondeterministic game
            # (lf52 replays non-exactly; Retrodict documented the same) must
            # not sink the other 24. Disclosed wherever the URL is published.
            print(f"{g}: REPLAY DIVERGED ({type(exc).__name__}: {str(exc)[:80]}): "
                  "partial progress kept, continuing", flush=True)

    final = arcade.close_scorecard(card)
    d = json.loads(final.model_dump_json()) if hasattr(final, "model_dump_json") else final
    url = f"https://arcprize.org/scorecards/{card}"
    print(json.dumps({"scorecard_url": url, "score": d.get("score"),
                      "per_game": {e["id"]: (e["runs"][0].get("score") if e.get("runs") else None)
                                   for e in d.get("environments", [])}}, indent=2), flush=True)
    out_dir = ROOT / "runs-competition" / "replays"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{args.model or args.label or 'manifest'}-{int(time.time())}.json").write_text(
        json.dumps(d, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
