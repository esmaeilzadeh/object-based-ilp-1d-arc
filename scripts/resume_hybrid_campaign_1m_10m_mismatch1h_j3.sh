#!/usr/bin/env bash
# Resume run_hybrid_campaign_1m_10m_mismatch1h_j3.sh after an interrupt.
#
# Detects completed stages from on-disk artifacts:
#   1) results/eval_60s_hybrid_all54_j3/.../summary.json
#   2) results/eval_600s_hybrid_all54_j3/.../summary.json
#   3) results/eval_3600s_census_mismatch21_j3/... — skip tasks that already
#      have a valid {cat}_{stem}.json; re-run only the rest (cleans partial
#      task dirs first), then write summary + commit/push.
#
# Usage (from repo root):
#   ./scripts/resume_hybrid_campaign_1m_10m_mismatch1h_j3.sh
#   DRY_RUN=1 ./scripts/resume_hybrid_campaign_1m_10m_mismatch1h_j3.sh   # status only
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
DRY_RUN="${DRY_RUN:-0}"
TIMEOUT_MISMATCH="${TIMEOUT_MISMATCH:-3600}"

OUT_60="results/eval_60s_hybrid_all54_j3"
OUT_600="results/eval_600s_hybrid_all54_j3"
OUT_MISMATCH="results/eval_3600s_census_mismatch21_j${JOBS}"

commit_results_and_push() {
  local path="$1"
  local msg="$2"
  [[ -d "$path" ]] || { echo "[git] missing results dir: $path" >&2; exit 1; }
  git reset HEAD --quiet 2>/dev/null || true
  echo "[git] add results: ${path}"
  git add -- "$path"
  if git diff --cached --quiet; then
    echo "[git] nothing new to commit for ${path}"
  else
    if ! git commit -m "$(cat <<EOF
${msg}

EOF
)"; then
      echo "[git] WARNING: commit failed for ${path}; continuing" >&2
    fi
  fi
  echo "[git] push ${BRANCH} → ${REMOTE}"
  if ! git push -u "$REMOTE" "HEAD:${BRANCH}"; then
    echo "[git] WARNING: push failed for ${path}; continuing" >&2
  else
    echo "[git] done: committed+pushed ${path}"
  fi
}

print_summary() {
  local summary="$1"
  python - <<PY
import json
from pathlib import Path
p = Path("$summary")
s = json.loads(p.read_text())
n = int(s.get("n") or 0)
exact = float(s.get("exact_accuracy") or 0.0)
soft = float(s.get("soft_accuracy") or 0.0)
print(f"  {p}: n={n} exact={exact:.4f} ({round(exact*n)}/{n}) soft={soft:.4f}")
PY
}

stage_done() {
  local out="$1"
  [[ -f "${out}/${MODE}/summary.json" ]]
}

echo "Resume hybrid campaign on branch=${BRANCH} JOBS=${JOBS} DRY_RUN=${DRY_RUN}"
mem_avail_gi="$(awk '/MemAvailable/ {printf "%.1fGi", $2/1024/1024}' /proc/meminfo)"
echo "Host nproc=$(nproc)  mem_available=${mem_avail_gi}"
if [[ "$(nproc)" -lt "$JOBS" ]]; then
  echo "ALERT: JOBS=${JOBS} > nproc=$(nproc) (oversubscribe). Aborting." >&2
  exit 1
fi

# --- Status report ---
echo
echo "=== Stage status ==="
if stage_done "$OUT_60"; then
  echo "[done] stage1 60s all54 → ${OUT_60}"
  print_summary "${OUT_60}/${MODE}/summary.json"
else
  echo "[todo] stage1 60s all54 → ${OUT_60}"
fi
if stage_done "$OUT_600"; then
  echo "[done] stage2 600s all54 → ${OUT_600}"
  print_summary "${OUT_600}/${MODE}/summary.json"
else
  echo "[todo] stage2 600s all54 → ${OUT_600}"
fi

MISMATCH_MODE_DIR="${OUT_MISMATCH}/${MODE}"
mkdir -p "$MISMATCH_MODE_DIR"

# Enumerate census-mismatch first-3 tasks and which lack result JSON.
PENDING_LIST="$(mktemp)"
DONE_N=0
PENDING_N=0
python - <<PY
import json
import os
from pathlib import Path

from solver.harness import discover, filter_files
from solver.census import census_match

src = Path("$DATASET")
out = Path("$MISMATCH_MODE_DIR")
pending_path = Path("$PENDING_LIST")
files = filter_files(discover(src), trials="$TRIALS", limit=0)
mismatch = []
for f in files:
    data = json.loads(Path(f).read_text())
    if census_match(data["train"]):
        continue
    mismatch.append(Path(f))
assert len(mismatch) == 21, len(mismatch)

done = []
pending = []
for f in mismatch:
    result = out / f"{f.parent.name}_{f.stem}.json"
    if result.is_file():
        try:
            json.loads(result.read_text())
            done.append(f)
            continue
        except Exception:
            pass
    pending.append(f)

pending_path.write_text("\n".join(str(p) for p in pending) + ("\n" if pending else ""))
print(f"[info] mismatch21: done={len(done)} pending={len(pending)} total=21")
print(f"[info] OUT={out.parent}")
for f in done:
    print(f"  DONE  {f.parent.name}/{f.name}")
for f in pending:
    print(f"  TODO  {f.parent.name}/{f.name}")
# expose counts via env file for bash
Path("$PENDING_LIST.counts").write_text(f"{len(done)} {len(pending)}\n")
PY
read -r DONE_N PENDING_N < "${PENDING_LIST}.counts"
rm -f "${PENDING_LIST}.counts"

if stage_done "$OUT_MISMATCH" && [[ "$PENDING_N" -eq 0 ]]; then
  echo "[done] stage3 mismatch21 @${TIMEOUT_MISMATCH}s → ${OUT_MISMATCH}"
  print_summary "${OUT_MISMATCH}/${MODE}/summary.json"
elif [[ "$PENDING_N" -eq 0 ]]; then
  echo "[info] stage3 all 21 result JSONs present; summary missing → will summarize only"
else
  echo "[todo] stage3 mismatch21 @${TIMEOUT_MISMATCH}s → ${OUT_MISMATCH} (${DONE_N}/21 done, ${PENDING_N} to run)"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "DRY_RUN=1 — no eval / commit. Re-run without DRY_RUN to continue."
  rm -f "$PENDING_LIST"
  exit 0
fi

# --- Stage 1 / 2: only if still missing ---
run_full54() {
  local timeout="$1"
  local out="$2"
  export JOBS DELAY DATASET OUT="$out"
  echo "=== full54 ${MODE} timeout=${timeout}s JOBS=${JOBS} OUT=${out} ==="
  ./scripts/run_solver_eval_parallel.sh "$MODE" "$timeout" "$TRIALS"
  local summary="${out}/${MODE}/summary.json"
  [[ -f "$summary" ]] || { echo "missing summary: $summary" >&2; exit 1; }
  print_summary "$summary"
  python - <<PY
import json
from pathlib import Path
s = json.loads(Path("$summary").read_text())
assert int(s.get("n") or 0) == 54, s.get("n")
PY
}

if ! stage_done "$OUT_60"; then
  run_full54 60 "$OUT_60"
  commit_results_and_push "$OUT_60" \
    "eval: hybrid_census all54 @60s JOBS=${JOBS} (${OUT_60})"
else
  # Ensure stage1 tree is pushed if a prior push failed mid-campaign.
  if git status --porcelain -- "$OUT_60" | grep -q .; then
    commit_results_and_push "$OUT_60" \
      "eval: hybrid_census all54 @60s JOBS=${JOBS} (${OUT_60})"
  fi
fi

if ! stage_done "$OUT_600"; then
  run_full54 600 "$OUT_600"
  commit_results_and_push "$OUT_600" \
    "eval: hybrid_census all54 @600s JOBS=${JOBS} (${OUT_600})"
else
  if git status --porcelain -- "$OUT_600" | grep -q .; then
    commit_results_and_push "$OUT_600" \
      "eval: hybrid_census all54 @600s JOBS=${JOBS} (${OUT_600})"
  fi
fi

# Push any already-committed-but-unpushed campaign tip (e.g. power-off after commit).
if [[ -n "$(git rev-list --count "@{u}..HEAD" 2>/dev/null || true)" ]]; then
  ahead="$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)"
  if [[ "${ahead:-0}" -gt 0 ]]; then
    echo "[git] branch is ahead by ${ahead}; pushing ${BRANCH} → ${REMOTE}"
    git push -u "$REMOTE" "HEAD:${BRANCH}" || \
      echo "[git] WARNING: catch-up push failed; continuing" >&2
  fi
fi

# --- Stage 3: resume pending mismatch tasks ---
if stage_done "$OUT_MISMATCH" && [[ "$PENDING_N" -eq 0 ]]; then
  echo "Stage3 already complete; nothing to do."
  rm -f "$PENDING_LIST"
  echo "Compound campaign finished (resume no-op)."
  exit 0
fi

echo "=== census-mismatch21 resume timeout=${TIMEOUT_MISMATCH}s JOBS=${JOBS} OUT=${OUT_MISMATCH} ==="

# Build symlink dataset of all 21 (needed for path layout); only queue pending.
DS_TMP="$(mktemp -d /tmp/census_mismatch_first3_ds.XXXXXX)"
trap 'rm -rf "$DS_TMP"; rm -f "$PENDING_LIST"' EXIT

python - <<PY
import json
import os
from pathlib import Path

from solver.harness import discover, filter_files
from solver.census import census_match

src = Path("$DATASET")
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
print(f"census_mismatch tasks linked: {n}")
assert n == 21, n
PY

# Map pending absolute dataset paths → tmp symlink paths; wipe partial task dirs.
mapfile -t PENDING_SRC < "$PENDING_LIST"
PENDING_TMP=()
for src in "${PENDING_SRC[@]:-}"; do
  [[ -n "$src" ]] || continue
  stem="$(basename "$src")"
  cat="$(basename "$(dirname "$src")")"
  tmp_path="${DS_TMP}/${cat}/${stem}"
  [[ -e "$tmp_path" ]] || { echo "missing tmp link: $tmp_path" >&2; exit 1; }
  PENDING_TMP+=("$tmp_path")
  # Incomplete worker dirs from power-off (encode/popper_* without result JSON).
  task_dir="${MISMATCH_MODE_DIR}/${stem%.json}"
  if [[ -d "$task_dir" ]]; then
    echo "[clean] removing incomplete task dir: $task_dir"
    rm -rf "$task_dir"
  fi
done

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

# Preserve original campaign started_at if present.
python - <<PY
import json
from pathlib import Path
from solver.run_meta import collect_run_meta

out = Path("$MISMATCH_MODE_DIR")
man = out / "run_manifest.json"
prev_started = None
prev_sha = None
if man.exists():
    try:
        prev = json.loads(man.read_text())
        prev_started = prev.get("started_at")
        prev_sha = prev.get("git_sha")
    except Exception:
        pass
meta = collect_run_meta(
    mode="$MODE",
    timeout=int("$TIMEOUT_MISMATCH"),
    jobs=int("$JOBS"),
    trials="$TRIALS",
    dataset="$DS_TMP",
    out="$OUT_MISMATCH",
    extra={
        "entry": "resume_hybrid_campaign_mismatch",
        "phase": "resume",
        "n_pending": int("$PENDING_N"),
        "n_done_before": int("$DONE_N"),
    },
)
if prev_started:
    meta["started_at"] = prev_started
if prev_sha and not meta.get("git_sha"):
    meta["git_sha"] = prev_sha
man.write_text(json.dumps(meta, indent=2))
print(f"Wrote {man} (resume; started_at={meta.get('started_at')})")
PY

if [[ "${#PENDING_TMP[@]}" -gt 0 ]]; then
  echo "Running ${#PENDING_TMP[@]} pending tasks (JOBS=${JOBS})…"
  parallel --jobs "$JOBS" --delay "$DELAY" \
    --joblog "${MISMATCH_MODE_DIR}/parallel.resume.joblog" \
    python -m solver.harness --mode "$MODE" --timeout "$TIMEOUT_MISMATCH" \
      --out "$OUT_MISMATCH" --one {} \
    ::: "${PENDING_TMP[@]}" || true
else
  echo "No pending tasks; summarizing existing results only."
fi

# Summarize all result JSONs (done + newly finished).
python - <<PY
import json
from pathlib import Path
from solver.harness import summarize
from solver.run_meta import collect_run_meta, mark_finished

out = Path("$MISMATCH_MODE_DIR")
rows = []
for p in sorted(out.glob("*.json")):
    if p.name in ("summary.json", "run_manifest.json"):
        continue
    rows.append(json.loads(p.read_text()))
assert len(rows) == 21, f"expected 21 result JSONs, got {len(rows)}"
summary = summarize(rows)
summary["mode"] = "$MODE"
summary["timeout"] = int("$TIMEOUT_MISMATCH")
summary["jobs"] = int("$JOBS")
meta = collect_run_meta(
    mode="$MODE",
    timeout=int("$TIMEOUT_MISMATCH"),
    jobs=int("$JOBS"),
    trials="$TRIALS",
    dataset="$DS_TMP",
    out="$OUT_MISMATCH",
    extra={"entry": "resume_hybrid_campaign_mismatch", "n_tasks": len(rows)},
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
PY

print_summary "${OUT_MISMATCH}/${MODE}/summary.json"

commit_results_and_push "$OUT_MISMATCH" \
  "eval: hybrid_census census-mismatch21 @${TIMEOUT_MISMATCH}s JOBS=${JOBS} (${OUT_MISMATCH})"

echo "Compound campaign finished (resumed)."
echo "  ${OUT_60}/${MODE}/summary.json"
echo "  ${OUT_600}/${MODE}/summary.json"
echo "  ${OUT_MISMATCH}/${MODE}/summary.json"
