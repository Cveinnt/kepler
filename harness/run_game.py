"""Outer loop: run one Kepler agent (one model) on one game to completion.

Sets up the workspace, starts the game daemon, then repeatedly launches CLI-agent
sessions (codex / claude) until WIN or budget exhaustion. Continuity between
sessions lives in the workspace files (notes.md, world_model.py, events.jsonl).

Usage:
  .venv/bin/python harness/run_game.py --game ls20 --model gpt-xhigh \
      [--runs-root runs] [--max-actions N] [--max-hours 8] [--max-sessions 12]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"

MODELS: dict[str, dict] = {
    "gpt-xhigh": {
        "kind": "codex",
        "model": "gpt-5.6-sol",
        "effort": "xhigh",
    },
    "gpt-max": {
        "kind": "codex",
        "model": "gpt-5.6-sol",
        "effort": "max",
    },
    "opus": {"kind": "claude", "model": "opus"},
    "fable": {"kind": "claude", "model": "fable"},
    # Free tier, via the opencode CLI. The harness is model-agnostic by design —
    # it drives whatever coding agent you already have — and opencode's free models
    # cost nothing, so the reproduction does not require paid frontier quota to try.
    # Expect much lower scores: the methodology asks the agent to write and debug an
    # executable world model, which is squarely a coding-ability task.
    "deepseek-free": {"kind": "opencode", "model": "opencode/deepseek-v4-flash-free"},
    # Other coding-agent CLIs. The harness only needs a CLI that can read files,
    # run shell commands and edit a workspace — which model sits behind it is the
    # variable under test, so adding a CLI is a few lines, not a port.
    "kimi": {"kind": "kimi", "model": "kimi-code/k3"},
    # Google's agentic CLI — generous free tier (user logs in via `gemini`).
    "gemini": {"kind": "gemini", "model": None},
    "muse": {"kind": "muse", "model": None, "effort": "high"},
}
# opencode's catalogue rotates, so pinning names here rots. Any opencode model can
# be driven directly with `--model opencode:<id>`; run `opencode models` for the
# current list.
OPENCODE_PREFIX = "opencode:"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_json(port: int, path: str, payload: dict | None = None, timeout: int = 60) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    if payload is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def setup_workspace(ws: Path, baseline: bool = False, competition: bool = False) -> None:
    ws.mkdir(parents=True, exist_ok=True)
    tools = ws / "tools"
    tools.mkdir(exist_ok=True)
    if baseline:
        # Ablation: same model, same env, same budgets — but NO Kepler methodology.
        # The agent observes and acts directly; no world model, backtest, BFS, or
        # prediction-voided plans. Measures the harness's contribution to the score.
        for name in ("_lib.py", "observe.py"):
            shutil.copy(HARNESS / "ws_tools" / name, tools / name)
        (tools / "act.py").write_text(
            '#!/usr/bin/env python3\n'
            '"""Execute game actions directly. Usage:\n'
            '  python tools/act.py --actions \'[{"name":"ACTION1"},'
            '{"name":"ACTION6","x":3,"y":40},{"name":"RESET"}]\'\n"""\n'
            'import argparse, json\n'
            'from _lib import daemon, action_str, normalize_action\n'
            'ap = argparse.ArgumentParser(); ap.add_argument("--actions", required=True)\n'
            'a = ap.parse_args()\n'
            'for act in json.loads(a.actions):\n'
            '    act = {"name": "RESET"} if act.get("name") == "RESET" else normalize_action(act)\n'
            '    ev = daemon("/reset", {}) if act["name"] == "RESET" else daemon("/act", act)\n'
            '    if "error" in ev: print(action_str(act), "ERROR:", ev["error"]); break\n'
            '    print(f"{action_str(act)} -> level {ev[\'level\']}/{ev[\'win_levels\']} '
            '{ev[\'state\']} changed={ev[\'prev_grid_changed_cells\']}")\n'
            '    if ev["win"] or ev["game_over"] or ev["level_up"]: break\n'
        )
        directive = (
            "# ARC-AGI-3 agent (baseline)\n\n"
            "You are playing one unseen ARC-AGI-3 game: a 64x64 grid of 16 colors, no "
            "rules given. Observe with `python tools/observe.py` (free), act with "
            "`python tools/act.py --actions '[...]'` (ACTION1-4 usually move, ACTION5 "
            "enter/space, ACTION6 click x,y, ACTION7 undo, RESET restarts the level). "
            "Score is Relative Human Action Efficiency: per level min((human/yours)^2, "
            "1.15), later levels weighted more, every action counts. observe.py shows "
            "the human baselines. Play until state=WIN, in as few actions as you can. "
            "Work autonomously; do not stop early; do not ask questions.\n"
        )
    else:
        for f in (HARNESS / "ws_tools").glob("*.py"):
            if f.name == "world_model_template.py":
                continue
            shutil.copy(f, tools / f.name)
        if not (ws / "world_model.py").exists():
            shutil.copy(HARNESS / "ws_tools" / "world_model_template.py", ws / "world_model.py")
        if not (ws / "notes.md").exists():
            (ws / "notes.md").write_text(
                "# Lab notebook\n\n(nothing yet — first observation pending)\n"
            )
        directive = (HARNESS / "directive.md").read_text()
        if os.environ.get("KEPLER_VISUAL_DIRECTIVE"):
            directive += (
                "\n## VISUAL MODE (this run)\n\n"
                "You have vision -- use it. Every frame of every action, including\n"
                "ANIMATION frames, is saved as a PNG under frames/ (evNNNNN_fK.png),\n"
                "and python tools/render.py renders any frame on demand. Look at\n"
                "frames before theorizing over cell diffs: transient animation frames\n"
                "often show a mechanism (a path, an emission, a split) that the\n"
                "settled grid erases. When a residual or anomaly resists explanation,\n"
                "VIEW the animation strip for that event (python tools/render.py\n"
                "--event N --strip) before designing more probes.\n")
    if competition:
        directive += (
            "\n## COMPETITION MODE — rules differ from local play\n\n"
            "This run is scored on the official ARC-AGI-3 server. Two rules change:\n"
            "1. You get ONE continuous attempt at this game. There is no full reset: a "
            "game reset is converted by the server into a LEVEL reset. The "
            "learn-everything-then-full-reset-and-speedrun strategy DOES NOT EXIST "
            "here — do not plan for it.\n"
            "2. Every action you commit is permanently on the scorecard. Deliberate "
            "longer before acting; there is no unscored exploration pass.\n"
        )
    (ws / "AGENTS.md").write_text(directive)
    (ws / "CLAUDE.md").write_text(directive)
    if baseline:
        # Mark ablation workspaces intrinsically, not by directory name. The audit's
        # contamination check keyed on the path "runs-baseline", which meant a valid
        # ablation could not be run anywhere else -- and running it outside the repo
        # tree is exactly how you stop the agent finding harness/ws_tools and
        # rebuilding the methodology it is supposed to be a control for.
        (ws / ".baseline").write_text(
            "This workspace is an ablation control: observe + act only.\n"
            "No world model, certification, planning, or guarded channel.\n")


def session_cmd(cfg: dict, ws: Path, prompt: str) -> list[str]:
    if cfg["kind"] == "codex":
        img = ws / "frames" / "current.png"
        extra = ["-i", str(img)] if (os.environ.get("KEPLER_VISUAL_DIRECTIVE") and img.exists()) else []
        return [
            "codex", "exec", *extra,
            "--cd", str(ws),
            "--skip-git-repo-check",
            "--sandbox", "danger-full-access",
            "-c", "approval_policy=never",
            "-m", cfg["model"],
            "-c", f"model_reasoning_effort={cfg['effort']}",
            prompt,
        ]
    if cfg["kind"] == "gemini":
        return ["gemini", "--yolo", "-p", prompt]
    if cfg["kind"] == "opencode":
        return [
            "opencode", "run",
            # --pure disables the user's locally-installed opencode plugins. Without
            # it the run measures somebody's plugin stack as much as the model: in a
            # first pass, plugins asked for directories outside the workspace, were
            # auto-rejected, and the agent burned whole sessions on failed shell
            # calls instead of the game.
            "--pure",
            "--model", cfg["model"],
            prompt,
        ]
    if cfg["kind"] == "kimi":
        # -p is already unattended: kimi rejects both -y and --auto alongside it,
        # and prompt mode runs tools without prompting (verified — it created a
        # file via its Write tool with no approval flag).
        cmd = ["kimi", "-p", prompt]
        if cfg.get("model"):
            cmd += ["-m", cfg["model"]]
        return cmd
    if cfg["kind"] == "muse":
        cmd = ["muse", "exec", prompt, "--workspace", str(ws)]
        if cfg.get("model"):
            cmd += ["--model", cfg["model"]]
        if cfg.get("effort"):
            cmd += ["--reasoning-effort", cfg["effort"]]
        return cmd
    return [
        "claude", "-p", prompt,
        "--model", cfg["model"],
        "--permission-mode", "bypassPermissions",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--model", required=True,
                    help="one of: " + ", ".join(MODELS) +
                         f"; or {OPENCODE_PREFIX}<id> for any opencode model "
                         "(run `opencode models` to list them)")
    ap.add_argument("--runs-root", default=str(ROOT / "runs"))
    ap.add_argument("--max-actions", type=int, default=None,
                    help="default: 20x total human baseline")
    ap.add_argument("--max-hours", type=float, default=8.0)
    ap.add_argument("--session-mem-cap-gb", type=int, default=24,
                    help="address-space cap (GB) for each session subtree; guards the host against a runaway agent search")
    ap.add_argument("--final-level-grace-hours", type=float, default=4.0,
                    help="v6: extra wall-clock granted while the run is on its final level")
    ap.add_argument("--max-sessions", type=int, default=12)
    ap.add_argument("--session-timeout", type=int, default=10800)
    ap.add_argument("--force", action="store_true", help="wipe an existing workspace")
    ap.add_argument("--baseline", action="store_true",
                    help="ablation: no Kepler methodology — observe/act tools only")
    ap.add_argument("--competition", action="store_true",
                    help="API-only competition mode against three.arcprize.org: "
                         "produces a shareable arcprize.org scorecard. Single "
                         "attempt per game; game resets become level resets; "
                         "--resume is not allowed.")
    ap.add_argument("--scorecard-id", default=None,
                    help="join an existing competition scorecard (one card can "
                         "span all 25 games)")
    ap.add_argument("--clean-run-min", type=float, default=100.0,
                    help="local mode: a WIN scoring below this triggers a clean-run "
                         "phase (fresh attempt executing the known solution)")
    ap.add_argument("--max-clean-runs", type=int, default=3,
                    help="local mode: how many certify+mechanical-execute repair "
                         "cycles after an inefficient win (0 disables). Execution "
                         "is harness-driven (tools/cleanrun.py), so a repair can "
                         "only fail closed, never play worse live")
    ap.add_argument("--resume", action="store_true",
                    help="reuse an interrupted workspace (keeps world_model/notes/timeline; "
                         "the environment and scorecard restart fresh)")
    ap.add_argument("--visual", action="store_true",
                    help="v7 ablation: daemon saves every frame (incl. animation) as PNG; directive tells the agent to LOOK")
    args = ap.parse_args()

    if args.visual:
        os.environ["KEPLER_VISUAL_DIRECTIVE"] = "1"
    if args.competition and args.resume:
        raise SystemExit("--competition allows a single attempt per environment; "
                         "--resume would call make() twice on the same card")
    if args.model.startswith(OPENCODE_PREFIX):
        cfg = {"kind": "opencode", "model": args.model[len(OPENCODE_PREFIX):]}
    elif args.model in MODELS:
        cfg = MODELS[args.model]
    else:
        raise SystemExit(f"unknown --model {args.model!r}; choose from "
                         f"{', '.join(MODELS)} or {OPENCODE_PREFIX}<id>")
    ws = Path(args.runs_root).resolve() / args.model / args.game
    if ws.exists() and args.force:
        shutil.rmtree(ws)
    if (ws / "events.jsonl").exists() and not args.resume:
        print(f"workspace {ws} already has a timeline; use --force or --resume")
        return 1
    setup_workspace(ws, baseline=args.baseline, competition=args.competition)
    (ws / "sessions").mkdir(exist_ok=True)

    port = free_port()
    daemon_log = open(ws / "daemon.log", "w")
    daemon_env = dict(os.environ)
    if args.visual:
        daemon_env["KEPLER_VISUAL"] = "1"
    # Load ARC_API_KEY from .env so competition daemons use the REGISTERED key.
    # Without this each daemon falls back to a fresh anonymous key, whose
    # scorecards expire server-side within a few hours -- which silently sank
    # every long competition run (re86) while short ones squeaked through.
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                daemon_env.setdefault(k.strip(), v.strip())
    daemon = subprocess.Popen(
        [str(VENV_PY), str(HARNESS / "daemon.py"),
         "--game", args.game, "--workspace", str(ws), "--port", str(port),
         "--tag", f"kepler-{args.model}"]
        + (["--competition"] if args.competition else [])
        + (["--scorecard-id", args.scorecard_id] if args.scorecard_id else []),
        stdout=daemon_log, stderr=subprocess.STDOUT, env=daemon_env,
    )
    try:
        for _ in range(60):
            try:
                st = http_json(port, "/status")
                break
            except Exception:
                if daemon.poll() is not None:
                    print("daemon died on startup; see daemon.log")
                    return 1
                time.sleep(0.5)
        else:
            print("daemon did not become ready")
            return 1

        max_actions = args.max_actions or 20 * sum(st["human_baseline_actions"] or [100])
        t0 = time.time()
        result_note = "budget_exhausted"

        def _full_resets() -> int:
            evp = ws / "events.jsonl"
            if not evp.exists():
                return 0
            return sum(1 for l in evp.read_text().splitlines()
                       if l.strip() and json.loads(l).get("full_reset"))

        def _current_score(gid: str):
            try:
                for e in _iter_env_scores(http_json(port, "/scorecard")):
                    if e.get("id", "").startswith(gid[:4]):
                        return e.get("score")
            except Exception:
                pass
            return None

        # Only the FINAL attempt is scored, so a sloppy win is repairable: start a
        # fresh attempt and execute the now-known solution near baseline. Local
        # mode only — in competition /scorecard closes the card, and replay
        # already takes the last attempt. Capped: a failed repair attempt would
        # REPLACE the winning one and lower the score, so the prompt insists on
        # consolidation before the reset and we allow few tries.
        clean_prompt = None
        # Simplification pass (adopted from baseline1's ewma_sv treatment): when a
        # session ends with no level progress and the level has already consumed
        # 2x its human baseline, the next session is a maintenance session — no
        # live play — that compresses the world model. Fires at most once per level.
        prev_session_level = None
        simplified_levels: set[int] = set()
        clean_tries = 0
        resets_at_win = None
        for session_i in range(1, args.max_sessions + 1):
            st = http_json(port, "/status")
            if st["state"] == "WIN":
                if args.competition or args.max_clean_runs <= 0:
                    result_note = "win"
                    break
                if resets_at_win is not None and _full_resets() > resets_at_win:
                    result_note = "win (clean run)"
                    break
                sc = _current_score(st["game_id"])
                if sc is None or sc >= args.clean_run_min:
                    result_note = "win"
                    break
                if clean_tries >= args.max_clean_runs:
                    result_note = f"win (score {sc:.1f}, clean-run budget spent)"
                    break
                clean_tries += 1
                resets_at_win = _full_resets()
                print(f"[{args.game}/{args.model}] WIN at score {sc:.1f} < "
                      f"{args.clean_run_min} — clean-run phase "
                      f"{clean_tries}/{args.max_clean_runs}", flush=True)
                clean_prompt = (
                    f"You have already WON this game, but the winning attempt was "
                    f"inefficient: score {sc:.1f}, and each level scores "
                    f"min((baseline/actions)^2, 1.15). Only the final attempt is "
                    f"scored, and the harness will EXECUTE the repair attempt "
                    f"mechanically — your ONLY job is the certificate. Derive from "
                    f"your world model the tightest program for EVERY level and "
                    f'write cleanrun.json in the workspace root: '
                    f'{{"programs": [[action, ...], ...]}} — full action lists, one '
                    f"per level, each within 1.3x that level's human baseline. "
                    f"Validate with: python tools/cleanrun.py --dry-run (it also "
                    f"simulates each program from the recorded level-start grid "
                    f"when world_model.py has init_state/step_state/outcome — make "
                    f"sure it does). Do NOT commit a RESET; do NOT play the game. "
                    f"When --dry-run passes, your work is done.")
            # Budget from the LEDGER, not the daemon process: daemon counters
            # start at 0 on every resume, which silently refilled the tank and
            # let one run reach 2x its budget across quota resumes.
            ledger_actions = 0
            evp = ws / "events.jsonl"
            if evp.exists():
                ledger_actions = sum(
                    1 for l in evp.read_text().splitlines()
                    if l.strip() and '"action"' in l)
            if max(st["action_count"], ledger_actions) >= max_actions:
                result_note = (f"action budget exhausted "
                               f"({max(st['action_count'], ledger_actions)})")
                break
            hours_left = args.max_hours - (time.time() - t0) / 3600
            if hours_left <= 0:
                # v6: never kill a run on its FINAL level — the completion cap
                # (80 -> 100) is worth more than any hour. A bounded grace applies.
                on_final = st["level"] == st["win_levels"] - 1 and st["state"] != "WIN"
                grace_left = args.max_hours + args.final_level_grace_hours - (time.time() - t0) / 3600
                if on_final and grace_left > 0:
                    hours_left = grace_left
                else:
                    result_note = "wall clock exhausted"
                    break

            first = session_i == 1 and st["action_count"] == 0
            simplify_now = False
            if not first and st["state"] not in ("WIN",) and prev_session_level == st["level"] \
                    and st["level"] not in simplified_levels:
                bases = st.get("human_baseline_actions") or []
                base = bases[st["level"]] if st["level"] < len(bases) else 0
                lvl_actions = 0
                if evp.exists():
                    for l in evp.read_text().splitlines():
                        if not l.strip():
                            continue
                        try:
                            e = json.loads(l)
                        except ValueError:
                            continue
                        if isinstance(e.get("action"), dict) and \
                                e.get("prev_level", e.get("level")) == st["level"]:
                            lvl_actions += 1
                if base > 0 and lvl_actions >= 2 * base:
                    simplify_now = True
                    simplified_levels.add(st["level"])
            prev_session_level = st["level"]
            if clean_prompt is not None and st["state"] == "WIN":
                prompt = clean_prompt
            elif simplify_now:
                print(f"[{args.game}/{args.model}] simplification session for level "
                      f"{st['level']}", flush=True)
                prompt = (
                    f"MAINTENANCE SESSION — do not take live game actions this session. "
                    f"Level {st['level']} has resisted far past its baseline, which is a "
                    f"strong signal your model of the game is more complicated than the "
                    f"game. Review world_model.py and notes.md and SIMPLIFY: assume the "
                    f"real mechanics are simpler than your current implementation, and do "
                    f"not defend the current model. Ask, for every special case, rule, "
                    f"object type, or state field: is this distinction actually forced by "
                    f"the evidence, or is it modeling observed trajectories too literally? "
                    f"Replace case-by-case behaviour with fewer, shared, parameterised "
                    f"rules. The goal is usually the same across levels and the solution "
                    f"is likely simple — you may be overthinking. Re-derive the level "
                    f"objective from what changed at the exact moments earlier levels "
                    f"ended (level_up and GAME_OVER frames), not from whatever changes. "
                    f"Then verify the simplified model retrodicts the recorded history "
                    f"(python tools/backtest.py) and record in notes.md the single "
                    f"cheapest live experiment that would separate your top two "
                    f"hypotheses. End the session after that — the next session plays."
                )
            else:
                prompt = (
                f"{'You are starting on' if first else 'Continue playing'} the ARC-AGI-3 "
                f"game {st['title']}. Status: state={st['state']}, level "
                f"{st['level']}/{st['win_levels']}, {st['action_count']} actions used so far. "
                f"Follow your directive ({'CLAUDE.md' if cfg['kind'] == 'claude' else 'AGENTS.md'}) "
                f"strictly: observe, build/repair world_model.py, certify with backtest, "
                f"plan with bfs, act only via tools/commit.py. "
                f"{'Read notes.md first to restore your understanding. ' if not first else ''}"
                f"Play until state=WIN. Do not stop early; do not ask questions."
                )
            if args.visual:
                # VISTA-fidelity: put the CURRENT frame in front of the model at
                # session start (codex: attached to the prompt; claude: first Read).
                try:
                    import sys as _sys
                    _sys.path.insert(0, str(HARNESS / "ws_tools"))
                    from _render_core import grid_to_png as _g2p
                    if st.get("grid"):
                        (ws / "frames").mkdir(exist_ok=True)
                        _g2p(st["grid"], str(ws / "frames" / "current.png"))
                except Exception as exc:
                    print(f"current-frame render failed (non-fatal): {exc}", flush=True)
                prompt = ("FIRST: view frames/current.png (open/Read the image — you "
                          "have vision) before taking any other step. ") + prompt
            log_path = ws / "sessions" / f"session-{session_i:02d}.log"
            print(f"[{args.game}/{args.model}] session {session_i} starting "
                  f"(level {st['level']}, {st['action_count']} actions)", flush=True)
            actions_before = st["action_count"]
            mtimes_before = tuple(
                (ws / f).stat().st_mtime if (ws / f).exists() else 0
                for f in ("world_model.py", "notes.md")
            )
            with open(log_path, "w") as log:
                try:
                    # Memory safety: cap the session subtree's address space so an
                    # agent-spawned exhaustive search cannot OOM the host (an sp80
                    # search once hit 10GB+ RSS and forced a machine reboot). The cap
                    # is generous (does not touch scored behavior — an OOM search
                    # would have crashed anyway) and best-effort (skipped where the
                    # shell lacks ulimit -v).
                    _capped = ["/bin/sh", "-c",
                               f"ulimit -v {args.session_mem_cap_gb * 1024 * 1024} 2>/dev/null; "
                               'exec "$@"', "sh"] + session_cmd(cfg, ws, prompt)
                    subprocess.run(
                        _capped,
                        cwd=ws, stdout=log, stderr=subprocess.STDOUT,
                        timeout=min(args.session_timeout, hours_left * 3600),
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    print(f"session {session_i} timed out", flush=True)

            if clean_prompt is not None and prompt == clean_prompt:
                cr = subprocess.run(
                    [sys.executable, str(ws / "tools" / "cleanrun.py")],
                    cwd=ws, capture_output=True, text=True, timeout=3600)
                print(f"[{args.game}/{args.model}] mechanical clean run: "
                      f"{(cr.stdout or cr.stderr).strip().splitlines()[-1] if (cr.stdout or cr.stderr).strip() else 'no output'}",
                      flush=True)
            st = http_json(port, "/status")
            print(f"[{args.game}/{args.model}] session {session_i} done: "
                  f"state={st['state']} level={st['level']}/{st['win_levels']} "
                  f"actions={st['action_count']}", flush=True)
            log_text = log_path.read_text(errors="ignore")
            import re as _re
            if (_re.search(r"hit your \w+[\w ]* limit"
                           # kimi/opencode word it differently; a run that stops on
                           # quota must not be recorded as the agent stalling.
                           r"|reached your usage limit|usage limit for this billing"
                           r"|Rate limit exceeded", log_text)
                    and st["action_count"] == actions_before):
                # Provider quota exhausted: abort WITHOUT writing result.json so the
                # workspace stays resumable and score.py sees "not run", not a zero.
                print(f"[{args.game}/{args.model}] provider usage limit hit — aborting "
                      f"without a result; resume with --resume when quota returns")
                return 3
            # Transient provider failure is NOT an agent stall. Overnight codex
            # dropped its response stream repeatedly ("Reconnecting... 5/5",
            # "stream disconnected before completion"); sessions produced zero
            # actions, tripped the two-strike stall rule, and killed three lanes —
            # including an unresumable competition run at level 5/8. When the log
            # shows connection errors and no real work, wait out the outage with
            # backoff and try again without counting a strike.
            transient = (st["action_count"] == actions_before
                         and _re.search(r"Reconnecting\.\.\. \d/\d"
                                        r"|stream disconnected before completion"
                                        r"|error sending request for url", log_text))
            if transient:
                retries = json.loads((ws / ".net_retries").read_text()) if (ws / ".net_retries").exists() else 0
                retries += 1
                (ws / ".net_retries").write_text(json.dumps(retries))
                if retries > 12:
                    result_note = "provider unreachable across 12 backoff retries"
                    break
                delay = min(300 * retries, 1800)
                print(f"[{args.game}/{args.model}] provider stream errors, no actions — "
                      f"backoff {delay}s (retry {retries}/12), not counted as a stall",
                      flush=True)
                time.sleep(delay)
                continue
            (ws / ".net_retries").write_text("0")
            mtimes_after = tuple(
                (ws / f).stat().st_mtime if (ws / f).exists() else 0
                for f in ("world_model.py", "notes.md")
            )
            if (st["state"] != "WIN" and st["action_count"] == actions_before
                    and mtimes_after == mtimes_before):
                stall = json.loads((ws / ".stall").read_text()) if (ws / ".stall").exists() else 0
                stall += 1
                (ws / ".stall").write_text(json.dumps(stall))
                if stall >= 2:
                    result_note = "stalled (two sessions with no actions)"
                    break
            else:
                (ws / ".stall").write_text("0")

        st = http_json(port, "/status")
        card = http_json(port, "/scorecard")
        (ws / "scorecard.json").write_text(json.dumps(card, indent=2))
        try:
            hv = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout.strip()
        except Exception:
            hv = "unknown"
        result = {
            "harness_version": hv,
            "game": args.game,
            "game_id": st["game_id"],
            "model": args.model,
            "state": st["state"],
            "levels_completed": st["level"],
            "win_levels": st["win_levels"],
            "actions": st["action_count"],
            "note": result_note,
            "elapsed_hours": round((time.time() - t0) / 3600, 2),
        }
        if card.get("scorecard_url"):
            # The verifiable ARC Prize URL for this competition run.
            result["scorecard_url"] = card["scorecard_url"]
            result["competition"] = True
        for env_score in _iter_env_scores(card):
            if env_score.get("id", "").startswith(st["game_id"][:4]):
                result["score"] = env_score.get("score")
                result["level_scores"] = env_score.get("level_scores")
                result["level_actions"] = env_score.get("level_actions")
        (ws / "result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return 0
    finally:
        try:
            http_json(port, "/shutdown", {})
        except Exception:
            pass
        try:
            daemon.wait(timeout=15)
        except Exception:
            daemon.kill()
        daemon_log.close()


def _iter_env_scores(card: dict):
    for key in ("environments", "cards", "scores"):
        v = card.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    if isinstance(item.get("runs"), list):
                        best = max(item["runs"], key=lambda r: r.get("score", 0), default=None)
                        if best:
                            yield {**best, "id": item.get("id", best.get("id", ""))}
                    else:
                        yield item


if __name__ == "__main__":
    sys.exit(main())
