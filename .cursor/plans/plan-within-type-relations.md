# Plan: Within-type cardinal/ordinal relations (stepwise spec S1–S5)

**Status:** PROPOSED — awaiting approval per `plan-approval-gate.mdc`. Do not implement before explicit go-ahead.
**Implementation branch (on approval):** `cursor/within-type-relations-ebb2`
**Direction constraint:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit only; no category/name gating; no answer-leaking BK.

## 1. Context and frozen baseline

Eval on `main @ ee81f5f` (`block_primary`, timeout 120 s, trials `0,1,2` = first 3 per
category, JOBS=2, dataset `raw_data/onedarcraw/dataset`):

- **Exact: 38/54 (0.704)**, soft 0.704 ± 0.063 SEM
- 11 perfect categories / 3 partial / 4 fail
- Hard fails: `1d_flip` 0/3, `1d_hollow` 0/3, `1d_pcopy_1c` 0/3, `1d_pcopy_mc` 0/3
- Failure reasons: `paint_verify_failed` ×14, `decode_error` ×1, unlabeled ×1
- Artifacts: `results/eval_main_120s_j2_t012/` (`FULL_REPORT.md`, `block_primary/summary.json`; gitignored)

## 2. Root-cause summary (analysis behind this spec)

Role typing isolates `value(v*)/position(p*)/size(s*)/block_id(b*)/rank(r*)`
(`solver/encoder.py:78-95`, roles documented in `solver/predicates.py:3-8`), but on the
block-primary (lean) path:

1. **Cardinal×cardinal comparative relations are missing at runtime.** `size_lt`
   (`encoder.py:359-364`), `shorter/longer/same_len` (`encoder.py:258-270`) are emitted only
   on the non-lean path and are absent from `OBJECT_BODY_ALLOWLIST`
   (`solver/predicates.py:123-138`). `size_add` exists but sparse (obj_succ pairs + `(1,L-1,L)`
   closure only, `encoder.py:281-305`). The only "comparison" the learner sees is precomputed
   aggregation (`largest`/`non_largest`).
2. **Ordinal×ordinal relations are nearly absent in lean.** Positions: nothing (`my_succ`,
   `lt`, `add`, `offset_pos`, `from_right`, `mirror_index` all non-lean/cell-gated).
   Block ids: only `obj_succ`/`obj_pair`. Ranks: nothing.
3. **Consequence per failing family:**
   - `1d_hollow` — rule is *expressible in principle* (L−1 closure + `size_add` in bias);
     failure is search-convergence under multi-clause + large neg set + 120 s.
   - `1d_flip` — genuinely inexpressible (needs ordinal reversal / position arithmetic).
   - `1d_pcopy_1c/mc` — genuinely inexpressible (true rule: expand each unit to largest-block
     length anchored at own start−1; needs cardinal equality with `largest` + position offset).

## 3. Steps (priority order; one knob per commit)

### S1 — Within-type cardinal relations (highest priority)

**Gap:** no comparative relation between two same-type cardinals at runtime.

Changes:
- `solver/predicates.py`: add `size_lt` to `OBJECT_BODY_ALLOWLIST`; extend its
  `ladder_levels` to include 4.
- `solver/encoder.py`: emit `size_lt(a,b)` over observed sizes on the lean path (move the
  existing non-lean closure at `:359-364` to shared emission).
- `solver/encoder.py`: make `size_add` a dense uniform closure over observed sizes
  (all `a+b<=w`), replacing the sparse emission at `:281-305`.
- `solver/tests/test_encoder.py`: update lean-emit assertions.

Targets: `1d_hollow`, `1d_pcopy_*`; mild help elsewhere.
Rule check: uniform emission from observed sizes only ("generic arith sugar" — allowed);
no category switches; no answer-leaking BK.
Validation: `pytest solver/tests`; `scripts/smoke_solver.sh`; 54-task slice (120 s, JOBS=2,
trials `0,1,2`) → soft gate per `.cursor/rules/soft-eval-regression.mdc` (prefer exact ≥ 40/54
and multi-category gains; partial 3→2 OK if gains dominate; reject net loss without gains
or any 3/3 → 0/3); else revert the commit.

### S2 — Ordinal structure on `block_id`

**Gap:** block ids have only `obj_succ`/`obj_pair`; no order, no inverse, no equality.

Changes:
- `solver/encoder.py`: emit `left_of(E,Bi,Bj)` for colored block pairs on the lean path
  (exists non-lean at `:307-312`); add `left_of` to the allowlist.
- Emit `obj_pred(E,A,B)` as the uniform mechanical inverse of `obj_succ`.
- Tests updated accordingly.

Targets: `1d_flip` (ordering prerequisite), clause economy in move families.
Rule check / validation: same soft gate as S1 (`.cursor/rules/soft-eval-regression.mdc`).

### S3 — Rank/ordinal arithmetic (conditional)

Run only if S2 shows `1d_flip` order-expressible but not rank-computable.

- Emit `len_rank`/`obj_index` on the lean path + allowlist; uniform rank-successor sugar
  over observed ranks.
- Isolated A/B; revert if it costs timeouts in move families.

### S4 — Position↔size bridge (FLAGGED — requires explicit written confirmation)

The cardinal-as-ordinal wall. Minimal compliant form: emit generic `offset_pos(p,s,p)`
and/or `from_right` on the lean path (generic arithmetic already in inventory — NOT the
refused marker/reflect_block family: no `marker_block`, `unit_block`, `reflect_pos`,
`reflect_end`, `block_marker_gap`, `between_block_marker`, `same_side_marker`,
`opp_side_marker`).
Per `block-level-only.mdc` this step is planned in detail only after the user confirms this
specific bridge family in writing. Only step that can fully unlock `1d_flip`; may enable the
true `1d_pcopy_*` rule.

### S5 — Budget knobs (last resort, one at a time)

- `max_clauses 3→4` (hollow/pcopy need ≥2 output blocks per input block), then
  `max_body 6→7`, then timeout 120→180. Uniform, not category-gated.
- Updates `OBJECT_MAX_LITERALS`; adjust `solver/tests/test_failure_reason.py` (asserts 21)
  and `solver/tests/test_encoder.py`.
- Only after S1–S4: bigger budgets mask expressibility fixes and inflate runtime everywhere.

## 4. Cross-cutting protocol (every step)

- [ ] Clean tree check (`git status`) before starting; branch from `main`.
- [ ] One knob per commit; commit message names the knob and carries the attestation:
      "uniform mechanical emit; no category/name gating; no answer-leaking BK."
- [ ] Per-step artifacts: `results/eval_sN/` with `summary.json` + `FULL_REPORT.md`;
      maintain a comparison table vs frozen baseline.
- [ ] Soft acceptance gate (`.cursor/rules/soft-eval-regression.mdc`): net exact / multi-category
      fail-family gains outweigh regressions; partial 3→2 OK; reject 3→0 wipe or net loss
      without gains. Soft rule wins over older “zero perfect regressions” wording.
- [ ] Tests: `pytest solver/tests` green; smoke scripts pass before each commit.
- [ ] SPEC sync (`spec-sync.mdc`): S1/S2/S4 change documented BK/bias vocabulary → ask
      before editing any `spec/` file; edit only the smallest relevant file; update root
      `SPEC.md` index only if titles/files change.

## 5. Non-goals (per `block-level-only.mdc`, refused without separate explicit confirmation)

- Marker/mirror geometry hacks (`marker_block`, `unit_block`, `reflect_pos`, `reflect_end`,
  `block_marker_gap`, `between_block_marker`, `same_side_marker`, `opp_side_marker`).
- Category/task-name switches on bias, BK, or exs shape; per-family pipeline stages.
- Pixel-head rescue ladders, hybrid pixel/block heads, trivial closed-form solvers.
- Answer-leaking BK (precomputed correct `out_block` etc.).

## 6. Open questions for approval

- [ ] Approve S1 (start)? Code+tests only, or include `spec/` update in the same step?
- [ ] Confirm S4 bridge family now, or defer the decision until S1–S3 results are in?
