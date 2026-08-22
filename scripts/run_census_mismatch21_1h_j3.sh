#!/usr/bin/env bash
# 21 census-mismatch (pixel-road) first-3 tasks @ 1h, 3-way parallel.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

MODE="${MODE:-hybrid_census}"
TIMEOUT="${TIMEOUT:-3600}"
TRIALS="${TRIALS:-0,1,2}"
JOBS="${JOBS:-3}"
DELAY="${DELAY:-5}"
DS_SRC="${DATASET_SRC:-raw_data/onedarcraw/dataset}"
OUT="${OUT:-results/eval_${TIMEOUT}s_census_mismatch21_j${JOBS}}"
DS_TMP="$(mktemp -d /tmp/census_mismatch_first3_ds.XXXXXX)"
trap 'rm -rf "$DS_TMP"' EXIT

# Build a 21-task dataset tree (symlinks) where train census_match is false.
python - <<PY
import json
import os
from pathlib import Path

from solver.harness import discover, filter_files
from solver.census import census_match

src = Path("$DS_SRC")
dst = Path("$DS_TMP")
files = filter_files(discover(src), trials="$TRIALS", limit=0)
n = 0
for f in files:
    data = json.loads(Path(f).read_text())
    if census_match(data["train"]):
        continue
    cat = Path(f).parent.name
    out_dir = dst / cat
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / Path(f).name
    if not target.exists():
        os.symlink(Path(f).resolve(), target)
    n += 1
print(f"census_mismatch tasks: {n}")
assert n == 21, n
PY

echo "OUT=$OUT  JOBS=$JOBS  TIMEOUT=${TIMEOUT}s  DATASET=$DS_TMP"
JOBS="$JOBS" DELAY="$DELAY" DATASET="$DS_TMP" OUT="$OUT" \
  ./scripts/run_solver_eval_parallel.sh "$MODE" "$TIMEOUT" "$TRIALS"

echo "Done. Summary: $OUT/$MODE/summary.json"
