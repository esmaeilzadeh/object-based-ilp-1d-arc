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
Deterministic segmentation: a block is a **maximal run of same-colored,
non-background cells**. This is preprocessing, not learning — it is the "object
prior" made explicit.

Facts per block:
- `block(Ex, Id, Start, End, Color)`

Derived relations (computed during encoding, NOT learned — these are the
aggregations ILP cannot invent under timeout):
- geometry: `block_len(Ex,Id,L)`, `left_of(Ex,Id1,Id2)`, `adjacent(Ex,Id1,Id2)`,
  `gap(Ex,Id1,Id2,G)`, `touches_edge(Ex,Id,left|right)`
- ranking/aggregation: `largest(Ex,Id)`, `smallest(Ex,Id)`, `block_count(Ex,N)`,
  `color_count(Ex,Color,N)`, `unique_color(Ex,Color)`, `len_rank(Ex,Id,K)`
- position anchors: `mid(Ex,M)`, `mirror_index(Ex,I,J)` (I+J = W-1),
  `from_right(Ex,Pos,Offset)`

### Arithmetic / order primitives (unchanged from paper)
`my_succ/2`, `lt/2`, `add/3`, small-integer and color constants, plus type
declarations and the example-id threading constraint (every body literal about a
grid must use the head's example variable — prevents mixing examples).

---

## Stage 2 — Output semantics and the bridge problem

The learned program's head stays pixel-level: `out(Ex, Pos, Color)`. This keeps
one uniform target for every task. But block-level reasoning must be able to
*produce* pixel outputs cheaply, so BK provides bridge predicates, e.g.:

- `span(Start, End, Pos)` — Pos lies in [Start, End]; lets one rule paint a whole
  block: `out(E,P,C) :- block(E,B,S,T,_), span(S,T,P), ...`
- shifted/scaled spans: `span_shift(S,T,K,Pos)` for "block moved by K".

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
