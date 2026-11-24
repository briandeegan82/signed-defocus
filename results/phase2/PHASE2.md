# Phase 2: all 27 M3 designs on every RobotCar plate at continuous displacements

- Render: `src/phase2_render.sh ~/blur_study ~/blur_study/results/robotcar_noise_model.json ~/sd_data/phase2` on Brian's machine (GB10 GPU), 2026-11-24. Each design in `data/m3_lenses.csv` is rendered with `m2_continuous.py render --n-plates 0 --k 8`: 245 plates from 12 traversals, 8 distinct displacements per plate drawn uniformly from ±0.1 DZ (`draw_dz`, seeded by plate), so 1,960 frames per lens; pre-ISP arm, frozen `defocus-estimator@4564cf2` code.
- Score: `python src/phase2_score.py --cache ~/sd_data/phase2 --out results/phase2`. Each lens is scored with `m2_continuous.score`: five traversal-disjoint folds, direction sign and offset fitted on training traversals, displacement from the through-focus curve of training frames binned at 0.01 DZ. Every test displacement is absent from training. Gate A and Gate B as in `docs/PROTOCOL.md`.
- Optics: f/2.0, 5.5 µm pitch, δ = 22 µm, 1 DZ = 1 mm. This supersedes the 8-plate subset in `results/m3_gate/` and the 40-plate test in `results/m2_gate/` for reported numbers.

## Gates

| | Subset (8 plates/traversal, 9 rungs) | Full (245 plates, continuous) |
|---|---:|---:|
| Gate A: Spearman ρ over 27 lenses | 0.96 | 0.95 (one-sided p < 1e-14) |
| Kendall τ | 0.88 | 0.87 |
| Gate B: MAE for the 9 lenses with LCA/δ > 1 | 0.48–0.51 δ | 0.59–0.63 δ, all pass |

## Per LCA level (`phase2_summary.csv`, ranges over sign and SA)

| LCA/δ | Direction accuracy | Within 0.5 δ of focus | MAE (δ) | p90 (δ) |
|---:|---:|---:|---:|---:|
| 2.0 | 0.97–0.99 | 0.82–0.89 | 0.59–0.61 | 1.36–1.40 |
| 1.82 (synth_lcaP copy) | 0.98 | 0.88 | 0.59 | 1.37 |
| 1.5 | 0.97–0.98 | 0.80–0.87 | 0.61–0.63 | 1.40–1.42 |
| 1.0 | 0.96–0.98 | 0.73–0.83 | 0.65–0.71 | 1.46–1.52 |
| 0.75 | 0.91–0.96 | 0.62–0.77 | 0.72–0.81 | 1.54–1.65 |
| 0.5 | 0.86–0.89 | 0.54–0.70 | 0.96–1.01 | 1.95–2.11 |
| 0.25 | 0.70–0.73 | 0.51–0.57 | 1.58–1.71 | 5.33–5.68 |
| 0 | 0.51–0.54 | 0.44–0.56 | 2.44–2.64 | 7.00–7.22 |

**Findings**
1. **Both gates hold on the full render.** The rank trend is as strong as on the subset.
2. **Errors are about 20% larger than on the subset** (0.59–0.63 against 0.48–0.51 δ for LCA > 1 δ). The full render has 2.5 times as many plates (245 against 96) and scores continuous rather than leave-one-rung-out displacements; we attribute the difference to both, without separating them.
3. **Spherical aberration is not a direction confound on the full render.** With no LCA, direction accuracy is 0.54 without SA and 0.51 with it, both chance. The subset's 0.55 for `m3_z000_sa` (`results/m3_gate/M3_GATE.md`) did not survive more scenes. SA still lowers near-focus accuracy at some levels (e.g. 0.73 against 0.83 at +1 δ).
4. **Direction within 0.5 δ of focus stays the weak point:** at most 0.89 even at 2 δ LCA.
5. **Below 1 δ LCA the error grows quickly:** MAE reaches 1 δ at 0.5 δ LCA, and the p90 exceeds 5 δ at 0.25 δ.

Per-lens direction and displacement by |Δz| band are in `lenses/<lens>/`; per-frame tables only for `m3_ref` (Fig. 3).

## Provenance

Feature parquets on Brian's machine, `~/sd_data/phase2/rc_feat_m2_<lens>_pre_all.parquet`, SHA-256 prefixes:

m3_n025 `1a9f6a79`, m3_n025_sa `a5176169`, m3_n050 `a48c309f`, m3_n050_sa `15ef6465`, m3_n075 `077d4e66`, m3_n075_sa `2227fcc5`, m3_n100 `d6d0012f`, m3_n100_sa `ecbd1f67`, m3_n150 `0a6f8200`, m3_n150_sa `6b4eb4e2`, m3_n200 `403a8c25`, m3_n200_sa `32b98eb9`, m3_p025 `650d5add`, m3_p025_sa `54d861b7`, m3_p050 `3760b91e`, m3_p050_sa `4b22b18d`, m3_p075 `30e98a38`, m3_p075_sa `54f93609`, m3_p100 `f8dc6fbb`, m3_p100_sa `54567d0a`, m3_p150 `1815cb7a`, m3_p150_sa `9d03ee5e`, m3_p200 `5caa363f`, m3_p200_sa `6482b86a`, m3_ref `5e9f8c7d`, m3_z000 `13109332`, m3_z000_sa `4abcf65f`.
