# Plan: Port main designs into independent-out encode

**Status:** PROPOSED — wait for explicit implement approval.
**Branch:** `cursor/indep-out-blocks-ebb2` (keep; do not revert head)
**Compare:** latest `main` (Bid+Off, ~39/54 @120s) vs this rewrite (Rank+Start, **0/54** @120s)
**Note:** No `cursor/indep-out-blocks-ebb` branch exists; comparison is main vs ebb2 indep-out.
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit; no category gating; no answer-leaking BK; no marker/reflect hacks.
**Gate:** `.cursor/rules/soft-eval-regression.mdc` on first-3-per-cat (54 tasks, 120s).

## Goal

Keep independent head `out_block(E, Rank, Start, Len, Color)` but **copy clever search-pruning / geometry / exs / decode designs** from main’s Bid-anchored method that the rewrite dropped. Not a revert to Bid+Off.

## Verdict

The rewrite correctly changed the head shape, but dropped several designs that made main work. One clear bug (`gap` always `s0`) plus missing bias/exs/decode counterparts explain the collapse more than “independent indexing is impossible.”

## What main got right (to port, not revert)

| Design | Main | Indep now | Why it mattered |
|---|---|---|---|
| **Forced head↔input bind** | Every clause: `block(_, Bid=var1, _, _)` | Dropped (plan said so) | Without a Rank↔input bridge constraint, var1 is free / only `rK` constants |
| **Meaningful `gap`** | `obj_succ`-only gaps between **colored** blocks | Gaps between consecutive all-runs | Consecutive runs are always adjacent → **every `gap` is `s0`** (confirmed) |
| **Colored-only paint exs** | `segment_blocks(out)` + blank canvas | `segment_all_runs(out)` incl. `v0` | Canvas is already 0; empty `pos` only inflate coverage |
| **Relative placement** | `Off` vs Bid start via `anchor_input_block_offset` | Absolute `Start` | Same idea must be rebuilt as `in_start` + `size_add`, with enough arith facts |
| **Neg families** | Off=0 identity killers, wrong Bid, cross-block Len/Color mix, Off=0 wrong color | Wrong Rank/Start/Len/Color only | Main negs killed loose `block`/`s0` over-paints; those patterns still exist under Rank/Start |
| **Decode grounding** | Enumerate known input Bids (+ Off/Len/Color) | Full `Rank × Start × Len × Color` | Verify/decode cost explodes; more false paints |
| **Lean size_add scope** | Closure on colored succession lengths/gaps | Same arith loop, but `gap/4` broken; starts not systematically closed | Absolute Start needs `size_add(in_start, δ, out_start)` for observed δ |

## What’s wrongly implemented (bugs / regressions)

1. **`gap/4` on lean is vacuous** — consecutive all-runs ⇒ `g = s2-e1-1 = 0` always. Main’s colored gaps are gone from `gap/4` (they still appear only inside `size_add`/`size_sum3` loops).
2. **No replacement for the Bid-forcing bias** after dropping `:- clause(C), not body_literal(C, block, 4, (0,1,_,_)).`
3. **Empty output runs as positives** — e.g. `pos(out_block(...,v0))` — unnecessary and costly.
4. **Decode brute-force** — `max_rank × (w+1) × w × 10` queries vs Bid-scoped; also paints `c=0`, which is noise on a zero canvas.
5. **Incomplete Start arithmetic** — `in_start` emits absolute starts, but `size_add` is still succession-shaped; many `Start_out = Start_in + δ` triples never appear as BK facts.
6. **Negatives under-adapted** — Rank/Start/Len/Color flips exist; main’s identity / cross-block mix killers were not re-expressed for independent args.
7. **Popper invented-only BK (critical)** — Popper needs facts for body preds in the object path. If the loader only loads `bk.pl` + `exs.pl` but does not pre-assert `in_start` / `in_rank` / `rank_rev` / `block_succ` / `gap` as BK facts, then those body preds are “invented” and **never true** during search. Main path worked because `block/4` facts were always there; indep’s new rank/start geometry may not be loaded. Verify `induce.py` / `pipeline.py` loads `test_bk.pl` and `bk.pl` into Popper context, not just into Prolog for decode.
8. **Rank constant binding in bias** — `:- not body_var(_,1)` requires var1 used. With `out_block(E, Rank, ...)` the only way to bind Rank is `rK` constants or `in_rank` / `rank_rev`. If bias does not allow rank constants and does not force `in_rank` on every clause, search is empty.
9. **Start-Len type overlap confusion** — Both `Start` and `Len` are `size`. Bias must allow them to come from `size_add` chains and `in_start`, not force them to be identical to input `Len` unless actually true.
10. **Static bias/object.pl is a fallback but stale** — `render_object_bias()` dummy facts are fine for tests, but committed `solver/bias/object.pl` has `constant(v1,'value').constant(r0,'rank').` only; it lacks a Rank-forcing constraint, and may be used in odd paths. Align it with the generated dynamic bias after Step 3.
11. **`_collect_out_blocks` decode cost** — `max_rank × (w+1) × w × 10` ground queries. For w≈20, that is ~50k+ Prolog queries per example; verify timeouts / false paints on wide outputs.

## Steps

### Step 0 — Freeze baseline & fixtures (no solver change)

- Keep branch; do **not** revert the head.
- Pick 3–6 tasks that main solved (e.g. flip / hollow / move) and dump `bk.pl`, `exs_object.pl`, `bias_object.pl` for **main vs HEAD**.
- Checklist per dump: gaps non-zero?, empty `pos`?, bias force-bind?, `size_add` covering start+δ?, neg identity/cross-mix present?
- **Done when:** short gap analysis note in this plan or sibling doc under `.cursor/plans/`.

### Step 1 — Fix lean `gap` (port main’s obj_succ-only gaps)

- Restore **colored-succession** `gap(E,Bi,Bj,G)` on lean (same as main).
- Keep `block_succ` / empty-as-`block` / `in_start` / `in_rank` if still needed for Rank bridging — but do **not** emit consecutive-run gaps.
- Tests: row `[2,2,0,0,9]` ⇒ `gap(...,s2)` not only `s0`.
- Soft smoke optional after Step 3+.
- **Done when:** unit tests green; fixture gaps match main’s meaning.

### Step 2 — Exs: colored-only positives + ported neg families

- Positives: `segment_blocks(out)` only (no `v0` runs), still `out_block(E, Rank, Start, Len, Color)` with Rank = ordinal among **chosen** indexing convention (decide in Step 2a).
- **Step 2a — Rank convention (pick one, document):**
  - **A (recommended):** Rank = left→right index among **colored** out blocks; `in_rank` = colored ordinal (`obj_index`-style). Aligns with main’s colored world.
  - **B:** Rank among all runs, but still omit empty `pos` (Rank holes). Only if you need empty geometry in the head.
- Port neg families into Rank/Start language:
  - Wrong color / Len / Start / Rank (keep).
  - **Identity killers:** at each input `in_start`/`block` color, neg wrong Len (and wrong color at true Len) — analogue of Off=0 killers.
  - **Cross-source mix:** true `(Rank,Start)` with another block’s `(Len,Color)`.
  - **Wrong Rank** for a true `(Start,Len,Color)` (already partly there).
- **Done when:** tests assert no `v0` pos; neg families present; encode fixtures reviewed.

### Step 3 — Bias: force Rank↔input bridge (port of Bid-force)

- Add mechanical constraint(s), same spirit as main’s forced `block(_,var1,_,_)`:
  - Every clause must contain `in_rank(E, Bid, Rank)` with `Rank = head var 1`, **or**
  - `rank_rev(Rank, R2), in_rank(E, Bid, R2)` (for flip), if you want reverse without constants.
- Also require Len/Color (and usually Start) to come from the **same** `Bid` via `block` / `in_start` (or `size_add` result tied to that `in_start`) — prevent “Rank from block A, Len from block B”.
- Keep bidirectional `size_add`/`size_sum3` on Start/Len (vars 2/3) — already good (S6).
- Keep `:- not body_var(_,1/2/3).`
- **Done when:** bias tests lock the new constraints; static `bias/object.pl` regenerated.

### Step 3.5 — BK loading for Popper object path

- Verify `induce.py` / `pipeline.py` loads `bk.pl` **and** `test_bk.pl` into Popper’s search context, not only into Prolog for decode.
- If Popper only gets `exs.pl` + `bias.pl`, then `in_start`, `in_rank`, `rank_rev`, `block_succ`, `gap` are “invented” and never true → search space is empty.
- Fix: ensure object BK facts are passed as Popper background knowledge, or generated as Prolog rules that Popper can use (depending on how Popper is invoked).
- **Done when:** a smoke run shows Popper actually considers rules using `in_start`/`in_rank`/`rank_rev`.

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
- **Done when:** report vs main 39/54 and vs indep 0/54.

### Step 7 — Only if Step 6 still weak (optional, separate commits)

- Clause/body caps if Rank bridging made search tight enough to raise `max_body` carefully.
- Whether empty input runs stay as `block(...,v0)` or only as gap geometry (main omitted empty `block` on lean).
- SPEC sync ask if documented head/BK contract changes (`spec-sync.mdc`).

## Suggested commit order (after approval)

1. Fix lean `gap` + tests
2. Exs colored-only + ported negs + Rank convention
3. Bias Rank↔input force-bind
4. BK loading for Popper object path
5. Start `size_add` closure
6. Decode scoped grounding
7. Eval report (docs/plan only)

## Non-goals

- No revert to `out_block(E, Bid, Off, Len, Color)` as the primary head
- No marker/reflect BK, no category-named bias, no pixel-head rescue
- No answer-leaking `out_*` BK

## Open decision before implement

- Rank convention **A** (colored ordinal, recommended) vs **B** (all-runs rank, omit empty pos)
