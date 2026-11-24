"""Re-score physics baseline v0 in physical units: micrometres and depth of focus.

The v0 results label the render ladder DZ x 1000 as micrometres. It is not: in
`defocus-estimator/src/lens_synth.py` the focus error of a channel is
DZ * defocus_scale + long_ca * (lambda - 0.588 um), in mm. This script converts the
v0 per-fold results of the synthetic lenses, whose optics are in `data/lens_optics.csv`:

  sensor displacement   dz_um = DZ * defocus_scale * 1000
  depth of focus        delta = 2 N c   (protocol section 1)
  LCA, red minus blue   z_r - z_b = -long_ca * (0.656 - 0.486) * 1000 um

The four real-lens banks have no recorded f-number or pixel pitch and are left out.
Direction accuracy is the "fitted" level (sign and offset fitted on training traversals),
the only level v0 scored on every synthetic lens. Inputs are read-only; writes CSVs.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

LAMBDA_R, LAMBDA_B = 0.656, 0.486


def optics_table(path):
    o = pd.read_csv(path).set_index("lens")
    o["delta_um"] = 2.0 * o.f_number * o.pixel_pitch_um
    o["lca_rb_um"] = -o.long_ca_mm_per_um * (LAMBDA_R - LAMBDA_B) * 1000.0
    o["lca_over_delta"] = (o.lca_rb_um.abs() / o.delta_um).round(4)
    o["rung_um"] = 10.0 * o.defocus_scale_mm
    return o


def direction(dirs, o):
    d = dirs[(dirs.level == "fitted") & dirs.lens.isin(o.index)].copy()
    d["dz_um"] = d.dz * 1000.0 * d.lens.map(o.defocus_scale_mm)
    d["dz_over_delta"] = d.dz_um / d.lens.map(o.delta_um)
    d["ok"] = d.n * d.acc
    return d


def summarise(d, dzs, o):
    g = d.groupby("lens")
    acc = g.ok.sum() / g.n.sum()
    fold = d.groupby(["lens", "fold"]).apply(lambda x: x.ok.sum() / x.n.sum(), include_groups=False)
    near = d[d.dz_over_delta.abs() <= 1.0].groupby("lens")
    e = dzs[dzs.lens.isin(o.index)].copy()
    e["err_phys_um"] = e.err_um * e.lens.map(o.defocus_scale_mm)
    e["err_delta"] = e.err_phys_um / e.lens.map(o.delta_um)
    ge = e.groupby("lens")
    out = o[["f_number", "pixel_pitch_um", "delta_um", "defocus_scale_mm", "rung_um",
             "lca_rb_um", "lca_over_delta"]].copy()
    out["dir_acc"] = acc
    out["dir_acc_fold_min"] = fold.groupby("lens").min()
    out["dir_acc_fold_max"] = fold.groupby("lens").max()
    out["dir_acc_within_1delta"] = near.ok.sum() / near.n.sum()
    out["n_frames_within_1delta"] = near.n.sum()
    out["mae_um"] = ge.err_phys_um.apply(lambda x: x.abs().mean())
    out["p90_um"] = ge.err_phys_um.apply(lambda x: x.abs().quantile(0.9))
    out["bias_um"] = ge.err_phys_um.mean()
    out["mae_delta"] = ge.err_delta.apply(lambda x: x.abs().mean())
    out["p90_delta"] = ge.err_delta.apply(lambda x: x.abs().quantile(0.9))
    out["gate_b_applies"] = out.lca_over_delta > 1.0
    out["gate_b_pass"] = np.where(out.gate_b_applies, out.mae_delta < 1.0, pd.NA)
    return out.reset_index().sort_values(["lca_over_delta", "lens"], ascending=[False, True], kind="mergesort").set_index("lens"), e


def gate_a(s):
    s = s.dropna(subset=["dir_acc"])
    rho, p_rho = stats.spearmanr(s.lca_over_delta, s.dir_acc)
    tau, p_tau = stats.kendalltau(s.lca_over_delta, s.dir_acc)
    ordered = s.reset_index().sort_values(["lca_over_delta", "lens"], kind="mergesort").dir_acc.values  # ties by lens name
    p_one = stats.spearmanr(s.lca_over_delta, s.dir_acc, alternative="greater").pvalue
    return pd.DataFrame([dict(n_lenses=len(s), spearman_rho=rho, spearman_p=p_rho, spearman_p_one_sided=p_one,
                              kendall_tau=tau, kendall_p=p_tau,
                              adjacent_inversions=int(np.sum(np.diff(ordered) < 0)),
                              strictly_monotone=bool(np.all(np.diff(ordered) > 0)))])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=Path("results"), help="directory with the v0 CSVs")
    ap.add_argument("--optics", type=Path, default=Path("data/lens_optics.csv"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    a = ap.parse_args()
    o = optics_table(a.optics)
    dirs = pd.read_csv(a.results / "physics_baseline_direction.csv")
    dzs = pd.read_csv(a.results / "physics_baseline_displacement.csv")
    d = direction(dirs, o)
    s, _ = summarise(d, dzs, o)
    ga = gate_a(s)
    a.out.mkdir(parents=True, exist_ok=True)
    s.round(4).to_csv(a.out / "dof_summary.csv")
    ga.round(4).to_csv(a.out / "dof_gate_a.csv", index=False)
    (d.groupby(["lens", "dz", "dz_um", "dz_over_delta"]).apply(
        lambda x: pd.Series(dict(n=x.n.sum(), acc=x.ok.sum() / x.n.sum())), include_groups=False)
        .reset_index().round(4).to_csv(a.out / "dof_direction_by_dz.csv", index=False))
    pd.set_option("display.width", 250)
    print(s.round(3).to_string())
    print(ga.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
