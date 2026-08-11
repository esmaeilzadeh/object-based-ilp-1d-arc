#!/usr/bin/env bash
# Parallel 1D-ARC object-ILP eval with breathing room between jobs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

MODE="${1:-block_primary}"
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

python - <<PY
import json
from pathlib import Path
from solver.run_meta import collect_run_meta
out = Path("$OUT") / "$MODE"
meta = collect_run_meta(
    mode="$MODE",
    timeout=int("$TIMEOUT"),
    jobs=int("$JOBS"),
    trials="$TRIALS",
    dataset="$DATASET",
    out="$OUT",
    extra={"entry": "run_solver_eval_parallel", "phase": "start", "n_files": int("${#FILES[@]}")},
)
(out / "run_manifest.json").write_text(json.dumps(meta, indent=2))
print(f"Wrote {out / 'run_manifest.json'} (start)")
PY

parallel --jobs "$JOBS" --delay "$DELAY" --joblog "${OUT}/${MODE}/parallel.joblog" \
  python -m solver.harness --mode "$MODE" --timeout "$TIMEOUT" --out "$OUT" --one {} \
  ::: "${FILES[@]}"

python - <<PY
import json
from pathlib import Path
from solver.harness import summarize
from solver.run_meta import collect_run_meta, mark_finished

out = Path("$OUT") / "$MODE"
rows = []
for p in sorted(out.glob("*.json")):
    if p.name in ("summary.json", "run_manifest.json"):
        continue
    rows.append(json.loads(p.read_text()))
summary = summarize(rows)
summary["mode"] = "$MODE"
summary["timeout"] = int("$TIMEOUT")
summary["jobs"] = int("$JOBS")
meta = collect_run_meta(
    mode="$MODE",
    timeout=int("$TIMEOUT"),
    jobs=int("$JOBS"),
    trials="$TRIALS",
    dataset="$DATASET",
    out="$OUT",
    extra={"entry": "run_solver_eval_parallel", "n_tasks": len(rows)},
)
man = out / "run_manifest.json"
if man.exists():
    try:
        prev = json.loads(man.read_text())
        if prev.get("started_at"):
            meta["started_at"] = prev["started_at"]
        if prev.get("git_sha") and not meta.get("git_sha"):
            meta["git_sha"] = prev["git_sha"]
    except Exception:
        pass
summary["run_meta"] = mark_finished(meta)
print(json.dumps(summary, indent=2))
(out / "summary.json").write_text(json.dumps(summary, indent=2))
(out / "run_manifest.json").write_text(json.dumps(summary["run_meta"], indent=2))
print(f"Wrote {out / 'summary.json'}")
print(f"Wrote {out / 'run_manifest.json'}")
PY
