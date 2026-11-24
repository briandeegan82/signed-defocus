# signed-defocus

Signed single-image defocus estimation from longitudinal chromatic aberration, for focus monitoring of fixed-focus cameras. Target venue: IEEE Open Journal of Vehicular Technology.

This repository is a fresh start. The earlier study (`briandeegan82/defocus-estimator`) is frozen and is used only as a source of raw data, renders and caches.

| Path | Contents |
|---|---|
| `docs/PROPOSAL.md` | What the earlier data supports, research questions, scope, missing experiments, plan |
| `docs/PROTOCOL.md` | Definitions, splits, metrics, decision rules and the figure list, fixed before experiments |
| `src/` | Analysis and figure scripts (empty until the protocol is approved) |
| `paper/` | LaTeX source and generated `numbers.tex` (empty until analysis is complete) |

Reproducibility: `python src/reproduce.py` reruns every analysis from the caches and checks all committed CSVs (`results/m9_reproduce/REPRODUCE.md`).

Status: protocol v1 approved (2026-11-24). Phase 1 gates passed: Gate A (Spearman ρ = 0.96 over 27 M3 lenses, `results/m3_gate/M3_GATE.md`) and Gate B (withheld-Δz MAE below 1 δ on continuous displacement, `results/m2_gate/M2_GATE.md`). Phase 2 (full renders) under way.

Phase 2 full render scored (`results/phase2/PHASE2.md`): Gate A ρ = 0.95 over 27 designs, Gate B MAE 0.59–0.63 δ for LCA > 1 δ.
