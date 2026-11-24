# M7: field position

Script: `src/m7_field.py`. Inputs: the defocus-estimator's `robotcar_render_fieldvarying` and caches at commit `4564cf2`, which had uncommitted local changes. Features are extracted here with the frozen `extract_parallel.extract`. SHA-256 prefixes:

| Input | SHA-256 |
|---|---|
| field-varying features `rc_feat_fieldvarying_sony_pre_all.parquet` (on Brian's machine, `~/sd_data/m7/`) | `51cede52bedf8542` |
| uniform Sony ladder `rc_feat_robotcar_render_sony_pre_all.parquet` | `f3e0c823e213078a` |
| `robotcar_render_fieldvarying/field_labels.json` | `3bbdbfb38479d182` |
| `lab_sweep_field_mtf.csv` | `26f6f0d894628cd5` |

## Rendered: Sony full field map, 219 RobotCar plates, 9 rungs

- **Calibration:** on the uniform centre-PSF Sony ladder of the training traversals, as it would be deployed.
- **Scoring:** held-out traversals, five folds, per field zone. Each zone's patches within a frame are pooled by their median.
- **Zones:** by normalised field radius: centre < 1/3, mid 1/3–2/3, corner ≥ 2/3.
- **Control:** the same plates and zones on the uniform render.
- **Units:** DZ is in ladder units, since Sony has no recorded f-number or pitch.
- **Direction truth:** "nominal" is the sign of the rung. "Local" subtracts the zone's own best-focus shift, the peak of the field map's mtf025_mean.

| Render | Zone | Direction, nominal | Direction, local | MAE (DZ) | Bias (DZ) | Zone best focus (DZ) | Zone red − blue focus (DZ) |
|---|---|---:|---:|---:|---:|---:|---:|
| uniform | centre | 0.877 | 0.877 | 0.025 | −0.009 | −0.004 | 0.016 |
| uniform | mid | 0.898 | 0.898 | 0.026 | −0.002 | | |
| uniform | corner | 0.903 | 0.903 | 0.036 | −0.008 | | |
| field-varying | centre | 0.814 | 0.814 | 0.047 | −0.001 | −0.004 | 0.016 |
| field-varying | mid | 0.689 | 0.789 | 0.063 | +0.044 | −0.019 | 0.023 |
| field-varying | corner | 0.678 | 0.781 | 0.076 | +0.036 | −0.015 | 0.023 |

MAE is against the nominal rung, from leaving one rung out, as in v0. Per-rung accuracy is in `m7_direction_by_dz.csv`, and the field-map focus per cell in `sony_field_focus.csv`.

**Findings**
1. **Off-axis, direction accuracy falls from about 0.90 to 0.69 under the real field PSF.** Field curvature explains about half of the fall. Mid and corner focus about 0.015–0.019 DZ nearer than the centre, so at rungs −0.01 and −0.02 those patches are on the other side of their own focus. Accuracy at those rungs drops to 0.09–0.29 (`m7_direction_by_dz.csv`). Scored against local focus, mid and corner reach 0.78–0.79, still below the uniform 0.90.
2. **Even the centre zone drops, from 0.88 to 0.81.** Its cells also carry the field map's off-centre PSFs.
3. **The displacement estimate gains a positive bias off-axis**, of +0.04 DZ (+0.02 against local focus). A calibration made on the centre PSF does not transfer to the field edge. A per-zone calibration, or a field-varying training render, is needed before off-axis numbers are reported (finding 5).
4. **The red − blue focus difference grows slightly off-axis** in the Sony map, from 0.016 to 0.023 DZ.

### Per-zone calibration (`m7_zonecal.csv`)

The estimator refitted on each zone of the field-varying render's training traversals (threshold and sign; through-focus curve with the scored rung withheld), then scored on the same zone of the held-out traversals. Direction truth is the nominal rung. This is a best case: it assumes a calibration render or chart that matches the deployed lens's field map.

| Zone | Direction, centre-calibrated | Direction, zone-calibrated | MAE (DZ), centre → zone | p90 (DZ), zone | Bias (DZ), centre → zone |
|---|---:|---:|---:|---:|---:|
| centre | 0.814 | 0.817 | 0.047 → 0.028 | 0.071 | −0.001 → −0.006 |
| mid | 0.689 | 0.753 | 0.063 → 0.022 | 0.050 | +0.044 → −0.003 |
| corner | 0.678 | 0.682 | 0.076 → 0.024 | 0.052 | +0.036 → −0.002 |

5. **Per-zone calibration removes the off-axis displacement bias.** Bias falls to within ±0.006 DZ in every zone, and MAE to 0.022–0.028 DZ, the level of the uniform render (0.025–0.036).
6. **It does not recover direction.** Mid gains 0.06, corner nothing; both stay well below the uniform 0.90. A single threshold per zone cannot fit rungs that sit on opposite sides of their nominal and local focus, so the off-axis direction loss is a property of the field PSF, not of the calibration.

## Lab: the 11 chart squares, 80-step sweep

Best-focus step per channel, square and frequency, from a parabola in log MTF over ±6 steps of the peak (`lab_squares_focus.csv`). One δ is 6.5 steps (`results/lab_sweep/LAB_SWEEP.md`).

| Zone (squares) | Red − blue at 0.125 cy/px, steps (δ) | Red − blue at 0.25 cy/px, steps (δ) |
|---|---:|---:|
| centre (0) | 1.53 (0.23) | 1.34 (0.21) |
| inner (1–2) | 1.25 (0.19) | −0.31 (−0.05) |
| mid (3–6) | 0.51 (0.08) | −1.75 (−0.27) |
| corner (7–10) | 0.32 (0.05) | −2.63 (−0.40) |

- **Centre:** both frequencies agree, at 0.2 δ.
- **Off-axis:** they disagree, by up to 6 steps on single squares (4, 8, 10). At 0.25 cy/px the red−blue order reverses in the mid and corner zones; at 0.125 cy/px it shrinks toward zero.
- **Reading:** the lab lens's chromatic cue is weak everywhere (≤ 0.23 δ), and off-axis it is not a stable signed quantity. Astigmatism and lateral colour along each square's edge direction are the likely causes; one edge per square cannot separate them.
- **Consequence for the held-out lab test:** frame-level pooling can still work on this lens, since it gave 19/20 on the calibration split (PR #8). The test should therefore also report accuracy per field zone; the off-axis squares are where it is expected to fail first.
