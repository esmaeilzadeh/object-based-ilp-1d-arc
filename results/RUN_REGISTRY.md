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

## Related (not a separate scoreboard)

| id | note |
|----|------|
| `eval_60s_functional_color` | Intermediate branch `cursor/functional-color-negs` only; merged into the combined ablation above — do not treat as a second headline. Local partial tree may exist under `results/eval_60s_functional_color/` (incomplete / non-citable alone). |
| `eval_60s_instance_colors` | Branch `cursor/instance-color-constants` @ `ab523e69db7832f14e77e64361cd544e770e9d69`. **31/54** exact = soft @60 s, `JOBS=4`, trials `0,1,2`. Local artifacts: `results/eval_60s_instance_colors/block_primary/summary.json`. Not a headline; −9 vs 40/54. Recolor_cmp stays 3/3 (novel `vK`). Denoise/fill/padded_fill/mirror mostly timeout or paint-verify. Confirm at `JOBS=2` before treating as a language verdict. |
