# Plan: Step-wise object bias budget tuning (accuracy + stability)

**Status:** executing on `feature/stepwise-bias-tuning`  
**Progress:** B0 code landed (`failure_reason` + `max_literals=21`). Restarting B0 R=3 protocol (prior run killed at ~48/54 r1).  
**Note:** Object-only cleanup lives on `feature/object-only-solver` (4 stepwise commits); docs step still open there.
**Targets:** (1) exact solve rate on fixed eval slice, (2) **stability** =
repeatability of pass/fail under same timeout / machine class.  
**Constraint:** [block-level-only.mdc](../rules/block-level-only.mdc) — one
uniform mechanical bias for every instance; no category-named budgets.

Related: [plan-tighter-bias-failure-reason.md](plan-tighter-bias-failure-reason.md)
(failure reasons are a **prerequisite**, not optional).

---

## 0. What we already know (do not ignore)

From `all_first3` programs vs proposed hard cut `(vars=8, body=5, lits=18)`:

| Observed need | Implication |
|---------------|-------------|
| **Fill** clauses use **9–10 vars** (`size_sum3`+`gap`+`block`+`s0`) | `max_vars=8` likely **regresses green fill** |
| All seen bodies ≤ **5** | `max_body=5` is low-risk vs current 6 |
| Green moves/recolor/denoise are small (body 2–4, vars ≤8) | Room to tighten elsewhere without touching them |
| Weak cats (flip/hollow/pcopy) often have large/overfit programs | Blind shrink may not help them; may only fail faster |
| Wall-clock timeout dominates flakiness | Stability ≠ only smaller bias; also **eval protocol** |

**Do not start at `max_vars=8`.** That is a late ablation, not step 1.

---

## 1. Fixed eval protocol (every step)

Use the same harness for all steps so numbers are comparable:

| Setting | Value |
|---------|--------|
| Mode | `block_primary` only |
| Slice | first-3 per category (`0,1,2`) = 54 tasks — primary |
| Timeout | **120s** primary; optional **300s** spot-check on flips only |
| Workers | **1** for stability measurements; **2** only for throughput after a step wins |
| Repeats | **R=3** independent runs per config on the 54-slice (stability) |
| Metrics | exact pass count; per-task pass rate over R; **flip-rate** = tasks that pass in some runs and fail in others; `failure_reason` histogram |
| Success of a step | exact mean ≥ previous **and** flip-rate ≤ previous (or exact ↑ with flip-rate flat) |

Ship **failure_reason** before serious tuning (timeout vs exhausted vs
paint_verify_failed). Without it, “failed” is uninterpretable.

---

## 2. Baseline config (step 0) — lock current language

| Knob | Value |
|------|--------|
| `max_vars` | **10** |
| `max_body` | **6** |
| `max_clauses` | **3** |
| `max_literals` | **21** = `(1+6)×3` (explicit; remove silent 40 slack) |
| Guards | keep current connectivity guards |

Actions:

1. Implement failure_reason plumbing.
2. Set `max_literals=21` only (should be near no-op vs today).
3. Run protocol → **Baseline B0** numbers + reason histogram.

Expect: accuracy ≈ historical ~39/54; instability on flip/mirror/padded edge cases.

---

## 3. Step ladder (only advance if step meets §1 success rule)

### Step 1 — Soft body cut (lowest risk)

| Knob | Change |
|------|--------|
| `max_body` | 6 → **5** |
| others | unchanged (`vars=10`, `clauses=3`, `lits=(1+5)×3=18`) |

Why: no all_first3 program needed body >5; shrinks search without killing fill.

Gate: fill/move/denoise/recolor/scale exact must not drop; flip-rate should not rise.

### Step 2 — Match literals to bias (already partly done in step 1)

If step 1 used `lits=18`, skip. Else set `max_literals=(1+max_body)×max_clauses`.

Gate: no accuracy drop; more `popper_exhausted` vs `popper_timeout` is **good**
for stability (search finishing).

### Step 3 — Stability via eval, not bias

Without changing language:

- Prefer **1 worker** for reported numbers.
- Optional: pin CPU affinity / disable parallel eval for paper tables.
- Record induce_elapsed and reason; classify flaky tasks.

If flip-rate is still high only on timeout tasks, bias is still too large **or**
paint-verify rejects dominate — use histogram to choose next step.

### Step 4 — Mild vars cut (only if step 1–2 green)

| Knob | Change |
|------|--------|
| `max_vars` | 10 → **9** |

Why: fill often uses 9–10; **9 may keep fill**, 8 likely does not. Measure fill
3/3 carefully.

Gate: **fill must stay 3/3** (or document intentional trade). If fill breaks,
**revert to 10** and do not proceed to 8.

### Step 5 — Aggressive vars cut (ablation only)

| Knob | Change |
|------|--------|
| `max_vars` | 9 → **8** |

Expect fill/padded_fill/mirror regressions. Keep as labeled ablation for
“smaller space ⇒ more exhausted finishes,” not as default unless accuracy
surprisingly holds.

### Step 6 — Clause budget (last; high risk to multi-clause greens)

| Knob | Try |
|------|-----|
| `max_clauses` | 3 → **2** (ablation) |

Green **recolor_cnt** uses 3 clauses; **move_dp** uses 2. Cutting to 2 may kill
recolor_cnt. Only try after vars/body settled; likely reject as default.

Alternative (safer): keep `max_clauses=3`, do not touch.

### Step 7 — Optional constant pressure (mechanical only)

If reason histogram still shows timeout with small clauses:

- Uniformly restrict size constants (e.g. only sizes that appear in **block/gap
  facts**, not every Off candidate from exs) — still one algorithm.
- Re-measure; this can help flip search without lowering vars below fill need.

Do **not** special-case flip.

---

## 4. Decision table (default recommendation path)

```text
B0: (10, 6, 3, lits=21) + failure_reason
 → S1: (10, 5, 3, lits=18)     # primary candidate for new default
 → S4: (9, 5, 3, lits=18)      # only if fill holds
 → stop for default
S5/S6 = ablations only
```

**Predicted best default after ladder:** `(max_vars=10, max_body=5,
max_clauses=3, max_literals=18)` — improves finish-rate/stability a bit without
knowingly deleting fill’s language. Vars=9 is the first accuracy-risking move.

---

## 5. Stability score (report every step)

For each config C on the 54-slice with R=3:

- `exact_mean` = average exact passes  
- `stable_pass` = tasks exact in all R runs  
- `stable_fail` = tasks fail in all R runs  
- `flaky` = R − stable_pass − stable_fail  
- `timeout_share` = fraction of failures with `failure_reason=popper_timeout`  
- `exhausted_share` = `popper_exhausted`  
- `verify_fail_share` = `paint_verify_failed`

Prefer configs that raise `stable_pass` and cut `flaky` and `timeout_share`,
even if `exact_mean` is flat.

---

## 6. Implementation order (when executing)

1. Failure reasons + explicit `max_literals` (B0)  
2. Run B0 protocol (R=3, 1 worker, 120s) — commit results note under `work/` or
   short `docs/EVAL_NOTES.md` snippet  
3. Step 1 (`max_body=5`) + protocol  
4. Promote Step 1 to default **only if** gate passes  
5. Step 4 (`max_vars=9`) as optional follow-up PR  
6. Steps 5–6 as ablations, not defaults  

Keep override kwargs for A/B (`max_vars=...`) without category switches.

---

## 7. Acceptance for “tuning done”

- [ ] B0 and S1 (and S4 if tried) have R=3 tables on the same 54-slice  
- [ ] Default config chosen by §4 decision table + §5 stability  
- [ ] Fill/move/denoise/recolor/scale not regressed vs B0 on stable_pass  
- [ ] Harness JSON always carries `failure_reason`  
- [ ] No category-specific budgets introduced  

---

## 8. Explicit non-goals

- Per-family bias files or “flip gets more vars”  
- Raising timeout as the main stability fix (helps a little; does not replace
  space control + reasons)  
- Claiming deterministic Popper under wall-clock timeout
