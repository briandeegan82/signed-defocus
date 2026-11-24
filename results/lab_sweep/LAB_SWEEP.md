# Lab sweep, Phase 1: step size from the MTF fall-off, and the physics baseline on the calibration split

Inputs (read-only): `blur_study/results/lab_sweep_mtf.csv` (raw-Bayer-plane slanted-edge SFR of the centre square at each of the 80 steps) and `blur_study/results/lab_feat_real_all.parquet` (patch features, chart region), from `defocus-estimator@4564cf2` plus the lab files of 2026-11-23. Step s = file step / 2 (0-79).

Command: `python src/lab_sweep.py --estimator ~/blur_study --out results/lab_sweep`. Model and splits are in the script docstring.

## Step size

The measured per-channel MTF at 0.125 and 0.25 cy/px is fitted with the exact (Hopkins) defocus OTF of a circular pupil, one shared µm-per-step k, a per-channel best-focus step s0, a per-channel, per-frequency in-focus scale and a noise floor (`step_size_fits.csv`, `mtf_fit_calibration.csv`).

| Fit | k at f/2 (µm/step) | s0 blue / red / green | RMSE |
|---|---|---|---|
| Calibration steps (0, 4, ..., 76), both frequencies (primary) | 2.13 (95% residual bootstrap 2.07-2.18) | 42.7 / 44.7 / 46.2 | 0.040 |
| All 80 steps | 2.15 | 42.9 / 44.6 / 46.2 | 0.041 |
| 0.125 cy/px only | 2.30 | 43.2 / 44.8 / 46.9 | 0.045 |
| 0.25 cy/px only | 1.98 | 43.3 / 44.2 / 45.3 | 0.033 |
| Tails only (s < 36 or s > 56) | 1.85 | 42.8 / 44.7 / 46.3 | 0.037 |
| k per channel | 2.13 / 2.31 / 2.18 (b / r / g) | 42.8 / 44.8 / 46.2 | 0.040 |

- The defocus blur sets k / N, not k: the fit measures 1.07 µm of focus shift per step per unit f-number. At f/2 that is 2.1 µm/step (1.85-2.30 over the variants); at f/2.8, 3.0 µm/step.
- In depth-of-focus units the f-number cancels: one step is k / (2Nc) = 0.154 δ, so δ is about 6.5 steps. This holds whatever the iris setting was.
- The geometry estimate in `docs/LAB_RIG.md` (3.7 µm/step, assuming step 79 is infinity) agrees only if the lens was at about f/3.5. At f/2, step 79 would focus at about 0.7 m and infinity would lie near step 104, past the end of the sweep. The iris was at about f/2, set by eye (Brian, 2026-11-24), so the sweep does not reach infinity.
- The off-chart wall peaks at file step 112-114 (s = 56-57, `hf_wall_raw`), 10.3 steps after the chart. At 2.13 µm/step that is 22 µm, a wall about 6 cm behind the chart; at 3.7 µm/step it is about 13 cm. Field curvature does not explain the offset: the corner squares peak at most one step after the centre square (`lab_sweep_field_mtf.csv`).

Limits: the model treats the lens's other aberrations as a constant in-focus loss. Spherical aberration would broaden the through-focus curve and bias k low; the tails-only fit (1.85) and the 0.25 cy/px fit (1.98) are within 15% of the primary fit. The pixel pitch (3.45 µm) is still the datasheet value.

## Lab lens LCA

Blue focuses 1.9 steps before red (red-blue LCA 0.29 δ; 4.1 µm at f/2), and green focuses 1.5 steps after red, beyond both. Green outside the red-blue interval is the secondary-spectrum pattern of an achromat. At 0.29 δ the lab lens sits near the 0.25 δ M3 designs, where direction accuracy on RobotCar plates was 0.66-0.76.

## Physics baseline, calibration split only

Calibration split: every fourth step (s = 0, 4, ..., 76) on the left chart half (165 patches per frame). Δz = 0 at the fitted green peak, s = 46.2. Leave-one-frame-out: the sign and offset (calibration level "fitted") and the through-focus curve over (red/blue ratio, log luminance gradient) are fitted on the other 19 frames (`baseline_calibration_frames.csv`).

| Metric | Value |
|---|---|
| Direction accuracy | 0.95 (19 of 20 frames); the miss is s = 48, 1.8 steps (0.28 δ) past focus |
| Displacement error, 18 interior frames | MAE 1.07 steps (0.16 δ), p90 1.95 steps (0.30 δ), bias -0.1 steps |

The red/blue ratio is not monotone in s. It is flat from s = 36 to 48 and falls again past s = 68, so the direction comes from the different levels on the two sides of focus, not from a sign change at focus (the M3 spherical-aberration pattern). The displacement result holds on a chart with neighbouring calibration frames 4 steps (0.62 δ) apart, and is not a test result.

The lab test split (the other 60 steps, right chart half) has not been touched. It is evaluated once, after the method is frozen on rendered data (protocol section 2).
