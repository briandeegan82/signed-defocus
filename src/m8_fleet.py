"""M8 follow-up: ROC and many-frame aggregation of the defocus alarm, from the committed per-frame
M8 tables (`results/m8_confounds/<lens>/m8_frames.csv`; held-out predictions, five traversal folds).

Score: |predicted DZ| of a frame. ROC AUC of each defocused condition (DZ -0.02, +0.02) against each
in-focus condition (in focus, motion, fog); descriptive, thresholds are not fitted.

Aggregation over N frames (N = 1, 10, 100): the alarm statistic is |mean predicted DZ| over N frames
drawn with replacement from one condition's held-out frames (distinct scenes, so treated as
independent; consecutive frames of one drive are correlated, which makes this optimistic). The
threshold is the 95th percentile of the statistic on 2,000 in-focus draws; the alarm rate per
condition is measured on 2,000 independent draws.

  python src/m8_fleet.py --m8 results/m8_confounds --out results/m8_confounds/fleet/m8_fleet.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

LENSES = ("synth_lcaP", "laikin")
POS = ("defocus -0.02", "defocus +0.02")
NEG = ("in focus", "motion", "fog")
NS = (1, 10, 100)


def agg(x, n, draws, rng):
    return np.abs(x[rng.integers(0, len(x), (draws, n))].mean(1))


def lens_rows(fr, lens, draws=2000, seed=0):
    rng = np.random.default_rng(seed)
    dz = {c: g.dz_pred.values for c, g in fr.groupby("condition")}
    rows = []
    for p in POS:
        for q in NEG:
            u = mannwhitneyu(np.abs(dz[p]), np.abs(dz[q])).statistic  # AUC = U / (n_p n_q), ties count half
            rows.append(dict(lens=lens, kind="auc", condition=p, against=q, n=1,
                             value=u / (len(dz[p]) * len(dz[q]))))
    for n in NS:
        thr = np.percentile(agg(dz["in focus"], n, draws, rng), 95)
        for c in POS + NEG:
            rows.append(dict(lens=lens, kind="alarm", condition=c, against="", n=n,
                             value=(agg(dz[c], n, draws, rng) > thr).mean()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m8", type=Path, default=Path("results/m8_confounds"))
    ap.add_argument("--out", type=Path, default=Path("results/m8_confounds/fleet/m8_fleet.csv"))
    a = ap.parse_args()
    rows = []
    for lens in LENSES:
        rows += lens_rows(pd.read_csv(a.m8 / lens / "m8_frames.csv"), lens)
    t = pd.DataFrame(rows)
    t.to_csv(a.out, index=False, float_format="%.4f")
    print(t.pivot_table(index=["lens", "kind", "condition", "against"], columns="n", values="value").round(3))


if __name__ == "__main__":
    main()
