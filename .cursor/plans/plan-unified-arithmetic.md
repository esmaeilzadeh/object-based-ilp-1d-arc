# Plan: Unified arithmetic execution (S1′ series) — stepwise with per-step gates

**Status:** IN PROGRESS — S1′b complete and kept; S1′c deferred pending confirmation.
**Supersedes:** `plan-within-type-relations.md` steps S1–S5 for execution.
**Purpose:** Self-contained runbook. Future agents execute steps in order and update
checkboxes + results below; **do not re-derive prior analysis** — trust the recorded
outcomes and move to the next unchecked step.

**Rules:**
- `.cursor/rules/block-level-only.mdc` — uniform mechanical emit only; no category/name
  gating; no answer-leaking BK.
- `.cursor/rules/plan-implementation.mdc` — clean tree, one branch, one commit per step.
- `.cursor/rules/spec-sync.mdc` — ask before editing `spec/`; edit smallest file only.
- `.cursor/rules/soft-eval-regression.mdc` — soft balance of gains vs regressions (3→2 OK
  when gains dominate; reject 3→0 wipe or net loss without fail-family gains).

**Branch:** `cursor/unified-arithmetic-ebb2` (create from `main` or current head).
**Baseline:** `main @ ee81f5f` + S1a kept → **38/54 exact**, 11 perfect categories intact.
Baseline eval artifacts: `results/eval_main_120s_j2_t012/` (frozen) and
`results/eval_s1a/` (S1a reference).

---

## Step status tracker (edit this table as you complete each step)

| Step | Status | Commit | Exact | Perfect cats | Gate | Notes |
|---|---|---|---|---|---|---|
| S1′a size_lt only | ✅ DONE | `104e241` | 38/54 | 11/11 | PASS | flip +1, padded_fill −1; on branch `cursor/plan-within-type-relations-ebb2` |
| S1 dense size_add | ❌ REVERTED | `f8885e0` | 19/54 | 3/11 | FAIL | BK bloat 5–12× |
| S2 left_of+obj_pred | ❌ REVERTED | `2f67b28` | 38/52 | 10/11 | FAIL | recolor_cnt regression |
| S3 rank/ordinal | ⏭️ SKIPPED | — | — | — | — | S2 hurt flip |
| S5a max_clauses 4 | ❌ REVERTED | `1bc6fa0` | 36/52 | 10/11 | FAIL | recolor_cnt regression |
| S4 bridge | ⏭️ SKIPPED | — | — | — | — | user instruction |
| S1′b bridge_cardinal_ordinal | ✅ DONE | `35dd2e6` | 39/54 | 11/11 | PASS | pcopy_1c +1; flip/hollow/pcopy_mc still 0/3 |
| S1′c constraint arithmetic | ⬜ DEFERRED | — | — | — | — | optional; needs explicit user confirmation |

---

## S1′b — bridge_cardinal_ordinal (NEXT)

**Gap:** `1d_flip`, `1d_hollow`, `1d_pcopy_*` need a length (cardinal, `s*`) read as an
offset/position (ordinal, `p*`).

**Change:**
1. `solver/predicates.py`: add
   `Predicate("cardinal_ordinal", 2, ("size", "position"), "arith", frozenset({4}))`
   and add `"cardinal_ordinal"` to `OBJECT_BODY_ALLOWLIST`.
2. `solver/encoder.py`: on the lean path, for every observed size `s` and position `p`
   where `s == p` (i.e. same integer value), emit
   `cardinal_ordinal(s{s}, p{p}).`
   Uniform, mechanical, no category knowledge.
3. `solver/tests/test_encoder.py`: assert bridge fact present, e.g.
   `cardinal_ordinal(s3,p3)` for a width-4 grid with a length-3 block.
4. Regenerate `solver/bias/object.pl` (`python -m solver.bias_gen`).

**Expected targets:** `1d_flip` (mirror offset = width − (start+L)), `1d_hollow`
(far-end offset = L−1), `1d_pcopy_*` (second copy offset = L).

**Risk:** position-type body preds expand search; keep `max_body(6)` and monitor timeouts.

**Validation gate (MANDATORY):**
1. `pytest solver/tests -q` — must pass before commit.
2. Commit with message:
   `feat(solver): S1'b cardinal_ordinal bridge (uniform size-position map)`
   plus attestation: `uniform mechanical emit; no category/name gating; no answer-leaking BK.`
3. Run 54-task eval:
   `OUT=results/eval_s1b JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2`
4. **Acceptance (soft gate — `.cursor/rules/soft-eval-regression.mdc`):**
   - Prefer exact ≥ 38/54 (baseline); prefer ≥ 40 with fail-family gains
   - Partial perfect-cat drops (e.g. 3→2) OK if net exact rises / gains dominate
   - Reject if net exact falls with no fail-family gains, or any 3/3 → 0/3
   - Soft rule wins over older “zero perfect regressions” wording in this plan
5. **If gate FAILS:** `git revert HEAD`, push, mark row ❌ REVERTED with reason, stop or
   move to next TODO.
6. **If gate PASSES:** mark row ✅, push, proceed to S1′c evaluation decision.

**Results (2026-08-05):**
- Exact: **39/54** | Perfect intact: **11/11** | Regressions: none | Gains: `1d_pcopy_1c` 0→1
- Soft: 0.722 | `1d_flip_1` segfaulted in parallel pass, re-ran cleanly (still fail)
- Gate: **PASS** → action: **kept**
- Induction time on paired PASSes: mean −2.1s vs baseline; notable wins on `move_2p_dp` / `move_dp`, small overhead elsewhere

---

## S1′c — constraint-based arithmetic (OPTIONAL, deferred)

**Do NOT start until S1′b gate outcome is recorded above.**

Only implement if:
- S1′b passed AND we still see BK-size / timeout pressure, OR
- user explicitly asks for the unified `add/3` refactor.

**Sketch (proposal only):**
- Replace `size_add` fact table with bias-level arithmetic checks (`bad_body` hooks) so
  Popper verifies `C = A+B` at eval time instead of grounding from facts.
- Risks (from analysis): Popper bias-language mismatch; search guidance loss (constants no
  longer suggested by facts); eval-time overhead; debugging opacity.

**Gate:** same soft gate as S1′b (pytest, commit, 54-task eval; see
`.cursor/rules/soft-eval-regression.mdc`).

**Status:** DEFERRED — do not implement without explicit user confirmation after S1′b.

---

## Post-run bookkeeping

- [ ] Update this file's tracker table after each step.
- [ ] Update PR body on `cursor/plan-within-type-relations-ebb2` (or new PR for
      `cursor/unified-arithmetic-ebb2`) with step outcomes.
- [ ] If any step touches documented BK/bias vocabulary: **ask** before editing `spec/`.
- [ ] Keep `results/eval_s1b/` etc. as per-step artifacts (gitignored).

## Current next action for an agent resuming this plan

1. Read this file; confirm tree clean on correct branch.
2. Skip all rows marked ✅ / ❌ / ⏭️.
3. Execute **S1′b** exactly as specified; do not redesign.
4. After S1′b gate, stop and report; S1′c requires separate user confirmation.
