#!/usr/bin/env python3
"""Package the already-compiled public PDF and a crawlable citation page.

No models, game execution, uploads, or private submission files. Run after
compiling docs/paper/latex/main.tex. Only referenced public figures are archived.
"""
from pathlib import Path
import hashlib
import html
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/paper/latex"
SITE = ROOT / "blog/site"
PAPER = SITE / "paper"
PAPER.mkdir(parents=True, exist_ok=True)
tex = (SOURCE / "main.tex").read_text()
abstract = tex.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0].strip()
abstract = abstract.replace(r"\%", "%").replace(r"\$", "$").replace("--", "-")
assert "\\" not in abstract, "Add an explicit plain-text rendering for new TeX commands"
title = "Kepler: Auditable World Models for ARC-AGI-3"
bib = (ROOT / "docs/paper/kepler.bib").read_text()
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Wensen Wu</title>
<link rel="canonical" href="https://kepler-harness.vercel.app/paper/">
<meta name="citation_title" content="{title}">
<meta name="citation_author" content="Wensen Wu">
<meta name="citation_publication_date" content="2026/09/01">
<meta name="citation_pdf_url" content="https://kepler-harness.vercel.app/paper/kepler.pdf">
<meta name="description" content="Executable world models, replay evidence, and documented evaluation failures. Public technical report by Wensen Wu.">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="Executable world models, replay evidence, and documented evaluation failures. Public technical report by Wensen Wu.">
<meta property="og:url" content="https://kepler-harness.vercel.app/paper/">
<meta property="og:image" content="https://kepler-harness.vercel.app/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="Executable world models, replay evidence, and documented evaluation failures. Public technical report by Wensen Wu.">
<meta name="twitter:image" content="https://kepler-harness.vercel.app/og.png">
<style>body{{max-width:820px;margin:3rem auto;padding:0 1.25rem;font:18px/1.65 system-ui;color:#222;background:#faf9f6}}h1{{font:600 2.3rem/1.15 Georgia,serif}}a{{color:#164d83}}nav{{display:flex;flex-wrap:wrap;gap:1rem}}pre{{padding:1rem;background:#eee;white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}}.meta{{color:#555}}h2{{margin-top:2rem}}</style>
</head><body>
<nav><a href="/">Project</a><a href="https://www.wensenwu.com/thoughts/kepler">Engineering essay</a><a href="https://github.com/Cveinnt/kepler">Code</a></nav>
<h1>{title}</h1><p>Wensen Wu · Independent Researcher</p>
<p class="meta">Public technical report, September 1, 2026. Revised September 30, 2026.</p>
<h2>Abstract</h2><p>{html.escape(abstract)}</p>
<nav><a href="kepler.pdf">Download paper (PDF)</a><a href="kepler-latex.zip">LaTeX source</a><a href="kepler.bib">BibTeX</a><a href="https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces">50-run trace corpus</a></nav>
<h2>Scope and revision</h2>
<p>Accepted to the non-archival Interpreting Agent Behavior workshop at NeurIPS 2026, not the main conference. This public revision is not a camera-ready submission receipt. Presentation format is not confirmed.</p>
<p>Our replay scores concern the public development set, not official first-exposure evaluation. ARC Prize imposes a five-times-human-baseline per-level evaluation budget; our earlier denial was incorrect. Conditional checks do not guarantee verified execution on every action. No new performance or causal reliability result is claimed.</p>
<p><a href="https://github.com/Cveinnt/kepler/blob/main/docs/evidence-boundaries.md">Failure taxonomy, implementation limits, and reproduction scope</a> · <a href="https://github.com/Cveinnt/kepler/blob/main/docs/resource-comparison.md">Resource accounting</a> · <a href="https://github.com/Cveinnt/kepler/blob/main/docs/research-followups.md">Exploratory negative result</a></p>
<h2>Cite the paper</h2><pre>{html.escape(bib)}</pre>
<p>Specify the software commit and dataset revision when reusing artifacts. No arXiv identifier or Scholar indexing is claimed.</p>
<p><a href="https://www.wensenwu.com/">Author homepage</a> · <a href="https://scholar.google.com/citations?user=9MXpr74AAAAJ&amp;hl=en">Existing author Scholar profile</a></p>
</body></html>'''
(PAPER / "index.html").write_text(page)
shutil.copy2(SOURCE / "main.pdf", PAPER / "kepler.pdf")
shutil.copy2(SOURCE / "main.pdf", SITE / "paper.pdf")
shutil.copy2(ROOT / "docs/paper/kepler.bib", PAPER / "kepler.bib")
figures = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
members = ["main.tex", "references.bib", *figures]
assert len(members) == len(set(members))
archive = ROOT / "docs/paper/kepler-latex-overleaf.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
    for name in members:
        assert ".." not in Path(name).parts
        out.write(SOURCE / name, name)
shutil.copy2(archive, PAPER / "kepler-latex.zip")
print("Packaged", len(members), "public source members")
print("PDF SHA256", hashlib.sha256((PAPER / "kepler.pdf").read_bytes()).hexdigest())
