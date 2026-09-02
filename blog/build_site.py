#!/usr/bin/env python3
"""Build blog/site/index.html, the Kepler release page.

Every figure is generated from the recorded runs or the numbers registered in
RESULTS.md. The hero wall is real 64x64 environment observations lifted out of
<runs>/<model>/<game>/events.jsonl and rendered with the ARC-AGI-3 palette; the
convergence strip reads the release boards' result.json files directly; the ladder
and cost figures carry the audited composites from RESULTS.md. Nothing is
illustrative: if a figure shows a grid, that grid was observed, and if it shows
a number, that number is in the ledger.

Layout/copy live in blog/template.html; this file only produces the figures.

Usage:  python3 blog/build_site.py
"""

from __future__ import annotations

import base64
import glob
import io
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "blog" / "site"

# Exact release boards, exposed through one neutral local evidence root.
FINAL_BOARDS = (
    ("release-runs", "opus", "Claude Opus 5"),
    ("release-runs", "gpt-max", "GPT-5.6 Sol"),
)

PALETTE = [
    "#FFFFFF", "#CCCCCC", "#999999", "#666666", "#333333", "#000000",
    "#E53AA3", "#FF7BCC", "#F93C31", "#1E93FF", "#88D8F1", "#FFDC00",
    "#FF851B", "#921231", "#4FCC30", "#A356D6",
]
RGB = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in PALETTE]


def frame_png(grid) -> str:
    """One observed grid -> base64 PNG at native 64x64 (CSS upscales it)."""
    h, w = len(grid), len(grid[0])
    img = Image.new("RGB", (w, h))
    img.putdata([RGB[v % 16] for row in grid for v in row])
    img = img.convert("P", palette=Image.ADAPTIVE, colors=16)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def winning_runs() -> list[Path]:
    out = []
    for root, model, _ in FINAL_BOARDS:
        for p in sorted(glob.glob(str(ROOT / root / model / "*/events.jsonl"))):
            ws = Path(p).parent
            if "superseded" in ws.parts:
                continue
            rj = ws / "result.json"
            if not rj.exists():
                continue
            try:
                if json.loads(rj.read_text()).get("score", 0) >= 100:
                    out.append(ws)
            except Exception:
                pass
    return out


# ───────────────────────────── figures ─────────────────────────────

def hero_wall(limit: int = 96) -> str:
    """A band of real observations sampled across every run that scored 100.

    This sits under the hero because it is the one image nobody else could
    make: our actual evidence, not an illustration of it. The CSS shows the
    tiles at 48/32/24/16 per row. Every count divides 96, so there is never
    a ragged last row.
    """
    ups_by_run: list[tuple[str, list]] = []
    for ws in winning_runs():
        ev = [json.loads(l) for l in (ws / "events.jsonl").read_text().splitlines()
              if l.strip()]
        ups = [e["grid"] for e in ev if e.get("level_up") and e.get("grid")]
        if ups:
            ups_by_run.append((ws.name, ups))
    tiles: list[tuple[str, list]] = []
    depth = 0
    while len(tiles) < limit and depth <= 12:
        for name, ups in ups_by_run:
            if len(tiles) >= limit:
                break
            if depth < len(ups):
                tiles.append((name, ups[depth]))
        depth += 1
    cells = "".join(
        f'<img src="{frame_png(g)}" alt="observed frame from {name}" loading="lazy" '
        f'width="64" height="64">' for name, g in tiles)
    return (f'<div class="wall" role="img" aria-label="{len(tiles)} real observed '
            f'frames from winning runs">{cells}</div>')




def interactive_data() -> str:
    """Per-game data for the interactive explorer: the two FINAL boards."""
    import json as _json
    rows = []
    for root, model, label in FINAL_BOARDS:
        for rj in sorted((ROOT / root / model).glob("*/result.json")):
            d = _json.loads(rj.read_text())
            rows.append({
                "game": rj.parent.name, "board": label,
                "score": round(d.get("score", 0), 2),
                "actions": d.get("actions", 0),
                "levels": f"{d.get('levels_completed','?')}/{d.get('win_levels','?')}",
                "scored_actions": sum(d.get("level_actions", []) or []),
            })
    return _json.dumps(rows)

def plot_ladder(w=940, h=340) -> str:
    """Figure (a): the named-stage ablation ladder as a stepped line.

    Composites are the audited single-config Claude Opus boards registered in
    RESULTS.md (each harness frozen by commit hash before its board existed).
    The discipline dip is the regression we published rather than buried.
    """
    rows = [
        ("initial", "base loop + guarded channel", 97.78),
        ("discipline", "uniform discipline added", 94.01),
        ("guards", "guards demoted to warnings", 96.51),
        ("certify/replay", "mechanical scored attempts", 98.86),
    ]
    lo, hi = 92.0, 100.0
    x0, x1, y0, y1 = 64, w - 30, 46, h - 84
    pad = 30
    seg = (x1 - x0) / len(rows)

    def yp(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Ablation ladder: initial loop 97.78, added discipline '
         f'94.01, guard corrections 96.51, certify and replay 98.86">']
    for gv in (92, 94, 96, 98, 100):
        y = yp(gv)
        cls = "grid strong" if gv == 100 else "grid"
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="{cls}"/>')
        s.append(f'<text x="{x0-10}" y="{y+4:.1f}" class="tick" text-anchor="end">{gv}</text>')

    spans = []
    for i, (_, _, v) in enumerate(rows):
        xs = x0 + i * seg + pad
        xe = x0 + (i + 1) * seg - pad
        spans.append((xs, xe, yp(v)))

    d = [f'M {spans[0][0]:.1f} {spans[0][2]:.1f} H {spans[0][1]:.1f}']
    for (xs_a, xe_a, y_a), (xs_b, xe_b, y_b) in zip(spans, spans[1:]):
        xm = (xe_a + xs_b) / 2
        d.append(f'H {xm:.1f} V {y_b:.1f} H {xe_b:.1f}')
    s.append(f'<path d="{" ".join(d)}" class="step"/>')
    # the discipline plateau restated in the flag colour: regression, not hidden
    s.append(f'<line x1="{spans[1][0]:.1f}" y1="{spans[1][2]:.1f}" '
             f'x2="{spans[1][1]:.1f}" y2="{spans[1][2]:.1f}" class="step flag"/>')

    for i, ((tag, note, v), (xs, xe, y)) in enumerate(zip(rows, spans)):
        xm = (xs + xe) / 2
        dot = "dot flag" if i == 1 else "dot"
        s.append(f'<circle cx="{xm:.1f}" cy="{y:.1f}" r="5" class="{dot}"/>')
        vy = y + 24 if i == 1 else y - 12
        s.append(f'<text x="{xm:.1f}" y="{vy:.1f}" class="val" '
                 f'text-anchor="middle">{v:.2f}</text>')
        s.append(f'<text x="{xm:.1f}" y="{h-44}" class="lbl" '
                 f'text-anchor="middle">{tag}</text>')
        s.append(f'<text x="{xm:.1f}" y="{h-26}" class="lbl faint" '
                 f'text-anchor="middle">{note}</text>')
    # annotate the dip
    xm2 = (spans[1][0] + spans[1][1]) / 2
    s.append(f'<text x="{xm2:.1f}" y="{spans[1][2]+44:.1f}" class="lbl flag" '
             f'text-anchor="middle">the regression we published</text>')
    s.append(f'<text x="{x0}" y="20" class="tick">RHAE composite · Claude Opus · '
             f'single configuration · all 25 public games</text>')
    s.append("</svg>")
    return "".join(s)


def plot_convergence(w=940) -> str:
    """Figure (c): the two release boards as a 25x2 strip, read from result.json.

    Solid accent cells scored exactly 100.0; the exceptions carry their score.
    The counts are asserted so this figure cannot drift from the data.
    """
    scores: dict[str, dict[str, float]] = {}
    for root, model, _ in FINAL_BOARDS:
        for rj in sorted(glob.glob(str(ROOT / root / model / "*/result.json"))):
            ws = Path(rj).parent
            if "superseded" in ws.parts:
                continue
            scores.setdefault(model, {})[ws.name] = json.loads(
                Path(rj).read_text())["score"]
    games = sorted(scores[FINAL_BOARDS[0][1]])
    assert len(games) == 25, f"expected 25 games, found {len(games)}"
    full = sum(1 for _, m, _ in FINAL_BOARDS for g in games if scores[m][g] >= 99.995)
    miss = 50 - full
    assert (full, miss) == (48, 2), \
        f"convergence drifted from RESULTS.md: {full} at 100, {miss} below"

    x0, cw, gap, ch = 118, 30, 2.8, 30
    rows_y = (40, 40 + ch + 8)
    h = int(rows_y[1] + ch + 58)
    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Per-game release scores for both models: {full} of 50 cells '
         f'at 100.0, {miss} exceptions labeled">']
    s.append(f'<text x="{x0}" y="20" class="tick">Kepler release boards · frozen per model · '
             f'score per game, solid = 100.0</text>')
    for (_, model, label), y in zip(FINAL_BOARDS, rows_y):
        comp = "100.00" if model == "opus" else "95.97"
        s.append(f'<text x="{x0-12}" y="{y+13:.1f}" class="lbl" '
                 f'text-anchor="end">{label}</text>')
        s.append(f'<text x="{x0-12}" y="{y+27:.1f}" class="tick" '
                 f'text-anchor="end">{comp}</text>')
        for i, g in enumerate(games):
            x = x0 + i * (cw + gap)
            v = scores[model][g]
            if v >= 99.995:
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{cw}" height="{ch}" '
                         f'rx="3" class="cell"/>')
            else:
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{cw}" height="{ch}" '
                         f'rx="3" class="cell miss"/>')
                s.append(f'<text x="{x+cw/2:.1f}" y="{y+ch/2+3.5:.1f}" '
                         f'class="val on" text-anchor="middle">{v:.1f}</text>')
    ly = rows_y[1] + ch + 12
    for i, g in enumerate(games):
        x = x0 + i * (cw + gap) + cw / 2
        s.append(f'<text x="{x:.1f}" y="{ly}" class="tick" text-anchor="end" '
                 f'transform="rotate(-55 {x:.1f} {ly})">{g}</text>')
    s.append("</svg>")
    return "".join(s)


def plot_cost(w=940, h=340) -> str:
    """Score against disclosed or current API list-equivalent cost."""
    lo, hi = math.log10(300), math.log10(3500)
    ylo, yhi = 90.0, 101.0
    x0, x1, y0, y1 = 64, w - 30, 40, h - 76

    def xp(cost):
        return x0 + (math.log10(cost) - lo) / (hi - lo) * (x1 - x0)

    def yp(v):
        return y1 - (v - ylo) / (yhi - ylo) * (y1 - y0)

    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Cost frontier: Kepler Opus at $777.72 and Tycho at '
         f'$2,986 both scoring 100; Retrodict at $654 scoring 99.86; baseline1 '
         f'at $400 scoring 99; Kepler GPT at $1,312.14 scoring 95.97">']
    for gv in (90, 95, 100):
        y = yp(gv)
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="grid"/>')
        s.append(f'<text x="{x0-10}" y="{y+4:.1f}" class="tick" text-anchor="end">{gv}</text>')
    for cost, lab in ((400, "$400"), (650, "$650"), (1000, "$1k"),
                      (1600, "$1.6k"), (3000, "$3k")):
        x = xp(cost)
        s.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" class="grid"/>')
        s.append(f'<text x="{x:.1f}" y="{y1+20}" class="tick" '
                 f'text-anchor="middle">{lab}</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{h-12}" class="tick" '
             f'text-anchor="middle">reported or current API list-equivalent USD, log scale</text>')

    # Published lower-cost, lower-scoring points.
    bx, by = xp(400), yp(99.0)
    s.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="6" class="dot other"/>')
    s.append(f'<text x="{bx+12:.1f}" y="{by+23:.1f}" class="lbl dim">baseline1 · $400 · 99.0</text>')
    rx, ry = xp(654), yp(99.86)
    s.append(f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="6" class="dot other"/>')
    s.append(f'<text x="{rx+12:.1f}" y="{ry-12:.1f}" class="lbl">Retrodict · $654 · 99.86</text>')

    # Kepler boards from complete provider transcripts and current API rates.
    gx, gy = xp(1312.14), yp(95.97)
    s.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="6" class="dot"/>')
    s.append(f'<text x="{gx-12:.1f}" y="{gy+24:.1f}" class="lbl dim" text-anchor="end">'
             f'Kepler GPT · $1,312.14 · 95.97</text>')
    ox, oy = xp(777.72), yp(100.0)
    s.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="7" class="dot"/>')
    s.append(f'<text x="{ox-12:.1f}" y="{oy-13:.1f}" class="lbl" text-anchor="end">'
             f'Kepler Opus · $777.72 · 100.00</text>')

    tx, ty = xp(2986), yp(100.0)
    s.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="6" class="dot other"/>')
    s.append(f'<text x="{tx:.1f}" y="{ty+24:.1f}" class="lbl dim" text-anchor="middle">'
             f'Tycho · $2,986 · 100.00</text>')
    s.append(f'<line x1="{ox:.1f}" y1="{oy+40:.1f}" x2="{tx:.1f}" y2="{ty+40:.1f}" '
             f'class="grid strong"/>')
    s.append(f'<text x="{(ox+tx)/2:.1f}" y="{oy+58:.1f}" class="lbl flag" '
             f'text-anchor="middle">Kepler 74.0% lower</text>')
    s.append("</svg>")
    return "".join(s)


# ───────────────────────────── page ─────────────────────────────

def og_image() -> None:
    """1200x630 social card, drawn from the same numbers as the ladder.

    Links on X/HN/Slack render as bare grey text without one, which for a page
    whose job is to be shared is a measurable loss. Drawn with PIL so it ships
    from the same build as every other figure: no design tool, no drift.
    """
    from PIL import ImageDraw

    W, H = 1200, 630
    bg, ink, muted = (18, 17, 15), (236, 234, 228), (160, 156, 146)
    accent, flag = (130, 179, 221), (224, 122, 108)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    def font(size, bold=False):
        from PIL import ImageFont
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",
                                      size, index=1 if bold else 0)
        except Exception:
            return ImageFont.load_default()

    d.text((70, 50), "KEPLER", font=font(28, bold=True), fill=accent)
    d.text((1015, 53), "OPEN SOURCE", font=font(20, bold=True), fill=muted)
    d.text((66, 100), "100% ON ARC-AGI-3", font=font(83, bold=True), fill=ink)
    d.text((70, 205), "ONE FROZEN CONFIG", font=font(29, bold=True), fill=accent)

    d.rounded_rectangle([70, 286, 570, 478], radius=12,
                        outline=(66, 63, 57), width=2)
    d.text((98, 311), "$777.72", font=font(59, bold=True), fill=ink)
    d.text((101, 383), "CURRENT API LIST-EQUIVALENT", font=font(18, bold=True),
           fill=muted)
    d.text((101, 426), "74% BELOW TYCHO ESTIMATE", font=font(24, bold=True),
           fill=accent)

    d.rounded_rectangle([606, 286, 1130, 478], radius=12,
                        outline=flag, width=2)
    d.text((634, 311), "VOIDED 100", font=font(49, bold=True), fill=flag)
    d.text((636, 383), "AGENT READ THE ANSWER KEY", font=font(21, bold=True),
           fill=ink)
    d.text((636, 426), "AUDIT CAUGHT IT. RESULT WITHDRAWN.", font=font(18),
           fill=muted)

    d.text((70, 518), "THE SCORE IS REAL. SO ARE THE FAILURES.",
           font=font(31, bold=True), fill=ink)
    d.text((70, 578),
           "25 public games · ARC server replay · Tycho estimate via Retrodict",
           font=font(17), fill=muted)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "og.png", optimize=True)
    print(f"wrote {OUT/'og.png'}")


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    figs = {
        "hero_wall": hero_wall(),
        "plot_ladder": plot_ladder(),
        "plot_convergence": plot_convergence(),
        "plot_cost": plot_cost(),
        "interactive_data": interactive_data(),
    }
    html = Path(__file__).with_name("template.html").read_text()
    for k, v in figs.items():
        m = f"<!--{k}-->"
        assert m in html, f"missing placeholder {m}"
        html = html.replace(m, v)
    leftover = [l for l in html.splitlines() if "<!--plot_" in l or "<!--hero_" in l]
    assert not leftover, f"unfilled placeholders: {leftover}"
    (OUT / "index.html").write_text(html)
    og_image()
    print(f"wrote {OUT/'index.html'}  ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
