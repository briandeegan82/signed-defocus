"""Generate qualitative comparison crops for in-focus, lens defocus, motion blur, and fog.

Uses the exact same pre-ISP rendering pipeline and confound calibration as the M8 study
(synth_lcaP, f/2.0, 5.5 um pitch, LCA 1.82 delta; matched to +0.02 DZ = +0.91 delta):
  - Default (in focus): DZ = 0.0
  - Lens defocus:       DZ = +0.02 (+0.91 delta)
  - Motion blur:        2.03 px at 20 deg convolved with in-focus optical PSF
  - Fog:                uniform neutral veiling airlight t = 0.956, A = 220 DN (inverse-WB scaled)

Saves a compact npz to results/figures/data/confound_examples.npz so src/fig_confound_examples.py
can redraw the figure without raw RobotCar data.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

import m2_continuous as M2
import m8_confound_render as M8R

ROOT = Path(__file__).resolve().parents[1]
MOTION_LEN = 2.03125
MOTION_ANG = 20.0
FOG_TRANS = 0.95625


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--noise-model", type=Path, required=True)
    ap.add_argument("--plate", type=int, default=12)
    ap.add_argument("--crop", type=int, default=320)
    ap.add_argument("--crop-yx", type=int, nargs=2, default=[380, 680],
                    help="crop top-left (y0, x0) in full-res pixels")
    ap.add_argument("--out", type=Path, default=ROOT / "results/figures/data/confound_examples.npz")
    a = ap.parse_args()

    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import confound as CF
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC
    import weather_raw as WR

    # synth_lcaP = m3_ref: f/2.0, 5.5 um pitch, LCA = 40 um = 1.82 delta
    design = dict(M2.BASE, long_ca=0.2353, spherical=0.0)
    levels = [0.0, 0.02]
    LS.DZ_LEVELS = levels
    device = "cuda" if torch.cuda.is_available() else "cpu"
    psfs = M2.centre_kernels(LS.render_psfs(design, device), levels)

    groups = RC.plate_paths()
    t, p = M2.pick_plates(groups, sum(len(v) for v in groups.values()))[a.plate]
    plate = RC.load_plate(p)
    wb = RA.plate_grey_world(plate)
    model = json.loads(a.noise_model.read_text())["model"]

    seed0 = RA.stable_seed(t, p.stem, 0.0, 0)
    seed_def = RA.stable_seed(t, p.stem, 0.02, 0)
    img_focus = RA.render(plate, psfs[0.0], wb, model, "pre", seed0)
    img_defocus = RA.render(plate, psfs[0.02], wb, model, "pre", seed_def)

    mp = M8R.motion_psfs_convolved(CF, MOTION_LEN, MOTION_ANG, psfs[0.0])
    img_motion = RA.render(plate, mp, wb, model, "pre", RA.stable_seed(t, p.stem, 99.0, 0))

    foggy = M8R.fog_bayer_neutral(WR, plate, FOG_TRANS, wb)
    img_fog = RA.render(foggy, psfs[0.0], RA.plate_grey_world(foggy), model, "pre",
                        RA.stable_seed(t, p.stem, 98.0, 0))

    n = a.crop
    y0, x0 = a.crop_yx[0] - a.crop_yx[0] % 2, a.crop_yx[1] - a.crop_yx[1] % 2
    sl = (slice(y0, y0 + n), slice(x0, x0 + n))

    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        a.out,
        meta=json.dumps(dict(
            lens="synth_lcaP", traversal=t, frame=p.stem,
            dz_defocus=0.02, dz_delta=0.9091,
            motion_len_px=MOTION_LEN, motion_angle_deg=MOTION_ANG,
            fog_transmission=FOG_TRANS, fog_airlight=220.0,
            crop_yx=[int(y0), int(x0)], crop=n,
        )),
        crop_focus=img_focus[sl],
        crop_defocus=img_defocus[sl],
        crop_motion=img_motion[sl],
        crop_fog=img_fog[sl],
    )
    print(f"Saved {a.out}: plate {t}/{p.stem}, crop {n}x{n} at ({y0},{x0})")


if __name__ == "__main__":
    main()
