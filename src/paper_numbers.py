"""Write paper/numbers.tex: every number the paper reports, as LaTeX macros, from the committed result CSVs.

Do not edit numbers.tex by hand; rerun `python src/paper_numbers.py` after any result changes.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[1] / "results"


def f(x, nd=2):
    return f"{x:.{nd}f}"


def numbers():
    n = {}
    p2, ga = pd.read_csv(R / "phase2/phase2_summary.csv"), pd.read_csv(R / "phase2/phase2_gate_a.csv").iloc[0]
    n["MthreeNlenses"] = int(ga.n_lenses)
    n["MthreeNframes"] = int(p2.n_frames.iloc[0])
    n["MthreeRho"] = f(ga.spearman_rho)
    n["MthreeTau"] = f(ga.kendall_tau)
    gb = p2[p2.gate_b_applies.astype(str) == "True"]
    n["MthreeGateBN"] = len(gb)
    n["MthreeGateBMaeMin"], n["MthreeGateBMaeMax"] = f(gb.mae_delta.min()), f(gb.mae_delta.max())
    z = p2.set_index("lens")
    n["MthreeZeroDir"], n["MthreeZeroSaDir"] = f(z.loc["m3_z000", "dir_acc"]), f(z.loc["m3_z000_sa", "dir_acc"])
    q = p2[p2.lca_over_delta == 0.25]
    n["MthreeQuarterDirMin"], n["MthreeQuarterDirMax"] = f(q.dir_acc.min()), f(q.dir_acc.max())
    n["MthreeQuarterMaeMin"], n["MthreeQuarterMaeMax"] = f(q.mae_delta.min()), f(q.mae_delta.max())
    ref = R / "phase2/lenses/m3_ref"
    e = pd.read_csv(ref / "m2_displacement.csv")
    c = e[(e.train == "continuous") & (e.band == "all")].iloc[0]
    n["MtwoN"] = int(c.n)
    n["MtwoMaeUm"], n["MtwoMaeDelta"], n["MtwoPninetyDelta"] = f(c.mae_um, 1), f(c.mae_delta), f(c.p90_delta)
    d = pd.read_csv(ref / "m2_direction.csv")
    d = d[d.level == "fitted"].set_index("band")
    n["MtwoDirAll"], n["MtwoDirNear"] = f(d.loc["all", "acc"]), f(d.loc["[0.0, 0.5)", "acc"])
    s2 = pd.read_csv(R / "m2_gate/m2_displacement.csv")
    s2 = s2[s2.band == "all"].set_index("train")
    n["MtwoSubsetN"] = int(s2.loc["continuous", "n"])
    n["MtwoSubsetMaeDelta"], n["MtwoSubsetLadderMaeDelta"] = f(s2.loc["continuous", "mae_delta"]), f(s2.loc["ladder", "mae_delta"])
    st = pd.read_csv(R / "lab_sweep/step_size_fits.csv").iloc[0]
    n["LabStepUm"] = f(st.k)
    n["LabDeltaPerStep"] = f(st.k / (2 * 2.0 * 3.45), 3)
    n["LabLcaDelta"] = f(st.lca_rb_over_delta)
    b = pd.read_csv(R / "lab_sweep/baseline_calibration_frames.csv")
    nz = b[b.dz_steps.abs() > 0.5]
    n["LabCalDirOk"], n["LabCalDirN"] = int(nz.dir_ok.sum()), len(nz)
    n["LabCalMaeDelta"] = f((b.dz_hat_steps - b.dz_steps).abs().mean() * st.k / (2 * 2.0 * 3.45))
    m7 = pd.read_csv(R / "m7_field/m7_summary.csv").set_index(["render", "zone"])
    zc = pd.read_csv(R / "m7_field/m7_zonecal.csv").set_index("zone")
    for zone in ("centre", "mid", "corner"):
        Z = zone.title()
        n[f"MsevenUni{Z}Dir"] = f(m7.loc[("uniform", zone), "direction_acc"])
        n[f"MsevenFv{Z}Dir"] = f(m7.loc[("field-varying", zone), "direction_acc"])
        n[f"MsevenFv{Z}DirLocal"] = f(m7.loc[("field-varying", zone), "direction_acc_local"])
        n[f"MsevenFv{Z}Bias"] = f(m7.loc[("field-varying", zone), "bias_dz"], 3)
        n[f"MsevenZc{Z}Dir"] = f(zc.loc[zone, "direction_acc"])
        n[f"MsevenZc{Z}Bias"] = f(zc.loc[zone, "bias_dz"], 3)
    s4 = pd.read_csv(R / "m4_repeat/sampling_se_calibration.csv")
    n["MfourSeMedianDelta"] = f(s4.se_delta.median())
    for lens, tag in (("synth_lcaP", "Strong"), ("laikin", "Weak")):
        m8 = pd.read_csv(R / f"m8_confounds/{lens}/m8_summary.csv").set_index("condition").share_alarm
        n[f"Meight{tag}InFocus"], n[f"Meight{tag}Motion"], n[f"Meight{tag}Fog"] = (
            f(m8["in focus"]), f(m8["motion"]), f(m8["fog"]))
        n[f"Meight{tag}DefocusPos"], n[f"Meight{tag}DefocusNeg"] = f(m8["defocus +0.02"]), f(m8["defocus -0.02"])
    m6 = pd.read_csv(R / "m6_illuminant/m6_summary.csv").set_index("condition")
    n["MsixDirMin"] = f"{np.floor(m6.direction_acc.min() * 100) / 100:.2f}"  # floor: "at or above"
    n["MsixMaeNominal"], n["MsixMaeMax"] = f(m6.loc["nominal", "mae_delta"]), f(m6.mae_delta.max())
    n["MsixShiftBiasMax"] = f(m6.loc[["shift+10", "shift-10", "warm", "cool"], "bias_delta"].abs().max())
    rr = pd.read_csv(R / "reference/reference_rows.csv")
    q = rr[rr.lca_over_delta > 1].pivot(index="lens", columns="method")
    n["RefGateBN"] = len(q)
    n["RefPhysMaeMin"], n["RefPhysMaeMax"] = f(q.mae_delta.physics.min()), f(q.mae_delta.physics.max())
    n["RefLearnMaeMin"], n["RefLearnMaeMax"] = f(q.mae_delta.learned.min()), f(q.mae_delta.learned.max())
    n["RefPhysAbsMin"], n["RefPhysAbsMax"] = f(q.abs_mae_delta.physics.min()), f(q.abs_mae_delta.physics.max())
    for m, tag in (("laplacian", "Lap"), ("tenengrad", "Ten")):
        n[f"Ref{tag}AbsMin"], n[f"Ref{tag}AbsMax"] = f(q.abs_mae_delta[m].min()), f(q.abs_mae_delta[m].max())
    lo = rr[rr.lca_over_delta == 0.25].pivot(index="lens", columns="method")
    n["RefQuarterLearnDirMin"], n["RefQuarterLearnDirMax"] = f(lo.direction_acc.learned.min()), f(lo.direction_acc.learned.max())
    n["RefQuarterLearnMaeMin"], n["RefQuarterLearnMaeMax"] = f(lo.mae_delta.learned.min()), f(lo.mae_delta.learned.max())
    lt = pd.read_csv(R / "lab_test/lab_test_summary.csv").set_index("level")
    for lvl, tag in (("rendered", "Rendered"), ("order", "Order"), ("calibration", "Cal")):
        n[f"LabTest{tag}Ok"], n[f"LabTest{tag}N"] = int(lt.loc[lvl, "direction_ok"]), int(lt.loc[lvl, "n_direction"])
        n[f"LabTest{tag}Dir"] = f(lt.loc[lvl, "direction_acc"])
        n[f"LabTest{tag}CiLo"], n[f"LabTest{tag}CiHi"] = f(lt.loc[lvl, "direction_ci_lo"]), f(lt.loc[lvl, "direction_ci_hi"])
    n["LabTestRenderedMae"], n["LabTestCalMae"] = f(lt.loc["rendered", "mae_delta"]), f(lt.loc["calibration", "mae_delta"])
    n["LabTestCalBias"] = f(lt.loc["calibration", "bias_delta"])
    fr = pd.read_csv(R / "lab_test/lab_test_frames.csv")
    far = fr[fr.dz_delta.abs() >= 2]
    n["LabTestFarDir"] = f((far.dir_calibration == np.sign(far.dz_delta)).mean())
    n["LabTestFarMae"] = f((far.dz_calibration - far.dz_delta).abs().mean())
    return n


def reference_table():
    """Table rows: no-SA designs, mean over the two LCA signs at each LCA/δ."""
    rr = pd.read_csv(R / "reference/reference_rows.csv")
    rr = rr[rr.lens.str.match(r"m3_[zpn]\d{3}$")]
    g = rr.groupby(["lca_over_delta", "method"])[["direction_acc", "mae_delta", "abs_mae_delta"]].mean().unstack()
    lines = [r"\begin{table}[t]\centering\footnotesize",
             r"\caption{Reference rows on the Phase~2 render (no spherical aberration, mean over LCA sign). "
             r"Dir.: direction accuracy; MAE: signed error; $|\Delta z|$: error of the magnitude only, all in $\delta$.}",
             r"\label{tab:ref}\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{rcccccccc}\hline",
             r"LCA/$\delta$ & \multicolumn{3}{c}{Two-feature} & \multicolumn{3}{c}{Learned} & Lapl. & Ten. \\",
             r" & Dir. & MAE & $|\Delta z|$ & Dir. & MAE & $|\Delta z|$ & $|\Delta z|$ & $|\Delta z|$ \\\hline"]
    for lca, r in g.iterrows():
        v = [r[("direction_acc", "physics")], r[("mae_delta", "physics")], r[("abs_mae_delta", "physics")],
             r[("direction_acc", "learned")], r[("mae_delta", "learned")], r[("abs_mae_delta", "learned")],
             r[("abs_mae_delta", "laplacian")], r[("abs_mae_delta", "tenengrad")]]
        lines.append(f"{lca:.2f} & " + " & ".join(f(x) for x in v) + r" \\")
    lines += [r"\hline\end{tabular}\end{table}"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=R.parent / "paper" / "numbers.tex")
    a = ap.parse_args()
    lines = ["% Generated by src/paper_numbers.py from results/*.csv. Do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(numbers().items())]
    a.out.write_text("\n".join(lines) + "\n")
    (a.out.parent / "reference_table.tex").write_text(reference_table())
    print("\n".join(lines))


if __name__ == "__main__":
    main()
