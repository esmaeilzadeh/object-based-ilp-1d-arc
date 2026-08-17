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

## Related (not a separate scoreboard)

| id | note |
|----|------|
| `eval_60s_functional_color` | Intermediate branch `cursor/functional-color-negs` only; merged into the combined ablation above — do not treat as a second headline. Local partial tree may exist under `results/eval_60s_functional_color/` (incomplete / non-citable alone). |
