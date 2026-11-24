# Lab test: chart-half transfer versus step interpolation (exploratory, after the freeze)

- **Status:** exploratory, run after the single held-out evaluation, with Brian's approval (item 10 of the round-1 review). The rule is the frozen `calibration` level of `src/lab_test.py` at `method-freeze-v1`, unchanged. The held-out test split is **not** re-evaluated; its row is read from the committed `results/lab_test/lab_test_frames.csv`.
- **Command:** `python src/lab_transfer.py --estimator ~/blur_study --out results/lab_transfer`. Input `lab_feat_real_all.parquet` SHA-256 prefix `ee9ec9b4`, the same file as the lab test.
- **Why:** the test split differs from the calibration split in both chart half and focus step, so its near-focus failure could come from either. Each subset below changes one factor only, and neither overlaps the test split.

| Subset | Half | Steps | Direction, all | Within 2 δ | Beyond 2 δ | MAE (δ) | Bias (δ) |
|---|---|---|---|---|---|---:|---:|
| In-sample (reference; the curve passes through these frames, so MAE is trivially 0) | left | s mod 4 = 0 | 19/20 | 5/6 | 14/14 | 0.00 | 0.00 |
| Other steps | left | s mod 4 ≠ 0 | 55/59 | 16/19 | 39/40 | 0.09 | −0.01 |
| Other half | right | s mod 4 = 0 | 16/20 | 3/6 | 13/14 | 1.06 | +1.02 |
| Test split (committed, not re-run) | right | s mod 4 ≠ 0 | 46/59 | 10/19 | 36/40 | 1.03 | +0.96 |

Cue offset (`lab_transfer_offsets.csv`): at the same calibration steps, the right half's chromatic cue c is higher than the left half's by a median of 0.116 within 2 δ of focus (6 steps), against 0.011 over all 20 steps. A threshold refit on the right-half calibration steps alone would be −0.184, against −0.174 from the left half: the halves differ near focus, not in a global offset that one threshold could absorb.

**Findings**
1. **Step interpolation is not the problem.** On the calibration half, the frozen rule carries to the steps it never saw almost unchanged (55/59 direction, MAE 0.09 δ).
2. **The change of chart half accounts for the test-split failure.** At the very steps used for calibration, the other half reproduces the test split's pattern: about half right within 2 δ (3/6 against 10/19), and MAE and bias of about 1 δ.
3. **Mechanism (interpreted):** near focus the cue depends on chart content and field position, not only on focus; far from focus the focus term dominates. A calibration made on one scene region carries to another only away from focus.

**Limits:** one static chart and one sweep. Consecutive steps are not independent samples, so no intervals are given; the near-focus counts are 6 and 19 frames.
