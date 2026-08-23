#!/usr/bin/env bash
# Rerun the 1d_scale_dp first-3 wave that was contaminated by host standby
# during match33 @1h (JOBS=3 concurrent; all three show ~5.5h wall elapsed
# vs 3600s budget). Writes back into the match33 results tree and rewrites
# summary.json over all 33.
#
# Tasks: 1d_scale_dp_{0,1,2} only.
#
# Usage (from repo root):
#   ./scripts/rerun_match33_scale_dp_1h.sh
#   DRY_RUN=1 ./scripts/rerun_match33_scale_dp_1h.sh
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
OUT="${OUT:-results/eval_${TIMEOUT}s_census_match33_j${JOBS}}"
DRY_RUN="${DRY_RUN:-0}"
MODE_DIR="${OUT}/${MODE}"

echo "Rerun match33 scale_dp wave  OUT=${OUT}  JOBS=${JOBS}  TIMEOUT=${TIMEOUT}s  DRY_RUN=${DRY_RUN}"
echo "Host nproc=$(nproc)"
if [[ "$(nproc)" -lt "$JOBS" ]]; then
  echo "ALERT: JOBS=${JOBS} > nproc=$(nproc). Aborting." >&2
  exit 1
fi
[[ -d "$MODE_DIR" ]] || { echo "missing results dir: $MODE_DIR" >&2; exit 1; }

PENDING_LIST="$(mktemp)"
trap 'rm -f "$PENDING_LIST"' EXIT

python - <<PY
import json
from pathlib import Path

src = Path("$DS_SRC")
out = Path("$MODE_DIR")
pending_path = Path("$PENDING_LIST")

cat = "1d_scale_dp"
trials = [t.strip() for t in "$TRIALS".split(",") if t.strip()]
selected = []
print("Prior 1h rows for scale_dp wave:")
for t in trials:
    f = src / cat / f"{cat}_{t}.json"
    if not f.is_file():
        raise SystemExit(f"missing dataset file: {f}")
    result = out / f"{cat}_{f.stem}.json"
    if result.is_file():
        row = json.loads(result.read_text())
        print(
            f"  {cat}/{f.name}: exact={row.get('exact_ok')} "
            f"elapsed={row.get('elapsed')} level={row.get('level')} "
            f"reason={row.get('failure_reason')}"
        )
    else:
        print(f"  {cat}/{f.name}: (no prior result JSON)")
    selected.append(f)

print(f"SELECTED ({len(selected)}) standby-contaminated concurrent wave:")
for f in selected:
    print(f"  {f.parent.name}/{f.name}")

pending_path.write_text("\n".join(str(f) for f in selected) + "\n")
Path("$PENDING_LIST.n").write_text(f"{len(selected)}\n")
PY

read -r N_PENDING < "${PENDING_LIST}.n"
rm -f "${PENDING_LIST}.n"

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "DRY_RUN=1 — no eval. Re-run without DRY_RUN to execute ${N_PENDING} tasks."
  exit 0
fi

mapfile -t PENDING_SRC < "$PENDING_LIST"
[[ "${#PENDING_SRC[@]}" -gt 0 ]] || { echo "no pending files"; exit 1; }

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

for src in "${PENDING_SRC[@]}"; do
  stem="$(basename "$src" .json)"
  task_dir="${MODE_DIR}/${stem}"
  if [[ -d "$task_dir" ]]; then
    echo "[clean] $task_dir"
    rm -rf "$task_dir"
  fi
done

echo "Running ${#PENDING_SRC[@]} tasks → ${OUT} (JOBS=${JOBS})…"
parallel --jobs "$JOBS" --delay "$DELAY" \
  --joblog "${MODE_DIR}/parallel.scale_dp_rerun.joblog" \
  python -m solver.harness --mode "$MODE" --timeout "$TIMEOUT" --out "$OUT" --one {} \
  ::: "${PENDING_SRC[@]}" || true

python - <<PY
import json
from pathlib import Path
from solver.harness import summarize
from solver.run_meta import collect_run_meta, mark_finished

out = Path("$MODE_DIR")
rows = []
for p in sorted(out.glob("*.json")):
    if p.name in ("summary.json", "run_manifest.json"):
        continue
    rows.append(json.loads(p.read_text()))
assert len(rows) == 33, len(rows)
summary = summarize(rows)
summary["mode"] = "$MODE"
summary["timeout"] = int("$TIMEOUT")
summary["jobs"] = int("$JOBS")
meta = collect_run_meta(
    mode="$MODE",
    timeout=int("$TIMEOUT"),
    jobs=int("$JOBS"),
    trials="$TRIALS",
    dataset="$DS_SRC",
    out="$OUT",
    extra={
        "entry": "rerun_match33_scale_dp_1h",
        "n_tasks": len(rows),
        "n_rerun": int("$N_PENDING"),
        "reason": "standby_inflated_wall_clock_on_scale_dp_wave",
    },
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
n = int(summary["n"])
exact = float(summary["exact_accuracy"])
soft = float(summary["soft_accuracy"])
print(f"summary n={n} exact={exact:.4f} ({round(exact*n)}/{n}) soft={soft:.4f}")
(out / "summary.json").write_text(json.dumps(summary, indent=2))
(out / "run_manifest.json").write_text(json.dumps(summary["run_meta"], indent=2))
print(f"Wrote {out / 'summary.json'}")

print("Rerun outcomes:")
for line in Path("$PENDING_LIST").read_text().splitlines():
    if not line.strip():
        continue
    f = Path(line)
    rp = out / f"{f.parent.name}_{f.stem}.json"
    r = json.loads(rp.read_text())
    print(
        f"  {f.parent.name}/{f.name}: exact={r.get('exact_ok')} "
        f"elapsed={r.get('elapsed')} soft={r.get('soft_accuracy')} "
        f"level={r.get('level')} reason={r.get('failure_reason')}"
    )
PY

echo "Done. Summary: ${MODE_DIR}/summary.json"
