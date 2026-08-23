# 06 — Running & Reproducing

How to install the census-routed hybrid solver, solve one task, and run the 54-task evaluation slice.

## 5-minute quick start

```bash
# 1. Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./popper

# 2. Smoke test (harness, hybrid_census)
./scripts/smoke_solver.sh

# 3. Solve one task and inspect artifacts
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json \
  --mode hybrid_census --timeout 60 \
  --out pred.json --work-dir work/demo

cat pred.json | head
ls work/demo/
```

For walkthroughs of object vs pixel roads, see [03 — Tutorial](03-TUTORIAL.md).

---

## Prerequisites

| Tool | Why |
|------|-----|
| Python 3.10+ | Solver package |
| SWI-Prolog | Consults BK and paints / applies programs (via `janus-swi`) |
| Clingo | Popper’s ASP backend; also used in pixel encode helpers |
| GNU `parallel` | Only needed for parallel eval |

On Ubuntu 24.04 Cloud images the distro `swi-prolog` package is often too old for `janus-swi`. Prefer the SWI PPA (≥ 9.1.12). See `.cursor/environment.json` for the Cloud Agent install script sketch:

```bash
sudo apt-get install -y python3.12-venv python3-dev build-essential parallel gringo
sudo add-apt-repository -y ppa:swi-prolog/stable
sudo apt-get update && sudo apt-get install -y swi-prolog
```

`gringo` provides `/usr/bin/clingo`.

---

## Setup

```bash
cd /path/to/object-based-ilp-1d-arc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./popper
```

Confirm:

```bash
python -c "from solver.pipeline import solve, solve_hybrid; import popper; print('ok')"
```

Most shell scripts auto-activate `.venv` if it exists.

---

## Solve one instance (CLI)

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json \
  --mode hybrid_census \
  --timeout 60 \
  --out pred.json \
  --work-dir work/demo
```

| Flag | Default | Meaning |
|------|---------|---------|
| `json_path` | (required) | Path to the task JSON |
| `--mode` | `hybrid_census` | `hybrid_census` (census route) or `block_primary` (object only) |
| `--timeout` | `600` | Seconds for Popper’s search |
| `--out` | none | Write the result JSON here |
| `--work-dir` | `work/solve` | Encode / induce scratch tree |

### What the result JSON means

| Field | Meaning |
|-------|---------|
| `predicted_grid` | Predicted test output (list of pixel colors) |
| `program` | Learned Prolog rules (empty on hard failure) |
| `level` | e.g. `object_ilp`, `pixel_ilp`, `fallback_identity` |
| `verified_train` | Object road: paint-verify passed. Pixel road: interpret with soft matrix |
| `exact_ok` | (harness) predicted grid matches gold |
| `soft_accuracy` / `soft_matrix` | Per-label soft: `[TP,FN,TN,FP]` over `pos`/`neg` `out` atoms (`per_label_out_v1`) |
| `failure_reason` | `null` on clean success paths; else timeout / exhausted / verify / decode … |
| `failure_detail.census_match` | Whether the train census matched |
| `failure_detail.road` | `object` or `pixel` under hybrid |
| `confidence` | `high` when train-verified on object path; `low` on fallback |

On failure the pipeline still returns a prediction (usually a copy of the test input) so evaluation rows stay comparable. Check `level`, `failure_reason`, and `road`—not only that a grid exists.

### Work directories

**Object road** (typical when `census_match=true`):

```
work/demo/
├── encode/
│   ├── bk.pl
│   ├── exs_object.pl
│   ├── bias_object.pl
│   ├── test_bk.pl
│   ├── test.pl
│   └── grids.json
├── popper_object/
│   └── program.pl
└── soft_score/
```

**Pixel road** (typical when `census_match=false`):

```
work/demo/
├── encode/            # pixel bk / exs / bias from pixel_encode.py
├── popper_pixel/
│   └── program.pl
└── soft_score/
```

Open the directory after the run; filenames follow the encoder that actually ran.

---

## Smoke tests

```bash
./scripts/smoke_solver.sh
# optional: TIMEOUT=120 ./scripts/smoke_solver.sh path/to.json

TIMEOUT=180 ./scripts/smoke_block_hard.sh
pytest solver/tests -q
```

---

## Batch evaluation (54-task slice)

The comparison slice is 18 categories × trials `0,1,2` = **54 tasks**.

### Recommended host settings

On a 4-CPU machine: use `JOBS=2` (leave headroom for Popper/clingo workers). Do not oversubscribe (`JOBS > nproc`). Stricter apples-to-apples vs Decom’s single-CPU paper setup: `JOBS=1`.

### Parallel eval (preferred)

```bash
JOBS=2 OUT=results/eval_hybrid_600s \
  ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2
```

| Env / arg | Default | Meaning |
|-----------|---------|---------|
| `JOBS` | `4` | Parallel workers — use `JOBS=2` on a 4-CPU host |
| `OUT` | `results/solver` | Results land under `$OUT/<mode>/` |
| `$1` MODE | (required) | `hybrid_census` or `block_primary` |
| `$2` TIMEOUT | `600` | Seconds per task |
| `$3` TRIALS | `0,1,2` | Instance suffixes to keep |

Object-only control:

```bash
JOBS=2 OUT=results/eval_block_only_600s \
  ./scripts/run_solver_eval_parallel.sh block_primary 600 0,1,2
```

### Sequential eval

```bash
./scripts/run_solver_eval.sh hybrid_census 60 0,1,2
```

Quick debug (first 3 files only):

```bash
LIMIT=3 ./scripts/run_solver_eval.sh hybrid_census 30 0,1,2
```

### Reading results

```
results/<campaign>/hybrid_census/
├── summary.json              # exact_accuracy, soft_accuracy, n, run_meta
├── run_manifest.json         # Git SHA, host, timeout, jobs
└── <category>_<stem>.json    # Per-task row
```

Headline scoreboard: see [04 — Evaluation](04-EVALUATION.md) (e.g. 44/54 @600 s, 45/54 @3600 s with noted `scale_dp_0` interim).

---

## Stability protocol

Repeat a full eval **R** times at `JOBS=1` to measure flaky exact counts:

```bash
./scripts/run_stability_protocol.sh b0 120 3 0,1,2
```

Results land under `results/solver/b0_stability/` with a final `stability_summary.json`.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|-------------------|
| `janus` / Prolog errors | Install SWI-Prolog; reinstall `janus-swi` in the venv |
| Popper / clingo failures | Install Clingo; `pip install -e ./popper` |
| `parallel: command not found` | Install GNU parallel, or use sequential `run_solver_eval.sh` |
| Unexpected `road` | Inspect train bulky/unit counts; census is geometry-only |
| `paint_verify_failed` | Object road: program does not paint train gold — inspect `program.pl` + `bk.pl` |
| Pixel path soft-fail | Check `soft_matrix`, `decom_solved`, `popper_pixel/program.pl` |
| `popper_timeout` | Raise `--timeout` |
| `popper_exhausted` | Search finished under bias caps with no program |
| CPU thrash in parallel | Keep `JOBS ≤ nproc / 2` on small machines |
| Wrong trial count | Ensure `--trials 0,1,2` and dataset has `*_0.json` … `*_2.json` |

---

## Eval provenance

Every campaign should leave:

| Artifact | Contents |
|----------|----------|
| `run_manifest.json` | Git SHA, branch, host, timeout, jobs, timestamps |
| `summary.json` | Aggregate exact/soft plus `run_meta` |
| Per-task JSON | Slim `run_meta` + `failure_detail` |

Cite a run as **directory + git SHA + exact n/N**. Index of local campaigns: `results/RUN_REGISTRY.md`.
