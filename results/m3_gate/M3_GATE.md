# M3 gate: synthetic lenses spanning LCA/δ 0-2, both signs

Cheap gate (proposal Phase 1), not the full M3 experiment: 8 plates per traversal, 9 ladder rungs.

## Provenance

- Lens set: `src/m3_lenses.py designs` -> `data/m3_lenses.csv`, `data/m3_lca.csv`. All 27 lenses share the `synth_lcaP` optics (f/2.0, 5.5 µm pitch, `defocus_scale` 1.0 mm, so δ = 2Nc = 22 µm and one rung DZ = 0.01 is 10 µm). Only red-minus-blue LCA (0, ±0.25, ±0.5, ±0.75, ±1, ±1.5, ±2 δ) and spherical aberration (0, or 1.0 × `aberration_scale` 0.3 in the `_sa` half) vary. `m3_ref` is an exact copy of `synth_lcaP`.
- Render: `python src/m3_lenses.py render --estimator ~/blur_study --noise-model ~/blur_study/results/robotcar_noise_model.json --out ~/sd_data/m3 --plates 8` on Brian's machine (GB10 GPU), frozen `defocus-estimator@4564cf2` code, pre-ISP arm. 96 plates from 12 traversals x 9 rungs = 864 frames per lens; renders and caches outside the repo.
- Pipeline check: `m3_ref` features equal the cached v0 `synth_lcaP` features on every matched patch (76,032 patches, `ch_ten_rb`, `ch_ten_rg`, `ch_ten_gb`, `ed_width_med`, `sp_f50`: max |difference| 0.0).
- Score: `python src/physics_baseline.py --cache ~/sd_data/m3 --lca data/m3_lca.csv --lenses lca --cache-fmt 'rc_feat_{lens}_pre_all.parquet' --out results/m3_gate`, then `python src/rescore_dof.py --results results/m3_gate --optics data/m3_lenses.csv --out results/m3_gate`.

## Results (`dof_summary.csv`)

Direction accuracy is the "fitted" level; MAE is for the withheld rung (leave-one-rung-out). p and n lenses score alike, so each cell gives p / n.

| LCA/δ | LCA (µm) | Direction, no SA | Direction, SA | MAE (δ), no SA | MAE (δ), SA |
|---|---|---|---|---|---|
| 0 | 0 | 0.503 | 0.553 | 1.64 | 1.60 |
| 0.25 | 5.5 | 0.711 / 0.720 | 0.655 / 0.759 | 0.99 / 0.99 | 1.04 / 0.97 |
| 0.5 | 11 | 0.874 / 0.867 | 0.836 / 0.893 | 0.73 / 0.73 | 0.77 / 0.75 |
| 0.75 | 16.5 | 0.973 / 0.970 | 0.888 / 0.935 | 0.58 / 0.58 | 0.60 / 0.64 |
| 1 | 22 | 0.987 / 0.987 | 0.953 / 0.962 | 0.51 / 0.52 | 0.54 / 0.55 |
| 1.5 | 33 | 0.999 / 0.999 | 0.992 / 0.986 | 0.49 / 0.49 | 0.50 / 0.51 |
| 1.82 (`m3_ref`) | 40 | 0.999 | | 0.49 | |
| 2 | 44 | 1.000 / 0.999 | 1.000 / 0.992 | 0.48 / 0.48 | 0.48 / 0.48 |

## Gates

- **Gate A (rank trend) passes.** Over all 27 lenses, Spearman ρ = 0.96, one-sided p < 1e-4 (`dof_gate_a.csv`); 0.98 without SA (14 lenses) and 0.98 with SA (13 lenses). Of the 12 adjacent inversions, most are ties: p/n mirror pairs and SA/no-SA pairs at the same LCA/δ.
- **Gate B (withheld MAE < 1 δ when LCA > 1 δ) passes** on all 9 lenses strictly above 1 δ: MAE 0.48-0.51 δ, p90 ≤ 1.36 δ. The ±1 δ lenses sit on the threshold (0.51-0.55 δ). This is still the 9-rung ladder, so the MAE floor of about 0.48 δ (10.6 µm) mostly reflects rung spacing; M2 tests continuous displacement.
- **The sign does not matter without SA.** p and n mirror lenses differ by at most 0.009 in direction accuracy and 0.01 δ in MAE.

## Spherical aberration is a confound

- With no LCA, `m3_z000_sa` scores 0.553, against 0.503 for `m3_z000`. By rung (`dof_direction_by_dz.csv`) its accuracy is 0.17-0.24 at DZ = -0.1 and -0.05 and 0.82-0.85 at +0.05 and +0.1. So SA alone gives a red/blue cue whose sign follows defocus at large |dz|, but it does not flip at focus the way the LCA cue does.
- With LCA, SA lowers accuracy by up to 0.09 (0.888 vs 0.973 at +0.75 δ), and the two signs no longer match (0.655 vs 0.759 at 0.25 δ). The SA cue adds to one LCA sign and subtracts from the other.
- Bias of the withheld-rung estimate is up to 5.6 µm (0.25 δ) on SA lenses, against at most 2.6 µm without. This is consistent with best focus sitting off DZ = 0 when SA is present (protocol: Δz is from the channel-mean MTF peak).

## Limits

- One f-number and pixel pitch; LCA/δ is varied through LCA only.
- 8 plates per traversal (96 plates); `m3_ref` scores MAE 10.8 µm here against 12.3 µm on the full v0 render.
- Withheld-rung displacement only; continuous displacement is M2.
