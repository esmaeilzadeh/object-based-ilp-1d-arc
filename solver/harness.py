"""Ablation harness over 1D-ARC JSON files."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from solver.pipeline import solve

MODES = {
    "pixel_only": dict(include_blocks=False, include_pixels=True, include_aggregations=False, ladder=False, force_bias="pixel"),
    "block_only": dict(include_blocks=True, include_pixels=False, include_aggregations=True, ladder=True),
    "dual": dict(include_blocks=True, include_pixels=True, include_aggregations=True, ladder=True, canonicalize_colors=False),
    "dual_no_agg": dict(include_blocks=True, include_pixels=True, include_aggregations=False, ladder=True),
    "dual_no_ladder": dict(include_blocks=True, include_pixels=True, include_aggregations=True, ladder=False),
    "dual_full": dict(include_blocks=True, include_pixels=True, include_aggregations=True, ladder=True, canonicalize_colors=True),
}


def discover(dataset_root: Path) -> List[Path]:
    return sorted(dataset_root.glob("*/*.json"))


def run_one(path: Path, mode: str, timeout: int, out_dir: Path) -> dict:
    kwargs = dict(MODES[mode])
    t0 = time.time()
    result = solve(
        path,
        timeout=timeout,
        work_dir=out_dir / path.stem,
        **kwargs,
    )
    elapsed = time.time() - t0
    gold = None
    obj = json.loads(path.read_text())
    if obj["test"] and "output" in obj["test"][0]:
        from solver.grid import flatten
        gold = flatten(obj["test"][0]["output"])
    ok = gold is not None and list(result.predicted_grid) == list(gold)
    return {
        "file": str(path),
        "task": path.parent.name,
        "mode": mode,
        "ok": ok,
        "level": result.level,
        "confidence": result.confidence,
        "elapsed": elapsed,
        "predicted": result.predicted_grid,
        "gold": gold,
    }


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("raw_data/onedarcraw/dataset"))
    ap.add_argument("--mode", default="dual", choices=list(MODES))
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--trials", type=str, default="", help="comma ids e.g. 0,1,2")
    ap.add_argument("--out", type=Path, default=Path("results/solver"))
    args = ap.parse_args(argv)

    files = discover(args.dataset)
    if args.trials:
        allowed = {int(x) for x in args.trials.split(",")}
        files = [f for f in files if any(f.stem.endswith(f"_{i}") for i in allowed)]
    if args.limit:
        files = files[: args.limit]

    out_dir = args.out / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    by_task: Dict[str, List[bool]] = defaultdict(list)
    for i, f in enumerate(files):
        print(f"[{i+1}/{len(files)}] {f}")
        row = run_one(f, args.mode, args.timeout, out_dir)
        rows.append(row)
        by_task[row["task"]].append(row["ok"])
        (out_dir / f"{f.parent.name}_{f.stem}.json").write_text(json.dumps(row, indent=2))

    n = len(rows)
    acc = sum(1 for r in rows if r["ok"]) / n if n else 0.0
    summary = {
        "mode": args.mode,
        "n": n,
        "accuracy": acc,
        "per_task": {t: sum(v) / len(v) for t, v in by_task.items()},
    }
    print(json.dumps(summary, indent=2))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
