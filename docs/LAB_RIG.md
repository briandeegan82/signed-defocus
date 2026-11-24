# Lab through-focus sweep: rig record (experiment M1)

Source: B. Deegan et al., "The Influence of Bayer Demosaic Algorithms on Spatiotemporal Frequency Response Measurements," IEEE Access, vol. 12, pp. 163958-163977, 2024, doi:10.1109/ACCESS.2024.3491413 (Section II-A and Figs. 6-7). The data in `blur_study/data/lab_images/raw/` are frame 0 of that sweep.

| Item | Value | Source |
|---|---|---|
| Camera | FLIR Blackfly BFS-U3-89S6C, colour (the paper prints "89s6M") | Paper II-A; colour model confirmed by Brian, 2026-11-23 |
| Sensor | Sony IMX255, 4096 x 2160 | Paper II-A; frame size in `lab_sweep.py` |
| Pixel pitch | 3.45 µm (IMX255 datasheet value; not stated in the paper; to confirm) | Datasheet, not yet checked |
| Lens | 6 mm focal length, f/2.0, C-mount, focused by its own focus ring; make and model not stated | Paper II-A; C-mount confirmed by Brian, 2026-11-23 |
| Object distance | 30 cm, ISO 12233:2017 e-SFR chart (Imatest) | Paper II-A |
| Illumination | Two LED panels, CCT 5000 K, 500 lux at the target | Paper II-A |
| Exposure | 32 ms, 0 dB gain, linear OECF, white balance by on-sensor digital gains | Paper II-A, II-B |
| Focus mechanism | 3D-printed focus ring driven by an Arduino-controlled servo; 80 equal steps over the full focus range, from minimum focus distance to infinity; the ring turns 90 degrees over the sweep | Paper II-A, Fig. 7, III-B; equal steps and 90 degrees confirmed by Brian, 2026-11-23 |
| Step size | Measured from the MTF fall-off: 0.154 δ per step (δ is about 6.5 steps), whatever the f-number; 2.1 µm per step if the lens was at f/2 (1.85-2.30 over fit variants), 3.0 µm at f/2.8. The thin-lens geometry estimate (3.7 µm per step, assuming step 80 is infinity) matches only at about f/3.5 | `results/lab_sweep/LAB_SWEEP.md`; consequence 1 |
| Frames per step | 30 captured; only frame 0 (`<step>-0.raw`) is in `blur_study` | Paper II-A; file listing |
| Peak focus (paper) | Step 46-48 of 80 by SFR50, depending on demosaic; the local file names use 2 x step index (peak near file step 90-96) | Paper III-B; `lab_sweep_mtf.csv` |

## Consequences for the new paper

1. Focus steps are servo positions on the lens's focus ring, not a calibrated stage. Two estimates of the step size disagree unless the iris was stopped down. The geometry estimate: with f = 6 mm and the chart at u = 300 mm, best focus lies f^2 / (u - f) = 122 µm beyond the infinity position; if step 80 is infinity, the 33 steps after the chart peak (step 47) give 3.7 µm per step. The MTF fit (exact defocus OTF, per-channel SFR at 0.125 and 0.25 cy/px) measures k / N = 1.07 µm per step per unit f-number, so 2.1 µm per step at f/2. At f/2 the sweep would end at about 0.7 m, not infinity; the two agree at about f/3.5. The depth of focus in steps does not depend on N: δ = 2Nc is about 6.5 steps. Results in δ units are therefore measured; results in µm need the iris setting.
2. The off-chart wall peaks 10.3 steps after the chart (file step 112-114, `hf_wall_raw` in `lab_sweep_mtf.csv`; the source of the proposal's "near step 112"). That is 22 µm at 2.1 µm per step, a wall about 6 cm behind the chart, or 38 µm and about 13 cm at 3.7 µm per step. Brian recalls a few cm (2026-11-23), which fits the MTF fit better. Field curvature does not explain the offset: the chart corners peak at most one step after the centre.
3. The 29 repeat frames per step would give measurement repeatability (and a proper noise test) without new captures. They are not on disk here.
4. The published paper already reports a direction-dependent difference between demosaic methods: before peak focus some methods measure higher SFR, after peak focus others do (Section IV), and the peak step shifts by 1-2 steps with processing. A per-channel focus shift (LCA) is one candidate explanation and is testable on these data.

## Open items for Brian

- The iris (f-number) setting during the sweep. It converts the measured step size to µm.
- Lens make and model (gives LCA and the datasheet minimum focus distance, a check on the step-size estimate).
- Whether the 29 repeat frames per step still exist.
