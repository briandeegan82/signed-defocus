# Literature review: signed defocus from longitudinal chromatic aberration

Search date: 2026-11-23. Type: scoping review for the novelty claim, not a systematic review.

## 1. Question

Has anyone already estimated the sign (direction) and size of a camera's focus error from a single image using longitudinal (axial) chromatic aberration (LCA), and has anyone done it for in-service monitoring of fixed-focus cameras?

## 2. Method

- Crossref (`query.bibliographic`, 25 rows per query, 8 rows for targeted queries), 26 queries; raw responses in `sources/crossref_*.json`.
- arXiv web search, 4 queries; raw pages in `sources/arxiv_*.html`.
- Semantic Scholar returned HTTP 429 for all 6 queries; not used. OpenAlex not used (429 after one query earlier).
- Screening by title, then by Crossref metadata. Authors, titles, venues, volumes and pages of every cited item were checked against its Crossref DOI record (`sources/crossref_doi_records.json`) or, for [21], its arXiv page.
- Limitation: Crossref returned no abstracts for most items, and no full text was read except [1]. What each work claims below is inferred from its title and venue, and is marked "title only". These works must be read in full before the paper relies on them.

## 3. Findings

### 3.1 The cue itself is known, in three separate fields

| Field | Works | What they do (verification level) |
|---|---|---|
| Vision science | Kruger and Pola 1986 [2]; Flitcroft 1989 [3]; Seidemann and Schaeffel 2002 [4]; Rucker and Wallman 2009, 2012 [5], [6]; Rucker et al. 2020 [7]; Kruger 2012 [8] | The eye uses LCA as a cue to the sign of defocus, for accommodation and for emmetropization (titles state this directly, e.g. [6] "Chicks use changes in luminance and chromatic contrast as indicators of the sign of defocus"; title only) |
| Microscopy | Fuller et al. 2011 [9] | Image-based microscope autofocus that exploits chromatic aberration (title only). Closest engineering precedent; must be read first |
| Chromatic depth from defocus | Garcia et al. 2000 [10]; Trouvé et al. 2012, 2013 [11], [12]; Atif and Jähne 2013 [13]; Chakrabarti and Zickler 2012 [14]; Zia et al. 2021 [15]; Zhao et al. 2025 [16] | Scene depth from one image using the different focus of the colour channels; [12] combines LCA with depth from defocus, which removes the front/behind-focus ambiguity of ordinary single-image depth from defocus (title only; [16] abstract read) |
| Extended depth of field | Guichard et al. 2009 [17]; Cossairt and Nayar 2010 [18] | Use LCA on purpose and transfer sharpness between channels (title only) |

Depth from defocus without colour is sign-ambiguous from one image unless the aperture or optics are coded [19], [20], [21] or a dual-pixel sensor is used [22]; these are context, not competitors.

### 3.2 Fixed-focus automotive cameras

| Works | Relevance |
|---|---|
| Pandey et al. 2025 [23] | Age-induced defocus of automotive cameras and its effect on object detection: establishes that focus drifts in service (title only) |
| Wang et al. 2022 [24] | Local sharpness failure detection of camera-module lenses from image blur assessment (title only) |
| IEEE Std 2020-2024 [25] | Automotive image-quality standard; reference for SFR-based focus metrics |
| Deegan et al. 2024 [1] | Source of the lab sweep; SFR from raw Bayer data; the measured peak-focus step depends on processing (full text read) |
| Jakab et al. 2026 [26] | Optical simulation and image quality for automotive segmentation, in OJVT (title only) |
| Pertuz et al. 2013 [27] | Survey of unsigned focus measures (Laplacian variance, Tenengrad), our unsigned baselines |

No work found estimates the signed focus error of a fixed-focus vehicle camera from its own image stream. This is a "not found in 30 queries" statement, not proof of absence.

## 4. Consequences for the proposal

1. The paper cannot claim that LCA gives the sign of defocus. That is established in vision science [2]-[8], used in microscope autofocus [9] and in chromatic depth from defocus [10]-[16].
2. What remains open, as far as this search shows:
   - Monitoring a camera's own focus state (sensor displacement, scene mostly far away) rather than scene depth.
   - How direction accuracy scales with LCA relative to depth of focus, across a population of lenses that includes well-corrected ones.
   - How much calibration a deployed camera needs (none, channel order, one sweep).
   - Behaviour through a raw-Bayer pipeline and under automotive confounds.
3. Proposed change to the working title: drop the implication that the cue is new. For example: "How much chromatic aberration does a fixed-focus camera need to report the direction of its own focus error?"
4. Read in full before writing: [9], [12], [14], [10], [23]. If [9] or [12] already quantify accuracy against LCA, research question 1 must be narrowed to the automotive regime.

## 5. Not yet searched

IEEE Xplore and Google Scholar directly (no API access); patents (camera-module active alignment and in-field focus diagnostics are often patented); phase-detection autofocus literature; arXiv beyond the four queries.

## References

[1] B. Deegan, D. Molloy, J. Cahill, D. Mullins, E. Ward, E. Jones, and M. Glavin, "The influence of Bayer demosaic algorithms on spatiotemporal frequency response measurements," IEEE Access, vol. 12, pp. 163958-163977, 2024, doi:10.1109/ACCESS.2024.3491413.
[2] P. B. Kruger and J. Pola, "Stimuli for accommodation: Blur, chromatic aberration and size," Vision Res., vol. 26, no. 6, pp. 957-971, 1986, doi:10.1016/0042-6989(86)90153-7.
[3] D. I. Flitcroft, "The interactions between chromatic aberration, defocus and stimulus chromaticity: Implications for visual physiology and colorimetry," Vision Res., vol. 29, no. 3, pp. 349-360, 1989, doi:10.1016/0042-6989(89)90083-7.
[4] A. Seidemann and F. Schaeffel, "Effects of longitudinal chromatic aberration on accommodation and emmetropization," Vision Res., vol. 42, no. 21, pp. 2409-2417, 2002, doi:10.1016/S0042-6989(02)00262-6.
[5] F. J. Rucker and J. Wallman, "Chick eyes compensate for chromatic simulations of hyperopic and myopic defocus: Evidence that the eye uses longitudinal chromatic aberration to guide eye-growth," Vision Res., vol. 49, no. 14, pp. 1775-1783, 2009, doi:10.1016/j.visres.2009.04.014.
[6] F. J. Rucker and J. Wallman, "Chicks use changes in luminance and chromatic contrast as indicators of the sign of defocus," J. Vision, vol. 12, no. 6, art. 23, 2012, doi:10.1167/12.6.23.
[7] F. Rucker, R. Eskew, and C. Taylor, "Signals for defocus arise from longitudinal chromatic aberration in chick," Exp. Eye Res., vol. 198, 108126, 2020, doi:10.1016/j.exer.2020.108126.
[8] P. B. Kruger, "Chromatic aberration as a possible cue to specify the sign of defocus in the eye," in Frontiers in Optics, paper FTu4G.2, 2012, doi:10.1364/FIO.2012.FTu4G.2.
[9] D. N. Fuller, A. L. Kellner, and J. H. Price, "Exploiting chromatic aberration for image-based microscope autofocus," Appl. Opt., vol. 50, p. 4967, 2011, doi:10.1364/AO.50.004967.
[10] J. Garcia, J. M. Sanchez, X. Orriols, and X. Binefa, "Chromatic aberration and depth extraction," in Proc. 15th Int. Conf. Pattern Recognit. (ICPR), vol. 1, pp. 762-765, 2000, doi:10.1109/ICPR.2000.905499.
[11] P. Trouvé, F. Champagnat, G. Le Besnerais, G. Druart, and J. Idier, "Chromatic depth from defocus: A theoretical and experimental performance study," in Imaging and Applied Optics, paper CM3B.3, 2012, doi:10.1364/COSI.2012.CM3B.3.
[12] P. Trouvé, F. Champagnat, G. Le Besnerais, J. Sabater, T. Avignon, and J. Idier, "Passive depth estimation using chromatic aberration and a depth from defocus approach," Appl. Opt., vol. 52, p. 7152, 2013, doi:10.1364/AO.52.007152.
[13] M. Atif and B. Jähne, "Optimal depth estimation from a single image by computational imaging using chromatic aberrations," tm - Technisches Messen, vol. 80, 2013, doi:10.1524/teme.2013.0042.
[14] A. Chakrabarti and T. Zickler, "Depth and deblurring from a spectrally-varying depth-of-field," in Proc. ECCV, LNCS, pp. 648-661, 2012, doi:10.1007/978-3-642-33715-4_47.
[15] A. Zia, J. Zhou, and Y. Gao, "Exploring chromatic aberration and defocus blur for relative depth estimation from monocular hyperspectral image," IEEE Trans. Image Process., vol. 30, pp. 4357-4370, 2021, doi:10.1109/TIP.2021.3071682.
[16] Z. Zhao et al., "Depth estimation from hyperspectral images based on chromatic aberration," Opt. Express, vol. 33, p. 47439, 2025, doi:10.1364/OE.576592.
[17] F. Guichard, H.-P. Nguyen, R. Tessières, M. Pyanet, I. Tarchouna, and F. Cao, "Extended depth-of-field using sharpness transport across color channels," Proc. SPIE, vol. 7250, 72500N, 2009, doi:10.1117/12.805915.
[18] O. Cossairt and S. Nayar, "Spectral focal sweep: Extended depth of field from chromatic aberrations," in Proc. IEEE ICCP, 2010, doi:10.1109/ICCPHOT.2010.5585101.
[19] A. Levin, R. Fergus, F. Durand, and W. T. Freeman, "Image and depth from a conventional camera with a coded aperture," ACM Trans. Graph., vol. 26, no. 3, art. 70, 2007, doi:10.1145/1276377.1276464.
[20] H. Haim, S. Elmalem, R. Giryes, A. M. Bronstein, and E. Marom, "Depth estimation from a single image using deep learned phase coded mask," IEEE Trans. Comput. Imaging, vol. 4, no. 3, pp. 298-310, 2018, doi:10.1109/TCI.2018.2849326.
[21] J. Chang and G. Wetzstein, "Deep optics for monocular depth estimation and 3D object detection," arXiv:1904.08601, 2019 (published version, ICCV 2019, to be confirmed).
[22] R. Garg, N. Wadhwa, S. Ansari, and J. Barron, "Learning single camera depth estimation using dual-pixels," in Proc. IEEE/CVF ICCV, pp. 7627-7636, 2019, doi:10.1109/ICCV.2019.00772.
[23] A. Pandey, S. Kühn, M. Kettelgerdes, B. Wunderle, and G. Elger, "Estimating the effect of age-induced defocus on object detection performance of automotive cameras," Results Eng., vol. 27, 105951, 2025, doi:10.1016/j.rineng.2025.105951.
[24] F. Wang, J. Chen, Z. Xie, Y. Ai, and W. Zhang, "Local sharpness failure detection of camera module lens based on image blur assessment," Appl. Intell., vol. 53, pp. 11241-11250, 2022, doi:10.1007/s10489-022-03948-9.
[25] IEEE Standard for Automotive System Image Quality, IEEE Std 2020-2024, doi:10.1109/IEEESTD.2024.10935839.
[26] D. Jakab et al., "Optical simulation and image quality for automotive semantic segmentation," IEEE Open J. Veh. Technol., vol. 7, pp. 1788-1803, 2026, doi:10.1109/OJVT.2026.3702262.
[27] S. Pertuz, D. Puig, and M. A. Garcia, "Analysis of focus measure operators for shape-from-focus," Pattern Recognit., vol. 46, no. 5, pp. 1415-1432, 2013, doi:10.1016/j.patcog.2012.11.011.
