"""M6 (simulation only): illuminant spectrum and white-balance error vs the signed estimate.

Lens: `m3_ref`, an exact copy of synth_lcaP (f/2.0, 5.5 µm, LCA 40 µm = 1.82 δ).
The estimator is calibrated on the defocus-estimator's synth_lcaP 9-rung ladder
(training traversals) and scored on held-out traversals of each condition, all
at the same 9 rungs, on a plate subset (`--n-plates`, round-robin over traversals).

Conditions (`CONDITIONS`), all through the frozen `render_arms.render` pre-ISP arm:
  nominal        defaults; must reproduce the ladder cache (pipeline check)
  shift+10       every channel's effective wavelength +10 nm (warmer light)
  shift-10       every channel -10 nm (cooler light)
  warm           red +5 nm, green +8 nm, blue +15 nm (blue channel's centroid moves most)
  cool           red -10 nm, green -6 nm, blue -5 nm
  wb_r0.8 / wb_r1.25 / wb_b0.8 / wb_b1.25
                 per-plate grey-world red or blue gain scaled by that factor (white-balance error)
The wavelength shifts are parametric stand-ins for an illuminant change: the
effective (sensor x illuminant x scene) centroid of each channel moves, which
moves its focus by long_ca x shift in `lens_synth`. No measured sensor QE or
illuminant spectrum is used.

  python src/m6_illuminant.py render --estimator ~/blur_study --noise-model <json> --out ~/sd_data/m6
  python src/m6_illuminant.py score --cache ~/blur_study/results --m6 ~/sd_data/m6 --out results/m6_illuminant
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import physics_baseline as PB
from m2_continuous import BASE, SYNTH_LCAP_LONG_CA, centre_kernels, pick_plates

LADDER = [-0.1, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.1]
NOMINAL_NM = {"r": 656.0, "g": 588.0, "b": 486.0}
CONDITIONS = {
    "nominal": dict(), "shift+10": dict(nm=(10, 10, 10)), "shift-10": dict(nm=(-10, -10, -10)),
    "warm": dict(nm=(5, 8, 15)), "cool": dict(nm=(-10, -6, -5)),
    "wb_r0.8": dict(wb=(0.8, 1.0)), "wb_r1.25": dict(wb=(1.25, 1.0)),
    "wb_b0.8": dict(wb=(1.0, 0.8)), "wb_b1.25": dict(wb=(1.0, 1.25)),
}
UM_PER_DZ, DELTA_UM = 1000.0, 22.0


def render(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC
    import extract_parallel as EP

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(Path(a.noise_model).read_text())["model"]
    design = dict(BASE, long_ca=SYNTH_LCAP_LONG_CA)
    plates = pick_plates(RC.plate_paths(), a.n_plates)
    LS.DZ_LEVELS = LADDER
    for cond, spec in CONDITIONS.items():
        feat = a.out / f"rc_feat_m6_{cond}_pre_all.parquet"
        if feat.exists():
            continue
        nm = spec.get("nm", (0, 0, 0))
        LS.CHANNELS = {c: (NOMINAL_NM[c] + d) / 1000.0 for c, d in zip("rgb", nm)}
        psfs = centre_kernels(LS.render_psfs(design, device), LADDER)
        root = a.out / cond
        lab = RA.labels(psfs)
        (root).mkdir(parents=True, exist_ok=True)
        (root / "labels.json").write_text(json.dumps(lab, indent=1))
        (root / "condition.json").write_text(json.dumps(dict(spec, channels_um=LS.CHANNELS, n_plates=a.n_plates)))
        gr, gb = spec.get("wb", (1.0, 1.0))
        for t, p in plates:
            plate = RC.load_plate(p)
            w = RA.plate_grey_world(plate)
            wb = (w[0] * gr, w[1] * gb)
            for dz in LADDER:
                d = root / "pre" / f"DZ={dz:g}"
                d.mkdir(parents=True, exist_ok=True)
                img = RA.render(plate, psfs[round(dz, 4)], wb, model, "pre", RA.stable_seed(t, p.stem, dz, 0))
                np.save(d / f"{t}__{p.stem}.npy", img)
        labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
        EP.extract(str(root), "pre", labels, a.workers).to_parquet(feat, index=False)
        print(f"{cond} -> {feat}", flush=True)
    LS.CHANNELS = {c: v / 1000.0 for c, v in NOMINAL_NM.items()}


def score(a):
    lad = PB.frame_table(a.cache / "rc_feat_robotcar_render_synth_lcaP_pre_all.parquet")
    fmap = PB.folds(lad.traversal.unique())
    lad["fold"] = lad.traversal.map(fmap)
    rows = []
    for cond in CONDITIONS:
        f = PB.frame_table(a.m6 / f"rc_feat_m6_{cond}_pre_all.parquet")
        f["fold"] = f.traversal.map(fmap)
        for k in range(PB.N_FOLDS):
            tr, te = lad[lad.fold != k], f[f.fold == k]
            c0, s = PB.fit_direction(tr)
            curve = PB.through_focus_curve(tr)
            rows.append(te.assign(condition=cond, dir_pred=s * np.sign(te.c - c0),
                                  dz_pred=PB.invert(curve, te[["c", "lum"]].values)))
    fr = pd.concat(rows, ignore_index=True)
    fr["err_um"] = (fr.dz_pred - fr.dz) * UM_PER_DZ
    a.out.mkdir(parents=True, exist_ok=True)
    fr.to_csv(a.out / "m6_frames.csv", index=False)
    nz = fr[fr.dz != 0]
    g, gz = fr.groupby("condition"), nz.groupby("condition")
    summ = pd.DataFrame(dict(
        n_frames=g.size(),
        direction_acc=gz.apply(lambda x: (x.dir_pred == np.sign(x.dz)).mean(), include_groups=False),
        direction_acc_near=gz.apply(lambda x: (x.dir_pred == np.sign(x.dz))[x.dz.abs() <= 0.02].mean(), include_groups=False),
        mae_um=g.err_um.apply(lambda x: x.abs().mean()), bias_um=g.err_um.mean(),
        median_c=g.c.median())).reindex(list(CONDITIONS))
    summ["mae_delta"], summ["bias_delta"] = summ.mae_um / DELTA_UM, summ.bias_um / DELTA_UM
    summ.to_csv(a.out / "m6_summary.csv")
    print(summ.round(3).to_string())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--estimator", type=Path, required=True)
    r.add_argument("--noise-model", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--n-plates", type=int, default=60)
    r.add_argument("--workers", type=int, default=4)
    s = sub.add_parser("score")
    s.add_argument("--cache", type=Path, required=True)
    s.add_argument("--m6", type=Path, required=True)
    s.add_argument("--out", type=Path, default=Path("results/m6_illuminant"))
    a = ap.parse_args()
    render(a) if a.cmd == "render" else score(a)


if __name__ == "__main__":
    main()
