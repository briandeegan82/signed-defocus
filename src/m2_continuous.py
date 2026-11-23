"""M2 gate: continuous sensor displacement on a 40-plate RobotCar subset, and its baseline score.

The v0 renders use 9 fixed rungs, so v0 Gate B is leave-one-rung-out. Here every
frame has its own displacement: each plate is rendered at K displacements drawn
uniformly from [-dz_max, dz_max] (nominal DZ units, x defocus_scale mm), seeded
by plate name so a re-run is identical. Default lens is an exact copy of
`synth_lcaP` (f/2.0, 5.5 um pitch, defocus_scale 1.0 mm, so DZ 0.01 = 10 um,
delta = 2 N c = 22 um, red-blue LCA 40 um = 1.82 delta).

Rendering reuses the frozen defocus-estimator code unchanged: PSFs from
`lens_synth.render_psfs` at the drawn displacements, quantised to 8 bit and centre
tile taken as `write_maps` -> `centre_psfs` do, then `render_arms.render` (pre-ISP
arm, measured RobotCar noise, per-plate white balance) with the
`render_robotcar` seeding and file layout, and `extract_parallel.extract`.

Scoring (traversal-disjoint 5 folds, as `physics_baseline.py`):
  direction     sign/offset fitted on training traversals ("fitted"), or the sign
                from the prescription and offset fitted ("order")
  displacement  through-focus curve of frame medians of (c, log luminance gradient)
                from training frames binned in dz ("continuous"); optionally also
                from the cached 9-rung render of the same lens ("ladder", --ladder)

  python src/m2_continuous.py render --estimator ~/blur_study --noise-model <json> --out ~/sd_data/m2
  python src/m2_continuous.py score --cache ~/sd_data/m2/rc_feat_m2_synth_lcaP_pre_all.parquet \
      [--ladder ~/blur_study/results/rc_feat_robotcar_render_synth_lcaP_pre_all.parquet]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import physics_baseline as PB

BASE = dict(f_number=2.0, pixel_pitch=5.5, aberration_scale=0.30, spherical=0.0,
            coma=0.30, astigmatism=0.30, field_curv=0.0, lat_ca=0.0, defocus_scale=1.0)
SYNTH_LCAP_LONG_CA = 0.235294
CENTRE_GY, CENTRE_GX = 3, 4
LAMBDA_R, LAMBDA_B = 0.656, 0.486


def centre_kernels(tiles, dz_levels):
    """{dz: {ch: kernel}} matching write_maps -> PNG -> centre_psfs, without the files."""
    out = {}
    for zi, dz in enumerate(dz_levels):
        ch = {}
        for ci, c in enumerate(("r", "g", "b")):
            t = tiles[CENTRE_GY, CENTRE_GX, zi, ci].astype(np.float64)
            q = np.round(255.0 * t / max(t.max(), 1e-30)).astype(np.uint8).astype(np.float64)
            ch[c] = (q / max(q.sum(), 1e-12)).astype(np.float32)
        out[round(float(dz), 4)] = ch
    return out


def pick_plates(groups, n):
    """n plates, round-robin over sorted traversals, each traversal's plates in sorted order."""
    trav = sorted(groups)
    out, i = [], 0
    while len(out) < n and any(i < len(groups[t]) for t in trav):
        out += [(t, groups[t][i]) for t in trav if i < len(groups[t])]
        i += 1
    return out[:n]


def render(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC
    import extract_parallel as EP

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(Path(a.noise_model).read_text())["model"]
    design = dict(BASE, long_ca=a.long_ca)
    root = a.out / a.lens
    plates = pick_plates(RC.plate_paths(), a.n_plates)
    print(f"{len(plates)} plates from {len({t for t, _ in plates})} traversals, {a.k} displacements each")
    draws = [(t, p, np.round(np.random.default_rng(RA.stable_seed(t, p.stem, "m2")).uniform(
        -a.dz_max, a.dz_max, a.k), 4)) for t, p in plates]
    levels = sorted({float(z) for _, _, zs in draws for z in zs})
    psfs = {}
    for i in range(0, len(levels), 32):
        LS.DZ_LEVELS = levels[i:i + 32]
        psfs.update(centre_kernels(LS.render_psfs(design, device), LS.DZ_LEVELS))
    root.mkdir(parents=True, exist_ok=True)
    lab = RA.labels(psfs)
    (root / "labels.json").write_text(json.dumps(lab, indent=1))
    (root / "design.json").write_text(json.dumps(dict(design, n_plates=a.n_plates, k=a.k, dz_max=a.dz_max), indent=1))
    manifest = []
    for j, (t, p, zs) in enumerate(draws):
        plate = RC.load_plate(p)
        wb = RA.plate_grey_world(plate)
        for z in zs:
            dz = round(float(z), 4)
            d = root / "pre" / f"DZ={dz:g}"
            d.mkdir(parents=True, exist_ok=True)
            img = RA.render(plate, psfs[dz], wb, model, "pre", RA.stable_seed(t, p.stem, dz, 0))
            np.save(d / f"{t}__{p.stem}.npy", img)
        manifest.append(dict(traversal=t, frame=p.stem, dz=[float(z) for z in zs],
                             r_gain=round(wb[0], 5), b_gain=round(wb[1], 5)))
        print(f"  {j + 1}/{len(draws)} plates", flush=True)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1))
    labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
    feat = a.out / f"rc_feat_m2_{a.lens}_pre_all.parquet"
    EP.extract(str(root), "pre", labels, a.workers).to_parquet(feat, index=False)
    print(f"-> {feat}")


def binned(train, width):
    return train.assign(dz=(np.floor(train.dz / width) + 0.5) * width)


def score(a):
    ds, delta = a.defocus_scale, 2.0 * a.f_number * a.pixel_pitch
    s_rx = int(np.sign(-a.long_ca))  # sign of z_r - z_b
    f = PB.frame_table(a.cache)
    fmap = PB.folds(f.traversal.unique())
    f["fold"] = f.traversal.map(fmap)
    lad = PB.frame_table(a.ladder) if a.ladder else None
    dir_rows, dz_rows = [], []
    for k in range(PB.N_FOLDS):
        tr, te = f[f.fold != k], f[f.fold == k]
        if te.empty:
            continue
        c0_f, s_f = PB.fit_direction(tr)
        for lvl, (c0, s) in {"fitted": (c0_f, s_f), "order": (PB.fit_offset(tr, s_rx), s_rx)}.items():
            ok = s * np.sign(te.c - c0) == np.sign(te.dz)
            dir_rows += [dict(level=lvl, fold=k, traversal=t, stem=st, dz=z, ok=o)
                         for t, st, z, o in zip(te.traversal, te.stem, te.dz, ok)]
        curves = {"continuous": PB.through_focus_curve(binned(tr, a.bin))}
        if lad is not None:
            curves["ladder"] = PB.through_focus_curve(lad[lad.traversal.map(fmap).fillna(-1) != k])
        for name, cv in curves.items():
            pred = PB.invert(cv, te[["c", "lum"]].values)
            dz_rows += [dict(train=name, fold=k, traversal=t, stem=st, dz=z, dz_hat=ph)
                        for t, st, z, ph in zip(te.traversal, te.stem, te.dz, pred)]
    d, e = pd.DataFrame(dir_rows), pd.DataFrame(dz_rows)
    for x in (d, e):
        x["dz_um"] = x.dz * ds * 1000.0
        x["dz_over_delta"] = x.dz_um / delta
    e["err_um"] = (e.dz_hat - e.dz) * ds * 1000.0
    e["err_delta"] = e.err_um / delta
    bins = [0, 0.5, 1, 2, np.inf]
    d["band"] = pd.cut(d.dz_over_delta.abs(), bins, right=False).astype(str)
    e["band"] = pd.cut(e.dz_over_delta.abs(), bins, right=False).astype(str)
    da = (d.groupby(["level", "band"]).ok.agg(n="size", acc="mean").reset_index()
          .pipe(lambda x: pd.concat([x, d.groupby("level").ok.agg(n="size", acc="mean").reset_index()
                                     .assign(band="all")])))
    agg = dict(n=("err_um", "size"), bias_um=("err_um", "mean"),
               mae_um=("err_um", lambda v: v.abs().mean()), p90_um=("err_um", lambda v: v.abs().quantile(0.9)),
               mae_delta=("err_delta", lambda v: v.abs().mean()),
               p90_delta=("err_delta", lambda v: v.abs().quantile(0.9)))
    ea = pd.concat([e.groupby(["train", "band"]).agg(**agg).reset_index(),
                    e.groupby("train").agg(**agg).reset_index().assign(band="all")])
    ea["gate_b_pass"] = ea.mae_delta < 1.0
    a.out.mkdir(parents=True, exist_ok=True)
    d.to_csv(a.out / "m2_direction_frames.csv", index=False)
    e.to_csv(a.out / "m2_displacement_frames.csv", index=False)
    da.round(4).to_csv(a.out / "m2_direction.csv", index=False)
    ea.round(4).to_csv(a.out / "m2_displacement.csv", index=False)
    print(f"lens LCA {abs(a.long_ca) * (LAMBDA_R - LAMBDA_B) * 1000:.1f} um = "
          f"{abs(a.long_ca) * (LAMBDA_R - LAMBDA_B) * 1000 / delta:.2f} delta, delta {delta:.1f} um; "
          f"{f.groupby(['traversal', 'stem']).ngroups} plates, {len(f)} frames, {f.traversal.nunique()} traversals")
    print(da.round(3).to_string(index=False))
    print(ea.round(3).to_string(index=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--estimator", type=Path, required=True, help="defocus-estimator checkout (has the plates)")
    r.add_argument("--noise-model", type=Path, required=True, help="robotcar_noise_model.json")
    r.add_argument("--out", type=Path, required=True, help="render root, outside both repos")
    r.add_argument("--workers", type=int, default=8)
    s = sub.add_parser("score")
    s.add_argument("--cache", type=Path, required=True, help="feature parquet written by `render`")
    s.add_argument("--ladder", type=Path, default=None, help="9-rung feature parquet of the same lens")
    s.add_argument("--out", type=Path, default=Path("results/m2_gate"))
    s.add_argument("--bin", type=float, default=0.01, help="training dz bin width, DZ units (default 0.01)")
    s.add_argument("--f-number", type=float, default=BASE["f_number"])
    s.add_argument("--pixel-pitch", type=float, default=BASE["pixel_pitch"])
    s.add_argument("--defocus-scale", type=float, default=BASE["defocus_scale"])
    for p in (r, s):
        p.add_argument("--lens", default="synth_lcaP")
        p.add_argument("--long-ca", type=float, default=SYNTH_LCAP_LONG_CA)
    r.add_argument("--n-plates", type=int, default=40)
    r.add_argument("--k", type=int, default=8, help="displacements per plate (default 8)")
    r.add_argument("--dz-max", type=float, default=0.1, help="nominal DZ half-range (default 0.1, the v0 ladder)")
    a = ap.parse_args()
    render(a) if a.cmd == "render" else score(a)


if __name__ == "__main__":
    main()
