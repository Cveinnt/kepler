#!/usr/bin/env python3
"""Regression checks for provider-message cost accounting."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cost_report  # noqa: E402


def row(message_id: str, block_type: str, output: int = 13) -> dict:
    return {
        "message": {
            "id": message_id,
            "model": "claude-opus-5",
            "content": [{"type": block_type}],
            "usage": {
                "input_tokens": 2,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 20,
                "cache_creation": {
                    "ephemeral_1h_input_tokens": 20,
                    "ephemeral_5m_input_tokens": 0,
                },
                "output_tokens": output,
            },
        }
    }


with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "session.jsonl"
    records = [
        row("msg_1", "thinking"),
        row("msg_1", "tool_use"),
        row("msg_1", "text"),
        row("msg_2", "text"),
    ]
    path.write_text("".join(json.dumps(item) + "\n" for item in records))
    usage = cost_report._claude_release_usage_from_files([path])

    assert usage.sessions == 1
    assert usage.records == 2
    assert usage.uncached_input == 4
    assert usage.cached_input == 200
    assert usage.cache_write_1h == 40
    assert usage.output == 26

    path.write_text(
        json.dumps(row("msg_conflict", "thinking", output=13))
        + "\n"
        + json.dumps(row("msg_conflict", "text", output=14))
        + "\n"
    )
    try:
        cost_report._claude_release_usage_from_files([path])
    except SystemExit as exc:
        assert "conflicting cumulative usage" in str(exc)
    else:
        raise AssertionError("conflicting duplicate usage must fail closed")

print("PASS: Claude transcript blocks are billed once per provider message ID.")
