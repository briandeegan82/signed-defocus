"""Render the 9-rung ladder plus motion-blur and fog confounds for `m5_lab` (0.29 δ lab-matched design),
so M8 (`src/m8_confounds.py`) compares two lenses with known f/2.0 optics, 5.5 µm pitch and LCA/δ:
`synth_lcaP` (1.82 δ) and `m5_lab` (0.29 δ), replacing `laikin` whose f-number and pitch are unrecorded.

  python src/m8_m5lab_render.py --estimator ~/blur_study \
      --noise-model ~/blur_study/results/robotcar_noise_model.json \
      --out ~/sd_data/m8/m5_lab --workers 12
"""
import argparse
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import m5_lab_lens as M5

RUNGS = (-0.1, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.1)
ANGLE = 20.0

_G = {}


def _init_worker(est_src, psfs, model, length, trans, out_dir):
    sys.path.insert(0, str(est_src))
    import confound_robotcar as CR
    import render_arms as RA
    import robotcar as RC
    _G.update(CR=CR, RA=RA, RC=RC, psfs=psfs, model=model, length=length, trans=trans, out=Path(out_dir))


def _render_one(item):
    trav, p_str = item
    p = Path(p_str)
    CR, RA, RC = _G["CR"], _G["RA"], _G["RC"]
    psfs, model, out = _G["psfs"], _G["model"], _G["out"]
    plate = RC.load_plate(p)
    wb = RA.plate_grey_world(plate)
    stem = p.stem
    for dz in RUNGS:
        d = out / "ladder" / "pre" / f"DZ={dz:g}"
        np.save(d / f"{trav}__{stem}.npy",
                RA.render(plate, psfs[dz], wb, model, "pre", RA.stable_seed(trav, stem, dz, 0)))
    mp = CR.motion_psfs(_G["length"], ANGLE, psfs[0.0])
    np.save(out / "tree_motion" / "pre" / "DZ=0" / f"{trav}__{stem}.npy",
            RA.render(plate, mp, wb, model, "pre", RA.stable_seed(trav, stem, "motion")))
    foggy = CR.fog_bayer(plate.astype(np.float64), _G["trans"])
    np.save(out / "tree_fog" / "pre" / "DZ=0" / f"{trav}__{stem}.npy",
            RA.render(foggy, psfs[0.0], RA.plate_grey_world(foggy), model, "pre",
                      RA.stable_seed(trav, stem, "fog")))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimator", type=Path, required=True)
    ap.add_argument("--noise-model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    est_src = a.estimator / "src"
    sys.path.insert(0, str(est_src))
    import torch
    import confound_robotcar as CR
    import extract_parallel as EP
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(a.noise_model.read_text())["model"]
    row = pd.read_csv(M5.HERE / "data" / "m5_lenses.csv").set_index("lens").loc["m5_lab"]
    row_ns = type("Row", (), dict(row.to_dict(), lens="m5_lab"))()
    psfs = M5.channel_psfs(LS, row_ns, RUNGS, device)

    groups = RC.plate_paths()
    items = [(t, str(p)) for t, ps in sorted(groups.items()) for p in ps]
    print(f"m5_lab: {len(items)} plates, {len(RUNGS)} ladder rungs + motion + fog, device={device}", flush=True)

    probe = [RC.load_plate(Path(p)) for _, p in items[:6]]
    length, ref = CR.calibrate(probe, psfs, RA.plate_grey_world, model, angle=ANGLE)
    trans = CR.calibrate_fog(probe, psfs, RA.plate_grey_world, model, ref)

    a.out.mkdir(parents=True, exist_ok=True)
    for dz in RUNGS:
        (a.out / "ladder" / "pre" / f"DZ={dz:g}").mkdir(parents=True, exist_ok=True)
    (a.out / "tree_motion" / "pre" / "DZ=0").mkdir(parents=True, exist_ok=True)
    (a.out / "tree_fog" / "pre" / "DZ=0").mkdir(parents=True, exist_ok=True)

    (a.out / "manifest.json").write_text(json.dumps(
        dict(lens="m5_lab", motion_length_px=length, motion_angle_deg=ANGLE,
             fog_transmission=trans, matched_to_dz=CR.MATCH_DZ,
             reference_sharpness=ref), indent=1))

    done = 0
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init_worker,
                             initargs=(est_src, psfs, model, length, trans, a.out)) as ex:
        for _ in ex.map(_render_one, items):
            done += 1
            if done % 50 == 0 or done == len(items):
                print(f"  rendered {done}/{len(items)} plates", flush=True)

    lab = RA.labels(psfs)
    labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
    zlab = {0.0: labels[0.0]}

    EP.extract(str(a.out / "ladder"), "pre", labels, a.workers).to_parquet(
        a.out / "rc_feat_robotcar_render_m5_lab_pre_all.parquet", index=False)
    EP.extract(str(a.out / "tree_motion"), "pre", zlab, a.workers).to_parquet(
        a.out / "rc_feat_confound_motion.parquet", index=False)
    EP.extract(str(a.out / "tree_fog"), "pre", zlab, a.workers).to_parquet(
        a.out / "rc_feat_confound_fog.parquet", index=False)

    for sub in ("ladder", "tree_motion", "tree_fog"):
        shutil.rmtree(a.out / sub)
    print("done", flush=True)


if __name__ == "__main__":
    main()
