# Object-based ILP 1D-ARC Solver

Per-instance object-head solver for 1D-ARC JSON (3 train I/O + 1 test input).
Popper induces `out_block/5`; decode paints pixels for scoring.

Direction: [`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).

**Docs:**

1. [Approach & Landscape](../docs/01-ILP-1D-Method.md) — why blocks vs pixels
2. [Method](../docs/02-SOLVER_PLAN.md) — encode → induce → verify → decode
3. [Tutorial](../docs/03-TUTORIAL.md) — one full example walkthrough
4. [Evaluation](../docs/04-EVALUATION.md) — scoreboard vs pixel Decom
5. [Repository Guide](../docs/05-REPO_STRUCTURE.md) — folder map, where to change what
6. [Running](../docs/06-RUNNING.md) — setup, CLI, eval, troubleshooting

Also: [Decom paper PDF](../docs/2408.12212v3.pdf).

## Pipeline

1. Encode lean typed block BK + mechanical object bias from that instance’s BK/exs.
2. Induce `out_block/5` (one Popper call).
3. Accept only paint-verified train programs.
4. Decode test; soft-score from the predicted grid.

## Run

From the **repo root**, with `.venv` active (`source .venv/bin/activate`).
Only mode: `block_primary`. Full flag tables / troubleshooting →
[docs/06-RUNNING.md](../docs/06-RUNNING.md).

### One instance (CLI)

Writes the full `SolveResult` JSON (and prints it). Use `--work-dir` to keep
encode/induce artifacts (`bk.pl`, `exs.pl`, `bias_object.pl`).

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 \
  --out pred.json \
  --work-dir work/demo
```

| Flag | Default | Meaning |
|------|---------|---------|
| `json_path` | required | Instance JSON |
| `--timeout` | `600` | Popper wall budget (seconds) |
| `--out` | none | Write result JSON here |
| `--work-dir` | `work/solve` | Scratch for encode / induce |

Check `verified_train`, `failure_reason`, and `predicted_grid` in the output.
On induce/verify failure the solver still returns a grid (usually identity copy
of the test input) — do not treat “got a prediction” as success.

### One instance (harness)

Same solver; also writes a scored row under `--out` / `block_primary/`.

```bash
python -m solver.harness --mode block_primary --timeout 60 \
  --out results/solver/smoke \
  --one raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json
```

→ `results/solver/smoke/block_primary/1d_denoising_1c_1d_denoising_1c_0.json`

### Smoke scripts

```bash
./scripts/smoke_solver.sh
# optional: TIMEOUT=120 ./scripts/smoke_solver.sh path/to.json

TIMEOUT=180 ./scripts/smoke_block_hard.sh   # 3 fixtures; exit ≠ 0 if any miss
pytest solver/tests -q
```

### Batch eval (54-task slice = trials `0,1,2`)

```bash
# sequential
./scripts/run_solver_eval.sh block_primary 60 0,1,2

# parallel (needs GNU parallel) — preferred for full runs
JOBS=4 OUT=results/eval_local_120 \
  ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

| Wrapper args | Meaning |
|--------------|---------|
| `$1` mode | `block_primary` only |
| `$2` timeout | seconds per task |
| `$3` trials | e.g. `0,1,2` (filename suffixes) |

Parallel env: `JOBS`, `DELAY`, `OUT`, `DATASET`. Summary:
`$OUT/block_primary/summary.json` (`exact_accuracy`, `per_task_exact`, …).

Quick debug (first 3 files after filter):

```bash
LIMIT=3 ./scripts/run_solver_eval.sh block_primary 30 0,1,2
```

### Stability (optional)

```bash
./scripts/run_stability_protocol.sh b0 120 3 0,1,2
# → results/solver/b0_stability/stability_summary.json
```

## Notes

- Soft `out/3` in `test.pl` is **scoring**, not a pixel solver.
- Static `solver/bias/object.pl` is fallback/tests only; runtime uses per-instance
  `bias_object.pl`.
