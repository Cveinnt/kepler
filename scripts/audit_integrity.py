#!/usr/bin/env python3
"""Adversarial integrity audit of every run.

Checks each run's session logs and workspace for the ways a score could be
illegitimate, and prints a per-run verdict. Exit code 1 if anything is flagged.

Checks
  SOURCE_READ  the agent read the local game implementation
               (.arc/environment_files/<game>/<hash>/<game>.py) or the engine
               internals, this leaks win conditions and invalidates the run
  SCORE_WRITE  the agent wrote result.json / scorecard.json itself
  TOOL_BYPASS  the agent hit the daemon directly instead of via commit.py
  TIMELINE_EDIT the append-only timeline was rewritten (indices non-monotonic)
  HARNESS_EDIT the agent modified the tools it is scored by
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Flag ACCESS to the game's implementation, not prose mentioning it. The directive
# itself names these paths (to forbid them) and the repo AGENTS.md lists them as
# git-ignored, so a bare substring match fires on agents *reading the rule*.
# Require a read/search command taking such a path as its target.
_READ_CMD = r"(cat|sed|head|tail|less|more|awk|grep|rg|find|ls|open\(|read_file|Read |python3? )"
_SECRET_PATH = r"[^\n]{0,40}(environment_files|\.arc/|arcengine|arc_agi/|site-packages)[^\n]{0,40}\.(py|json)"
SOURCE_PAT = re.compile(_READ_CMD + _SECRET_PATH, re.I)
# Bypassing commit.py's prediction check means hitting a MUTATING endpoint directly.
# /status is read-only (same data observe.py returns), so reading it is not a bypass.
BYPASS_PAT = re.compile(
    r"(curl|urlopen|requests\.(get|post))[^\n]{0,120}(127\.0\.0\.1|localhost)[^\n]{0,40}/(act|reset)\b",
    re.I)
SCORE_WRITE_PAT = re.compile(r">\s*(result|scorecard)\.json|open\(['\"][^'\"]*(result|scorecard)\.json['\"],\s*['\"]w", re.I)
# Real edits use an edit verb or a redirect INTO the file; a redirect elsewhere on the
# same command line (e.g. ">/dev/null && python3 tools/backtest.py") is not an edit.
# External network access: agents run with a permissive sandbox, so they *could*
# look up the benchmark online. Local daemon traffic (127.0.0.1/localhost) is the
# game itself and is expected; anything else is not.
NETWORK_PAT = re.compile(
    # The codex CLI prints its own quota URL (chatgpt.com/codex/settings/usage) on
    # rate limits; that is the tool talking, not the agent fetching. Require an
    # actual fetch command against a non-local host.
    r"(curl|wget|urlopen\(|requests\.(get|post)\()[^\n]{0,60}https?://"
    r"(?!127\.0\.0\.1|localhost)(?!chatgpt\.com/codex/settings)|web_search|WebFetch\("
    # Some coding CLIs ship their own web search/fetch tools, which are a direct
    # route to looking the answer up. kimi has moonshot_search / moonshot_fetch
    # enabled by default; muse and others have equivalents. Catch the tool call
    # itself, not just raw HTTP.
    r"|moonshot_search|moonshot_fetch|api\.kimi\.com/coding/v1/(search|fetch)"
    r"|\bWebSearch\b|\bweb_fetch\b|\bbrowser_(search|navigate)\b",
    re.I)
HARNESS_EDIT_PAT = re.compile(
    r"(edit_file|write_file|apply_patch|sed -i|tee)[^\n]{0,60}tools/(commit|backtest|bfs|_lib|observe|query)\.py"
    r"|>{1,2}\s*tools/(commit|backtest|bfs|_lib|observe|query)\.py", re.I)


# A --baseline run is the ablation: it is given ONLY observe.py/_lib.py/act.py, and
# its whole meaning is that the methodology is absent. Because the workspace lives
# inside the repo, agents found harness/ws_tools/ and put it back -- all six of the
# first baseline runs did, some via `cp`, some via run_path() shims. That silently
# turned the ablation into harness-vs-harness. Never again silently.
BASELINE_TOOLS = ("commit.py", "backtest.py", "bfs.py", "query.py", "world_model_template.py")


def audit_baseline(ws: Path) -> list[str]:
    hits = []
    for name in BASELINE_TOOLS:
        if (ws / "tools" / name).exists():
            hits.append(f"tools/{name} present in a baseline workspace")
    if (ws / "world_model.py").exists():
        hits.append("world_model.py present in a baseline workspace")
    return hits


def audit_run(ws: Path) -> dict:
    flags: dict[str, list[str]] = {}
    # Ablation runs are identified by the marker the harness writes, not by
    # directory name, a valid ablation has to be runnable outside the repo tree.
    if (ws / ".baseline").exists() or "runs-baseline" in ws.parts:
        hits = audit_baseline(ws)
        if hits:
            flags["BASELINE_CONTAMINATED"] = hits
    # Session tees, plus any transcripts recovered from the CLIs' own session
    # storage (scripts/recover_traces.py), both are the agent's behavioural record.
    logs = sorted(glob.glob(str(ws / "sessions" / "*.log")))
    logs += sorted(glob.glob(str(ws / "transcripts" / "*.jsonl")))
    if not logs:
        # No transcripts on disk -> the behavioural checks cannot run. This is NOT
        # the same as clean, and must never be reported as such.
        flags["NO_LOGS"] = ["session logs unavailable; behavioural checks not run"]
    text = ""
    for p in logs:
        try:
            text += Path(p).read_text(errors="ignore")
        except OSError:
            pass

    for name, pat in () if not logs else (
        ("SOURCE_READ", SOURCE_PAT),
        ("TOOL_BYPASS", BYPASS_PAT),
        ("SCORE_WRITE", SCORE_WRITE_PAT),
        ("HARNESS_EDIT", HARNESS_EDIT_PAT),
        ("NETWORK", NETWORK_PAT),
    ):
        hits = [m.group(0)[:90] for m in pat.finditer(text)]
        if hits:
            flags[name] = hits[:4] + ([f"... {len(hits)} total"] if len(hits) > 4 else [])

    # timeline integrity: indices must be strictly increasing
    ev = ws / "events.jsonl"
    if ev.exists():
        prev = -1
        for line in ev.read_text(errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                i = json.loads(line)["i"]
            except Exception:
                flags.setdefault("TIMELINE_EDIT", ["unparseable line"])
                break
            if i <= prev:
                # A resumed run restarts the daemon, which (before the fix) restarted
                # index numbering at 0 on its opening RESET. That is a known harness
                # defect, not tampering: the timeline is still append-only.
                if i == 0 and json.loads(line).get("reset"):
                    prev = i
                    continue
                flags.setdefault("TIMELINE_EDIT", []).append(f"index {i} after {prev}")
                break
            prev = i
    return flags


def audit_export_row(traces: Path, row: dict) -> dict:
    """Audit one row from scripts/export_traces.py without reconstructing a workspace."""
    flags: dict[str, list[str]] = {}
    label = str(row.get("model", "unknown"))
    game = str(row.get("game", "unknown"))

    if label.startswith("baseline-") and row.get("world_model_py"):
        flags["BASELINE_CONTAMINATED"] = [
            "world_model.py present in a baseline export"]

    log_root = traces / "agent_logs" / label / game
    logs = sorted(log_root.glob("sessions/*.log.gz"))
    logs += sorted(log_root.glob("transcripts/*.jsonl.gz"))
    if not logs:
        flags["NO_LOGS"] = [
            "session logs unavailable; behavioural checks not run"]
    text = ""
    for path in logs:
        try:
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
                text += handle.read()
        except OSError:
            flags.setdefault("NO_LOGS", []).append(f"could not read {path.name}")

    for name, pattern in () if not logs else (
        ("SOURCE_READ", SOURCE_PAT),
        ("TOOL_BYPASS", BYPASS_PAT),
        ("SCORE_WRITE", SCORE_WRITE_PAT),
        ("HARNESS_EDIT", HARNESS_EDIT_PAT),
        ("NETWORK", NETWORK_PAT),
    ):
        hits = [match.group(0)[:90] for match in pattern.finditer(text)]
        if hits:
            flags[name] = hits[:4] + (
                [f"... {len(hits)} total"] if len(hits) > 4 else [])

    event_path = traces / str(row.get("events_file", ""))
    if not event_path.exists():
        flags["TIMELINE_EDIT"] = ["exported event ledger missing"]
        return flags
    previous = -1
    try:
        with gzip.open(event_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = json.loads(line)
                index = event["i"]
                if index <= previous:
                    if index == 0 and event.get("reset"):
                        previous = index
                        continue
                    flags.setdefault("TIMELINE_EDIT", []).append(
                        f"index {index} after {previous}")
                    break
                previous = index
    except (OSError, ValueError, KeyError) as exc:
        flags.setdefault("TIMELINE_EDIT", []).append(
            f"unreadable exported ledger: {type(exc).__name__}")
    return flags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # A valid ablation runs OUTSIDE the repo tree, so the auditor has to be able
    # to reach roots that are not under ROOT.
    source = ap.add_mutually_exclusive_group()
    source.add_argument("--runs-root", action="append", default=None,
                        help="extra run root to audit (repeatable); default: every "
                             "runs*/ inside the repo")
    source.add_argument("--traces-dir",
                        help="exported dataset containing runs.jsonl, compressed "
                             "events, and agent_logs")
    args = ap.parse_args()
    bad = 0
    unaud = 0
    total = 0
    audited: list[tuple[object, object, dict]] = []
    if args.traces_dir:
        traces = Path(args.traces_dir)
        index = traces / "runs.jsonl"
        if not index.exists():
            print(f"VACUOUS: {index} is missing; no exported traces were checked.")
            return 2
        for line in index.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rel = f"{row.get('model')}/{row.get('game')}"
            audited.append((rel, row.get("score"), audit_export_row(traces, row)))
    else:
        roots = [str(ROOT / "runs*")] + [
            str(Path(root).expanduser()) for root in (args.runs_root or [])]
        paths: list[str] = []
        for root in roots:
            paths += glob.glob(str(Path(root) / "*/*/"))
        for result_path in sorted(set(paths)):
            ws = Path(result_path)
            if not (ws / "events.jsonl").exists():
                continue
            try:
                rel = ws.relative_to(ROOT)
            except ValueError:
                rel = ws
            score = None
            result_json = ws / "result.json"
            if result_json.exists():
                try:
                    score = json.loads(result_json.read_text()).get("score")
                except Exception:
                    pass
            audited.append((rel, score, audit_run(ws)))

    for rel, score, flags in audited:
        total += 1
        unauditable = set(flags) == {"NO_LOGS"}
        if flags and not unauditable:
            bad += 1
            s = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
            print(f"FLAGGED {rel}  (score {s})")
            for k, v in flags.items():
                print(f"    {k}: {v[0]}" + (f"  [+{len(v)-1} more]" if len(v) > 1 else ""))
        elif unauditable:
            unaud += 1
            s = f"{score:.2f}" if isinstance(score, (int, float)) else "running"
            print(f"NOLOGS  {rel}  (score {s}), transcripts deleted, cannot verify")
        else:
            s = f"{score:.2f}" if isinstance(score, (int, float)) else "running"
            print(f"clean   {rel}  (score {s})")
    if total == 0:
        # A green PASS that examined nothing is worse than a failure: it tells the
        # exact reader this repo is written for that everything checks out, when
        # nothing was checked. Run data is gitignored, so a fresh clone lands here.
        print("VACUOUS: no runs were found; this audit checked nothing.\n"
              "Download the trace dataset and pass --traces-dir, or run a game.")
        return 2
    print(f"\n{total - bad - unaud}/{total} runs verified clean, {bad} flagged, "
          f"{unaud} unauditable (session logs deleted)")
    return 1 if bad else (2 if unaud else 0)


if __name__ == "__main__":
    sys.exit(main())
