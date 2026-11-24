#!/usr/bin/env bash
# Phase 2 main render: every M3 design (data/m3_lenses.csv) on every RobotCar plate at 8 continuous
# displacements (src/m2_continuous.py render --n-plates 0). One feature parquet per lens in $OUT;
# a lens whose parquet exists is skipped, so the script can be re-run after an interruption.
#   src/phase2_render.sh ~/blur_study <noise_model.json> ~/sd_data/phase2 [python]
set -euo pipefail
EST=$1; NOISE=$2; OUT=$3; PY=${4:-python}
cd "$(dirname "$0")/.."
tail -n +2 data/m3_lenses.csv | while IFS=, read -r lens _ _ _ long_ca spherical _; do
  [ -f "$OUT/rc_feat_m2_${lens}_pre_all.parquet" ] && { echo "skip $lens"; continue; }
  echo "=== $lens long_ca=$long_ca spherical=$spherical $(date -Is)"
  "$PY" src/m2_continuous.py render --estimator "$EST" --noise-model "$NOISE" --out "$OUT" \
    --lens "$lens" --long-ca "$long_ca" --spherical "$spherical" --n-plates 0 --k 8
  rm -rf "${OUT:?}/$lens/pre"
done
