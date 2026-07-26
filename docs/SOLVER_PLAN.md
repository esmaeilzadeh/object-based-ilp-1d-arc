# Method Plan: A Generic 1D-ARC Solver

Target: a single program that takes one problem instance in the standard ARC JSON
format (3 train input/output pairs + 1 test input) and returns the predicted test
output grid. No per-task configuration, no task-type labels.

Core thesis (from prior discussion): 1D-ARC difficulty is *relational*, not
combinatorial. The highest-leverage design choice is the **representation** —
describe grids as **color blocks (objects)** in addition to pixels, and let a
general ILP system (Popper) learn the input→output relation over that
representation. Do NOT hand the solver pretrained geometric transformation rules
(mirror, fill, denoise operators); those are learnable. DO hand it everything ILP
provably cannot invent in reasonable time: segmentation, counting, aggregation,
and arithmetic.

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
identical for every instance. Learning happens at solve time (per instance);
nothing is trained offline.

---

## Stage 1 — Dual-granularity representation (the heart of the method)

Encode every grid at TWO levels simultaneously. The ILP search chooses which
level (or mix) expresses the transformation most compactly.

### Pixel layer (keep from the paper)
- `in(Ex, Pos, Color)` for non-background cells; `empty(Ex, Pos)` for background.
- `width(Ex, W)`.
- Needed because some tasks are genuinely sub-object: single-pixel noise,
  odd/even position recoloring, pattern stamping.

### Block layer (the new core)
Deterministic segmentation: **maximal runs of the same color**, including
background `0`. All runs share one left→right `block_id` space.

- Colored run (`C ≠ 0`): `block(Ex, Id, Len, Color)` + paint bridges
- Empty run (`C = 0`): `empty_block(Ex, Id, Len)` — **not** `block(..., 0)`
  (keeps `0` out of `value` / `largest` / `block_cell`)
- Dense nonempty ordinal: `obj_index(Ex, Bid, K)` with `K = 0,1,2,…` over
  colored runs only (so rules can say “first/second object” without skipping
  empty ids)

`block_len(Ex, Id, Len)` remains a thin alias for colored lengths.
`block_count` = colored count; `empty_block_count` = empty-run count.

Absolute Start/End stay **encoder-internal**. Exposing them in the ILP body
invites position-constant overfitting; geometry is pushed into relations and
bridges instead.

**Typed number roles** (Popper types — no cross-role arithmetic):
- `value` — color symbols (`v0..v9`)
- `position` — grid ordinals (`c*`, `my_succ`/`lt`/`add`; dual/pixel bias only)
- `size` — cardinals (lengths); compare via `shorter`/`longer`/`size_lt`
- `block_id` — run ordinals over all runs (variables only in block bias)
- `rank` — ordinals for `len_rank` and dense `obj_index` (dual may expose `r*`)

**Grounding policy:** all object/geometry/paint priors are finite facts for the
instance. No recursive object BK. Block bias omits `c*`/`s*` constants.

Derived relations (computed during encoding, NOT learned):
- geometry: `left_of`, `adjacent`, `gap`, `touches_edge` over **all** run ids
- length compare: `shorter`, `longer`, `same_len`, `size_lt` (all runs)
- ranking: `largest`, `smallest`, `non_largest`, `block_count`,
  `empty_block_count`, `color_count`, `unique_color`, `len_rank` —
  **colored runs only**
- position anchors: `mid`, `mirror_index`, `from_right` (dual bias)

### Arithmetic / order primitives
Position tables only: `my_succ/2`, `lt/2`, `add/3` (dual/pixel). Cardinal
compares use grounded `size_lt`, not position `lt`.

---

## Stage 2 — Output semantics and the bridge problem

The learned program's head stays pixel-level: `out(Ex, Pos, Color)`. This keeps
one uniform target for every task. Block→pixel painting uses **precomputed
bridges** (Start/End never appear as free body vars):

- `pixel_block(Ex, Pos, Bid)` — Pos-first membership for **any** run (colored or empty)
- `in_block(Ex, Id, Pos)` / `block_edge` / `in_gap` (`in_block`/`block_edge` colored only)
- `block_cell` / `edge_cell` / `interior_cell` / `solid_cell` — paint bridges
  (`solid_cell` = full non-largest **colored** blocks; use with `edge_cell`+`largest` for hollow)
- `gap_cell(Ex, Id1, Id2, Pos, Color)` — gap filled with **shorter** endpoint color;
  only when **both** endpoints are colored

Decode rule: a test cell is background unless some rule derives a color for it.
If two rules derive different colors for one cell, the program fails verification
on trains (exact match), so ambiguity is filtered out in Stage 3 rather than
resolved by heuristics.

---

## Stage 3 — Induction with a staged portfolio (anytime, cheap-first)

Do not throw every instance straight into full ILP. Run a fixed escalation
ladder; stop at the first level whose program passes exact verification on all 3
train pairs:

1. **Trivial checks** (constant-time): identity, global recolor (bijective color
   map), uniform shift by k, reversal. These are closed-form testable — no search.
2. **Block-level ILP** (small search space): bias exposes only block facts,
   derived relations, and bridges. Most move/fill/hollow/recolor tasks should
   resolve here with 1–3 short clauses.
3. **Full dual ILP**: pixel + block predicates together, larger clause budget.
   Catches sub-object tasks and mixed-granularity tasks.
4. **Fallback**: if nothing verifies within the time budget, emit the best
   partial program's prediction (or identity) and flag low confidence.

Rationale: the ladder preserves generality (every level is domain-generic) while
spending the timeout where the representation insight says it pays off.

---

## Stage 4 — Generalization safeguards

Two normalizations make learned programs transfer from train pairs to the test
input even when surface features differ:

- **Color canonicalization (optional, applied symmetrically):** map colors to
  roles per example (background, majority color, minority/noise color, unique
  color) and learn over roles; invert the mapping at decode. Handles instances
  where the test grid uses different colors than the trains.
- **Width independence:** never rely on absolute positions alone; BK's
  `from_right`, `mid`, `mirror_index` express positions relative to the grid, so
  programs survive width changes between train and test.

Both are representation-level, not learned — consistent with the thesis.

---

## Stage 5 — Verification-driven acceptance

A candidate program is accepted only if it reproduces **every cell of every
train output exactly** (no FP, no FN under the closed-world decode). This is the
solver's only quality gate and is what makes the pipeline trustworthy without
confidence models. Popper's own coverage testing already provides this; the plan
just makes it the hard acceptance criterion at every ladder level.

---

## Stage 6 — Evaluation protocol

- Dataset: 1D-ARC, 18 task types × 50 instances (standard JSON).
- Metric: top-1 exact match on the test output grid (same as the paper and ARGA).
- Baselines to beat/report: paper's pixel-only relational decomposition
  (59/63/69% at 1/10/60 min) and ARGA (94%).
- Required ablations (these validate the thesis):
  1. pixel-only BK (paper reproduction),
  2. block-only BK,
  3. dual BK (full method),
  4. dual BK minus derived aggregations (shows counting must be precomputed),
  5. ladder off (straight to full ILP) — shows the portfolio's time value.
- Report per-task-type solve rates, not just the aggregate, to see which
  representational level each concept needs.

---

## Stage 7 — Extension path (after the above works)

- **Library learning:** promote recurring learned clauses (e.g. "fill between
  markers") to named BK predicates for later instances — turns the per-instance
  solver into an improving one. Keep this OFF for benchmark comparability runs.
- **Multiple test inputs** per instance (some ARC JSONs have >1): apply the same
  accepted program to each.
- **2D lift:** the whole design carries over by replacing runs with connected
  components and adding row/column anchors; segmentation ambiguity becomes the
  new hard problem (out of scope for 1D).

---

## What a detailed implementation plan must specify (checklist for the next model)

1. JSON → facts encoder (both layers + derived relations), and the exact
   predicate/type inventory.
2. Bias files per ladder level (which predicates are exposed at level 2 vs 3),
   clause/variable budgets, example-id threading constraints.
3. Bridge predicate definitions (`span`, shifted spans) as Prolog/ASP BK.
4. The trivial-check implementations (level 1) and their verification.
5. Popper invocation per level with per-level timeouts summing to the global
   budget (suggest 10–20% / 40% / 40–50%).
6. Decoder + exact-match verifier shared by all levels.
7. Color canonicalization mapping and its inverse.
8. Harness: run over the 900 instances, produce the ablation table.
