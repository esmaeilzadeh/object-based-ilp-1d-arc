# Plan: Update all docs to current block-level ILP state

**Status:** executed on branch `cursor/docs-block-primary-e0d1` (docs only)  
**Goal:** Make every user-facing and method doc match the code on `main` /
`develop` / `cursor/fill-0-cloud-loop` tip (`d56f23f`), and align narrative
with [`.cursor/rules/block-level-only.mdc`](../rules/block-level-only.mdc).

---

## 0. Current truth (source of authority)

Docs must describe this stack, not the older dual-ladder thesis as the
*default research path*:

| Piece | Current behavior |
|-------|------------------|
| Research default | `block_primary` / object-head only (`include_pixels=False`) |
| Head | `out_block(Ex, Bid, Off, Len, Color)` — paint `Len` of `Color` at `start(Bid)+Off` |
| Input BK (lean) | Uniform emit from grids: `block`, `gap`, `obj_succ`, `obj_pair`, `largest` / `non_largest`, `component_*`, `size_add` / `size_sum3`, `size_even` / `size_odd` (`OBJECT_BODY_ALLOWLIST`) |
| Bias | **One** mechanical generator: `render_object_bias_from_bk(bk, exs)` → per-instance `bias_object.pl`; static `solver/bias/object.pl` is fallback/tests mirror only |
| Connectivity guards (uniform) | Every clause: `block` binds head Bid; `size_add` / `size_sum3` result ∈ {head Off, Len} |
| Exs | Mechanical pos/neg from train I/O (wrong color/len/off/bid, Off=0 prefixes, cross-block Len/Color mixes) — same algorithm every instance |
| Decode | Query `out_block/5` → paint on zero canvas; abolish dynamic after apply |
| Accept | Object path: **paint-verify** all train outputs (not soft-only) |
| Forbidden (unless explicit confirm) | Category-named bias stages, marker/reflect hacks, trivial closed-form as “block wins”, pixel/dual rescue ladder for block scores |
| Ablation modes still in code | `pixel_only`, `block_only`, `block_primary`, `dual`, `dual_no_agg`, `dual_no_ladder`, `dual_full` — dual ladder is **legacy ablation**, not the block-lift claim |

Code anchors: `solver/pipeline.py`, `solver/encoder.py`, `solver/bias_gen.py`,
`solver/predicates.py`, `solver/decode.py`, `solver/harness.py`,
`.cursor/rules/block-level-only.mdc`.

---

## 1. Doc inventory and verdict

| Doc | Role today | Verdict |
|-----|------------|---------|
| [README.md](../../README.md) | Repo entry | **Rewrite** — still sells dual cheap-first ladder as the product |
| [solver/README.md](../../solver/README.md) | Package how-to | **Rewrite** — pipeline + flags outdated |
| [docs/SOLVER_PLAN.md](../../docs/SOLVER_PLAN.md) | Method plan | **Major rewrite** — `out_block/4` Start/Len; dual ladder as core; missing mechanical bias / guards / Off |
| [docs/ILP-1D-Method.md](../../docs/ILP-1D-Method.md) | SOTA / BRIL planning | **Refresh + demote todos** — object-head marked pending; wrong paths (`1d-arc/...`); wrong head arity |
| [.cursor/rules/block-level-only.mdc](../rules/block-level-only.mdc) | Mandatory direction | **Keep**; only add cross-links from docs (do not dilute) |
| `popper/*.md`, `raw_data/**/README.md` | Upstream / data | **Leave** (not our method) |
| **New** `docs/CURRENT_METHOD.md` (proposed) | Living method snapshot | **Add** — short “as implemented” doc so SOLVER_PLAN can stay historical+target |
| **New** `docs/EVAL_NOTES.md` (optional) | Latest eval snapshot | **Add if** we want the 54-task / category table captured |

---

## 2. Work packages (ordered)

### WP1 — Living method doc (`docs/CURRENT_METHOD.md`) — **do first**

Single source of “what the code does now”:

1. **Claim:** measure block lift vs pixel Decom under uniform mechanical language.
2. **Encode:** input runs → lean BK; output colored runs → `out_block` pos/neg (Bid/Off semantics).
3. **Bias:** instance mechanical bias + connectivity guards; no category switch.
4. **Induce:** one object Popper call (`block_primary`).
5. **Verify / decode:** paint-verify trains; decode test; score pixels.
6. **Allowlist + arith sugar:** list `OBJECT_BODY_ALLOWLIST` and what `size_add` / `size_sum3` mean (pair-local, not answer leak).
7. **Explicit non-goals:** link rule file; list purged families (marker/reflect, family bias stages).
8. **How to run:** `python -m solver.harness --mode block_primary ...` and parallel script.
9. **Pointer:** “historical / dual-ladder design” → `SOLVER_PLAN.md`; “ILP landscape” → `ILP-1D-Method.md`.

### WP2 — Root + package READMEs

**README.md**

- Lead with object / `block_primary`, not dual ladder.
- One-sentence link to `block-level-only` rule + `CURRENT_METHOD.md`.
- Setup unchanged (venv / Popper / Clingo).
- Solve example: show harness `--mode block_primary` (and keep CLI one-liner if CLI stays dual-default — **document the default honestly**; if CLI default remains legacy dual, say so and point eval at `block_primary`).
- Ablation list: include `block_primary`; label dual\* as pixel/dual ablations.

**solver/README.md**

- Pipeline steps matching object path (encode → mechanical bias → induce `out_block` → paint-verify → decode).
- Document `out_block/5` and Off = offset from **input block start**.
- Flags / harness modes table; note `force_bias` / `include_pixels` behavior from `pipeline.solve`.
- Point to tests that lock mechanical bias (`test_encoder.py` guards against `mirrored_out_block`, etc.).

### WP3 — Rewrite `docs/SOLVER_PLAN.md` (history + still-valid design)

Do **not** silently pretend dual ladder is still the research default.

Structure:

1. **Preamble (new):** “Original dual-ladder plan; research default is now block-primary — see CURRENT_METHOD.md and block-level-only rule.”
2. **Keep** Stage 0 framing (per-instance encode/induce/verify/apply/decode) — still true.
3. **Update Stage 1 block layer** to match lean object BK (empty_block / obj_index may remain in inventory for dual ablations; call out what **block_primary actually emits**).
4. **Fix Stage 2** head signature and decoder (`Bid, Off, Len, Color`; paint at `start+Off`; unpainted = 0).
5. **Rewrite Stage 3:**  
   - Default path = single mechanical object induce.  
   - Dual ladder / trivials = ablation-only / off-direction unless confirmed.  
   - Remove any implication that family stages (`object_mirror`, …) are planned.
6. **Stage 4–6:** keep eval protocol; add `block_primary` as required ablation/column vs `pixel_only`.
7. **Stage 7 / checklist:** mark done items (object-head, mechanical bias); leave library learning as future; strike marker/reflect from any “needed BK” lists.
8. **Checklist § object head:** replace Start/Len with Bid/Off; add neg policy + connectivity guards.

### WP4 — Refresh `docs/ILP-1D-Method.md`

1. Strip or update YAML todos: `upgrade-object-head` → **completed** (point to CURRENT_METHOD); keep library as future; fix/remove broken `1d-arc/` links.
2. Fix M2 object-head signature to `out_block/5` (Bid, Off, Len, Color), not Start/End.
3. Update matrix row for SOLVER_PLAN / implementation: object-head **exists**; gap is library + hard categories under **uniform** language (hollow / pcopy / flip / mirror), not “add object-head.”
4. Reframe M3 portfolio: ordered **uniform** bias constraints ≠ category-named stages; cite rule.
5. Build-order paragraph: invert — object-primary is current; dual is ablation baseline, not prerequisite for the block claim.
6. Optional: rename title clarity (“landscape + BRIL target”) vs living method doc.

### WP5 — Optional eval snapshot (`docs/EVAL_NOTES.md`)

Capture last reported `block_primary` sweep (54 tasks, ~2 min, 2 workers): ~39 pass / 6 partial / 9 fail; perfect vs weak categories. Label as **snapshot, not CI**. Only add if we want the number frozen in-repo; otherwise put a one-liner “re-run harness” in CURRENT_METHOD and skip this file.

### WP6 — Cross-links and consistency pass

1. Every method doc links: rule ↔ CURRENT_METHOD ↔ SOLVER_PLAN ↔ ILP-1D-Method.
2. Grep docs for stale strings and fix or annotate:

   - `out_block(Ex, Start, Len, Color)` / `Start, End`
   - `object_mirror` / `object_hollow` / family bias stages as recommended path
   - “trivial checks → block-only → dual” as **default** product story
   - `marker_block`, `reflect_pos`, `mirrored_out`, answer-leaking BK
   - Claims that object-head is “future / M2 pending”
   - Absolute paths `1d-arc/docs/...`

3. Ensure READMEs do not contradict the rule (no encouraging pixel rescue for block scores).

### WP7 — Out of scope (do not change in this doc pass)

- Code / bias / encoder behavior.
- Popper upstream READMEs.
- Expanding BRIL library learning into an implementation plan (mention only as future).
- Re-introducing per-family doc “recipes” that read like bias switches.

---

## 3. Acceptance criteria

- [x] A newcomer reading **README → CURRENT_METHOD** can run `block_primary` and state the head schema correctly.
- [x] No doc presents category-staged object biases or marker/reflect BK as the intended method.
- [x] `out_block/5` Bid/Off semantics appear everywhere the head is described.
- [x] Dual ladder / trivials / pixel stages are labeled **ablation or legacy**, not the block-lift claim.
- [x] ILP-1D-Method todos/links match reality (object-head done).
- [x] Rule file remains the normative “do not” list; docs cite it.
- [x] Open Q defaults: document CLI dual default as-is; CURRENT_METHOD as-built + SOLVER_PLAN delta; skip EVAL_NOTES.

---

## 4. Suggested commit sequence (when executing)

1. Add `docs/CURRENT_METHOD.md`
2. Update `README.md` + `solver/README.md`
3. Rewrite `docs/SOLVER_PLAN.md` preamble + Stages 2–3 (+ checklist)
4. Refresh `docs/ILP-1D-Method.md`
5. Optional `docs/EVAL_NOTES.md` + final grep consistency commit

Keep commits doc-only; no solver changes in this plan’s execution.

---

## 5. Open questions (resolve at execution start)

1. Should `solver.cli` default stay legacy dual, or switch default solve path to `block_primary`? (**Docs must match CLI**; if CLI changes, that is a separate tiny code PR — not required for doc accuracy if we document current default.)
2. Keep `SOLVER_PLAN.md` as long historical plan vs slim it and move detail only into CURRENT_METHOD? Prefer: **CURRENT_METHOD = as-built**, SOLVER_PLAN = as-designed + explicit delta.
3. Include EVAL_NOTES numbers in-repo or leave ephemeral under `work/`?

Default answers if unconfirmed: (1) document CLI as-is; (2) CURRENT_METHOD + delta preamble; (3) skip EVAL_NOTES unless numbers are re-verified in the same turn.
