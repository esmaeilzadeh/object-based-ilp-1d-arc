# Plan: Tighter object bias + failure reasons

**Status:** plan only (no code in this step)  
**Branch:** `cursor/fill-0-cloud-loop`  
**Aligns with:** [block-level-only.mdc](../rules/block-level-only.mdc) — uniform mechanical bias
tighten (no category switch). Failure reasons are observability only.

---

## 0. Goals

1. Apply a **uniform** tighter object search budget so more instances can
   **finish** before wall-clock cut (less flaky pass/fail).
2. Surface a clear **`failure_reason`** (and related diagnostics) when
   `block_primary` does not accept a paint-verified program — e.g. timeout vs
   search exhausted vs paint-verify reject — instead of only
   `fallback_identity`.

Non-goals: category-named bias; pixel/ladder rescue; changing accept criterion
away from paint-verify.

---

## 1. Current vs proposed search budgets

### Current (object path)

| Knob | Current | Notes |
|------|---------|--------|
| `max_vars` | 10 | `render_object_bias_from_bk` |
| `max_body` | 6 | |
| `max_clauses` | 3 + `enable_multi_clause` | |
| Connectivity guards | on | keep |
| `max_literals` | **40** (Popper default) | **not passed** from `induce.py` |
| Bias-implied max size | `(1+6)×3 = 21` | so `max_literals=40` is slack |

### Proposed defaults (uniform for every instance)

| Knob | Proposed | Rationale |
|------|----------|-----------|
| `max_vars` | **8** | largest combinatorial cut; still ≥ head arity 5 |
| `max_body` | **5** | short object rules often suffice; 4 as fallback if still huge |
| `max_clauses` | **3** (unchanged) | keep multi-clause for recolor-style tasks |
| `max_literals` | **`(1 + max_body) * max_clauses`** → **18** | match bias ceiling; pass explicitly in `Settings` |
| Guards / allowlist | unchanged | still mechanical |

Expose as named constants in `bias_gen.py` (e.g. `OBJECT_MAX_VARS=8`, …) so
tests and static `object.pl` regeneration stay in sync via `write_bias_files()`.

**Rollback path:** keep old `(10,6,3,40)` behind a single optional override
kwarg on `render_object_bias_from_bk` / `induce` for A/B — default = new tighter
values. No category branching.

---

## 2. Failure-reason design

### Why Popper alone is not enough

`learn_solution` returns `(prog, terminated_by_timeout)` but the flag is
**always False** today (bug: on kill it sets `terminated_by_timeout = False`).
Do **not** trust that flag. Detect timeout in **our** wrapper:

- `Process.join(timeout)` then `is_alive()` → terminate → reason `popper_timeout`
- Or wall-clock around `learn_solution` when using Settings timeout path

### Taxonomy (object / `block_primary`)

Ordered classification after one induce attempt:

| `failure_reason` | When |
|------------------|------|
| `none` / omit | Exact success: paint-verified + (usually) test match reported separately |
| `popper_timeout` | Induce killed by wall-clock; no usable program **or** only unverified leftover |
| `popper_exhausted` | Induce finished before timeout with **empty** program (search done under bias/`max_literals`) |
| `popper_error` | Exception in induce / Popper |
| `paint_verify_failed` | Popper returned a program; **failed** `verify_object_on_train` |
| `decode_error` | Verified or candidate apply/decode raised (overlap/OOB/segfault path → catch if possible) |
| `fallback_identity` | No candidate program at all after induce miss (current fallback); can be paired with `popper_timeout` / `popper_exhausted` as primary |

Primary field: **`failure_reason`** (string).  
Optional diagnostics bag: **`failure_detail`** (dict), e.g.:

```json
{
  "failure_reason": "paint_verify_failed",
  "failure_detail": {
    "popper_terminated": "completed",
    "had_program": true,
    "program_chars": 312,
    "max_vars": 8,
    "max_body": 5,
    "max_clauses": 3,
    "max_literals": 18,
    "timeout_s": 120,
    "induce_elapsed_s": 41.2
  }
}
```

On success: `failure_reason: null` (or omit), still record bias budgets in detail
if cheap.

**Important:** distinguish Popper coverage success from our accept gate. A
program can be returned and still be `paint_verify_failed` — that is the common
flip failure mode when search “finds” something.

### What we will **not** claim as failure reason

- “max_body too small” as a direct Popper exit code — Popper does not emit that.
  If search **exhausts** with no program under the new caps, report
  `popper_exhausted` and include `max_body` / `max_vars` / `max_literals` in
  `failure_detail` so humans can infer the space was too tight.
- Soft-score-only failures (exact harness already has `exact_ok`).

---

## 3. Code changes (work packages)

### WP1 — Bias defaults + `max_literals` plumbing

1. `solver/bias_gen.py`: change object defaults to `max_vars=8`, `max_body=5`,
   `max_clauses=3`; document constants.
2. `solver/induce.py`: pass `max_literals=(1+max_body)*max_clauses` into
   `Settings` (read body/clauses from bias file or pass explicit args).
3. Regenerate `solver/bias/object.pl` via `write_bias_files()`.
4. Update `solver/tests/test_encoder.py` assertions for new numbers.

### WP2 — Richer induce return

Change `induce(...)` to return a small dataclass (or keep str + side channel):

```text
InduceResult:
  program: Optional[str]
  status: "ok" | "timeout" | "exhausted" | "error"
  elapsed_s: float
  error: Optional[str]
  max_literals: int
```

Implementation options (prefer minimal Popper fork):

- **A (preferred):** wrap `learn_solution` with our own `multiprocessing.Process`
  + `join(timeout)` so `status=timeout` is trustworthy; on clean exit with empty
  prog → `exhausted`; with prog → `ok`.
- **B:** call existing `learn_solution` and classify by wall clock ≈ timeout and
  empty prog (weaker).

Do not rely on Popper’s `terminated_by_timeout` until/unless upstream fixed.

### WP3 — Pipeline + harness surface

1. Extend `SolveResult` with `failure_reason: Optional[str]`,
   `failure_detail: dict`.
2. Object path in `pipeline.solve`:
   - induce → if timeout/exhausted/error and no verifying prog → set reason,
     then fallback as today.
   - if prog and not paint-verify → `paint_verify_failed` (do **not** silently
     treat as success; keep current reject behavior).
   - success → `failure_reason=None`.
3. `harness.run_one` / JSON: dump `failure_reason`, `failure_detail`.
4. Optional: CLI `--out` JSON includes the same fields.

### WP4 — Verify / smoke

1. Unit: bias file contains new max_* and induce Settings gets `max_literals=18`.
2. Unit: mock/timeout path sets `failure_reason=popper_timeout`.
3. Unit: hand program that fails paint-verify → `paint_verify_failed`.
4. Smoke: `1d_flip_0` / `1d_move_dp_0` under `block_primary` — confirm JSON
   reason is populated on fail; move_dp still passes if possible.
5. Mini sweep: first-3 tasks optional after merge readiness (not blocking WP1–3).

### WP5 — Docs (light)

One paragraph in `docs/CURRENT_METHOD.md` + `solver/README.md`: new budgets and
failure_reason vocabulary. No category recipes.

---

## 4. Suggested commit sequence

1. Tighter object bias defaults + static `object.pl` + tests  
2. `InduceResult` + trustworthy timeout detection in `induce.py`  
3. `SolveResult` / harness `failure_reason` plumbing  
4. Smoke on flip_0 + move_dp_0; doc blurb  

---

## 5. Risks

| Risk | Mitigation |
|------|------------|
| Tighter bias drops currently solvable tasks (e.g. some recolor/move) | Keep override; compare first-3 exact before/after |
| Exhausted ≠ “need bigger max_body” always | Detail fields list all caps; don’t over-interpret |
| Janus segfault on apply | Catch where possible → `decode_error`; process isolation already helps for induce |
| Popper multi-clause still large at vars=8 | If still timeout-dominated, second step try `max_body=4` uniformly |

---

## 6. Acceptance criteria

- [ ] Object bias defaults are `max_vars=8`, `max_body=5`, `max_clauses=3`, and
      induce sets `max_literals=18` (or `(1+body)*clauses`).
- [ ] Same algorithm for every instance (no category switch).
- [ ] Failed `block_primary` harness JSON includes `failure_reason` in
      `{popper_timeout, popper_exhausted, popper_error, paint_verify_failed,
      decode_error, fallback_identity}` (or success with null).
- [ ] `failure_detail` records bias caps + induce elapsed.
- [ ] Existing encoder/bias tests updated and green.
- [ ] At least one known-hard fail (`1d_flip_0`) shows a **non-empty** reason
      other than silent `fallback_identity` alone.

---

## 7. Open defaults (confirm at execution if needed)

1. Start with **`max_body=5`** (not 4) for first landing — less risk of mass
   regressions.
2. Prefer **WP2 option A** (our process+join) for honest timeouts.
3. On `paint_verify_failed`, still fall back to identity prediction for the
   grid (current behavior) but **label** the reason clearly in JSON.
