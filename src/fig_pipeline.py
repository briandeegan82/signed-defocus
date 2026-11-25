"""Rendering-pipeline figure from results/figures/data/pipeline_stages.npz (written by fig_pipeline_data.py).

  python src/fig_pipeline.py --out results/figures
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

R = Path(__file__).resolve().parents[1] / "results"
plt.rcParams.update({"font.family": "serif", "font.size": 7, "pdf.fonttype": 42, "savefig.dpi": 300})


def show(ax, img, title=None, **kw):
    ax.imshow(img, interpolation="nearest", **kw)
    ax.set_xticks([]), ax.set_yticks([])
    if title:
        ax.set_title(title, fontsize=7, pad=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=R / "figures")
    a = ap.parse_args()
    d = np.load(R / "figures/data/pipeline_stages.npz")
    m = json.loads(str(d["meta"]))
    y0, x0, n = *m["crop_yx"], m["crop"]
    z = m["dz_delta"]
    rows = [("neg", rf"$\Delta z=-{z:g}\,\delta$"), ("source", "Unblurred"), ("pos", rf"$\Delta z=+{z:g}\,\delta$")]

    fig = plt.figure(figsize=(7.16, 3.3))
    gs = fig.add_gridspec(3, 9, width_ratios=[2.66, 0.25, 1, 1, 1, 0.95, 1.3, 1.3, 1.3],
                          left=0.005, right=0.995, top=0.93, bottom=0.02, wspace=0.06, hspace=0.08)
    ax = fig.add_subplot(gs[:, 0])
    show(ax, d["frame_small"], "RobotCar scene")
    ax.add_patch(Rectangle((x0 / 2, y0 / 2), n / 2, n / 2, fill=False, ec="yellow", lw=1.0))

    def arrow(x_a, x_b, y, txt):
        fig.add_artist(FancyArrowPatch((x_a, y), (x_b, y), transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=8, lw=0.8, color="k"))
        fig.text((x_a + x_b) / 2, y + 0.02, txt, ha="center", va="bottom", fontsize=6, linespacing=1.15)

    for r, (s, lab) in enumerate(rows):
        crop = d[f"crop_{s}"]
        first = None
        for c, (img, t, kw) in enumerate([(crop, "Crop", {}),
                                          (crop[..., 0], "Red channel", dict(cmap="gray", vmin=0, vmax=255)),
                                          (crop[..., 2], "Blue channel", dict(cmap="gray", vmin=0, vmax=255))]):
            ax = fig.add_subplot(gs[r, 6 + c])
            show(ax, img, t if r == 0 else None, **kw)
            first = first or ax
        y = first.get_position().y0 + first.get_position().height / 2
        if s == "source":
            fig.text(0.285, y + 0.02, lab, ha="left", va="bottom", fontsize=7)
            arrow(0.275, 0.625, y, "no blur, no added noise:\nimage pipeline only")
            continue
        for c, ch in enumerate("rgb"):
            ax = fig.add_subplot(gs[r, 2 + c])
            k = d[f"psf_{s}_{ch}"]
            show(ax, k / k.max(), {"r": "Red PSF", "g": "Green PSF", "b": "Blue PSF"}[ch] if r == 0 else None,
                 cmap="gray", vmin=0, vmax=1)
            if c == 0:
                ax.set_ylabel(lab, fontsize=7, labelpad=2)
        arrow(0.555, 0.625, y - 0.04, "blur each\nBayer plane,\nadd noise,\nimage\npipeline")
    a.out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(a.out / f"fig_pipeline.{ext}")
    print(f"{m['lens']} LCA {m['lca_delta']:.2f} delta, plate {m['traversal']}/{m['frame']}")


if __name__ == "__main__":
    main()
