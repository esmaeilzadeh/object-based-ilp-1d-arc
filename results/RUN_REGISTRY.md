# Eval run registry

Citable experiment index. Prefer a path + `git_sha` + metric; if SHA/artifacts are missing, say so.

Schema notes: see `.agents/skills/eval-run-provenance/SKILL.md` (`eval-run-meta/v1`).

---

## Headline baseline (Decom comparison)

| Field | Value |
|-------|--------|
| **id** | `eval_60s_first3_j2` |
| **metric** | **40/54** exact @60 s |
| **mode** | `block_primary` |
| **timeout / jobs / trials** | 60 / 2 / `0,1,2` |
| **artifacts** | `results/eval_60s_first3_j2/block_primary/summary.json` (2026-08-11) |
| **role** | Headline “Ours” in `docs/04-EVALUATION.md` |

---

## Ablation: functional color + staged paint-in-induction (@60 s)

Single **combined** experiment (do not score the two changes separately on the scoreboard):

1. Functional color uniqueness (`non_functional` BK + `functional_test`) instead of wrong-color negs  
2. Staged train paint-check inside Popper (`paint_test`) after block-complete candidates  

| Field | Value |
|-------|--------|
| **id** | `eval_60s_paint_induction` (combined stack) |
| **branch** | `cursor/paint-in-induction` |
| **git_sha** | `c5bcfa9185f905c567c5493ed5c7ed30a297694d` (code tip for the stack) |
| **timeout / jobs / trials** | 60 / 2 / `0,1,2` |
| **host profile** | Cloud Agent VPS (4 vCPU, `JOBS=2`) — same knobs as 40/54 baseline |
| **implied exact** | **41/54** (+1 vs baseline) from category deltas below |
| **provenance** | `best_effort_experiment_report` until `results/eval_60s_paint_induction/block_primary/summary.json` is committed |
| **docs** | `docs/04-EVALUATION.md` § “Ablation: functional color + staged paint-in-induction” |
| **cloud bookmark** | agent `bc-8322cb2f-ea22-474b-b40e-522d6fe741ea` (same VPS lineage as functional-color try) |

### Category deltas vs `eval_60s_first3_j2` (40/54)

| Category | Was | Now | Δ |
|----------|-----|-----|---|
| `denoising_1c`, `denoising_mc`, `fill`, `hollow`, `move_*` (except `move_dp`), `recolor_*` | 3/3 or 2/3 | unchanged | 0 |
| `mirror` | 2/3 | 3/3 | +1 |
| `scale_dp` | 2/3 | 3/3 | +1 |
| `flip` | 2/3 | 2/3 | 0 |
| `padded_fill` | 2/3 | 1/3 | −1 |
| `pcopy_*`, `move_dp` | partial / 0 | unchanged | 0 |

**Net:** +1 exact task @60 s (mirror + scale_dp − padded_fill).

---

## Cloud Agent 120s first-3 (`eval_120s_first3_j2`)

| Field | Value |
|-------|--------|
| **id** | `eval_120s_first3_j2` |
| **metric** | **32/54** exact @120 s (`block_primary`) |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `eca83c56e1e051cd906c6976ee27df81ef4f6d34` (eval start) |
| **host** | Cloud Agent VPS, 4 vCPU, `JOBS=2` |
| **artifacts** | `results/eval_120s_first3_j2/block_primary/summary.json` |
| **notes** | Two GNU parallel workers exited 139 (SIGSEGV in `libswipl` GC) on `1d_flip_1` and `1d_recolor_oe_0`. `1d_recolor_oe_0` reran clean (`decode_error`). `1d_flip_1` recovered after isolating `apply_object_program` in a subprocess (train `bk.pl` + `test_bk.pl` must not share one janus engine). Parallel summary now still writes if a worker segfaults. |

---

## Census-fail pixel road vs Decom (`eval_120s_mismatch21_j2`)

Not a block-lift result. `hybrid_census` on the 21 first-3 tasks where `census_match` is false (pixel `out/3` fragment only).

| Field | Value |
|-------|--------|
| **id** | `eval_120s_mismatch21_j2` |
| **metric** | **18/21** exact @120 s (`hybrid_census` census-fail subset) |
| **soft** | 0.857 (same as exact; misses score 0) |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` (mismatch families only) |
| **git_sha** | `014b89748fcd9077d1c20d66305553210af946ef` |
| **branch** | `cursor/decom-pixel-fragment-92ee` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_mismatch21_j2/hybrid_census/summary.json` |
| **vs paper Decom** | **18/21** — same split: `denoising_1c`/`fill`/`hollow`/`denoising_mc`/`pcopy_*` 18/18, `padded_fill` 0/3 |
| **notes** | Closes the previous **9/21** (`block_primary` on these families). Smoke `pcopy_1c_0`, `pcopy_mc_0`, `denoising_mc_0` all exact before the 21-task sweep. `git_dirty=true` at run start because local smoke/result trees existed; code SHA is the four pixel-road commits. |

---

## Census-match hybrid block road (`eval_120s_match33_j2`)

`hybrid_census` bulky+unit `out_block`/`out_pixel` heads on the 33 first-3 tasks where `census_match` is true. Match language unchanged by the pixel-road work.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_match33_j2` |
| **metric** | **16/33** exact @120 s |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` (match families only) |
| **git_sha** | `30d1d9c74967e9630301a43adffdf60fe60f3994` (eval start; solver same as `014b897`) |
| **host** | Cloud Agent VPS, 4 vCPU, `JOBS=2` |
| **artifacts** | `results/eval_120s_match33_j2/hybrid_census/summary.json` |
| **notes** | `flip` 3/3, `move_1p/2p/2p_dp/3p` 12/12, `mirror` 1/3, `move_dp`/`recolor_*`/`scale_dp` 0/15. `1d_recolor_cmp_2` worker 139; reran clean (`paint_verify_failed`). |

---

## Whole `hybrid_census` system (`eval_120s_hybrid_full54_j2`)

Combined first-3 @120s `JOBS=2`: match 33 + fail 21. Not a single parallel invocation; subsets are the two campaigns above.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_hybrid_full54_j2` |
| **metric** | **34/54** exact @120 s (`hybrid_census`) |
| **by path** | census-match hybrid block **16/33**; census-fail pixel **18/21** |
| **soft** | 0.630 (same as exact; misses score 0) |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **artifacts** | `results/eval_120s_hybrid_full54_j2/hybrid_census/summary.json` |
| **vs `block_primary` @120s** | 34/54 vs 32/54 (`eval_120s_first3_j2`) — pixel road recovered `denoising_mc`+`pcopy_*`; match path is a different object language than `block_primary` |
| **vs paper Decom** | Decom comparison on the **pixel** subset is 18/21; do not report 34/54 as beating Decom |

---

## Single-invocation two-head confirm (`eval_120s_allcats_j2`)

Full 54-task `hybrid_census` @120s `JOBS=2` after removing unused `size_even`/`size_odd`. Same split as the combined 34/54 (two-head match, not single `out_block/5`).

| Field | Value |
|-------|--------|
| **id** | `eval_120s_allcats_j2` |
| **metric** | **34/54** exact @120 s (`hybrid_census`) |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `21c78a59c9bb9157d7fc3b3894fdcbc98d2e24f7` |
| **branch** | `cursor/remove-size-parity-92ee` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_allcats_j2/hybrid_census/summary.json` |
| **notes** | All 54 GNU parallel workers exit 0. Confirms combined `eval_120s_hybrid_full54_j2`. Census-match is still bulky+unit two-head (`recolor_cnt`/`scale_dp`/`move_dp` 0 vs `block_primary`). |

---

## Census-match single `out_block/5` (`eval_120s_single_head_j2`)

`hybrid_census` match calls `solve()` (same object head as `block_primary`). Census-fail stays pixel `out/3`.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_single_head_j2` |
| **metric** | **42/54** exact @120 s (`hybrid_census`) |
| **by path** | census-match object **24/33**; census-fail pixel **18/21** |
| **soft** | 0.778 (same as exact; misses score 0) |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `ecc030a31d3237b4e3e991350a3354cab9a6b9c6` |
| **branch** | `cursor/census-match-single-head-92ee` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_single_head_j2/hybrid_census/summary.json` |
| **vs two-head 34/54** | +8: `recolor_cnt` 0→3, `scale_dp` 0→3, `move_dp` 0→1, `mirror` 1→2 |
| **vs `block_primary` 32/54** | pixel recovered `denoising_mc`+`pcopy_*` (18/21); object match 24/33 vs 23/33 (`mirror` 2/3 vs 1/3) |
| **vs paper Decom** | Pixel subset is still **18/21**. Do not report 42/54 as beating Decom. |

---

## Concat `out_block/4` retry (`eval_120s_concat_j2`) — **REVERT**

Start-free concat head (`OutBid, Len, Color`; gaps = `v0`). Popper binds input runs in the body.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_concat_j2` |
| **metric** | **24/54** exact @120 s (`hybrid_census`) |
| **by path** | census-match object **6/33**; census-fail pixel **18/21** |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `af1d6574cf8c8c32600bd7a150cd7150acb8e529` |
| **branch** | `cursor/concat-out-block-ea52` |
| **vs baseline** | `eval_120s_single_head_j2` **42/54** → **24/54** (**−18**) |
| **soft-gate** | **REVERT** — wipe of previously perfect `move_*` (12→0) and `scale_dp` (3→0); `mirror` 2→0; pixel unchanged 18/21; `flip`/`recolor_cnt` held at 3/3 |
| **artifacts** | `results/eval_120s_concat_j2/hybrid_census/summary.json` |
| **note** | Confirms absolute-Start-free concat underfits shift/scale; do not merge as default object head |

---

## Left-margin blocks (`eval_120s_left_margin_move3_j2`) — move* probe only

Concat empty-run gaps replaced by colored `block`/`out_block(E, Bid, Left, Len, Color)`. Decode concatenates `(Left zeros + Len of Color)`. Uniform `size_add(s,k,s+k)` for `k∈{1,2,3}`. First-3 **move* only** (15 tasks), not the 54-task gate.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_left_margin_move3_j2` |
| **metric** | **9/15** exact @120 s (`hybrid_census`, move* first-3) |
| **per cat** | `move_1p` 3/3, `move_2p` 3/3, `move_3p` 3/3, `move_2p_dp` 0/3, `move_dp` 0/3 |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `798b41d7189a1df82a3e3ae49c9ba847fd1523cf` |
| **branch** | `cursor/left-margin-blocks-ea52` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_left_margin_move3_j2/hybrid_census/summary.json` |
| **vs concat** | recovered `1p`/`2p`/`3p` from 0/9 to 9/9; `2p_dp`/`dp` still 0/6 (concat also 0) |
| **vs Bid/Off 42/54** | those families were 12/12 + 1/3 dp; this probe did **not** continue other cats |
| **note** | Winning programs pin `s1`/`s2`/`s3` and `size_add` on Left. `2p_dp`/`dp` need two different object rules and still paint-verify-fail @120s. Do not merge as default. |

Earlier probes on the same branch (not the citable encoding):

| id | SHA | exact | note |
|----|-----|-------|------|
| `eval_120s_left_margin_move_j2` | `59d60b4` | 3/15 | +1 `size_add` only |
| `eval_120s_left_margin_kadd_j2` | `b57a718` | 8/15 | +k closure; Left negs only to s12 |

---

## Input `right_margin/3` (`eval_120s_right_margin2_move_j2`) — move* probe

Input-only `right_margin(E, Bid, Right)` with `Right` = next object's Left (or trailing pad). `out_block/5` unchanged. `block` stays 5-ary.

| Field | Value |
|-------|--------|
| **id** | `eval_120s_right_margin2_move_j2` |
| **metric** | **9/15** exact @120 s (`hybrid_census`, move* first-3) |
| **per cat** | `move_1p` 3/3, `move_2p` 3/3, `move_3p` 3/3, `move_2p_dp` 0/3, `move_dp` 0/3 |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `e97f57916b023ff64fd0875cf7550c6df0f77d01` |
| **branch** | `cursor/input-right-margin-ea52` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_right_margin2_move_j2/hybrid_census/summary.json` |
| **vs left-margin 9/15** | same split; `2p_dp`/`dp` still paint-verify-fail (programs did not use `right_margin`) |
| **note** | Did not continue other cats. Do not merge as default. |

Tried first: `block/6` with Right in the atom (`eval_120s_right_margin_move_j2`, SHA `d4de759`) **7/15** — `2p` 1/3, `2p_dp` timeouts. Reverted that shape.

---

## Census-match left+right-margin (`eval_120s_right_margin_match33_j2`)

OutBid + Left concat head; input `right_margin/3`. First-3 census-match only (33 tasks).

| Field | Value |
|-------|--------|
| **id** | `eval_120s_right_margin_match33_j2` |
| **metric** | **11/33** exact @120 s |
| **per cat** | `move_1p/2p/3p` 9/9; `flip` 1/3; `recolor_cnt` 1/3; rest 0 |
| **timeout / jobs / trials** | 120 / 2 / `0,1,2` |
| **git_sha** | `996820e956a4edb50ac01c500f1370d8d36d3609` |
| **branch** | `cursor/input-right-margin-ea52` |
| **host** | Cloud Agent VPS, 4 vCPU, 15 GiB, 0 swap, `JOBS=2` |
| **artifacts** | `results/eval_120s_right_margin_match33_j2/hybrid_census/summary.json` |
| **note** | `right_margin` unused in all 11 exact-ok programs; 19× `paint_verify_failed`. Do not merge. |

---

## Related (not a separate scoreboard)

| id | note |
|----|------|
| `eval_60s_functional_color` | Intermediate branch `cursor/functional-color-negs` only; merged into the combined ablation above — do not treat as a second headline. Local partial tree may exist under `results/eval_60s_functional_color/` (incomplete / non-citable alone). |
