#!/usr/bin/env python3
"""Fail closed when Kepler's public release identity or claims drift."""

from __future__ import annotations

import json
import base64
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
    "One frozen setup, 100.00 on 25 public games, $777.72 API-equivalent release cost. "
    "Inspect the agent-written simulators and the winning traces."
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
        self.headings: list[str] = []
        self.in_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "h1":
            self.headings.append("")
            self.in_heading = True
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href", "").startswith("#"):
            self.fragments.add(values["href"][1:])
        if tag == "img":
            self.images.append(values)
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href", ""))

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.headings[-1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self.in_heading = False


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
assert parse_page(project_page).headings == [HOOK]
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

assert parse_page(generated_page).headings == [HOOK]
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

# These regressions previously overstated discovery speed, information loss,
# and the resource denominator. Test the claim, not the layout or prose order.
for path, text in {
    "README.md": readme,
    "blog/template.html": project_page,
    "blog/site/index.html": generated_page,
    "docs/paper/latex/main.tex": paper,
}.items():
    for stale_claim in (
        "Nineteen sessions of correct proofs",
        "Fifty-seven\n      actions later",
        "find the\nrule in 57 actions",
        "actions (learning included)",
        "current API list-equivalent",
        "current standard API",
        "current Opus 5 API",
        "zero-prior CI",
        "enforce zero game-specific",
        "contain zero game-specific information",
        "score and a stricter integrity record",
        "We conclude only that transient visual evidence was necessary",
    ):
        assert stale_claim not in text, f"{path}: restored unsupported claim {stale_claim!r}"
    assert "September 1, 2026" in text, f"{path}: missing fixed pricing basis"

assert 'id="see"' in project_page
assert '<!--sp80_frames-->' in project_page
assert '<!--sp80_frames-->' not in generated_page
for frame_name in ("sp80-start.png", "sp80-deflection.png", "sp80-filled.png"):
    frame = (ROOT / "docs/paper/latex/figures" / frame_name).read_bytes()
    uri = "data:image/png;base64," + base64.b64encode(frame).decode()
    assert any(image.get("src") == uri for image in generated_contract.images), (
        f"project case figure no longer matches retained artifact {frame_name}"
    )
assert "development event 8324" in paper
assert "not simulator predictions" in paper

launch_surfaces = {
    "README.md": readme,
    "release.json": read("release.json"),
    "CITATION.cff": citation,
    "docs/paper/latex/main.tex": paper,
    "docs/release-comparison.md": read("docs/release-comparison.md"),
    "docs/benchmark-observations.md": read("docs/benchmark-observations.md"),
    "docs/research-followups.md": read("docs/research-followups.md"),
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
