"""Offline publication contract: metadata, source bundle, and served PDF identity."""
from pathlib import Path
import html
import re
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PublicPaperTests(unittest.TestCase):
    def test_arxiv_citation_consistency(self):
        bib = (ROOT / "docs/paper/kepler.bib").read_text()
        self.assertEqual(bib, (ROOT / "blog/site/paper/kepler.bib").read_text())
        for field in ("eprint = {2610.00834}", "archivePrefix = {arXiv}",
                      "primaryClass = {cs.AI}", "url = {https://arxiv.org/abs/2610.00834}"):
            self.assertIn(field, bib)
        page = (ROOT / "blog/site/paper/index.html").read_text()
        self.assertIn(html.escape(bib), page)
        for path in ("blog/site/paper/index.html", "scripts/package_public_paper.py"):
            text = (ROOT / path).read_text()
            self.assertIn('href="https://arxiv.org/abs/2610.00834"', text)
            self.assertIn("v1 submitted September 30, 2026", text)
            self.assertIn("Scholar indexing is not verified", text)
            self.assertNotIn("No arXiv identifier", text)
        citation = (ROOT / "CITATION.cff").read_text().split("preferred-citation:", 1)[1]
        self.assertIn('url: "https://arxiv.org/abs/2610.00834"', citation)

    def test_pdf_identity(self):
        pdf = (ROOT / "docs/paper/latex/main.pdf").read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertLess(len(pdf), 5_000_000)
        for path in ("blog/site/paper.pdf", "blog/site/paper/kepler.pdf"):
            self.assertEqual(pdf, (ROOT / path).read_bytes())

    def test_metadata_and_scope(self):
        page = (ROOT / "blog/site/paper/index.html").read_text()
        for value in (
            'name="citation_title" content="Kepler: Auditable World Models for ARC-AGI-3"',
            'name="citation_author" content="Wensen Wu"',
            'name="citation_publication_date" content="2026/09/01"',
            'name="citation_pdf_url" content="https://kepler-harness.vercel.app/paper/kepler.pdf"',
            "<h2>Abstract</h2>", "not official first-exposure", "non-archival",
        ):
            self.assertIn(value, page)
        home = (ROOT / "blog/site/index.html").read_text()
        self.assertIn('href="/paper/"', home)
        self.assertIn('name="citation_pdf_url" content="https://kepler-harness.vercel.app/paper/kepler.pdf"', home)
        self.assertNotIn("releases/download/v1.0.0/kepler-1.0-paper.pdf", home)
        for text in (page, home, (ROOT / "blog/template.html").read_text()):
            self.assertIn('href="https://arxiv.org/abs/2610.00834"', text)
            self.assertIn('href="https://iab-agents.github.io/accepted-papers/"', text)
            self.assertIn('href="https://www.wensenwu.com/about">Vincent Wu</a>', text)
            self.assertIn('name="citation_author" content="Wensen Wu"', text)

    def test_bundle_is_exact_public_source(self):
        source = ROOT / "docs/paper/latex"
        tex = (source / "main.tex").read_text()
        expected = {"main.tex", "references.bib", *re.findall(
            r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)}
        with zipfile.ZipFile(ROOT / "docs/paper/kepler-latex-overleaf.zip") as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(set(bundle.namelist()), expected)
            for name in expected:
                self.assertEqual(bundle.read(name), (source / name).read_bytes())

    def test_protocol_regression(self):
        paper = (ROOT / "docs/paper/latex/main.tex").read_text()
        self.assertIn("explicitly imposes that per-level action budget", paper)
        self.assertNotIn("5$\\times$ is a score floor, not a wall", paper)
        self.assertNotIn("repairs can only fail closed", paper)
        self.assertIn("Private provider records", (ROOT / "CITATION.cff").read_text())


if __name__ == "__main__":
    unittest.main()
