# Reference rows on the Phase 2 render

`src/reference_rows.py`, all 27 M3 designs, 1,960 frames each, the same five traversal folds as the
method. Table: `reference_rows.csv`. Errors in δ; `abs_mae_delta` is the error of |Δz| only.

| Row | What it is | Output |
|---|---|---|
| physics | the method (c, ℓ frame medians, threshold + through-focus curve) | signed |
| learned | histogram gradient boosting on all 69 patch features, the earlier study's SDFE settings (300 trees, lr 0.08, depth 6, min leaf 40), patch median | signed |
| laplacian | finest Laplacian-pyramid energy (`lp_e0`, green), 1-D curve against |Δz| | unsigned |
| tenengrad | mean green gradient magnitude (`cx_grad_mean`), 1-D curve against |Δz| | unsigned |

No-SA designs, mean over LCA sign:

| LCA/δ | physics dir | physics MAE | physics |Δz| | learned dir | learned MAE | Laplacian |Δz| | Tenengrad |Δz| |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.54 | 2.64 | 0.64 | 0.51 | 2.26 | 0.29 | 0.65 |
| 0.25 | 0.72 | 1.65 | 0.66 | 0.86 | 1.82 | 0.29 | 0.65 |
| 0.5 | 0.87 | 1.00 | 0.65 | 0.94 | 1.13 | 0.29 | 0.65 |
| 1 | 0.98 | 0.67 | 0.62 | 0.98 | 0.45 | 0.29 | 0.65 |
| 2 | 0.98 | 0.59 | 0.59 | 0.99 | 0.18 | 0.29 | 0.65 |

## Findings

- **Magnitude:** the Laplacian floor's |Δz| error (0.29 δ; 0.38 δ with SA) is half the method's
  (0.59–0.66 δ). The method's value over the floor is the sign, not the magnitude.
- **Learned regressor:** better signed MAE than the method once LCA ≥ 1 δ (0.17–0.26 δ against
  0.59–0.63 δ above 1 δ) and better direction at low LCA (0.82–0.86 at 0.25 δ against 0.70–0.73), but
  no better MAE below 0.75 δ.
- **The floors do not depend on the lens design:** green focus is the same in every M3 design, and
  both floor features are green-channel features, so they are identical across the 13 no-SA designs.
- **The physics rows reproduce Phase 2** (`m3_ref` MAE 0.5915 δ, as in `phase2_summary.csv`).

## Limits

- Every row is trained and tested on renders of one lens design: in-distribution. Nothing here says
  how the learned regressor transfers to a real lens; the held-out lab split is spent
  (`results/lab_test`), so it cannot be used to test it.
- The old two-output CNN is not rerun: it needs rendered frames, which the Phase 2 render deletes
  after feature extraction. The earlier study's CNN and benchmark CSVs are not reused (their
  provenance is not established; see `ADDITIONAL_BASELINES_PLAN.md` in defocus-estimator).
- A first run included the `target` label column among the learned inputs (MAE 0.12 δ on `m3_ref`);
  it is excluded and that run discarded.
