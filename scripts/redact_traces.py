#!/usr/bin/env python3
"""Redact operator-identifying strings from an exported trace corpus. Stdlib only.

Reads an export produced by scripts/export_traces.py and writes a redacted copy
to a new directory. Source logs and run directories are never opened for write.

What it removes, and why it matters:

  1. The absolute workspace prefix. Every recorded CLI session banner carries
     `workdir: <repo path>`, so the corpus embeds the operator's macOS account
     name tens of thousands of times. The same string also embeds a private
     local checkout name that must not appear in published Kepler material.
  2. Any residual home path, plus the bare account name, which also shows up as
     the owner column of `ls -la` output.
  3. Per-user scratch directory names.

Order matters: the longest, most specific pattern is applied first so the
generic rules only see what the specific ones left behind.

Usage:
  python3 scripts/redact_traces.py --in traces --out traces-redacted
  python3 scripts/redact_traces.py --in traces --out traces-redacted --verify-only

After redacting, always re-run both verifiers against the OUTPUT directory and
confirm the audit still returns the same clean/flagged counts as the input. The
integrity audit matches within fixed-width character windows, so a length change
in a path prefix can in principle move a match across a window boundary. This
script does not assume it cannot; it is on the caller to check.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_ACCOUNT = Path.home().name.encode()
LOCAL_CHECKOUT = ROOT.name.encode()

# (name, pattern, replacement). Applied in this order to raw bytes.
RULES: list[tuple[str, re.Pattern[bytes], bytes]] = [
    ("workspace_prefix", re.compile(rb"/Users/[A-Za-z0-9._-]+/GitHub/[A-Za-z0-9._-]+"), b"/workspace"),
    ("home_path",        re.compile(rb"/Users/[A-Za-z0-9._-]+"),               b"/home/user"),
    ("scratch_dir",      re.compile(rb"/private/tmp/claude-\d+"),              b"/private/tmp/scratch"),
    ("account_name",     re.compile(rb"(?i)\b" + re.escape(LOCAL_ACCOUNT) + rb"\b"), b"user"),
    ("checkout_path",    re.compile(rb"(?i)([/\\])" + re.escape(LOCAL_CHECKOUT) + rb"\b"), rb"\1project"),
    ("checkout_name",    re.compile(rb"\b" + re.escape(LOCAL_CHECKOUT.title()) + rb"\b"), b"Project"),
    # Internal run-generation directory labels. These appear in the agent's own
    # git diff headers ("diff --git a/runs-v6/gpt-max/ar25/notes.md"), so the
    # corpus would otherwise publish the internal version ladder hundreds of
    # thousands of times, and would reveal that the two release boards were
    # produced from different internal generations. The exporter already
    # relabels the boards to release-opus / release-gpt for exactly this
    # reason; this keeps the log text consistent with that contract. Only the
    # generation segment is replaced, so model/game structure is preserved.
    ("run_generation",   re.compile(rb"runs-v\d+[a-z0-9-]*"),                    b"board"),
]

# Nothing matching these may survive in the output.
RESIDUAL: list[tuple[str, re.Pattern[bytes]]] = [
    ("home_path",     re.compile(rb"/Users/")),
    ("account_name",  re.compile(rb"(?i)\b" + re.escape(LOCAL_ACCOUNT) + rb"\b")),
    # Match the local checkout name only as a proper noun or path component.
    # A lowercase technical noun can appear legitimately in dataset docs.
    ("checkout_name", re.compile(
        rb"[/\\]" + re.escape(LOCAL_CHECKOUT) + rb"\b|\b" +
        re.escape(LOCAL_CHECKOUT.title()) + rb"\b"
    )),
    ("scratch_dir",   re.compile(rb"/private/tmp/claude-\d+")),
    ("run_generation", re.compile(rb"runs-v\d+")),
]


def redact(buf: bytes, counts: dict[str, int]) -> bytes:
    for name, pat, repl in RULES:
        buf, n = pat.subn(repl, buf)
        counts[name] = counts.get(name, 0) + n
    return buf


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def process(src: Path, dst: Path, counts: dict[str, int], stats: dict[str, int]) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".gz":
        with gzip.open(src, "rb") as fi:
            data = fi.read()
        stats["bytes_in"] += len(data)
        out = redact(data, counts)
        stats["bytes_out"] += len(out)
        with gzip.open(dst, "wb") as fo:
            fo.write(out)
    elif src.suffix in (
        ".jsonl", ".md", ".json", ".txt", ".csv", ".py", ".toml", ".yaml", ".yml"
    ):
        data = src.read_bytes()
        stats["bytes_in"] += len(data)
        out = redact(data, counts)
        stats["bytes_out"] += len(out)
        dst.write_bytes(out)
    else:
        shutil.copy2(src, dst)
        stats["copied_verbatim"] += 1
    stats["files"] += 1


def scan_residual(root: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for p in iter_files(root):
        if p.suffix == ".gz":
            try:
                data = gzip.open(p, "rb").read()
            except OSError:
                continue
        elif p.suffix in (
            ".jsonl", ".md", ".json", ".txt", ".csv", ".py", ".toml", ".yaml", ".yml"
        ):
            data = p.read_bytes()
        else:
            continue
        for name, pat in RESIDUAL:
            n = len(pat.findall(data))
            if n:
                found[name] = found.get(name, 0) + n
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--verify-only", action="store_true",
                    help="scan --in for residual identifiers and exit")
    args = ap.parse_args()

    src = Path(args.src)
    if not (src / "runs.jsonl").exists():
        sys.exit(f"{src} does not look like an export (runs.jsonl missing)")

    if args.verify_only:
        found = scan_residual(src)
        print(json.dumps({"scanned": str(src), "residual": found}, indent=2))
        sys.exit(1 if found else 0)

    dst = Path(args.dst)
    if dst.exists():
        sys.exit(f"{dst} already exists, refusing to overwrite")

    counts: dict[str, int] = {}
    stats = {"files": 0, "bytes_in": 0, "bytes_out": 0, "copied_verbatim": 0}
    for p in iter_files(src):
        process(p, dst / p.relative_to(src), counts, stats)

    print(f"files processed      : {stats['files']}")
    print(f"copied verbatim      : {stats['copied_verbatim']}")
    print(f"bytes in / out       : {stats['bytes_in']:,} / {stats['bytes_out']:,}")
    print("replacements:")
    for name, _, _ in RULES:
        print(f"  {name:18s} {counts.get(name, 0):,}")

    found = scan_residual(dst)
    if found:
        print("\nRESIDUAL IDENTIFIERS REMAIN, output is NOT publishable:")
        for k, v in sorted(found.items()):
            print(f"  {k:18s} {v:,}")
        sys.exit(2)
    print("\nresidual scan: clean (no home paths, account name, "
          "local checkout name, or scratch dirs)")


if __name__ == "__main__":
    main()
