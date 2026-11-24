# M6 (simulation only): illuminant shift and white-balance error vs the signed estimate

Script: `src/m6_illuminant.py`. Lens `m3_ref`, an exact copy of synth_lcaP (f/2.0, 5.5 µm pitch, LCA 40 µm = 1.82 δ, δ = 22 µm). 60 RobotCar plates (round-robin over 12 traversals) × 9 ladder rungs (DZ 0, ±0.01, ±0.02, ±0.05, ±0.1; 1 DZ = 1 mm) = 540 frames per condition, rendered through the frozen `render_arms.render` pre-ISP arm and extracted with the frozen `extract_parallel.extract`.

**This is a rendered stress test, not hardware evidence.** The wavelength shifts move each channel's effective centroid (sensor × illuminant × scene), which moves its focus through `lens_synth`'s `long_ca`; no measured sensor QE or illuminant spectrum is used. White-balance errors scale the per-plate grey-world red or blue gain.

| Condition | Change |
|---|---|
| nominal | r/g/b at 656/588/486 nm, grey-world gains |
| shift+10, shift-10 | all channels ±10 nm |
| warm | r +5, g +8, b +15 nm |
| cool | r −10, g −6, b −5 nm |
| wb_r0.8, wb_r1.25, wb_b0.8, wb_b1.25 | red or blue gain × 0.8 or × 1.25 |

**Pipeline check:** the nominal condition reproduces the defocus-estimator cache `rc_feat_robotcar_render_synth_lcaP_pre_all` (`b4083e9a`) exactly on the shared frames: 47,520 patch rows, maximum absolute difference 0.0 in `ch_ten_rb` and `cx_grad_mean`.

## Method

Physics baseline as in `physics_baseline.py` (frame medians of the red/blue Tenengrad ratio c and the log luminance gradient). It is calibrated on the defocus-estimator's synth_lcaP 9-rung ladder of the training traversals and scored on each condition's held-out traversals (five traversal-disjoint folds). The calibration is always nominal, so each row measures what an uncorrected illuminant or white-balance change does to a deployed estimator. Nothing abstains.

## Results

| Condition | Direction | Direction, \|Δz\| ≤ 0.91 δ | MAE (µm) | MAE (δ) | Bias (δ) | MAE, \|Δz\| ≤ 0.45 δ (δ) | Median c |
|---|---:|---:|---:|---:|---:|---:|---:|
| nominal | 1.000 | 1.000 | 8.6 | 0.39 | −0.01 | 0.24 | 0.163 |
| shift+10 | 1.000 | 1.000 | 8.9 | 0.40 | +0.11 | 0.26 | 0.062 |
| shift-10 | 0.998 | 0.996 | 8.9 | 0.40 | −0.11 | 0.28 | 0.255 |
| warm | 1.000 | 1.000 | 9.0 | 0.41 | +0.09 | 0.26 | 0.068 |
| cool | 1.000 | 1.000 | 8.7 | 0.40 | −0.07 | 0.25 | 0.221 |
| wb_r0.8 | 1.000 | 1.000 | 11.5 | 0.52 | +0.13 | 0.37 | −0.034 |
| wb_r1.25 | 0.998 | 0.996 | 9.3 | 0.42 | −0.03 | 0.30 | 0.272 |
| wb_b0.8 | 0.967 | 0.942 | 10.3 | 0.47 | −0.07 | 0.41 | 0.364 |
| wb_b1.25 | 0.990 | 0.979 | 10.3 | 0.47 | +0.08 | 0.33 | 0.008 |

Direction excludes the DZ = 0 rung. The worst rung is +0.45 δ under wb_b0.8 (direction 0.77) and −0.45 δ under wb_b1.25 (0.92). Full table: `m6_summary.csv`; per frame: `m6_frames.csv`.

## Interpretation

- **Direction is robust on this lens.** It stays at or above 0.97 under every condition; only the rungs nearest focus lose any frames.
- **The error is an offset in c, not lost signal.** Each condition moves the in-focus red/blue ratio (median c from −0.03 to 0.36 against 0.16 nominal), which shifts the estimated focus point. The far rungs are unaffected; the error concentrates within ±0.45 δ of focus, where MAE rises from 0.24 δ to at most 0.41 δ.
- **Wavelength shifts of ±10 nm bias Δz by about ±0.1 δ.** The sign follows the direction of the shift.
- **A 20 % white-balance gain error costs more than a 10 nm shift** (MAE up to 0.52 δ) but stays under Gate B's 1 δ.
- **Consequence:** a deployed estimator needs either a per-illuminant zero point or a white-balance-invariant cue. The lab lens (LCA 0.29 δ) has a 6× weaker chromatic signal, so the same offset would be a larger fraction of it; M6 does not test that lens.

## Limitations

One strong-LCA lens, one strength per perturbation, parametric wavelength shifts, nominal calibration only. Not hardware evidence.

## Provenance

Feature parquets on Brian's machine, `~/sd_data/m6/rc_feat_m6_<condition>_pre_all.parquet`, SHA-256 prefixes: nominal `09877aa2`, shift+10 `66459cdc`, shift-10 `985c4293`, warm `6fb7ad7d`, cool `bac11554`, wb_r0.8 `e2921d39`, wb_r1.25 `8b0af960`, wb_b0.8 `08aa907c`, wb_b1.25 `d100072c`. Calibration cache `b4083e9a` (defocus-estimator `4564cf2`, uncommitted local changes). Each condition directory records its channel wavelengths and gains in `condition.json`.

```
python src/m6_illuminant.py render --estimator ~/blur_study --noise-model <json> --out ~/sd_data/m6
python src/m6_illuminant.py score --cache ~/blur_study/results --m6 ~/sd_data/m6 --out results/m6_illuminant
```
