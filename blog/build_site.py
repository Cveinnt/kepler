#!/usr/bin/env python3
"""Build blog/site/index.html — the Kepler release page.

Every figure is generated from the recorded runs or the numbers registered in
RESULTS.md. The hero wall is real 64x64 environment observations lifted out of
<runs>/<model>/<game>/events.jsonl and rendered with the ARC-AGI-3 palette; the
convergence strip reads the v5 boards' result.json files directly; the ladder
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

# Roots that contain scored run workspaces (model/game/...). runs-v5 is the
# frozen v5 board; "superseded" subtrees are excluded from the hero wall.
RUN_ROOTS = ("runs", "runs-v5")
V5_BOARDS = (("opus", "Claude Opus"), ("gpt-max", "GPT-5.6 Sol"))

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
    for root in RUN_ROOTS:
        for p in sorted(glob.glob(str(ROOT / root / "*/*/events.jsonl"))):
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
    tiles at 48/32/24/16 per row — every count divides 96, so there is never
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
    for root, model, label in (("runs-v8/opus", "opus", "Claude Opus 5 (v8.1)"),
                               ("runs-v6/gpt-max", "gpt", "GPT-5.6 Sol (v6)")):
        for rj in sorted(Path(root).glob("*/result.json")):
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
    """Figure (a): the ablation ladder v1 -> v5 as a stepped line.

    Composites are the audited single-config Claude Opus boards registered in
    RESULTS.md (each harness frozen by commit hash before its board existed).
    The v2 dip is the regression we published rather than buried.
    """
    rows = [
        ("v1", "base loop + guarded channel", 97.78),
        ("v2", "uniform discipline added", 94.01),
        ("v3", "guards demoted to warnings", 96.51),
        ("v5", "mechanical scored attempts", 98.86),
    ]
    lo, hi = 92.0, 100.0
    x0, x1, y0, y1 = 64, w - 30, 46, h - 84
    pad = 30
    seg = (x1 - x0) / len(rows)

    def yp(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Ablation ladder: v1 97.78, v2 94.01 (the published '
         f'regression), v3 96.51, v5 98.86">']
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
    # the v2 plateau restated in the flag colour: the regression, not hidden
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
    """Figure (c): the two v5 boards as a 25x2 strip, read from result.json.

    Solid accent cells scored exactly 100.0; the exceptions carry their score.
    The counts are asserted so this figure cannot drift from the data.
    """
    scores: dict[str, dict[str, float]] = {}
    for model, _ in V5_BOARDS:
        for rj in sorted(glob.glob(str(ROOT / "runs-v5" / model / "*/result.json"))):
            ws = Path(rj).parent
            if "superseded" in ws.parts:
                continue
            scores.setdefault(model, {})[ws.name] = json.loads(
                Path(rj).read_text())["score"]
    games = sorted(scores[V5_BOARDS[0][0]])
    assert len(games) == 25, f"expected 25 games, found {len(games)}"
    full = sum(1 for m, _ in V5_BOARDS for g in games if scores[m][g] >= 99.995)
    miss = 50 - full
    assert (full, miss) == (43, 7), \
        f"convergence drifted from RESULTS.md: {full} at 100, {miss} below"

    x0, cw, gap, ch = 118, 30, 2.8, 30
    rows_y = (40, 40 + ch + 8)
    h = int(rows_y[1] + ch + 58)
    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Per-game v5 scores for both models: {full} of 50 cells '
         f'at 100.0, {miss} exceptions labeled">']
    s.append(f'<text x="{x0}" y="20" class="tick">v5 boards · one frozen harness · '
             f'score per game — solid = 100.0</text>')
    for (model, label), y in zip(V5_BOARDS, rows_y):
        comp = "98.86" if model == "opus" else "93.99"
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
    """Figure (b): score against measured tokens, log x.

    Two measured points (Kepler v5 GPT board, Retrodict); Tycho reports no
    token accounting, so it is drawn as a labeled line at its score rather
    than a fabricated point. The cached-input caveat lives in the caption.
    """
    lo, hi = 7.0, 9.0           # log10 tokens: 10M .. 1B
    ylo, yhi = 90.0, 101.0
    x0, x1, y0, y1 = 64, w - 30, 40, h - 76

    def xp(tok):
        return x0 + (math.log10(tok) - lo) / (hi - lo) * (x1 - x0)

    def yp(v):
        return y1 - (v - ylo) / (yhi - ylo) * (y1 - y0)

    s = [f'<svg viewBox="0 0 {w} {h}" class="plot" role="img" '
         f'aria-label="Cost frontier: Kepler v5 GPT at 18.7M tokens scoring '
         f'93.99, Retrodict at 659.9M tokens scoring 99.86, Tycho at 100 with '
         f'no token accounting">']
    for gv in (90, 95, 100):
        y = yp(gv)
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="grid"/>')
        s.append(f'<text x="{x0-10}" y="{y+4:.1f}" class="tick" text-anchor="end">{gv}</text>')
    for tok, lab in ((1e7, "10M"), (3e7, "30M"), (1e8, "100M"),
                     (3e8, "300M"), (1e9, "1B")):
        x = xp(tok)
        s.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" class="grid"/>')
        s.append(f'<text x="{x:.1f}" y="{y1+20}" class="tick" '
                 f'text-anchor="middle">{lab}</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{h-12}" class="tick" '
             f'text-anchor="middle">total measured tokens, log scale — '
             f'~98% cached input on both measured systems</text>')

    # Tycho: a labeled line, not a fake point (no token accounting exists)
    ty = yp(100.0)
    s.append(f'<line x1="{x0}" y1="{ty:.1f}" x2="{x1}" y2="{ty:.1f}" class="band"/>')
    s.append(f'<text x="{x1}" y="{ty-9:.1f}" class="lbl faint" text-anchor="end">'
             f'Tycho · 100.00 · est. $2,986 · no token accounting</text>')

    # Retrodict — the published cost-performance frontier
    rx, ry = xp(659.9e6), yp(99.86)
    s.append(f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="6" class="dot other"/>')
    s.append(f'<text x="{rx-14:.1f}" y="{ry+22:.1f}" class="lbl" '
             f'text-anchor="end">Retrodict</text>')
    s.append(f'<text x="{rx-14:.1f}" y="{ry+38:.1f}" class="lbl dim" '
             f'text-anchor="end">99.86 · 659.9M tokens · $654</text>')

    # Kepler v5 GPT board — the measured board
    kx, ky = xp(18.7e6), yp(93.99)
    s.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="6" class="dot"/>')
    s.append(f'<text x="{kx+14:.1f}" y="{ky-16:.1f}" class="lbl">Kepler v5 · '
             f'GPT-5.6 Sol</text>')
    s.append(f'<text x="{kx+14:.1f}" y="{ky:.1f}" class="lbl dim">93.99 · '
             f'18.7M tokens · ~$9–94 list</text>')
    s.append(f'<text x="{kx+14:.1f}" y="{ky+16:.1f}" class="lbl faint">'
             f'(Opus board: 98.86, tokens unmeasured — CLI emits no usage)</text>')

    # the ~35x raw-token gap, drawn between the two measured x positions
    gy = ky + 44
    s.append(f'<line x1="{kx:.1f}" y1="{gy:.1f}" x2="{rx:.1f}" y2="{gy:.1f}" '
             f'class="grid strong"/>')
    for x in (kx, rx):
        s.append(f'<line x1="{x:.1f}" y1="{gy-4:.1f}" x2="{x:.1f}" y2="{gy+4:.1f}" '
                 f'class="grid strong"/>')
    s.append(f'<text x="{(kx+rx)/2:.1f}" y="{gy+18:.1f}" class="lbl dim" '
             f'text-anchor="middle">~35× raw tokens</text>')
    s.append("</svg>")
    return "".join(s)


# ───────────────────────────── page ─────────────────────────────

def og_image() -> None:
    """1200x630 social card, drawn from the same numbers as the ladder.

    Links on X/HN/Slack render as bare grey text without one, which for a page
    whose job is to be shared is a measurable loss. Drawn with PIL so it ships
    from the same build as every other figure — no design tool, no drift.
    """
    from PIL import ImageDraw

    W, H = 1200, 630
    bg, ink, muted = (18, 17, 15), (236, 234, 228), (160, 156, 146)
    accent, flag, base = (130, 179, 221), (224, 122, 108), (111, 107, 99)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    def font(size, bold=False):
        from PIL import ImageFont
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",
                                      size, index=1 if bold else 0)
        except Exception:
            return ImageFont.load_default()

    d.text((70, 58), "KEPLER", font=font(28, bold=True), fill=accent)
    d.text((66, 108), "98.86 on ARC-AGI-3.", font=font(92, bold=True), fill=ink)
    d.text((70, 232), "Single config · 2,426 lines · every action auditable",
           font=font(30), fill=muted)

    rows = [("v1 · base loop", 97.78, base),
            ("v2 · the published regression", 94.01, flag),
            ("v3 · guards demoted", 96.51, base),
            ("v5 · mechanical scored attempts", 98.86, accent)]
    y0, bar_x, bar_w = 318, 500, 560
    for i, (label, v, color) in enumerate(rows):
        y = y0 + i * 56
        d.text((70, y + 2), label, font=font(24), fill=muted)
        d.rectangle([bar_x, y, bar_x + bar_w * (v - 90) / 10, y + 28], fill=color)
        d.text((bar_x + bar_w * (v - 90) / 10 + 14, y), f"{v:.2f}",
               font=font(24, bold=True), fill=ink)
    d.text((70, 570), "the ablation ladder, RHAE 90–100 · every trace published · "
           "the audit caught us twice", font=font(22), fill=muted)
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
