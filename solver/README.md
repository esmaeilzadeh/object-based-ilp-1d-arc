# Object-based ILP 1D-ARC Solver

Generic per-instance solver for 1D-ARC JSON problems (3 train I/O pairs + 1 test input).
Uses Popper with a **dual pixel + color-block** representation. See [docs/SOLVER_PLAN.md](../docs/SOLVER_PLAN.md).

## Input JSON

```json
{
  "train": [{"input": [[...]], "output": [[...]]}, ...],
  "test":  [{"input": [[...]], "output": [[...]]}]
}
```

## Pipeline

1. Encode grids as pixels + maximal same-color blocks (+ derived relations).
2. Cheap-first ladder: trivial checks → block-only ILP → dual ILP.
3. Accept only programs that exactly reproduce all train outputs.
4. Apply to test input; closed-world decode (background = 0).

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./popper

python -m solver.cli raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json
```

Flags: `--no-ladder`, `--canonicalize-colors`, `--timeout N`.
