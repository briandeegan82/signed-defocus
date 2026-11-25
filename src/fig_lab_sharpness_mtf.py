"""Calibration-split comparison of Tenengrad and Laplacian-pyramid energy against raw-Bayer green MTF.

Uses only the 20 laboratory calibration steps (every fourth step, left chart half; s = 0, 4, ..., 76)
so the frozen held-out laboratory test split is never touched.

  python src/fig_lab_sharpness_mtf.py --feat /home/ubuntu/labest/results/lab_feat_real_all.parquet
  python src/fig_lab_sharpness_mtf.py          # redraw from committed CSV only
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent.parent
CSV_PATH = HERE / "results/lab_sweep/sharpness_mtf_calibration.csv"
MTF_PATH = HERE / "results/lab_sweep/mtf_fit_calibration.csv"
FITS_PATH = HERE / "results/lab_sweep/step_size_fits.csv"
OUT_DIR = HERE / "results/figures"

CHART_X_MID = 2048
COL1 = 3.5
FS = 8
OK = dict(blue="#0072B2", orange="#D55E00")

plt.rcParams.update({
    "font.family": "STIXGeneral",
    "mathtext.fontset": "stix",
    "font.size": FS,
    "axes.labelsize": FS,
    "legend.fontsize": FS,
    "xtick.labelsize": FS,
    "ytick.labelsize": FS,
    "axes.titlesize": FS,
    "figure.labelsize": FS,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "savefig.dpi": 300,
    "legend.frameon": False,
    "lines.markersize": 4.2,
})


def build_csv(feat_path: Path) -> pd.DataFrame:
    d = pd.read_parquet(feat_path, columns=["cx_grad_mean", "lp_e0", "step", "px"])
    d["s"] = d.step // 2
    cal = d[d.s.isin(range(0, 80, 4)) & (d.px + 64 < CHART_X_MID)]
    f = cal.groupby("s", as_index=False).agg(
        tenengrad=("cx_grad_mean", "median"),
        laplacian=("lp_e0", "median"),
        n_patches=("px", "size"),
    )
    s0_g = float(pd.read_csv(FITS_PATH).iloc[0]["s0_g"])
    f["dz_steps"] = f["s"] - s0_g
    f["ten_norm"] = f["tenengrad"] / f["tenengrad"].max()
    f["lap_norm"] = f["laplacian"] / f["laplacian"].max()
    mtf = pd.read_csv(MTF_PATH, dtype={"fk": str})
    for fk in ("0125", "025"):
        g = mtf[(mtf.ch == "g") & (mtf.fk == fk)][["s", "mtf"]].rename(columns={"mtf": f"mtf_g_{fk}"})
        f = f.merge(g, on="s")
    f.round(6).to_csv(CSV_PATH, index=False)
    return f


def plot_figure(df: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(COL1, 4.35), layout="constrained")
    sfs = fig.subfigures(2, 1, hspace=0.06)
    neg = df["dz_steps"] < 0
    pos = ~neg

    specs = [
        (sfs[0], "mtf_g_0125", "Raw-Bayer green MTF at 0.125 cy/px", "a", True),
        (sfs[1], "mtf_g_025", "Raw-Bayer green MTF at 0.25 cy/px", "b", False),
    ]
    handles, labels = [], []
    for sf, col, xlabel, tag, collect_leg in specs:
        ax = sf.subplots()
        ax.plot(df[col], df["ten_norm"], color=OK["blue"], lw=0.7, alpha=0.35, zorder=1)
        ax.plot(df[col], df["lap_norm"], color=OK["orange"], lw=0.7, alpha=0.35, zorder=1)
        h1, = ax.plot(df.loc[neg, col], df.loc[neg, "ten_norm"], "o", color=OK["blue"],
                      label="Tenengrad ($\\Delta z < 0$)")
        h2, = ax.plot(df.loc[pos, col], df.loc[pos, "ten_norm"], "o", color=OK["blue"], mfc="white",
                      label="Tenengrad ($\\Delta z > 0$)")
        h3, = ax.plot(df.loc[neg, col], df.loc[neg, "lap_norm"], "^", color=OK["orange"],
                      label="Laplacian ($\\Delta z < 0$)")
        h4, = ax.plot(df.loc[pos, col], df.loc[pos, "lap_norm"], "^", color=OK["orange"], mfc="white",
                      label="Laplacian ($\\Delta z > 0$)")
        if collect_leg:
            handles = [h1, h2, h3, h4]
            labels = [h.get_label() for h in handles]

        rt, _ = spearmanr(df["tenengrad"], df[col])
        rl, _ = spearmanr(df["laplacian"], df[col])
        ax.text(0.98, 0.08, f"Spearman $\\rho$: Ten. {rt:.3f}, Lap. {rl:.3f}",
                transform=ax.transAxes, ha="right", va="bottom")
        ax.set(xlabel=xlabel, ylabel="Sharpness / peak", ylim=(0.22, 1.06))
        sf.supxlabel(f"({tag})")

    fig.legend(handles, labels, loc="outside upper center", ncol=2, handletextpad=0.3, columnspacing=1.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig_lab_sharpness_mtf.{ext}", bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat", type=Path, default=None, help="lab_feat_real_all.parquet (optional; rebuilds CSV)")
    a = ap.parse_args()
    df = build_csv(a.feat) if a.feat is not None else pd.read_csv(CSV_PATH)
    plot_figure(df)
    print(f"Wrote {CSV_PATH} ({len(df)} rows) and {OUT_DIR / 'fig_lab_sharpness_mtf.pdf'}")


if __name__ == "__main__":
    main()
