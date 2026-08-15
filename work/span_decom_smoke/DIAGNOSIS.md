# Span-decom smoke diagnosis (120s sequential)

Live report for `.venv/bin/python work/span_decom_smoke/smoke.py 120`
on `f2ca01f` (`cursor/index-in-out-blocks`). Sequential only (`jobs=1`).

**Final (54/54, finished 2026-08-15 05:02Z, ~108 min):** train exact **6/54**, test exact **3/54**.
Only `1d_flip` is 3/3 test. Train-only: `1d_move_1p_2`, `1d_recolor_oe_1`, `1d_recolor_oe_2`.

This is **not** an infra 0/54 collapse (that was the earlier `jobs=2` Pool daemon bug).
Induce is running; almost every `status=ok` at ~120.3s is a **timeout leftover**.

---

## Verdict in one paragraph

Surface fail is almost always `decode:width` after a leftover program that
**under-generates** `out_block` atoms. Leftover marked `ok` is a reporting
hole. `missing_head` staying out of `non_functional` is **intentional**
(flip partials); do not “fix” it.

Under that, the language cannot say the real transform for most families:

- **BK gaps** dominate when the output run *count* or *role* changes
  (denoise / fill / hollow / padded_fill / pcopy / mirror / recolor).
- **Bias barriers** dominate when the geometry is already in the language
  (move / scale length arithmetic) but search cannot assemble a full, general
  program in 3 clauses with “one `succ` **or** one `add`, not both”.

More timeout alone will not lift pcopy / mirror / recolor / denoise.

---

## Shared machinery (every leftover fail)

### 1. Timeout leftover is reported as `ok`

`solver/induce.py` worker ignores Popper’s `_terminated` flag:

```python
prog, _terminated = learn_solution(settings)
if prog:
    q.put(("ok", prog, None))
```

If the child exits after ~120s with any `prog`, smoke prints `ok`.
These are **not** solutions. Typical leftover: 1–3 clauses that copy
`in_block` plus a constant (`n14(V2)`, `n0(V1)`).

### 2. Functional checker allows missing heads (keep it that way)

Smoke BK defines `missing_head` but does **not** wire it into `non_functional`
(only `dup_bid` and `extra_head`). That is how flip survives: a 1- or 2-clause
partial under-generates and must stay legal. Completeness is checked at
decode, not inside Popper. Do not add `non_functional :- missing_head`.

### 3. Independent in/out bid numbering

Bids are left-to-right run indices, numbered **separately** on input vs output.
Identity `out_block(E,B,L,C) :- in_block(E,B,L,C)` is only correct when
run **count and alignment** stay the same. Denoise / fill / hollow / pcopy
change the number of runs; leftover “copy bid 0 / copy length 14” cannot
rebuild the output tape.

### 4. Decode is a tape concat

`paint()` walks bids `0..max_bid` and concatenates lengths. Partial coverage
is a width error, not a soft near-miss.

---

## Shared bias barriers (all tasks)

From `work/span_decom_smoke/smoke.py` `_bias()`:

| Barrier | Effect |
|---|---|
| `max_clauses(3)` / `max_body(6)` / `max_vars(10)` | Multi-object move, hollow (shell\|hole\|shell), pcopy tiling need more structure |
| every clause **must** contain `in_block` | Cannot emit a brand-new out run from arith / constants alone |
| bid (V1) must appear via `in_block` 2nd arg or `succ`/`add`/`in_succ`/`in_col_succ` | New out bids that are not an input bid or ±1 are hard |
| **at most one** `succ`, **at most one** `add`, **not both** | Move/scale often need `succ` on one length **and** `add` on another |
| `bad_body`: `add`/`succ` only on head vars 1 or 2 (bid/len) | Cannot arith on a helper length then copy color |
| all of V1, V2, V3 must appear in the body | Forces every clause to mention bid, len, and color somehow |

These barriers are **uniform** (not category-gated). They are still a search
ceiling for families whose true rule needs more than 3 clauses or both
`succ` and `add`.

---

## What the BK actually has

Input-only: `in_block/4`, `empty/2`, `in_succ/3`, `in_col_succ/3`, `in_pair/3`,
`succ/2`, `add/3` (bids + lengths, not a pixel ruler), `size_lt/2`.
Novel colors `vK` from train-out − train-in. Train output is checker-only.

**Not present** (main `block_primary` object BK has several of these):

`largest` / `non_largest`, `size_even` / `size_odd`, `gap`, `obj_succ`,
`component_start`, any count/compare-on-color, any interior/hole, any
reflect/marker (and those stay refused without a dedicated confirm).

---

## Why `1d_flip` is 3/3

Same run count. Transform is a **permutation of existing input runs**:

```
out_block(V0,V1,V2,V3):- in_block(V0,V4,V2,V3), in_col_succ(V0,V1,V4).
out_block(V0,V1,V2,V3):- in_block(V0,V1,V2,V3), empty(V0,V1).
out_block(V0,V1,V2,V3):- in_block(V0,V4,V2,V3), in_col_succ(V0,V4,V1).
```

Copy empties; swap adjacent colored runs via `in_col_succ`. Fits 3 clauses,
no new bids, no length arith, no novel color. This is the language’s sweet spot.

---

## Family diagnoses (49 done)

Surface bucket (54): **~44 leftover decode-width**, **3 pass**,
**3 train-ok / test-fail** (`move_1p_2` decode, `oe_1` mismatch, `oe_2` decode).

### Denoise (`1d_denoising_1c`, `1d_denoising_mc`) — 0/6 test

| task | fail | leftover |
|---|---|---|
| `1d_denoising_1c_0` | width 0 0!=32 | `in_block, n14(V2)` |
| `1d_denoising_1c_1` | width 0 0!=32 | `n13(V2), in_block` |
| `1d_denoising_1c_2` | width 0 15!=32 | `in_block, n15(V2)` |
| `1d_denoising_mc_0` | width 0 4!=32 | copy len=7 + copy empties |
| `1d_denoising_mc_1` | width 0 5!=32 | copy bid 0 + `add` shift |
| `1d_denoising_mc_2` | width 0 2!=32 | copy bid 0 |

Train in-runs 5–13 → out-runs 2–3. Need **merge singleton noise into the
neighbor blob**. Missing BK: `largest` / `non_largest` (or equivalent size
role). Cannot invent fewer out bids from `in_block` identity. **BK gap
(agg/role)**, not a missing `succ`.

### Fill / hollow / padded_fill — 0/9 test

Fill train is always 5 in-runs → 3 out-runs (hole disappears).
Hollow is 3 → 5 (shell \| hole \| shell). Padded fill also changes run count.

Leftovers copy bid 0 / a constant length. No interior/hole predicate; no way
to split one colored run into three out runs without leaking the answer.
**BK gap (interior geometry)**. `max_clauses(3)` is a second ceiling for hollow.

### Mirror — 0/3 test

`1d_mirror_1` even has the flip-shaped leftover (`in_col_succ` both ways +
`succ(V2,V1)`) and still width 6!=18. Reflection is not adjacent-swap.
No reflect-bid / opposite-side relation. **BK gap**. Do **not** add
`marker_block` / `reflect_pos` without a dedicated confirm
(`block-level-only.mdc`).

### Move family — 1/15 train, 0/15 test

Closest: `1d_move_1p_2` train-exact, test `width 3 25!=30`.

```
out_block(V0,V1,V2,V3):- in_block(V0,V1,V6,V3), add(V5,V2,V6), in_succ(V4,V5,V1).
out_block(V0,V1,V2,V3):- in_block(V0,V1,V4,V3), n0(V1), succ(V4,V2).
```

Train is a +1 right shift (left empty grows, right empty shrinks). The
leftover overfits train lengths / a broken `in_succ` typing
(`in_succ(V4,V5,V1)` uses V4 as `ex`). Test grid is 30 wide; paint emits 25.

`1d_move_1p_1` is the same idea (succ ±1 on bids 0 and 2, copy bid 1) but
only paints 7/30 — leftover incomplete.

Other move tasks: two/three objects or a pointer. Need per-object empty
arith **and** both `succ` and `add`, often >3 clauses. Pointer role is
absent. **Bias + missing pointer/role BK**, not “no `add`”.

### Periodic copy — 0/6 test

`1d_pcopy_1c_0` input has a motif plus singleton seeds; output expands each
seed to the motif (more colored runs). Leftover tries `in_col_succ` copy
and `n0(V1)`. Cannot tile a template onto new bids. Every clause must
contain `in_block`, so you cannot *emit* a new run that is not already an
input run. **BK + bias (tiling / new-run invention)**.

### Recolor cmp / cnt / oe — 2/9 train, 0/9 test

Same run count (geometry identity). Need a **new color** from comparison,
count, or even/odd. Leftovers guess `v1`/`v8` with bid/len constants.

Missing: color-compare, count/agg, `size_even` / `size_odd`.
`vK` constants exist but there is no *condition* that selects which object
gets which novel color. **BK gap (recolor predicates)**. Bias is secondary
(3 clauses would be enough *if* the condition pred existed).

`1d_recolor_oe_0` leftover under-generated (`width 18!=20`).
`oe_1` / `oe_2` finished after this section was first written — see Incoming.

---

## Incoming (last five, now complete)

### `1d_recolor_oe_1` — train exact, `test_mismatch`

Gold rule is even-length blob → 9, odd-length → 7 (all input color 2).

Leftover that paints train:

```
out_block(V0,V1,V2,V3):- in_block(V0,V1,V2,V4), v9(V3), n1(V1).
out_block(V0,V1,V2,V3):- v7(V3), in_block(V0,V1,V2,V5), in_col_succ(V4,V6,V1).
out_block(V0,V1,V2,V3):- in_block(V0,V1,V2,V3), empty(V0,V1).
```

Train always puts the even object at **bid 1**. Test’s last blob is even
length 2 but not bid 1 → program paints 7, gold is 9. **BK gap:
`size_even` / `size_odd`**. Not a decode hole. Proves 3 clauses are enough
once the condition exists; the leftover overfit bid identity.

### `1d_recolor_oe_2` — train exact, `test_decode:width 3 28!=29`

Same even→8 / odd→5 rule. Leftover:

```
out_block(..., n1(V1), v8(V3)).      # bid 1 → 8
out_block(..., n4(V2), v8(V3)).      # length 4 → 8
out_block(..., v5(V3), in_col_succ(...)).
out_block(..., n9(V1), v8(V3)).
out_block(..., empty(V0,V1)).
```

Overfit bid/length constants. Test singleton (odd, length 1) is not
covered → 28/29 px. Same **BK gap (even/odd)**.

### `1d_scale_dp_0` — leftover undergen `width 0 0!=25`

Pointer color 3; the other blob grows through the empty gap toward the
pointer (not a uniform `*2`). Leftover: `n4(V2), in_block` and
`succ(V1,V2), in_block` — paints nothing useful.

Need: identify pointer vs object, take the empty-run length between them,
`add(obj_len, gap, new_len)`. `add` exists but there is no pointer/role
pred; bias also forbids `succ` and `add` in the same clause.
**BK gap (pointer/gap) + bias.**

### `1d_scale_dp_1` — leftover partial `width 2!=30`

Same grow-to-pointer pattern (pointer color 2). Leftover copies bid 0
plus a `succ`/`in_pair` fragment. Same root as `_0`.

### `1d_scale_dp_2` — leftover partial `width 15!=30`

```
out_block(..., n0(V1)).
out_block(..., in_col_succ(...), in_block(...)).
out_block(..., add(V1,V2,V4)).
```

Copies the leading empty; does not grow the object by the gap. Same root.

---

## Final family table

| family | train | test | root |
|---|---|---|---|
| `1d_flip` | 3/3 | 3/3 | language fit (`in_col_succ` swap) |
| `1d_recolor_oe` | 2/3 | 0/3 | BK: even/odd; oe_1/2 overfit bid |
| `1d_move_1p` | 1/3 | 0/3 | bias/arith leftover; test width |
| `1d_denoising_*` | 0/6 | 0/6 | BK: largest / merge |
| `1d_fill` / `hollow` / `padded_fill` | 0/9 | 0/9 | BK: interior / run-count change |
| `1d_mirror` | 0/3 | 0/3 | BK: reflect (no marker hack) |
| other `1d_move_*` | 0/12 | 0/12 | bias + pointer/role |
| `1d_pcopy_*` | 0/6 | 0/6 | BK+bias: cannot invent tiled runs |
| `1d_recolor_cmp` / `cnt` | 0/6 | 0/6 | BK: compare / count |
| `1d_scale_dp` | 0/3 | 0/3 | BK: pointer/gap + succ+add ban |

---

## What this is / is not

- **Not** a capability regression vs the main `block_primary` 40/54 @60s gate.
  Different language (index-only smoke vs object-head solver).
- **Not** “Popper found nothing”. It found leftover fragments because
  under-generation is legal and leftovers are labeled `ok`.
- **Not** fixed by another 120s. Flip already fits; the rest are language
  limits, not a missing `largest` / `size_even` label.

## Suggestions (rewritten again)

**Not implementing** `size_even`, `size_odd`, `largest`, `non_largest`,
or any other family-decision pred. The earlier “even is `add(K,K,L)`”
line was wrong as a reason to skip *or* to add parity: smoke `add`/`succ`
are pinned to head bid/len (`num` smashed together, then `bad_body` on
V1/V2). That is not “cardinal arith on all cardinals.”

### Do now (reporting only; no language change)

1. Report leftover as `timeout` (`_terminated`). Do not call it `ok`.
2. Leave `missing_head` out of `non_functional` (flip partials).

### Acceptable language (if later approved — not this turn)

Simple arith, same ops for every domain of that kind. Mixing cardinal
and ordinal is **allowed**, with one constraint: do not dump a large
cardinal/pixel ruler into the **ordinal (bid) domain**. Bids are a small
line; inflating that set makes search explode.

| kind | domains | ops |
|---|---|---|
| ordinal | bid (keep this set small), also position/rank if used | bidirectional `my_succ` (walk either way; reverse order is this, not a reflect pred). `lt` optional |
| cardinal | length, gap width, count-as-a-number | `add` is the useful op. `lt`/`gt` are fine. `my_succ` is meaningful (+1) but secondary to `add` |

Parity, if it exists at all, is `add(K,K,L)` on **cardinal** add after
that add is grounded on cardinal values — not `size_even`, and not add
locked only to a size/index head slot as a substitute for a parity pred.

Colors stay `value` (categorical).

Smoke today: one `num` for bid and len, then `bad_body` pinning
`add`/`succ` to V1/V2. Mixing is not the bug; **blowing up bid** and
**special-case head-slot arith** are. Bidirectional `my_succ` is what
makes reverse-on-ordinal automatic; do not add `reflect_*`.

### Still refuse

`missing_head` in `non_functional`; `largest` / `size_even` / `color_lt`
/ `color_count` / pointer role / marker-mirror / category-gated bias /
pixel rescue / longer timeout as a capability result.
