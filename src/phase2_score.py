"""Phase 2 scoring: every M3 design on every RobotCar plate at 8 continuous displacements.

Render: `src/phase2_render.sh` (`m2_continuous.py render --n-plates 0 --k 8` per design in
data/m3_lenses.csv). Each lens is scored with `m2_continuous.score` (traversal-disjoint five folds;
direction with sign and offset fitted on training traversals; displacement from the through-focus
curve of training frames binned at 0.01 DZ). Draws are rounded to 1e-4 DZ, so a test frame can share its
displacement with a training frame of another plate; `mae_delta_unseen` scores only the test frames whose
displacement occurs in no training fold, as the protocol's "Δz absent from training". Then, over lenses,
Gate A (Spearman rho of direction accuracy against LCA/δ, one-sided) and Gate B (MAE < 1 δ for
LCA/δ > 1), as `rescore_dof.gate_a`. Per-frame CSVs are kept for m3_ref (the synth_lcaP copy) only.

  python src/phase2_score.py --cache ~/sd_data/phase2 --out results/phase2
"""
import argparse
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import m2_continuous as M2
from rescore_dof import gate_a

HERE = Path(__file__).resolve().parent.parent


def unseen(out):
    """MAE (δ) over test frames whose rounded Δz is in no training fold."""
    f = pd.read_csv(out / "m2_displacement_frames.csv")
    f = f[f.train == "continuous"]
    seen = pd.Series(False, index=f.index)
    for k, g in f.groupby("fold"):
        seen[g.index] = g.dz.round(4).isin(f[f.fold != k].dz.round(4))
    u = f[~seen]
    return dict(n_unseen=len(u), mae_delta_unseen=u.err_delta.abs().mean(), p90_delta_unseen=u.err_delta.abs().quantile(0.9))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results/phase2"))
    a = ap.parse_args()
    lenses = pd.read_csv(HERE / "data" / "m3_lenses.csv")
    lca = pd.read_csv(HERE / "data" / "m3_lca.csv").set_index("lens")
    delta = 2.0 * M2.BASE["f_number"] * M2.BASE["pixel_pitch"]
    rows, missing = [], []
    for r in lenses.itertuples():
        feat = a.cache / f"rc_feat_m2_{r.lens}_pre_all.parquet"
        if not feat.exists():
            missing.append(r.lens)
            continue
        out = a.out / "lenses" / r.lens
        M2.score(SimpleNamespace(cache=feat, ladder=None, out=out, bin=0.01, lens=r.lens, long_ca=r.long_ca_mm_per_um,
                                 **{k: M2.BASE[k] for k in ("f_number", "pixel_pitch", "defocus_scale")}))
        d, e = pd.read_csv(out / "m2_direction.csv"), pd.read_csv(out / "m2_displacement.csv")
        fit = d[d.level == "fitted"].set_index("band")
        cont = e[e.train == "continuous"].set_index("band")
        rows.append(dict(lens=r.lens, spherical=r.spherical, lca_rb_um=lca.loc[r.lens, "lca_spread_um"],
                         lca_over_delta=round(lca.loc[r.lens, "lca_spread_um"] / delta, 4),
                         n_frames=int(fit.loc["all", "n"]), dir_acc=fit.loc["all", "acc"],
                         dir_acc_within_half_delta=fit.loc["[0.0, 0.5)", "acc"],
                         mae_delta=cont.loc["all", "mae_delta"], p90_delta=cont.loc["all", "p90_delta"],
                         bias_um=cont.loc["all", "bias_um"], mae_um=cont.loc["all", "mae_um"], **unseen(out)))
        if r.lens != "m3_ref":
            for f in out.glob("*_frames.csv"):
                f.unlink()
    s = pd.DataFrame(rows).sort_values(["lca_over_delta", "lens"], ascending=[False, True], kind="mergesort")
    s["gate_b_applies"] = s.lca_over_delta > 1.0
    s["gate_b_pass"] = np.where(s.gate_b_applies, s.mae_delta < 1.0, pd.NA)
    s["gate_b_pass_unseen"] = np.where(s.gate_b_applies, s.mae_delta_unseen < 1.0, pd.NA)
    a.out.mkdir(parents=True, exist_ok=True)
    s.round(4).to_csv(a.out / "phase2_summary.csv", index=False)
    g = gate_a(s.set_index("lens"))
    g["missing_lenses"] = ";".join(missing)
    g.round(4).to_csv(a.out / "phase2_gate_a.csv", index=False)
    print(s.round(3).to_string(index=False))
    print(g.to_string(index=False))


if __name__ == "__main__":
    main()
