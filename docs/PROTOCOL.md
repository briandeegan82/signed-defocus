# Analysis protocol (version 1, approved 2026-11-24)

Fixed before any new experiment is run. Changes after approval are logged at the bottom with a date and a reason. A result that the protocol did not plan is reported as exploratory.

## 1. Definitions

- Δz: displacement of the sensor from the best-focus plane of the channel-mean MTF at 0.25 cycles/pixel, in µm; positive away from the lens. Direction is sign(Δz).
- Depth of focus (DoF): \(\delta = 2 N c\), with N the working f-number and c one pixel pitch. Displacements and LCA are reported in µm and in units of δ.
- LCA: separation in µm between the best-focus planes of the red and blue channels; channel order is the sequence of the three best-focus planes along z.
- Patch: 128 x 128 pixels; frame estimate: pooled over admitted patches of one frame.

## 2. Data

| Set | Source | Use |
|---|---|---|
| R-train / R-test | Oxford RobotCar raw plates, blur inserted before the ISP, Δz drawn uniformly at random per frame (experiment M2) | RQ1, RQ2, RQ4 |
| Lens population | Synthetic designs with LCA in 6-8 levels from 0 to about 60 µm, both signs, with and without spherical aberration (M3); existing real prescriptions as a check | RQ1 |
| Lab sweep | 80 real through-focus frames, one lens, eSFR chart, chart region only | RQ3 |

Splits: rendered data are split by traversal (scene-disjoint), five folds. The lab sweep is split by alternating steps (calibration: every fourth step; test: the rest) and by chart half, so no pixel or step is in both. The lab test split is evaluated once, after the method is frozen on rendered data.

Exclusions, decided in advance: patches below the texture threshold are not admitted; frames with fewer than 10 admitted patches return "no estimate" and are counted in the abstain rate, not dropped.

## 3. Method under test

Per-channel sharpness on admitted patches -> chromatic ratios -> signed Δz through a through-focus model built from the lens's per-channel MTF curves -> frame pooling. Free parameters (texture threshold, pooling statistic, calibration curve) are set on R-train only.

Comparisons: Laplacian variance and Tenengrad (unsigned floor); SDFE magnitude + CHROMA and a two-output CNN (reference rows, same splits).

## 4. Metrics

| Question | Primary | Secondary |
|---|---|---|
| RQ1 direction | Frame direction accuracy as a function of LCA/δ and of \|Δz\|/δ | Patch accuracy; abstain rate |
| RQ2 displacement | Signed error on Δz values absent from training: bias, MAE, 90th percentile, in µm and in δ | Error vs \|Δz\|; error by field position (centre, mid, corner) |
| RQ3 hardware | RQ1 and RQ2 metrics on the lab test split at three calibration levels: none, channel order only, calibration steps | Agreement between rendered and measured per-channel through-focus curves |
| RQ4 threats | Direction accuracy and abstain rate per condition; false-alarm rate on in-focus frames with motion blur or fog | - |

Rank correlation is not a headline metric. Uncertainty: 95% bootstrap intervals over frames within fold, and the spread over folds and over lenses, both reported. No significance claim without a stated test.

## 5. Decision rules

- Gate A (direction): frame direction accuracy must rise with LCA/δ across the lens population as a rank trend: Spearman ρ > 0 with a one-sided p < 0.05, over lenses with known f-number and pixel pitch. Strict order between every pair of lenses is not required, because lenses with similar LCA/δ differ by noise. If the trend fails, the central claim is wrong and the paper is redesigned before any writing.
- Gate B (displacement): on withheld Δz, MAE must be below one δ for lenses with LCA above one δ. If not, the paper claims direction only and reports displacement as a negative result.
- The lab sweep cannot be used to choose features, thresholds or pooling.

## 6. Planned figures and tables

1. Principle: per-channel through-focus MTF and the chromatic ratio vs Δz (rendered and measured).
2. Pipeline: where blur is inserted, and the noise-floor check against hardware (one panel).
3. RQ1: direction accuracy vs LCA/δ and vs \|Δz\|/δ.
4. RQ2: predicted vs true Δz on withheld states; error vs \|Δz\| and field position.
5. RQ3: lab sweep, three calibration levels.
6. RQ4: threats (illuminant, scene colour, texture, noise, motion, fog).

Table 1: lens population. Table 2: all estimators on one protocol. Table 3: hardware case study.

## 7. Provenance

Every number in the paper is a macro in `paper/numbers.tex`, written by a script from result files produced at one tagged commit. Result files record the commit hash and the input data paths. Data and caches stay in `blur_study` (frozen at `defocus-estimator@4564cf2` plus the lab files of 2026-11-23) and are read by path.

## Change log

- v0, 2026-11-23: first version.
- v0.1, 2026-11-23: Gate A is a rank trend (Spearman), not strict monotonicity. Reason: the v0 re-scoring (`results/DOF_RESCORE.md`) showed adjacent-lens inversions at similar LCA/δ; decided by Brian.
- v1, 2026-11-24: approved by Brian (the merge of PR #4 counts as approval). Text unchanged from v0.1. Later changes are logged here with a date and a reason.
