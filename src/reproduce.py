"""M9: rerun every analysis from the caches and check its CSVs against the committed results.

Each step runs one committed script into a scratch directory, then every CSV the committed results
directory holds is compared with the regenerated one: same columns and rows, strings equal, numbers
within --rtol / --atol (NaN equals NaN). A step whose script or inputs are missing is reported as
skipped, not passed. Regenerated CSVs with no committed counterpart are listed as "new".

Not rerun: renders and feature extraction (GPU, hours; their parquet caches are hashed into the
provenance instead). The `lab_test` step verifies that the frozen held-out laboratory table
reproduces byte-consistently from the committed feature cache without modifying or tuning any
parameter (docs/PROTOCOL.md section 2). Figures are rebuilt to check they run, not compared byte-wise.
Every input a step reads (feature caches, MTF tables, raw duplicates) is SHA-256-hashed into
provenance.json with the commit, a dirty flag for src/ and data/, and package versions.

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
    rc = lambda lens: cache / f"rc_feat_robotcar_render_{lens}_pre_all.parquet"
    v0 = [rc(x) for x in pd.read_csv(REPO / "data" / "lens_lca.csv").lens]
    return [
        ("physics_baseline_v0", "results", [
            ["physics_baseline.py", "--cache", cache, "--lca", "data/lens_lca.csv", "--out", "{out}"],
            ["rescore_dof.py", "--results", "{out}", "--optics", "data/lens_optics.csv", "--out", "{out}"]],
         v0),
        ("m3_gate", "results/m3_gate", [
            ["physics_baseline.py", "--cache", data / "m3", "--lca", "data/m3_lca.csv", "--lenses", "lca",
             "--cache-fmt", "rc_feat_{lens}_pre_all.parquet", "--out", "{out}"],
            ["rescore_dof.py", "--results", "{out}", "--optics", "data/m3_lenses.csv", "--out", "{out}"]],
         [data / "m3"]),
        ("m2_gate", "results/m2_gate", [
            ["m2_continuous.py", "score", "--cache", data / "m2" / "rc_feat_m2_synth_lcaP_pre_all.parquet",
             "--ladder", cache / "rc_feat_robotcar_render_synth_lcaP_pre_all.parquet", "--out", "{out}"]],
         [data / "m2" / "rc_feat_m2_synth_lcaP_pre_all.parquet", rc("synth_lcaP")]),
        ("lab_sweep", "results/lab_sweep", [
            ["lab_sweep.py", "--estimator", est, "--out", "{out}"],
            ["fig_lab_sharpness_mtf.py", "--feat", cache / "lab_feat_real_all.parquet",
             "--csv-out", "{out}/sharpness_mtf_calibration.csv", "--out", "{out}"]],
         [cache / "lab_sweep_mtf.csv", cache / "lab_feat_real_all.parquet"]),
        ("m4_repeat", "results/m4_repeat", [
            ["m4_repeat.py", "--estimator", est, "--out", "{out}"]],
         [cache / "lab_feat_real_all.parquet", est / "data/lab_images/archives/duplicates"]),
        ("m6_illuminant", "results/m6_illuminant", [
            ["m6_illuminant.py", "score", "--cache", cache, "--m6", data / "m6", "--out", "{out}"]],
         [data / "m6", rc("synth_lcaP")]),
        ("m7_field", "results/m7_field", [
            ["m7_field.py", "score", "--cache", cache, "--fv", fv,
             "--field-labels", est / "data/raw/robotcar_render_fieldvarying/field_labels.json",
             "--lab-field", cache / "lab_sweep_field_mtf.csv", "--out", "{out}"]],
         [fv, rc("sony"), est / "data/raw/robotcar_render_fieldvarying/field_labels.json",
          cache / "lab_sweep_field_mtf.csv"]),
        ("m8_synth_lcaP", "results/m8_confounds/synth_lcaP", [
            ["m8_confounds.py", "--cache", cache, "--lens", "synth_lcaP", "--conf-dir", data / "m8" / "synth_lcaP",
             "--out", "{out}"]],
         [data / "m8" / "synth_lcaP", rc("synth_lcaP")]),
        ("m8_m5_lab", "results/m8_confounds/m5_lab", [
            ["m8_confounds.py", "--cache", data / "m8" / "m5_lab", "--lens", "m5_lab",
             "--conf-dir", data / "m8" / "m5_lab", "--out", "{out}"]],
         [data / "m8" / "m5_lab"]),
        ("m8_fleet", "results/m8_confounds/fleet", [
            ["m8_fleet.py", "--m8", REPO / "results/m8_confounds", "--out", "{out}/m8_fleet.csv"]],
         [REPO / "results/m8_confounds/synth_lcaP/m8_frames.csv",
          REPO / "results/m8_confounds/m5_lab/m8_frames.csv"]),
        ("phase2", "results/phase2", [
            ["phase2_score.py", "--cache", data / "phase2", "--out", "{out}"]],
         [data / "phase2"]),
        ("m5_lab", "results/m5_lab", [
            ["m5_lab_lens.py", "score", "--cache", data / "m5", "--out", "{out}"]],
         [data / "m5"]),
        ("reference", "results/reference", [
            ["reference_rows.py", "--cache", data / "phase2", "--out", "{out}"]],
         [data / "phase2"]),
        ("lab_test", "results/lab_test", [
            ["lab_test.py", "--estimator", est, "--m5", data / "m5", "--out", "{out}"]],
         [cache / "lab_feat_real_all.parquet", data / "m5"]),
        ("lab_transfer", "results/lab_transfer", [
            ["lab_transfer.py", "--estimator", est, "--out", "{out}"]],
         [cache / "lab_feat_real_all.parquet"]),
        ("figures", None, [
            ["figures.py", "--out", "{out}"],
            ["fig_confound_examples.py", "--out", "{out}"],
            ["fig_lab_sharpness_mtf.py", "--out", "{out}"]], []),
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
    files = sorted({f for p in inputs if p.exists()
                    for f in ([p] if p.is_file() else [*p.glob("*.parquet"), *p.glob("*.raw")])})
    return dict(commit=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain", "--", "src", "data")),
                python=platform.python_version(),
                packages={k: metadata.version(k) for k in ("numpy", "pandas", "pyarrow", "scipy", "matplotlib")},
                inputs={str(f).replace(str(Path.home()), "~"): sha256(f) for f in files})


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
        pat = "*.csv" if ref == "results" else "**/*.csv"  # results/ itself also holds the other steps' dirs
        have = {str(p.relative_to(refd)) for p in refd.glob(pat)}
        made = {str(p.relative_to(out)) for p in out.glob(pat)}
        for f in sorted(have):
            rows.append(dict(step=name, file=f"{ref}/{f}", status=compare(refd / f, out / f, a.rtol, a.atol)
                             if f in made else "not regenerated"))
        for f in sorted(made - have):
            rows.append(dict(step=name, file=f"{ref}/{f}", status="new (not committed)"))
    t = pd.DataFrame(rows)
    t.to_csv(a.scratch / "reproduce_report.csv", index=False)
    (a.scratch / "provenance.json").write_text(json.dumps(provenance(inputs), indent=1))
    print(t.to_string(index=False))
    bad = ~t.status.str.startswith(("ok", "ran", "new"))
    print(f"\n{int((~bad).sum())} ok/ran, {int(bad.sum())} not ok; report and provenance in {a.scratch}")
    sys.exit(int(bad.any()))


if __name__ == "__main__":
    main()
