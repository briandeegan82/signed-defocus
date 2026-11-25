"""Experimental-design figure for the Phase 2 render, from committed CSVs (no raw data).

  python src/fig_design.py --out results/figures

Counts come from data/m3_lenses.csv and results/phase2/lenses/m3_ref/m2_displacement_frames.csv
(every design shares the same plates, displacement draws and folds).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from m3_lenses import BASE

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
TRAIN, TEST, EDGE = "#56B4E9", "#D55E00", "#333333"
plt.rcParams.update({"font.family": "serif", "font.size": 7, "pdf.fonttype": 42, "savefig.dpi": 300})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=R / "figures")
    a = ap.parse_args()
    lenses = pd.read_csv(ROOT / "data/m3_lenses.csv")
    f = pd.read_csv(R / "phase2/lenses/m3_ref/m2_displacement_frames.csv")
    plates = f.drop_duplicates(["traversal", "stem"])
    per_trav = plates.groupby(["fold", "traversal"]).size().reset_index(name="n")
    n_plates, n_trav, n_fold = len(plates), plates.traversal.nunique(), plates.fold.nunique()
    k = len(f) // n_plates
    dz_max = f.dz.abs().max() * BASE["defocus_scale"] * 1000 / (2 * BASE["f_number"] * BASE["pixel_pitch"])

    fig, ax = plt.subplots(figsize=(3.5, 3.0))
    ax.set_xlim(0, 100), ax.set_ylim(0, 100), ax.axis("off")
    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99)

    def box(x, y, w, h, txt):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5", fc="#F2F2F2", ec=EDGE, lw=0.6))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=6.5, linespacing=1.25)

    def arrow(p, q):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=0.7, color=EDGE))

    # population
    box(1, 80, 30, 19, f"{len(lenses)} lens designs\nLCA 0 to 2 $\\delta$,\nboth signs, with and\nwithout spherical ab.")
    box(35, 80, 30, 19, f"{n_plates} RobotCar\nraw plates from\n{n_trav} traversals")
    box(69, 80, 30, 19, f"{k} random\ndisplacements per\nplate, within\n$\\pm{dz_max:.1f}\\,\\delta$")
    for x in (33, 67):
        ax.text(x, 89.5, r"$\times$", ha="center", va="center", fontsize=8)
    arrow((50, 79.5), (50, 73.5))
    ax.text(50, 70.5, f"{len(f):,} rendered frames per design", ha="center", va="center", fontsize=7)

    # traversals grouped into folds, width proportional to plate count
    ax.text(1, 63.5, f"The {n_trav} traversals form {n_fold} groups (box width = number of plates)", fontsize=6.5, va="center")
    gap, x = 2.0, 1.0
    scale = (98 - gap * (n_fold - 1)) / n_plates
    for fold, g in per_trav.groupby("fold"):
        x0 = x
        for n in g.n:
            ax.add_patch(Rectangle((x, 52), n * scale, 7, fc="white", ec=EDGE, lw=0.5))
            ax.text(x + n * scale / 2, 55.5, str(n), ha="center", va="center", fontsize=5.5)
            x += n * scale
        ax.text((x0 + x) / 2, 49, f"group {fold + 1}", ha="center", va="center", fontsize=6)
        x += gap

    # folds
    ax.text(1, 42, f"{n_fold} folds: every traversal is scored once, by a rule that never saw it", fontsize=6.5, va="center")
    w, h, x0 = 9.5, 4.6, 14
    for i in range(n_fold):
        y = 34 - i * 5.6
        ax.text(x0 - 1.5, y + h / 2, f"fold {i + 1}", ha="right", va="center", fontsize=6)
        for j in range(n_fold):
            ax.add_patch(Rectangle((x0 + j * (w + 0.8), y), w, h, fc=TEST if i == j else TRAIN, ec=EDGE, lw=0.4))
    ax.add_patch(Rectangle((68, 30.5), 4, 3.6, fc=TRAIN, ec=EDGE, lw=0.4))
    ax.text(73.5, 32.3, "fit threshold\nand size map", va="center", fontsize=6, linespacing=1.2)
    ax.add_patch(Rectangle((68, 19.5), 4, 3.6, fc=TEST, ec=EDGE, lw=0.4))
    ax.text(73.5, 21.3, "score direction\nand displacement", va="center", fontsize=6, linespacing=1.2)
    ax.text(50, 4, "Repeated independently for each lens design", ha="center", va="center", fontsize=6.5, style="italic")

    a.out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(a.out / f"fig_design.{ext}")
    print(len(lenses), n_plates, n_trav, k, len(f), n_fold, round(dz_max, 2))


if __name__ == "__main__":
    main()
