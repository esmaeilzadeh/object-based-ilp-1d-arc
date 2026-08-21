# Census-routed hybrid ILP — solver package

Per-instance solver for 1D-ARC JSON (typically 3 train I/O + 1 test input).

**Default mode `hybrid_census`:** a name-free train-grid census routes to object-head
`out_block/5` or pixel-head `out/3`; decode paints pixels for scoring.

**Mode `block_primary`:** object road only (ablation / debug).

Human docs (start at the repo README summaries):

1. [Approach & Landscape](../docs/01-ILP-1D-Method.md)
2. [Method](../docs/02-SOLVER_PLAN.md)
3. [Tutorial](../docs/03-TUTORIAL.md) — flip (object) + pcopy (pixel)
4. [Evaluation](../docs/04-EVALUATION.md) — TBD scoreboard vs Decom
5. [Repository Guide](../docs/05-REPO_STRUCTURE.md)
6. [Running](../docs/06-RUNNING.md)

Also: [Decom paper PDF](../docs/2408.12212v3.pdf).

## Pipeline (hybrid)

1. `census_match` on train bulky/unit run counts (`census.py`).
2. **Match** → encode object BK/exs/bias → induce `out_block/5` → paint-verify → decode.
3. **Mismatch** → encode pixel BK/exs/bias → induce `out/3` → soft-score / apply → pixels.
4. Soft-score / exact vs gold in the harness.

## Run

From the **repo root**, with `.venv` active.

### One instance (CLI)

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
| `json_path` | required | Instance JSON |
| `--mode` | `hybrid_census` | or `block_primary` |
| `--timeout` | `600` | Popper wall budget (seconds) |
| `--out` | none | Write result JSON |
| `--work-dir` | `work/solve` | Scratch for encode / induce |

Check `failure_detail.road`, `level`, `verified_train`, `failure_reason`, and `predicted_grid`.

### One instance (harness)

```bash
python -m solver.harness --mode hybrid_census --timeout 60 \
  --out results/solver/smoke \
  --one raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json
```

→ `results/solver/smoke/hybrid_census/...json`

### Smoke scripts

```bash
./scripts/smoke_solver.sh
TIMEOUT=180 ./scripts/smoke_block_hard.sh
pytest solver/tests -q
```

### Batch eval (54-task slice = trials `0,1,2`)

```bash
./scripts/run_solver_eval.sh hybrid_census 60 0,1,2

JOBS=2 OUT=results/eval_local_600 \
  ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2
```

| Wrapper args | Meaning |
|--------------|---------|
| `$1` mode | `hybrid_census` or `block_primary` |
| `$2` timeout | seconds per task |
| `$3` trials | e.g. `0,1,2` |

Summary: `$OUT/<mode>/summary.json`.

### Stability (optional)

```bash
./scripts/run_stability_protocol.sh b0 120 3 0,1,2
```

## Notes

- Soft `out/3` facts in object-road `test.pl` are for **scoring**, not a second learner.
- Pixel-road learning uses its own `out/3` exs/bias from `pixel_encode.py`.
- Static `solver/bias/object.pl` is fallback/tests only; runtime uses per-instance bias.
