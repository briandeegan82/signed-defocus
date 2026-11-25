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
# OJVT template: Times-style lettering at 8 pt or more.
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8, "pdf.fonttype": 42, "savefig.dpi": 300})


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

    # drawn in inches on a single-column canvas
    W, rh, cw = 3.5, 0.165, 0.27
    pt = per_trav.sort_values(["fold", "traversal"]).reset_index(drop=True)
    H = 1.75 + len(pt) * rh + 0.75
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W), ax.set_ylim(0, H), ax.axis("off")

    def box(x, y, w, h, txt):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc="#F2F2F2", ec=EDGE, lw=0.6))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", linespacing=1.15)

    # population
    bw, bh, gap, y0 = 1.06, 0.64, 0.16, H - 0.69
    xs = [0.03 + i * (bw + gap) for i in range(3)]
    box(xs[0], y0, bw, bh, f"{len(lenses)} lens designs,\nLCA 0 to 2 $\\delta$,\nboth signs, with and\nwithout sph. aberr.")
    box(xs[1], y0, bw, bh, f"{n_plates} RobotCar\nraw images\nfrom {n_trav} drives")
    box(xs[2], y0, bw, bh, f"{k} random\ndisplacements\nper image, within\n$\\pm{dz_max:.1f}\\,\\delta$")
    for i in range(2):
        ax.text(xs[i] + bw + gap / 2, y0 + bh / 2, r"$\times$", ha="center", va="center")
    ya = y0 - 0.05
    ax.add_patch(FancyArrowPatch((W / 2, ya), (W / 2, ya - 0.15), arrowstyle="-|>", mutation_scale=7, lw=0.7, color=EDGE))
    ax.text(W / 2, ya - 0.26, f"{len(f):,} rendered frames per design", ha="center", va="center")

    # one row per drive (traversal), one column per test round (fold)
    ax.text(0.03, ya - 0.52, f"{n_trav} drives (RobotCar traversals, 2014) in {n_fold} groups", va="center")
    cx = W - n_fold * cw - 0.05
    top = ya - 0.95
    for c in range(n_fold):
        ax.text(cx + c * cw + cw / 2, top + 0.03, str(c + 1), ha="center", va="bottom")
    ax.text(cx + n_fold * cw / 2, top + 0.17, "test round", ha="center", va="bottom")
    for r, row in pt.iterrows():
        y = top - (r + 1) * rh
        t = pd.Timestamp(pd.to_datetime(row.traversal, format="%Y-%m-%d-%H-%M-%S"))
        ax.text(0.03, y + rh / 2, t.strftime("%-d %b, %H:%M"), va="center")
        ax.text(cx - 0.08, y + rh / 2, f"{row.n} images", va="center", ha="right")
        for c in range(n_fold):
            ax.add_patch(Rectangle((cx + c * cw, y + 0.012), cw - 0.025, rh - 0.024,
                                   fc=TEST if row.fold == c else TRAIN, ec=EDGE, lw=0.3))
        if r + 1 < len(pt) and pt.fold[r + 1] != row.fold:
            ax.plot([0.03, cx + n_fold * cw], [y, y], color=EDGE, lw=0.3, ls=":")
    yl = top - len(pt) * rh - 0.2
    for dy, fc, txt in [(0, TRAIN, "calibrate: threshold $c_0$, sign $s$, curve $\\gamma$"),
                        (-0.19, TEST, "test: score direction and displacement")]:
        ax.add_patch(Rectangle((0.03, yl + dy - 0.055), 0.16, 0.11, fc=fc, ec=EDGE, lw=0.4))
        ax.text(0.25, yl + dy, txt, va="center")
    ax.text(W / 2, 0.1, "Repeated independently for each lens design", ha="center", va="center", style="italic")

    a.out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(a.out / f"fig_design.{ext}")
    print(len(lenses), n_plates, n_trav, k, len(f), n_fold, round(dz_max, 2))


if __name__ == "__main__":
    main()
