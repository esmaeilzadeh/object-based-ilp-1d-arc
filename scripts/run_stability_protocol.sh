#!/usr/bin/env bash
# B0 / stepwise stability protocol: R repeats, 1 worker, 120s, trials 0,1,2.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .venv/bin/activate ]] && source .venv/bin/activate

TAG="${1:-b0}"
TIMEOUT="${2:-120}"
R="${3:-3}"
TRIALS="${4:-0,1,2}"
BASE_OUT="results/solver/${TAG}_stability"

for i in $(seq 1 "$R"); do
  OUT="${BASE_OUT}/r${i}"
  echo "======== ${TAG} repeat ${i}/${R} OUT=${OUT} ========"
  rm -rf "${OUT}"
  mkdir -p "${OUT}"
  OUT="$OUT" JOBS=1 DELAY=1 \
    ./scripts/run_solver_eval_parallel.sh block_primary "$TIMEOUT" "$TRIALS"
done

python - <<PY
import json
from pathlib import Path
from collections import defaultdict

base = Path("${BASE_OUT}")
expected_tasks = None
per_task_runs = defaultdict(list)
exact_counts = []
reason_hist = defaultdict(int)

for rdir in sorted(base.glob("r*")):
    rows = []
    for p in rdir.joinpath("block_primary").glob("*.json"):
        if p.name == "summary.json":
            continue
        rows.append(json.loads(p.read_text()))
    exact = sum(1 for row in rows if row.get("exact_ok") or row.get("ok"))
    exact_counts.append(exact)
    for row in rows:
        key = f"{row['task']}/{Path(row['file']).stem}"
        per_task_runs[key].append(bool(row.get("exact_ok") or row.get("ok")))
        fr = row.get("failure_reason")
        if fr:
            reason_hist[fr] += 1
        elif not (row.get("exact_ok") or row.get("ok")):
            reason_hist["missing_reason"] += 1

stable_pass = stable_fail = flaky = 0
for key, flags in per_task_runs.items():
    if all(flags):
        stable_pass += 1
    elif not any(flags):
        stable_fail += 1
    else:
        flaky += 1

summary = {
    "tag": "${TAG}",
    "timeout": int("${TIMEOUT}"),
    "R": int("${R}"),
    "exact_per_repeat": exact_counts,
    "exact_mean": sum(exact_counts) / len(exact_counts) if exact_counts else 0,
    "stable_pass": stable_pass,
    "stable_fail": stable_fail,
    "flaky": flaky,
    "failure_reason_hist": dict(reason_hist),
    "n_tasks": len(per_task_runs),
}
out = base / "stability_summary.json"
out.write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
print(f"Wrote {out}")
PY
