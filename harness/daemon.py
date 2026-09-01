"""Per-run game daemon.

Owns exactly one local ARC-AGI-3 environment and the append-only events.jsonl
timeline. Every real transition (including the initial RESET) is recorded here
and nowhere else; workspace tools talk to this daemon over localhost HTTP.

Endpoints:
  GET  /status  -> game state, level, counts, available actions, current grid
  POST /act     -> execute ONE action {"name": ..., "x": ..., "y": ...}
  POST /reset   -> reset the environment
  GET  /scorecard -> official local scorecard JSON for this run
  POST /shutdown

Usage: daemon.py --game ls20 --workspace <dir> --port 8765
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

logging.disable(logging.INFO)

from arc_agi import Arcade, OperationMode  # noqa: E402
from arcengine import GameAction  # noqa: E402

ACTION_BY_NAME = {a.name: a for a in GameAction}


class GameSession:
    def __init__(self, game_prefix: str, workspace: Path, tags: list[str],
                 competition: bool = False, scorecard_id: str | None = None):
        self.lock = threading.Lock()
        self.workspace = workspace
        self.events_path = workspace / "events.jsonl"
        # INTEGRITY: the toolkit materializes each game's Python implementation
        # (win conditions and all) into environments_dir. That must NEVER live
        # inside the agent's workspace — an agent that reads it can derive the
        # solution instead of modelling it, which invalidates the run. Keep it in
        # a shared directory outside every workspace; scripts/audit_integrity.py
        # flags any run whose session logs touch it.
        shared = Path(__file__).resolve().parent.parent / ".arc-private"
        # COMPETITION mode runs API-only against three.arcprize.org and yields a
        # shareable scorecard URL — the verification path Tycho and Retrodict used.
        # It also enforces stricter rules than local play: make() once per env,
        # and game resets are converted to level resets by the server, so the
        # learn-then-full-reset strategy does not exist there.
        self.competition = competition
        api_key = os.environ.get("ARC_API_KEY", "")
        self.arcade = Arcade(
            arc_api_key=api_key,
            operation_mode=OperationMode.COMPETITION if competition else OperationMode.NORMAL,
            environments_dir=str(shared / "environment_files"),
            recordings_dir=str(shared / "recordings"),
        )
        if competition:
            print(f"competition key: {'registered '+api_key[:8] if api_key else 'ANONYMOUS (cards expire fast)'}", flush=True)
        if competition:
            # The toolkit auto-closes a scorecard after 15 minutes idle. Frontier
            # models deliberate for minutes per action, so a hard game's card
            # expires mid-run and the win is never scored on the server -- exactly
            # what happened to re86 in the pilot. Push the idle window past any
            # realistic per-action think time.
            try:
                self.arcade.scorecard_manager.set_idle_for(24 * 60)
            except Exception as exc:
                print(f"set_idle_for failed: {exc}", flush=True)
        matches = [
            e for e in self.arcade.get_environments()
            if e.game_id.startswith(game_prefix.lower())
        ]
        if len(matches) != 1:
            raise SystemExit(
                f"game prefix {game_prefix!r} matched {[e.game_id for e in matches]}"
            )
        self.info = matches[0]
        self.game_id = self.info.game_id
        # A shared card lets one competition scorecard span many sequential game
        # daemons — one URL for the whole set, as the leaderboard entries do it.
        self.owns_card = scorecard_id is None
        self.card_id = scorecard_id or self.arcade.open_scorecard(tags=tags)
        self.env = self.arcade.make(self.game_id, scorecard_id=self.card_id)
        # A resumed run appends to an existing timeline: continue the numbering so
        # event indices stay unique and monotonic across runs.
        self.step_index = 0
        if self.events_path.exists():
            with open(self.events_path) as f:
                for line in f:
                    if line.strip():
                        self.step_index = json.loads(line)["i"] + 1
        self.run_start_index = self.step_index
        self.action_count = 0  # env actions this run, excluding the opening RESET
        self.prev_grid: Optional[list[list[int]]] = None
        self.last: dict[str, Any] = {}
        self._record(self.env.reset(), {"name": "RESET"}, reset=True)

    # ---------- recording ----------

    def _record(self, frame: Any, action: dict[str, Any], reset: bool = False) -> dict:
        if frame is None:
            raise RuntimeError("environment returned no frame")
        grids = frame.frame if frame.frame is not None else []
        grid = grids[-1] if len(grids) else None
        if grid is not None:
            grid = [[int(v) for v in row] for row in grid]
        state = str(frame.state).split(".")[-1]
        prev_level = self.last.get("level", 0)
        level = frame.levels_completed
        event = {
            "i": self.step_index,
            "ts": round(time.time(), 3),
            "action": action,
            "reset": reset,
            # full_reset = whole game restarted (fresh run / post-WIN); otherwise a
            # RESET only restarts the current level and its actions still count.
            "full_reset": bool(getattr(frame, "full_reset", False)) if reset else False,
            "prev_level": prev_level,
            "level": level,
            "level_up": (not reset) and level > prev_level,
            "state": state,
            "win": state == "WIN",
            "game_over": state == "GAME_OVER",
            "win_levels": frame.win_levels,
            "available_actions": list(frame.available_actions or []),
            "n_anim_frames": len(grids),
            "grid": grid,
            "prev_grid_changed_cells": self._diff_count(self.prev_grid, grid),
        }
        # Visual mode (v7 ablation): persist EVERY frame -- animation frames
        # included -- as PNGs the agent can look at. The text ledger keeps only
        # the settled grid; mechanisms that live in transient frames are
        # invisible to a text-only agent (KEPLER_VISUAL=1 gates the ablation).
        if os.environ.get("KEPLER_VISUAL") and grids:
            try:
                import sys as _sys
                _sys.path.insert(0, str(Path(__file__).resolve().parent / "ws_tools"))
                from _render_core import grid_to_png as _g2p
                fdir = self.events_path.parent / "frames"
                fdir.mkdir(exist_ok=True)
                for j, fr in enumerate(grids):
                    _g2p([[int(v) for v in row] for row in fr],
                         str(fdir / f"ev{self.step_index:05d}_f{j}.png"))
            except Exception as exc:
                print(f"visual frame dump failed (non-fatal): {exc}", flush=True)
        with open(self.events_path, "a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
        self.step_index += 1
        if not reset:
            self.action_count += 1
        self.prev_grid = grid
        self.last = event
        return event

    @staticmethod
    def _diff_count(a: Optional[list], b: Optional[list]) -> Optional[int]:
        if a is None or b is None:
            return None
        return sum(
            1 for r1, r2 in zip(a, b) for v1, v2 in zip(r1, r2) if v1 != v2
        )

    # ---------- api ----------

    def status(self) -> dict:
        e = self.last
        return {
            "game_id": self.game_id,
            "title": self.info.title,
            "state": e["state"],
            "level": e["level"],
            "win_levels": e["win_levels"],
            "available_actions": e["available_actions"],
            "step_index": self.step_index,
            "action_count": self.action_count,
            "grid": e["grid"],
            "human_baseline_actions": self.info.baseline_actions,
        }

    def act(self, action: dict[str, Any]) -> dict:
        name = action.get("name", "")
        if name not in ACTION_BY_NAME:
            return {"error": f"unknown action {name!r}"}
        ga = ACTION_BY_NAME[name]
        if ga == GameAction.RESET:
            return self.reset()
        data = None
        if name == "ACTION6":
            try:
                data = {"x": int(action["x"]), "y": int(action["y"])}
            except (KeyError, TypeError, ValueError):
                return {"error": "ACTION6 requires integer x and y"}
        reasoning = action.get("reasoning")
        rd = {"text": str(reasoning)[:2000]} if reasoning else None
        frame = self.env.step(ga, data=data, reasoning=rd)
        return self._record(frame, {k: v for k, v in action.items() if k in ("name", "x", "y")})

    def reset(self) -> dict:
        return self._record(self.env.reset(), {"name": "RESET"}, reset=True)

    def scorecard(self) -> dict:
        # Competition scorecards are 403 in flight and 404 by id once closed; the
        # only way to read one is the value close_scorecard() returns, which is the
        # fully-scored card. Local NORMAL cards are readable by get_scorecard any time.
        if self.competition and self.owns_card:
            try:
                card = self.arcade.close_scorecard(self.card_id)
            except Exception as exc:
                return {"error": f"close_scorecard: {type(exc).__name__}: {exc}",
                        "card_id": self.card_id}
        else:
            card = self.arcade.get_scorecard(self.card_id)
        d = json.loads(card.model_dump_json()) if hasattr(card, "model_dump_json") else card
        if self.competition:
            d["scorecard_url"] = f"https://arcprize.org/scorecards/{self.card_id}"
        return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--competition", action="store_true",
                    help="API-only competition mode: shareable scorecard, single "
                         "attempt per env, game resets become level resets")
    ap.add_argument("--scorecard-id", default=None,
                    help="join an existing scorecard instead of opening one "
                         "(one card can span all 25 games)")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    os.chdir(ws)
    session = GameSession(args.game, ws, args.tag, competition=args.competition, scorecard_id=args.scorecard_id)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:
            pass

        def _send(self, obj: Any, code: int = 200) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            with session.lock:
                if self.path == "/status":
                    self._send(session.status())
                elif self.path == "/scorecard":
                    self._send(session.scorecard())
                else:
                    self._send({"error": "not found"}, 404)

        def do_POST(self) -> None:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}") if n else {}
            with session.lock:
                if self.path == "/act":
                    try:
                        self._send(session.act(payload))
                    except Exception as exc:  # surface env errors to the tool
                        self._send({"error": f"{type(exc).__name__}: {exc}"}, 500)
                elif self.path == "/reset":
                    self._send(session.reset())
                elif self.path == "/shutdown":
                    self._send({"ok": True})
                    threading.Thread(target=server.shutdown).start()
                else:
                    self._send({"error": "not found"}, 404)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    (ws / ".daemon.json").write_text(
        json.dumps({"port": args.port, "pid": os.getpid(), "game_id": session.game_id})
    )
    print(f"daemon ready game={session.game_id} port={args.port}", flush=True)
    server.serve_forever()
    # dump final scorecard on shutdown
    (ws / "scorecard.json").write_text(json.dumps(session.scorecard(), indent=2))


if __name__ == "__main__":
    sys.exit(main())
