# Physics baseline v0 on cached renders

Exploratory gate check, not a paper result. Every number here will be regenerated from the frozen pipeline.

## Provenance

- Code: `src/physics_baseline.py` (this commit).
- Inputs: cached patch features `results/rc_feat_robotcar_render_<lens>_pre_all.parquet` from `defocus-estimator` at commit `4564cf2`, which had uncommitted local changes. The Laikin cache SHA-256 starts `d983ec144fa0d598`. Lens LCA is in `data/lens_lca.csv`.
- Command: `python src/physics_baseline.py --cache <defocus-estimator>/results --lca data/lens_lca.csv --out results`
- The lab sweep was not read.

## Setup

- 18 rendered lenses, pre-ISP arm.
- 9 displacement rungs: 0, ±10, ±20, ±50 and ±100 µm.
- Five folds by traversal.
- One cue per frame: the median over patches of the log red/blue gradient-energy ratio `ch_ten_rb`. For displacement, the median log luminance gradient energy is used as well.
- Direction is scored on dz ≠ 0 frames. Calibration levels are defined in the module docstring.
- Displacement is scored leave-one-rung-out: the withheld rung is never in training, and ±100 µm is never withheld.

## Results (`physics_baseline_summary.csv`)

Accuracy columns are direction accuracy. MAE is for the withheld rung, in µm.

| Lens | LCA R-B (µm) | none | order | fitted | none, \|dz\| ≤ 20 µm | MAE | p90 |
|---|---|---|---|---|---|---|---|
| sunex | 60 | 0.932 | 0.935 | 0.935 | 0.863 | 17.5 | 41.5 |
| synth_lcaP | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 12.3 | 31.3 |
| synth_lcaN | 40 | 1.000 | 1.000 | 1.000 | 1.000 | 12.3 | 31.0 |
| sony | 30 | 0.926 | 0.926 | 0.926 | 0.862 | 23.3 | 50.0 |
| laikin | 30 | 0.800 | 0.813 | 0.813 | 0.914 | 22.7 | 58.5 |
| synth00 / synth01 | 10 | 0.562 / 0.618 | 0.557 / 0.642 | 0.557 / 0.642 | 0.506 / 0.613 | 52.8 / 29.1 | 100.0 / 78.4 |
| 11 lenses with no R-B LCA | 0 | n/a | n/a | 0.506-0.603, synth11 0.856 | n/a | 13.8-50.7 | 27.4-110.0 |

For the withheld rung, the MAE of synth_lcaP rises with distance from focus: 6.8 µm at 0, 8.2 at ±10, 13.0-13.6 at ±20 and 17.6-18.4 at ±50.

## Reading

1. **Direction needs no learned model.** It rises from chance (0 µm of R-B LCA) through 0.56-0.64 (10 µm) to 0.80-1.00 (30-60 µm). Gate A is roughly met in µm, but not strictly: sunex (60 µm) falls below synth_lcaP (40 µm). Depth-of-focus units need the render's f-number and pixel pitch, which are not recorded in the caches.
2. **Channel order is enough calibration on renders.** The "none" and "order" columns differ by at most 0.024. Fitting the sign as well gains nothing.
3. **Withheld-displacement error does not pass Gate B yet.** It is 12-23 µm on lenses with LCA, against the old SDFE's 20.8 µm, and our rung spacing is 10-50 µm. Gate B cannot be judged without the render's depth of focus. The 9-rung ladder also limits this test; continuous displacements need new renders (proposal, Gate B experiment).
4. **Anomaly to check:** synth11 has no R-B LCA in `lca_all.csv` but gives 0.856 fitted direction accuracy. Possible causes are another asymmetric aberration or an error in the LCA table. This needs checking before the dose-response figure.
