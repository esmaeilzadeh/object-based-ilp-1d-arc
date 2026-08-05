# Plan: S2v2 obj_pred + S5d sparse doubling (from updated main)

**Status:** APPROVED TO EXECUTE — user: plan in detail, then implement and push; start from updated `main`.
**Base:** `main @ 64393f2` (includes S1′a `size_lt` + S1′b `cardinal_ordinal`; baseline **39/54** exact, 11/11 perfect).
**Branch:** `cursor/obj-pred-doubling-ebb2`
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit only; no category/name gating; no answer-leaking BK; no S4 marker/reflect hacks.

## Frozen baseline (do not re-run unless gate fails)

| Source | Exact | Perfect | Notes |
|---|---:|---|---|
| `main @ ee81f5f` original | 38/54 | 11/11 | pre-S1a |
| S1′a only | 38/54 | 11/11 | size_lt |
| **S1′a+S1′b (current main)** | **39/54** | **11/11** | pcopy_1c +1 |

Perfect categories (must stay 3/3 after every step):
`1d_denoising_1c, 1d_denoising_mc, 1d_fill, 1d_move_1p, 1d_move_2p, 1d_move_2p_dp, 1d_move_3p, 1d_move_dp, 1d_recolor_cmp, 1d_recolor_cnt, 1d_scale_dp`

---

## Step status tracker

| Step | Status | Commit | Exact | Perfect | Gate | Notes |
|---|---|---|---|---|---|---|
| S2v2 `obj_pred` only | ⬜ TODO | — | — | — | — | next |
| S5d `size_add(L,L,2L)` | ⬜ TODO | — | — | — | — | after S2v2 |
| S1′c constraint arith | ⏭️ SKIP | — | — | — | — | not in this plan |
| S4 position bridge | ⏭️ SKIP | — | — | — | — | needs separate confirmation |

---

## S2v2 — `obj_pred` only (no `left_of`)

### Why (lesson from failed S2)
Full S2 added `left_of` (O(n²) block-id pairs) **and** `obj_pred`. Eval regressed `1d_recolor_cnt` 3→2. Diagnosis: dense `left_of` bloated search. The useful half is `obj_pred` — one fact per existing `obj_succ` edge (O(n), not O(n²)).

### Why it helps failed categories
- `1d_flip` / `1d_mirror`: reverse/order needs “block before Bid” without chaining only forward `obj_succ`.
- Clause economy: one `obj_pred(E,B,A)` vs multi-hop `obj_succ` chains.

### Changes (exact)
1. `solver/predicates.py`
   - Add `Predicate("obj_pred", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({4}))`
   - Add `"obj_pred"` to `OBJECT_BODY_ALLOWLIST`
   - **Do not** add `left_of` to allowlist / lean emit
2. `solver/encoder.py` — in the colored `obj_succ` loop (already emits `obj_succ(E,A,B)`), also emit:
   `obj_pred(E, B, A)` (uniform inverse)
3. `solver/tests/test_encoder.py`
   - Assert `obj_pred(0,b2,b0)` for `[2,2,2,0,5,5]`
   - Assert bias includes `body_pred(obj_pred,3)` when BK has `obj_pred`
   - Assert lean facts do **not** include `left_of(` for that row
4. `python -m solver.bias_gen` → update `solver/bias/object.pl`

### Gate (mandatory)
1. `pytest solver/tests -q`
2. Commit:
   `feat(solver): S2v2 lean obj_pred only (no left_of)`
   + attestation: `uniform mechanical emit; no category/name gating; no answer-leaking BK.`
3. Eval: `OUT=results/eval_s2v2 JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2`
4. **Accept iff** exact ≥ 39/54 **and** all 11 perfect stay 3/3
5. Prefer exact ≥ 40; if 39 with no perfect regressions and a clear gain on flip/mirror/pcopy, still keep (document trade)
6. **If fail:** `git revert HEAD`, push, mark ❌, stop before S5d

### Results (fill after run)
- Exact: ___/54 | Perfect: ___/11 | Gains: ___ | Regressions: ___
- Gate: PASS / FAIL → kept / reverted

---

## S5d — sparse doubling `size_add(L, L, 2L)`

### Why
`1d_pcopy_*` needs second copy at `Off = Len` / length `2·L`. Sparse `size_add` today only emits succession pairs + `size_add(1,L-1,L)`. Missing uniform `size_add(L,L,2L)` for each observed colored length (when `2L ≤ width`).

### Why not dense size_add
S1 dense closure caused 5–12× BK growth and 19/54 collapse. Doubling is **one fact per observed L**, same sparsity class as the existing predecessor closure.

### Changes (exact) — only after S2v2 kept
1. `solver/encoder.py` lean branch — after the `size_add(1, L-1, L)` loop, add:
   ```python
   if 2 * L <= w:
       facts.append(f"size_add({_sz(L, t)},{_sz(L, t)},{_sz(2 * L, t)}).")
       observed_sizes.add(2 * L)
   ```
   (still before `size_lt` / `cardinal_ordinal` so those see `2L` in the observed set)
2. `solver/tests/test_encoder.py`
   - For `[1,1,1,0]` (L=3, w=4): assert `size_add(s3,s3,s6)` **absent** (2×3=6 > 4)
   - For a wider row e.g. length-3 in width ≥6: assert `size_add(s3,s3,s6)` present
3. No allowlist change (`size_add` already listed)

### Gate (mandatory)
Same as S2v2, baseline = **post-S2v2 exact** (or 39 if S2v2 was flat).
Artifacts: `results/eval_s5d/`
Commit: `feat(solver): S5d sparse size_add(L,L,2L) doubling closure`

### Results (fill after run)
- Exact: ___/54 | Perfect: ___/11 | Gains: ___ | Regressions: ___
- Gate: PASS / FAIL → kept / reverted

---

## Protocol (every step)

- Clean tree; branch from updated `main`.
- One knob per commit; push after each commit.
- 54-task eval before declaring keep/revert.
- Update this tracker after each step.
- Ask before any `spec/` edit (`spec-sync.mdc`).
- Do **not** implement S1′c or S4 in this plan.

## Current next action

1. Create `cursor/obj-pred-doubling-ebb2` from `main`.
2. Execute **S2v2** exactly as above.
3. Gate; then **S5d** only if S2v2 kept.
4. Stop and report; do not start S1′c/S4 without confirmation.
