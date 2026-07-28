#!/usr/bin/env bash
# Parallel 1D-ARC object-ILP eval with breathing room between jobs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

MODE="${1:-dual}"
TIMEOUT="${2:-600}"
TRIALS="${3:-0,1,2}"
JOBS="${JOBS:-4}"
DELAY="${DELAY:-5}"
DATASET="${DATASET:-raw_data/onedarcraw/dataset}"
OUT="${OUT:-results/solver}"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

mapfile -t FILES < <(
  python - <<PY
from pathlib import Path
from solver.harness import discover, filter_files
files = filter_files(discover(Path("$DATASET")), trials="$TRIALS", limit=0)
for f in files:
    print(f)
PY
)

echo "Parallel eval: mode=${MODE} timeout=${TIMEOUT}s jobs=${JOBS} delay=${DELAY}s n=${#FILES[@]}"

if [[ "${#FILES[@]}" -eq 0 ]]; then
  echo "No files matched" >&2
  exit 1
fi

mkdir -p "${OUT}/${MODE}"

parallel --jobs "$JOBS" --delay "$DELAY" --halt soon,fail=1 \
  python -m solver.harness --mode "$MODE" --timeout "$TIMEOUT" --out "$OUT" --one {} \
  ::: "${FILES[@]}"

python - <<PY
import json
from pathlib import Path
from solver.harness import summarize

out = Path("$OUT") / "$MODE"
rows = []
for p in sorted(out.glob("*.json")):
    if p.name == "summary.json":
        continue
    rows.append(json.loads(p.read_text()))
summary = summarize(rows)
summary["mode"] = "$MODE"
summary["timeout"] = int("$TIMEOUT")
summary["jobs"] = int("$JOBS")
print(json.dumps(summary, indent=2))
(out / "summary.json").write_text(json.dumps(summary, indent=2))
print(f"Wrote {out / 'summary.json'}")
PY
