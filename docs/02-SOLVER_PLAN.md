# 02 — Method: Census, Encode, Induce, Decode

How a 1D-ARC JSON file becomes a predicted pixel grid in the **current codebase**.

## Overview

The entry point for the headline system is `solve_hybrid` in `solver/pipeline.py` (CLI/harness mode `hybrid_census`). For each instance it:

1. Loads the JSON (train pairs + test input).
2. Runs `census_match` on the **training** grids only.
3. Takes either the **object road** (`solve`, head `out_block`) or the **pixel road** (Decom-style `out/3`).
4. Returns a `SolveResult` with a predicted test row, program text, level, soft scores, and `failure_detail` tags such as `census_match` and `road`.

Mode `block_primary` skips the census and always runs the object road. Use it for ablations, not as the default claim.

Nothing is learned across tasks. Each JSON trial is independent.

---

## Stage 0: The census gate

**Code:** `solver/census.py` → `census_match(train)`.

### What “bulky” and “unit” mean

Segment a row into maximal same-color runs (cannot extend left/right without changing color). Among **colored** runs (non-background):

| Name | Rule | Intuition |
|------|------|-----------|
| Bulky | length ≥ 2 | A solid bar |
| Unit | length = 1 | A single-pixel “dot” |

Background (`0`) runs are ignored for the census counts.

### Decision rule

For **every** training pair:

- `#bulky(input) == #bulky(output)` **and**
- `#unit(input) == #unit(output)`

If that holds for all pairs (and there is at least one pair), return **True** → object road.  
Otherwise return **False** → pixel road.

The census does **not** look at task names. It does **not** check that colors or positions stay the same—only run **counts**.

### Worked match

```
Input:  0 4 8 8 8 8 8 8 8 0
Output: 0 8 8 8 8 8 8 8 4 0
```

- Input bulky: one (seven `8`s). Unit: one (the `4`).
- Output bulky: one (seven `8`s). Unit: one (the `4`).
- Counts match → object road (`road: object` in the result detail).

### Worked mismatch

```
Input:  4 8 8 8
Output: 8 8 8 0 8 8 8
```

Run inventory changes (new structure appears). Counts fail → pixel road (`road: pixel`).

---

## Object road (when the census matches)

Used by `solve` / the match branch of `solve_hybrid`. Goal: learn which **input blocks** to paint, where (offset), how long, and which color.

### Segmentation

Each row becomes maximal **colored** runs (background is not a searchable object). IDs are left-to-right dense ranks: `b0`, `b1`, …. Example row `0 0 4 4 4 0 2 2`:

| ID | Cells | Length | Color |
|----|-------|--------|-------|
| `b0` | three fours | 3 | 4 |
| `b1` | two twos | 2 | 2 |

Geometry (start/end per block) is kept in Python for painting; searchable BK uses typed constants.

### Typed roles (why prefixes exist)

| Type | Prefix | Example | Meaning |
|------|--------|---------|---------|
| Block id | `b*` | `b3` | Which run |
| Size | `s*` | `s10` | Length or offset |
| Value | `v*` | `v4` | Color |

Typing stops the learner from treating “block 3” as “length 3.”

### Background knowledge (`bk.pl`) — English then Prolog

For each training example the encoder emits facts such as:

- **`block(Example, BlockId, Length, Color)`** — “example 0 has a colored run `b0` of length 10 and color 4” → `block(0, b0, s10, v4).`
- **`obj_succ`** — next colored run to the right.
- **`bind`** — output object rank corresponds to an input object rank.
- **`gap`** — background length between two successive colored runs.
- **`size_lt` / `size_add` / `size_sum3`** — compare and add sizes that appear in this instance.
- **`cardinal_ordinal`** — a size constant that coincides with a position index.

The bias only allows body predicates that show up in this instance’s BK (from that same set).

**Code:** `solver/encoder.py`, `solver/bias_gen.py`, `solver/predicates.py`.

### Examples (`exs_object.pl`)

Head predicate (five arguments):

> **`out_block(Example, BlockId, Offset, Length, Color)`**  
> “In this example, take input block `BlockId`, shift its start by `Offset`, and paint `Length` cells with `Color`.”

- **Positives** — correct output blocks for each train example.
- **Negatives** — wrong block choice, wrong color, wrong length, wrong offset (so Popper learns what *not* to do).

### Bias (`bias_object.pl`)

Mechanically generated search grammar: max vars/body/clauses, `head_pred(out_block,5)`, and `body_pred` lines for predicates present in this instance. **Not** selected by category name.

### Induction

`solver/induce.py` runs Popper once on BK + exs + bias. Example program (copy a bound input block):

```prolog
out_block(V0, V1, V2, V3, V4) :-
    bind(V0, V1, V5),
    block(V0, V5, V3, V4),
    s0(V2).
```

English: “Paint the bound input block at offset 0 with its own length and color.”

### Verification (acceptance gate)

Object programs must **paint-verify** on train (`solver/verify.py`):

1. Consult train BK + program.
2. Collect true `out_block` atoms.
3. Paint using `block_geometry`.
4. Require exact match to every training output grid.

Failure → `fallback_identity` (usually copy the test input) with a `failure_reason` such as `paint_verify_failed`.

### Decode test

Same painting on `test_bk.pl` (`solver/decode.py`) → predicted pixel row. Level on success: `object_ilp`.

---

## Pixel road (when the census fails)

Used by the mismatch branch of `solve_hybrid`. Goal: learn a Decom-style rule that assigns an **output color to each position**.

### Encoding

**Code:** `solver/pixel_encode.py` (`encode_pixel_instance`).

Writes Decom-faithful artifacts under the work dir, including:

- Pixel BK: `in(Example, Position, Color)`, `empty(...)`, arithmetic helpers from the Decom templates.
- Learning examples for head **`out(Example, Position, Color)`** (nonzero gold positives; generated negatives).
- Pixel bias with `head_pred(out,3)`.

Positions and colors are the native language—no requirement that output run counts match input.

### Induction

Popper runs with a pixel literal budget (`PIXEL_MAX_LITERALS = 40` in `pipeline.py`). Functional/paint settings follow the pixel path (not the object paint-verify gate).

### Acceptance and scoring

On the pixel road, **soft scoring against Decom-style test facts** is the primary success signal (aligned with Decom’s `do_test_ex` mindset). Paint-verify is **not** the sole gate: a program can still count as solved when the soft matrix says so even if a separate paint check would disagree.

The predicted grid is produced by applying the program (`apply_pixel_program` in `decode.py`). Level on success: `pixel_ilp`. Detail includes `road: pixel` and often `decom_solved`.

---

## Modes (how you select a path)

| Mode | Function | When to use |
|------|----------|-------------|
| `hybrid_census` (default) | `solve_hybrid` | Headline system / paper claim |
| `block_primary` | `solve` only | Object-only ablation or debugging |

CLI:

```bash
python -m solver.cli TASK.json --mode hybrid_census --timeout 600
python -m solver.cli TASK.json --mode block_primary --timeout 600
```

Harness / eval scripts take the same mode names.

---

## Scoring (both roads)

After a prediction exists:

- **Exact** — predicted test row equals gold cell-for-cell.
- **Soft accuracy** — `(TP + TN) / (TP + FN + TN + FP)` over each `pos`/`neg` `out` label in `test.pl` (Decom-compatible; `solver/paper_score.py`). Near-misses can be high due to TN inflation; do not confuse with pixel Hamming or with pre-`per_label_out_v1` soft (which matched exact).

Pixel-level gold in `test.pl` is for **scoring**, not for teaching the object learner.

---

## Design constraints (what we still refuse)

These remain out of bounds for the scientific claim:

- **No category-named bias or BK switches** (`1d_mirror` → special vocabulary).
- **No answer-leaking BK** (precomputed correct `out_block` / mirrored answers as “facts”).
- **No marker / reflect geometry hacks** that encode the transform instead of neutral relations.
- **Do not report pixel-road solves as “block-only wins.”** Tag and discuss them as the pixel road.

The hybrid **does** use pixel ILP when the census fails—that is intentional and must be described honestly.

---

## Known limitations

### Census is a heuristic

Equal bulky/unit counts do not guarantee the object encoding can express the rule; unequal counts do not guarantee pixel ILP will finish in time. The census is a cheap geometry gate, not an oracle.

### Non-monotonic search at long timeouts

Popper’s timeout is a search budget. It may replace an early good program with a later compressed one that verifies or generalizes worse. Shorter budgets can occasionally look better than longer ones for that reason.

### Object anchoring

The object head paints **from input blocks**. Tasks that invent many new runs (classic `pcopy`-style duplication) are exactly why the pixel road exists.

---

## Where to look in the code

| File | Role |
|------|------|
| `solver/census.py` | Bulky/unit counts; `census_match` |
| `solver/pipeline.py` | `solve`, `solve_hybrid` orchestration |
| `solver/encoder.py` | Object BK / exs / geometry |
| `solver/bias_gen.py` | Mechanical object bias |
| `solver/pixel_encode.py` | Pixel BK / exs / bias |
| `solver/induce.py` | Popper child process |
| `solver/verify.py` | Object paint-verify |
| `solver/decode.py` | Object and pixel application |
| `solver/cli.py` / `harness.py` | `--mode` entry points |
