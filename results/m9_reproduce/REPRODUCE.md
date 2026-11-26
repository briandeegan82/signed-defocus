# M9: reproducibility check

Command (on Brian's machine, where the caches are):

    python src/reproduce.py --estimator ~/blur_study --data ~/sd_data --scratch ~/sd_work/m9_final

`src/reproduce.py` reruns every analysis script from the feature caches into a scratch directory and compares each committed result CSV with the regenerated one (columns, rows, strings equal, numbers within rtol 1e-9 / atol 1e-12). It exits non-zero on any mismatch, missing output or failed step.

**Result at commit `c47cf78` (16 steps): 107 of 108 committed CSVs reproduce exactly (max |difference| 0), 6 per-frame CSVs are produced that are not committed, and the figure scripts run** (`reproduce_report.csv`). Steps: physics baseline v0 + DoF re-score, M3 gate, M2 gate, lab sweep and calibration-split sharpness/MTF, M4, M6, M7, M8 (strong-LCA and laboratory-matched designs) and the M8 multi-frame bootstrap, Phase 2 (27 designs), M5 laboratory-matched designs, reference rows, lab test, lab transfer, figures.

**The one difference** is in `results/m8_confounds/fleet/m8_fleet.csv`: the ROC AUC of strong-LCA defocus +0.02 DZ against fog is 0.8253 on the reproduction machine (aarch64) and 0.8254 committed. The committed value is 0.825356 unrounded (it is written with 4 decimals), and 35 of the 60,025 frame pairs differ by less than 1e-9 in |Δz|, so last-bit floating-point differences between architectures move ties across the rounding boundary. On the x86_64 machine the same step reproduces the committed file exactly. The paper prints this AUC to two decimals (0.83), so no reported number changes.

**Provenance** (`provenance.json`): commit `c47cf78`, clean src/ and data/, Python 3.12.13, numpy 2.4.6, pandas 3.0.5, pyarrow 25.0.0, scipy 1.18.0, matplotlib 3.11.1, and the SHA-256 of all 100 input files the steps read.

**Not rerun**
- Renders and feature extraction (GPU, hours each). Their output caches are hashed instead, so a changed cache is detectable.
- The `lab_test` step recomputes the stored held-out laboratory predictions from the committed feature cache with the frozen rules; it changes no parameter and is not a new evaluation (`docs/PROTOCOL.md` section 2).
- Figures are rebuilt but not compared byte-wise (PDF/PNG metadata and font subsetting vary).

**What earlier runs found and fixed**
- `rescore_dof.py` sorted lenses with tied LCA/δ in an unstable order, so `dof_summary.csv` row order and the M3 `adjacent_inversions` count (10, 11 or 12) depended on the pandas version. Ties are now ordered by lens name; the count is 11 and `M3_GATE.md` notes it is descriptive only. Spearman ρ and Kendall τ, which Gate A uses, were unaffected.
- `M8_CONFOUNDS.md` had the synth_lcaP motion and fog checksums swapped (motion is `5f6ebb39`, fog `c51f9cf0`).
