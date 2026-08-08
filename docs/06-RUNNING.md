# 06 — Running the solver (setup, CLI, scripts, eval)

**Reading order:** [01 landscape](01-ILP-1D-Method.md) → [02 plan](02-SOLVER_PLAN.md) →
[03 as-built](03-CURRENT_METHOD.md) → [04 vs Decom](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) →
[05 repo map](05-REPO_STRUCTURE.md) → **you are here (running)**.
Full blurbs: root [README](../README.md).

How to install, smoke-test, solve one JSON, and run the 54-task eval slice.
Method claim → [03-CURRENT_METHOD.md](03-CURRENT_METHOD.md). Folder map →
[05-REPO_STRUCTURE.md](05-REPO_STRUCTURE.md).

**Sole mode:** `block_primary` (object-head `out_block/5`). No pixel/dual modes.

---

## 1. Prerequisites

| Tool | Why |
|------|-----|
| Python 3.10+ | Solver package |
| SWI-Prolog | `janus-swi` (BK consult / paint decode) |
| Clingo | Popper’s ASP backend |
| GNU `parallel` | Only for `run_solver_eval_parallel.sh` |

On Ubuntu/Debian, typical packages: `swi-prolog`, `clingo`, `parallel`.

---

## 2. One-time setup

From the repo root:

```bash
cd /path/to/object-based-ilp-1d-arc

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e ./popper
```

Confirm imports:

```bash
python -c "from solver.pipeline import solve; import popper; print('ok')"
```

Most shell scripts auto-`source .venv/bin/activate` if `.venv` exists.

---

## 3. Dataset layout

Default root: `raw_data/onedarcraw/dataset/`.

```text
raw_data/onedarcraw/dataset/
├── 1d_denoising_1c/1d_denoising_1c_0.json
├── 1d_flip/1d_flip_0.json …
└── …
```

Each JSON is one ARC-style trial: `train` (usually 3 I/O pairs) + `test`
(input; gold output used only for scoring).

**Paper / Decom comparison slice:** 18 categories × trials `0,1,2` = **54 tasks**.
Trial filter is by filename suffix (`_0`, `_1`, `_2`), not by re-running the same file.

---

## 4. Solve one instance

### 4.1 CLI (`python -m solver.cli`)

```bash
source .venv/bin/activate

python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 \
  --out pred.json
```

| Flag | Default | Meaning |
|------|---------|---------|
| `json_path` | (required) | Instance JSON |
| `--timeout` | `600` | Wall budget for Popper (seconds) |
| `--out` | none | Write full `SolveResult` JSON here (also printed) |
| `--work-dir` | `work/solve` | Encode / induce scratch (`bk.pl`, `exs.pl`, `bias_object.pl`, …) |

Example with explicit work dir:

```bash
python -m solver.cli tests/fixtures/hollow_largest_keep_rest.json \
  --timeout 180 \
  --work-dir work/hollow_demo \
  --out work/hollow_demo/pred.json
```

### 4.2 What the JSON result means

Important fields in CLI / harness rows:

| Field | Meaning |
|-------|---------|
| `predicted_grid` | 1D list of pixel colors for the test input |
| `program` | Induced Prolog (`out_block/5` clauses), or empty on fallback |
| `verified_train` | `true` iff paint-verify passed on all train outputs |
| `exact_ok` / `ok` | (harness) predicted grid equals gold test output |
| `soft_accuracy` | Cell soft score (on this path, failures often match exact via identity fallback) |
| `failure_reason` | `null` on accept; else e.g. `popper_timeout`, `popper_exhausted`, `paint_verify_failed`, `popper_error` |
| `failure_detail` | Bias caps, induce elapsed, Popper status, … |
| `confidence` | `high` when train-verified; `low` on fallback |
| `level` | Internal label of which path produced the prediction |

On induce/verify failure the pipeline still returns a prediction (usually **identity**:
copy test input) so harness rows stay comparable — check `verified_train` and
`failure_reason`, not only that a grid exists.

### 4.3 Harness one-shot

Same solver, writes under `results/…/block_primary/`:

```bash
python -m solver.harness --mode block_primary --timeout 60 \
  --out results/solver/smoke \
  --one raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json
```

Output file name pattern:
`{out}/{mode}/{category}_{stem}.json`
e.g. `results/solver/smoke/block_primary/1d_denoising_1c_1d_denoising_1c_0.json`.

---

## 5. Smoke scripts

### 5.1 `scripts/smoke_solver.sh`

Creates `.venv` if missing, installs deps + editable Popper, runs harness `--one`
on a default denoising instance.

```bash
./scripts/smoke_solver.sh
# optional: path + timeout
TIMEOUT=120 ./scripts/smoke_solver.sh \
  raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json
```

| Env / arg | Default | Meaning |
|-----------|---------|---------|
| `$1` | `…/1d_denoising_1c_0.json` | JSON path |
| `TIMEOUT` | `90` | Popper timeout |

Writes under `results/solver/smoke/block_primary/`.

### 5.2 `scripts/smoke_block_hard.sh`

Runs three **fixtures** via CLI and checks exact match against gold test output:

- `tests/fixtures/fill_gap_with_shorter.json`
- `tests/fixtures/move_left_block_past_pivot.json`
- `tests/fixtures/hollow_largest_keep_rest.json`

```bash
TIMEOUT=180 ./scripts/smoke_block_hard.sh
```

Artifacts: `work/block_hard/<name>/pred.json` (+ encode work dirs).  
Exit status non-zero if any fixture mismatches. Exit message: `RESULT: pass=N fail=M`.

### 5.3 Unit tests

```bash
source .venv/bin/activate
pytest solver/tests -q
```

---

## 6. Batch eval (54-task slice)

### 6.1 Sequential — `scripts/run_solver_eval.sh`

Thin wrapper around `python -m solver.harness` (one process, all files in order).

```bash
./scripts/run_solver_eval.sh block_primary 60 0,1,2
```

| Positional | Default | Meaning |
|------------|---------|---------|
| `$1` MODE | `block_primary` | Only supported mode |
| `$2` TIMEOUT | `60` | Seconds per task |
| `$3` TRIALS | `0,1,2` | Filename suffixes to keep |

| Env | Default | Meaning |
|-----|---------|---------|
| `LIMIT` | `0` | If non-zero, pass `--limit N` (first N files after trial filter) |

Quick debug (3 files only):

```bash
LIMIT=3 ./scripts/run_solver_eval.sh block_primary 30 0,1,2
```

Default out dir: `results/solver/block_primary/` (+ `summary.json` at the end).

### 6.2 Parallel — `scripts/run_solver_eval_parallel.sh` (preferred for full runs)

Requires GNU `parallel`. Spawns one harness `--one` per JSON, then aggregates
`summary.json`.

```bash
JOBS=4 OUT=results/eval_demo \
  ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

| Positional | Default | Meaning |
|------------|---------|---------|
| `$1` MODE | `block_primary` | Mode |
| `$2` TIMEOUT | `600` | Seconds per task |
| `$3` TRIALS | `0,1,2` | Trial filter |

| Env | Default | Meaning |
|-----|---------|---------|
| `JOBS` | `4` | Parallel workers |
| `DELAY` | `5` | Seconds between job starts (breathing room) |
| `OUT` | `results/solver` | Root; results land in `$OUT/$MODE/` |
| `DATASET` | `raw_data/onedarcraw/dataset` | Discover root |
| `OMP_NUM_THREADS` etc. | `1` | Avoid BLAS oversubscription |

Also writes `$OUT/$MODE/parallel.joblog`.

**Example — matched Decom-style 60s campaign:**

```bash
JOBS=4 OUT=results/eval_s6_60s \
  ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

**Example — longer budget:**

```bash
JOBS=4 OUT=results/eval_s6_120s \
  ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

### 6.3 Direct harness (no shell wrapper)

```bash
python -m solver.harness \
  --mode block_primary \
  --timeout 60 \
  --trials 0,1,2 \
  --dataset raw_data/onedarcraw/dataset \
  --out results/solver
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--dataset` | `raw_data/onedarcraw/dataset` | Category folders of JSON |
| `--mode` | `block_primary` | Only choice |
| `--timeout` | `60` | Per instance |
| `--trials` | `""` (all) | e.g. `0,1,2` |
| `--limit` | `0` (all) | Cap after filter |
| `--out` | `results/solver` | Parent of `$mode/` |
| `--one` | unset | Single file (parallel worker path) |

---

## 7. Stability protocol

`scripts/run_stability_protocol.sh` repeats a full parallel eval **R** times at
`JOBS=1` to measure flaky exact counts.

```bash
./scripts/run_stability_protocol.sh b0 120 3 0,1,2
```

| Positional | Default | Meaning |
|------------|---------|---------|
| `$1` TAG | `b0` | Label under `results/solver/${TAG}_stability/` |
| `$2` TIMEOUT | `120` | Per task |
| `$3` R | `3` | Number of repeats |
| `$4` TRIALS | `0,1,2` | Trial filter |

Each repeat: `results/solver/${TAG}_stability/r{i}/block_primary/…`  
Final aggregate: `…/stability_summary.json` with `exact_per_repeat`,
`stable_pass` / `stable_fail` / `flaky`, and `failure_reason_hist`.

---

## 8. Reading results

### Per-task row (harness)

```text
results/<OUT>/<mode>/<category>_<stem>.json
```

Use `exact_ok`, `failure_reason`, `elapsed`, `program`.

### Campaign summary

After sequential or parallel eval:

```text
results/<OUT>/<mode>/summary.json
```

Fields include `n`, `exact_accuracy`, `soft_accuracy`, `per_task_exact`,
`per_task_soft`. Headline scoreboard number is usually **`exact_accuracy * n`**
exact solves out of `n` (e.g. 39/54).

### Work / encode dumps

CLI `--work-dir` or harness `…/<stem>/` under the mode out dir holds Popper
inputs (`bk.pl`, `exs.pl`, `bias_object.pl`) useful for debugging a single fail.

---

## 9. Suggested first-time path

```bash
# 1. Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./popper

# 2. Fast smoke
./scripts/smoke_solver.sh

# 3. One CLI solve you can inspect
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json --work-dir work/demo
less pred.json
ls work/demo/encode

# 4. Unit tests
pytest solver/tests -q

# 5. Tiny eval (optional)
LIMIT=3 ./scripts/run_solver_eval.sh block_primary 30 0

# 6. Full 54 @ 120s (needs GNU parallel; long-running)
JOBS=4 OUT=results/eval_local_120 \
  ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---------|-------------------|
| `janus` / Prolog errors | Install SWI-Prolog; reinstall `janus-swi` in the venv |
| Popper / clingo failures | Install Clingo; check `pip install -e ./popper` |
| `parallel: command not found` | Install GNU parallel, or use `run_solver_eval.sh` (sequential) |
| All `paint_verify_failed` | Program returned but closed-world paint ≠ train gold — inspect `program` + work-dir BK |
| `popper_timeout` | Raise `--timeout` / script timeout; see [03](03-CURRENT_METHOD.md) |
| `popper_exhausted` | Search finished under bias caps with no program — see `failure_detail` |
| BLAS/CPU thrash in parallel | Scripts set `OMP_NUM_THREADS=1`; keep `JOBS` modest (e.g. 4) |
| Wrong trial count | Ensure `--trials 0,1,2` and dataset has `*_0.json`…`*_2.json` per category |

Direction constraints (no pixel rescue modes, etc.):
[`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).
