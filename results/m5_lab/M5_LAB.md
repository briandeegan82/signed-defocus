# M5a: a rendered lens matched to the lab lens's chromatic focus

Designs and render: `src/m5_lab_lens.py` (`data/m5_lenses.csv`). M3 base optics (f/2.0, 5.5 µm, δ = 22 µm); per-channel focus copied from the lab sweep in δ (red − blue 0.29 δ, green beyond both), mirrored along z. Same 245 plates × 8 displacements and seeds as the Phase 2 render, so the frames pair with the M3 designs. Truth Δz is the displacement from the green plane.

Score: `python src/m5_lab_lens.py score --cache ~/sd_data/m5 --out results/m5_lab` (`m2_continuous.score`: five traversal-disjoint folds, unseen continuous displacements).

| Lens | Direction | Within 0.5 δ of focus | MAE (δ) | p90 (δ) |
|---|---:|---:|---:|---:|
| `m5_lab` (lab order: green beyond red and blue) | 0.78 | 0.69 | 1.46 | 5.03 |
| `m5_lab_sa` (same, with spherical aberration) | 0.75 | 0.57 | 1.47 | 5.13 |
| `m5_lin029` (linear LCA, green between) | 0.76 | 0.56 | 1.49 | 5.02 |
| Phase 2 M3 designs at 0.25 δ (`results/phase2`, PR for Phase 2) | 0.70–0.73 | 0.51–0.57 | 1.58–1.71 | 5.33–5.68 |
| Phase 2 M3 designs at 0.5 δ | 0.86–0.89 | 0.54–0.70 | 0.96–1.01 | 1.95–2.11 |

**Findings**
1. **On driving scenes, a lens with the lab lens's LCA gives direction about 0.78 of the time, and no usable displacement.** MAE is about 1.5 δ and p90 about 5 δ, against the 1 δ Gate B threshold. The result sits between the 0.25 δ and 0.5 δ M3 designs, as its 0.29 δ predicts.
2. **The lab lens's secondary spectrum (green outside red–blue) helps a little.** Against the linear control at the same red–blue LCA, direction is +0.02 overall and +0.13 within 0.5 δ of focus. That is one render with no interval, so it is suggestive only.
3. **Adding spherical aberration removes that near-focus gain** (0.57 within 0.5 δ).
4. **The rendered result does not match the lab calibration split** (19/20 direction, MAE 0.16 δ, `results/lab_sweep/LAB_SWEEP.md`). The chart is one fixed high-contrast scene, and the lab fit uses its own through-focus curve. The rendered folds hold out whole traversals of natural scenes. For this lens, then, the chart result should not be read as evidence of in-service accuracy.

**Limits:** rendered only; the PSF model resolves blue focus only roughly at this pitch (`m5_lab_lens.py check`); and the lab's step direction relative to the sensor is assumed.

## Provenance

Feature parquets on Brian's machine, `~/sd_data/m5/rc_feat_<lens>_pre_all.parquet`, SHA-256 prefixes: m5_lab `fd07af17`, m5_lab_sa `3868ebd4`, m5_lin029 `5c048d40`. Code: `src/m5_lab_lens.py` at the commit that added it (PR #20), frozen `defocus-estimator@4564cf2`.
