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
plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "dejavuserif", "font.size": 7, "pdf.fonttype": 42, "savefig.dpi": 300})


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

    fig, ax = plt.subplots(figsize=(3.5, 3.3))
    ax.set_xlim(0, 100), ax.set_ylim(0, 100), ax.axis("off")
    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99)

    def box(x, y, w, h, txt):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5", fc="#F2F2F2", ec=EDGE, lw=0.6))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=6.5, linespacing=1.25)

    def arrow(p, q):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=0.7, color=EDGE))

    # population
    box(1, 80, 30, 19, f"{len(lenses)} lens designs\nLCA 0 to 2 $\\delta$,\nboth signs, with and\nwithout spherical ab.")
    box(35, 80, 30, 19, f"{n_plates} RobotCar\nraw images from\n{n_trav} drives")
    box(69, 80, 30, 19, f"{k} random\ndisplacements per\nimage, within\n$\\pm{dz_max:.1f}\\,\\delta$")
    for x in (33, 67):
        ax.text(x, 89.5, r"$\times$", ha="center", va="center", fontsize=8)
    arrow((50, 79.5), (50, 75.5))
    ax.text(50, 72.5, f"{len(f):,} rendered frames per design", ha="center", va="center", fontsize=7)

    # one row per drive (traversal), one column per fold
    ax.text(1, 67.5, f"{n_trav} drives (RobotCar traversals), split into {n_fold} folds", fontsize=6.5, va="center")
    pt = per_trav.sort_values(["fold", "traversal"]).reset_index(drop=True)
    top, rh, cw, cx = 60, 4.3, 6.4, 42
    for c in range(n_fold):
        ax.text(cx + c * cw + cw / 2, top + 0.6, f"fold\n{c + 1}", ha="center", va="bottom", fontsize=5.5, linespacing=1.0)
    for r, row in pt.iterrows():
        y = top - (r + 1) * rh
        t = pd.Timestamp(pd.to_datetime(row.traversal, format="%Y-%m-%d-%H-%M-%S"))
        ax.text(1, y + rh / 2, t.strftime("%-d %b %Y, %H:%M"), va="center", fontsize=5.5)
        ax.text(cx - 2, y + rh / 2, f"{row.n} images", va="center", ha="right", fontsize=5.5)
        for c in range(n_fold):
            ax.add_patch(Rectangle((cx + c * cw, y + 0.3), cw - 0.6, rh - 0.6,
                                   fc=TEST if row.fold == c else TRAIN, ec=EDGE, lw=0.3))
        if r + 1 < len(pt) and pt.fold[r + 1] != row.fold:
            ax.plot([1, cx + n_fold * cw], [y, y], color=EDGE, lw=0.3, ls=":")
    lx = cx + n_fold * cw + 2
    ax.add_patch(Rectangle((lx, 51), 3.5, 3.2, fc=TRAIN, ec=EDGE, lw=0.4))
    ax.text(lx + 4.5, 52.6, "calibrate:\nthreshold $c_0$,\nsign $s$,\ncurve $\\gamma$", va="center", fontsize=6, linespacing=1.2)
    ax.add_patch(Rectangle((lx, 36), 3.5, 3.2, fc=TEST, ec=EDGE, lw=0.4))
    ax.text(lx + 4.5, 37.6, "test: score\ndirection and\ndisplacement", va="center", fontsize=6, linespacing=1.2)
    ax.text(50, 3, "Repeated independently for each lens design", ha="center", va="center", fontsize=6.5, style="italic")

    a.out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(a.out / f"fig_design.{ext}")
    print(len(lenses), n_plates, n_trav, k, len(f), n_fold, round(dz_max, 2))


if __name__ == "__main__":
    main()
