# Held-out lab test (RQ3), evaluated once

- Method frozen at tag `method-freeze-v1` (commit `9ea45c2`). The plan, splits, truth and the three calibration levels are in the docstring of `src/lab_test.py`, committed before the run. This is the protocol's single evaluation of the test split; it is not to be re-run with changed settings.
- Command: `python src/lab_test.py --estimator ~/blur_study --m5 ~/sd_data/m5 --out results/lab_test`, run once on 2026-11-24 at the tag.
- Inputs (SHA-256 prefixes): `lab_feat_real_all.parquet` `ee9ec9b4`, `rc_feat_m5_lab_pre_all.parquet` `fd07af17`.
- Test split: 60 steps (s mod 4 ≠ 0) on the right chart half, 150 patches per frame. Truth Δz = (s − 46.20) × 0.154 δ. One frame (s = 46) lies within half a step of focus and has no direction truth, so direction uses 59 frames. No frame abstains at frame level.

| Calibration level | Direction (95% Wilson CI) | Bias (δ) | MAE (δ) | p90 (δ) |
|---|---|---:|---:|---:|
| Rendered only (M5a lab-matched lens) | 34/59 = 0.58 (0.45–0.69) | −2.93 | 3.78 | 7.74 |
| Channel order + threshold from calibration split | 46/59 = 0.78 (0.66–0.87) | – | – | – |
| Calibration split (every fourth step, left half) | 46/59 = 0.78 (0.66–0.87) | +0.96 | 1.03 | 3.31 |

Direction at the `calibration` level by |Δz| (`lab_test_frames.csv`): 0.50 within 0.5 δ (4 frames), 0.50 at 0.5–1 δ (4), 0.55 at 1–2 δ (11), 0.90 beyond 2 δ (40). MAE beyond 2 δ is 0.47 δ, and about 2.2 δ closer to focus.

By field zone (`lab_test_zones.csv`, calibration level): centre 0.80 (0.68–0.88), mid 0.73 (0.60–0.83); the corner zone has 4 patches per frame on this half and abstains on all 60 frames.

**Findings**
1. **Rendered-only calibration fails on the lab:** direction is at chance (CI includes 0.5) and the displacement is biased by −2.9 δ. The rendered (c, lum) scale does not carry over from driving scenes to the chart.
2. **One bit of channel order plus a threshold gives 0.78**, the same as the full calibration split. The through-focus curve adds displacement, not direction.
3. **The test split is much harder than the calibration split** (0.95 direction and 0.16 δ MAE there, `results/lab_sweep/LAB_SWEEP.md`). Twelve of the 13 direction errors are the near-side steps 30–45 (−2.5 to −0.2 δ), which the threshold from the left chart half calls positive: the right half's cue sits higher at the same focus. The chart halves differ in content and field position, so a threshold set on one half does not transfer to the other within about 2 δ of focus.
4. **Far from focus the lab lens works:** 0.90 direction and 0.47 δ MAE beyond 2 δ.
5. **The rendered prediction for a lens of this LCA was 0.78 direction** on driving scenes (M5a, `results/m5_lab/M5_LAB.md`); the lab test gives the same figure. The match is in the headline only: the error pattern differs (the lab fails on one side of focus).

**Reading for the paper:** with the lab lens's LCA (0.29 δ), signed defocus is measurable on hardware only well away from focus, and only with at least the channel order and a per-scene threshold. This is a single-lens, single-chart case study.
