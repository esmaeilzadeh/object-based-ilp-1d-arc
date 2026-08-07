# 03 — Current method (as-built)

**Reading order:** [01](01-ILP-1D-Method.md) → [02](02-SOLVER_PLAN.md) →
**you are here** → [04](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) →
[05](05-REPO_STRUCTURE.md).

Living snapshot of **what the code does now** on the object-only path.

## Claim

Measure whether lifting 1D-ARC to **blocks** (`out_block/5`) improves results vs
pixel Decom under one **uniform mechanical** language. Decode to pixels for
metrics. External Decom remains the pixel baseline (not an in-solver mode).
Each trial is induced from scratch (no curriculum); see
[01-ILP-1D-Method.md §4](01-ILP-1D-Method.md#why-per-task-from-scratch-not-curriculum--transfer).

## Pipeline (`block_primary`)

1. **Encode** lean typed-role block BK + mechanical `out_block` exs + instance
   `bias_object.pl` (`render_object_bias_from_bk`).
2. **Induce** one Popper call, head `out_block/5`, `max_literals=(1+body)×clauses`.
3. **Paint-verify** on train (`verify_object_on_train`).
4. **Decode** test via `apply_object_program` + `block_geometry`.
5. **Soft-score** from predicted grid (`out/3` in `test.pl` is scoring only).

Failures surface `failure_reason` (`popper_timeout`, `popper_exhausted`,
`paint_verify_failed`, …) plus bias caps in `failure_detail`.

## How to run

```bash
python -m solver.harness --mode block_primary --timeout 60 --trials 0,1,2
./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

CLI: `python -m solver.cli path.json --timeout 60` (same object path).

## Non-goals (see block-level-only rule)

- Pixel / dual / trivial induction stages
- Category-named bias stages
- Marker / reflect answer hacks

Method plan → [02-SOLVER_PLAN.md](02-SOLVER_PLAN.md).  
ILP landscape → [01-ILP-1D-Method.md](01-ILP-1D-Method.md).
