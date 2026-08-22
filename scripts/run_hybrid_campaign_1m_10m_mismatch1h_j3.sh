#!/usr/bin/env bash
# Compound hybrid eval campaign:
#   1) all 54 @ 60s  JOBS=3  → git add results / commit / push
#   2) all 54 @ 600s JOBS=3 → git add results / commit / push
#   3) census-mismatch 21 @ 3600s JOBS=3 → git add results / commit / push
#
# Usage (from repo root):
#   ./scripts/run_hybrid_campaign_1m_10m_mismatch1h_j3.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

MODE="${MODE:-hybrid_census}"
TRIALS="${TRIALS:-0,1,2}"
JOBS="${JOBS:-3}"
DELAY="${DELAY:-5}"
DATASET="${DATASET:-raw_data/onedarcraw/dataset}"
REMOTE="${REMOTE:-origin}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# After each eval stage: add only that results tree, commit, push.
commit_results_and_push() {
  local path="$1"
  local msg="$2"
  [[ -d "$path" ]] || { echo "[git] missing results dir: $path" >&2; exit 1; }
  # Drop anything else already staged so this commit is results-only.
  git reset HEAD --quiet 2>/dev/null || true
  echo "[git] add results: ${path}"
  git add -- "$path"
  if git diff --cached --quiet; then
    echo "[git] nothing new to commit for ${path}"
    return 0
  fi
  git commit -m "$(cat <<EOF
${msg}

EOF
)"
  echo "[git] push ${BRANCH} → ${REMOTE}"
  git push -u "$REMOTE" "HEAD:${BRANCH}"
  echo "[git] done: committed+pushed ${path}"
}

run_full54() {
  local timeout="$1"
  local out="$2"
  export JOBS DELAY DATASET OUT="$out"
  echo "=== full54 ${MODE} timeout=${timeout}s JOBS=${JOBS} OUT=${out} ==="
  ./scripts/run_solver_eval_parallel.sh "$MODE" "$timeout" "$TRIALS"
  local summary="${out}/${MODE}/summary.json"
  [[ -f "$summary" ]] || { echo "missing summary: $summary" >&2; exit 1; }
  python - <<PY
import json
from pathlib import Path
s = json.loads(Path("$summary").read_text())
n = int(s.get("n") or 0)
assert n == 54, n
exact = float(s.get("exact_accuracy") or 0.0)
soft = float(s.get("soft_accuracy") or 0.0)
print(f"summary n={n} exact={exact:.4f} ({round(exact*54)}/54) soft={soft:.4f}")
PY
}

echo "Compound campaign on branch=${BRANCH} JOBS=${JOBS}"
echo "Host nproc=$(nproc)"

# --- Stage 1: 1 minute, all 54 ---
OUT_60="results/eval_60s_hybrid_all54_j${JOBS}"
run_full54 60 "$OUT_60"
commit_results_and_push "$OUT_60" \
  "eval: hybrid_census all54 @60s JOBS=${JOBS} (${OUT_60})"

# --- Stage 2: 10 minutes, all 54 ---
OUT_600="results/eval_600s_hybrid_all54_j${JOBS}"
run_full54 600 "$OUT_600"
commit_results_and_push "$OUT_600" \
  "eval: hybrid_census all54 @600s JOBS=${JOBS} (${OUT_600})"

# --- Stage 3: census-mismatch 21 @ 1h ---
OUT_MISMATCH="results/eval_3600s_census_mismatch21_j${JOBS}"
echo "=== census-mismatch21 ${MODE} timeout=3600s JOBS=${JOBS} OUT=${OUT_MISMATCH} ==="
OUT="$OUT_MISMATCH" JOBS="$JOBS" DELAY="$DELAY" MODE="$MODE" TRIALS="$TRIALS" \
  ./scripts/run_census_mismatch21_1h_j3.sh
[[ -f "${OUT_MISMATCH}/${MODE}/summary.json" ]] || {
  echo "missing summary: ${OUT_MISMATCH}/${MODE}/summary.json" >&2
  exit 1
}
commit_results_and_push "$OUT_MISMATCH" \
  "eval: hybrid_census census-mismatch21 @3600s JOBS=${JOBS} (${OUT_MISMATCH})"

echo "Compound campaign finished."
echo "  ${OUT_60}/${MODE}/summary.json"
echo "  ${OUT_600}/${MODE}/summary.json"
echo "  ${OUT_MISMATCH}/${MODE}/summary.json"
