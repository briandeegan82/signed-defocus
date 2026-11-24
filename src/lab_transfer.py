"""Exploratory, after the method freeze: separate chart-half transfer from step interpolation in the lab test.

The held-out test split (right chart half, steps s mod 4 != 0) differs from the calibration split (left half,
s mod 4 == 0) in both chart half and focus step, so its near-focus failure cannot be attributed to either.
This script applies the frozen `calibration`-level rule of `lab_test.py` (threshold, sign and through-focus
curve fitted on the left-half calibration steps, unchanged) to the two lab subsets that change one factor only:

  other_half   right half, calibration steps (s mod 4 == 0): chart half changes, steps do not.
  other_steps  left half, non-calibration steps (s mod 4 != 0): steps change, chart half does not.

Neither subset overlaps the test split, which is not re-evaluated; its row is read from the committed
`results/lab_test/lab_test_frames.csv`. The in-sample row (left half, calibration steps) is for reference.
The cue offset between halves is the median over the 20 calibration steps of right-half c minus left-half c.
Also reported: the threshold a refit on the right-half calibration steps alone would choose. Bands split
frames at |Δz| = 2 δ. Truth, frame
pooling, abstention and metrics are as in `lab_test.py`. Consecutive steps of one static sweep are not
independent samples, so no intervals are given.

  python src/lab_transfer.py --estimator ~/blur_study --out results/lab_transfer
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import lab_test as LT

R = Path(__file__).resolve().parents[1] / "results"
NEAR = 2.0


def rows(name, f, d, dz_hat):
    sc = f.dz_delta.abs() > 0.5 * LT.DELTA_PER_STEP
    out = []
    use = f.n_patches >= LT.MIN_PATCHES
    for band, m in (("all", use), ("within_2d", use & (f.dz_delta.abs() < NEAR)), ("beyond_2d", use & (f.dz_delta.abs() >= NEAR))):
        e = (dz_hat - f.dz_delta)[m]
        ok = (d == np.sign(f.dz_delta))[m & sc]
        out.append(dict(subset=name, band=band, n_direction=int(len(ok)), direction_ok=int(ok.sum()),
                        direction_acc=ok.mean() if len(ok) else np.nan,
                        bias_delta=e.mean(), mae_delta=e.abs().mean()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results/lab_transfer"))
    a = ap.parse_args()
    p = LT.patches(a.estimator / "results" / "lab_feat_real_all.parquet")
    cal_steps, other_steps = list(range(0, 80, 4)), [s for s in range(80) if s % 4]
    cal = LT.frames(p, cal_steps, "left")
    c0, sgn = LT.fit_dir(cal.c, cal.dz_delta)
    cv = LT.curve_steps(cal)

    subsets = {"in_sample": cal, "other_half": LT.frames(p, cal_steps, "right"),
               "other_steps": LT.frames(p, other_steps, "left")}
    res, fr = [], []
    for name, f in subsets.items():
        d = sgn * np.sign(f.c - c0)
        dz = (LT.invert_steps(cv, f[["c", "lum"]].values) - LT.S_G) * LT.DELTA_PER_STEP
        res += rows(name, f, d, dz)
        fr.append(f.assign(subset=name, dir=d, dz_hat=dz))
    t = pd.read_csv(R / "lab_test/lab_test_frames.csv")
    res += rows("test_split_committed", t, t.dir_calibration, t.dz_calibration)

    right_cal = subsets["other_half"]
    off = right_cal.set_index("s").c - cal.set_index("s").c
    c0_right, sgn_right = LT.fit_dir(right_cal.c, right_cal.dz_delta)
    near = off[(off.index.to_series() - LT.S_G).abs() * LT.DELTA_PER_STEP < NEAR]
    extra = pd.DataFrame([dict(c0_left=c0, sign_left=sgn, c0_right_refit=c0_right, sign_right_refit=sgn_right,
                               cue_offset_median=off.median(), cue_offset_median_within_2d=near.median(),
                               n_steps_within_2d=len(near))])
    a.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(res).round(4).to_csv(a.out / "lab_transfer_summary.csv", index=False)
    pd.concat(fr)[["subset", "s", "c", "lum", "n_patches", "dz_delta", "dir", "dz_hat"]].round(5).to_csv(
        a.out / "lab_transfer_frames.csv", index=False)
    extra.round(5).to_csv(a.out / "lab_transfer_offsets.csv", index=False)
    print(pd.DataFrame(res).round(3).to_string(index=False))
    print(extra.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
