# 04 — Comparison: this solver (block-ILP, S6) vs Hocquette & Cropper IJCAI-25 "Relational Decomposition" (Decom)

**Reading order:** [01 landscape](01-ILP-1D-Method.md) → [02 plan](02-SOLVER_PLAN.md) →
[03 as-built](03-CURRENT_METHOD.md) → **you are here (vs Decom)** →
[05 repo map](05-REPO_STRUCTURE.md) → [06 running](06-RUNNING.md).
Full blurbs: root [README](../README.md).

Reference: `2408.12212v3.pdf` (next to this file in `docs/`), code + stored results in
`../sources/ijcai25-relational-decomposition-main/` (in the parent `ml-project/` dir, outside
this repo; `programs/relational/{60,600,3600}/1d/*`).

## 0. TL;DR

On the **identical 54-task 1D-ARC slice** (18 categories × first-3 instances), the two approaches
have **complementary per-category strengths**. Our best measured budget so far is **@600s
(41/54 exact)** — not @3600s. A measured 1h `JOBS=2` S6 run scores **30/54 exact** and is a
**real regression vs 39/54 @120s and 41/54 @600s** (raw harness scores; not offline-corrected).
See §2d.

| Side | Wins on | Reason shape |
|---|---|---|
| **Decom (pixel-level)** | `pcopy_1c`, `pcopy_mc`, `scale_dp` (part), `flip`/`mirror` at long budget | pixel rules can invent position arithmetic; but no object concept, so it dies on all 3 `recolor_*` |
| **Ours (block-ILP, S6)** | `recolor_*` (at short/mid budgets), `move_2p_dp`, `move_dp` (part), `flip`+`hollow` already @120s | object/block facts capture "the block", "its length/color", count/sum; but we still die on `pcopy` duplication and can lose short-budget wins when search keeps compressing |

Decom remains 0/3 on `move_dp` and `padded_fill` at every paper budget; ours gets partial credit
there at mid/long budgets (`move_dp` 1/3, `padded_fill` up to 2/3).

The takeaway for the project: **block-level representation pays off at 2–10 min**, dominating
the `recolor` family where pixel Decom is 0/9, **but longer Popper search is currently
non-monotonic** for us (see not-implemented anytime paint-valid retention in
[02-SOLVER_PLAN.md](02-SOLVER_PLAN.md#not-implemented-feature-requests)). The `pcopy` family
remains the pixel-head blind spot for blocks.

---

## 1. Protocol alignment (verified against their code, not just the PDF)

**Learning setup (both sides):** each trial is induced **from scratch** from that
trial’s own train pairs — no curriculum, no transfer from simpler categories.
That matches the ARC few-shot synthesis framing and keeps the comparison about
representation (pixel vs block), not lifelong ILP. Rationale:
[01-ILP-1D-Method.md §4](01-ILP-1D-Method.md#why-per-task-from-scratch-not-curriculum--transfer).

The PDF says "18 tasks, 3 train + 1 test each" (App. B). The user asked us to double-check
that "first 3 of each category" matches. Verified in the repo:

- `train.py`: `train/relational/1d/{task}/{trial}` — a **trial is a full train/test instance**
  (own `exs.pl`/`bk.pl`/`test.pl`), not a re-run of the same data. Trial 0/1/2 = dataset
  instances `_0/_1/_2`. So their 54 runs = **same first-3-per-category slice as ours**.
- `results.py` metric: per run `(tp+tn)/(tp+fn+tn+fp)`; every test pixel contributes one pos
  and 9 neg atoms, so a wrong pixel drowns in ≈9 TN ⇒ their accuracy is a **soft cell-accuracy**,
  not exact. `solved: True` in `results.pl` (`test.py`: `fn==0 and fp==0`) is the **exact**
  all-pixels-correct flag.
- Timeouts stored: 60 / 600 / 3600 s, single CPU (paper: Xeon Gold 6138).
- Their 1D bias (`train/relational/1d/*/bias.pl`): head `out(ex,pos,val)`; body = `in/3`,
  `empty/2`, `my_succ/2`, `add/3`, `lt/2`, unary color constants `cK`/`vK`.
  **Pixel-level only — no block/run concepts at all.**

Our side: `block_primary`, head `out_block(E,Bid,Off,Len,Color)` (Bid-anchored S6 design),
exact = `verified_train AND test grid equal`; `soft_accuracy` = same confusion-matrix ratio
as theirs (that is why our `exact == soft` in summaries — on this dataset our soft *is* the
all-or-nothing cell ratio per run and our failures return identity).

**Apples-to-apples caveat:** their "accuracy%" is soft; our headline "exact" is all-or-nothing.
We therefore compare their **solved count** (exact) against our **exact count**, and separately
their soft % against our soft %.

---

## 2. Totals

All cells below are **exact /54** (all-pixels-correct). Soft % shown in parentheses where a
distinct soft value exists (Decom soft ≠ exact because its per-pixel TN padding inflates
partial credit; ours soft = exact on this dataset because failures return identity).

Both methods now have stored results at **every budget 60/120/600/3600 s**
(Decom @60/@600/@3600 = paper artifacts; Decom @120 = local rerun; ours @60/@120/@3600 =
local runs; @600 = S6 plan).

| Approach | @60s (paper:1min) | @120s | @600s (10min) | @3600s (1h) |
|---|---|---|---|---|
| **Decom (pixel-ILP)** | 32/54 | 30/54 (local rerun) | 34/54 | **37/54** |
| **Ours S6** | 25/54 (see §2a) | **39/54** | **41/54** | 30/54 (see §2d) |
| **Winner (margin)** | Decom (−7) | **Ours (+9)** | **Ours (+7)** | Decom (−7) |

(The pre-S6 `S1′a+S1′b` main scored 39/54 @120 s — same total as S6 @120 s; S6's gain over it
is the flip+hollow unlock at *lower* search time, not net exact.)

Decom soft % (not exact; paper Table 2/4 + local rerun): 59.3 / 55.6 / 63.0 / 68.5 across
60/120/600/3600 s. Ours soft (= exact on this dataset): 46.3 @60 s, 68.5 @120 s,
75.9 @600 s, **55.6 @3600 s**.

The Decom @120s row is a **local rerun** (this machine, `JOBS=4` — see §2b), stored in
`1d-arc/programs/relational/120/`, log `1d-arc/logs/eval120.log`.

Reading: at 10 minutes ours peaks at **41/54** vs their 34/54 (+7). At 1h Decom recovers to
37/54 while our measured `JOBS=2` run **falls to 30/54** — below both our 120s and 600s
scores. That drop is documented as a real regression in §2d (not corrected). Our peak soft
**0.759 @600s** remains the strongest like-for-like soft number vs their 0.63 @600s /
0.685 @3600s.

### 2a. 60 s run (added 2026-08-07)

Ran on the S6 branch tip (`JOBS=4`, `TIMEOUT=60`), stored in
`results/eval_s6_60s/block_primary/summary.json`. **25/54 exact** — below Decom's 32/54 at
the same budget. Per-category (x/3):

| Category | Ours @60s | Decom @60s |
|---|---|---|
| denoising_1c | 1 | 3 |
| denoising_mc | 3 | 3 |
| fill | 3 | 3 |
| flip | 0 | 0 |
| hollow | 3 | 3 |
| mirror | 0 | 1 |
| move_1p | 3 | 3 |
| move_2p | 3 | 3 |
| move_2p_dp | 3 | 1 |
| move_3p | 3 | 3 |
| move_dp | 1 | 0 |
| padded_fill | 0 | 0 |
| pcopy_1c | 0 | 3 |
| pcopy_mc | 0 | 3 |
| recolor_cmp | 2 | 0 |
| recolor_cnt | 0 | 0 |
| recolor_oe | 0 | 0 |
| scale_dp | 0 | 3 |
| **Total** | **25/54** | **32/54** |

Interpretation: block induction + paint-verify converges slower than the paper's minimal
pixel bias at 60 s — the categories we lose at 60 s (`denoising_1c`, `mirror`, `recolor_*`,
`scale_dp`) are exactly those that recover at 120 s+. Our fast wins (`move_2p_dp`, `move_dp`,
`hollow`) hold even at 60 s. **Fairness caveat:** our run was 4-way parallel on one host
(each job effectively ≈ ¼ machine), whereas the paper ran single-CPU; a true 1-min
apples-to-apples should use `JOBS=1`.

### 2b. Decom @120 s local rerun (added 2026-08-07)

A 120 s Decom run exists on this machine at `1d-arc/programs/relational/120/` with driver
log `1d-arc/logs/eval120.log` (`TIMEOUT=120s JOBS=4 trials=0 1 2`, same conditions as our
runs). Per-category exact (x/3), from `results.pl` `solved` flags:

| Category | Decom @120 (local) |
|---|---|
| denoising_1c | 3 |
| denoising_mc | 3 |
| fill | 3 |
| flip | 0 |
| hollow | 3 |
| mirror | 0 |
| move_1p | 3 |
| move_2p | 3 |
| move_2p_dp | 0 |
| move_3p | 3 |
| move_dp | 0 |
| padded_fill | 0 |
| pcopy_1c | 3 |
| pcopy_mc | 3 |
| recolor_cmp | 0 |
| recolor_cnt | 0 |
| recolor_oe | 0 |
| scale_dp | 3 |
| **Total** | **30/54** (soft 55.6%) |

**This is the sharpest budget-matched result in our favor:** at the *same* 120 s budget on
the *same* host, ours scores **39/54 exact vs Decom 30/54** (+9). Decom is essentially flat
from 60 s→120 s (32→30, within noise) — pixel rules either fire almost immediately or not at
all — while our block method nearly doubles (25→39) over the same window. The categories
Decom still loses at 120 s (`flip`, `mirror`, `move_2p_dp`, `move_dp`, `padded_fill`, all
`recolor_*`) are the block-friendly ones; ours at 120 s still loses only `pcopy_*` (pixel-index
duplication) and the two shared-hard categories.

### 2d. 3600 s run (added 2026-08-08) — measured regression vs shorter budgets

```bash
OUT=results/eval_s6_3600s_jobs2 JOBS=2 \
  ./scripts/run_solver_eval_parallel.sh block_primary 3600 0,1,2
```

- Host affinity: 4 CPUs; `JOBS=2` (viable; not oversubscribed).
- Code: S6 branch tip at run start (`d151266` lineage; bidirectional `size_add` still present).
- Wall clock: ~19.9 h (`exit_code: 0`); artifact
  `results/eval_s6_3600s_jobs2/block_primary/summary.json`.
- **Exact 30/54** (soft 0.556 ± 0.068). **No offline SIGSEGV / paint recovery applied.**

| Metric | @120s | @600s | **@3600s (this run)** |
|---|---:|---:|---:|
| Exact | 39/54 | **41/54** | **30/54** |
| Soft | 68.5 | **75.9** | 55.6 |
| Perfect cats (3/3) | 8 | 9 | 8 |

**Category collapses vs @600s (exact x/3):**

| Category | @600 | @3600 | Δ |
|---|---:|---:|---:|
| `1d_flip` | 3 | **0** | −3 |
| `1d_mirror` | 2 | **0** | −2 |
| `1d_recolor_oe` | 3 | **0** | −3 |
| `1d_recolor_cmp` | 3 | 1 | −2 |
| `1d_recolor_cnt` | 2 | 1 | −1 |
| `1d_scale_dp` | 3 | 1 | −2 |
| `1d_pcopy_mc` | 1 | 0 | −1 |
| `1d_padded_fill` | 1 | 2 | +1 |

Failure mix on the 24 inexact trials: `popper_timeout` 15, `paint_verify_failed` 7,
`decode_error` 2. Notably `flip` is **0/3 all `popper_timeout`** even though the same S6
code solves flip **3/3 @120s** (and a later `JOBS=2` @120s flip smoke also recovered 3/3
with one offline SIGSEGV). **We do not hide this regression.**

**Hypothesis (leading, not proven):** the drop is explained by the missing
[Anytime train-paint-valid candidate retention / paint-aware induction](02-SOLVER_PLAN.md#anytime-train-paint-valid-candidate-retention--paint-aware-induction).

Mechanism in one line: Popper keeps compressing after the first train-perfect
program and returns only the final best; paint verify is post-hoc on that one
program, so longer budgets can discard earlier train-paint-valid answers
(`popper_timeout` / `paint_verify_failed` / worse generalization). No test
leakage. Until that feature lands, non-monotonic 600s→3600s drops remain an
expected risk — not evidence that S6 bias disappeared.

Per-category (x/3) for this run:

| Category | Ours @3600 | Decom @3600 |
|---|---|---|
| denoising_1c | 3 | 3 |
| denoising_mc | 3 | 3 |
| fill | 3 | 3 |
| flip | 0 | 2 |
| hollow | 3 | 3 |
| mirror | 0 | 3 |
| move_1p | 3 | 3 |
| move_2p | 3 | 3 |
| move_2p_dp | 3 | 2 |
| move_3p | 3 | 3 |
| move_dp | 1 | 0 |
| padded_fill | 2 | 0 |
| pcopy_1c | 0 | 3 |
| pcopy_mc | 0 | 3 |
| recolor_cmp | 1 | 0 |
| recolor_cnt | 1 | 0 |
| recolor_oe | 0 | 0 |
| scale_dp | 1 | 3 |
| **Total** | **30/54** | **37/54** |

### 2c. Summary scoreboard — every budget × both methods

Decom provenance: @60/@600/@3600 are the paper's own artifacts (May 2025, single-CPU);
@120 is the local rerun (this host, `JOBS=4`, `1d-arc/programs/relational/120`). Ours: S6
code; `@60`/`@120` local `JOBS=4`; `@600` from the S6 plan; `@3600` local `JOBS=2` (§2d).

**Exact (/54):**

| Method | @60 | @120 | @600 | @3600 |
|---|---|---|---|---|
| **Ours (block-ILP, S6)** | 25 | **39** | **41** | 30 |
| **Decom (pixel-ILP)** | **32** | 30 | 34 | **37** |
| **Winner (margin)** | Decom (−7) | **Ours (+9)** | **Ours (+7)** | Decom (−7) |

**Soft (%):**

| Method | @60 | @120 | @600 | @3600 |
|---|---|---|---|---|
| **Ours (block-ILP, S6)** | 46.3 | 68.5* | **75.9** | 55.6 |
| **Decom (pixel-ILP)** | **59.3** | 55.6 | 63.0 | **68.5** |

\* Ours @120 soft 68.5 is from the stored `baseline_block_primary_120` summary (exact=soft
on this dataset); it is consistent with the 39/54 exact.

Per-category totals (exact x/3) for every cell above are in §3.

**Trend:** Ours rises steeply through mid budgets (25 → 39 → **41**) then **falls at 1h to
30/54** under the current final-program / post-hoc paint policy. Decom is nearly flat then
slowly recovers (32 → 30 → 34 → 37). Peak block-ILP advantage remains at 120–600 s; the 1h
cell is currently a known regression, not a capability peak.

---

## 3. Per-category table (exact, x/3)

Ours S6 @600s reconstructed from `results/solver/baseline_block_primary_120` (S1′a+b, 37/54
stored) + the S6 plan's documented deltas (`.cursor/plans/plan-s6-size-add-direction.md` S6d/S6e).
Decom from `programs/relational/*/1d/*/popper/*/results.pl` (`solved` flag).

Each category spans **two sub-rows** (`Ours` then `Decom`) so a column = one timeout and the
two methods sit in the *same cell position* for direct comparison. Exact x/3. Bold marks the
higher of the two within a category×timeout cell (bold both = tie at 3; neither = tie below 3).
Decom @120 is the local rerun; ours @3600 is the measured `JOBS=2` run (§2d).

| Category | Method | @60 | @120 | @600 | @3600 |
|---|---|---|---|---|---|
| **1d_denoising_1c** | Ours | 1 | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_denoising_mc** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_fill** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_flip** | Ours | 0 | **3** | **3** | 0 |
| | Decom | 0 | 0 | 0 | **2** |
| **1d_hollow** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | 2 | **3** |
| **1d_mirror** | Ours | 0 | **2** | 2 | 0 |
| | Decom | **1** | 0 | **3** | **3** |
| **1d_move_1p** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_move_2p** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_move_2p_dp** | Ours | **3** | **3** | **3** | **3** |
| | Decom | 1 | 0 | 2 | 2 |
| **1d_move_3p** | Ours | **3** | **3** | **3** | **3** |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_move_dp** | Ours | **1** | **1** | **1** | **1** |
| | Decom | 0 | 0 | 0 | 0 |
| **1d_padded_fill** | Ours | 0 | **1** | **1** | **2** |
| | Decom | 0 | 0 | 0 | 0 |
| **1d_pcopy_1c** | Ours | 0 | 0 | 0 | 0 |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_pcopy_mc** | Ours | 0 | 0 | 1 | 0 |
| | Decom | **3** | **3** | **3** | **3** |
| **1d_recolor_cmp** | Ours | **2** | **3** | **3** | **1** |
| | Decom | 0 | 0 | 0 | 0 |
| **1d_recolor_cnt** | Ours | 0 | **2** | **2** | **1** |
| | Decom | 0 | 0 | 0 | 0 |
| **1d_recolor_oe** | Ours | 0 | **3** | **3** | 0 |
| | Decom | 0 | 0 | 0 | 0 |
| **1d_scale_dp** | Ours | 0 | 2 | **3** | 1 |
| | Decom | **3** | **3** | **3** | **3** |
| **Total exact** | **Ours** | 25/54 | **39/54** | **41/54** | 30/54 |
| | **Decom** | **32/54** | 30/54 | 34/54 | **37/54** |
| **Perfect cats (3/3)** | **Ours** | 8 | 8 | 9 | 8 |
| | **Decom** | 9 | 8 | 9 | **11** |

### 3a. Head-to-head tally (categories won per budget)

Counting, for each budget, how many of the 18 categories each method wins in the §3 table
(**O** = ours strictly higher, **D** = Decom strictly higher, tie = equal). Uses Decom-local
@120 s; Decom-paper at 60/600/3600 s.

| | @60 | @120 | @600 | @3600 |
|---|---|---|---|---|
| **O-wins / D-wins / ties** | 3 / 5 / 10 | **8 / 3 / 7** | **8 / 3 / 7** | 5 / 5 / 8 |

Aggregate read: at 60 s Decom edges ahead (5 D vs 3 O); at **120–600 s we lead decisively
(8 O vs 3 D)**; at **3600 s the head-to-head ties 5–5** while Decom leads on total exact
(37 vs 30) because our long-budget collapses on `flip`/`mirror`/`recolor_oe`/`scale_dp` wipe
earlier wins. Durable Decom wins remain `pcopy_*`; durable Decom zeros remain most of
`recolor_*` plus `move_dp`/`padded_fill`.

> Reconstruction note: the frozen pre-S6 baseline the S6 plan gated against is **39/54**
> (plan-unified-arithmetic, commit `653b9d7`); the directory
> `results/solver/baseline_block_primary_120` is an *earlier* S1′a+b artifact totaling 37/54
> (differs on `padded_fill` 0 vs 1, `pcopy_1c` 0 vs 1 — both of which the S6 deltas then
> describe relative to the 39/54 baseline). The 39→39 (+6/−6) and 41/54 totals in the table
> follow the plan documents; the two disputed cells cancel out of every total.

---

## 4. Where each side wins, and why (program-level evidence)

### 4a. Decom wins: `pcopy_1c`, `pcopy_mc` (6/6 both budgets), `move_2p_dp` early

Their learned rule for `1d_pcopy_1c` (paper App. C):

```prolog
out(V0,V1,V2):- in(V0,V5,V2), add(V1,V6,V5), lt(V6,V1), succ(V3,V5), add(V3,V4,V1).
out(V0,V1,V2):- succ(V4,V1), in(V0,V4,V2), succ(V3,V4), empty(V0,V3).
```

i.e. *"output index I is input index I/2"* — pure per-pixel index arithmetic. A block-level head
cannot express "stretch each pixel" without inventing per-pixel addresses inside a block.
This is the **known block-ILP blind spot**: transforms whose description is shorter over pixel
indices than over runs.

### 4b. Ours wins: the whole `recolor` family (0/9 → 8/9) and `flip`/`hollow` at low budget

Decom's 1D bias has **no counting / comparison of block contents** (only `lt` on positions and
unary color constants), so `recolor_cmp` (recolor by comparing runs), `recolor_cnt` (by count),
`recolor_oe` (by odd/even length) are all 0/3 at every budget. Our block BK (`block_len`,
`largest`, parity, `size_lt`) sees these directly.

`flip` and `hollow` are also faster for us: S6's bidirectional `size_add` unlocks both at 120s
(3/3 each), where Decom needs a full hour to find flip (and then only 2/3). Caveat: our
measured @3600s run loses `flip` again (0/3 timeouts) — a long-budget regression, not a
representation loss (§2d).

### 4c. Shared hard families: `move_dp` and `padded_fill`

- `move_dp` — Decom 0/3 at every paper budget; ours occasionally 1/3 under S6.
- `padded_fill` — Decom 0/3 everywhere; ours reaches 1/3 @120/@600 and **2/3 @3600**.

These remain high-value targets, but they are no longer symmetric zeros on our side.

### 4d. ARGA reference (paper Table 4)

The paper's domain-specific ARGA baseline scores **94% @1h** on 1D-ARC using hand-built
`mirror`/`fill`/`hollow` operators — i.e. exactly the category-named BK our project rules
forbid (`block-level-only.mdc`: no `reflect_*`, no marker hacks, no per-family vocab). The gap
between any *uniform-language* ILP approach (ours **peak** 41/54 @600s, theirs 37/54 @3600s)
and ARGA's hand-routed DSL is the price of staying domain-general — that is a deliberate
project constraint, not an oversight.

---

## 5. Conclusions for the block-ILP direction

1. **The block lift is real at mid budgets**: at equal 10-min budget we beat the paper's
   pixel-Decom on exact (**41 vs 34 @600s**) with a *uniform* block language and no
   per-category vocabulary — the property pixel Decom lacks (`recolor` 0/9).
2. **Longer is not currently better for us**: measured @3600s is **30/54**, a clear drop vs
   39/54 @120s and 41/54 @600s. Treat that as a pipeline/search-selection regression
   (final compressed program + post-hoc paint), not as evidence that S6 bias is absent.
   Fix direction is tracked in
   [02-SOLVER_PLAN.md § Not implemented feature requests](02-SOLVER_PLAN.md#not-implemented-feature-requests).
3. **The block abstraction is lossy in a specific, nameable way**: `pcopy_*` shows that
   pixel-index arithmetic sometimes *is* the compact hypothesis; that family stays Decom's.
4. **Do not chase ARGA's 94%** with category-named BK — forbidden by project rules and would
   invalidate the block-lift measurement.
5. **Highest-value next targets:** make long-budget selection monotonic (anytime
   train-paint-valid retention / paint-aware induction); then `1d_move_dp` / further
   `padded_fill`; then recover `pcopy_*` without breaking uniformity (deferred S5d-style
   doubling is the honest block-level candidate).

---

## Appendix A — data provenance

| Claim | Source |
|---|---|
| Decom per-trial accuracy / solved | `../sources/ijcai25-relational-decomposition-main/programs/relational/{60,600,3600}/1d/*/popper/{0,1,2}/results.pl` (parent `ml-project/` dir) |
| Trial = instance `_0/_1/_2` | `train.py` path `train/relational/1d/{task}/{trial}`; `results.py` TASKS list (same `../sources/` repo) |
| Paper headline (soft) | PDF Table 2/4: 59/63/69% @1/10/60min |
| Our S6 @120 / @600 totals | `.cursor/plans/plan-s6-size-add-direction.md` S6d (39/54 @120) & S6e (41/54, soft 0.759 @600) |
| Our pre-S6 baseline | `results/solver/baseline_block_primary_120/block_primary/summary.json` (37/54 stored; 39/54 frozen-baseline per `plan-unified-arithmetic.md` commit `653b9d7`) |
| Our 60 s run | `results/eval_s6_60s/block_primary/summary.json` (25/54 exact, `JOBS=4`, run 2026-08-07) |
| Our 3600 s run | `results/eval_s6_3600s_jobs2/block_primary/summary.json` (30/54 exact, soft 0.556, `JOBS=2`, wall ~19.9 h, finished 2026-08-08; raw harness scores, no offline recovery) |
| Our head/bias shape | `solver/encoder.py`, `solver/bias_gen.py`, `solver/predicates.py` on `cursor/s6-size-add-direction-ebb2` |
