# 02 — Method: Encode, Induce, Decode

This document describes the complete pipeline: how a 1D-ARC JSON file becomes a solved pixel grid. It merges the design plan and the as-built snapshot into one definitive method description.

## Overview

The solver takes one ARC instance (three training input/output pairs and one test input) and returns a predicted test grid. The core idea is to **lift the representation from pixels to objects** (maximal same-color runs), let Popper learn rules about those objects, then paint the answer back to pixels.

The pipeline has five stages:

1. **Encode** — Segment grids into blocks, write Prolog facts (background knowledge), generate training examples, and build a per-instance bias (the grammar of rules Popper may try).
2. **Induce** — Run Popper once to learn `out_block(Example, BlockId, Offset, Length, Color)` rules.
3. **Verify** — Paint the learned rules onto training inputs and check that every training output is reproduced exactly.
4. **Apply** — Run the verified rules on the test input’s blocks.
5. **Score** — Compare the painted test pixels to gold, producing exact-match and soft-accuracy numbers.

Everything is per-instance. Nothing is learned across tasks.

---

## Stage 1: Encoding — from grids to logic

### Segmentation

Each input row is segmented into **maximal runs** of the same color. A maximal run cannot be extended left or right without changing color. Background color `0` is also a run.

All runs share one left-to-right identifier space: `b0`, `b1`, `b2`, … For example, a row like `0 0 4 4 4 0 2 2` has four runs: `b0` = two zeros, `b1` = three fours, `b2` = one zero, `b3` = two twos.

### Facts written to `bk.pl` (background knowledge)

For each training example, the encoder writes facts that describe the blocks and their relationships. The vocabulary is **typed**: different kinds of values cannot be mixed.

| Type | Prefix | Example | Meaning |
|------|--------|---------|---------|
| `block_id` | `b*` | `b3` | Run identifier |
| `size` | `s*` | `s10` | Length or offset |
| `value` | `v*` | `v4` | Color |
| `rank` | `r*` | `r2` | Ordinal position |

**Core facts:**

- `block(Example, BlockId, Length, Color)` — a colored run.
- `empty_block(Example, BlockId, Length)` — a background run (not emitted on the lean path, but part of the full vocabulary).
- `largest(Example, BlockId)` — the longest colored run in that example.
- `non_largest(Example, BlockId)` — any other colored run.
- `gap(Example, BlockId1, BlockId2, Size)` — the number of background cells between two colored runs.
- `obj_succ(Example, BlockId1, BlockId2)` — BlockId2 is the next colored run after BlockId1.
- `obj_index(Example, BlockId, Rank)` — dense ordinal among colored runs only (first colored run is rank 0, second is rank 1, …).

**Arithmetic sugar** (only sizes that actually appear in this instance):

- `size_lt(A, B)` — size A is less than size B.
- `size_add(A, B, Result)` — A + B = Result.
- `size_sum3(A, B, C, Result)` — A + B + C = Result.
- `size_even(Size)` / `size_odd(Size)`.
- `cardinal_ordinal(Size, Position)` — bridges sizes to ordinal positions.

These are **not** learned; they are mechanical relations computed from the instance. The bias only allows Popper to use predicates that actually appear in the background knowledge.

### Examples written to `exs_object.pl`

Popper needs positive and negative examples of the target predicate. The head is:

```prolog
out_block(Example, BlockId, Offset, Length, Color)
```

- **Positive example:** The correct output block for each training example. For denoising tasks, this is typically the largest input block, unchanged in position (`Offset = 0`).
- **Negative examples:** Wrong colors, wrong lengths, wrong offsets, and wrong block choices. These teach Popper what *not* to learn.

### Bias written to `bias_object.pl`

The bias constrains the search space:

- `max_vars(10)` — at most 10 variables per rule.
- `max_body(6)` — at most 6 conditions in the body of a rule.
- `max_clauses(3)` — at most 3 rules in the program.
- `head_pred(out_block, 5)` — the target predicate.
- `body_pred(Predicate, Arity)` — which predicates may appear in rule bodies.

The bias is **mechanical**: it is generated from the instance’s own facts, not hand-tuned per task category.

---

## Stage 2: Induction — Popper learns the rule

The three files (`bk.pl`, `exs_object.pl`, `bias_object.pl`) are passed to Popper. Popper searches for a small logic program that covers all positive examples and no negative examples.

The output is a set of clauses like:

```prolog
out_block(V0, V1, V2, V3, V4) :-
    largest(V0, V1),
    s0(V2),
    block(V0, V1, V3, V4).
```

In English: “For any example `V0`, if block `V1` is the largest, paint it at offset `s0` (meaning 0, i.e., unchanged position) with its own length `V3` and color `V4`.”

---

## Stage 3: Verification — paint and check

Popper’s “train-perfect” is not enough. A program might cover the examples in a way that does not actually paint the correct pixels (e.g., wrong offset, overlapping blocks).

The verifier:

1. Copies the learned program to a temporary file with `:- dynamic out_block/5.` so SWI-Prolog can consult it.
2. Consults the training background knowledge (`bk.pl`) and the program.
3. Queries which `out_block(Example, BlockId, Offset, Length, Color)` atoms are true.
4. Paints each block onto a pixel canvas starting at `start(BlockId) + Offset`.
5. Checks that every painted grid matches the gold training output exactly.

If any training example fails, the program is rejected and the pipeline falls back to returning the test input unchanged (`fallback_identity`).

---

## Stage 4: Application — decode the test grid

The test input gets its own background knowledge (`test_bk.pl`), same format as training. The verified program is consulted with the test background knowledge, and the true `out_block` atoms are painted using the same `block_geometry` map.

The result is a predicted pixel row.

---

## Stage 5: Scoring — exact and soft metrics

- **Exact:** The predicted grid must match gold cell-for-cell.
- **Soft accuracy:** `(TP + TN) / (TP + FN + TN + FP)`, computed by comparing predicted pixel colors to gold. This is the same metric used by the pixel Decom baseline.

The file `test.pl` contains pixel-level `pos(out(...))` and `neg(out(...))` facts used **only** for this scoring step. Popper never sees them.

---

## Design constraints (what we do not do)

- **No pixel-head rescue.** If the block representation fails, the task fails. We do not fall back to pixel ILP.
- **No category-named bias.** The bias is generated from the instance’s own facts, not from a task-type label like `1d_mirror`.
- **No marker/reflect hacks.** No special predicates that precompute the answer.
- **No curriculum.** Each trial is learned from scratch.

---

## Known limitations and failure modes

### Non-monotonic search at long timeouts

Popper’s timeout is a **search budget**, not “stop at first success.” When Popper finds a train-perfect program, it keeps searching for a smaller one. At the end it returns the **last best**, not the first program that was already good.

This can cause a shorter timeout (e.g., 120 s) to produce a better answer than a longer timeout (e.g., 3600 s), because the longer run replaces a valid program with a later compressed one that fails paint verification or generalizes worse.

**Mitigation:** Not currently implemented. Possible directions are paint-aware induction (steer search toward paint-consistent programs) or anytime candidate retention (keep the first train-paint-valid program).

### The `pcopy` blind spot

Tasks that duplicate pixel patterns (e.g., copy a block multiple times) are hard for the block representation because the output contains more blocks than the input. The current encoding anchors output blocks to input blocks; it cannot invent new blocks. These tasks remain a pixel-head advantage.

---

## Where to look in the code

| File | Role |
|------|------|
| `solver/encoder.py` | Segmentation, fact generation, `bk.pl`, `exs_object.pl` |
| `solver/bias_gen.py` | Mechanical bias generation from instance facts |
| `solver/induce.py` | Popper invocation and timeout handling |
| `solver/verify.py` | Paint-verify on training examples |
| `solver/decode.py` | Paint `out_block` atoms to pixel grids |
| `solver/pipeline.py` | Orchestrates the five stages |
