# 06 — Running & Reproducing

How to install the solver, solve one task, and run the 54-task evaluation slice.

## 5-minute quick start

```bash
# 1. Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./popper

# 2. Smoke test (solves one denoising task)
./scripts/smoke_solver.sh

# 3. Solve one task and inspect the artifacts
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json --work-dir work/demo

cat work/demo/popper_object/program.pl   # the learned rule
ls work/demo/encode/                     # BK, examples, bias
```

For a walkthrough of what those artifacts mean, see [03 — Tutorial](03-TUTORIAL.md).

---

## Prerequisites

| Tool | Why |
|------|-----|
| Python 3.10+ | Solver package |
| SWI-Prolog | Consults background knowledge and paints blocks (via `janus-swi`) |
| Clingo | Popper’s ASP backend |
| GNU `parallel` | Only needed for parallel eval |

On Ubuntu/Debian: `sudo apt install swi-prolog clingo parallel`

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
python -c "from solver.pipeline import solve; import popper; print('ok')"
```

Most shell scripts auto-activate `.venv` if it exists.

---

## Solve one instance

### CLI

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 \
  --out pred.json \
  --work-dir work/demo
```

| Flag | Default | Meaning |
|------|---------|---------|
| `json_path` | (required) | Path to the task JSON |
| `--timeout` | `600` | Seconds for Popper’s search |
| `--out` | none | Write the result JSON here |
| `--work-dir` | `work/solve` | Where to dump encode/induce artifacts |

### What the result JSON means

| Field | Meaning |
|-------|---------|
| `predicted_grid` | The predicted test output (list of pixel colors) |
| `program` | The learned Prolog rules (empty on failure) |
| `verified_train` | `true` if the program reproduced all training outputs exactly |
| `exact_ok` | `true` if the predicted grid matches gold |
| `soft_accuracy` | Soft cell accuracy (see Evaluation doc) |
| `failure_reason` | `null` on success; otherwise e.g. `popper_timeout`, `paint_verify_failed` |
| `confidence` | `high` when train-verified; `low` on fallback |

On failure, the pipeline still returns a prediction (usually a copy of the test input) so evaluation rows stay comparable. Check `verified_train` and `failure_reason`, not only that a grid exists.

### Inspecting the work directory

After a CLI run with `--work-dir work/demo`:

```
work/demo/
├── encode/
│   ├── bk.pl              # Training background knowledge
│   ├── exs_object.pl      # Positive and negative examples
│   ├── bias_object.pl     # Search grammar
│   ├── test_bk.pl         # Test-example background knowledge
│   ├── test.pl            # Pixel gold for soft scoring (not for learning)
│   └── grids.json         # Pixel grids + block_geometry
├── popper_object/
│   └── program.pl         # The learned rule
└── soft_score/            # Soft-scoring scratch files
```

---

## Smoke tests

```bash
# End-to-end on one denoising task
./scripts/smoke_solver.sh

# Three hand-written fixtures (fill, move, hollow)
TIMEOUT=180 ./scripts/smoke_block_hard.sh

# Unit tests
pytest solver/tests -q
```

---

## Batch evaluation (54-task slice)

The paper comparison uses 18 categories × trials `0,1,2` = **54 tasks**.

### Recommended host settings

On a 4-CPU machine: use `JOBS=2` (leaves headroom for Popper/clingo workers). Do not oversubscribe (`JOBS > nproc`). Stricter apples-to-apples vs Decom’s single-CPU paper setup: `JOBS=1`.

### Parallel eval (preferred)

```bash
JOBS=2 OUT=results/eval_60s \
  ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

| Env / arg | Default | Meaning |
|-----------|---------|---------|
| `JOBS` | `4` | Parallel workers — use `JOBS=2` on a 4-CPU host |
| `OUT` | `results/solver` | Where results land (`$OUT/block_primary/`) |
| `$2` TIMEOUT | `600` | Seconds per task |
| `$3` TRIALS | `0,1,2` | Which instance suffixes to keep |

### Sequential eval

```bash
./scripts/run_solver_eval.sh block_primary 60 0,1,2
```

Quick debug (first 3 files only):

```bash
LIMIT=3 ./scripts/run_solver_eval.sh block_primary 30 0,1,2
```

### Reading results

```
results/<campaign>/block_primary/
├── summary.json              # Aggregate: exact_accuracy, soft_accuracy, n
├── run_manifest.json         # Git SHA, host, timeout, jobs
└── <category>_<stem>.json    # Per-task row
```

Headline scoreboard number: `exact_accuracy * n` (e.g., 40/54).

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
| Popper / clingo failures | Install Clingo; check `pip install -e ./popper` |
| `parallel: command not found` | Install GNU parallel, or use sequential `run_solver_eval.sh` |
| All `paint_verify_failed` | Program returned but paint ≠ train gold — inspect `program.pl` + `bk.pl` |
| `popper_timeout` | Raise `--timeout`; see Method doc for search behavior |
| `popper_exhausted` | Search finished under bias caps with no program — check `failure_detail` |
| CPU thrash in parallel | Keep `JOBS ≤ nproc / 2` on small machines; scripts set `OMP_NUM_THREADS=1` |
| Wrong trial count | Ensure `--trials 0,1,2` and dataset has `*_0.json` … `*_2.json` |

---

## Eval provenance

Every campaign should leave:

| Artifact | Contents |
|----------|----------|
| `run_manifest.json` | Git SHA, branch, host, timeout, jobs, timestamps |
| `summary.json` | Aggregate exact/soft plus `run_meta` |
| Per-task JSON | Slim `run_meta` |

Cite a run as **directory + git SHA + exact n/N**. Index of local campaigns: `results/RUN_REGISTRY.md`.
