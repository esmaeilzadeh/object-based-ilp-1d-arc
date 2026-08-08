<!-- plan-doc-3600-regression-hypothesis -->
---
name: Doc — 3600s regression hypothesis link
overview: "Docs-only: make the measured S6 @3600s 30/54 drop cite the missing anytime/paint-aware feature as the leading hypothesis, with a reciprocal pointer from 02-SOLVER_PLAN.md."
isProject: true
todos:
  - id: tighten-04-hypothesis
    content: "Tighten §2d hypothesis in docs/04 to a concise labeled hypothesis + link to 02 feature request"
    status: completed
  - id: backlink-02-evidence
    content: "Add short Observed evidence note under the feature request in docs/02-SOLVER_PLAN.md pointing at 04 §2d"
    status: completed
  - id: commit-docs
    content: "One docs commit on current branch; no code/eval changes"
    status: in_progress
---

# Plan: document anytime/paint-aware gap as @3600s regression hypothesis

**Propose only — do not implement until approved.**

## Goal

Make the measured S6 regression (**41/54 @600s → 30/54 @3600s**, `JOBS=2`, raw harness scores) explicitly and **concisely** attribute a leading hypothesis to the not-implemented feature in
[`docs/02-SOLVER_PLAN.md`](../../docs/02-SOLVER_PLAN.md#anytime-train-paint-valid-candidate-retention--paint-aware-induction):

> Anytime train-paint-valid candidate retention / paint-aware induction

Without rewriting that whole feature request into the comparison doc, and without claiming the hypothesis is proven.

## Current state (already partly present)

[`docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md`](../../docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) §2d already has a **Hypothesis** paragraph (~8 lines) linking to the 02 feature request.

[`docs/02-SOLVER_PLAN.md`](../../docs/02-SOLVER_PLAN.md) feature request does **not** yet cite the measured 30/54 @3600s run as motivating evidence.

This plan is therefore mostly **tighten + bidirectional link**, not a greenfield writeup.

## Scope

**In scope (docs only):**

1. `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md` — §2d hypothesis block
2. `docs/02-SOLVER_PLAN.md` — short evidence note under the feature request

**Out of scope:**

- Implementing anytime retention / paint-aware induction
- Re-running evals
- Offline score correction / hiding the 30/54 result
- Changing TL;DR / conclusions beyond a one-line consistency tweak if needed

## Exact edits

### Step 1 — Tighten comparison §2d hypothesis

In `docs/04` §2d, keep measured numbers/tables as-is. Replace or reshape the existing hypothesis paragraph into a **short labeled block**, roughly:

```markdown
**Hypothesis (leading, not proven):** the drop is explained by the missing
[Anytime train-paint-valid candidate retention / paint-aware induction](02-SOLVER_PLAN.md#anytime-train-paint-valid-candidate-retention--paint-aware-induction).

Mechanism in one line: Popper keeps compressing after the first train-perfect
program and returns only the final best; paint verify is post-hoc on that one
program, so longer budgets can discard earlier train-paint-valid answers
(`popper_timeout` / `paint_verify_failed` / worse generalization). No test
leakage. Until that feature lands, non-monotonic 600s→3600s drops remain an
expected risk — not evidence that S6 bias disappeared.
```

Constraints:

- Call it a **hypothesis**, not a proven root cause
- Stay concise (≈5–8 lines max)
- Keep the deep explanation in `02`, not duplicated in `04`
- Preserve “we do not hide this regression” / raw-score wording nearby

### Step 2 — Back-link from the feature request in `02`

Under the feature request heading (after **Status: not implemented**), add a short note:

```markdown
**Observed evidence (motivating, not a completed root-cause proof):**
measured S6 @3600s (`JOBS=2`) scored **30/54 exact**, below **39/54 @120s** and
**41/54 @600s**. Documented as a real regression with this feature named as the
leading hypothesis in
[04-COMPARISON §2d](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md#2d-3600-s-run-added-2026-08-08--measured-regression-vs-shorter-budgets).
```

Do **not** paste the full failure-mode essay again; one short evidence pointer is enough.

### Step 3 — Commit

Single docs commit on the current working branch, e.g.:

`docs: link 3600s regression to anytime paint-valid hypothesis`

No code, no results commits (`results/` gitignored).

## Acceptance

- [ ] `04` §2d names the 02 feature request as the **leading hypothesis** for 41→30
- [ ] Wording is concise; full mechanism stays in `02`
- [ ] `02` feature request cites the measured 30/54 @3600s evidence and links back to `04` §2d
- [ ] Regression remains reported as real / uncorrected
- [ ] One docs commit; no solver changes

## Non-goals / explicit non-claims

- Not claiming every `popper_timeout` at 3600s is proven compression-overwrite
- Not claiming test-set leakage
- Not approving implementation of the feature itself (separate plan later if requested)
