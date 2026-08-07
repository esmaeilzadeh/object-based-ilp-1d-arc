# 01 — ILP Method for Generic 1D-ARC

**Reading order:** start here → [02](02-SOLVER_PLAN.md) → [03](03-CURRENT_METHOD.md) →
[04](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) → [05](05-REPO_STRUCTURE.md).

Landscape note + how this repo’s **object-only** path sits among ILP work.
As-built: [03-CURRENT_METHOD.md](03-CURRENT_METHOD.md). Method plan:
[02-SOLVER_PLAN.md](02-SOLVER_PLAN.md). Direction:
[`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).

Scope: **ILP-only lineage** (no LLM program search, no pure neural TTT).

---

## 1. What recent ILP work actually did

### A. Relational Decomposition + Popper (Hocquette & Cropper, IJCAI 2025)
- **Idea:** Decompose I/O into facts; learn `out(...)` from `in(...)` with
  off-the-shelf Popper.
- **1D-ARC BK:** pixels + `empty` + arithmetic; deliberately **no** object
  operators.
- **Result:** ~59/63/69% at 1/10/60 min on 1D-ARC (vs ARGA ~94% with object DSL).
- **Strengths:** Domain-light; interpretable; exact few-shot induction.
- **Weaknesses:** Pixel BK forces long clauses; weak on objects/counting; no
  cross-task library.

### B. ILPAR — ILP over object DSL (Rocha et al., 2024/2025)
- **Idea:** Sequence of ILP tasks that **generate output objects** into an empty
  grid, using a hand-designed object-centric DSL as BK.
- **Strengths:** Objects-first; FOL fits relations; criticizes pixel-Popper as
  limiting.
- **Weaknesses:** Fixed DSL prior; not a full 1D-ARC (900) competitor; risk of
  developer-aware generalization.

### C. Adjacent symbolic baselines
- **ARGA:** Graph objects + DSL search — ~94% on 1D-ARC (not ILP).
- **Undecomposed ILP baselines:** ~0% — representation is the bottleneck.

### D. This repo (object-only / `block_primary`)
- **Idea:** Per-instance Popper; **block** facts only for induction; head
  `out_block/5`; mechanical object bias from the instance; paint-verify; decode
  to pixels for metrics.
- **Strengths vs A:** Objects + aggregations without leaving ILP.
- **Strengths vs B:** Learned relations over blocks; no hand transform operators;
  full-benchmark harness.
- **Limits:** No cross-task library yet; single segmentation prior (maximal
  same-color runs); no pixel-head rescue (by design — see block-level-only).

```mermaid
flowchart LR
  pixelPopper[Pixel Popper Decomp] -->|"+blocks +agg"| objectOnly[Object-only out_block]
  ilpar[ILPAR object DSL ILP] -->|"less hand DSL more learned relations"| objectOnly
  objectOnly -->|"optional later: library"| library[Library refinement]
```

---

## 2. Strength / weakness matrix (ILP line)

| Method | Representation | What ILP learns | Prior in BK | Main gap |
|--------|----------------|-----------------|-------------|----------|
| Pixel relational decomp | pixels | `out` pixel rules | arithmetic | no objects/count |
| ILPAR | objects + DSL | object-generating LPs | rich object DSL | DSL completeness; scale |
| This repo | blocks + aggs | `out_block/5` | segmentation + aggs (no transform ops) | no library; hard sub-object tasks stay hard |

External pixel Decom is the baseline to beat for the **block lift** claim — not
an in-solver mode.

---

## 3. Current method (object-only)

**Claim:** Measure whether lifting to blocks improves results vs pixel Decom
under one uniform mechanical language.

1. **Encode** lean typed-role block BK + mechanical `out_block` exs + instance
   object bias.
2. **Induce** one Popper call, head `out_block/5`.
3. **Paint-verify** train; **decode** test; soft-score pixels.

Forbidden for the claim (unless explicit confirmation): pixel/dual ladders,
trivial closed-forms reported as block wins, category-named bias stages,
marker/reflect answer hacks.

Optional later (not required for the claim): cross-task library refinement
(OFF for comparable single-instance runs).

---

## 4. Evaluation

On 1D-ARC categories / trials via harness `block_primary`:

- vs external pixel Decom
- per-type exact rates
- failures via `failure_reason` / `failure_detail`

Success for the block-lift question: honest object-only numbers, not scores
inflated by pixel induction.

### Why per-task from scratch (not curriculum / transfer)

Both this repo and pixel Decom treat each JSON trial as an independent
**few-shot program synthesis** problem: induce from that trial’s train pairs,
then score the held-out test. There is no shared training set across
categories, and no warm-start from an “easier” sibling task.

That is deliberate:

1. **ARC-style claim.** The target is inventing a program for a *novel*
   transform from a tiny support set — not accumulating a curriculum of known
   transforms. Simple→complex transfer answers a different question
   (lifelong / multi-task ILP).
2. **Fair vs Decom.** Head-to-head numbers only measure the representation
   (pixel vs block) if both sides use the same per-trial scratch protocol.
   Transfer on our side alone would confound the block-lift claim.
3. **Hypotheses do not transfer cleanly.** Each instance has its own latent
   rule, BK constants, and geometry. A program that paint-verifies on one
   trial is usually wrong for another category — or even another trial in the
   same family. Reusing “simple” solutions as priors is easy to turn into
   answer leakage or category-routed search (forbidden for the claim).
4. **Scientific target is representation.** We ask whether lifting
   pixels→blocks under one uniform mechanical language improves induction.
   Curriculum adds a second axis (what to transfer, when, how to avoid
   contamination) and muddies that measurement.

Cross-task library refinement remains an **optional later** extension
(Stage 7 in [02-SOLVER_PLAN.md](02-SOLVER_PLAN.md)), OFF for comparable
single-instance runs. Scoreboards and Decom comparisons assume scratch
induction per trial.
