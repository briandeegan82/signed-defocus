# Lab through-focus sweep: rig record (experiment M1)

Source: B. Deegan et al., "The Influence of Bayer Demosaic Algorithms on Spatiotemporal Frequency Response Measurements," IEEE Access, vol. 12, pp. 163958-163977, 2024, doi:10.1109/ACCESS.2024.3491413 (Section II-A and Figs. 6-7). The data in `blur_study/data/lab_images/raw/` are frame 0 of that sweep.

| Item | Value | Source |
|---|---|---|
| Camera | FLIR Blackfly BFS-U3-89S6 (the paper prints "89s6M"; the data are RGGB Bayer, so this is presumably the colour model, BFS-U3-89S6C; to confirm) | Paper II-A |
| Sensor | Sony IMX255, 4096 x 2160 | Paper II-A; frame size in `lab_sweep.py` |
| Pixel pitch | 3.45 µm (IMX255 datasheet value; not stated in the paper; to confirm) | Datasheet, not yet checked |
| Lens | 6 mm focal length, f/2.0; make and model not stated | Paper II-A |
| Object distance | 30 cm, ISO 12233:2017 e-SFR chart (Imatest) | Paper II-A |
| Illumination | Two LED panels, CCT 5000 K, 500 lux at the target | Paper II-A |
| Exposure | 32 ms, 0 dB gain, linear OECF, white balance by on-sensor digital gains | Paper II-A, II-B |
| Focus mechanism | 3D-printed focus ring driven by an Arduino-controlled servo; 80 steps over the full focus range, from minimum focus distance to infinity | Paper II-A, Fig. 7, III-B |
| Frames per step | 30 captured; only frame 0 (`<step>-0.raw`) is in `blur_study` | Paper II-A; file listing |
| Peak focus (paper) | Step 46-48 of 80 by SFR50, depending on demosaic; the local file names use 2 x step index (peak near file step 90-96) | Paper III-B; `lab_sweep_mtf.csv` |

## Consequences for the new paper

1. Focus steps are servo positions on a focus ring, not a calibrated stage. There is no direct µm calibration. Displacement in physical units has to be inferred, for example by fitting the measured through-focus MTF width to a model with the known f-number and pixel pitch (depth of focus 2Nc = 13.8 µm at N = 2, c = 3.45 µm). That conversion is an assumption and must be reported as one.
2. The servo-to-ring mapping may not be linear; uniform steps cannot be assumed to be uniform image-side displacement.
3. The 29 repeat frames per step would give measurement repeatability (and a proper noise test) without new captures. They are not on disk here.
4. The published paper already reports a direction-dependent difference between demosaic methods: before peak focus some methods measure higher SFR, after peak focus others do (Section IV), and the peak step shifts by 1-2 steps with processing. A per-channel focus shift (LCA) is one candidate explanation and is testable on these data.

## Open items for Brian

- Lens make and model (gives LCA and the focus-ring thread pitch).
- Colour or mono camera variant.
- Whether the 29 repeat frames per step still exist.
