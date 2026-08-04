# Object-based ILP 1D-ARC Solver

Per-instance object-head solver for 1D-ARC JSON (3 train I/O + 1 test input).
Popper induces `out_block/5`; decode paints pixels for scoring.

Direction: [`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).  
As-built: [docs/CURRENT_METHOD.md](../docs/CURRENT_METHOD.md).

## Pipeline

1. Encode lean typed block BK + mechanical object bias from that instance’s BK/exs.
2. Induce `out_block/5` (one Popper call).
3. Accept only paint-verified train programs.
4. Decode test; soft-score from the predicted grid.

## Run

```bash
python -m solver.cli path/to.json --timeout 60 --out pred.json
python -m solver.harness --mode block_primary --timeout 60 --one path/to.json
./scripts/run_solver_eval.sh block_primary 60 0,1,2
```

Only harness mode: `block_primary`.

## Notes

- Soft `out/3` in `test.pl` is **scoring**, not a pixel solver.
- Static `solver/bias/object.pl` is fallback/tests only; runtime uses per-instance
  `bias_object.pl`.
