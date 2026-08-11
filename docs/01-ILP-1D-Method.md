# 01 — Approach & Landscape

Why we solve 1D-ARC with **object-level** inductive logic programming, and how that choice positions this work among recent ILP methods.

## The problem

1D-ARC tasks are one-dimensional grids. A task shows a few input/output pairs (typically three training examples and one test input). The solver must infer the transformation rule and apply it to the test input.

The challenge is **relational**: the rule usually depends on *objects* (contiguous runs of the same color), not on individual pixels. A rule like “keep the largest block and delete the rest” is trivial to state in terms of objects, but verbose and brittle when expressed as pixel coordinates.

## Three recent ILP strategies

### A. Relational Decomposition + Popper (Hocquette & Cropper, IJCAI 2025)

**What they did.** Decompose input/output grids into pixel facts (`in`, `out`, `empty`), add arithmetic predicates (`my_succ`, `add`, `lt`), and let off-the-shelf Popper learn `out(Pixel, Color)` rules.

**Why it matters.** Domain-light, interpretable, and exact on the pixel level. It proved that standard ILP can solve ARC-style tasks without a neural network or a hand-crafted domain-specific language (DSL).

**The limitation.** Because the background knowledge is pixel-level, the learned rules must reconstruct objects from coordinates. That forces long clauses, struggles with counting, and cannot express “the block” as a first-class concept.

### B. ILPAR — ILP over an object DSL (Rocha et al., 2024/2025)

**What they did.** Use a hand-designed object-centric DSL as background knowledge and have ILP generate output objects into an empty grid.

**Why it matters.** Objects-first, which matches the relational nature of ARC. First-order logic fits relations naturally.

**The limitation.** The DSL is fixed *a priori*. The system inherits the designer’s choices about which object operations are possible, risking a bias toward what the developer already knows. It also does not scale to the full 900-task 1D-ARC benchmark.

### C. This repository — block-anchored object ILP (`block_primary`)

**What we do.** Per-instance Popper induction, but the facts are **blocks** (maximal same-color runs), not pixels. The head predicate is `out_block(Example, BlockId, Offset, Length, Color)`. The bias (the grammar of rules Popper can try) is generated mechanically from that instance’s own facts.

**How it differs from A.** We keep the ILP machinery but lift the representation from pixels to blocks. Popper learns rules about objects directly, without needing to invent object concepts from coordinates.

**How it differs from B.** We do not hand-craft a DSL of transforms. The only prior is segmentation (maximal runs) and aggregation (largest, smallest, count). The relations over blocks are learned, not given.

**Known limits.** No cross-task library yet. The segmentation prior is fixed (maximal same-color runs). No pixel-head rescue — if the block representation fails, the task fails.

## Positioning summary

| Method | Representation | What ILP learns | Prior in background knowledge | Main gap |
|--------|----------------|-----------------|------------------------------|----------|
| Pixel relational decomposition (A) | pixels | `out(Pixel, Color)` | arithmetic | no object concept |
| ILPAR (B) | objects + DSL | object-generating rules | rich object DSL | DSL completeness; scale |
| **This repo** | **blocks + aggregations** | `out_block/5` | segmentation + aggregation only | no library; hard sub-object tasks stay hard |

The baseline to beat is **A** (pixel Decom), not because A is the strongest system overall, but because it shares the same ILP engine (Popper) and the same evaluation protocol. The comparison isolates the effect of the representation: pixels versus blocks.

## Why per-task from scratch (not curriculum)

Both this repo and pixel Decom treat each JSON trial as an independent **few-shot program synthesis** problem: learn from that trial’s training pairs, then score the held-out test. There is no shared training set across categories, and no warm-start from a simpler sibling task.

That is deliberate:

1. **ARC-style claim.** The target is inventing a program for a *novel* transform from a tiny support set — not accumulating a curriculum of known transforms.
2. **Fair comparison.** Head-to-head numbers only measure the representation (pixel vs block) if both sides use the same per-trial scratch protocol.
3. **Hypotheses do not transfer cleanly.** Each instance has its own latent rule, constants, and geometry. Reusing “simple” solutions as priors risks answer leakage.
4. **Scientific target is representation.** We ask whether lifting pixels→blocks under one uniform mechanical language improves induction. Curriculum adds a second axis that muddies that measurement.

Cross-task library refinement remains an optional later extension, but it is disabled for the comparable single-instance runs reported here.

## Pipeline at a glance

```
Input grids (JSON)
    ↓
Segment into maximal runs (blocks)
    ↓
Encode as Prolog facts (BK) + examples (exs) + bias
    ↓
Popper induces out_block/5 rules
    ↓
Paint-verify on training examples
    ↓
Decode to pixels for test scoring
```

The next document walks through this pipeline in detail.
