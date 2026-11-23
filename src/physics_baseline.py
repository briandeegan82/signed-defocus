"""Physics baseline v0: focus direction and signed displacement from the red/blue sharpness ratio.

Model. With longitudinal chromatic aberration the red and blue channels focus at
different image-plane positions z_r and z_b. At sensor displacement dz the channel
whose focus is nearer dz is sharper, so the log ratio of red to blue gradient energy,
c = log(T_r / T_b) (cached as `ch_ten_rb`), changes sign at the midpoint
(z_r + z_b) / 2 and has the sign of (z_r - z_b) * (dz - midpoint) nearby.

Direction estimate per frame: s * sign(median_patches(c) - c0), with s the channel
order and c0 the in-focus offset. Three calibration levels (protocol RQ3):
  none   s from the lens prescription, c0 = 0
  order  s from the lens prescription, c0 fitted on training traversals
  fitted s and c0 both fitted on training traversals
Signed displacement (protocol RQ2): the training through-focus curve of the frame
medians of (c, log luminance gradient energy) is interpolated in dz, and each test
frame is assigned the dz of the nearest curve point. Evaluated leave-one-rung-out,
so the test displacement is never in training.

Reads the cached patch features of `defocus-estimator` read-only. Writes CSVs.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

LENSES = ["laikin", "sony", "sunex", "horimoto", "synth_lcaP", "synth_lcaN"] + [f"synth{i:02d}" for i in range(12)]
N_FOLDS = 5
DZ_GRID = np.linspace(-0.1, 0.1, 401)


def frame_table(path):
    d = pd.read_parquet(path, columns=["ch_ten_rb", "cx_grad_mean", "dz", "traversal", "stem"])
    d["lum"] = np.log(d["cx_grad_mean"] + 1e-9)
    f = d.groupby(["traversal", "stem", "dz"], as_index=False)[["ch_ten_rb", "lum"]].median()
    return f.rename(columns={"ch_ten_rb": "c"})


def folds(traversals):
    t = np.array(sorted(traversals))
    return {tr: i % N_FOLDS for i, tr in enumerate(t)}


def fit_direction(train):
    """c0 and s that maximise training direction accuracy (dz != 0 only)."""
    tr = train[train.dz != 0]
    best = (0.0, 1, -1.0)
    for c0 in np.quantile(tr.c, np.linspace(0.02, 0.98, 97)):
        for s in (1, -1):
            acc = np.mean(s * np.sign(tr.c - c0) == np.sign(tr.dz))
            if acc > best[2]:
                best = (float(c0), s, acc)
    return best[:2]


def fit_offset(train, s):
    tr = train[train.dz != 0]
    cands = np.quantile(tr.c, np.linspace(0.02, 0.98, 97))
    accs = [np.mean(s * np.sign(tr.c - c0) == np.sign(tr.dz)) for c0 in cands]
    return float(cands[int(np.argmax(accs))])


def through_focus_curve(train):
    m = train.groupby("dz")[["c", "lum"]].median().sort_index()
    sd = train[["c", "lum"]].std().values + 1e-9
    curve = np.column_stack([np.interp(DZ_GRID, m.index, m[k]) for k in ("c", "lum")])
    lo, hi = m.index.min(), m.index.max()
    keep = (DZ_GRID >= lo) & (DZ_GRID <= hi)
    return DZ_GRID[keep], curve[keep] / sd, sd


def invert(curve, x):
    grid, pts, sd = curve
    dist = (((x / sd)[:, None, :] - pts[None]) ** 2).sum(-1)
    return grid[np.argmin(dist, axis=1)]


def run(cache, lca):
    dir_rows, dz_rows = [], []
    for lens in LENSES:
        p = cache / f"rc_feat_robotcar_render_{lens}_pre_all.parquet"
        if not p.exists():
            continue
        f = frame_table(p)
        fmap = folds(f.traversal.unique())
        f["fold"] = f.traversal.map(fmap)
        s_rx = int(np.sign(lca.loc[lens, "r_um"] - lca.loc[lens, "b_um"])) if lens in lca.index else 0
        for k in range(N_FOLDS):
            tr, te = f[f.fold != k], f[f.fold == k].copy()
            c0_f, s_f = fit_direction(tr)
            levels = {"fitted": (c0_f, s_f)}
            if s_rx != 0:
                levels["none"] = (0.0, s_rx)
                levels["order"] = (fit_offset(tr, s_rx), s_rx)
            for lvl, (c0, s) in levels.items():
                pred = s * np.sign(te.c - c0)
                for dz, g in te.assign(ok=pred == np.sign(te.dz)).groupby("dz"):
                    if dz != 0:
                        dir_rows.append(dict(lens=lens, level=lvl, fold=k, dz=dz, n=len(g), acc=g.ok.mean()))
        for dz_out in sorted(f.dz.unique()):
            if dz_out in (f.dz.min(), f.dz.max()):
                continue
            for k in range(N_FOLDS):
                tr = f[(f.fold != k) & (f.dz != dz_out)]
                te = f[(f.fold == k) & (f.dz == dz_out)]
                pred = invert(through_focus_curve(tr), te[["c", "lum"]].values)
                err = (pred - dz_out) * 1000.0
                dz_rows += [dict(lens=lens, fold=k, dz_withheld=dz_out, err_um=e) for e in err]
    return pd.DataFrame(dir_rows), pd.DataFrame(dz_rows)


def summarise(dirs, dzs, lca):
    w = dirs.assign(nacc=dirs.n * dirs.acc).groupby(["lens", "level"])[["nacc", "n"]].sum()
    s1 = (w.nacc / w.n).unstack("level").round(3)
    near = dirs[dirs.dz.abs() <= 0.02]
    w2 = near.assign(nacc=near.n * near.acc).groupby(["lens", "level"])[["nacc", "n"]].sum()
    s1 = s1.join((w2.nacc / w2.n).unstack("level").round(3), rsuffix="_near")
    s2 = dzs.groupby("lens").err_um.agg(bias="mean", mae=lambda e: e.abs().mean(),
                                         p90=lambda e: e.abs().quantile(0.9)).round(1)
    out = s1.join(s2).join(lca[["lca_spread_um", "r_um", "b_um"]], how="left")
    return out.sort_values("lca_spread_um", ascending=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, required=True, help="defocus-estimator results/ directory")
    ap.add_argument("--lca", type=Path, required=True, help="per-lens LCA table (lens,r_um,g_um,b_um,lca_spread_um)")
    ap.add_argument("--out", type=Path, default=Path("results"))
    a = ap.parse_args()
    lca = pd.read_csv(a.lca).set_index("lens")
    dirs, dzs = run(a.cache, lca)
    a.out.mkdir(parents=True, exist_ok=True)
    dirs.to_csv(a.out / "physics_baseline_direction.csv", index=False)
    dzs.to_csv(a.out / "physics_baseline_displacement.csv", index=False)
    s = summarise(dirs, dzs, lca)
    s.to_csv(a.out / "physics_baseline_summary.csv")
    print(s.to_string())


if __name__ == "__main__":
    main()
