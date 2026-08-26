# 03 — Tutorial: Both Roads

This tutorial walks through **two** complete solves that match what the code actually does:

1. **Part A — Object road** on `1d_flip_0` (`census_match=true`)
2. **Part B — Pixel road** on `1d_pcopy_1c_0` (`census_match=false`)

Commands use the default hybrid CLI.

```bash
source .venv/bin/activate
python -m solver.cli PATH.json --mode hybrid_census --timeout 60 \
  --work-dir work/tut --out work/tut/pred.json
```

After a run, open `pred.json` and check `failure_detail.census_match`, `failure_detail.road`, `level`, `program`, and `predicted_grid`. Do not guess the road from the category name alone—always read the JSON.

---

# Part A — Object road (`1d_flip_0`)

**File:** `raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json`

## The task (short grids)

### Training example 0

```
Input:  0 0 0 0 0 0 0 0 0 0 0 0 0 4 8 8 8 8 8 8 8 0 0 0 0
Output: 0 0 0 0 0 0 0 0 0 0 0 0 0 8 8 8 8 8 8 8 4 0 0 0 0
```

### Training example 1

```
Input:  0 0 0 0 1 3 3 3 3 3 3 3 3 3 3 0 0 0 0 0 0 0 0 0 0
Output: 0 0 0 0 3 3 3 3 3 3 3 3 3 3 1 0 0 0 0 0 0 0 0 0 0
```

### Training example 2

```
Input:  0 0 0 0 0 0 6 5 5 5 5 5 5 5 5 5 5 5 0 0 0 0 0 0 0
Output: 0 0 0 0 0 0 5 5 5 5 5 5 5 5 5 5 5 6 0 0 0 0 0 0 0
```

### Test

```
Input:  0 0 0 0 0 0 6 2 2 2 2 2 2 2 0 0 0 0 0 0 0 0 0 0 0
Output: (to predict; gold swaps the unit marker to the other end of the bar)
```

**Rule in English:** there is one long bar and one adjacent single-pixel marker. The output keeps both runs but **flips** which side of the bar the marker sits on (and swaps which color is the marker vs the bar body in the obvious way for each example).

## Why the census matches

For every train pair, count **bulky** colored runs (length ≥ 2) and **unit** colored runs (length = 1):

| Pair | Bulky in→out | Unit in→out |
|------|--------------|-------------|
| 0 | 1 → 1 | 1 → 1 |
| 1 | 1 → 1 | 1 → 1 |
| 2 | 1 → 1 | 1 → 1 |

Counts are preserved → `census_match=true` → hybrid takes the **object road** (`road: object`).

## Segmentation (example 0 input)

Ignore background for a moment; the interesting colored runs are:

| Block | Span (approx.) | Length | Color | Role |
|-------|----------------|--------|-------|------|
| unit | one cell of `4` | 1 | 4 | marker |
| bulky | seven cells of `8` | 7 | 8 | bar |

(Object facts number **colored** runs only; background gaps are `gap/4`, not extra block ids.)

## Background knowledge (English then Prolog)

The object encoder writes facts such as:

- **`block(Example, BlockId, Length, Color)`** — “this example has a colored run with this length and color.”
- **`obj_succ`** — which colored run sits to the right of which.
- **`bind`** — output object rank corresponds to an input object rank.
- **`gap`** — background length between successive colored runs.
- **`size_lt` / `size_add`** — compare and add observed lengths and gaps (same family as Decom `lt` / `add`).
- Size/color constants use typed prefixes (`s7`, `v8`) so lengths are not confused with block ids.

A sketch for example 0 (colored ranks only — open `work/tut/encode/bk.pl` after a real run for exact ids):

```prolog
% Conceptual — open work/tut/encode/bk.pl after a real run for exact ids
block(0, b_marker, s1, v4).
block(0, b_bar,    s7, v8).
obj_succ(0, b_marker, b_bar).
```

## Target examples

Head predicate:

> **`out_block(Example, BlockId, Offset, Length, Color)`**  
> “Paint this **input** block, shifted by `Offset`, with the given length and color.”

Positives teach how each train output is assembled from input blocks (here: both blocks still appear, but with swapped sides / colors as the flip requires). Negatives forbid wrong offsets, wrong colors, and painting the wrong block.

## Bias, induction, verify

`bias_object.pl` declares `head_pred(out_block,5)` and only allows body predicates that appear in this instance’s BK. Popper returns a small logic program. Before accepting it, the object road **paint-verifies** on all training outputs (`solver/verify.py`). On success:

- `level: object_ilp`
- `verified_train: true`
- `failure_detail.road: object`

Then the same program is applied to the test BK and painted to pixels.

### Work-dir sketch (object)

```
work/tut/
├── encode/
│   ├── bk.pl
│   ├── exs_object.pl
│   ├── bias_object.pl
│   ├── test_bk.pl
│   └── grids.json
├── popper_object/
│   └── program.pl
└── soft_score/
```

Try it:

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json \
  --mode hybrid_census --timeout 120 \
  --work-dir work/tut_flip --out work/tut_flip/pred.json
```

---

# Part B — Pixel road (`1d_pcopy_1c_0`)

**File:** `raw_data/onedarcraw/dataset/1d_pcopy_1c/1d_pcopy_1c_0.json`

## Why the census fails

### Training example 0 (excerpt)

```
Input:  0 0 1 1 1 0 0 1 0 0 ...
Output: 0 0 1 1 1 0 1 1 1 0 ...
```

| Pair | Bulky in→out | Unit in→out |
|------|--------------|-------------|
| 0 | 1 → 2 | 1 → 0 |
| 1 | 1 → 4 | 3 → 0 |
| 2 | 1 → 2 | 1 → 0 |

The output **invents extra bulky copies** of the pattern and removes unit markers. Counts change → `census_match=false` → hybrid takes the **pixel road** (`road: pixel`).

That is exactly the blind spot of an object head that only paints from an existing input-block inventory: the output needs more bars than the input provided as first-class objects.

## Tiny unit-test mismatch (same idea)

```
Input:  4 8 8 8
Output: 8 8 8 0 8 8 8
```

Run inventory changes → pixel road. The `solver/tests/test_pipeline_pixel.py` fixture uses this shape.

## What the pixel encoder writes

`solver/pixel_encode.py` builds a Decom-style encoding:

| Artifact idea | Meaning in English |
|---------------|--------------------|
| `in(Example, Position, Color)` | “At this index of the input, the color is …” |
| `empty(Example, Position)` | “This input index is background.” |
| `out(Example, Position, Color)` examples | “At this index of the **output**, the color should be …” |
| Bias `head_pred(out,3)` | Learn pixel output rules, not `out_block` |

English target: **for each position, what output color?** — not “which input block do I move?”

## Induction and acceptance

Popper searches under the pixel literal budget. On this road, **soft scoring** against Decom-style test facts is the main success signal (aligned with Decom’s evaluation helper). Paint-verify is not the sole gate. On success you typically see:

- `level: pixel_ilp`
- `failure_detail.road: pixel`
- `failure_detail.decom_solved: true` (when the soft matrix says so)

The predicted row comes from `apply_pixel_program`, not from painting `out_block` atoms.

### Work-dir sketch (pixel)

```
work/tut/
├── encode/           # pixel bk / exs / bias / test.pl (see pixel_encode.py)
├── popper_pixel/
│   └── program.pl
└── soft_score/
```

Try it:

```bash
python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_pcopy_1c/1d_pcopy_1c_0.json \
  --mode hybrid_census --timeout 120 \
  --work-dir work/tut_pcopy --out work/tut_pcopy/pred.json
```

---

## How to read the result JSON

| Field | Object road (Part A) | Pixel road (Part B) |
|-------|----------------------|---------------------|
| `failure_detail.census_match` | `true` | `false` |
| `failure_detail.road` | `object` | `pixel` |
| `level` | `object_ilp` | `pixel_ilp` |
| `verified_train` | paint-verify gate | soft / Decom-style path |
| `program` | `out_block(...)` clauses | `out(...)` clauses |

On hard failure both roads may return `fallback_identity` (often a copy of the test input) with reasons such as `popper_timeout` or `popper_exhausted`.

---

## Summary

1. Hybrid always starts with a **train-grid census** (bulky/unit counts).
2. **Match** (flip) → learn **which blocks to paint** (`out_block`), paint-verify, decode.
3. **Mismatch** (pcopy) → learn **which color per position** (`out`), soft-score like Decom, decode.
4. Trust `pred.json` + the work directory—not the category name—to see which road ran.
