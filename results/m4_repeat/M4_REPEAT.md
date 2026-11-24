# M4: repeatability on the lab sweep (minimal)

Command: `python src/m4_repeat.py --estimator ~/blur_study --out results/m4_repeat`. Data: `blur_study/data/lab_images` (raw frames) and `blur_study/results/lab_feat_real_all.parquet` (patch features). Only the calibration split is used (every fourth step, left chart half); the lab test split is untouched.

## The duplicate frames are copies, not repeats

`archives/duplicates` holds three raw frames, file steps 146, 148 and 150 (steps 73–75). Each is byte-identical to the frame of the same step in `raw/` (SHA-256 in `duplicates_check.csv`). They are copies of the sweep frames, so they carry **no frame-to-frame repeatability**. The sweep has one exposure per step, so exposure-to-exposure noise cannot be measured from the existing data.

## Proxy: within-frame sampling uncertainty of the cue

Not repeatability. For each calibration frame, the cue c is the median of its 165 patches' `ch_ten_rb`. Resampling the patches (2000 bootstrap draws, seed 20261124) gives the standard error of that median. Dividing by the local slope |dc/ds| (line fit over calibration frames within ±8 steps) and multiplying by 0.154 δ per step gives the error in δ (`sampling_se_calibration.csv`).

| Steps (best focus ≈ 46) | SE of c | Local slope dc/ds | SE in δ |
|---|---:|---:|---:|
| 0–28 (near side) | 0.007–0.014 | 0.0031–0.0043 | 0.32–0.59 |
| 32–48 (around focus) | 0.010–0.027 | 0.0006–0.0027 (flat) | 1.3–4.9 |
| 52–76 (far side) | 0.014–0.029 | 0.0006–0.0043, sign changes at ~66 | 0.81–3.8 |

Median 0.95 δ over the 20 frames.

**Reading**
- On this lens (red − blue LCA 0.29 δ) the chromatic cue alone resolves displacement to about 0.3–0.6 δ per frame only on the near side of focus. Within about ±2 δ of focus its slope is near zero, so one frame's c cannot place the frame there.
- This fits the lab-sweep finding (`results/lab_sweep/LAB_SWEEP.md`) that near focus the cue is flat, and that magnitude comes mainly from the luminance-gradient term.
- Patches overlap and share chart content, so the bootstrap probably understates the error; sensor noise between exposures is not included.

**To measure repeatability properly:** capture N ≥ 10 exposures at a few steps (e.g. near side, best focus, far side) without moving the focus, and report the spread of the frame estimate in δ.
