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
| Step size (estimate) | About 3.7 µm image-side per step (3.6-3.8 for peak step 46-48); depth of focus 13.8 µm is about 3.7 steps; full travel about 297 µm, implying a minimum focus distance of about 13 cm | Thin-lens estimate, see consequence 1 |
| Frames per step | 30 captured; only frame 0 (`<step>-0.raw`) is in `blur_study` | Paper II-A; file listing |
| Peak focus (paper) | Step 46-48 of 80 by SFR50, depending on demosaic; the local file names use 2 x step index (peak near file step 90-96) | Paper III-B; `lab_sweep_mtf.csv` |

## Consequences for the new paper

1. Focus steps are servo positions on the lens's focus ring, not a calibrated stage. The step size is estimated, not measured: with f = 6 mm and the chart at u = 300 mm, best focus lies f^2 / (u - f) = 122 µm beyond the infinity position; the chart peaks at step 47 of 80, and step 80 is infinity, so 33 equal steps span 122 µm, 3.7 µm per step. It assumes that step 80 is exactly infinity, that 30 cm is measured from the lens, and that the helicoid moves the lens linearly with ring angle (true of a single-thread helicoid; equal servo steps are confirmed). It must be reported as an estimate until checked against the data: fit the measured through-focus MTF fall-off with a defocus-plus-diffraction model at N = 2, c = 3.45 µm (depth of focus 2Nc = 13.8 µm), which gives µm per step independently of the geometry.
2. The off-chart wall is only a few cm behind the chart (Brian, 2026-11-23), so its best focus differs from the chart's by about 8-18 µm, 2-5 steps at 3.7 µm per step. It cannot calibrate the step size. The proposal's "in focus near step 112" for the wall has no traceable source and is unverified.
3. The 29 repeat frames per step would give measurement repeatability (and a proper noise test) without new captures. They are not on disk here.
4. The published paper already reports a direction-dependent difference between demosaic methods: before peak focus some methods measure higher SFR, after peak focus others do (Section IV), and the peak step shifts by 1-2 steps with processing. A per-channel focus shift (LCA) is one candidate explanation and is testable on these data.

## Open items for Brian

- Lens make and model (gives LCA and the datasheet minimum focus distance, a check on the step-size estimate).
- Whether the 29 repeat frames per step still exist.
