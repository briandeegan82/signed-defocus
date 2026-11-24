"""M8: do in-focus motion blur and fog trigger false signed-defocus alarms?

Inputs (defocus-estimator caches, pre-ISP RobotCar, Laikin centre PSF):
  rc_feat_robotcar_render_laikin_pre_all.parquet   the 9-rung focus ladder
  rc_feat_confound_{motion,fog}.parquet           in-focus (DZ = 0) frames with
      5.75 px motion blur at 20 deg, or fog at transmission 0.934, both matched in
      90th-percentile gradient to a DZ = +0.02 defocus (`confound_robotcar.py`)
The confound frames are the same 245 plates as the ladder.

The physics baseline (`physics_baseline.py`: frame medians of the red/blue
Tenengrad ratio c and log luminance gradient) is calibrated on the ladder of the
training traversals and applied to the held-out traversals' frames under each
condition: in focus (DZ 0), defocus DZ -0.02 and +0.02, motion, fog. Five
traversal-disjoint folds. DZ is the nominal ladder unit: Laikin has no recorded
f-number or pixel pitch, so nothing here is in µm or δ.

Reported per condition: median predicted DZ; share predicted positive; share with
|predicted DZ| >= 0.01 (one rung); share above the 95th percentile of |predicted
DZ| on the in-focus frames of the same fold (the "alarm" threshold).

  python src/m8_confounds.py --cache ~/blur_study/results --out results/m8_confounds
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import physics_baseline as PB

LENS = "laikin"
MATCH_DZ = 0.02


def conf_table(path, cond):
    d = pd.read_parquet(path, columns=["ch_ten_rb", "cx_grad_mean", "traversal", "stem"])
    d["lum"] = np.log(d["cx_grad_mean"] + 1e-9)
    f = d.groupby(["traversal", "stem"], as_index=False)[["ch_ten_rb", "lum"]].median()
    return f.rename(columns={"ch_ten_rb": "c"}).assign(condition=cond, dz=0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results/m8_confounds"))
    a = ap.parse_args()
    lad = PB.frame_table(a.cache / f"rc_feat_robotcar_render_{LENS}_pre_all.parquet")
    conf = pd.concat([conf_table(a.cache / f"rc_feat_confound_{c}.parquet", c) for c in ("motion", "fog")])
    fmap = PB.folds(lad.traversal.unique())
    lad["fold"], conf["fold"] = lad.traversal.map(fmap), conf.traversal.map(fmap)
    named = {0.0: "in focus", -MATCH_DZ: "defocus -0.02", MATCH_DZ: "defocus +0.02"}
    rows = []
    for k in range(PB.N_FOLDS):
        tr = lad[lad.fold != k]
        c0, s = PB.fit_direction(tr)
        curve = PB.through_focus_curve(tr)
        te = pd.concat([lad[(lad.fold == k) & lad.dz.isin(named)].assign(condition=lambda x: x.dz.map(named)),
                        conf[conf.fold == k]])
        te = te.assign(fold=k, dir_pred=s * np.sign(te.c - c0), dz_pred=PB.invert(curve, te[["c", "lum"]].values))
        thr = np.quantile(np.abs(te.loc[te.condition == "in focus", "dz_pred"]), 0.95)
        rows.append(te.assign(alarm_thr=thr))
    fr = pd.concat(rows, ignore_index=True)
    a.out.mkdir(parents=True, exist_ok=True)
    fr[["condition", "traversal", "stem", "fold", "c", "lum", "dir_pred", "dz_pred", "alarm_thr"]].to_csv(
        a.out / "m8_frames.csv", index=False)
    order = ["in focus", "defocus -0.02", "defocus +0.02", "motion", "fog"]
    g = fr.groupby("condition")
    summ = pd.DataFrame(dict(
        n_frames=g.size(),
        median_dz_pred=g.dz_pred.median(),
        share_dir_positive=g.dir_pred.apply(lambda x: (x > 0).mean()),
        share_dz_pred_positive=g.dz_pred.apply(lambda x: (x > 0).mean()),
        share_abs_ge_rung=g.dz_pred.apply(lambda x: (x.abs() >= 0.01 - 1e-9).mean()),
        share_alarm=g.apply(lambda x: (x.dz_pred.abs() > x.alarm_thr).mean(), include_groups=False),
        median_c=g.c.median(), median_lum=g.lum.median(),
    )).reindex(order)
    summ.to_csv(a.out / "m8_summary.csv")
    print(summ.round(3).to_string())


if __name__ == "__main__":
    main()
