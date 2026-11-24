# M2 gate: continuous displacement on 40 RobotCar plates

Cheap gate (proposal Phase 1), not the full M2 experiment: one lens, 40 plates.

## Provenance

- Lens: exact copy of `synth_lcaP` (f/2.0, 5.5 µm pitch, `defocus_scale` 1.0 mm, so δ = 22 µm; red-blue LCA 40 µm = 1.82 δ).
- Render: `python src/m2_continuous.py render --estimator ~/blur_study --noise-model ~/blur_study/results/robotcar_noise_model.json --out ~/sd_data/m2` on Brian's machine (GB10 GPU), frozen `defocus-estimator@4564cf2` code, pre-ISP arm. 40 plates from 12 traversals, 8 displacements per plate drawn uniformly from ±0.1 DZ (±100 µm), seeded by plate. 319 frames: one plate drew two displacements that round to the same 1e-4 DZ directory, so one frame overwrote the other.
- Score: `python src/m2_continuous.py score --cache ~/sd_data/m2/rc_feat_m2_synth_lcaP_pre_all.parquet --ladder ~/blur_study/results/rc_feat_robotcar_render_synth_lcaP_pre_all.parquet --out results/m2_gate`. Five traversal-disjoint folds; every test frame has a displacement never seen in training. "continuous" trains the through-focus curve on the other folds' continuous frames (binned at 0.01 DZ); "ladder" trains it on the cached 9-rung v0 render of the same lens, minus the test fold's traversals.

## Results (`m2_direction.csv`, `m2_displacement.csv`)

| \|dz\| band | Frames | Direction acc. | MAE (δ), continuous | MAE (δ), ladder | p90 (δ), continuous | p90 (δ), ladder |
|---|---|---|---|---|---|---|
| 0-0.5 δ | 32 | 0.844 | 0.35 | 0.21 | 0.43 | 0.28 |
| 0.5-1 δ | 38 | 1.000 | 0.34 | 0.33 | 0.82 | 0.90 |
| 1-2 δ | 71 | 1.000 | 0.53 | 0.63 | 1.28 | 1.42 |
| > 2 δ | 178 | 1.000 | 0.66 | 0.65 | 1.20 | 1.39 |
| all | 319 | 0.984 | 0.56 (12.3 µm) | 0.56 (12.4 µm) | 1.22 | 1.37 |

Direction is the "fitted" level; "order" (sign from the prescription) gives the same numbers. Per fold, direction accuracy is 0.975-1.000 and continuous MAE 0.50-0.61 δ.

## Gates

- **Gate B passes on continuous displacement for this lens:** MAE 0.56 δ over 319 unseen displacements, below 1 δ in every band and every fold. It matches the v0 leave-one-rung-out MAE (12.3 µm), so the ladder test was not flattering the estimator.
- **Training on the ladder is as good as training on continuous frames** (MAE 0.56 δ both); continuous training has a shorter tail (p90 1.22 vs 1.37 δ).
- **Direction fails only near focus:** 0.844 below 0.5 δ, where the red/blue ratio is close to its in-focus value; 1.000 above.

## Limits

- One optical design (the LCA/δ = 1.82 probe); M3 covers LCA/δ 0-2 on the ladder.
- 40 plates; the full M2 run renders more plates and lenses.
