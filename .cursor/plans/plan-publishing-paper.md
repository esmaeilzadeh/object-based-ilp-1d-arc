# Plan: Publishing paper (block-ILP vs pixel Decom on 1D-ARC)

**Status:** PROPOSED — conversation summary turned into a publishing plan. Wait for
explicit implement/write-go-ahead before drafting the paper body.
**Paper type:** **Methodological contribution with strong empirical evaluation** — not a
simple empirical bake-off (see §0a).
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical language only;
no category-named BK; no ARGA-style operator chasing.
**Working comparison report:** `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md`
**Best code tip:** `cursor/s6-size-add-direction-ebb2` (Bid-anchored `out_block(E,Bid,Off,Len,Color)`)
**Reference:** Hocquette & Cropper, *Relational Decomposition for Program Synthesis*
(IJCAI 2025 / arXiv:2408.12212), code in `sources/ijcai25-relational-decomposition-main`
and local Decom reruns in `1d-arc/`.

---

## 0. One-sentence thesis (optimize the paper for this)

**We introduce a uniform block-anchored encode–induce–decode method for 1D-ARC ILP
(`out_block(E, Bid, Off, Len, Color)` + mechanical BK/bias + paint decode), and show it
outperforms pixel Relational Decomposition on the standard 54-task slice at matched
budgets ≥120 s, with a named failure mode (`pcopy`) and without category-named background
operators.**

---

## 0a. Paper type: methodological + empirical (not “simple empirical”)

### Positioning

| Label | Fit? | Why |
|---|---|---|
| **Methodological paper** | **Yes — lead with this** | The contribution is *how* to cast 1D-ARC as an ILP task: head shape, uniform BK/exs/bias, typed roles, Bid+Off anchoring, closed decode + paint-verify — same genre as Decom’s “decompose examples into relational facts,” but at **object** granularity with a **paintable** head |
| **Empirical evaluation** | **Yes — required half** | 54-task scoreboard, budget curves, complementarity vs Decom, ablations (indep-out → 0/54) |
| **Simple empirical only** | **No — undersells** | “We tried blocks and scored higher” invites “why not ARGA?” and hides the reusable encode/decode framing |

### What makes the framing special (beyond “block level”)

“Block level” alone is thin. The method is the full loop:

| Piece | Methodological role |
|---|---|
| Head `out_block(E, Bid, Off, Len, Color)` | Defines *what* is learned (object transform), not just input features |
| Uniform mechanical BK / exs / bias | Design rule for hypothesis language (no category / task-name routing) |
| Typed roles (`b*` / `s*` / `v*` / `r*`) | Role isolation so ILP cannot unify block id with length/color/position |
| Bid+Off anchoring + decode | Closed encode → induce → decode; absolute paint from input geometry |
| Paint-verify gate | Train-exact before test decode; junk programs fail closed-world |
| Explicit refusals | No markers/reflect, no answer-leaking BK, no pixel-head rescue — defines the claim |

### Recommended one-sentence positioning for abstracts

> We introduce a **uniform block-anchored encode–induce–decode method** for 1D-ARC ILP, and
> show empirically that it outperforms pixel Relational Decomposition at matched timeouts
> ≥120 s under a domain-general bias.

### Framing pitfalls

- **Undersell:** pure empirical bake-off → reviewers miss the reusable method.
- **Oversell:** “new general ILP paradigm” without Decom head-to-head + negatives → thin method paper.
- **Wrong competitor:** claiming SOTA over ARGA (hand-built operators) breaks project rules and the domain-general claim.

---

## 1. Venue strategy (agreed focus)

| Priority | Target | Role |
|---|---|---|
| **1 — goal** | **IJCAI** (or **AAAI** as same-tier twin) | Peer venue of the Decom paper; primary peer-reviewed aim |
| **0 — ship first** | **arXiv cs.AI** (+ optional cs.LG / cs.LO) | Post as soon as 3600 s numbers are in and story is stable |
| **2 — Plan B** | ILP symposium / ARC or neuro-symbolic workshop | Only if main-track reviews say “nice but incremental” |

**Do not Plan-A:** NeurIPS/ICML main track (weak fit for a Popper/BK representation study
unless reframed with much broader empirical scale).

**Do not chase:** ARGA’s ~94% via hand-built `mirror`/`fill`/`hollow` operators — forbidden by
project rules and would invalidate the “uniform language / block lift” claim.

### What “IJCAI-flashy” means (clarified in conversation)

Top general venues often reward big absolute jumps, clear SOTA one-liners, or multi-domain
scale. Our current profile is a **careful method + evaluation study** (~39–41/54 vs Decom
~30–37/54, complementary wins/losses, lose at 60 s / win at ≥120 s). That can be
**scientifically solid** without looking flashy. Write for IJCAI/AAAI with an honest claim;
do not oversell.

---

## 2. Technical story to put in the paper (from this chat)

### 2.1 Method (S6 / current best) — encode → induce → decode

- **Head:** `out_block(Ex, Bid, Off, Len, Color)` — output block anchored to an input block id
  with relative offset (not independent Rank+Start).
- **Pipeline:** encode ARC JSON → lean typed-role BK + `exs_object` + mechanical bias → Popper
  induce → paint-verify on train → decode to pixels → soft score.
- **Encoding:** maximal runs; colored `block/4`; lean BK allowlist; typed atoms `b*/s*/v*/r*`;
  uniform `size_add` / `size_sum3` / gaps / components; per-instance bias from BK/exs only.
- **Decode:** Bid geometry + Off → absolute paint; overlap/OOB fail.

### 2.2 Negative results that strengthen the paper

| Experiment | Outcome | Lesson |
|---|---|---|
| Independent-out `out_block(E,Rank,Start,Len,C)` | **0/54** @120 s; ported scaffolding recovered only ~partial | Bid-anchoring was the right decision; Rank+Start recreates Bid poorly and adds Start arithmetic / rank walls |
| Output-gap Offset head idea | Half-helpful for flip/timeouts; regresses move; does not fix count-changing transforms | Do not pursue as primary head |
| Marker / reflect / category BK | Explicitly refused | Domain-general claim stays clean |

### 2.3 Empirical comparison vs Decom (same 54-task slice: 18 cats × first-3)

Protocol verified: Decom `trial` ∈ {0,1,2} = dataset instances `_0/_1/_2`. Exact = all-pixels
correct (`solved: True` for them; `verified_train` + grid equality for us). Soft % is separate
(TN-padded cell accuracy).

**Headline exact (/54)** — fill ours@3600 when cloud run completes:

| Method | @60 | @120 | @600 | @3600 |
|---|---|---|---|---|
| Ours (block-ILP, S6) | 25 | **39** | **41** | *(cloud run in flight)* |
| Decom (pixel-ILP) | **32** | 30 (local) | 34 | 37 |
| Winner | Decom (−7) | **Ours (+9)** | **Ours (+7)** | TBD |

**Complementarity (durable):**

- **Ours wins:** `recolor_*` family (Decom 0/9), `flip`/`hollow` earlier, `move_2p_dp` /
  partial `move_dp`.
- **Decom wins:** `pcopy_1c` / `pcopy_mc` (pixel-index duplication — structural block blind spot).
- **Both fail:** `move_dp` (mostly), `padded_fill`.

**Trend:** Ours climbs with budget (25→39→41); Decom nearly flat after 60 s (32→30→34→37).
Crossover between 60 s and 120 s — block induction needs >1 min, then dominates.

Stored artifacts:

- Ours @60: `results/eval_s6_60s/`
- Ours @120/@600: S6 plan + `results/solver/baseline_block_primary_120/` (see comparison doc caveats)
- Decom all budgets: `1d-arc/programs/relational/{60,120,600,3600}/` (+ paper originals)
- Comparison writeup: `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md`

### 2.4 Hardware fairness (strengthens, does not weaken, the ≥120 s claim)

| | Ours (local) | Decom paper (§5.5) |
|---|---|---|
| Machine | Dell Precision M4600 laptop | HPC node |
| CPU | i7-2720QM @ 2.20 GHz (4C/8T, ~2011) | Dual Xeon Gold 6138 @ 2.0 GHz (40 cores, ~2017) |
| Per-task CPU | Contended (`JOBS=4`–`7` on 8 threads) | **1 CPU per system** |
| RAM | ~16 GB | 192 GB DDR4 |

**Validity takeaway:**

- For a **single task** with a wall-clock timeout, what matters is **single-core throughput**
  (architecture + clock + cache), **not** core count. Extra cores only speed up the *suite*
  when running parallel jobs; they do not enlarge one task’s 60 s search budget.
- Same nominal GHz ≠ same work: their quieter modern Xeon still does more per second than a
  2011 mobile i7; plus `JOBS>1` contention can *shrink* effective per-task time.
- Therefore beating Decom at matched wall-clock ≥120 s on the weaker machine is
  **conservative in our favor** (more valid, not less).
- Cleanest head-to-head: **same-host @120** (local Decom rerun vs ours) → **39 vs 30**.
- Soften the @60 loss (25 vs 32) as possibly timeout-/machine-sensitive; optional `JOBS=1`
  sanity check if needed for the paper.

---

## 3. Paper outline (draft when writing starts)

Lead with **method** (encode–induce–decode), then evaluate — not “results first.”

1. **Introduction** — program synthesis / 1D-ARC; Decom’s pixel decomposition; our claim:
   a *uniform object-anchored encode–induce–decode* ILP method (not merely “use blocks”).
2. **Related work** — Decom (IJCAI’25), ARGA/BEN (domain-specific operators), HL, Popper;
   position as sibling *representation* contribution to Decom.
3. **Method** — Bid+Off head; mechanical BK/exs/bias; typed roles; decode + paint-verify;
   explicit design refusals (markers, category routing, answer-leaking BK, indep-out).
4. **Experimental setup** — 54-task slice, Popper, timeouts, exact vs soft; hardware note
   (laptop vs HPC; why ≥120 s wins are conservative); same-host @120 fairness.
5. **Results** — scoreboard + sub-row per-category table; complementarity; budget trend.
6. **Ablations / negatives** — indep-out collapse; why Bid-anchoring matters; Offset-head
   deferred.
7. **Limitations** — `pcopy` wall; no 2D ARC yet; 3600 s until filled; 60 s sensitivity.
8. **Conclusion** — method + empirical validation at ≥120 s; future: `move_dp` /
   `padded_fill` / honest `pcopy` recovery without category BK.

---

## 4. Checklist before arXiv / IJCAI draft

- [ ] Cloud 3600 s eval finishes; fold ours@3600 into comparison doc §2 / §2c / §3
- [ ] Freeze one S6 tip commit + exact command lines for reproducibility
- [ ] Resolve / footnote baseline 37 vs 39 exact reconstruction ambiguity (already noted in doc)
- [ ] Optional but IJCAI-helpful: one extra ablation or second domain (even a small ARC subset)
- [ ] Write arXiv preprint: **method section first** (encode/decode/bias), then comparison empirics
- [ ] Submit IJCAI/AAAI; keep workshop/ILP as Plan B

---

## 5. Explicit non-goals for the paper

- No category-named BK or marker/reflect geometry to inflate scores
- No claiming SOTA over ARGA
- No presenting indep-out or Offset head as the main method
- No framing as a **simple empirical-only** paper (undersells encode/decode method)
- No mixing soft-% and exact-/54 in the same table cells without labeling
- No arguing “more cores = stronger Decom timeout” — per-task timeout is single-core work

---

## 6. Conversation provenance (this session)

Topics covered and folded into this plan: encode/decode state; Offset-head idea (deferred);
indep-out judged a failure vs Bid-anchoring; S6 branch as best pre-indep code; full comparison
report vs Decom; 60 s / 120 s local evals; scoreboard + sub-row category tables; publishing
venue discussion (arXiv → IJCAI/AAAI, ILP/workshop Plan B); clarification of “IJCAI-flashy”;
**paper type = methodological + empirical** (special encode–induce–decode framing, not simple
empirical); **hardware fairness** (laptop vs Xeon; cores vs clock; ≥120 s wins are
conservative); cloud agent for 3600 s (`bc-2d58c401-c0f2-44d8-9e10-ecf27d2bad45`, JOBS=7).
