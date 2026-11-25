"""Figures 1-6 from the committed result CSVs (no raw data needed).

  python src/figures.py --out results/figures

Fig 1 M3 dose-response, Fig 2 lab through-focus MTF (calibration steps), Fig 3 M2 continuous
displacement, Fig 4 M7 field position, Fig 5 M8 confounds, Fig 6 M6 illuminant / white balance.
Units: δ = 2 N p; rendered synth lenses use δ = 22 µm (f/2, 5.5 µm); the lab lens uses
0.154 δ per step (results/lab_sweep); Sony and Laikin stay in nominal DZ units.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lab_sweep as LSW  # noqa: E402
from m3_lenses import BASE, LAMBDA, SYNTH_LCAP_LONG_CA  # noqa: E402

R = Path(__file__).resolve().parents[1] / "results"
OK = dict(black="#000000", orange="#E69F00", sky="#56B4E9", green="#009E73",
          yellow="#F0E442", blue="#0072B2", verm="#D55E00", purple="#CC79A7")
CH = {"r": OK["verm"], "g": OK["green"], "b": OK["blue"]}
COL1, COL2 = 3.5, 7.16
DELTA_UM, UM_PER_DZ = 22.0, 1000.0
DZ2D = UM_PER_DZ / DELTA_UM
RNG = np.random.default_rng(20261124)

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False,
    "axes.spines.right": False, "pdf.fonttype": 42, "savefig.dpi": 300,
    "legend.frameon": False, "lines.markersize": 4,
})


LCAP = SYNTH_LCAP_LONG_CA * (LAMBDA["r"] - LAMBDA["b"]) * 1000 / (2 * BASE["f_number"] * BASE["pixel_pitch"])


def save(fig, out, name):
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{name}.{ext}", metadata={"Creator": "src/figures.py"} if ext == "pdf" else None)
    plt.close(fig)


def tag(ax, s):
    ax.text(-0.18, 1.04, s, transform=ax.transAxes, fontweight="bold", va="bottom")


def boot_mean(x, groups, n=2000):
    """Mean and 95% interval, resampling whole groups (plates) with replacement."""
    g = pd.Series(x).groupby(np.asarray(groups))
    s, c = g.sum().values, g.size().values
    idx = RNG.integers(0, len(s), (n, len(s)))
    b = s[idx].sum(1) / c[idx].sum(1)
    return s.sum() / c.sum(), *np.percentile(b, [2.5, 97.5])


def fig1_m3(out):
    d = pd.read_csv(R / "phase2/phase2_summary.csv")
    d["sign"] = np.where(d.lens.str.contains("_n"), "−", np.where(d.lens.str.contains("_p"), "+", "0"))
    d.loc[d.lens == "m3_ref", "sign"] = "ref"
    d["sa"] = d.lens.str.endswith("_sa")
    ga = pd.read_csv(R / "phase2/phase2_gate_a.csv").iloc[0]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.4), layout="constrained")
    mk = {"+": "^", "−": "v", "0": "o", "ref": "*"}
    for (sg, sa), g in d.groupby(["sign", "sa"]):
        kw = dict(marker=mk[sg], ls="none", ms=6 if sg == "ref" else 5, color=OK["orange"] if sa else OK["blue"],
                  mfc="white" if sa else None, label=f"LCA {sg}{', SA' if sa else ''}" if sg != "ref" else "reference design (copy)")
        a.plot(g.lca_over_delta, g.dir_acc, **kw)
        b.plot(g.lca_over_delta, g.mae_delta_unseen, **kw)
        b.plot(g.lca_over_delta, g.p90_delta_unseen, **{**kw, "alpha": 0.45, "label": None})
    a.axhline(0.5, color="0.6", lw=0.6, ls=":")
    a.set(xlabel="|LCA| / δ", ylabel="Direction accuracy", ylim=(0.45, 1.02))
    a.text(0.98, 0.05, f"Spearman ρ = {ga.spearman_rho:.2f}, n = {int(ga.n_lenses)}", transform=a.transAxes, ha="right")
    b.axhline(1.0, color="k", lw=0.8, ls="--")
    b.axvspan(1.0, 2.1, color="0.92", zorder=0)
    b.text(1.55, 6.3, "Gate B applies", ha="center", fontsize=7)
    b.text(0.02, 1.08, "1 δ", fontsize=7)
    b.set(xlabel="|LCA| / δ", ylabel="Error, Δz absent from training (δ)", xlim=(-0.08, 2.1), ylim=(0, 7.6))
    b.set_title("solid: MAE   faded: p90", loc="right", fontsize=7)
    a.legend(loc="center right", ncol=1, handletextpad=0.3)
    tag(a, "(a)"); tag(b, "(b)")
    save(fig, out, "fig1_m3_dose_response")


def fig2_lab(out):
    d = pd.read_csv(R / "lab_sweep/mtf_fit_calibration.csv", dtype={"fk": str})
    res, _, r = LSW.fit(d)
    chans, fks = sorted(d.ch.unique()), sorted(d.fk.unique())
    keys = [(c, f) for c in chans for f in fks]
    k, s0 = r.x[0], dict(zip(chans, r.x[1:4]))
    A, F = dict(zip(keys, r.x[4:4 + len(keys)])), dict(zip(fks, r.x[4 + len(keys):]))
    dps = float(pd.read_csv(R / "lab_sweep/step_size_fits.csv").iloc[0].lca_rb_over_delta /
                (res["s0_r"] - res["s0_b"]))  # δ per step
    ss = np.linspace(0, 79, 400)
    fig, axs = plt.subplots(1, 2, figsize=(COL2, 2.4), layout="constrained", sharey=True)
    for ax, fk in zip(axs, ["0125", "025"]):
        nu = LSW.FREQ[fk] / LSW.PITCH
        for c in "rgb":
            g = d[(d.ch == c) & (d.fk == fk)]
            ax.plot(g.s, g.mtf, "os^"["rgb".index(c)], color=CH[c], mfc="white", label=f"{c.upper()} measured")
            m = A[(c, fk)] * np.abs(LSW.otf_defocus(nu, LSW.LAMBDA[c], k * (ss - s0[c]))) + F[fk]
            ax.plot(ss, m, color=CH[c], lw=1, ls=["-", "--", "-."]["rgb".index(c)], label=f"{c.upper()} fit")
            ax.axvline(s0[c], color=CH[c], lw=0.6, ls=":")
        ax.set(xlabel="Focus step", xlim=(0, 79))
        ax.set_title(f"({'ab'[fks.index(fk)]}) {LSW.FREQ[fk]} cy/px", loc="left", fontweight="bold")
        top = ax.secondary_xaxis("top", functions=(lambda s: (s - s0["g"]) * dps, lambda z: z / dps + s0["g"]))
        top.set_xlabel("Δz from green focus (δ)")
    axs[0].set_ylabel("MTF (raw Bayer plane)")
    axs[1].legend(ncol=2, loc="upper right", columnspacing=0.8)
    axs[0].text(0.52, 0.03, f"1 step = {k / LSW.N_F:.2f}·N µm = {dps:.3f} δ\n"
                f"R − B focus = {(s0['r'] - s0['b']) * dps:.2f} δ", transform=axs[0].transAxes, ha="center",
                va="bottom", fontsize=7)
    save(fig, out, "fig2_lab_through_focus")


def fig3_m2(out):
    f = pd.read_csv(R / "phase2/lenses/m3_ref/m2_displacement_frames.csv")
    f = f[f.train == "continuous"]
    dr = pd.read_csv(R / "phase2/lenses/m3_ref/m2_direction.csv")
    dr = dr[(dr.level == "fitted") & (dr.band != "all")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.5), layout="constrained", gridspec_kw=dict(width_ratios=[1.3, 1]))
    x, y = f.dz_over_delta, f.dz_hat * DZ2D
    lim = np.array([-5, 5])
    a.fill_between(lim, lim - 1, lim + 1, color="0.9", lw=0, label="±1 δ")
    a.plot(lim, lim, "k-", lw=0.7, label="y = x")
    a.plot(x, y, "o", ms=1.5, color=OK["blue"], alpha=0.35, mew=0, label=f"held-out frames (n = {len(f)})")
    a.set(xlabel="True Δz (δ)", ylabel="Predicted Δz (δ)", xlim=lim, ylim=lim, aspect="equal")
    a.legend(loc="upper left")
    lab = [s.replace("inf", "∞") for s in dr.band]
    b.bar(range(len(dr)), dr.acc, color=OK["sky"], edgecolor="k", lw=0.5)
    for i, (acc, n) in enumerate(zip(dr.acc, dr.n)):
        b.text(i, acc + 0.01, f"{acc:.2f}\nn={n}", ha="center", va="bottom", fontsize=6.5)
    b.set(xticks=range(len(dr)), xticklabels=lab, xlabel="|Δz| band (δ)", ylabel="Direction accuracy", ylim=(0, 1.18))
    b.axhline(0.5, color="0.6", lw=0.6, ls=":")
    tag(a, "(a)"); tag(b, "(b)")
    save(fig, out, "fig3_m2_continuous")


def fig4_m7(out):
    s = pd.read_csv(R / "m7_field/m7_summary.csv")
    q = pd.read_csv(R / "m7_field/lab_squares_focus.csv")
    zones = ["centre", "mid", "corner"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.4), layout="constrained")
    series = [("uniform", "direction_acc", "Uniform PSF", OK["blue"], "o"),
              ("field-varying", "direction_acc", "Field-varying, nominal focus", OK["verm"], "s"),
              ("field-varying", "direction_acc_local", "Field-varying, zone's own focus", OK["orange"], "D")]
    for j, (rd, col, lab, c, m) in enumerate(series):
        g = s[s.render == rd].set_index("zone").loc[zones]
        a.plot(np.arange(3) + (j - 1) * 0.12, g[col], m, color=c, label=lab, ls="-", lw=0.6, mfc="white" if j == 2 else c)
    a.set(xticks=range(3), xticklabels=["center", "mid", "corner"], xlabel="Field zone (rendered Sony map)", ylabel="Direction accuracy",
          ylim=(0.5, 1.0))
    a.axhline(0.5, color="0.6", lw=0.6, ls=":")
    a.legend(loc="lower left")
    for fq, m, c in [(0.125, "o", OK["blue"]), (0.25, "^", OK["verm"])]:
        g = q[q.freq_cy_px == fq]
        b.plot(g.field_r, g.lca_rb_delta, m, color=c, mfc="white" if fq == 0.25 else c, label=f"{fq} cy/px")
    b.axhline(0, color="k", lw=0.6)
    b.set(xlabel="Field radius (normalized)", ylabel="R − B focus (δ), lab squares")
    b.legend(loc="lower left")
    tag(a, "(a)"); tag(b, "(b)")
    save(fig, out, "fig4_m7_field")


def fig5_m8(out):
    order = ["in focus", "defocus -0.02", "defocus +0.02", "motion", "fog"]
    lab = ["In focus", "Defocus −", "Defocus +", "Motion blur", "Fog"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.5), layout="constrained")
    w = 0.38
    for j, (lens, c, h) in enumerate([("synth_lcaP", OK["blue"], None), ("laikin", OK["orange"], "///")]):
        fr = pd.read_csv(R / f"m8_confounds/{lens}/m8_frames.csv")
        fr["alarm"] = fr.dz_pred.abs() > fr.alarm_thr
        stats = [boot_mean(fr[fr.condition == k].alarm.astype(float).values,
                           fr[fr.condition == k].traversal.values) for k in order]
        m, lo, hi = np.array(stats).T
        xs = np.arange(5) + (j - 0.5) * w
        a.bar(xs, m, w, color=c, hatch=h, edgecolor="k", lw=0.5, label=f"strong LCA ({LCAP:.2f} δ)" if j == 0 else "Laikin (weak LCA)")
        a.errorbar(xs, m, [m - lo, hi - m], fmt="none", ecolor="k", lw=0.7, capsize=1.5)
    a.set(xticks=range(5), xticklabels=lab, ylabel="Alarm rate", ylim=(0, 1.0))
    a.tick_params(axis="x", rotation=25)
    a.legend(loc="upper right")
    fr = pd.read_csv(R / "m8_confounds/synth_lcaP/m8_frames.csv")
    data = [fr[fr.condition == k].dz_pred.values * DZ2D for k in order]
    bp = b.boxplot(data, whis=(5, 95), showfliers=False, widths=0.5, patch_artist=True,
                   medianprops=dict(color="k"), boxprops=dict(facecolor=OK["sky"], lw=0.6))
    for i, v in enumerate(data):
        b.plot(np.full(len(v), i + 1) + RNG.uniform(-0.18, 0.18, len(v)), v, ".", ms=1.5, color="0.35", alpha=0.35)
    b.axhline(0, color="k", lw=0.6)
    for y in (-20 / DELTA_UM, 20 / DELTA_UM):
        b.axhline(y, color="0.5", lw=0.6, ls="--")
    b.set(xticks=range(1, 6), xticklabels=lab, ylabel="Predicted Δz (δ), strong-LCA design")
    b.tick_params(axis="x", rotation=25)
    b.set_title("box: IQR; whiskers: 5–95 %; dashed: true Δz = ±0.91 δ", loc="right", fontsize=6.5)
    a.set_title("bars: 95 % traversal-bootstrap interval", loc="right", fontsize=6.5)
    tag(a, "(a)"); tag(b, "(b)")
    save(fig, out, "fig5_m8_confounds")


def fig6_m6(out):
    f = pd.read_csv(R / "m6_illuminant/m6_frames.csv")
    f["e"] = (f.dz_pred - f.dz) * DZ2D
    order = ["nominal", "shift+10", "shift-10", "warm", "cool", "wb_r0.8", "wb_r1.25", "wb_b0.8", "wb_b1.25"]
    lab = ["Nominal", "+10 nm", "−10 nm", "Warm", "Cool", "R gain ×0.8", "R gain ×1.25", "B gain ×0.8", "B gain ×1.25"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.6), layout="constrained", sharey=True)
    y = np.arange(len(order))[::-1]
    for i, k in enumerate(order):
        g = f[f.condition == k]
        for ax, val, sub, c, m, dy in [(a, g.e, g, OK["blue"], "o", 0),
                                       (b, g.e.abs(), g, OK["blue"], "o", 0.15),
                                       (b, g.e.abs()[g.dz.abs() <= 0.01], g[g.dz.abs() <= 0.01], OK["verm"], "s", -0.15)]:
            mu, lo, hi = boot_mean(val.values, sub.stem.values)
            ax.errorbar(mu, y[i] + dy, xerr=[[mu - lo], [hi - mu]], fmt=m, color=c, ms=4, lw=0.8, capsize=1.5,
                        mfc="white" if m == "s" else c)
    a.axvline(0, color="k", lw=0.6)
    for ax in (a, b):
        for yy in (3.5, 7.5):
            ax.axhline(yy, color="0.75", lw=0.5)
    a.set(yticks=y, yticklabels=lab, xlabel="Bias of predicted Δz (δ)")
    b.plot([], [], "o", color=OK["blue"], label="all ladder steps")
    b.plot([], [], "s", color=OK["verm"], mfc="white", label="|Δz| ≤ 0.45 δ")
    b.axvline(1.0, color="k", lw=0.8, ls="--")
    b.set(xlabel="MAE (δ)", xlim=(0, 1.05))
    b.legend(loc="lower right")
    tag(a, "(a)"); tag(b, "(b)")
    save(fig, out, "fig6_m6_illuminant")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=R / "figures")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for fn in (fig1_m3, fig2_lab, fig3_m2, fig4_m7, fig5_m8, fig6_m6):
        fn(a.out)
        print("ok", fn.__name__)


if __name__ == "__main__":
    main()
