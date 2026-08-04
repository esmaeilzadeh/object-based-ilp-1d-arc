# Current method: block-primary object ILP

Living snapshot of **what the code does now**. For the older dual-ladder design
and deltas, see [SOLVER_PLAN.md](SOLVER_PLAN.md). For ILP landscape / BRIL
target, see [ILP-1D-Method.md](ILP-1D-Method.md). Normative do-nots:
[`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).

Code anchors: `solver/pipeline.py`, `solver/encoder.py`, `solver/bias_gen.py`,
`solver/predicates.py`, `solver/decode.py`, `solver/harness.py`.

---

## Claim

Measure whether lifting 1D-ARC from **pixel** to **block** improves results vs
pixel Decom, under one **uniform mechanical** language (same encode / exs / BK /
bias algorithm for every instance). No category-named bias stages, no
marker/reflect answer hacks, no pixel-rescue ladder counted as a block win.

## Pipeline (`block_primary`)

1. **Encode** input grids → lean block BK; train outputs → `out_block` pos/neg.
2. **Bias** → one mechanical `bias_object.pl` from that instance’s BK/exs
   (`render_object_bias_from_bk`).
3. **Induce** → one Popper call with head `out_block/5`.
4. **Verify** → paint-verify all train outputs (exact grid match).
5. **Decode** → query `out_block/5` on test BK → paint pixels → score.

Research / eval default: harness mode `block_primary`
(`include_pixels=False`, `include_blocks=True`, `ladder=False`).

## Head and decode

```text
out_block(Ex, Bid, Off, Len, Color)
```

Paint `Len` cells of `Color` starting at `start(Bid) + Off`, where `start(Bid)`
is the left edge of input run `Bid`. Unpainted cells stay `0`. Overlap / OOB /
ambiguous color fails verify. After apply, dynamic `out_block/5` is retracted /
abolished.

## Lean input BK (`OBJECT_BODY_ALLOWLIST`)

Uniform emit from grids (typed roles `b*` / `s*` / `v*` on block-primary):

| Pred | Role |
|------|------|
| `block/4` | colored run `(Ex, Bid, Len, Color)` |
| `gap/3` | gap size between successive colored objects |
| `obj_succ/3`, `obj_pair/3` | succession / pairing over colored runs |
| `largest/2`, `non_largest/2` | length aggregations (colored) |
| `component_start/2`, `component_len/2` | component anchors |
| `size_even/1`, `size_odd/1` | parity |
| `size_add/3`, `size_sum3/4` | pair/triple arith sugar from observed sizes/gaps |

Not answer-leaking: arith facts close over **observed** lengths/gaps, not
precomputed correct outputs. Dual-ablation inventory may still include
`empty_block`, `obj_index`, paint bridges, etc.; **block_primary does not emit
those**.

## Bias (mechanical, one generator)

- Generator: `render_object_bias_from_bk(bk, exs)` → per-instance bias.
- Body preds / size / value constants = only what appears in that instance’s
  BK/exs (within the allowlist).
- Static `solver/bias/object.pl` is a fallback / tests mirror only.
- **Connectivity guards** (every instance):
  1. Each clause must use `block/4` with head `Bid` (var 1).
  2. `size_add` / `size_sum3` result ∈ head `{Off, Len}` (vars 2 or 3).

No branching on task name or family (`object_mirror`, …).

## Examples (mechanical)

Positives: true output colored runs as `out_block(Ex, Bid, Off, Len, Color)`.
Negatives (same algorithm every instance): wrong color / len / off / bid;
Off=0 identity prefixes; cross-block Len/Color mixes. Same codegen path for all
tasks.

## Accept / score

- Object path: **paint-verify** all train outputs (not soft-only acceptance).
- Test: decode → pixel grid; soft metrics from materialized `out/3` when labels
  exist.

## How to run

```bash
# Research default (object-head only)
python -m solver.harness --mode block_primary --timeout 60 --trials 0,1,2

# Parallel sweep
./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2

# Single instance via harness kwargs (same path as block_primary)
python -c "
from solver.pipeline import solve
r = solve('raw_data/onedarcraw/dataset/1d_recoloring_bmc/1d_recoloring_bmc_0.json',
          timeout=60, include_pixels=False, include_blocks=True, ladder=False)
print(r.level, r.verified_train, r.predicted_grid)
"
```

**CLI note:** `python -m solver.cli` still defaults to the **legacy dual ladder**
(`ladder=True`, pixels+blocks). Document that honestly; evaluate the block lift
with `--mode block_primary`, not the CLI default.

## Ablation modes (still in code)

| Mode | Role |
|------|------|
| `block_primary` | **Research default** — object-head only |
| `pixel_only` | Pixel Decom-style ablation |
| `block_only` | Blocks, no pixels (same object path entry) |
| `dual`, `dual_no_agg`, `dual_no_ladder`, `dual_full` | **Legacy** pixel/dual ladder ablations — not the block-lift claim |

## Explicit non-goals

See the rule file. Purged / refused without separate confirmation:

- Category-staged biases (`object_mirror`, `object_hollow`, …)
- Marker / reflect geometry (`marker_block`, `reflect_pos`, …)
- Answer-leaking BK (`mirrored_out_block`, …) — guarded in tests
- Counting trivials or pixel stages as “block” wins

## Pointers

- Historical / dual-ladder design + checklist → [SOLVER_PLAN.md](SOLVER_PLAN.md)
- ILP comparison + BRIL (library still future) → [ILP-1D-Method.md](ILP-1D-Method.md)
- Package how-to → [solver/README.md](../solver/README.md)
