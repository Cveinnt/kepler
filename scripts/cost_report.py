#!/usr/bin/env python3
"""Recover Kepler release usage from complete provider-side session records.

Workspace CLI footer counters are not complete accounting. In particular, the
GPT footer path omitted most cached-input traffic and one long workspace. This
script instead reads the cumulative provider record for each Codex session and
per-message Claude usage for the two frozen release boards.

The records live in provider-owned local stores and are not included in the
repository. Running this script on a machine without those stores fails closed.

Usage:
  .venv/bin/python scripts/cost_report.py --release
  .venv/bin/python scripts/cost_report.py --release --markdown
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MODEL = "claude-opus-5"
RELEASE_RUNS = ROOT / "release-runs"
OPUS_WORKSPACE = RELEASE_RUNS / "opus"
GPT_WORKSPACE = RELEASE_RUNS / "gpt-max"


@dataclass
class Usage:
    sessions: int = 0
    records: int = 0
    uncached_input: int = 0
    cached_input: int = 0
    cache_write_1h: int = 0
    cache_write_5m: int = 0
    output: int = 0

    @property
    def total(self) -> int:
        return (
            self.uncached_input
            + self.cached_input
            + self.cache_write_1h
            + self.cache_write_5m
            + self.output
        )


def _objects(path: Path) -> Iterator[dict]:
    try:
        with path.open(errors="ignore") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def claude_release_usage() -> Usage:
    projects = Path.home() / ".claude" / "projects"
    encoded = str(OPUS_WORKSPACE.resolve()).replace("/", "-").replace("_", "-")
    session_files = sorted(projects.glob(f"{encoded}-*/*.jsonl"))
    usage = Usage(sessions=len(session_files))
    for path in session_files:
        for obj in _objects(path):
            message = obj.get("message")
            if not isinstance(message, dict) or message.get("model") != CLAUDE_MODEL:
                continue
            item = message.get("usage")
            if not isinstance(item, dict):
                continue
            usage.records += 1
            usage.uncached_input += int(item.get("input_tokens", 0) or 0)
            usage.cached_input += int(item.get("cache_read_input_tokens", 0) or 0)
            cache = item.get("cache_creation") or {}
            one_hour = int(cache.get("ephemeral_1h_input_tokens", 0) or 0)
            five_min = int(cache.get("ephemeral_5m_input_tokens", 0) or 0)
            # Older records expose only the aggregate creation count.
            aggregate = int(item.get("cache_creation_input_tokens", 0) or 0)
            if not one_hour and not five_min:
                one_hour = aggregate
            usage.cache_write_1h += one_hour
            usage.cache_write_5m += five_min
            usage.output += int(item.get("output_tokens", 0) or 0)
    return usage


def codex_release_usage() -> Usage:
    sessions_root = Path.home() / ".codex" / "sessions"
    target = str(GPT_WORKSPACE.resolve()) + "/"
    usage = Usage()
    for path in sorted(sessions_root.glob("**/*.jsonl")):
        cwd = None
        last = None
        records = 0
        for obj in _objects(path):
            if obj.get("type") == "session_meta":
                payload = obj.get("payload") or {}
                cwd = payload.get("cwd")
            payload = obj.get("payload") or {}
            if obj.get("type") == "event_msg" and payload.get("type") == "token_count":
                total = (payload.get("info") or {}).get("total_token_usage")
                if isinstance(total, dict):
                    last = total
                    records += 1
        if not isinstance(cwd, str) or not (cwd + "/").startswith(target):
            continue
        if last is None:
            continue
        usage.sessions += 1
        usage.records += records
        input_tokens = int(last.get("input_tokens", 0) or 0)
        cached = int(last.get("cached_input_tokens", 0) or 0)
        usage.uncached_input += input_tokens - cached
        usage.cached_input += cached
        usage.output += int(last.get("output_tokens", 0) or 0)
    return usage


def opus_cost(u: Usage) -> float:
    return (
        u.uncached_input * 5
        + u.cached_input * 0.50
        + u.cache_write_1h * 10
        + u.cache_write_5m * 6.25
        + u.output * 25
    ) / 1_000_000


def gpt_cost(u: Usage) -> float:
    return (
        u.uncached_input * 4
        + u.cached_input * 0.40
        + u.output * 20
    ) / 1_000_000


def _validate(opus: Usage, gpt: Usage) -> None:
    if not opus.sessions or not opus.records:
        raise SystemExit(
            f"missing Claude release records under {Path.home() / '.claude/projects'}"
        )
    if not gpt.sessions or not gpt.records:
        raise SystemExit(
            f"missing Codex release records under {Path.home() / '.codex/sessions'}"
        )
    if opus.cache_write_5m:
        raise SystemExit(
            "unexpected five-minute Opus cache writes; update the published pricing split"
        )


def _markdown(opus: Usage, gpt: Usage) -> None:
    print("| board | sessions | usage records | uncached input | cached/read input | cache write | output | raw total | list-equivalent |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    print(
        f"| Claude Opus 5, 100.00 | {opus.sessions} | {opus.records:,} | "
        f"{opus.uncached_input:,} | {opus.cached_input:,} | "
        f"{opus.cache_write_1h:,} | {opus.output:,} | {opus.total:,} | "
        f"${opus_cost(opus):,.2f} |"
    )
    print(
        f"| GPT-5.6 Sol, 95.97 | {gpt.sessions} | {gpt.records:,} | "
        f"{gpt.uncached_input:,} | {gpt.cached_input:,} | 0 | "
        f"{gpt.output:,} | {gpt.total:,} | ${gpt_cost(gpt):,.2f} |"
    )


def _plain(opus: Usage, gpt: Usage) -> None:
    print("Kepler 1.0 provider-record resource accounting")
    print()
    for label, usage, cost in (
        ("Claude Opus 5, 100.00", opus, opus_cost(opus)),
        ("GPT-5.6 Sol, 95.97", gpt, gpt_cost(gpt)),
    ):
        print(label)
        print(f"  sessions:        {usage.sessions:,}")
        print(f"  usage records:   {usage.records:,}")
        print(f"  uncached input:  {usage.uncached_input:,}")
        print(f"  cached input:    {usage.cached_input:,}")
        if usage.cache_write_1h:
            print(f"  cache write 1h:  {usage.cache_write_1h:,}")
        print(f"  output:          {usage.output:,}")
        print(f"  raw total:       {usage.total:,}")
        print(f"  list-equivalent: ${cost:,.2f}")
        print()
    print("Pricing basis, 2026-09-01:")
    print("  Opus 5: $5/M uncached input, $0.50/M cache read, $10/M 1h cache write, $25/M output")
    print("  GPT-5.6 Sol: $4/M uncached input, $0.40/M cached input, $20/M output")
    print("Actual execution used subscription quota; dollar values are API list-equivalent.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release",
        action="store_true",
        help="recover the two frozen Kepler 1.0 boards (default behavior)",
    )
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    opus = claude_release_usage()
    gpt = codex_release_usage()
    _validate(opus, gpt)
    if args.markdown:
        _markdown(opus, gpt)
    else:
        _plain(opus, gpt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
