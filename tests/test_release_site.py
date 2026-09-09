"""Check committed site copy without downloading the private run timelines.

Run: python tests/test_release_site.py
This checks template synchronization and chart row coverage, not score validity
or reproduction of generated figures from raw observations.
"""
import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def match_template(template, rendered, names):
    pattern = re.escape(template)
    for name in names:
        marker = f"<!--{name}-->"
        if template.count(marker) != 1 or marker in rendered:
            raise ValueError(f"Missing, repeated or unresolved placeholder: {name}")
        pattern = pattern.replace(re.escape(marker), f"(?P<{name}>[\\s\\S]+?)")
    match = re.fullmatch(pattern, rendered)
    if match is None:
        raise ValueError("Committed site copy differs from its source template")
    return match.groupdict()


class ReleaseSiteTests(unittest.TestCase):
    def test_static_copy_cannot_drift(self):
        with self.assertRaises(ValueError):
            match_template("Title<!--figure-->End", "Wrong<svg/>End", ["figure"])

    def test_dynamic_figure_may_change(self):
        self.assertEqual(match_template("Title<!--figure-->End", "Title<svg/>End", ["figure"]),
                         {"figure": "<svg/>"})

    def test_empty_or_unresolved_figure_rejected(self):
        for rendered in ("TitleEnd", "Title<!--figure-->End"):
            with self.assertRaises(ValueError):
                match_template("Title<!--figure-->End", rendered, ["figure"])

    def test_committed_site_matches_source(self):
        tree = ast.parse((ROOT / "blog/build_site.py").read_text())
        build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
        figs = next(n.value for n in build.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "figs" for t in n.targets))
        names = [ast.literal_eval(k) for k in figs.keys]
        self.assertTrue(names)
        self.assertEqual(len(names), len(set(names)))
        rendered = (ROOT / "blog/site/index.html").read_text()
        groups = match_template((ROOT / "blog/template.html").read_text(), rendered, names)
        rows = json.loads(groups["interactive_data"])
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({(row["game"], row["board"]) for row in rows}), 50)
        boards = {row["board"] for row in rows}
        self.assertEqual(boards, {"Claude Opus 5", "GPT-5.6 Sol"})
        game_sets = [{row["game"] for row in rows if row["board"] == board} for board in boards]
        self.assertEqual(len(game_sets[0]), 25)
        self.assertEqual(game_sets[0], game_sets[1])


if __name__ == "__main__":
    unittest.main()
