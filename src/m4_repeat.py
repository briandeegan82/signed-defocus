"""M4 repeatability on the lab sweep: what the data can and cannot say.

1. Duplicates. `data/lab_images/archives/duplicates` holds three raw frames (file steps 146, 148, 150,
   i.e. steps 73-75). Each is compared byte-for-byte with the frame of the same step in
   `data/lab_images/raw`. If they are identical they are copies, not repeat exposures, and give no
   frame-to-frame repeatability.
2. Within-frame sampling uncertainty (a proxy, not temporal repeatability). On the calibration split
   only (every fourth step, left chart half; protocol section 2), each frame's chromatic cue c is the
   median of its patches' `ch_ten_rb`. Resampling the patches with replacement gives the standard error
   of that median. Dividing by the local slope |dc/ds| of the calibration through-focus curve (a line
   fitted over the calibration frames within +-8 steps) converts
   it to steps, then to δ (0.154 δ per step, `results/lab_sweep/LAB_SWEEP.md`). Sensor noise between
   exposures is not in this number; only repeat exposures can measure it.

    python src/m4_repeat.py --estimator ~/blur_study --out results/m4_repeat
"""
import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from lab_sweep import CHART_X_MID

DELTA_PER_STEP = 0.154
CAL_STEPS = range(0, 80, 4)
N_BOOT = 2000
SLOPE_HALF = 8
SEED = 20261124


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def duplicates(root):
    rows = []
    for p in sorted((root / "archives" / "duplicates").glob("*.raw")):
        file_step = int(p.stem.split("__")[-1].split("-")[0])
        raw = root / "raw" / f"{file_step}-0.raw"
        rows.append(dict(file=p.name, file_step=file_step, step=file_step // 2, raw_match=raw.name,
                         sha256_dup=sha256(p), sha256_raw=sha256(raw) if raw.exists() else "",
                         identical=raw.exists() and sha256(p) == sha256(raw)))
    return pd.DataFrame(rows)


def sampling(feat_path):
    d = pd.read_parquet(feat_path, columns=["ch_ten_rb", "step", "px"])
    d["s"] = d.step // 2
    d = d[d.s.isin(CAL_STEPS) & (d.px + 64 < CHART_X_MID)]
    rng = np.random.default_rng(SEED)
    rows = []
    for s, g in d.groupby("s"):
        x = g.ch_ten_rb.dropna().values
        b = np.median(x[rng.integers(0, len(x), (N_BOOT, len(x)))], axis=1)
        rows.append(dict(s=int(s), n_patches=len(x), c=float(np.median(x)), se_c=float(b.std(ddof=1))))
    t = pd.DataFrame(rows).sort_values("s")
    t["slope_c_per_step"] = [np.polyfit(t.s[(t.s - s).abs() <= SLOPE_HALF], t.c[(t.s - s).abs() <= SLOPE_HALF], 1)[0]
                             for s in t.s]
    t["se_steps"] = t.se_c / t.slope_c_per_step.abs()
    t["se_delta"] = t.se_steps * DELTA_PER_STEP
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--estimator", type=Path, required=True, help="blur_study root")
    ap.add_argument("--out", type=Path, default=Path("results/m4_repeat"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    dup = duplicates(a.estimator / "data" / "lab_images")
    dup.to_csv(a.out / "duplicates_check.csv", index=False)
    t = sampling(a.estimator / "results" / "lab_feat_real_all.parquet")
    t.round(6).to_csv(a.out / "sampling_se_calibration.csv", index=False)
    print(dup[["file", "step", "identical"]].to_string(index=False))
    print(t.round(4).to_string(index=False))
    print("median se_delta:", round(t.se_delta.median(), 4), "max", round(t.se_delta.max(), 4))


if __name__ == "__main__":
    main()
