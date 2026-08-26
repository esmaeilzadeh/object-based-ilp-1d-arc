# 01 — Approach & Landscape

Why this repository solves 1D-ARC with a **census-routed hybrid** of object-level and pixel-level inductive logic programming, and how that choice sits next to recent ILP methods.

## The problem

1D-ARC tasks are one-dimensional grids. A task shows a few input/output pairs (typically three training examples and one test input). The solver must infer the transformation rule and apply it to the test input.

Many rules are naturally stated over **objects**: contiguous runs of the same color (“move the left block past the pivot,” “recolor by length,” “flip the unit to the other end of the bar”). Stating the same ideas only in pixel coordinates is possible but verbose and brittle. Other rules change how many runs exist or stretch structure in ways that are awkward for a fixed object inventory (for example, duplicating a pattern across the row). A single representation therefore leaves blind spots.

The result this repo measures is **not** “blocks always beat pixels.” It is that a **block-level representation** plus Decom-family arithmetic on block sizes (no transform DSL) solves census-match categories that pixel Decom misses. A name-free train-grid **census** then routes the rest to the pixel encoding so those wins are not paid for by collapsing duplication-style tasks.

## Three recent ILP strategies

### A. Relational Decomposition + Popper (Hocquette & Cropper, IJCAI 2025)

**What they did.** Decompose input/output grids into pixel facts (`in`, `out`, `empty`), add arithmetic predicates, and let off-the-shelf Popper learn rules whose head is roughly “output color at position.”

**Why it matters.** Domain-light, interpretable, and exact on the pixel level. It showed that standard ILP can solve ARC-style tasks without a neural network or a hand-crafted domain-specific language (DSL).

**The limitation.** Because background knowledge is pixel-level, the learner must reconstruct object concepts from coordinates when the true rule is about blocks. That forces long clauses and struggles with counting and first-class block sizes.

In this repo we treat Decom as the **shared-engine baseline**: same Popper family, same 54-task evaluation slice, different representation (and, in our case, a router).

### B. ILPAR — ILP over an object DSL (Rocha et al., 2024/2025)

**What they did.** Use a hand-designed object-centric DSL as background knowledge and have ILP generate output objects into an empty grid.

**Why it matters.** Objects-first matches the relational nature of many ARC transforms. First-order logic fits relations naturally.

**The limitation.** The DSL is fixed *a priori*. The system inherits the designer’s choices about which object operations are possible. Scaling that vocabulary to the full 1D-ARC benchmark is hard without baking transform knowledge into the language.

### C. This repository — census-routed hybrid ILP (`hybrid_census`)

**What we do.** For each JSON trial independently:

1. Run a **name-free census** on the training pairs (see below).
2. If the census says object geometry is preserved, induce an **object** program whose head paints blocks (`out_block`).
3. Otherwise induce a **pixel** program in the Decom-style head (`out`).
4. Decode to a pixel grid and score against gold.

Neither road is chosen by reading the category name (`1d_mirror`, `1d_pcopy_1c`, …). The census looks only at run counts derived from the grids.

**How it differs from A.** We still use Popper and we still score pixels, but we do not force every instance through a pixel-only language. When bulky/unit run counts are stable across train input→output, we give Popper first-class blocks.

**How it differs from B.** We do not ship a rich hand-authored transform DSL (no marker/reflect/mirror-index/fill recipes). Object background knowledge is the block individuals produced by segmentation, the ordinal/cardinal facts those individuals induce (`obj_succ`; `gap` as the empty span between successive blocks, as a size), and Decom-family binary arithmetic on those cardinals (`size_lt` ≈ `lt`, `size_add` ≈ `add`), all computed from that instance’s grids. Pixel background knowledge follows the Decom-style encoding path when the census fails.

**What we claim.** On tasks where a name-free run-count census says object structure is stable, first-class blocks plus that Decom-style arithmetic on block sizes solve categories pixel Decom does not. The census only routes the rest to the pixel encoding. The /54 hybrid number is that object-road lift **plus** not dumping mismatch tasks—not a claim that routing itself is the capability.

## The census in plain language

Segment every training row into maximal same-color runs. Split colored runs into:

- **Bulky runs** — length at least 2
- **Unit runs** — length exactly 1

For each train pair, compare input vs output:

- Same number of bulky runs?
- Same number of unit runs?

If **every** train pair answers yes to both, `census_match` is true → **object road**.  
If any pair fails → **pixel road**.

### Tiny match example (object road)

```
Input:  0 4 8 8 8 8 8 8 8 0
Output: 0 8 8 8 8 8 8 8 4 0
```

Both sides have one bulky run (seven `8`s) and one unit run (a single colored cell). Colors and order can change; **counts** match → object induction is appropriate.

### Tiny mismatch example (pixel road)

```
Input:  4 8 8 8
Output: 8 8 8 0 8 8 8
```

The output invents a different run inventory (structure/length profile changes). Counts no longer match → pixel induction.

## Positioning summary

| Method | Representation | What ILP learns | Prior in background knowledge | Main gap |
|--------|----------------|-----------------|-------------------------------|----------|
| Pixel relational decomposition (A) | pixels only | pixel `out` rules | arithmetic over indices | no first-class objects |
| ILPAR (B) | objects + DSL | object-generating rules | rich hand-designed DSL | DSL completeness; scale |
| **This repo (hybrid)** | **census → objects or pixels** | `out_block` **or** `out` | blocks + succession/gap-as-size + Decom-family size arith, or Decom-style pixels | census is a heuristic, not an oracle |

The baseline to beat is **A** (pixel Decom): same ILP engine family and the same evaluation protocol. Lead with the **census-match object-road** comparison vs Decom on those tasks; the hybrid /54 is the same encoding plus the pixel road on mismatch. Neither number is “we secretly switched vocabulary by task name.”

## Why per-task from scratch (not curriculum)

Both this repo and pixel Decom treat each JSON trial as an independent **few-shot program synthesis** problem: learn from that trial’s training pairs, then score the held-out test. There is no shared training set across categories, and no warm-start from a sibling task.

That is deliberate:

1. **ARC-style claim.** Invent a program for a *novel* transform from a tiny support set.
2. **Fair comparison.** Head-to-head numbers only stay meaningful if both sides use the same per-trial scratch protocol.
3. **No answer leakage via transfer.** Reusing “simple” solutions as priors risks contaminating the measurement.

Cross-task library refinement remains a possible later extension; it is disabled for the comparable single-instance runs described in the evaluation doc.

## Pipeline at a glance

```
Input grids (JSON)
        ↓
Train-grid census (bulky / unit run counts)
        ↓
   ┌────┴────┐
   │ match?  │
   └────┬────┘
  yes   │   no
   ↓    │    ↓
Object road     Pixel road
(out_block)     (out)
   ↓    │    ↓
Paint / decode to pixels
        ↓
Exact + soft score vs gold
```

The next document walks through both roads in detail. The tutorial then shows one real task on each road.
