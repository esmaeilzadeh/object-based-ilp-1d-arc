# 03 — Tutorial: A Full Example

This tutorial walks through one complete 1D-ARC task from raw JSON to predicted pixels. We use the `1d_denoising_1c_0` instance, which is small enough to inspect by hand but shows every stage of the pipeline.

## The task

The task file is `raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json`. It contains three training examples and one test input. Each grid is a single row of 32 pixels.

### Training example 0

```
Input:  0 0 4 0 0 0 0 0 4 4 4 4 4 4 4 4 4 4 0 0 0 0 4 0 0 0 0 0 0 0 0 0
Output: 0 0 0 0 0 0 0 0 4 4 4 4 4 4 4 4 4 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### Training example 1

```
Input:  0 0 0 2 0 0 2 0 0 2 0 0 2 0 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 0 0 0
Output: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 0 0 0
```

### Training example 2

```
Input:  4 4 4 4 4 4 4 4 4 4 4 4 4 4 0 0 0 4 0 0 0 0 4 0 0 0 0 0 0 0 0 0
Output: 4 4 4 4 4 4 4 4 4 4 4 4 4 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### Test example 3

```
Input:  3 3 3 3 3 3 3 3 3 3 3 3 0 0 3 0 0 3 0 0 0 3 0 0 0 0 0 0 0 0 0 0
Output: (to predict)
```

**What is the rule?** Looking at the training pairs: each input has one long run of a color and a few isolated single-pixel “noise” runs of the same color. The output keeps only the long run and deletes the noise. The test input follows the same pattern: a length-12 run of color `3`, plus three single-pixel noise runs of `3`.

---

## Step 1: Segmentation — from pixels to blocks

The first thing the solver does is segment each row into **maximal runs** — stretches of the same color that cannot be extended. Background (`0`) is also a run.

For training example 0, the input segments into seven runs:

| Block ID | Start | End | Length | Color | Type |
|----------|-------|-----|--------|-------|------|
| `b0` | 0 | 1 | 2 | 0 | background |
| `b1` | 2 | 2 | 1 | 4 | colored |
| `b2` | 3 | 7 | 5 | 0 | background |
| `b3` | 8 | 17 | 10 | 4 | colored — **largest** |
| `b4` | 18 | 21 | 4 | 0 | background |
| `b5` | 22 | 22 | 1 | 4 | colored |
| `b6` | 23 | 31 | 9 | 0 | background |

The other examples segment similarly. Example 1 has five colored runs (four single-pixel noise runs and one length-15 run). Example 2 has three colored runs (one length-14 run and two single-pixel noise runs). The test example has four colored runs (one length-12 run and three single-pixel noise runs).

This segmentation is deterministic. It is stored in Python as `block_geometry`: a map from example ID → block ID → `[start, end]`. We will use this map later to paint blocks back to pixels.

---

## Step 2: Background knowledge — facts for the learner

The encoder writes a file `bk.pl` containing Prolog facts that describe the blocks. Here are the facts for training example 0:

```prolog
block(0, b1, s1, v4).
block(0, b3, s10, v4).
block(0, b5, s1, v4).
```

In English: “Example 0 has a colored block `b1` of length 1 and color 4, a block `b3` of length 10 and color 4, and a block `b5` of length 1 and color 4.”

The `s*` and `v*` prefixes are **typed roles**. `s10` means “size 10”, `v4` means “color 4”. These types prevent the learner from confusing a block ID with a length or a color.

Additional facts describe relationships:

```prolog
largest(0, b3).
non_largest(0, b1).
non_largest(0, b5).

gap(0, b1, b3, s5).
gap(0, b3, b5, s4).

obj_succ(0, b1, b3).
obj_succ(0, b3, b5).
```

- `largest(0, b3)` — in example 0, block `b3` is the longest colored run.
- `gap(0, b1, b3, s5)` — there are 5 background cells between blocks `b1` and `b3`.
- `obj_succ(0, b1, b3)` — block `b3` is the next colored run after `b1`.

Similar facts are written for examples 1 and 2. The test example gets its own background knowledge file (`test_bk.pl`), which follows the same format but only describes the test input.

---

## Step 3: Examples — teaching the target predicate

Popper learns a predicate called `out_block`:

```prolog
out_block(Example, BlockId, Offset, Length, Color)
```

This means: “In this example, paint the block `BlockId` at position `start(BlockId) + Offset`, with length `Length` and color `Color`.”

The encoder generates positive and negative examples.

**Positive examples** (one per training example):

```prolog
pos(out_block(0, b3, s0, s10, v4)).
pos(out_block(1, b9, s0, s15, v2)).
pos(out_block(2, b0, s0, s14, v4)).
```

In English: “For example 0, the correct output is block `b3` at offset 0 (unchanged position), length 10, color 4.”

**Negative examples** teach what is wrong. For example 0, the encoder writes things like:

```prolog
neg(out_block(0, b3, s0, s10, v1)).   % wrong color
neg(out_block(0, b3, s0, s1, v4)).    % wrong length
neg(out_block(0, b3, s1, s10, v4)).   % wrong offset
neg(out_block(0, b1, s0, s1, v4)).    % wrong block (noise, not largest)
```

These negatives prevent Popper from learning rules that paint the wrong block, the wrong color, the wrong length, or the wrong position.

---

## Step 4: Bias — constraining the search

The bias file `bias_object.pl` tells Popper what kinds of rules it may try. Key constraints in this instance:

```prolog
max_vars(10).        % at most 10 variables per rule
max_body(6).         % at most 6 conditions in a rule body
max_clauses(3).      % at most 3 rules in the program
head_pred(out_block, 5).
body_pred(block, 4).
body_pred(largest, 2).
body_pred(non_largest, 2).
body_pred(gap, 4).
body_pred(obj_succ, 3).
body_pred(size_lt, 2).
% ... and so on
```

The bias is generated mechanically from the facts in `bk.pl`. It does not know the task is called “denoising.” It only knows which predicates and constants appear in this instance.

---

## Step 5: Induction — what Popper learns

Popper receives `bk.pl`, `exs_object.pl`, and `bias_object.pl`. It searches for a small program that covers all positive examples and no negative examples.

For this task, Popper returns:

```prolog
out_block(V0, V1, V2, V3, V4) :-
    largest(V0, V1),
    s0(V2),
    block(V0, V1, V3, V4).
```

**Translation:** For any example `V0`, if block `V1` is the largest colored block, then paint it at offset `s0` (which means 0, so unchanged position) with its own length `V3` and color `V4`.

This is exactly the rule we observed: keep the largest block, delete the rest.

---

## Step 6: Verification — paint and check

Before accepting the program, the solver verifies it on the training examples:

1. Consult `bk.pl` and the learned program.
2. Query: which `out_block` atoms are true?
3. Paint each true block onto a pixel canvas using `block_geometry` (the map from block ID to start position).
4. Check that the painted grid matches the gold training output exactly.

For all three training examples, the rule paints only the largest block at its original position. This matches the gold outputs, so the program is accepted.

---

## Step 7: Application — solving the test input

The test input’s background knowledge (`test_bk.pl`) contains:

```prolog
block(3, b0, s12, v3).
block(3, b2, s1, v3).
block(3, b4, s1, v3).
block(3, b6, s1, v3).
largest(3, b0).
```

The learned rule says: paint the largest block at offset 0. Here, `b0` is the largest (length 12, color 3). So the rule paints:

```prolog
out_block(3, b0, s0, s12, v3)
```

Using `block_geometry`, block `b0` starts at position 0. Offset 0 means “start at 0.” Length 12 means “paint 12 cells.” Color 3 means “use color 3.”

The painted test output is:

```
3 3 3 3 3 3 3 3 3 3 3 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

This matches the gold test output exactly.

---

## Step 8: Scoring

The predicted grid is compared to gold. Since every cell matches, the exact score is 1 (solved) and the soft accuracy is 100%.

The file `test.pl` contains pixel-level gold facts (`pos(out(...))` and `neg(out(...))`) used only for this scoring step. They are not shown to Popper during learning.

---

## Summary: the pipeline in one paragraph

We segment the input into maximal runs (blocks). We write Prolog facts describing those blocks and their relationships. We generate positive and negative examples of the target `out_block` predicate. We let Popper search for a small rule that covers the positives and avoids the negatives. We verify that the rule paints the correct training outputs. Finally, we apply the rule to the test input and paint the result back to pixels.

For this denoising task, the learned rule is: **paint the largest block, unchanged.**
