"""M3 gate: a controlled synthetic lens set spanning LCA/delta 0-2, both signs, rendered on RobotCar.

Every lens shares the optics of the matched LCA probe `synth_lcaP`/`synth_lcaN`
(`defocus-estimator/src/lens_lca_probe.py` BASE: f/2.0, 5.5 um pitch, defocus_scale
1.0 mm, so delta = 2 N c = 22 um and one ladder rung DZ=0.01 is 10 um). Only the
red-minus-blue focus separation and, in the `_sa` half, spherical aberration vary:

  LCA/delta in {0, 0.25, 0.5, 0.75, 1, 1.5, 2}, both signs, spherical 0 or 1.0
  (x aberration_scale 0.3 = W040 0.3 waves at 0.588 um), plus `m3_ref`, an exact
  copy of `synth_lcaP` that checks this pipeline against the cached v0 render.

Sign: `p` is long_ca > 0 (red focuses nearer the lens, z_r < z_b, as synth_lcaP).

Rendering reuses the frozen defocus-estimator code unchanged: PSFs from
`lens_synth.render_psfs`, quantised to 8 bit as `lens_synth.write_maps` does and
centre tile taken as `render_arms.centre_psfs` does, then
`render_arms.render_robotcar` (pre-ISP arm, measured RobotCar noise, per-plate
white balance, same seeds) and `extract_parallel.extract`. Nothing is written
into the defocus-estimator tree; the PSFs are held in memory.

  python src/m3_lenses.py designs                 # writes data/m3_lenses.csv, data/m3_lca.csv
  python src/m3_lenses.py render --estimator ~/blur_study --out ~/sd_data/m3 --plates 8
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

BASE = dict(f_number=2.0, pixel_pitch=5.5, aberration_scale=0.30, spherical=0.0,
            coma=0.30, astigmatism=0.30, field_curv=0.0, lat_ca=0.0, defocus_scale=1.0)
LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
SPHERICAL = {"": 0.0, "_sa": 1.0}
SYNTH_LCAP_LONG_CA = 0.235294
LAMBDA = {"r": 0.656, "g": 0.588, "b": 0.486}
REF = 0.588
CENTRE_GY, CENTRE_GX = 3, 4
HERE = Path(__file__).resolve().parent.parent


def designs():
    delta_um = 2.0 * BASE["f_number"] * BASE["pixel_pitch"]
    rows = []
    for suffix, sa in SPHERICAL.items():
        for lv in LEVELS:
            for sign in ((1,) if lv == 0 else (1, -1)):
                tag = "z" if lv == 0 else ("p" if sign > 0 else "n")
                long_ca = sign * lv * delta_um / 1000.0 / (LAMBDA["r"] - LAMBDA["b"])
                rows.append(dict(lens=f"m3_{tag}{int(round(lv * 100)):03d}{suffix}", lca_over_delta_design=lv,
                                 long_ca=long_ca, spherical=sa))
    rows.append(dict(lens="m3_ref", lca_over_delta_design=np.nan, long_ca=SYNTH_LCAP_LONG_CA, spherical=0.0))
    return pd.DataFrame(rows)


def write_tables(d):
    src = "src/m3_lenses.py (lens_lca_probe.py BASE)"
    optics = pd.DataFrame(dict(lens=d.lens, f_number=BASE["f_number"], pixel_pitch_um=BASE["pixel_pitch"],
                               defocus_scale_mm=BASE["defocus_scale"], long_ca_mm_per_um=d.long_ca.round(6),
                               spherical=d.spherical, aberration_scale=BASE["aberration_scale"], source=src))
    optics.to_csv(HERE / "data" / "m3_lenses.csv", index=False)
    # Channel focus planes in um of sensor displacement: dz * ds + long_ca * (lambda - REF) = 0.
    z = {c: (-d.long_ca * (lam - REF) / BASE["defocus_scale"] * 1000.0).round(3) + 0.0 for c, lam in LAMBDA.items()}
    lca = pd.DataFrame(dict(lens=d.lens, r_um=z["r"], g_um=z["g"], b_um=z["b"],
                            lca_spread_um=(z["b"] - z["r"]).abs().round(3), source=src))
    lca.to_csv(HERE / "data" / "m3_lca.csv", index=False)
    print(optics.to_string(index=False))


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


def render(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    import render_arms as RA
    import extract_parallel as EP

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(Path(a.noise_model).read_text())["model"]
    table = pd.read_csv(HERE / "data" / "m3_lenses.csv")
    if a.lenses:
        table = table[table.lens.isin(a.lenses.split(","))]
    a.out.mkdir(parents=True, exist_ok=True)
    for r in table.itertuples():
        feat = a.out / f"rc_feat_{r.lens}_pre_all.parquet"
        if feat.exists():
            print(f"{r.lens}: cached")
            continue
        design = dict(BASE, long_ca=r.long_ca_mm_per_um, spherical=r.spherical)
        psfs = centre_kernels(LS.render_psfs(design, device), LS.DZ_LEVELS)
        root = a.out / r.lens
        root.mkdir(parents=True, exist_ok=True)
        lab = RA.labels(psfs)
        (root / "labels.json").write_text(json.dumps(lab, indent=1))
        (root / "design.json").write_text(json.dumps(design, indent=1))
        ns = SimpleNamespace(out=str(root), arms="pre", traversals=a.traversals, plates=a.plates, frames=1,
                             denoise=0.0, isp_denoise=0.0, isp_denoise_kind="bilateral", isp_sharpen=0.0,
                             jpeg_quality=0)
        print(f"{r.lens}: rendering on {device}", flush=True)
        RA.render_robotcar(ns, psfs, model)
        labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
        EP.extract(str(root), "pre", labels, a.workers).to_parquet(feat, index=False)
        print(f"{r.lens}: -> {feat}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("designs")
    r = sub.add_parser("render")
    r.add_argument("--estimator", type=Path, required=True, help="defocus-estimator checkout (has data/raw plates)")
    r.add_argument("--noise-model", type=Path, required=True, help="robotcar_noise_model.json")
    r.add_argument("--out", type=Path, required=True, help="render root, outside both repos")
    r.add_argument("--plates", type=int, default=8, help="first N plates per traversal (gate default 8)")
    r.add_argument("--traversals", default=None)
    r.add_argument("--lenses", default=None, help="comma-separated subset of data/m3_lenses.csv")
    r.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "designs":
        write_tables(designs())
    else:
        render(a)


if __name__ == "__main__":
    main()
