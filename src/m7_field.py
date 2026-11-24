"""M7: does the signed estimate hold off-axis, under field-varying blur?

Rendered part. `robotcar_render_fieldvarying` (defocus-estimator,
`render_arms.py --field-varying`) is the Sony lens's full 9 x 7 field PSF map on
219 RobotCar plates, 9 ladder rungs, pre-ISP arm; features from the frozen
`extract_parallel.extract` (`extract` below). The estimator is calibrated on the
uniform centre-PSF Sony ladder (`rc_feat_robotcar_render_sony_pre_all.parquet`)
of the training traversals, as deployed, and scored on held-out traversals per
field zone: patch medians of (c, log luminance gradient) within each zone of each
frame. Zones by normalised field radius r = |(fy, fx)| / sqrt(2), with fy, fx in
[-1, 1] from the patch centre: centre r < 1/3, mid 1/3-2/3, corner >= 2/3. The
same zones on the uniform render of the same plates are the control (same
content, centre PSF everywhere), so the field-PSF effect is the difference.
Direction truth is the sign of the nominal rung; the zone's own best-focus shift
(peak of mtf025_mean over dz in `field_labels.json`) is reported next to it.
Sony has no recorded f-number or pixel pitch, so DZ stays in ladder units.

Lab part. The 11 chart squares of the 80-step sweep (`lab_sweep_field_mtf.csv`,
raw-plane SFR at 0.125 and 0.25 cy/px): best-focus step per channel, square and
frequency from a parabola in log MTF over +-6 steps of the peak, so the red-blue
LCA per square, in steps and δ (0.154 δ per step, `results/lab_sweep/LAB_SWEEP.md`).

  python src/m7_field.py extract --estimator ~/blur_study --out ~/sd_data/m7
  python src/m7_field.py score --cache ~/blur_study/results --fv ~/sd_data/m7/rc_feat_fieldvarying_sony_pre_all.parquet \\
      --field-labels ~/blur_study/data/raw/robotcar_render_fieldvarying/field_labels.json \\
      --lab-field ~/blur_study/results/lab_sweep_field_mtf.csv --out results/m7_field
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import physics_baseline as PB

H, W, PATCH = 958, 1280, 128
ZONES = [("centre", 0.0, 1 / 3), ("mid", 1 / 3, 2 / 3), ("corner", 2 / 3, 9.0)]
DELTA_PER_STEP = 0.154


def zone_of(r):
    return np.select([r < 1 / 3, r < 2 / 3], ["centre", "mid"], "corner")


def zone_table(path):
    d = pd.read_parquet(path, columns=["ch_ten_rb", "cx_grad_mean", "dz", "traversal", "stem", "py", "px"])
    fy = (d.py + PATCH / 2 - H / 2) / (H / 2)
    fx = (d.px + PATCH / 2 - W / 2) / (W / 2)
    d["zone"] = zone_of(np.hypot(fy, fx) / np.sqrt(2))
    d["lum"] = np.log(d["cx_grad_mean"] + 1e-9)
    z = d.groupby(["traversal", "stem", "dz", "zone"], as_index=False).agg(
        c=("ch_ten_rb", "median"), lum=("lum", "median"), n_patch=("lum", "size"))
    return z


def peak(x, y, half=None):
    """Best-focus position: vertex of a parabola fitted to log y within +-half of the
    maximum of the 3-point running mean (the five nearest points if half is None)."""
    ys = np.convolve(y, np.ones(3) / 3, "same")
    i = int(np.argmax(ys[1:-1])) + 1
    m = np.abs(x - x[i]) <= half if half else np.abs(np.arange(len(x)) - i) <= 2
    a, b, _ = np.polyfit(x[m], np.log(np.clip(y[m], 1e-4, None)), 2)
    return float(-b / (2 * a)) if a < 0 else float(x[i])


def peak_dz(x, y):
    """Vertex of a parabola in log y through the ladder rung at the maximum and its two neighbours."""
    i = int(np.clip(np.argmax(y), 1, len(y) - 2))
    a, b, _ = np.polyfit(x[i - 1:i + 2], np.log(np.clip(y[i - 1:i + 2], 1e-4, None)), 2)
    return float(-b / (2 * a)) if a < 0 else float(x[int(np.argmax(y))])


def field_focus(path):
    rows = pd.DataFrame(json.loads(Path(path).read_text()))
    rows["zone"] = zone_of(rows.field_h / np.sqrt(2))
    out = []
    for (gy, gx), g in rows.groupby(["gy", "gx"]):
        g = g.sort_values("dz")
        out.append(dict(gy=gy, gx=gx, zone=g.zone.iloc[0], field_h=g.field_h.iloc[0],
                        **{f"peak_dz_{c}": peak_dz(g.dz.values, g[f"mtf025_{c}"].values) for c in ("mean", "r", "g", "b")}))
    return pd.DataFrame(out)


def lab_squares(path):
    d = pd.read_csv(path)
    d["s"] = d.step / 2 if d.step.max() > 79 else d.step
    out = []
    for (sq, zone), g in d.groupby(["square_id", "zone"]):
        g = g.sort_values("s")
        for f in ("0125", "025"):
            r = dict(square_id=sq, zone=zone, field_r=g.field_r.iloc[0], freq_cy_px=int(f) / 10 ** (len(f) - 1))
            for c in ("r", "g", "b"):
                r[f"s0_{c}"] = peak(g.s.values, g[f"mtf{f}_{c}"].values, half=6)
            r["lca_rb_steps"] = r["s0_r"] - r["s0_b"]
            r["lca_rb_delta"] = r["lca_rb_steps"] * DELTA_PER_STEP
            out.append(r)
    return pd.DataFrame(out)


def extract(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import extract_parallel as EP
    root = a.estimator / "data" / "raw" / "robotcar_render_fieldvarying"
    lab = {round(r["dz"], 4): {"mtf025_mean": r["mtf025_mean"], "mtf025_g": r["mtf025_g"]}
           for r in json.loads((root / "labels.json").read_text())}
    a.out.mkdir(parents=True, exist_ok=True)
    EP.extract(str(root), "pre", lab, a.workers).to_parquet(a.out / "rc_feat_fieldvarying_sony_pre_all.parquet", index=False)


def score(a):
    uni_frames = PB.frame_table(a.cache / "rc_feat_robotcar_render_sony_pre_all.parquet")
    uni = zone_table(a.cache / "rc_feat_robotcar_render_sony_pre_all.parquet")
    fv = zone_table(a.fv)
    keys = set(map(tuple, fv[["traversal", "stem"]].drop_duplicates().values))
    uni = uni[[k in keys for k in zip(uni.traversal, uni.stem)]]
    fmap = PB.folds(uni_frames.traversal.unique())
    for t in (uni_frames, uni, fv):
        t["fold"] = t.traversal.map(fmap)
    dir_rows, dz_rows = [], []
    for k in range(PB.N_FOLDS):
        tr = uni_frames[uni_frames.fold != k]
        c0, s = PB.fit_direction(tr)
        for render, z in (("uniform", uni), ("field-varying", fv)):
            te = z[(z.fold == k) & (z.dz != 0)]
            ok = s * np.sign(te.c - c0) == np.sign(te.dz)
            dir_rows.append(te.assign(render=render, ok=ok.values)[["render", "zone", "dz", "fold", "ok"]])
        for dz_out in sorted(uni_frames.dz.unique())[1:-1]:
            curve = PB.through_focus_curve(tr[tr.dz != dz_out])
            for render, z in (("uniform", uni), ("field-varying", fv)):
                te = z[(z.fold == k) & (z.dz == dz_out)]
                err = PB.invert(curve, te[["c", "lum"]].values) - dz_out
                dz_rows.append(pd.DataFrame(dict(render=render, zone=te.zone.values, dz=dz_out, fold=k, err_dz=err)))
    dr, er = pd.concat(dir_rows), pd.concat(dz_rows)
    ff = field_focus(a.field_labels)
    a.out.mkdir(parents=True, exist_ok=True)
    ff.to_csv(a.out / "sony_field_focus.csv", index=False)
    summ = dr.groupby(["render", "zone"]).ok.agg(direction_acc="mean", n="size").join(
        er.groupby(["render", "zone"]).err_dz.agg(mae_dz=lambda x: x.abs().mean(),
                                                   p90_dz=lambda x: x.abs().quantile(0.9), bias_dz="mean"))
    fz = ff.groupby("zone")[["peak_dz_mean", "peak_dz_r", "peak_dz_b"]].mean()
    fz["lca_rb_dz"] = fz.peak_dz_r - fz.peak_dz_b
    summ = summ.join(fz, on="zone")
    summ.to_csv(a.out / "m7_summary.csv")
    dr.groupby(["render", "zone", "dz"]).ok.mean().unstack("dz").to_csv(a.out / "m7_direction_by_dz.csv")
    print(summ.round(4).to_string())
    if a.lab_field:
        lab = lab_squares(a.lab_field)
        lab.to_csv(a.out / "lab_squares_focus.csv", index=False)
        print(lab.round(2).to_string(index=False))
        print(lab.groupby(["freq_cy_px", "zone"])[["s0_r", "s0_g", "s0_b", "lca_rb_steps", "lca_rb_delta"]].mean().round(2).to_string())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--estimator", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--workers", type=int, default=6)
    s = sub.add_parser("score")
    s.add_argument("--cache", type=Path, required=True, help="defocus-estimator results/")
    s.add_argument("--fv", type=Path, required=True)
    s.add_argument("--field-labels", type=Path, required=True)
    s.add_argument("--lab-field", type=Path, default=None)
    s.add_argument("--out", type=Path, default=Path("results/m7_field"))
    a = ap.parse_args()
    extract(a) if a.cmd == "extract" else score(a)


if __name__ == "__main__":
    main()
