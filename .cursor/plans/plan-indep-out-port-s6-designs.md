# Plan: Port S6 designs into independent-out encode

**Status:** IMPLEMENTED on `cursor/indep-out-blocks-ebb2` (Rank convention A). Smoke @120s: `move_1p_0` exact PASS; flip/hollow/denoise/recolor still fail — **expressibility gaps confirmed**, see post-implementation analysis below.
**Branch:** `cursor/indep-out-blocks-ebb2` (keep; do not revert head)
**Compare:** `cursor/s6-size-add-direction-ebb2` (= latest main tip, S1′b/S6 Bid+Off, **39/54 @120s**, 41/54 @600s) vs this rewrite (Rank+Start, **0/54** @120s)
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit; no category gating; no answer-leaking BK; no marker/reflect hacks.
**Gate:** `.cursor/rules/soft-eval-regression.mdc` on first-3-per-cat (54 tasks, 120s).

## Goal

Keep independent head `out_block(E, Rank, Start, Len, Color)` but **copy the clever search-pruning / geometry / exs / decode designs** from the S6 (Bid+Off) method that the rewrite dropped. Not a revert to Bid+Off.

## Verified facts (so the plan is grounded)

- `solver/induce.py` and `solver/pipeline.py` are **unchanged** between S6 and HEAD; Popper does get `bk.pl` + `exs_object.pl` + `bias_object.pl`. So the earlier “BK not loaded” worry is **removed** — failures are in BK/exs/bias shape, not wiring.
- S6’s `size_add` bad_body (`A/B/R ∈ {var2,var3}`) and lean gap/arithmetic closure were copied almost verbatim; the rewrite kept them but **broke their inputs** (see bugs).
- `popper_exhausted` (38/54) = Popper searched and proved no consistent rule within bias — consistent with a poisoned/contradictory example set and over-loose bias, not just “too slow”.
- `paint_verify_failed` (13/54) = found rules that paint train wrong — consistent with missing main’s killer negatives and unscoped decode.

## What S6 got right (to port, not revert)

| Design | S6 / main | Indep now | Why it mattered |
|---|---|---|---|
| **Forced head↔input bind** | Every clause: `block(_, Bid=var1, _, _)` | Dropped (plan said so) | Without a Rank↔input bridge constraint, var1 is free / only `rK` constants |
| **Meaningful `gap`** | `obj_succ`-only gaps between **colored** blocks | Gaps between consecutive all-runs | Consecutive runs are always adjacent → **every `gap` is `s0`** (confirmed) |
| **Colored-only paint exs** | `segment_blocks(out)` + blank canvas | `segment_all_runs(out)` incl. `v0` | Canvas is already 0; empty `pos` only inflate coverage |
| **Relative placement** | `Off` vs Bid start via `anchor_input_block_offset` | Absolute `Start` | Same idea must be rebuilt as `in_start` + `size_add`, with enough arith facts |
| **Neg families** | Off=0 identity killers, wrong Bid, cross-block Len/Color mix, Off=0 wrong color | Wrong Rank/Start/Len/Color only | S6 negs killed loose `block`/`s0` over-paints; those patterns still exist under Rank/Start |
| **Decode grounding** | Enumerate known input Bids (+ Off/Len/Color) | Full `Rank × Start × Len × Color` | Verify/decode cost explodes; more false paints |
| **Lean size_add scope** | Closure on colored succession lengths/gaps | Same arith loop, but `gap/4` broken; starts not systematically closed | Absolute Start needs `size_add(in_start, δ, out_start)` for observed δ |

## What’s wrongly implemented (bugs / regressions)

1. **`gap/4` on lean is vacuous** — consecutive all-runs ⇒ `g = s2-e1-1 = 0` always. S6’s colored gaps are gone from `gap/4` (they still appear only inside `size_add`/`size_sum3` loops).
2. **No replacement for the Bid-forcing bias** after dropping `:- clause(C), not body_literal(C, block, 4, (0,1,_,_)).`
3. **Empty output runs as positives** — e.g. `pos(out_block(...,v0))` — unnecessary and costly.
4. **Decode brute-force** — `max_rank × (w+1) × w × 10` queries vs Bid-scoped; also paints `c=0`, which is noise on a zero canvas.
5. **Incomplete Start arithmetic** — `in_start` emits absolute starts, but `size_add` is still succession-shaped; many `Start_out = Start_in + δ` triples never appear as BK facts.
6. **Negatives under-adapted** — Rank/Start/Len/Color flips exist; S6’s identity / cross-block mix killers were not re-expressed for independent args.
7. **Rank constant binding in bias** — `:- not body_var(_,1)` requires var1 used. With `out_block(E, Rank, ...)` the only way to bind Rank is `rK` constants or `in_rank` / `rank_rev`. If bias does not force `in_rank` on every clause, search space is wrong.
8. **Start-Len type overlap confusion** — Both `Start` and `Len` are `size`. Bias must allow them to come from `size_add` chains and `in_start`, not force them to be identical to input `Len` unless actually true.
9. **Static bias/object.pl is a fallback but stale** — `render_object_bias()` dummy facts are fine for tests, but committed `solver/bias/object.pl` has `constant(v1,'value').constant(r0,'rank').` only; it lacks a Rank-forcing constraint, and may be used in odd paths. Align it with the generated dynamic bias after Step 3.
10. **`_collect_out_blocks` decode cost** — `max_rank × (w+1) × w × 10` ground queries. For w≈20, that is ~50k+ Prolog queries per example; verify timeouts / false paints on wide outputs.

## Steps

### Step 0 — Freeze baseline & fixtures (no solver change)

- Keep branch; do **not** revert the head.
- Pick 3–6 tasks that S6 solved (e.g. flip / hollow / move) and dump `bk.pl`, `exs_object.pl`, `bias_object.pl` for **S6 vs HEAD**.
- Checklist per dump: gaps non-zero?, empty `pos`?, bias force-bind?, `size_add` covering start+δ?, neg identity/cross-mix present?
- **Done when:** short gap analysis note in this plan or sibling doc under `.cursor/plans/`.

### Step 1 — Fix lean `gap` (port S6 obj_succ-only gaps)

- Restore **colored-succession** `gap(E,Bi,Bj,G)` on lean (same as S6).
- Keep `block_succ` / empty-as-`block` / `in_start` / `in_rank` if still needed for Rank bridging — but do **not** emit consecutive-run gaps.
- Tests: row `[2,2,0,0,9]` ⇒ `gap(...,s2)` not only `s0`.
- Soft smoke optional after Step 3+.
- **Done when:** unit tests green; fixture gaps match S6’s meaning.

### Step 2 — Exs: colored-only positives + ported neg families

- Positives: `segment_blocks(out)` only (no `v0` runs), still `out_block(E, Rank, Start, Len, Color)` with Rank = ordinal among **chosen** indexing convention (decide in Step 2a).
- **Step 2a — Rank convention (pick one, document):**
  - **A (recommended):** Rank = left→right index among **colored** out blocks; `in_rank` = colored ordinal (`obj_index`-style). Aligns with S6’s colored world.
  - **B:** Rank among all runs, but still omit empty `pos` (Rank holes). Only if you need empty geometry in the head.
- Port neg families into Rank/Start language:
  - Wrong color / Len / Start / Rank (keep).
  - **Identity killers:** at each input `in_start`/`block` color, neg wrong Len (and wrong color at true Len) — analogue of Off=0 killers.
  - **Cross-source mix:** true `(Rank,Start)` with another block’s `(Len,Color)`.
  - **Wrong Rank** for a true `(Start,Len,Color)` (already partly there).
- **Done when:** tests assert no `v0` pos; neg families present; encode fixtures reviewed.

### Step 3 — Bias: force Rank↔input bridge (port of Bid-force)

- Add mechanical constraint(s), same spirit as S6’s forced `block(_,var1,_,_)`:
  - Every clause must contain `in_rank(E, Bid, Rank)` with `Rank = head var 1`, **or**
  - `rank_rev(Rank, R2), in_rank(E, Bid, R2)` (for flip), if you want reverse without constants.
- Also require Len/Color (and usually Start) to come from the **same** `Bid` via `block` / `in_start` (or `size_add` result tied to that `in_start`) — prevent “Rank from block A, Len from block B”.
- Keep bidirectional `size_add`/`size_sum3` on Start/Len (vars 2/3) — already good (S6).
- Keep `:- not body_var(_,1/2/3).`
- **Done when:** bias tests lock the new constraints; static `bias/object.pl` regenerated.

### Step 4 — BK: Start arithmetic closure (independent-out analogue of Off)

- Uniformly emit `size_add` for observed starts/deltas needed to express train outs, e.g. pairs from `{in_start values} ∪ {gaps,1,…}` whose sum is another observed size / out Start — **instance-mechanical**, no category gate.
- Keep existing succession `size_add` / `size_sum3` / `size_lt` / parity / components.
- Do **not** add answer `out_*` facts.
- **Done when:** for a move-style fixture, `size_add(in_start, δ, out_start)` appears when δ is observed.

### Step 5 — Decode / verify: scoped grounding (port Bid enumeration)

- Stop full Rank×Start×Color brute force.
- Ground using BK-derived candidates: ranks from `in_rank` (or observed rank constants), starts from `in_start` ∪ `size_add`-reachable sizes, colors from `block` values (skip painting `c=0` unless you explicitly need erase).
- Preserve overlap/OOB fail behavior for paint-verify.
- **Done when:** decode tests still pass; timing on a wide grid is clearly cheaper.

### Step 6 — Micro smoke then soft gate

- Smoke: flip×3, hollow×3, one move (same as S6 path).
- Then soft gate: `OUT=... JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2`.
- Compare failure mix vs current (`popper_exhausted` 38 / `paint_verify_failed` 13 / timeout 3).
- Soft-gate KEEP/REVERT per project rule; **no 600s** unless 120s soft-gate passes.
- **Done when:** report vs S6 39/54 and vs indep 0/54.

### Step 7 — Only if Step 6 still weak (optional, separate commits)

- Clause/body caps if Rank bridging made search tight enough to raise `max_body` carefully.
- Whether empty input runs stay as `block(...,v0)` or only as gap geometry (S6 omitted empty `block` on lean).
- SPEC sync ask if documented head/BK contract changes (`spec-sync.mdc`).

## Suggested commit order (after approval)

1. Fix lean `gap` + tests
2. Exs colored-only + ported negs + Rank convention
3. Bias Rank↔input force-bind
4. Start `size_add` closure
5. Decode scoped grounding
6. Eval report (docs/plan only)

## Non-goals

- No revert to `out_block(E, Bid, Off, Len, Color)` as the primary head
- No marker/reflect BK, no category-named bias, no pixel-head rescue
- No answer-leaking `out_*` BK

## Open decision before implement

- Rank convention **A** (colored ordinal, recommended) vs **B** (all-runs rank, omit empty pos)

## Smoke @120s (2026-08-06, after implement)

| Task | Result | Failure |
|---|---|---|
| 1d_move_1p_0 | **exact PASS** soft=1.0 | — |
| 1d_flip_0 | fail | popper_timeout |
| 1d_hollow_0 | fail | paint_verify_failed |
| 1d_hollow_1 | fail | paint_verify_failed |
| 1d_denoising_1c_0 | fail | paint_verify_failed |
| 1d_recolor_cmp_0 | fail | paint_verify_failed |

Commits: `fdb0247`, `8f7e957`, `f08b830`. Independent head kept (Rank A).
