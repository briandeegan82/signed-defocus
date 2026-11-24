"""Held-out lab test (protocol section 2, RQ3): evaluated once, with the method frozen at tag
`method-freeze-v1`. Nothing here was tuned on the test split; the plan below was committed first.

Test split: the 60 steps not in the calibration set (s mod 4 != 0) on the right chart half
(patch px >= CHART_X_MID), from `blur_study/results/lab_feat_real_all.parquet`. Frame features are the
medians over the frame's patches of `ch_ten_rb` (c) and log `cx_grad_mean` (lum). A frame with fewer
than 10 patches abstains and is counted, not dropped.

Truth: Δz = (s - s_g) * 0.154 δ, with s_g = 46.20 the green best-focus step of the calibration-step MTF
fit (`results/lab_sweep/step_size_fits.csv`, primary row), positive towards higher steps. Frames within
0.5 steps of s_g have no direction truth and are left out of direction accuracy.

Three calibration levels:
  rendered     No lab data. Direction rule (threshold c0, sign) and through-focus curve over (c, lum)
               fitted on the M5a lab-matched render `m5_lab` (all 1,960 frames, nominal Δz). M5a is
               the lab lens mirrored along z, so lab Δz = -rendered Δz (DZ -> δ: x 1000 / 22).
  order        Sign from the lens's channel order only, carried by the M5a mirror mapping as in
               `rendered`; threshold c0 fitted on the calibration split. Direction only.
  calibration  Threshold, sign and through-focus curve fitted on the calibration split (every fourth
               step, left half), as `lab_sweep.baseline_calibration` but applied to the test split.
               Test steps above the last calibration step (77-79) are scored; the curve is not
               extrapolated, so they are expected to saturate.
Metrics: direction accuracy (with a 95% Wilson interval), displacement bias, MAE and p90 in δ, and
direction accuracy per field zone (frame medians within normalised field radius r < 1/3, 1/3-2/3,
>= 2/3 of the 4096 x 2160 sensor, as M7) at the `calibration` level.

  python src/lab_test.py --estimator ~/blur_study --m5 ~/sd_data/m5 --out results/lab_test
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import physics_baseline as PB
from lab_sweep import CHART_X_MID

DELTA_PER_STEP = 0.154
S_G = 46.1995
DELTA_UM, UM_PER_DZ = 22.0, 1000.0
H, W, PATCH = 2160, 4096, 128
MIN_PATCHES = 10
ZONES = ("centre", "mid", "corner")


def patches(feat_path):
    d = pd.read_parquet(feat_path, columns=["ch_ten_rb", "cx_grad_mean", "step", "px", "py"])
    d["s"] = d.step // 2
    d["lum"] = np.log(d.cx_grad_mean + 1e-9)
    fy, fx = (d.py + PATCH / 2 - H / 2) / (H / 2), (d.px + PATCH / 2 - W / 2) / (W / 2)
    r = np.hypot(fy, fx) / np.sqrt(2)
    d["zone"] = np.select([r < 1 / 3, r < 2 / 3], ["centre", "mid"], "corner")
    return d


def frames(p, steps, half, by=("s",)):
    m = p[p.s.isin(steps) & ((p.px + 64 < CHART_X_MID) if half == "left" else (p.px >= CHART_X_MID))]
    f = m.groupby(list(by)).agg(c=("ch_ten_rb", "median"), lum=("lum", "median"), n_patches=("lum", "size")).reset_index()
    f["dz_delta"] = (f.s - S_G) * DELTA_PER_STEP
    return f


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def fit_dir(c, z):
    return PB.fit_direction(pd.DataFrame(dict(c=c, dz=z)))


def curve_steps(cal):
    grid = np.linspace(cal.s.min(), cal.s.max(), 2001)
    sd = cal[["c", "lum"]].std().values
    pts = np.column_stack([np.interp(grid, cal.s, cal[k]) for k in ("c", "lum")]) / sd
    return grid, pts, sd


def invert_steps(cv, x):
    grid, pts, sd = cv
    return grid[np.argmin((((x / sd)[:, None, :] - pts[None]) ** 2).sum(-1), axis=1)]


def score(name, te, pred_dir, dz_hat):
    ok = te.dz_delta.abs() > 0.5 * DELTA_PER_STEP
    n_abst = int((te.n_patches < MIN_PATCHES).sum())
    valid = ok & (te.n_patches >= MIN_PATCHES)
    k, n = int((pred_dir[valid] == np.sign(te.dz_delta[valid])).sum()), int(valid.sum())
    lo, hi = wilson(k, n)
    row = dict(level=name, n_frames=len(te), n_abstain=n_abst, n_direction=n, direction_ok=k,
               direction_acc=k / n if n else np.nan, direction_ci_lo=lo, direction_ci_hi=hi)
    if dz_hat is not None:
        e = (dz_hat - te.dz_delta)[te.n_patches >= MIN_PATCHES]
        row.update(bias_delta=e.mean(), mae_delta=e.abs().mean(), p90_delta=e.abs().quantile(0.9))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--m5", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results/lab_test"))
    a = ap.parse_args()
    p = patches(a.estimator / "results" / "lab_feat_real_all.parquet")
    cal_steps, test_steps = range(0, 80, 4), [s for s in range(80) if s % 4]
    cal, te = frames(p, cal_steps, "left"), frames(p, test_steps, "right")
    rf = PB.frame_table(a.m5 / "rc_feat_m5_lab_pre_all.parquet")
    rows, out = [], te.copy()

    c0, s = PB.fit_direction(rf)
    cv = PB.through_focus_curve(rf)
    out["dir_rendered"] = -s * np.sign(te.c - c0)
    out["dz_rendered"] = -PB.invert(cv, te[["c", "lum"]].values) * UM_PER_DZ / DELTA_UM
    rows.append(score("rendered", te, out.dir_rendered, out.dz_rendered))

    sgn = -s
    c0_cal = PB.fit_offset(pd.DataFrame(dict(c=cal.c, dz=cal.dz_delta)), sgn)
    out["dir_order"] = sgn * np.sign(te.c - c0_cal)
    rows.append(score("order", te, out.dir_order, None))

    c0c, sc = fit_dir(cal.c, cal.dz_delta)
    out["dir_calibration"] = sc * np.sign(te.c - c0c)
    out["dz_calibration"] = (invert_steps(curve_steps(cal), te[["c", "lum"]].values) - S_G) * DELTA_PER_STEP
    rows.append(score("calibration", te, out.dir_calibration, out.dz_calibration))

    summ = pd.DataFrame(rows)
    zt = frames(p, test_steps, "right", by=("s", "zone"))
    zt["dir"] = sc * np.sign(zt.c - c0c)
    zrows = []
    for zone in ZONES:
        g = zt[zt.zone == zone].reset_index(drop=True)
        r = score(f"calibration, {zone}", g, g.dir, None)
        r["patches_per_frame"] = g.n_patches.median()
        zrows.append(r)
    a.out.mkdir(parents=True, exist_ok=True)
    summ.round(4).to_csv(a.out / "lab_test_summary.csv", index=False)
    pd.DataFrame(zrows).round(4).to_csv(a.out / "lab_test_zones.csv", index=False)
    out.round(5).to_csv(a.out / "lab_test_frames.csv", index=False)
    pd.DataFrame([dict(rendered_c0=c0, rendered_sign=s, order_c0=c0_cal, order_sign=sgn,
                       calibration_c0=c0c, calibration_sign=sc)]).round(6).to_csv(a.out / "lab_test_rules.csv", index=False)
    print(summ.round(3).to_string(index=False))
    print(pd.DataFrame(zrows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
