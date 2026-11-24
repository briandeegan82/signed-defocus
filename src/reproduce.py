"""M9: rerun every analysis from the caches and check its CSVs against the committed results.

Each step runs one committed script into a scratch directory, then every CSV the committed results
directory holds is compared with the regenerated one: same columns and rows, strings equal, numbers
within --rtol / --atol (NaN equals NaN). A step whose script or inputs are missing is reported as
skipped, not passed. Regenerated CSVs with no committed counterpart are listed as "new".

Not rerun: renders and feature extraction (GPU, hours; their parquet caches are hashed into the
provenance instead), and the held-out lab test split, which no script touches until the method is
frozen (docs/PROTOCOL.md section 2). Figures are rebuilt to check they run, not compared byte-wise.

    python src/reproduce.py --estimator ~/blur_study --data ~/sd_data --scratch ~/sd_work/m9
"""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def steps(est, data):
    cache = est / "results"
    fv = data / "m7" / "rc_feat_fieldvarying_sony_pre_all.parquet"
    return [
        ("physics_baseline_v0", "results", [
            ["physics_baseline.py", "--cache", cache, "--lca", "data/lens_lca.csv", "--out", "{out}"],
            ["rescore_dof.py", "--results", "{out}", "--optics", "data/lens_optics.csv", "--out", "{out}"]],
         [cache / "rc_feat_robotcar_render_laikin_pre_all.parquet"]),
        ("m3_gate", "results/m3_gate", [
            ["physics_baseline.py", "--cache", data / "m3", "--lca", "data/m3_lca.csv", "--lenses", "lca",
             "--cache-fmt", "rc_feat_{lens}_pre_all.parquet", "--out", "{out}"],
            ["rescore_dof.py", "--results", "{out}", "--optics", "data/m3_lenses.csv", "--out", "{out}"]],
         [data / "m3" / "rc_feat_m3_ref_pre_all.parquet"]),
        ("m2_gate", "results/m2_gate", [
            ["m2_continuous.py", "score", "--cache", data / "m2" / "rc_feat_m2_synth_lcaP_pre_all.parquet",
             "--ladder", cache / "rc_feat_robotcar_render_synth_lcaP_pre_all.parquet", "--out", "{out}"]],
         [data / "m2" / "rc_feat_m2_synth_lcaP_pre_all.parquet"]),
        ("lab_sweep", "results/lab_sweep", [
            ["lab_sweep.py", "--estimator", est, "--out", "{out}"]],
         [cache / "lab_sweep_mtf.csv", cache / "lab_feat_real_all.parquet"]),
        ("m4_repeat", "results/m4_repeat", [
            ["m4_repeat.py", "--estimator", est, "--out", "{out}"]],
         [cache / "lab_feat_real_all.parquet"]),
        ("m6_illuminant", "results/m6_illuminant", [
            ["m6_illuminant.py", "score", "--cache", cache, "--m6", data / "m6", "--out", "{out}"]],
         [data / "m6"]),
        ("m7_field", "results/m7_field", [
            ["m7_field.py", "score", "--cache", cache, "--fv", fv,
             "--field-labels", est / "data/raw/robotcar_render_fieldvarying/field_labels.json",
             "--lab-field", cache / "lab_sweep_field_mtf.csv", "--out", "{out}"]],
         [fv]),
        ("m8_laikin", "results/m8_confounds/laikin", [
            ["m8_confounds.py", "--cache", cache, "--lens", "laikin", "--out", "{out}"]],
         [cache / "rc_feat_confound_motion.parquet"]),
        ("m8_synth_lcaP", "results/m8_confounds/synth_lcaP", [
            ["m8_confounds.py", "--cache", cache, "--lens", "synth_lcaP", "--conf-dir", data / "m8" / "synth_lcaP",
             "--out", "{out}"]],
         [data / "m8" / "synth_lcaP"]),
        ("figures", None, [["figures.py", "--out", "{out}"]], []),
    ]


def compare(ref, new, rtol, atol):
    a, b = pd.read_csv(ref), pd.read_csv(new)
    if list(a.columns) != list(b.columns):
        return "columns differ"
    if a.shape != b.shape:
        return f"shape {a.shape} vs {b.shape}"
    worst = 0.0
    for c in a.columns:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            x, y = x.to_numpy(float), y.to_numpy(float)
            ok = np.isclose(x, y, rtol=rtol, atol=atol, equal_nan=True)
            if not ok.all():
                return f"{c}: {int((~ok).sum())} values differ, max |d| {np.nanmax(np.abs(x - y)):.3g}"
            d = np.abs(x - y)
            worst = max(worst, float(np.nanmax(d)) if np.isfinite(d).any() else 0.0)
        elif not (x.astype(object).fillna("").astype(str) == y.astype(object).fillna("").astype(str)).all():
            return f"{c}: strings differ"
    return f"ok (max |d| {worst:.3g})"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def provenance(inputs):
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()
    files = sorted({f for p in inputs if p.exists() for f in ([p] if p.is_file() else p.rglob("*.parquet"))})
    return dict(commit=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain", "--", "src", "data")),
                python=platform.python_version(),
                packages={k: metadata.version(k) for k in ("numpy", "pandas", "pyarrow", "scipy", "matplotlib")},
                inputs={str(f): sha256(f) for f in files})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--estimator", type=Path, required=True, help="blur_study root (frozen, read-only)")
    ap.add_argument("--data", type=Path, required=True, help="render/cache root (sd_data)")
    ap.add_argument("--scratch", type=Path, required=True, help="output root, outside the repo")
    ap.add_argument("--only", default=None, help="comma-separated step names")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--atol", type=float, default=1e-12)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    rows, inputs = [], []
    for name, ref, cmds, needs in steps(a.estimator.expanduser(), a.data.expanduser()):
        if a.only and name not in a.only.split(","):
            continue
        out = a.scratch / name
        missing = [str(p) for p in needs if not p.exists()] + \
            [c[0] for c in cmds if not (REPO / "src" / c[0]).exists()]
        if missing:
            rows.append(dict(step=name, file="", status="skipped: missing " + ", ".join(missing)))
            continue
        inputs += needs
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        failed = None
        for c in cmds:
            argv = [sys.executable, str(REPO / "src" / c[0])] + [str(x).replace("{out}", str(out)) for x in c[1:]]
            r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
            (out / f"{c[0]}.log").write_text(r.stdout + r.stderr)
            if r.returncode:
                failed = f"failed: {c[0]} exit {r.returncode}"
                break
        if failed or ref is None:
            rows.append(dict(step=name, file="", status=failed or "ran"))
            continue
        refd = REPO / ref
        for f in sorted(refd.glob("*.csv")):
            n = out / f.name
            rows.append(dict(step=name, file=f"{ref}/{f.name}",
                             status=compare(f, n, a.rtol, a.atol) if n.exists() else "not regenerated"))
        for n in sorted(set(p.name for p in out.glob("*.csv")) - set(p.name for p in refd.glob("*.csv"))):
            rows.append(dict(step=name, file=f"{ref}/{n}", status="new (not committed)"))
    t = pd.DataFrame(rows)
    t.to_csv(a.scratch / "reproduce_report.csv", index=False)
    (a.scratch / "provenance.json").write_text(json.dumps(provenance(inputs), indent=1))
    print(t.to_string(index=False))
    bad = ~t.status.str.startswith(("ok", "ran", "new"))
    print(f"\n{int((~bad).sum())} ok/ran, {int(bad.sum())} not ok; report and provenance in {a.scratch}")
    sys.exit(int(bad.any()))


if __name__ == "__main__":
    main()
