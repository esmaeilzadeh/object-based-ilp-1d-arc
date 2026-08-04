# Object-based ILP 1D-ARC Solver

Generic per-instance solver for 1D-ARC JSON problems (3 train I/O pairs + 1 test
input). Research default: **block-primary** object head
`out_block(Ex, Bid, Off, Len, Color)`.

- As-built: [docs/CURRENT_METHOD.md](../docs/CURRENT_METHOD.md)
- Direction: [`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc)
- Historical dual-ladder plan: [docs/SOLVER_PLAN.md](../docs/SOLVER_PLAN.md)

## Input JSON

```json
{
  "train": [{"input": [[...]], "output": [[...]]}, ...],
  "test":  [{"input": [[...]], "output": [[...]]}]
}
```

## Pipeline (`block_primary`)

1. **Encode** input runs → lean BK (`block`, `gap`, `obj_succ`, … per
   `OBJECT_BODY_ALLOWLIST`); train outputs → mechanical `out_block` pos/neg.
2. **Bias** → `render_object_bias_from_bk(bk, exs)` (per-instance; connectivity
   guards on `block` Bid and `size_add` / `size_sum3`).
3. **Induce** → one Popper call, head `out_block/5`.
4. **Verify** → paint-verify all train outputs (`start(Bid)+Off`, length `Len`).
5. **Decode** → paint test on a zero canvas; abolish dynamic `out_block/5`.

`Off` is an offset from the **input block start**, not an absolute grid index.

Static `solver/bias/object.pl` mirrors the lean allowlist for tests/fallback;
production uses the mechanical per-instance file. Tests in
`solver/tests/test_encoder.py` lock the allowlist and reject answer-leaking
preds (`mirrored_out_block`, …).

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./popper

# Research default
python -m solver.harness --mode block_primary --timeout 60 --one path/to.json

# Batch / parallel
./scripts/run_solver_eval.sh block_primary 60 0,1,2
JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

### `pipeline.solve` flags

| Flag | Notes |
|------|--------|
| `include_pixels=False`, `include_blocks=True` | Object path (as in `block_primary`) |
| `ladder` | Dual-ladder only; ignored for pure object path |
| `force_bias="pixel"` | Pixel-only induce |
| `force_bias="object"` | Force object bias path |
| `canonicalize_colors` | Optional role remap (dual_full ablation) |

### Legacy CLI

`python -m solver.cli path.json --timeout 60 --out pred.json` defaults to the
**legacy dual ladder**. Flags: `--no-ladder`, `--canonicalize-colors`,
`--timeout N`, `--work-dir`.

## Harness modes

| Mode | Meaning |
|------|---------|
| `block_primary` | Object-head only — **research default** |
| `pixel_only` | Pixel BK / pixel head |
| `block_only` | Blocks, no pixels |
| `dual`, `dual_no_agg`, `dual_no_ladder`, `dual_full` | Legacy pixel/dual ablations |
