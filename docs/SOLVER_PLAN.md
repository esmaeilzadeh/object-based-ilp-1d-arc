# Method Plan: A Generic 1D-ARC Solver

> **Preamble (current research default).** This document is the original
> dual-ladder design plus checklist. The **as-built** research path is now
> **block-primary** object ILP only — see
> [CURRENT_METHOD.md](CURRENT_METHOD.md) and
> [`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).
> Dual ladder, trivials, and pixel stages remain in code as **ablations /
> legacy**, not the block-lift claim. Where this plan and CURRENT_METHOD
> disagree, CURRENT_METHOD + the rule win for “what we run.”

Target: a single program that takes one problem instance in the standard ARC JSON
format (3 train input/output pairs + 1 test input) and returns the predicted test
output grid. No per-task configuration, no task-type labels.

Core thesis: 1D-ARC difficulty is *relational*, not combinatorial. The
highest-leverage design choice is the **representation** — describe grids as
**color blocks (objects)**, induce at that level (`out_block`), and decode to
pixels for scoring. Do NOT hand the solver pretrained geometric transformation
rules (mirror, fill, denoise operators); those are learnable. DO hand it
everything ILP cannot invent in reasonable time: segmentation, counting,
aggregation, and arithmetic — emitted by one **uniform mechanical** algorithm.

ILP landscape / BRIL target: [ILP-1D-Method.md](ILP-1D-Method.md).

---

## Stage 0 — Problem framing

The solver is a fixed pipeline, run fresh per instance:

1. **Encode** the 3 train pairs relationally (facts).
2. **Induce** a logic program that maps input facts to output facts, consistent
   with all 3 train pairs.
3. **Verify** the program reproduces all 3 train outputs exactly. Reject otherwise.
4. **Apply** the program to the test input facts.
5. **Decode** the derived output facts back into a grid.

"Generic" means the pipeline, background knowledge (BK), and language bias are
produced by the **same mechanical generators** for every instance (bias body
preds/constants may differ only by what that instance’s grids emit). Learning
happens at solve time (per instance); nothing is trained offline. No switching
on category / task name.

---

## Stage 1 — Representation

### Research default: block layer (`block_primary`)

Deterministic segmentation: **maximal runs of the same color**. On the lean
object path, typed roles (`b*` / `s*` / `v*`) keep block_id / size / value
distinct. Lean BK emit (`OBJECT_BODY_ALLOWLIST`):

- `block(Ex, Id, Len, Color)` — colored runs
- `gap`, `obj_succ`, `obj_pair`
- `largest` / `non_largest`
- `component_start` / `component_len`
- `size_even` / `size_odd`
- `size_add` / `size_sum3` — pair-local arith sugar from observed sizes/gaps

Absolute pixel coordinates are **not** free search constants on this path;
paint position is `start(Bid)+Off` via Python `block_geometry` at decode.

### Dual-ablation inventory (legacy ladder only)

When `include_pixels=True`, encode may also emit the fuller dual inventory:

- Pixel layer: `in`, `empty`, `width`, arithmetic `my_succ` / `lt` / `add`
- Empty runs: `empty_block`; dense ordinal: `obj_index`
- Paint bridges: `in_block` / `in_gap` / `block_edge` / `block_cell` / …
- Anchors: `block_start` / `block_end` / `mid` / `mirror_index` / `from_right`

**block_primary does not emit** that dual inventory. Do not treat dual BK as
required for the block-lift claim.

**Typed number roles** (Popper types — no cross-role arithmetic):

- `value` — color symbols (`v0..v9`)
- `position` — grid ordinals (dual/pixel bias only)
- `size` — cardinals (lengths, offsets)
- `block_id` — run ordinals
- `rank` — ordinals for `len_rank` / `obj_index` (dual)

---

## Stage 2 — Induction targets and decode

### Object head (research default) — **done**

Examples: `pos/neg out_block(Ex, Bid, Off, Len, Color)` from train I/O
(mechanical neg policy: wrong color/len/off/bid, Off=0 prefixes, cross-block
Len/Color mixes). BK is **input-only**.

**Decoder:** query `out_block(E, Bid, Off, Len, Color)`, paint
`[start(Bid)+Off, start(Bid)+Off+Len)` on a zero canvas; fail verify on overlap /
OOB / ambiguous color. Unpainted = 0.

### Pixel head (ablation / legacy ladder)

`pos/neg out(Ex, Pos, Color)` with closed-world decode (background default 0).
Used by `pixel_only` and dual ladder stages — **not** the block-lift default.

---

## Stage 3 — Induction path

### Default: single mechanical object induce

1. Encode lean BK + object exs.
2. `render_object_bias_from_bk` → connectivity-guarded bias.
3. One Popper call (`object_ilp`).
4. Paint-verify trains; decode test.

No category-named stages (`object_mirror`, `object_hollow`, …). No marker /
reflect BK. See the block-level-only rule.

### Legacy dual ladder (ablation only)

Still present in `pipeline.solve` when pixels+ladder are enabled:

1. Trivial closed-form checks (identity, recolor, shift, reverse) — **off-direction**
   for block scores unless explicitly confirmed.
2. Block pixel-head ILP (`block.pl`).
3. Object-head ILP (mechanical bias).
4. Pixel / dual ILP.
5. Fallback identity, low confidence.

Use harness modes `dual*` / `pixel_only` for ablations. Do not report these as
the block-lift method.

---

## Stage 4 — Generalization safeguards

- **Color canonicalization (optional):** map colors to roles per example; invert
  at decode (`dual_full` ablation). Block-primary typically leaves this off.
- **Width independence:** object head binds via Bid/Off relative to input runs,
  not absolute `c*` constants on the lean path.

---

## Stage 5 — Verification-driven acceptance

Object path: accept only if **paint-verify** reproduces every cell of every train
output. Soft metrics may still be reported for harness tables; they do not
override paint-verify acceptance on `block_primary`.

---

## Stage 6 — Evaluation protocol

- Dataset: 1D-ARC, 18 task types × 50 instances (standard JSON).
- Metric: top-1 exact match on the test output grid.
- Baselines: paper’s pixel-only relational decomposition; ARGA.
- **Required columns for the block-lift claim:**
  1. `pixel_only` (Decom-style),
  2. `block_primary` (object-head, mechanical bias),
  3. optional dual\* ablations (legacy portfolio — label as such).
- Report per-task-type solve rates.

Harness: `python -m solver.harness --mode block_primary …` /
`./scripts/run_solver_eval_parallel.sh block_primary …`.

---

## Stage 7 — Extension path

- **Library learning:** promote recurring verified clauses to named BK for later
  instances — still **future**; keep OFF for single-instance comparable runs.
- **Multiple test inputs** per instance: apply the same accepted program to each.
- **2D lift:** runs → components; out of scope for 1D.

Strike from any “needed BK” lists: `marker_block`, `reflect_pos`, family bias
stages, answer-leaking mirrored/shifted out predicates.

---

## Implementation checklist (status)

| Item | Status |
|------|--------|
| JSON → facts encoder (lean object + dual inventory) | Done |
| Mechanical object bias + connectivity guards | Done |
| Head `out_block/5` (Bid, Off, Len, Color) + paint decode | Done |
| Mechanical exs neg policy | Done |
| `block_primary` harness mode | Done |
| Legacy dual ladder (ablation) | Done (not research default) |
| Library learning across tasks | Future |
| Marker / reflect / family bias stages | **Refused** (rule) |

### Object-head checklist detail

- Positives: output colored runs as `out_block(Ex, Bid, Off, Len, Color)`.
- Negatives: wrong color, length, offset, bid; Off=0 identity prefixes;
  cross-block Len/Color mixes.
- Guards: every clause binds head Bid via `block/4`; arith results ∈ {Off, Len}.
- Decode: `start(Bid)+Off`, unpainted = 0.
