# Copilot instructions for `object-based-ilp-1d-arc`

## Commands

- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e ./popper`
- Smoke run: `./scripts/smoke_solver.sh`
- Hard smoke fixtures: `TIMEOUT=180 ./scripts/smoke_block_hard.sh`
- Single instance: `python -m solver.cli raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json --timeout 60 --out pred.json --work-dir work/demo`
- Full harness: `python -m solver.harness --mode block_primary --timeout 60 --trials 0,1,2`
- Sequential eval wrapper: `./scripts/run_solver_eval.sh block_primary 60 0,1,2`
- Parallel eval wrapper: `JOBS=2 OUT=results/eval_local_120 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2`
- Stability protocol: `./scripts/run_stability_protocol.sh b0 120 3 0,1,2`
- Tests: `pytest solver/tests -q`
- Single test file: `pytest solver/tests/test_encoder.py -q`
- Single test case: `pytest solver/tests/test_encoder.py -k test_name -q`

## High-level architecture

- The main solver path is `block_primary`: encode one 1D-ARC instance into object/block facts, run Popper once, paint-verify the learned program on train, decode the test, and soft-score the result.
- `solver/encoder.py` builds the instance-specific BK/exs/bias artifacts and the Python-only geometry used during decode.
- `solver/bias_gen.py` derives Popper bias mechanically from the instance BK/exs; `solver/predicates.py` is the frozen predicate inventory and type system.
- `solver/induce.py` wraps Popper in a child process with timeout handling and literal limits.
- `solver/verify.py` is the train acceptance gate; `solver/decode.py` turns `out_block/5` into pixels.
- `solver/pipeline.py` orchestrates the full solve and records failure reasons / fallback identity behavior.
- `solver/harness.py` runs batch evals, writes per-task JSON, and emits `summary.json` plus run provenance.
- `solver/pixel_encode.py` and `solve_hybrid` exist for the auxiliary census/pixel road, but the repo’s primary path is object/block-first.

## Key conventions

- Stay on the object/block path unless the user explicitly asks for something else. The canonical head is `out_block/5`; the repo is organized around `block_primary`.
- Bias, BK, and examples are generated per instance from that instance’s facts. Do not introduce task-name/category switches or hand-authored family-specific bias files.
- Use the typed-role object encoding (`b*`, `s*`, `v*`, `sm*`) and the lean block facts; keep geometry and decode helpers in Python when they are not meant to be searchable BK.
- Train success means paint verification passed, not just that Popper returned a program. Failures should preserve `failure_reason`, `verified_train`, `confidence`, and fallback identity behavior.
- Keep eval artifacts in `results/` and scratch artifacts in `work/`; do not treat them as source.
- Batch evals should preserve run provenance (`run_manifest.json`, `summary.json`) and use viable parallel settings; `JOBS=2` is the repo’s preferred small-machine default.
- The vendored `popper/` directory is consumed as-is; repo changes should target the solver package, scripts, and docs unless a Popper bug is explicitly being addressed.
