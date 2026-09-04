#!/usr/bin/env python3
"""Fail closed when Kepler's public release identity or claims drift."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
TITLE = "Kepler: Auditable World Models for ARC-AGI-3"
HOOK = "100% on ARC-AGI-3 at one-fourth the cost."
PREVIEW_DESCRIPTION = (
    "Open-source agent harness with one frozen configuration, exact server replay, "
    "$777.72 list-equivalent cost, and audits that voided its own best-looking results."
)


def read(path: str) -> str:
    return (ROOT / path).read_text()


class PageContract(HTMLParser):
    """Collect structural checks without adding an HTML-parser dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.fragments: set[str] = set()
        self.images: list[dict[str, str]] = []
        self.canonicals: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href", "").startswith("#"):
            self.fragments.add(values["href"][1:])
        if tag == "img":
            self.images.append(values)
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href", ""))


def parse_page(text: str) -> PageContract:
    page = PageContract()
    page.feed(text)
    return page


release = json.loads(read("release.json"))
project = tomllib.loads(read("pyproject.toml"))
readme = read("README.md")
citation = read("CITATION.cff")
paper = read("docs/paper/latex/main.tex")
project_page = read("blog/template.html")
generated_page = read("blog/site/index.html")
dataset_card_source = read("scripts/export_traces.py")

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
assert len(PREVIEW_DESCRIPTION) <= 160
assert project_page.count(f'content="{PREVIEW_DESCRIPTION}"') == 3

for path, text in {
    "blog/template.html": project_page,
    "blog/site/index.html": generated_page,
}.items():
    page = parse_page(text)
    assert page.canonicals == ["https://kepler-harness.vercel.app/"], (
        f"{path}: canonical URL drifted"
    )
    assert not page.fragments - page.ids, (
        f"{path}: broken internal links: {sorted(page.fragments - page.ids)}"
    )

assert generated_page.count(f'<h1>{HOOK}</h1>') == 1
assert f'<meta name="citation_title" content="{TITLE}">' in generated_page
assert generated_page.count(f'content="{PREVIEW_DESCRIPTION}"') == 3
for url in (
    "https://kepler-harness.vercel.app/",
    "https://github.com/Cveinnt/kepler",
    "https://github.com/Cveinnt/kepler/releases/download/v1.0.0/kepler-1.0-paper.pdf",
    "https://github.com/Cveinnt/kepler/blob/main/INTEGRITY.md",
):
    assert url in dataset_card_source, f"dataset card source: missing {url}"
generated_contract = parse_page(generated_page)
assert generated_contract.images, "blog/site/index.html: expected generated evidence images"
for image in generated_contract.images:
    assert image.get("alt"), "blog/site/index.html: image is missing alt text"
    assert image.get("width") and image.get("height"), (
        "blog/site/index.html: image is missing intrinsic dimensions"
    )

launch_surfaces = {
    "README.md": readme,
    "release.json": read("release.json"),
    "CITATION.cff": citation,
    "docs/paper/latex/main.tex": paper,
    "docs/release-comparison.md": read("docs/release-comparison.md"),
    "docs/benchmark-observations.md": read("docs/benchmark-observations.md"),
    "blog/template.html": project_page,
    "blog/site/index.html": generated_page,
    "scripts/export_traces.py": dataset_card_source,
}
for path, text in launch_surfaces.items():
    claim_text = re.sub(r'data:image/[^"\']+', "", text)
    for forbidden in (
        "V7", "V8", "1/30", "1/35", "under review at", "Submitted to ICLR",
        "176-line", "508 lines", "2,753 lines",
    ):
        assert forbidden.lower() not in claim_text.lower(), f"{path}: contains {forbidden!r}"
    assert "\N{EM DASH}" not in claim_text, f"{path}: contains an em dash"

tracked_submissions = subprocess.check_output(
    ["git", "ls-files", "--", "docs/paper/submissions"],
    cwd=ROOT,
    text=True,
).strip()
assert not tracked_submissions, (
    "venue-specific submission files must remain private: " + tracked_submissions
)

print("PASS: one public release identity, scoped claims, pinned engine, private venue files.")
