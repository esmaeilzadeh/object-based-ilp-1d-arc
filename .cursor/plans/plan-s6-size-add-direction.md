# Plan: S6 — bidirectional size_add / size_sum3 bias (flip unlock)

**Status:** APPROVED for implementation (user: plan stepwise then implement + eval).
**Base:** `main @ 64393f2` + soft-eval docs from `cursor/obj-pred-doubling-ebb2` tip.
**Branch:** `cursor/s6-size-add-direction-ebb2`
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical language only; no category/name gating; no answer-leaking BK; no marker/reflect hacks.
**Gate rule:** `.cursor/rules/soft-eval-regression.mdc`

## Frozen baseline

| Source | Exact | Perfect | Notes |
|---|---:|---|---|
| **S1′a+S1′b (current main)** | **39/54** | **11/11** | `1d_pcopy_1c` +1; flip/hollow still 0/3 |

Perfect cats (soft-gate reference):
`1d_denoising_1c, 1d_denoising_mc, 1d_fill, 1d_move_1p, 1d_move_2p, 1d_move_2p_dp, 1d_move_3p, 1d_move_dp, 1d_recolor_cmp, 1d_recolor_cnt, 1d_scale_dp`

Fail families of interest: `1d_flip` 0/3, `1d_hollow` 0/3, `1d_pcopy_*` partial.

## Diagnosis (do not re-derive)

1. Hand-written 2-clause flip swap using only current BK (`block`, `obj_succ`, `size_add(La,Off,Lb)`, `s0`) paint-verifies all train pairs and decodes **exactly** on all 3 flip tests.
2. Bias currently has:
   ```
   bad_body(size_add, Vars):- vars(_, Vars), Vars = (_,_,R), R != 2, R != 3.
   ```
   This allows **compute** direction only (`C = A+B` with `C` = head Off/Len) and **bans check** direction (`A+B=C` with head Off as an *input* arg). Clause 2 of the true flip program is pruned before search.
3. Same form unlocks hollow (`Off = L−1` via `size_add(s1,Off,L)`).
4. 120s junk programs are timeout best-effort (already fail paint-verify / cover no pos). More negs cannot help until the truth is reachable. 600s can find train-consistent overfits; that is a separate later lever.

**Not a hack:** S6 removes an arbitrary designer restriction on a generic 3-place arithmetic relation. No new predicates, no new BK, no category gating, nothing from the refused marker/reflect list.

## Soft gate (per step)

1. Prefer net exact ≥ 39/54 with fail-family gains (`flip`/`hollow`/`pcopy`).
2. Partial perfect drops (3→2) OK if gains dominate.
3. Reject: net exact falls with no fail-family gains, or any 3/3 → 0/3.
4. Report Δ exact, per-category Δ, soft-gate KEEP / REVERT.

---

## Step status tracker

| Step | Status | Commit | Exact | Perfect | Gate | Notes |
|---|---|---|---|---|---|---|
| S6a plan file | ✅ | `d50f09f` | — | — | — | this file |
| S6b bias direction + tests | ✅ | `40c5e2a` | — | — | — | bidirectional size_add/size_sum3 |
| S6c flip smoke (3 trials, 120s) | ✅ | — | **3/3** | — | PASS | t0+t2 pipeline exact; t1 SIGSEGV after induce, offline exact |
| S6d full 54-task soft gate | ✅ | — | **39/54** | 8/11 | **KEEP** | flip+hollow 0→3; see results below |

---

## S6a — Plan commit

Write this runbook; commit alone.

---

## S6b — Bidirectional arithmetic bias (the code change)

### Exact change

1. `solver/bias_gen.py` — replace result-only guard with “any arg may be head Off/Len”:

   **Before:**
   ```prolog
   bad_body(size_add, Vars):- vars(_, Vars), Vars = (_,_,R), R != 2, R != 3.
   bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (_,_,_,R), R != 2, R != 3.
   ```

   **After:**
   ```prolog
   % Legal iff at least one of A,B,R is head Off (var 2) or Len (var 3).
   % Allows compute (R ∈ {2,3}) and check (A or B ∈ {2,3}) directions.
   bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R),
     A != 2, A != 3, B != 2, B != 3, R != 2, R != 3.
   bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R),
     A != 2, A != 3, B != 2, B != 3, C != 2, C != 3, R != 2, R != 3.
   ```

2. `python -m solver.bias_gen` → update `solver/bias/object.pl` to match.

3. `solver/tests/test_encoder.py` — assert rendered bias contains the new `bad_body(size_add` form (any-arg) and does **not** contain the old `Vars = (_,_,R), R != 2, R != 3` form.

4. `pytest solver/tests -q` must pass.

5. Commit:
   `feat(solver): S6 bidirectional size_add/size_sum3 bias (check+compute)`
   attestation: `uniform mechanical emit; no category/name gating; no answer-leaking BK.`

### What we deliberately do **not** change in S6

- No new BK facts / predicates
- No `obj_pred` / `left_of` (S2v2 already failed soft gate)
- No S5d doubling (separate authorization)
- No “head Color must be body-bound” constraint (own later step; recolor risk)
- No SPEC edit without separate confirmation (`spec-sync.mdc`)

---

## S6c — Flip smoke (mandatory before full sweep)

```bash
OUT=results/eval_s6_flip JOBS=1 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
# restrict to 1d_flip only if script supports a filter; else run three files via pipeline.solve
```

Accept to proceed to S6d if **any** of:

- ≥1/3 flip exact, or
- any flip trial `verified_train=True` with a non-overfit program shape (uses `size_add` check-direction / no hardcoded `vK` color), or
- clear induction progress vs baseline (baseline: all 3 `paint_verify_failed` @ ~120s with gap-as-Off junk)

If flip smoke shows **no** progress (still 0/3, same junk, no check-direction programs), **stop**, report, do **not** burn a full 54-task run unless user insists.

---

## S6d — Full 54-task soft gate

```bash
OUT=results/eval_s6 JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

Compare vs frozen baseline 39/54 / 11 perfect. Soft-gate KEEP or `git revert` S6b commit. Update this tracker + push.

### Results (2026-08-05)

| Metric | Baseline (S1′b) | S6 | Δ |
|---|---:|---:|---:|
| Exact | 39/54 | **39/54** | 0 |
| Perfect cats | 11/11 | 8/11 | −3 partial |

**Gains (fail families):**
- `1d_flip` 0/3 → **3/3** (+3) — check-direction `size_add(Len,Off,ownLen)` / `size_sum3`
- `1d_hollow` 0/3 → **3/3** (+3)

**Regressions:**
- `1d_move_dp` 3/3 → 1/3 (−2) — perfect drop (not wipe)
- `1d_recolor_cnt` 3/3 → 2/3 (−1)
- `1d_scale_dp` 3/3 → 2/3 (−1)
- `1d_padded_fill` 2/3 → 1/3 (−1)
- `1d_pcopy_1c` 1/3 → 0/3 (−1)

**Soft gate: KEEP** — net exact flat; multi-category unlock of two hard fails (+6); no 3→0 wipe. Document `move_dp` 3→1 as the main trade for follow-up.

`1d_flip_1` pipeline SIGSEGV after induce (known janus flake); offline train_verify + test_decode exact — counted as exact.

---

## S6e — Full 54-task @ 600s (10 min)

```bash
OUT=results/eval_s6_600s JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 600 0,1,2
```

### Results (2026-08-06)

| Metric | S1′b (120s) | S6 @120s | **S6 @600s** |
|---|---:|---:|---:|
| Exact | 39/54 | 39/54 | **41/54** |
| Soft | — | — | 0.759 ± 0.059 |
| Perfect cats | 11/11 | 8/11 | **9/11** |

**Unlocks / gains vs S1′b:** flip +3, hollow +3, pcopy_mc +1  
**Extra vs S6@120:** pcopy_mc +1, scale_dp 2→3 (+1)  
**Still regressed:** move_dp 3→1, recolor_cnt 3→2, padded_fill 2→1, pcopy_1c 1→0  
**SIGSEGV recoveries (offline):** flip_1 exact; pcopy_mc_1 exact; pcopy_mc_0 inexact

Report artifact: `results/eval_s6_600s/SUMMARY_REPORT.md` (gitignored under `results/`).

---

## Follow-ups (not in this plan — ask first)

- Investigate `1d_move_dp` 3→1 regression under bidirectional arithmetic
- S5d sparse `size_add(L,L,2L)` for pcopy
- Head-color-in-body bias (kill train-consistent `vK` overfits)
- Decode robustness (under-bound programs → `decode_error` instead of SIGSEGV)
- SPEC sync for bias policy wording
- Anytime train-paint-valid candidate retention / paint-aware induction (not implemented):
  protect shorter-time train-valid answers from being replaced by later compressed
  train-perfect programs; no test leakage. If direct ILP integration is too expensive,
  keep all train-perfect candidates, paint-verify each on train, and deterministically
  return the first/best train-paint-valid candidate.
