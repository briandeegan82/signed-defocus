# M9: reproducibility check

Command (on Brian's machine, where the caches are):

    python src/reproduce.py --estimator ~/blur_study --data ~/sd_data --scratch ~/sd_work/m9

`src/reproduce.py` reruns every analysis script from the feature caches into a scratch directory and compares each committed result CSV with the regenerated one (columns, rows, strings equal, numbers within rtol 1e-9 / atol 1e-12). It exits non-zero on any mismatch, missing output or failed step.

**Result at commit `8cdca02`: 33 of 33 committed CSVs reproduce exactly (max |difference| 0), and the figure script runs** (`reproduce_report.csv`). Steps: physics baseline v0 + DoF re-score, M3 gate, M2 gate, lab sweep, M4, M6, M7 (including per-zone calibration), M8 (Laikin and synth_lcaP), figures.

**Provenance** (`provenance.json`): commit, clean src/ and data/, Python 3.12.13, numpy 2.4.6, pandas 3.0.5, pyarrow 25.0.0, scipy 1.18.0, matplotlib 3.11.1, and the SHA-256 of all 67 input files the steps read.

**Not rerun**
- Renders and feature extraction (GPU, hours each). Their output caches are hashed instead, so a changed cache is detectable.
- The held-out lab test split. No script reads it; it is evaluated once, after the method is frozen (`docs/PROTOCOL.md` section 2).
- Figures are rebuilt but not compared byte-wise (PDF/PNG metadata and font subsetting vary).
- The full Phase 2 render (still running); its scoring joins the runner when it is committed.

**What the first runs found and fixed**
- `rescore_dof.py` sorted lenses with tied LCA/δ in an unstable order, so `dof_summary.csv` row order and the M3 `adjacent_inversions` count (10, 11 or 12) depended on the pandas version. Ties are now ordered by lens name; the count is 11 and `M3_GATE.md` notes it is descriptive only. Spearman ρ and Kendall τ, which Gate A uses, were unaffected.
- `M8_CONFOUNDS.md` had the synth_lcaP motion and fog checksums swapped (motion is `5f6ebb39`, fog `c51f9cf0`).
