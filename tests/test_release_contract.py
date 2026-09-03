#!/usr/bin/env python3
"""Fail closed when Kepler's public release identity or claims drift."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
TITLE = "Kepler: Auditable World Models for ARC-AGI-3"
HOOK = "100% on ARC-AGI-3 at one-fourth the cost."


def read(path: str) -> str:
    return (ROOT / path).read_text()


release = json.loads(read("release.json"))
project = tomllib.loads(read("pyproject.toml"))
readme = read("README.md")
citation = read("CITATION.cff")
paper = read("docs/paper/latex/main.tex")
project_page = read("blog/template.html")

assert release["name"] == "Kepler"
assert release["version"] == VERSION
assert release["paper_title"] == TITLE
assert release["public_set_only"] is True
assert release["opus"]["score"] == 100.0
assert release["opus"]["games_at_100"] == 25
assert release["opus"]["resource_accounting"]["list_equivalent_usd"] == 777.72
assert release["comparisons"]["tycho_cost_usd_retrodict_estimate"] == 2986

assert project["project"]["version"] == VERSION
assert project["project"]["dependencies"] == [
    "arc-agi==0.9.9",
    "arcengine==0.9.3",
]
assert f'version: "{VERSION}"' in citation
assert 'title: "Kepler"' in citation
assert HOOK in readme
assert "Kepler 1.0" in readme
assert f"\\title{{{TITLE}}}" in paper
assert "\\author{Wensen Wu" in paper
assert f'<h1>{HOOK}</h1>' in project_page
assert f'<meta name="citation_title" content="{TITLE}">' in project_page

launch_surfaces = {
    "README.md": readme,
    "release.json": read("release.json"),
    "CITATION.cff": citation,
    "docs/paper/latex/main.tex": paper,
    "docs/release-comparison.md": read("docs/release-comparison.md"),
    "docs/benchmark-observations.md": read("docs/benchmark-observations.md"),
    "blog/template.html": project_page,
}
for path, text in launch_surfaces.items():
    for forbidden in ("V7", "V8", "1/30", "1/35", "under review at", "Submitted to ICLR"):
        assert forbidden.lower() not in text.lower(), f"{path}: contains {forbidden!r}"
    assert "\N{EM DASH}" not in text, f"{path}: contains an em dash"

tracked_submissions = subprocess.check_output(
    ["git", "ls-files", "--", "docs/paper/submissions"],
    cwd=ROOT,
    text=True,
).strip()
assert not tracked_submissions, (
    "venue-specific submission files must remain private: " + tracked_submissions
)

print("PASS: one public release identity, scoped claims, pinned engine, private venue files.")
