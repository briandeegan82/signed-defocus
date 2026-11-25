"""Stage images for the rendering-pipeline figure (one RobotCar plate, one M3 design).

Runs the same calls as `m2_continuous.render` (pre-ISP arm) on one plate and keeps each stage:
raw plate -> per-channel PSF at the displacement -> blurred Bayer + measured noise -> ISP -> RGB frame.
Needs the frozen defocus-estimator checkout (plates, renderer); `src/fig_pipeline.py` then draws the
figure from the saved npz with no raw data.

  python src/fig_pipeline_data.py --estimator ~/blur_study --noise-model <json> \
      [--lens m3_p200] [--dz-delta 2.0] [--plate 0] [--crop 128]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import m2_continuous as M2

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--noise-model", type=Path, required=True)
    ap.add_argument("--lens", default="m3_p200")
    ap.add_argument("--dz-delta", type=float, default=2.0, help="displacement shown, in depths of focus")
    ap.add_argument("--plate", type=int, default=0, help="index into pick_plates order")
    ap.add_argument("--crop", type=int, default=128)
    ap.add_argument("--crop-yx", type=int, nargs=2, default=None, help="crop top-left; default = most textured")
    ap.add_argument("--out", type=Path, default=ROOT / "results/figures/data/pipeline_stages.npz")
    a = ap.parse_args()

    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC

    row = pd.read_csv(ROOT / "data/m3_lenses.csv").set_index("lens").loc[a.lens]
    design = dict(M2.BASE, long_ca=float(row.long_ca_mm_per_um), spherical=float(row.spherical))
    delta_um = 2.0 * design["f_number"] * design["pixel_pitch"]
    dz = round(a.dz_delta * delta_um / (design["defocus_scale"] * 1000.0), 4)  # nominal DZ units
    levels = [-dz, 0.0, dz]
    LS.DZ_LEVELS = levels
    device = "cuda" if torch.cuda.is_available() else "cpu"
    psfs = M2.centre_kernels(LS.render_psfs(design, device), levels)

    groups = RC.plate_paths()
    t, p = M2.pick_plates(groups, sum(len(v) for v in groups.values()))[a.plate]
    plate = RC.load_plate(p)
    wb = RA.plate_grey_world(plate)
    model = json.loads(a.noise_model.read_text())["model"]
    frames = {z: RA.render(plate, psfs[round(z, 4)], wb, model, "pre", RA.stable_seed(t, p.stem, round(z, 4), 0))
              for z in levels}
    blurred = RA.blur_bayer(plate, psfs[round(dz, 4)])

    n = a.crop
    if a.crop_yx:
        y0, x0 = a.crop_yx
    else:  # most textured n x n window of the in-focus green channel, on an n/2 grid
        g = frames[0.0][..., 1].astype(np.float64)
        e = np.gradient(g)[0] ** 2 + np.gradient(g)[1] ** 2
        best = max(((e[y:y + n, x:x + n].sum(), y, x) for y in range(0, g.shape[0] - n, n // 2)
                    for x in range(0, g.shape[1] - n, n // 2)))
        y0, x0 = best[1], best[2]
    y0, x0 = y0 - y0 % 2, x0 - x0 % 2
    sl = (slice(y0, y0 + n), slice(x0, x0 + n))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        a.out,
        meta=json.dumps(dict(lens=a.lens, traversal=t, frame=p.stem, dz_levels=levels, dz_delta=a.dz_delta,
                             delta_um=delta_um, lca_delta=abs(design["long_ca"]) * (M2.LAMBDA_R - M2.LAMBDA_B) * 1000 / delta_um,
                             crop_yx=[int(y0), int(x0)], crop=n, shape=list(frames[0.0].shape),
                             plate_dtype=str(plate.dtype), plate_max=float(plate.max()), wb=list(map(float, wb)))),
        plate_crop=np.asarray(plate)[sl], blurred_crop=np.asarray(blurred)[sl],
        frame_small=frames[0.0][::2, ::2],
        **{f"psf_{s}_{c}": psfs[round(z, 4)][c] for s, z in (("neg", -dz), ("pos", dz)) for c in "rgb"},
        **{f"crop_{s}": frames[z][sl] for s, z in (("neg", -dz), ("zero", 0.0), ("pos", dz))})
    print(f"{a.lens} plate {t}/{p.stem} dz=+-{dz} DZ crop at {y0},{x0} -> {a.out}")


if __name__ == "__main__":
    main()
