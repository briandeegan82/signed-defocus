# signed-defocus

Signed single-image defocus estimation from longitudinal chromatic aberration, for focus monitoring of fixed-focus cameras. Target venue: IEEE Open Journal of Vehicular Technology.

This repository is a fresh start. The earlier study (`briandeegan82/defocus-estimator`) is frozen and is used only as a source of raw data, renders and caches.

| Path | Contents |
|---|---|
| `docs/PROPOSAL.md` | What the earlier data supports, research questions, scope, missing experiments, plan |
| `docs/PROTOCOL.md` | Definitions, splits, metrics, decision rules and the figure list, fixed before experiments |
| `src/` | Analysis and figure scripts (empty until the protocol is approved) |
| `paper/` | LaTeX source and generated `numbers.tex` (empty until analysis is complete) |

Status: proposal and protocol awaiting approval. Phase 1 gate checks under way: physics baseline v0 on cached renders (`results/PHYSICS_BASELINE.md`), re-scored in µm and depth of focus (`results/DOF_RESCORE.md`).
