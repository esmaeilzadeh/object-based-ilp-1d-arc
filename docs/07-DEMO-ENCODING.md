# 07 — Demo encoding (`1d_denoising_1c_0`)

Standalone walkthrough of **one** solved instance. Everything below is taken
from the inspectable dump under `work/demo/` (not a survey of the full 54-task
suite).

| | |
|---|---|
| **Task JSON** | `raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json` |
| **Work dir** | `work/demo/` |
| **Mode** | `block_primary` (object head only) |
| **Reproduce** | see §8 |

Artifacts:

```
work/demo/
├── encode/
│   ├── grids.json          # pixels + block geometry
│   ├── bk.pl               # train background knowledge
│   ├── exs_object.pl       # pos/neg out_block examples
│   ├── bias_object.pl      # Popper bias for this instance
│   ├── test_bk.pl          # test-example BK (decode time)
│   ├── test.pl             # pixel gold for soft scoring
│   └── _apply_object_prog.pl
├── popper_object/program.pl
└── soft_score/_score_prog.pl
```

---

## 1. Pixel grids

Length-32 rows. Color `0` is background; non-zero runs are the objects.

### Train 0

```
in:  0 0 4 0 0 0 0 0 4 4 4 4 4 4 4 4 4 4 0 0 0 0 4 0 0 0 0 0 0 0 0 0
out: 0 0 0 0 0 0 0 0 4 4 4 4 4 4 4 4 4 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### Train 1

```
in:  0 0 0 2 0 0 2 0 0 2 0 0 2 0 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 0 0 0
out: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 0 0 0
```

### Train 2

```
in:  4 4 4 4 4 4 4 4 4 4 4 4 4 4 0 0 0 4 0 0 0 0 4 0 0 0 0 0 0 0 0 0
out: 4 4 4 4 4 4 4 4 4 4 4 4 4 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### Test 3

```
in:  3 3 3 3 3 3 3 3 3 3 3 3 0 0 3 0 0 3 0 0 0 3 0 0 0 0 0 0 0 0 0 0
out: 3 3 3 3 3 3 3 3 3 3 3 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

Reading at a glance: keep the long same-color run; drop the short same-color
“noise” runs (single-color denoising).

---

## 2. Block geometry (maximal runs)

`grids.json` → `block_geometry`: every maximal run (including background) gets a
local block id `0,1,2,…` with inclusive pixel span `[start, end]`.

Colored objects used in BK use typed ids `b*` that match those indices
(`b1` ↔ geometry key `"1"`, etc.). Background runs stay in geometry for paint
decode but are **not** asserted as `block/4`.

### Example 0 — geometry and colored blocks

| Bid | Span | Len | Color | In `block/4`? |
|---|---|---|---|---|
| `b0` | `[0,1]` | 2 | 0 | no (bg) |
| `b1` | `[2,2]` | 1 | 4 | yes |
| `b2` | `[3,7]` | 5 | 0 | no |
| `b3` | `[8,17]` | 10 | 4 | yes — **largest** |
| `b4` | `[18,21]` | 4 | 0 | no |
| `b5` | `[22,22]` | 1 | 4 | yes |
| `b6` | `[23,31]` | 9 | 0 | no |

### Example 1 — colored blocks only

| Bid | Span | Len | Color | Note |
|---|---|---|---|---|
| `b1` | `[3,3]` | 1 | 2 | noise |
| `b3` | `[6,6]` | 1 | 2 | noise |
| `b5` | `[9,9]` | 1 | 2 | noise |
| `b7` | `[12,12]` | 1 | 2 | noise |
| `b9` | `[14,28]` | 15 | 2 | **largest** |

### Example 2 — colored blocks only

| Bid | Span | Len | Color | Note |
|---|---|---|---|---|
| `b0` | `[0,13]` | 14 | 4 | **largest** |
| `b2` | `[17,17]` | 1 | 4 | noise |
| `b4` | `[22,22]` | 1 | 4 | noise |

### Test example 3 — colored blocks only

| Bid | Span | Len | Color | Note |
|---|---|---|---|---|
| `b0` | `[0,11]` | 12 | 3 | **largest** |
| `b2` | `[14,14]` | 1 | 3 | noise |
| `b4` | `[17,17]` | 1 | 3 | noise |
| `b6` | `[21,21]` | 1 | 3 | noise |

---

## 3. Typed roles

Atoms are role-prefixed so ILP cannot unify a block id with a length or color:

| Prefix | Role | Examples in this dump |
|---|---|---|
| `b*` | block id | `b0`, `b1`, `b3`, … |
| `s*` | size / offset / length | `s0`, `s1`, `s10`, `s15`, … |
| `v*` | color value | `v2`, `v3`, `v4` |
| `p*` | ordinal position (via `cardinal_ordinal`) | `p1`, `p10`, … |

Constants also appear as unary facts (`s0(s0).`, `v4(v4).`, …) so bias can treat
them as body preds.

---

## 4. Train BK (`encode/bk.pl`) — what the learner sees

Only **train** examples `0,1,2` appear in `bk.pl`. Representative facts:

### Objects

```prolog
block(0,b1,s1,v4).
block(0,b3,s10,v4).
block(0,b5,s1,v4).
block(1,b1,s1,v2).
block(1,b3,s1,v2).
block(1,b5,s1,v2).
block(1,b7,s1,v2).
block(1,b9,s15,v2).
block(2,b0,s14,v4).
block(2,b2,s1,v4).
block(2,b4,s1,v4).
```

`block(Ex, Bid, Len, Color)`.

### Size / adjacency relations (mechanical, from the grids)

```prolog
largest(0,b3).
largest(1,b9).
largest(2,b0).
non_largest(0,b1).
non_largest(0,b5).
% …

gap(0,b1,b3,s5).      % zero-run length between colored blocks
gap(0,b3,b5,s4).
obj_succ(0,b1,b3).    % next colored object along the line
obj_succ(0,b3,b5).
obj_pair(0,b1,b3).
component_start(0,b1).
component_len(0,b3,s10).
```

### Arith sugar (sizes that actually occur)

```prolog
size_lt(s1,s10).
size_add(s1,s5,s6).
size_sum3(s1,s5,s10,s16).
size_even(s10).
size_odd(s1).
cardinal_ordinal(s10,p10).
```

No task-name BK, no mirror/marker predicates — only facts derived uniformly from
this instance’s runs and observed sizes/gaps.

---

## 5. Examples (`encode/exs_object.pl`)

Head target: `out_block(Ex, Bid, Off, Len, Color)`.

### Positives (one per train example)

```prolog
pos(out_block(0,b3,s0,s10,v4)).   % keep largest of ex 0 at offset 0
pos(out_block(1,b9,s0,s15,v2)).
pos(out_block(2,b0,s0,s14,v4)).
```

Meaning: paint the chosen input block’s color/length starting at
`start(Bid) + Off`. Here `Off = s0` (no shift).

### Negatives (sketch)

For each positive, the file enumerates wrong colors, wrong lengths, wrong
offsets, and wrong bids (e.g. painting a non-largest noise block). Excerpt for
example 0:

```prolog
neg(out_block(0,b3,s0,s10,v1)).   % wrong color
neg(out_block(0,b3,s0,s1,v4)).    % wrong length
neg(out_block(0,b3,s1,s10,v4)).   % wrong offset
neg(out_block(0,b1,s0,s1,v4)).    % wrong (non-largest) bid
neg(out_block(0,b5,s0,s1,v4)).
```

---

## 6. Bias (`encode/bias_object.pl`)

Instance-local mechanical bias: head `out_block/5`, body preds that appear in
this BK, typed constants `s*` / `v*`, and Bid-anchoring constraints (every clause
must mention `block` on the head’s block id; ex-argument of body preds fixed to
the head’s `Ex`).

Caps in this dump:

```prolog
max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
head_pred(out_block,5).
body_pred(block,4).
body_pred(largest,2).
body_pred(non_largest,2).
body_pred(gap,4).
body_pred(obj_succ,3).
body_pred(size_lt,2).
body_pred(size_add,3).
body_pred(size_sum3,4).
% …
```

---

## 7. Induced program → decode → score

### Program (`popper_object/program.pl`)

```prolog
out_block(V0,V1,V2,V3,V4):- largest(V0,V1),s0(V2),block(V0,V1,V3,V4).
```

| Var | Role | Bound by |
|---|---|---|
| `V0` | example id | shared |
| `V1` | block id | `largest(Ex, Bid)` |
| `V2` | offset | `s0` → **0** |
| `V3` | length | from `block(Ex, Bid, Len, Color)` |
| `V4` | color | from `block(Ex, Bid, Len, Color)` |

**Reading:** for each example, emit exactly the **largest** colored input block,
unmoved (`Off=0`), same length and color. Noise runs are never selected.

### Test-time BK (`encode/test_bk.pl`)

Same predicate language for example `3` only, e.g.:

```prolog
block(3,b0,s12,v3).
block(3,b2,s1,v3).
block(3,b4,s1,v3).
block(3,b6,s1,v3).
largest(3,b0).
non_largest(3,b2).
% …
```

Applying the program yields `out_block(3,b0,s0,s12,v3)`. Decode paints cells
`[0..11]` with color `3` (geometry start of `b0` plus offset 0). That matches the
gold test row; soft-score prog (`soft_score/_score_prog.pl`) records:

```prolog
out(3,0,3).
out(3,1,3).
% …
out(3,11,3).
```

---

## 8. How this dump was produced

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json --work-dir work/demo
```

Inspect:

```bash
cat work/demo/encode/bk.pl
cat work/demo/encode/exs_object.pl | head
cat work/demo/encode/bias_object.pl
cat work/demo/popper_object/program.pl
```

General pipeline notes (all tasks) → [03-CURRENT_METHOD.md](03-CURRENT_METHOD.md).  
Runbook → [06-RUNNING.md](06-RUNNING.md).
