# 02 — Method Plan: Object-only 1D-ARC Solver

**Reading order:** [01 landscape](01-ILP-1D-Method.md) → **you are here (plan)** →
[03 as-built](03-CURRENT_METHOD.md) → [04 vs Decom](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) →
[05 repo map](05-REPO_STRUCTURE.md) → [06 running](06-RUNNING.md).
Full blurbs: root [README](../README.md).

Living method plan for the **object-only** path. As-built snapshot:
[03-CURRENT_METHOD.md](03-CURRENT_METHOD.md). Direction:
[`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).

Target: a single program that takes one ARC JSON instance (3 train I/O + 1 test
input) and returns the predicted test grid. No per-task configuration, no
task-type labels, no pixel-head / dual / trivial induction stages.

Core thesis: 1D-ARC difficulty is *relational*. Lift grids to **color blocks
(objects)**, induce `out_block/5` with Popper, decode to pixels for scoring.
Do **not** hand pretrained geometric transform operators. Do hand what ILP
cannot invent cheaply: segmentation, counting, aggregation, and typed arithmetic
sugar emitted uniformly from the instance.

---

## Stage 0 — Problem framing

Fixed pipeline, fresh per instance:

1. **Encode** train/test grids as lean typed-role block BK + mechanical
   `out_block` exs + per-instance object bias.
2. **Induce** one Popper program with head `out_block/5`.
3. **Paint-verify** on all train outputs; reject otherwise.
4. **Apply** to the test input; **decode** `out_block` → pixel grid.
5. Soft-score from the predicted grid (`out/3` in `test.pl` is scoring only).

"Generic" means one mechanical codegen for `exs` / `bk` / `bias` from that
instance’s grids. Learning is per-instance; nothing is trained offline.
No curriculum / transfer across tasks — same scratch protocol as pixel Decom
(rationale: [01-ILP-1D-Method.md §4](01-ILP-1D-Method.md#why-per-task-from-scratch-not-curriculum--transfer)).

---

## Stage 1 — Block representation

Deterministic segmentation: **maximal runs of the same color**, including
background `0`. All runs share one left→right `block_id` space.

- Colored run (`C ≠ 0`): `block(Ex, Id, Len, Color)`
- Empty run (`C = 0`): `empty_block(Ex, Id, Len)` — not `block(..., 0)`
- Dense nonempty ordinal: `obj_index(Ex, Bid, K)` over colored runs only

Absolute coordinates are not free search constants. They appear only as
**grounded binders** tied to a run id (`block_start` / `block_end`, …).

**Typed number roles** (no cross-role arithmetic):

- `value` — color symbols
- `size` — cardinals (lengths); compare via grounded size preds
- `block_id` — run ordinals
- `rank` — ordinals for `len_rank` / `obj_index`
- `position` — used only where object bias needs grounded binders / sugar

**Grounding policy:** object/geometry/agg facts are finite for the instance.
No recursive object BK. Bias constants come from what appears in that instance’s
BK/exs.

Derived relations (encoding-time, not learned): geometry (`left_of`,
`adjacent`, `gap`, `block_succ`, `obj_succ`, …), length compare, ranking
(`largest`, `smallest`, …), and generic arith sugar (`offset_pos`, `size_add`,
`size_sum3`, …) when emitted uniformly from observed sizes/gaps. `size_add` /
`size_sum3` are bidirectional: legal when any argument binds the head `Off` or
`Len`, so ILP can both *compute* a target size/offset and *check* one against
input geometry (S6, `solver/bias_gen.py`).

---

## Stage 2 — Object induction target and decode

- **Head:** `out_block(Ex, Bid, Off, Len, Color)` — mechanical pos/neg from
  train **output** colored runs (input-anchored).
- **BK:** input-only reframe of the grids.
- **Bias:** one mechanical object bias per instance
  (`render_object_bias_from_bk`); static `solver/bias/object.pl` is
  fallback/tests only.
- **Decode:** paint each `out_block` span on a zero canvas; verify rejects
  overlap / OOB.
- **Scoring:** predicted pixels may be reflected as `out/3` soft facts — not a
  second solver.

---

## Stage 3 — Single induction path

One Popper call (`block_primary` / `object_ilp`). Accept only paint-verified
train programs. On failure: copy test input (`fallback_identity`), empty
program, low confidence — not a trivial closed-form “win.”

No ladder, dual bias stages, pixel-head ILP, or category-named bias switches.

---

## Stage 4 — Generalization safeguards

- **Width / position:** prefer relative / binder facts over naked absolute
  indices so programs can survive width changes.
- **Colors:** learn over values present in the instance; no optional
  color-canonicalization stage in the current path.
- **Uniform language:** bias body preds / constants from that instance’s BK/exs
  only (see block-level-only rule).

---

## Stage 5 — Verification-driven acceptance

Accept only if the program reproduces **every cell of every train output**
under object paint-decode. That is the sole quality gate.

---

## Stage 6 — Evaluation protocol

- Dataset: 1D-ARC JSON under `raw_data/onedarcraw/`.
- Metric: top-1 exact match on the test output grid.
- Baseline: external pixel Decom (not an in-solver mode).
- Report per-category solve rates for `block_primary`.
- Each trial induced **from scratch** (no simple→complex curriculum); see
  [01-ILP-1D-Method.md §4](01-ILP-1D-Method.md#why-per-task-from-scratch-not-curriculum--transfer).
- Ablations that switch to pixel/dual induction are **off-direction** for the
  block-lift claim unless explicitly confirmed.

---

## Stage 7 — Extension path (optional, not required for the claim)

- Cross-task library learning (OFF for comparable single-instance runs).
- Multiple test inputs per JSON.
- 2D lift (connected components) — out of scope for 1D.

---

## Implementation checklist (current code)

1. JSON → lean block facts + mechanical object exs/bias — `solver/encoder.py`,
   `solver/bias_gen.py`
2. Object predicate inventory — `solver/predicates.py` (object path only)
3. Induce / verify / decode — `solver/induce.py`, `verify.py`, `decode.py`
4. Thin orchestration — `solver/pipeline.py` (`solve(instance, timeout, …)`)
5. Harness mode `block_primary` only — `solver/harness.py`
6. Eval scripts default to `block_primary`
