"""Reference rows (protocol section 3): unsigned sharpness floors and a learned multi-feature regressor,
on the Phase 2 render with the same traversal folds as the physics method.

Per lens (data/m3_lenses.csv, caches `rc_feat_m2_<lens>_pre_all.parquet`) and per fold:
  physics      the method under test: frame medians of (c, lum), sign/threshold for direction, binned
               through-focus curve for signed Δz (as `m2_continuous.score`).
  tenengrad    unsigned floor: frame median of `cx_grad_mean` (mean green gradient magnitude), a 1-D
               curve against |Δz| from training frames binned at 0.01 DZ, inverted for |Δz|.
  laplacian    unsigned floor: the same with `lp_e0` (finest Laplacian-pyramid band energy).
  learned      a re-implementation of the earlier study's SDFE regressor settings (histogram gradient
               boosting, 300 trees, learning rate 0.08, depth 6, min leaf 40) on every patch feature,
               trained to regress signed Δz per patch; frame estimate = median over patches.
Unsigned floors have no direction output (direction accuracy is 0.5 by construction and not
reported). All methods report the error of |Δz| so they can be compared; signed methods also report
direction accuracy and signed MAE. The two-output CNN of the earlier study is not rerun: it needs the
rendered frames, which the Phase 2 render deletes after feature extraction.

  python src/reference_rows.py --cache ~/sd_data/phase2 --out results/reference [--lenses a,b]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import physics_baseline as PB

HERE = Path(__file__).resolve().parent.parent
DELTA_UM, UM_PER_DZ, BIN = 22.0, 1000.0, 0.01
META = {"dz", "traversal", "stem", "py", "px", "frame", "fy", "fx", "mtf025_mean", "mtf025_g", "target"}  # labels, not features


def binned_curve(x, y, width=BIN):
    b = (np.floor(x / width) + 0.5) * width
    m = pd.Series(y).groupby(b).median().sort_index()
    return m.index.values, m.values


def invert_1d(curve, v):
    grid = np.linspace(curve[0].min(), curve[0].max(), 401)
    pts = np.interp(grid, *curve)
    return grid[np.argmin(np.abs(v[:, None] - pts[None]), axis=1)]


def lens_rows(path, lens):
    p = pd.read_parquet(path)
    cols = [c for c in p.columns if c not in META and p[c].dtype.kind == "f"]
    p["lum"] = np.log(p.cx_grad_mean + 1e-9)
    p["fold"] = p.traversal.map(PB.folds(p.traversal.unique()))
    f = p.groupby(["traversal", "stem", "dz", "fold"], as_index=False).agg(
        c=("ch_ten_rb", "median"), lum=("lum", "median"), ten=("cx_grad_mean", "median"), lap=("lp_e0", "median"))
    out = []
    for k in range(PB.N_FOLDS):
        tr, te = f[f.fold != k], f[f.fold == k]
        c0, s = PB.fit_direction(tr)
        trb = tr.assign(dz=(np.floor(tr.dz / BIN) + 0.5) * BIN)
        phys = PB.invert(PB.through_focus_curve(trb), te[["c", "lum"]].values)
        r = te[["traversal", "stem", "dz"]].copy()
        r["physics_dir"], r["physics_dz"] = s * np.sign(te.c - c0), phys
        for name, col in (("tenengrad", "ten"), ("laplacian", "lap")):
            r[f"{name}_absdz"] = invert_1d(binned_curve(tr.dz.abs().values, np.log(tr[col].values + 1e-12)),
                                          np.log(te[col].values + 1e-12))
        ptr, pte = p[p.fold != k], p[p.fold == k]
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.08, max_depth=6, min_samples_leaf=40,
                                          early_stopping=False, random_state=0)
        m.fit(ptr[cols].values.astype(np.float32), ptr.dz.values)
        pr = pte[["traversal", "stem", "dz"]].assign(pred=m.predict(pte[cols].values.astype(np.float32)))
        lp = pr.groupby(["traversal", "stem", "dz"], as_index=False).pred.median()
        r = r.merge(lp.rename(columns={"pred": "learned_dz"}), on=["traversal", "stem", "dz"])
        r["learned_dir"] = np.sign(r.learned_dz)
        out.append(r)
    r = pd.concat(out)
    k = UM_PER_DZ / DELTA_UM
    nz = r.dz != 0
    rows = []
    for name in ("physics", "learned"):
        dz_hat = r[f"{name}_dz"]
        rows.append(dict(lens=lens, method=name, direction_acc=(r[f"{name}_dir"][nz] == np.sign(r.dz[nz])).mean(),
                         mae_delta=((dz_hat - r.dz).abs() * k).mean(), abs_mae_delta=((dz_hat.abs() - r.dz.abs()).abs() * k).mean()))
    for name in ("tenengrad", "laplacian"):
        rows.append(dict(lens=lens, method=name, direction_acc=np.nan, mae_delta=np.nan,
                         abs_mae_delta=((r[f"{name}_absdz"] - r.dz.abs()).abs() * k).mean()))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("results/reference"))
    ap.add_argument("--lenses", default=None)
    a = ap.parse_args()
    lenses = pd.read_csv(HERE / "data" / "m3_lenses.csv").lens.tolist()
    if a.lenses:
        lenses = [x for x in lenses if x in a.lenses.split(",")]
    lca = pd.read_csv(HERE / "data" / "m3_lca.csv").set_index("lens").lca_spread_um / DELTA_UM
    rows = []
    for lens in lenses:
        path = a.cache / f"rc_feat_m2_{lens}_pre_all.parquet"
        if path.exists():
            rows += lens_rows(path, lens)
            print(pd.DataFrame(rows[-4:]).round(3).to_string(index=False), flush=True)
    t = pd.DataFrame(rows)
    t.insert(1, "lca_over_delta", t.lens.map(lca).round(4))
    a.out.mkdir(parents=True, exist_ok=True)
    t.round(4).to_csv(a.out / "reference_rows.csv", index=False)
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
