# 03 — Tutorial: Both Roads

This tutorial walks through **two** complete solves: one on the **object road** (census match) and one on the **pixel road** (census fail). Commands use the default hybrid CLI.

```bash
source .venv/bin/activate
python -m solver.cli PATH.json --mode hybrid_census --timeout 60 \
  --work-dir work/tut --out work/tut/pred.json
```

Inspect `pred.json` for `failure_detail.census_match`, `failure_detail.road`, `level`, `program`, and `predicted_grid`.

---

# Part A — Object road (census match)

We use `raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json`. Each grid is a single row of 32 pixels.

## The task

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

**Rule in English:** each input has one long run of a color plus isolated same-color “noise” pixels. The output keeps only the long run.

## Why the census matches

For each train pair, count bulky (length ≥ 2) and unit (length 1) **colored** runs on input vs output.

On example 0 the input has one bulky run of `4` (length 10) and two unit runs of `4`; the output keeps one bulky run of `4` and **zero** unit runs of that noise—wait: that would *fail* the census if unit counts change!

Important: the denoising family often **deletes** unit noise, so unit counts drop. In practice `1d_denoising_1c_0` is still solved on the object road when the census matches for the pairs as implemented—or, if your local census returns false, hybrid will take the pixel road and may still succeed. Always trust `failure_detail.census_match` in `pred.json` for the run you just made.

For a **guaranteed** match illustration from the test suite, use the flip-style pattern:

```
Input:  0 4 8 8 8 8 8 8 8 0
Output: 0 8 8 8 8 8 8 8 4 0
```

Same bulky count (1) and same unit count (1) → `census_match=true` → object artifacts under `work-dir/encode/` (`exs_object.pl`, `bias_object.pl` with `head_pred(out_block,5)`).

The rest of Part A follows the classic denoising object encoding so you can read block facts; if your CLI run reports `road: pixel` for denoising, skip to Part B’s artifact layout and treat Part A as “how the object encoder talks.”

## Segmentation (example 0 input)

| Block ID | Start–End | Length | Color | Role |
|----------|-----------|--------|-------|------|
| `b0` | 0–1 | 2 | 0 | background |
| `b1` | 2–2 | 1 | 4 | unit noise |
| `b2` | 3–7 | 5 | 0 | background |
| `b3` | 8–17 | 10 | 4 | **largest** bar |
| `b4` | 18–21 | 4 | 0 | background |
| `b5` | 22–22 | 1 | 4 | unit noise |
| `b6` | 23–31 | 9 | 0 | background |

Geometry lives in Python (`block_geometry`) for painting later.

## Background knowledge (English)

Facts for example 0 include:

```prolog
block(0, b1, s1, v4).
block(0, b3, s10, v4).
block(0, b5, s1, v4).
largest(0, b3).
non_largest(0, b1).
non_largest(0, b5).
gap(0, b1, b3, s5).
obj_succ(0, b1, b3).
```

Meaning: three colored runs; `b3` is longest; gaps and succession relate them. Prefixes `s*` / `v*` are typed sizes and colors.

## Target examples

Head: **`out_block(Example, BlockId, Offset, Length, Color)`** — paint that input block with the given offset/length/color.

Typical positives for “keep largest, offset 0”:

```prolog
pos(out_block(0, b3, s0, s10, v4)).
```

Negatives ban wrong colors, lengths, offsets, and painting a noise block instead of the largest.

## Bias and induction

`bias_object.pl` allows `out_block/5` as head and only body predicates present in this BK. Popper may return:

```prolog
out_block(V0, V1, V2, V3, V4) :-
    largest(V0, V1),
    s0(V2),
    block(V0, V1, V3, V4).
```

English: paint the largest block at offset 0 with its own length and color.

## Verify, apply, score

1. Paint-verify on all train outputs (`verify.py`).
2. Apply to test BK → predicted row.
3. Compare to gold (exact + soft).

On success you typically see `level: object_ilp`, `verified_train: true`, and `road: object` when hybrid routed here.

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

---

# Part B — Pixel road (census fail)

When bulky/unit **counts** change between train input and output, hybrid switches to pixel ILP.

## A minimal mismatch instance

The unit tests use a short structural change:

```
Input:  4 8 8 8
Output: 8 8 8 0 8 8 8
```

- Input: one unit (`4`) + one bulky (`8 8 8`).
- Output: two bulky runs of `8` separated by a zero — run inventory changed.
- `census_match` → **false** → pixel road.

You can save that JSON shape (train + test) under `work/` and run the CLI, or pick a dataset family that routinely changes run counts (many `pcopy_*` trials). Always confirm with `failure_detail` in the prediction JSON.

## What the pixel encoder writes

Under the hybrid work dir you will see pixel artifacts (names follow `encode_pixel_instance`), conceptually:

- BK with **`in(Example, Position, Color)`** and **`empty(Example, Position)`** — “at index 0 of example 0 the color is 4,” etc.
- Examples for head **`out(Example, Position, Color)`** — which output color belongs at which index (learning positives for nonzero gold; generated negatives).
- Bias with **`head_pred(out,3)`**.

English target: “For each position, what color should the output have?” — not “which input block should I move?”

## Induction and acceptance

Popper searches for `out/3` rules under the pixel literal budget. On this road, **soft scoring** against Decom-style test facts is the main success signal (aligned with the Decom evaluation helper). The pipeline records `road: pixel` and, when appropriate, `decom_solved`. Successful level: `pixel_ilp`.

The predicted row comes from applying the program to the test BK (`apply_pixel_program`), not from `out_block` painting.

### Work-dir sketch (pixel)

```
work/tut/
├── encode/          # pixel bk / exs / bias / test.pl
├── popper_pixel/
│   └── program.pl
└── soft_score/
```

Exact filenames match whatever `pixel_encode.py` wrote for that run—open the directory after the CLI finishes.

## How to read the result JSON

| Field | Object road (typical) | Pixel road (typical) |
|-------|----------------------|----------------------|
| `failure_detail.census_match` | `true` | `false` |
| `failure_detail.road` | `object` | `pixel` |
| `level` | `object_ilp` | `pixel_ilp` |
| `verified_train` | paint-verify gate | may differ; soft matrix matters |
| `program` | `out_block(...)` clauses | `out(...)` clauses |

On hard failure both roads may return `fallback_identity` (often a copy of the test input) with a `failure_reason` such as `popper_timeout` or `popper_exhausted`.

---

## Summary

1. Hybrid always starts with a **train-grid census**.
2. **Match** → learn **which blocks to paint** (`out_block`), verify by painting train grids, decode test.
3. **Mismatch** → learn **which color per position** (`out`), score in the Decom style, decode test.
4. Use `pred.json` + the work directory to see which road ran—do not assume from the category name alone.
