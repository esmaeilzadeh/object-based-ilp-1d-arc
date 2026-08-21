# Copilot instructions for `object-based-ilp-1d-arc`

## Commands

- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e ./popper`
- Smoke run: `./scripts/smoke_solver.sh`
- Hard smoke fixtures: `TIMEOUT=180 ./scripts/smoke_block_hard.sh`
- Single instance (hybrid default): `python -m solver.cli raw_data/onedarcraw/dataset/1d_flip/1d_flip_0.json --mode hybrid_census --timeout 60 --out pred.json --work-dir work/demo`
- Object-only: add `--mode block_primary`
- Full harness: `python -m solver.harness --mode hybrid_census --timeout 60 --trials 0,1,2`
- Sequential eval: `./scripts/run_solver_eval.sh hybrid_census 60 0,1,2`
- Parallel eval: `JOBS=2 OUT=results/eval_local_600 ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2`
- Stability protocol: `./scripts/run_stability_protocol.sh b0 120 3 0,1,2`
- Tests: `pytest solver/tests -q`

## High-level architecture

- **Headline path:** `hybrid_census` → `solve_hybrid`: train-grid `census_match` routes to object `out_block/5` (`solve`) or pixel `out/3` (`pixel_encode` + induce).
- `solver/census.py` — bulky/unit run-count gate (no task names).
- `solver/encoder.py` / `bias_gen.py` / `predicates.py` — object BK/exs/bias.
- `solver/pixel_encode.py` — Decom-style pixel road.
- `solver/induce.py` — Popper child process.
- `solver/verify.py` — object paint-verify; pixel road uses soft-score acceptance.
- `solver/decode.py` — object paint + pixel apply.
- `solver/pipeline.py` — `solve` / `solve_hybrid`.
- `solver/cli.py` / `harness.py` — `--mode` ∈ `{hybrid_census, block_primary}`.

## Key conventions

- Default claim is **census-routed hybrid**, not object-only. Do not report pixel-road solves as block-only wins.
- Bias, BK, and examples are generated per instance from that instance’s grids/facts. Do not switch vocabulary by category/task name.
- Keep marker/mirror geometry hacks and answer-leaking BK out unless the user gives explicit dedicated confirmation.
- Train success on the object road means paint verification passed. Preserve `failure_reason`, `failure_detail`, `verified_train`, `confidence`, and fallback identity behavior.
- Eval artifacts in `results/`; scratch in `work/`. Prefer `JOBS=2` on small machines.
- Vendored `popper/` is consumed as-is unless fixing a Popper bug on purpose.
