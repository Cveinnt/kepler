"""Shared style for Kepler paper figures.

Principles (Tufte / frontier-lab house style): muted low-saturation palette with
strong value contrast, serif type matching the paper's Latin Modern, despined
axes, whisper-weight gridlines, direct labels over legends, no chartjunk.
"""
import matplotlib as mpl

# palette — restrained, colorblind-safe value contrast
INK = "#1f2328"      # near-black text
KEPLER = "#3d5a9e"   # slate blue: our boards
EXTERN = "#b6bcc4"   # cool gray: external systems
EXTERN_DK = "#8a919a"
ACCENT = "#b0442e"   # clay red: failures / the one highlighted thing
GOLD = "#d9a441"     # warm secondary highlight
GREEN = "#5e8c61"
PURPLE = "#7d6aa3"
FAINT = "#e8eaed"    # gridlines / context lines

SERIF = ["Latin Modern Roman", "CMU Serif", "Georgia", "Times New Roman", "DejaVu Serif"]


def apply():
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": SERIF,
        "mathtext.fontset": "cm",
        "text.color": INK,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": FAINT,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "axes.titlesize": 11,
        "axes.labelsize": 10.5,
        "font.size": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "figure.dpi": 150,
    })
