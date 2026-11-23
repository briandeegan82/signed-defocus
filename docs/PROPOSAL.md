# Proposal: one paper on signed defocus estimation (fresh start)

Status: revision 2, after Brian's decisions of 2026-11-23 (no new lab captures; target IEEE OJVT; physics-based method; new repository). Nothing in `~/blur_study` was changed. Evidence below was read from the repo at commit `4564cf2` plus the uncommitted lab results of 2026-11-23. All numbers are existing measurements, quoted to show what is known; none would be carried into the new paper without a re-run under one frozen code version.

## 1. What went wrong (so the new paper avoids it)

| Problem | Evidence in the repo |
|---|---|
| No fixed question | 9 `FINDINGS*.md` threads (KITTI, noise, lens, MTL, soiling, weather, VKITTI, deploy, features), 183 scripts, 2 papers plus a third copy |
| Headline moved with each experiment | Content gap, then ISP insertion point, then "the lens is the domain gap", then pooling, then sign |
| Circular validation | Labels, training data and test data all come from the same renderer and the same 9-rung ladder; the estimator is scored on states it was trained on |
| Signed defocus, the original idea, is a sub-section | `sec/6_sign.tex`; the title and abstract are about domain gaps |
| Rank correlation hides the measurement | Frame SROCC 0.987, but 0.048 MTF bias and 20.8 µm error once rungs are withheld (10 µm ladder step) |
| Numbers from many code versions | `*_superseded_labels.csv`, two label-provenance fixes, two bug fixes that had produced perfect scores |

## 2. What the data actually supports

**Sound and worth keeping**
1. Direction (sign of Δz) is recoverable from one image when the lens has longitudinal chromatic aberration (LCA): CHROMA, 6 features, 0.980 patch accuracy on the Laikin render; 1.000 frame accuracy on the real lab sweep at every distance bin, including 2-10 steps from focus.
2. Direction follows channel order, not lens identity: flipping only the LCA sign in a matched synthetic pair moves accuracy 0.955 -> 0.045. On real hardware a Laikin-trained classifier scores 0.10 raw and 0.90 once the sign is aligned. Lenses with LCA under the 10 µm step sit at chance.
3. Without a sign, displacement error has a long tail: 35.6 µm vs 8.2 µm (rendered); 40 vs 15 stage steps (lab).
4. Blur must be inserted before the ISP for training data to transfer: the flat-region noise floor changes 1.04x through focus on real hardware, 1.3x in the pre-ISP render and 5.5x in the post-ISP render; post-ISP-trained SDFE falls to 0.78 frame SROCC on real data vs 0.965 for pre-ISP.

**Weak, and the new paper must face it**
1. Magnitude estimation is not a contribution. On the real sweep, untrained Laplacian variance reaches 0.981 frame SROCC; SDFE reaches 0.965 and fine-tuned ResNet-50 0.979.
2. Absolute calibration does not transfer: MTF error on real hardware is 0.23-0.55 on a 0.02-0.49 range for every model.
3. The estimator memorises rungs: withholding a rung gives 6.8-46.9 µm error; pooled 20.8 µm.
4. It does not track field position: predicted centre/corner ratio 1.05 vs measured 2.01.
5. Only 3 of 16 cached lens designs have measurable LCA, so the dependence on LCA has two or three data points.
6. Real data is one lens, one chart, one session, and the rig (camera, lens, f-number, pixel pitch, stage step in µm) is not recorded in the code.

**Dropped from this paper**: KITTI/WoodScape/PDW post-ISP results, weather, soiling, multi-task learning, detection link, IQA baselines, the 14-group feature study, the pooling experiments, and the causal noise-floor chain (kept as one methods paragraph and one validation figure).

## 3. Proposed paper

**Working title:** Signed defocus estimation from a single image using longitudinal chromatic aberration: when it works, and how much calibration it needs.

**Claim to test (one sentence):** For a fixed-focus camera, the residual LCA of the lens makes the sign and size of a focus shift measurable from ordinary images, with accuracy set by the ratio of LCA to depth of focus, and a model built on rendered data agrees with one real through-focus sweep given the lens's channel order and a through-focus calibration.

### Research questions

| # | Question | Primary metric (fixed in advance) |
|---|---|---|
| RQ1 | How does direction accuracy depend on LCA magnitude, relative to depth of focus, and on distance from best focus? | Frame and patch direction accuracy vs LCA/DoF and vs \|Δz\|/DoF, with 95% CI over scene-disjoint folds |
| RQ2 | How accurately is signed displacement estimated at defocus states never seen in training? | Signed error in µm and in DoF units (bias, MAE, p90) on withheld Δz |
| RQ3 | On the one real lens available, what is the least calibration needed to move from rendered data to hardware: none, the channel order (1 bit), or part of a through-focus sweep? | Same metrics as RQ1-2 on the 80-step lab sweep, three calibration levels, calibration and test steps disjoint. Reported as a single-lens hardware case study |
| RQ4 | What breaks the chromatic cue in service: illuminant, scene colour, low texture, noise, motion blur? (simulation only) | Direction accuracy and abstain rate per condition; false-alarm rate on in-focus frames |

RQ1-RQ3 are the paper. RQ4 is limited to the listed conditions and can be cut to a limitations section if space runs out.

### Scope

- In: fixed-focus cameras, defocus of the whole image plane, Bayer sensor, a documented simple ISP, natural driving scenes plus a lab chart, a lens population with controlled LCA.
- Out: depth-from-defocus, autofocus, dual-pixel sensors, deblurring, downstream detection accuracy, weather and soiling, benchmark-corruption critique (possible separate paper later, not started until this one is done).

### Method (physics-based) and comparisons

1. The method: per-channel sharpness measured on edges and texture, combined into chromatic ratios, mapped to signed displacement by a through-focus model derived from the lens's per-channel MTF curves. A few interpretable numbers per patch, no learned representation; the only fitted parts are a monotone calibration and the pooling rule.
2. Unsigned floor: Laplacian variance and Tenengrad.
3. Reference points only, from the existing work and re-run once: SDFE (magnitude + CHROMA) and a two-output CNN. They answer "does a learned model do better?" and take one table.

## 4. Missing experiments

| # | Experiment | Why it is needed | Cost |
|---|---|---|---|
| M1 | Record the lab rig: camera, lens, f-number, pixel pitch, illuminant, stage step in µm | Without it the real data has no physical units and DoF cannot be computed | Minutes (Brian) |
| M2 | Continuous defocus rendering: Δz drawn at random over the range instead of 9 rungs | Fixes rung memorisation; required for RQ2 | Re-render; gate on a 40-frame subset first |
| M3 | LCA dose-response population: synthetic lenses with LCA from 0 to about 60 µm in 6-8 steps, both signs, with and without spherical aberration | RQ1 currently rests on 3 lenses | Lens synthesis exists (`lens_lca_probe.py`); render + extract |
| M4 | Hardware protocol on the existing 80-step sweep: split steps and chart halves into calibration and test; measure per-channel through-focus MTF from the slanted edges; repeatability from the duplicate frames in `archives/duplicates` if they are true repeats | Only real data available, so every use of it must be planned once and not reused for tuning | Analysis only |
| M5 | Natural-content check without new captures: (a) render natural plates through a lens model matched to the lab lens's measured per-channel curves; (b) test whether the off-chart wall region (in focus near step 112) has enough texture to serve as a second object distance | The chart is the easiest content for any focus measure; (b) may fail and is then stated as a limitation | Small render + analysis |
| M6 | Illuminant and scene-colour test, simulation only: shifted white balance and illuminant spectra, strongly coloured edges | Main threat to the chromatic cue; cannot be tested on hardware, so it is stated as a simulation result | Small render |
| M7 | Field position: evaluate at centre, mid and corner with field-varying PSFs and the 11 chart squares | Current model does not track field variation; lateral colour may corrupt the cue off-axis | Field-varying render exists for one lens |
| M8 | Confound gate on the signed output: in-focus motion blur and fog | Existing result: 97.6% false alarms on motion-blurred in-focus frames for the unsigned estimator | Renders exist |
| M9 | One frozen re-run of every reported number, all folds, all three estimators | Removes mixed code versions and fold-0-only rows | Compute only |

## 5. Plan

| Phase | Work | Gate to continue |
|---|---|---|
| 0. Protocol | Write the protocol: RQs, metrics, splits, estimators, exclusion rules, the figure and table list. New clean paper directory with a README, generated number macros, one figure script per figure | Brian approves the protocol |
| 1. Cheap gates | M1; M3 on a small frame subset; M2 on 40 frames; physics-baseline estimator on existing lab and render caches | (a) direction accuracy rises monotonically with LCA/DoF; (b) withheld-Δz error falls well below the current 20.8 µm. If (b) fails, the paper is re-scoped to direction only |
| 2. Data | Full M2 and M3 renders; lab captures M4-M6; M7-M8 from existing renders | Data complete and logged with commit hashes |
| 3. Analysis | M9: all numbers from one tagged commit; confidence intervals over folds and lenses | Every claim in the outline has a number or is deleted |
| 4. Writing | Draft against the fixed figure list; the outline is written before the results text | Builds clean |
| 5. Review | 3-4 independent reviewer agents, including one that audits every number against the macros | Ranked fix list agreed |

## 6. Decisions taken (2026-11-23)

| Decision | Outcome | Consequence |
|---|---|---|
| New lab captures | Not possible | Hardware evidence is one lens, one chart, one session; RQ3 is a case study; illuminant and natural-content questions are answered in simulation |
| Venue | IEEE OJVT | IEEEtran journal format; check current author instructions before formatting |
| Method | Physics-based | Chromatic sharpness-ratio estimator leads; learned models are reference rows |
| Location | New repository `signed-defocus` | Reads caches and renders from `blur_study` by path; old repo is frozen and cited by commit |

## 7. Still needed from Brian

The lab rig record (M1): camera or sensor, pixel pitch, lens, f-number, illuminant, and the focus-stage step in µm. Without the step size the hardware results stay in stage steps.
