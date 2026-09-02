#!/usr/bin/env python3
"""Regenerate fig1, fig3, fig4, fig5 from per-game data (source: runs*/ result.json).

Style: figstyle.py, muted palette, serif matching the paper, direct labels.
"""
import matplotlib
from pathlib import Path

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import figstyle as S

S.apply()
OUT = Path(__file__).resolve().parent

GAMES = ["ar25","bp35","cd82","cn04","dc22","ft09","g50t","ka59","lf52","lp85","ls20","m0r0",
         "r11l","re86","s5i5","sb26","sc25","sk48","sp80","su15","tn36","tr87","tu93","vc33","wa30"]

def board(over):
    b = {g: 100.0 for g in GAMES}; b.update(over); return b

OPUS = {  # single-config Claude Opus boards, per game
    "initial": board({"bp35":97.43,"sc25":74.92,"sp80":82.16,"tn36":90.04}),
    "discipline": board({"bp35":97.92,"g50t":87.35,"sc25":81.93,"sp80":14.29,"su15":79.03,"tn36":94.84,"tr87":94.81}),
    "guards": board({"g50t":92.29,"sc25":84.02,"sp80":47.62,"tn36":88.88}),
    "certify": board({"sp80":71.43}),
}
GPT_CERTIFY = board({"bp35":56.35,"cd82":95.76,"cn04":98.76,"ka59":98.06,"s5i5":96.31,"sp80":4.47})
GPT_RELEASE = board({"sp80":33.8,"tn36":65.38})
OPUS["kepler"] = board({})

# ---------------------------------------------------------------- fig1: ladder
def fig1():
    rows = [  # (label, score, ours)
        ("Tycho / VISTA / AVO", 100.00, False),
        ("Retrodict", 99.86, False),
        ("VISTA · GPT-5.6 Sol", 98.27, False),
        ("Kepler · Claude Opus 5", 100.00, True),
        ("certify/replay · Claude Opus 5", 98.86, True),
        ("initial loop · Claude Opus 5", 97.77, True),
        ("Kepler · GPT-5.6 Sol", 95.97, True),
        ("certify/replay · GPT-5.6 Sol", 93.99, True),
        ("initial loop · GPT-5.6 Sol (xhigh)", 84.20, True),
        ("minimal scaffold · GPT-5.6 Sol", 73.7, False),
        ("official harness + two settings", 38.3, False),
        ("official harness · GPT-5.6 Sol", 13.3, False),
    ]
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    y = range(len(rows) - 1, -1, -1)
    for yi, (label, v, ours) in zip(y, rows):
        ax.barh(yi, v, height=0.58, color=S.KEPLER if ours else S.EXTERN, zorder=3)
        ax.text(v + 1.2, yi, f"{v:.2f}".rstrip("0").rstrip("."), va="center", ha="left",
                fontsize=9, color=S.INK,
                fontweight="bold" if ours else "normal")
    ax.set_yticks(list(y))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5)
    for t, (_, _, ours) in zip(ax.get_yticklabels(), rows):
        t.set_color(S.INK if ours else S.EXTERN_DK)
        if ours: t.set_fontweight("bold")
    ax.set_xlim(0, 112)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    ax.set_xlabel("RHAE, ARC-AGI-3 public set (higher is better)", fontsize=9.5)
    fig.savefig(OUT / "fig1_ladder.pdf")
    plt.close(fig)

# ------------------------------------------------- fig3: per-game trajectories
def fig3():
    versions = ["initial", "discipline", "guards", "certify", "kepler"]
    x = range(5)
    hl = {"sp80": S.ACCENT, "sc25": S.KEPLER, "g50t": S.GREEN, "tn36": S.PURPLE}
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for g in GAMES:
        ys = [OPUS[v][g] for v in versions]
        if g in hl: continue
        ax.plot(x, ys, color=S.FAINT, lw=0.9, zorder=1)
    offs = {"tn36": 22, "sp80": 11, "g50t": 0, "sc25": -11}  # stagger the 100-convergers
    for g, c in hl.items():
        ys = [OPUS[v][g] for v in versions]
        ax.plot(x, ys, color=c, lw=1.8, marker="o", ms=4, zorder=3)
        ax.annotate(g, (4, ys[-1]), xytext=(9, offs[g]), textcoords="offset points",
                    va="center", fontsize=9.5, color=c, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["initial", "discipline", "guards", "certify/replay", "Kepler"])
    ax.set_xlim(-0.25, 4.55)
    ax.set_ylim(0, 104)
    ax.set_ylabel("per-game RHAE (Claude Opus 5)")
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT / "fig3_pergame.pdf")
    plt.close(fig)

# ------------------------------------------------------ fig4: convergence strip
def fig4():
    fig, ax = plt.subplots(figsize=(6.5, 1.5))
    rows = [("Claude Opus 5", OPUS["kepler"]), ("GPT-5.6 Sol", GPT_RELEASE)]
    for r, (label, b) in enumerate(rows):
        for c, g in enumerate(GAMES):
            v = b[g]
            if v == 100:
                fc = S.KEPLER
            elif v >= 90:
                fc = "#e9d9a8"   # near-miss: muted gold
            else:
                fc = "#dfb0a4"   # discovery failure: muted clay
            ax.add_patch(plt.Rectangle((c, 1 - r), 1, 1, facecolor=fc,
                                       edgecolor="white", lw=1.2))
            if v < 100:
                ax.text(c + 0.5, 1 - r + 0.5, f"{v:.0f}", ha="center", va="center",
                        fontsize=7.5, color=S.INK, fontweight="bold")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 2)
    ax.set_yticks([1.5, 0.5])
    ax.set_yticklabels(["Kepler · Opus 5", "Kepler · GPT-5.6"], fontsize=9)
    ax.set_xticks([i + 0.5 for i in range(25)])
    ax.set_xticklabels(GAMES, rotation=90, fontsize=7.5, fontfamily="monospace")
    ax.grid(False)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(left=False, bottom=False)
    fig.savefig(OUT / "fig4_convergence.pdf")
    plt.close(fig)

# ------------------------------------------------------------ fig5: cost scatter
def fig5():
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    ax.set_xscale("log")
    external = [(400, 99.0, "baseline1\n\\$400 · 99.0"),
                (654, 99.86, "Retrodict\n\\$654 · 99.86"),
                (2986, 100.0, "Tycho\n\\$2,986 est. (Retrodict) · 100.00")]
    for cost, score, label in external:
        ax.scatter([cost], [score], s=70, color=S.EXTERN_DK, zorder=3)
        offset = (0, -30) if cost in (400, 2986) else (-16, -31)
        ax.annotate(label, (cost, score), xytext=offset, textcoords="offset points",
                    ha="center", fontsize=8.5, color=S.INK)

    ax.scatter([1312.14], [95.97], s=70, color=S.KEPLER, zorder=3)
    ax.annotate("Kepler + GPT-5.6\n\\$1,312.14 · 95.97", (1312.14, 95.97),
                xytext=(0, 12), textcoords="offset points", ha="center",
                fontsize=8.5, color=S.INK)
    ax.scatter([777.72], [100.0], s=85, color=S.KEPLER, zorder=3)
    ax.annotate("Kepler + Opus 5\n\\$777.72 · 100.00", (777.72, 100.0),
                xytext=(24, 13), textcoords="offset points", ha="center",
                fontsize=8.5, color=S.INK)
    ax.annotate("", xy=(2986, 98.1), xytext=(777.72, 98.1),
                arrowprops=dict(arrowstyle="<->", color=S.ACCENT, lw=1.3))
    ax.text(1882, 98.35, "74.0% lower", ha="center", fontsize=9.5, color=S.ACCENT)
    ax.set_xlim(300, 3600)
    ax.set_ylim(94, 101.5)
    ax.set_xlabel("reported or current API list-equivalent cost (USD, log scale)")
    ax.set_ylabel("RHAE")
    fig.savefig(OUT / "fig5_cost.pdf")
    plt.close(fig)

if __name__ == "__main__":
    fig1(); fig3(); fig4(); fig5()
    print("wrote fig1, fig3, fig4, fig5")
