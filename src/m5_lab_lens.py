"""M5a: a rendered lens matched to the lab lens's chromatic focus, on the Phase 2 RobotCar design.

The lab sweep (`results/lab_sweep/LAB_SWEEP.md`, primary fit) puts best focus at steps 42.7 (blue),
44.7 (red), 46.2 (green): red - blue 1.90 steps = 0.29 δ, and green 1.55 steps beyond red, outside
the red-blue interval (secondary spectrum). The frozen `lens_synth` model is linear in wavelength,
focus_mm = dz * defocus_scale + long_ca * (lambda - 0.588), so green always sits between red and
blue. To place each channel's focus independently, each channel's PSF is taken from a
`lens_synth.render_psfs` call with its own long_ca (green has lambda = 0.588, so it stays at 0):
    z_c = -long_ca_c * (lambda_c - 0.588) / defocus_scale   (sensor plane of channel c, mm)
Optics are the M3 base (f/2.0, 5.5 µm, δ = 22 µm), so the match is in δ, the unit that transfers
from the lab whatever its f-number. The lab's step direction relative to the sensor is not known,
so the design is the mirror image along z (green, red, blue in increasing z; red-blue sign as the
M3 "p" lenses); M3 shows mirror pairs score alike without spherical aberration.

Designs (data/m5_lenses.csv):
  m5_lab      red +0.238 δ, blue +0.531 δ from green (lab order and spacing), no SA
  m5_lab_sa   the same with the M3 spherical aberration (1.0 x 0.3 waves); the lab cue's
              flat-near-focus shape resembles the M3 SA designs
  m5_lin029   linear LCA with the same red-blue 0.29 δ, green between (control)

Render: every RobotCar plate at 8 distinct displacements in +-0.1 DZ, seeded and drawn exactly as
the Phase 2 render (`draw_dz`, seed `stable_seed(traversal, stem, "m2")`), so frames pair with the
M3 Phase 2 lenses. Truth Δz is the nominal sensor displacement from the green plane.

  python src/m5_lab_lens.py designs
  python src/m5_lab_lens.py check  --estimator ~/blur_study            # per-channel focus of the PSFs
  python src/m5_lab_lens.py render --estimator ~/blur_study --noise-model <json> --out ~/sd_data/m5
  python src/m5_lab_lens.py score  --cache ~/sd_data/m5 --out results/m5_lab
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import m2_continuous as M2

LAMBDA = {"r": 0.656, "g": 0.588, "b": 0.486}
REF = 0.588
DELTA_UM = 2.0 * M2.BASE["f_number"] * M2.BASE["pixel_pitch"]
DELTA_PER_STEP = 0.154
LAB_STEPS = {"b": 42.7481, "r": 44.6532, "g": 46.1995}  # results/lab_sweep/step_size_fits.csv, primary
SA = 1.0
HERE = Path(__file__).resolve().parent.parent


def designs():
    lab = {c: -(LAB_STEPS[c] - LAB_STEPS["g"]) * DELTA_PER_STEP * DELTA_UM for c in "rgb"}  # mirrored, µm
    rb = lab["b"] - lab["r"]
    lin = {c: -(rb / 1000.0 / (LAMBDA["r"] - LAMBDA["b"])) * (LAMBDA[c] - REF) * 1000.0 for c in "rgb"}
    rows = []
    for lens, z, sa in (("m5_lab", lab, 0.0), ("m5_lab_sa", lab, SA), ("m5_lin029", lin, 0.0)):
        r = dict(lens=lens, spherical=sa)
        for c in "rgb":
            r[f"z_{c}_um"] = round(z[c], 3)
            r[f"long_ca_{c}"] = 0.0 if c == "g" else round(-z[c] / 1000.0 * M2.BASE["defocus_scale"] / (LAMBDA[c] - REF), 6)
        r["lca_rb_over_delta"] = round((z["b"] - z["r"]) / DELTA_UM, 4)
        r["long_ca_equiv"] = round((z["b"] - z["r"]) / 1000.0 / (LAMBDA["r"] - LAMBDA["b"]), 6)
        rows.append(r)
    return pd.DataFrame(rows)


def channel_psfs(LS, row, levels, device):
    """{dz: {ch: kernel}}, channel c from a render with long_ca_c."""
    out = {round(float(z), 4): {} for z in levels}
    for c in "rgb":
        design = dict(M2.BASE, long_ca=float(getattr(row, f"long_ca_{c}")), spherical=float(row.spherical))
        for i in range(0, len(levels), 32):
            LS.DZ_LEVELS = levels[i:i + 32]
            for dz, k in M2.centre_kernels(LS.render_psfs(design, device), LS.DZ_LEVELS).items():
                out[dz][c] = k[c]
    return out


def table():
    return pd.read_csv(HERE / "data" / "m5_lenses.csv")


def check(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    levels = [round(float(z), 4) for z in np.arange(-0.03, 0.0301, 0.001)]
    for row in table().itertuples():
        psfs = channel_psfs(LS, row, levels, device)
        peak = {}
        for c in "rgb":
            m = np.array([mtf(psfs[z][c]) for z in levels])
            i = int(np.clip(np.argmax(m), 2, len(m) - 3))
            x = np.array(levels[i - 2:i + 3]) * 1000.0
            a2, a1, _ = np.polyfit(x, m[i - 2:i + 3], 2)
            peak[c] = -a1 / (2 * a2)
        print(row.lens, {c: f"{peak[c] - peak['g']:+.1f} µm from green (design "
                         f"{getattr(row, f'z_{c}_um') - row.z_g_um:+.1f})" for c in "rgb"})


def mtf(k, f=0.25):
    """Radially averaged MTF of a centred kernel at f cycles/pixel."""
    n = k.shape[0]
    F = np.abs(np.fft.fftshift(np.fft.fft2(k, (4 * n, 4 * n))))
    y, x = np.indices(F.shape) - 2 * n
    r = np.hypot(y, x) / (4 * n)
    return float(F[np.abs(r - f) < 0.5 / (4 * n)].mean())


def render(a):
    sys.path.insert(0, str(a.estimator / "src"))
    import torch
    import lens_synth as LS
    import render_arms as RA
    import robotcar as RC
    import extract_parallel as EP
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = json.loads(Path(a.noise_model).read_text())["model"]
    groups = RC.plate_paths()
    plates = M2.pick_plates(groups, a.n_plates or sum(len(v) for v in groups.values()))
    draws = [(t, p, draw_dz(RA.stable_seed(t, p.stem, "m2"), a.k, a.dz_max)) for t, p in plates]
    levels = sorted({float(z) for _, _, zs in draws for z in zs})
    a.out.mkdir(parents=True, exist_ok=True)
    for row in table().itertuples():
        if a.lenses and row.lens not in a.lenses.split(","):
            continue
        feat = a.out / f"rc_feat_{row.lens}_pre_all.parquet"
        if feat.exists():
            print(f"{row.lens}: cached")
            continue
        print(f"{row.lens}: {len(plates)} plates, {a.k} displacements each, on {device}", flush=True)
        psfs = channel_psfs(LS, row, levels, device)
        root = a.out / row.lens
        root.mkdir(parents=True, exist_ok=True)
        lab = RA.labels(psfs)
        (root / "labels.json").write_text(json.dumps(lab, indent=1))
        (root / "design.json").write_text(json.dumps(dict(row._asdict(), n_plates=len(plates), k=a.k), indent=1, default=str))
        for j, (t, p, zs) in enumerate(draws):
            plate = RC.load_plate(p)
            wb = RA.plate_grey_world(plate)
            for z in zs:
                dz = round(float(z), 4)
                d = root / "pre" / f"DZ={dz:g}"
                d.mkdir(parents=True, exist_ok=True)
                np.save(d / f"{t}__{p.stem}.npy", RA.render(plate, psfs[dz], wb, model, "pre", RA.stable_seed(t, p.stem, dz, 0)))
            if (j + 1) % 25 == 0:
                print(f"  {j + 1}/{len(draws)} plates", flush=True)
        labels = {round(x["dz"], 4): {"mtf025_mean": x["mtf025_mean"], "mtf025_g": x["mtf025_g"]} for x in lab}
        EP.extract(str(root), "pre", labels, a.workers).to_parquet(feat, index=False)
        if not a.keep:
            import shutil
            shutil.rmtree(root / "pre")
        print(f"{row.lens}: -> {feat}", flush=True)


def draw_dz(seed, k, dz_max):
    """k distinct displacements rounded to 1e-4 DZ; as the Phase 2 render (`m2_continuous.draw_dz`)."""
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < k:
        for z in np.round(rng.uniform(-dz_max, dz_max, k), 4):
            if z not in out and len(out) < k:
                out.append(z)
    return np.array(out)


def score(a):
    for row in table().itertuples():
        feat = a.cache / f"rc_feat_{row.lens}_pre_all.parquet"
        if not feat.exists():
            print(f"{row.lens}: no cache, skipped")
            continue
        M2.score(SimpleNamespace(cache=feat, ladder=None, out=a.out / row.lens, bin=0.01, lens=row.lens,
                                 long_ca=float(row.long_ca_equiv), **{k: M2.BASE[k] for k in ("f_number", "pixel_pitch", "defocus_scale")}))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("designs")
    c = sub.add_parser("check")
    c.add_argument("--estimator", type=Path, required=True)
    r = sub.add_parser("render")
    r.add_argument("--estimator", type=Path, required=True)
    r.add_argument("--noise-model", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--lenses", default=None)
    r.add_argument("--n-plates", type=int, default=0, help="0 = every plate (Phase 2 design)")
    r.add_argument("--k", type=int, default=8)
    r.add_argument("--dz-max", type=float, default=0.1)
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--keep", action="store_true", help="keep rendered frames")
    s = sub.add_parser("score")
    s.add_argument("--cache", type=Path, required=True)
    s.add_argument("--out", type=Path, default=Path("results/m5_lab"))
    a = ap.parse_args()
    if a.cmd == "designs":
        d = designs()
        d.to_csv(HERE / "data" / "m5_lenses.csv", index=False)
        print(d.to_string(index=False))
    else:
        {"check": check, "render": render, "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
