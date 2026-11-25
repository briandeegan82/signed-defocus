"""Re-render M8 motion-blur and fog confounds for `synth_lcaP` (1.82 δ) and `m5_lab` (0.29 δ)
with physically consistent optical composition:

1. Motion blur: each channel's in-focus optical PSF is convolved with the achromatic linear
   motion kernel (`PSF_k(Δz=0) * k_motion`), preserving the lens's in-focus chromatic signature
   rather than replacing the optical PSF.
2. Fog: spatially uniform veiling-airlight layer applied to the raw Bayer image ahead of the
   in-focus PSF (black level = 0 DN), with per-plane airlight scaled by inverse white-balance
   gain (`A_r = A/g_r`, `A_g = A`, `A_b = A/g_b`, `A = 220` DN) so the veil is neutral after
   white balance.

Both confounds are matched in 90th-percentile gradient sharpness to a +0.02 DZ (+0.91 δ) defocus
render on the same six probe images. Uses existing 9-rung ladder caches.

  python src/m8_confound_render.py --estimator ~/blur_study \
      --noise-model ~/blur_study/results/robotcar_noise_model.json \
      --out-root ~/sd_data/m8 --workers 12
"""
import argparse
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import convolve2d

import m5_lab_lens as M5

RUNGS = (-0.1, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.1)
ANGLE = 20.0
AIRLIGHT = 220.0
MATCH_DZ = 0.02

_G = {}


def motion_psfs_convolved(CF, length_px, angle_deg, psf_in_focus):
    """Convolve each channel's in-focus optical PSF with the achromatic linear motion kernel."""
    k_mot = CF.motion_kernel(length_px, angle_deg).astype(np.float64)
    out = {}
    for c, k_opt in psf_in_focus.items():
        k_eff = convolve2d(np.asarray(k_opt, dtype=np.float64), k_mot, mode="full")
        k_eff /= k_eff.sum()
        out[c] = k_eff
    return out


def fog_bayer_neutral(WR, plate, transmission, wb, airlight=AIRLIGHT):
    """Neutral veiling-airlight model on a 2-D RGGB Bayer image (black level 0 DN).

    Scales airlight per plane by inverse white-balance gain so the veil is achromatic
    (R = G = B = airlight) after white balance.
    """
    r_gain, b_gain = wb
    pl = WR.split_planes(plate.astype(np.float64))
    air = {"r": airlight / r_gain, "gr": airlight, "gb": airlight, "b": airlight / b_gain}
    out = {k: np.clip(v * transmission + air[k] * (1.0 - transmission), 0.0, 255.0)
           for k, v in pl.items()}
    return WR.join_planes(out).astype(np.float64)


def calibrate_motion(CF, RA, probe, psfs, model, angle=ANGLE,
                     target_len_range=(0.5, 25.0), tol=0.02):
    ref = float(np.mean([
        CF.sharpness(RA.render(p, psfs[MATCH_DZ], RA.plate_grey_world(p), model, "pre", 0))
        for p in probe
    ]))
    lo, hi = target_len_range
    mid, got = lo, ref
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        mp = motion_psfs_convolved(CF, mid, angle, psfs[0.0])
        got = float(np.mean([
            CF.sharpness(RA.render(p, mp, RA.plate_grey_world(p), model, "pre", 0))
            for p in probe
        ]))
        if abs(got - ref) / ref < tol:
            break
        if got > ref:
            lo = mid
        else:
            hi = mid
    print(f"  motion (PSF*kernel) length {mid:.3f} px -> sharpness {got:.2f} vs DZ=+0.02 ref {ref:.2f}",
          flush=True)
    return mid, ref


def calibrate_fog(CF, RA, WR, probe, psfs, model, ref, tol=0.02):
    lo, hi = 0.30, 1.0
    mid, got = hi, ref
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        vals = []
        for p in probe:
            wb = RA.plate_grey_world(p)
            foggy = fog_bayer_neutral(WR, p, mid, wb)
            rgb = RA.render(foggy, psfs[0.0], RA.plate_grey_world(foggy), model, "pre", 0)
            vals.append(CF.sharpness(rgb))
        got = float(np.mean(vals))
        if abs(got - ref) / ref < tol:
            break
        if got > ref:
            hi = mid
        else:
            lo = mid
    print(f"  fog (neutral) transmission {mid:.4f} -> sharpness {got:.2f} vs DZ=+0.02 ref {ref:.2f}",
          flush=True)
    return mid


def _init_worker(est_src, psfs, mp, model, trans, out_dir):
    sys.path.insert(0, str(est_src))
    import render_arms as RA
    import robotcar as RC
    import weather_raw as WR
    _G.update(RA=RA, RC=RC, WR=WR, psfs=psfs, mp=mp, model=model, trans=trans, out=Path(out_dir))


def _render_one(item):
    trav, p_str = item
    p = Path(p_str)
    RA, RC, WR = _G["RA"], _G["RC"], _G["WR"]
    psfs, mp, model, out = _G["psfs"], _G["mp"], _G["model"], _G["out"]
    plate = RC.load_plate(p)
    wb = RA.plate_grey_world(plate)
    stem = p.stem
    np.save(out / "tree_motion" / "pre" / "DZ=0" / f"{trav}__{stem}.npy",
            RA.render(plate, mp, wb, model, "pre", RA.stable_seed(trav, stem, "motion")))
    foggy = fog_bayer_neutral(WR, plate, _G["trans"], wb)
    np.save(out / "tree_fog" / "pre" / "DZ=0" / f"{trav}__{stem}.npy",
            RA.render(foggy, psfs[0.0], RA.plate_grey_world(foggy), model, "pre",
                      RA.stable_seed(trav, stem, "fog")))
    return 1


def load_psfs(lens, RA, LS, device):
    if lens == "synth_lcaP":
        return RA.centre_psfs("synth_lcaP")
    if lens == "m5_lab":
        row = pd.read_csv(M5.HERE / "data" / "m5_lenses.csv").set_index("lens").loc["m5_lab"]
        row_ns = type("Row", (), dict(row.to_dict(), lens="m5_lab"))()
        return M5.channel_psfs(LS, row_ns, RUNGS, device)
    raise ValueError(f"Unknown lens: {lens}")


def run_lens(lens, a, est_src, CF, EP, LS, RA, RC, WR, model, items, probe, device):
    out = a.out_root / lens
    out.mkdir(parents=True, exist_ok=True)
    psfs = load_psfs(lens, RA, LS, device)
    print(f"\n=== {lens}: {len(items)} images, device={device} ===", flush=True)
    length, ref = calibrate_motion(CF, RA, probe, psfs, model, angle=ANGLE)
    trans = calibrate_fog(CF, RA, WR, probe, psfs, model, ref)
    mp = motion_psfs_convolved(CF, length, ANGLE, psfs[0.0])

    for sub in ("tree_motion", "tree_fog"):
        d = out / sub / "pre" / "DZ=0"
        if (out / sub).exists():
            shutil.rmtree(out / sub)
        d.mkdir(parents=True, exist_ok=True)

    (out / "manifest.json").write_text(json.dumps(
        dict(lens=lens, motion_model="psf_convolved", fog_model="neutral_inv_wb",
             motion_length_px=length, motion_angle_deg=ANGLE,
             fog_transmission=trans, fog_airlight_dn=AIRLIGHT,
             matched_to_dz=MATCH_DZ, reference_sharpness=ref), indent=1))

    done = 0
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init_worker,
                             initargs=(est_src, psfs, mp, model, trans, out)) as ex:
        for _ in ex.map(_render_one, items):
            done += 1
            if done % 50 == 0 or done == len(items):
                print(f"  {lens}: rendered {done}/{len(items)}", flush=True)

    lab = RA.labels(psfs)
    labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
    zlab = {0.0: labels[0.0]}

    EP.extract(str(out / "tree_motion"), "pre", zlab, a.workers).to_parquet(
        out / "rc_feat_confound_motion.parquet", index=False)
    EP.extract(str(out / "tree_fog"), "pre", zlab, a.workers).to_parquet(
        out / "rc_feat_confound_fog.parquet", index=False)

    for sub in ("tree_motion", "tree_fog"):
        shutil.rmtree(out / sub)
    print(f"=== {lens}: done ===", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--noise-model", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--lenses", nargs="+", default=["synth_lcaP", "m5_lab"])
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    est_src = a.estimator / "src"
    sys.path.insert(0, str(est_src))
    import torch
    import confound as CF
    import extract_parallel as EP
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC
    import weather_raw as WR

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(a.noise_model.read_text())["model"]
    groups = RC.plate_paths()
    items = [(t, str(p)) for t, ps in sorted(groups.items()) for p in ps]
    probe = [RC.load_plate(Path(p)) for _, p in items[:6]]

    for lens in a.lenses:
        run_lens(lens, a, est_src, CF, EP, LS, RA, RC, WR, model, items, probe, device)


if __name__ == "__main__":
    main()
