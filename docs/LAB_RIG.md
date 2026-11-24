# Lab through-focus sweep: rig record (experiment M1)

Source: B. Deegan et al., "The Influence of Bayer Demosaic Algorithms on Spatiotemporal Frequency Response Measurements," IEEE Access, vol. 12, pp. 163958-163977, 2024, doi:10.1109/ACCESS.2024.3491413 (Section II-A and Figs. 6-7). The data in `blur_study/data/lab_images/raw/` are frame 0 of that sweep.

| Item | Value | Source |
|---|---|---|
| Camera | FLIR Blackfly BFS-U3-89S6C, colour (the paper prints "89s6M") | Paper II-A; colour model confirmed by Brian, 2026-11-23 |
| Sensor | Sony IMX255, 4096 x 2160 | Paper II-A; frame size in `lab_sweep.py` |
| Pixel pitch | 3.45 µm (IMX255 datasheet value; not stated in the paper; to confirm) | Datasheet, not yet checked |
| Lens | VS Technology VS-0618H1: 6 mm, f/1.8 maximum aperture, C-mount, focused by its own focus ring; focus scale 0.1 m to infinity; iris scale 1.8 to 16 | Barrel markings in Brian's photos, 2026-11-24; C-mount confirmed by Brian, 2026-11-23 |
| Iris during the sweep | About f/2, set by eye on the iris scale (the paper's "f/2.0"); moved since | Brian, 2026-11-24 |
| Object distance | 30 cm, ISO 12233:2017 e-SFR chart (Imatest) | Paper II-A |
| Illumination | Two LED panels, CCT 5000 K, 500 lux at the target | Paper II-A |
| Exposure | 32 ms, 0 dB gain, linear OECF, white balance by on-sensor digital gains | Paper II-A, II-B |
| Focus mechanism | 3D-printed focus ring driven by an Arduino-controlled servo; 80 equal steps; the ring turns 90 degrees over the sweep. The paper describes this as the full focus range, but at about f/2 the sweep covers only part of the lens's 0.1 m to infinity range (consequence 1) | Paper II-A, Fig. 7, III-B; equal steps and 90 degrees confirmed by Brian, 2026-11-23 |
| Step size | Measured from the MTF fall-off: 0.154 δ per step (δ is about 6.5 steps), whatever the f-number; 2.1 µm per step at the recorded f/2 (1.85-2.30 over fit variants); 1.9 µm at f/1.8 and 3.0 µm at f/2.8 bound an eye-set iris. The thin-lens estimate of 3.7 µm per step assumed step 80 is infinity, which does not hold at f/2 | `results/lab_sweep/LAB_SWEEP.md`; consequence 1 |
| Frames per step | 30 captured; only frame 0 (`<step>-0.raw`) is in `blur_study` | Paper II-A; file listing |
| Peak focus (paper) | Step 46-48 of 80 by SFR50, depending on demosaic; the local file names use 2 x step index (peak near file step 90-96) | Paper III-B; `lab_sweep_mtf.csv` |

## Consequences for the new paper

1. Focus steps are servo positions on the lens's focus ring, not a calibrated stage. Two estimates of the step size disagree unless the iris was stopped down. The geometry estimate: with f = 6 mm and the chart at u = 300 mm, best focus lies f^2 / (u - f) = 122 µm beyond the infinity position; if step 80 is infinity, the 33 steps after the chart peak (step 47) give 3.7 µm per step. The MTF fit (exact defocus OTF, per-channel SFR at 0.125 and 0.25 cy/px) measures k / N = 1.07 µm per step per unit f-number, so 2.1 µm per step at f/2. The iris was at about f/2 (Brian, 2026-11-24), so the 80 steps move the image plane about 170 µm, under half of the lens's 0.1 m to infinity travel (about 380 µm thin-lens). With the chart in focus near step 45, the sweep runs from about 17 cm (step 0) to about 0.7 m (step 79); at f/1.8 and f/2.8 the limits are 18 cm to 0.64 m and 15 cm to 1.7 m. The 90-degree servo throw therefore covers the middle of the focus ring's travel, not its end stops. The depth of focus in steps does not depend on N: δ = 2Nc is about 6.5 steps. Results in δ units are therefore measured; results in µm need the iris setting.
2. The off-chart wall peaks 10.3 steps after the chart (file step 112-114, `hf_wall_raw` in `lab_sweep_mtf.csv`; the source of the proposal's "near step 112"). That is 22 µm at 2.1 µm per step, a wall about 6 cm behind the chart, or 38 µm and about 13 cm at 3.7 µm per step. Brian recalls a few cm (2026-11-23), which fits the MTF fit better. Field curvature does not explain the offset: the chart corners peak at most one step after the centre.
3. The 29 repeat frames per step would give measurement repeatability (and a proper noise test) without new captures. They are not on disk here.
4. The published paper already reports a direction-dependent difference between demosaic methods: before peak focus some methods measure higher SFR, after peak focus others do (Section IV), and the peak step shifts by 1-2 steps with processing. A per-channel focus shift (LCA) is one candidate explanation and is testable on these data.

## Open items for Brian

- Whether the 29 repeat frames per step still exist.
