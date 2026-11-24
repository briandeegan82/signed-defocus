"""Lab through-focus sweep (experiment M4, Phase 1 part): step size from the MTF fall-off, and the
physics baseline on the calibration split.

Data (read-only, from `blur_study`): `results/lab_sweep_mtf.csv`, the raw-Bayer-plane slanted-edge
SFR of the centre square of the eSFR chart at each of the 80 focus steps (file step = 2 x step), and
`results/lab_feat_real_all.parquet`, the patch features on the chart region.

Step size. For an aberration-free circular pupil with defocus W020 = dz / (8 N^2) the OTF at normalised
shift a = 2 nu lambda N (cut-off at a = 2) is
    OTF(a) = (1/pi) * Int_{|y| < ...} 2 sin(b L(y)) / b dy,   b = 4 pi W020 a / lambda,
    L(y) = sqrt(1 - y^2) - a/2,
the exact Hopkins result for pure defocus. The measured MTF of channel c at frequency nu is modelled as
    M(s) = A_{c,nu} |OTF(nu, lambda_c, k (s - s0_c))| + F_nu,
with k (µm per step) shared by all channels and frequencies, s0_c the channel's best-focus step, A
the in-focus loss from the lens's other aberrations, pixel aperture and demosaic-free sampling, and F
the noise floor of the SFR estimate. k scales with the assumed f-number: k(N) = k(2) * 2 / N.

Splits (protocol section 2): calibration = every fourth step (0, 4, ..., 76) and the left chart half;
test = the other steps and the right half. Only the calibration split is used for the estimator here;
the test split is held for the single evaluation after the method is frozen. The MTF fit is a rig
measurement (chart SFR, not estimator features); it is reported on calibration steps and on all steps.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

N_F = 2.0
PITCH = 3.45
LAMBDA = {"r": 0.61, "g": 0.535, "b": 0.465}
FREQ = {"0125": 0.125, "025": 0.25}
F_LENS_MM, U_CHART_MM = 6.0, 300.0
CHART_X_MID = (672 + 3392) // 2
_Y = np.linspace(-1, 1, 4001)


def otf_defocus(nu_cy_um, lam, dz_um, n=N_F):
    a = 2.0 * nu_cy_um * lam * n
    w020 = np.asarray(dz_um, float) / (8.0 * n * n)
    b = 4.0 * np.pi * w020 * a / lam
    L = np.clip(np.sqrt(1.0 - _Y ** 2) - a / 2.0, 0.0, None)
    bb = b[..., None]
    with np.errstate(invalid="ignore", divide="ignore"):
        integ = np.where(np.abs(bb) < 1e-12, 2.0 * L, 2.0 * np.sin(bb * L) / bb)
    return np.trapezoid(integ, _Y, axis=-1) / np.pi


def load_mtf(path):
    m = pd.read_csv(path)
    m["s"] = m.step // 2
    rows = [dict(s=r.s, ch=c, fk=fk, mtf=getattr(r, f"mtf{fk}_{c}")) for r in m.itertuples() for c in "rgb" for fk in FREQ]
    return pd.DataFrame(rows)


def fit(d, per_channel_k=False):
    chans, fks = sorted(d.ch.unique()), sorted(d.fk.unique())
    keys = [(c, f) for c in chans for f in fks]
    nk = len(chans) if per_channel_k else 1
    ci = d.ch.map({c: i for i, c in enumerate(chans)}).values
    ai = d.apply(lambda r: keys.index((r.ch, r.fk)), axis=1).values
    fi = d.fk.map({f: i for i, f in enumerate(fks)}).values
    nu = d.fk.map(FREQ).values / PITCH
    lam = d.ch.map(LAMBDA).values
    s, y = d.s.values.astype(float), d.mtf.values

    def model(p):
        k = p[:nk][ci if per_channel_k else np.zeros_like(ci)]
        s0 = p[nk:nk + len(chans)][ci]
        A = p[nk + len(chans):nk + len(chans) + len(keys)][ai]
        F = p[nk + len(chans) + len(keys):][fi]
        out = np.empty_like(y)
        for f in range(len(fks)):
            for c in range(len(chans)):
                j = (fi == f) & (ci == c)
                out[j] = np.abs(otf_defocus(nu[j][0], lam[j][0], k[j] * (s[j] - s0[j])))
        return A * out + F

    p0 = np.r_[[3.0] * nk, [46.0] * len(chans), [0.8] * len(keys), [0.03] * len(fks)]
    lo = np.r_[[0.3] * nk, [30.0] * len(chans), [0.05] * len(keys), [0.0] * len(fks)]
    hi = np.r_[[15.0] * nk, [65.0] * len(chans), [1.5] * len(keys), [0.3] * len(fks)]
    r = least_squares(lambda p: model(p) - y, p0, bounds=(lo, hi))
    res = r.fun
    out = dict(rmse=float(np.sqrt(np.mean(res ** 2))), n=len(y))
    for i in range(nk):
        out[f"k_{chans[i]}" if per_channel_k else "k"] = r.x[i]
    for i, c in enumerate(chans):
        out[f"s0_{c}"] = r.x[nk + i]
    return out, model(r.x), r


def bootstrap(d, n_boot=200, seed=0):
    out, pred, _ = fit(d)
    resid = d.mtf.values - pred
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(n_boot):
        db = d.assign(mtf=pred + rng.choice(resid, len(resid), replace=True))
        ks.append(fit(db)[0])
    return pd.DataFrame(ks)


def step_fits(mtf_path):
    d = load_mtf(mtf_path)
    cal = d[d.s % 4 == 0]
    variants = {
        "calibration steps, both freqs": cal,
        "all steps, both freqs": d,
        "calibration steps, 0.125 cy/px": cal[cal.fk == "0125"],
        "calibration steps, 0.25 cy/px": cal[cal.fk == "025"],
        "all steps, tails only (s < 36 or s > 56)": d[(d.s < 36) | (d.s > 56)],
    }
    rows = []
    for name, dd in variants.items():
        o = fit(dd)[0]
        rows.append(dict(variant=name, **o))
    o = fit(cal, per_channel_k=True)[0]
    rows.append(dict(variant="calibration steps, k per channel", **o))
    t = pd.DataFrame(rows)
    t["k"] = t["k"].fillna(t[["k_r", "k_g", "k_b"]].mean(axis=1))
    travel = F_LENS_MM ** 2 / (U_CHART_MM - F_LENS_MM) * 1000.0
    t["lca_rb_um"] = (t.s0_r - t.s0_b) * t.k
    t["lca_rb_over_delta"] = t.lca_rb_um / (2 * N_F * PITCH)
    t["infinity_step"] = t.s0_g + travel / t.k
    t["k_if_f2.8"] = t.k * 2.8 / N_F
    bs = bootstrap(cal)
    ci = bs.quantile([0.025, 0.975])
    return t, ci, d, cal


def frame_table(feat_path, steps, half):
    d = pd.read_parquet(feat_path, columns=["ch_ten_rb", "cx_grad_mean", "step", "px"])
    d["s"] = d.step // 2
    centre = d.px + 64 < CHART_X_MID if half == "left" else d.px >= CHART_X_MID
    d = d[d.s.isin(steps) & centre]
    d["lum"] = np.log(d.cx_grad_mean + 1e-9)
    f = d.groupby("s")[["ch_ten_rb", "lum"]].median().rename(columns={"ch_ten_rb": "c"})
    f["n_patches"] = d.groupby("s").size()
    return f.reset_index()


def baseline_calibration(feat_path, s_focus):
    cal = frame_table(feat_path, range(0, 80, 4), "left")
    cal["dz_steps"] = cal.s - s_focus
    rows = []
    for i in range(len(cal)):
        tr, te = cal.drop(index=i), cal.iloc[[i]]
        trn = tr[tr.dz_steps.abs() > 0.5]
        best = (0.0, 1, -1.0)
        for c0 in np.quantile(trn.c, np.linspace(0.02, 0.98, 97)):
            for sg in (1, -1):
                acc = np.mean(sg * np.sign(trn.c - c0) == np.sign(trn.dz_steps))
                if acc > best[2]:
                    best = (c0, sg, acc)
        c0, sg = best[:2]
        dir_ok = bool(sg * np.sign(te.c.values[0] - c0) == np.sign(te.dz_steps.values[0]))
        if te.s.values[0] in (cal.s.min(), cal.s.max()):
            dz_hat = np.nan
        else:
            grid = np.linspace(tr.s.min(), tr.s.max(), 2001)
            sd = tr[["c", "lum"]].std().values
            pts = np.column_stack([np.interp(grid, tr.s, tr[k]) for k in ("c", "lum")]) / sd
            x = te[["c", "lum"]].values / sd
            dz_hat = grid[np.argmin(((pts - x) ** 2).sum(1))] - s_focus
        rows.append(dict(s=int(te.s.values[0]), dz_steps=float(te.dz_steps.values[0]), c=float(te.c.values[0]),
                         lum=float(te.lum.values[0]), n_patches=int(te.n_patches.values[0]),
                         c0=float(c0), sign=int(sg), dir_ok=dir_ok, dz_hat_steps=dz_hat))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--estimator", type=Path, required=True, help="blur_study root")
    ap.add_argument("--out", type=Path, default=Path("results/lab_sweep"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t, ci, d, cal = step_fits(a.estimator / "results" / "lab_sweep_mtf.csv")
    t.round(4).to_csv(a.out / "step_size_fits.csv", index=False)
    ci.round(4).to_csv(a.out / "step_size_bootstrap_ci.csv")
    prim = t.iloc[0]
    _, pred, _ = fit(cal)
    cal.assign(pred=pred).round(5).to_csv(a.out / "mtf_fit_calibration.csv", index=False)
    b = baseline_calibration(a.estimator / "results" / "lab_feat_real_all.parquet", prim.s0_g)
    b["err_um"] = (b.dz_hat_steps - b.dz_steps) * prim.k
    b.round(5).to_csv(a.out / "baseline_calibration_frames.csv", index=False)
    print(t.round(3).to_string())
    print(ci.round(3).to_string())
    print(b.round(3).to_string())
    nz = b[b.dz_steps.abs() > 0.5]
    print("direction acc (calibration, leave-one-frame-out):", round(nz.dir_ok.mean(), 3), "n", len(nz))
    print("displacement MAE um:", round(b.err_um.abs().mean(), 2), "p90", round(b.err_um.abs().quantile(0.9), 2))


if __name__ == "__main__":
    main()
