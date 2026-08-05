# Plan: S2v2 obj_pred + S5d sparse doubling (from updated main)

**Status:** S2v2 FAILED and reverted; S5d not started (plan says stop if S2v2 fails).
**Base:** `main @ 64393f2` (includes S1′a `size_lt` + S1′b `cardinal_ordinal`; baseline **39/54** exact, 11/11 perfect).
**Branch:** `cursor/obj-pred-doubling-ebb2`
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit only; no category/name gating; no answer-leaking BK; no S4 marker/reflect hacks.

## Frozen baseline (do not re-run unless gate fails)

| Source | Exact | Perfect | Notes |
|---|---:|---|---|
| `main @ ee81f5f` original | 38/54 | 11/11 | pre-S1a |
| S1′a only | 38/54 | 11/11 | size_lt |
| **S1′a+S1′b (current main)** | **39/54** | **11/11** | pcopy_1c +1 |

Perfect categories (soft-gate reference — see `.cursor/rules/soft-eval-regression.mdc`):
`1d_denoising_1c, 1d_denoising_mc, 1d_fill, 1d_move_1p, 1d_move_2p, 1d_move_2p_dp, 1d_move_3p, 1d_move_dp, 1d_recolor_cmp, 1d_recolor_cnt, 1d_scale_dp`

**Soft gate:** keep if net exact improves (or flat with multi-category fail-family gains)
and no previously 3/3 category goes to 0/3. Partial 3→2 drops are acceptable when gains dominate.

---

## Step status tracker

| Step | Status | Commit | Exact | Perfect | Gate | Notes |
|---|---|---|---|---|---|---|
| S2v2 `obj_pred` only | ❌ REVERTED | `bf1c1af` | 36/54 | 9/11 | FAIL | regressed `recolor_cnt`+`scale_dp`; lost `pcopy_1c` |
| S5d `size_add(L,L,2L)` | ⏭️ BLOCKED | — | — | — | — | plan: stop if S2v2 fails; ask to run alone? |
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
4. **Accept (soft gate — `.cursor/rules/soft-eval-regression.mdc`):**
   - Prefer exact ≥ 39/54 with multi-category gains on fail families
   - Partial perfect-cat drops (e.g. 3→2) OK if net exact rises / gains dominate
   - Reject if net exact falls with no fail-family gains, or any 3/3 → 0/3
5. Prefer exact ≥ 40; document category tradeoffs in the plan tracker
6. **If fail soft gate:** `git revert HEAD`, push, mark ❌; S5d may still run alone if user confirms
7. **If pass soft gate:** mark ✅, push, proceed to S5d (or ask if S2v2 was marginal)

### Results (2026-08-05)
- Exact: **36/54** | Perfect: **9/11** | Gains: none | Regressions: `1d_recolor_cnt` 3→2, `1d_scale_dp` 3→2, `1d_pcopy_1c` 1→0
- Gate: **FAIL** → action: **reverted** (`bf1c1af`)
- Note: `obj_pred` alone still hurt search (same failure mode as full S2, without `left_of`)

---

## S5d — sparse doubling `size_add(L, L, 2L)`

**Status:** BLOCKED by this plan’s “stop if S2v2 fails” rule (see tracker). Spec retained below if user authorizes running S5d alone.

### Why
`1d_pcopy_*` needs second copy at `Off = Len` / length `2·L`. Sparse `size_add` today only emits succession pairs + `size_add(1,L-1,L)`. Missing uniform `size_add(L,L,2L)` for each observed colored length (when `2L ≤ width`).

### Why not dense size_add
S1 dense closure caused 5–12× BK growth and 19/54 collapse. Doubling is **one fact per observed L**, same sparsity class as the existing predecessor closure.

### Changes (exact) — only after S2v2 kept, or alone if user confirms
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
Accept (soft gate — `.cursor/rules/soft-eval-regression.mdc`):
net exact improves (or flat with multi-category fail-family gains); no 3/3→0/3 wipe.
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

## Current next action for an agent resuming this plan

1. S2v2 is reverted — do **not** re-implement without a new design.
2. S5d was blocked by this plan’s “stop if S2v2 fails” rule.
3. To continue toward failed categories: ask user whether to run **S5d alone** from current HEAD (S1′a+S1′b, no `obj_pred`).
