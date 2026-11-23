# Physics baseline v0 re-scored in µm and depth of focus

Exploratory gate check, not a paper result. It converts the v0 results; it does not re-run the estimator.

## Why

`PHYSICS_BASELINE.md` labels the render ladder DZ × 1000 as µm. The ladder is nominal. In `defocus-estimator/src/lens_synth.py` the focus error of a channel is DZ × `defocus_scale` + `long_ca` × (λ − 0.588 µm), in mm, so the sensor displacement of a rung is DZ × `defocus_scale`, and `defocus_scale` differs by lens (0.43-2.36 mm per unit). The real-lens banks (laikin, sunex, sony, horimoto) are published PSF maps with no recorded f-number or pixel pitch (`render_arms.py`: "Defocus is a nominal ladder index here, not a physical displacement"), so they cannot be converted and are left out.

## Provenance

- Code: `src/rescore_dof.py` (this commit).
- Inputs: `results/physics_baseline_direction.csv` and `results/physics_baseline_displacement.csv` from v0; `data/lens_optics.csv`, copied from `defocus-estimator@4564cf2` `results/lens_population.csv` (synth00-synth11) and `src/lens_lca_probe.py` `BASE` (synth_lcaP, synth_lcaN). Assumed, not checked: the RobotCar renders of each synth lens used the design in `lens_population.csv`.
- Command: `python src/rescore_dof.py`
- Outputs: `dof_summary.csv`, `dof_gate_a.csv`, `dof_direction_by_dz.csv`.

## Conversions

- Displacement: dz = DZ × `defocus_scale` × 1000 µm.
- Depth of focus: δ = 2Nc (protocol section 1).
- LCA: z_r − z_b = −`long_ca` × (0.656 − 0.486) × 1000 µm, unrounded. `lca_all.csv` instead rounds each channel to its best-focus rung, so any LCA below one rung shows as 0.
- Direction is the "fitted" level, the only level v0 scored on every synth lens.

## Results (`dof_summary.csv`)

| Lens | N | c (µm) | δ (µm) | Rung (µm) | LCA (µm) | LCA/δ | Direction acc. | Withheld MAE (µm) | MAE (δ) | p90 (δ) |
|---|---|---|---|---|---|---|---|---|---|---|
| synth_lcaP / N | 2.00 | 5.5 | 22.0 | 10.0 | 40.0 | 1.82 | 1.000 / 1.000 | 12.3 / 12.3 | 0.56 / 0.56 | 1.42 / 1.41 |
| synth11 | 1.94 | 3.1 | 12.1 | 11.2 | 7.2 | 0.60 | 0.856 | 15.4 | 1.27 | 2.52 |
| synth07 | 2.28 | 4.4 | 20.2 | 20.9 | 6.3 | 0.31 | 0.603 | 50.4 | 2.49 | 6.55 |
| synth08 | 2.85 | 5.8 | 33.0 | 19.7 | 8.9 | 0.27 | 0.583 | 58.5 | 1.78 | 4.51 |
| synth01 | 2.08 | 10.3 | 42.9 | 14.3 | 8.5 | 0.20 | 0.642 | 41.5 | 0.97 | 2.61 |
| synth03 | 2.45 | 6.4 | 31.4 | 5.8 | 4.3 | 0.14 | 0.529 | 26.6 | 0.85 | 1.87 |
| synth00 | 3.50 | 10.8 | 75.7 | 8.9 | 9.8 | 0.13 | 0.557 | 46.8 | 0.62 | 1.17 |
| 6 lenses, LCA/δ 0.01-0.07 | 1.66-3.85 | 4.9-11.5 | 25.9-86.2 | 4.3-23.6 | 0.4-5.9 | 0.01-0.07 | 0.506-0.557 | 21.6-91.5 | 0.69-2.27 | 1.58-6.41 |

LCA is unsigned in the table. Every synth00-synth11 lens has red focusing nearer the lens than blue; synth_lcaN is the mirror image of synth_lcaP.

## Gates (`dof_gate_a.csv`)

- **Gate A (direction rises with LCA/δ).** Over the 14 synth lenses, Spearman ρ = 0.90 (p = 1.3e-5) and Kendall τ = 0.78 (p = 1e-4); without synth_lcaP/N, ρ = 0.84 (p = 6e-4). The trend holds in rank but is not strictly monotone: 4 of 13 adjacent pairs invert (largest: synth01 at 0.20 δ scores 0.642, above synth08 and synth07 at 0.27-0.31 δ). The protocol's "must increase monotonically" does not say whether rank trend or strict order is meant; this needs a decision before approval.
- **synth11 is resolved.** Its 7.2 µm LCA is below one rung, so `lca_all.csv` shows 0, but its δ is the smallest in the population, giving 0.60 δ and the highest LCA/δ after synth_lcaP/N. Its 0.856 accuracy fits the trend.
- **Gate B (withheld MAE < 1 δ when LCA > 1 δ)** applies to synth_lcaP and synth_lcaN only, and both pass: MAE 0.56 δ, p90 1.4 δ. This is one optical design and its mirror, on a 9-rung ladder with rungs at up to 100 µm (4.5 δ), spaced 10-50 µm (0.45-2.3 δ) apart, so the test is coarse. No other lens has LCA above 0.6 δ.

## Consequences for the plan

1. The lens population for M3 needs LCA/δ spread over 0-2 δ, not 0-0.6 δ: synth00-synth11 sample `long_ca` up to 0.06 mm/µm, which caps LCA at 10 µm.
2. Gate B needs continuous displacements in δ (M2) and more than one design with LCA > 1 δ before it can be called met.
3. Protocol Δz is measured from the best-focus plane of the channel-mean MTF; this re-scoring uses DZ = 0. Lenses with spherical aberration may have best focus off DZ = 0.
