"""Offline publication contract: metadata, source bundle, and served PDF identity."""
from pathlib import Path
import re
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PublicPaperTests(unittest.TestCase):
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
        self.assertIn('href="/paper/"', (ROOT / "blog/site/index.html").read_text())

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
