# M8: in-focus motion blur and fog vs the signed estimate

Script: `src/m8_confounds.py`. Inputs are defocus-estimator caches at commit `4564cf2` (uncommitted local changes; SHA-256 prefixes below) and one confound set rendered for this study with the frozen `confound_robotcar.py`.

| Lens | Ladder cache | Confound caches | Motion blur | Fog transmission | Plates scored |
|---|---|---|---|---|---|
| synth_lcaP (f/2.0, 5.5 µm pitch; LCA 40 µm = 1.82 δ) | `rc_feat_robotcar_render_synth_lcaP_pre_all` `b4083e9a` | rendered here: `confound_robotcar.py --lens synth_lcaP`, motion `5f6ebb39`, fog `c51f9cf0` | 3.17 px at 20° | 0.956 | 245 |
| Laikin (no recorded f-number or pitch) | `rc_feat_robotcar_render_laikin_pre_all` `d983ec14` | defocus-estimator's own: motion `2dc7a661`, fog `66a0c5c4` | 5.75 px at 20° | 0.934 | 219 (traversals in the ladder) |

Both confounds are applied to in-focus frames (DZ = 0). Their strength is matched to a DZ = +0.02 defocus in 90th-percentile gradient. For synth_lcaP, DZ +0.02 is 20 µm, which is 0.91 δ.

## Method

This is the physics baseline as in `physics_baseline.py`: frame medians of the red/blue Tenengrad ratio c and of the log luminance gradient.
- Calibration uses the 9-rung ladder of the training traversals; scoring uses the held-out traversals (five traversal-disjoint folds).
- An "alarm" is |predicted Δz| above the 95th percentile of |predicted Δz| on the same fold's in-focus frames, so the in-focus alarm rate is about 5% by construction.
- No texture threshold is applied, so nothing abstains; this matches the M2/M3 gates.

## Results

| Condition | synth_lcaP: alarm | synth_lcaP: \|Δz\| ≥ 10 µm | synth_lcaP: direction "+" | synth_lcaP: median Δz (µm) | Laikin: alarm | Laikin: direction "+" |
|---|---:|---:|---:|---:|---:|---:|
| In focus | 0.053 | 0.061 | 0.118 | 0 | 0.068 | 0.037 |
| Defocus −20 µm (−0.91 δ) | 0.580 | 0.951 | 0.000 | −20 | 0.009 | 0.000 |
| Defocus +20 µm (+0.91 δ) | 0.576 | 0.992 | 1.000 | +20 | 0.110 | 0.826 |
| Motion blur, in focus | 0.163 | 0.184 | 0.592 | +4 | 0.301 | 0.511 |
| Fog, in focus | 0.106 | 0.167 | 0.192 | +1 | 0.237 | 0.005 |

Full table: `*/m8_summary.csv`; per frame: `*/m8_frames.csv`.

## Findings

1. **synth_lcaP: the confounds raise false alarms, but far less than a matched defocus does.** With LCA at 1.82 δ, motion blur trips the alarm on 16% of in-focus frames and fog on 11%, against 5% for clean in-focus frames. A defocus of equal apparent blur trips it on 58%, with the direction right on 100% of frames.
2. **The sign is biased under motion blur.** Motion blur moves c from 0.19 (in focus) to 0.03, between the in-focus and +20 µm values (−0.45). 93% of motion-blurred frames get a positive Δz estimate, but small: median +4 µm, 0.18 δ. Fog moves c less (0.14).
3. **Laikin: the confounds trip the alarm more often than the matched defocus does.** Laikin's ±0.02 defocus is barely separable from focus (alarm on 1% and 11% of frames), while motion blur and fog trip it on 30% and 24%. A lens with weak LCA does not tell a confound from defocus at this level. Its ladder is in nominal units only, so its LCA/δ is unknown.
4. **Scope.** These are rendered confounds on two lenses at one strength each, matched to DZ +0.02. They are not a hardware result.
