#!/usr/bin/env python3
"""Regenerate fig2_arch.pdf, the Kepler system architecture diagram.

The original fig2 had overlapping boxes/text; this lays every element out on an
explicit grid so nothing can collide.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import figstyle as S

S.apply()
BLUE = S.KEPLER
GRAY = S.EXTERN_DK
RED = S.ACCENT
INK = S.INK

fig, ax = plt.subplots(figsize=(6.5, 2.6))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x0, y0, x1, y1, color, lines, fs=8.0, lw=2.0, bold_first=True):
    ax.add_patch(
        FancyBboxPatch(
            (x0, y0), x1 - x0, y1 - y0,
            boxstyle="round,pad=0.6,rounding_size=1.6",
            fill=True, facecolor="white", edgecolor=color, linewidth=lw,
            mutation_aspect=100 / 45,
        )
    )
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    n = len(lines)
    step = min(9.5, (y1 - y0) / (n + 0.4)) if n > 1 else 0
    top = cy + step * (n - 1) / 2
    for i, ln in enumerate(lines):
        ax.text(
            cx, top - i * step, ln, ha="center", va="center", fontsize=fs,
            color=INK, fontweight="bold" if (bold_first and i == 0) else "normal",
            fontfamily="serif",
        )


def arrow(x0, y0, x1, y1, color, two_way=True, rad=0.0, lw=2.0):
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="<->" if two_way else "->", color=color, lw=lw,
            connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2,
        ),
    )


# --- main pipeline row -------------------------------------------------------
box(2, 42, 26, 92, BLUE, [
    "workspace",
    "agent (CLI model)",
    "world_model.py · notes.md",
    "events.jsonl (append-only)",
    "tools/",
], fs=7.4)
box(34, 56, 54, 84, BLUE, ["commit.py", "guarded channel", "predict $\\rightarrow$ act $\\rightarrow$ diff"], fs=7.4)
box(62, 56, 77, 84, GRAY, ["daemon"], fs=8.0)
box(85, 56, 98, 84, GRAY, ["local engine"], fs=8.0)

arrow(27.2, 70, 32.8, 70, BLUE)
arrow(55.2, 70, 60.8, 70, GRAY)
arrow(78.2, 70, 83.8, 70, GRAY)

# --- scored-attempt path (red) ----------------------------------------------
box(34, 10, 54, 38, RED, ["cleanrun.py", "mechanical replay", "(no model in loop)"], fs=7.4)
arrow(54.8, 32, 68, 54.4, RED, two_way=False, rad=-0.28, lw=2.2)
ax.text(50, 2.5, "agent writes the certificate; the harness plays the scored attempt",
        ha="center", va="center", fontsize=7.4, color=RED, style="italic", fontfamily="serif")

# --- environment files, outside every workspace ------------------------------
box(2, 12, 26, 30, GRAY, ["environment files", "outside every workspace", "(post-incident 1)"],
    fs=6.8, lw=1.6, bold_first=True)

fig.savefig("fig2_arch.pdf", bbox_inches="tight", pad_inches=0.05)
print("wrote fig2_arch.pdf")
