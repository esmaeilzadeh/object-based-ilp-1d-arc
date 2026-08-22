"""Ablation harness over 1D-ARC JSON files (exact + paper soft metrics)."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from solver.pipeline import solve, solve_hybrid
from solver.run_meta import collect_run_meta, mark_finished, slim_meta

MODES = {
    "block_primary": {},
    "hybrid_census": {},
}


def discover(dataset_root: Path) -> List[Path]:
    return sorted(dataset_root.glob("*/*.json"))


def run_one(
    path: Path,
    mode: str,
    timeout: int,
    out_dir: Path,
    *,
    run_meta: Optional[dict] = None,
) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected {sorted(MODES)}")
    t0 = time.time()
    if mode == "hybrid_census":
        result = solve_hybrid(
            path,
            timeout=timeout,
            work_dir=out_dir / path.stem,
        )
    else:
        result = solve(
            path,
            timeout=timeout,
            work_dir=out_dir / path.stem,
        )
    elapsed = time.time() - t0
    gold = None
    obj = json.loads(path.read_text())
    if obj["test"] and "output" in obj["test"][0]:
        from solver.grid import flatten

        gold = flatten(obj["test"][0]["output"])
    exact_ok = gold is not None and list(result.predicted_grid) == list(gold)
    row = {
        "file": str(path),
        "task": path.parent.name,
        "mode": mode,
        "ok": exact_ok,
        "exact_ok": exact_ok,
        "soft_accuracy": result.soft_accuracy,
        "soft_matrix": result.soft_matrix,
        "level": result.level,
        "confidence": result.confidence,
        "verified_train": result.verified_train,
        "elapsed": elapsed,
        "predicted": result.predicted_grid,
        "gold": gold,
        "failure_reason": result.failure_reason,
        "failure_detail": result.failure_detail,
        "program": result.program,
    }
    if run_meta is not None:
        row["run_meta"] = slim_meta(run_meta)
    return row


def filter_files(
    files: List[Path],
    *,
    trials: str = "",
    limit: int = 0,
) -> List[Path]:
    if trials:
        allowed = {int(x) for x in trials.split(",") if x.strip() != ""}
        files = [f for f in files if any(f.stem.endswith(f"_{i}") for i in allowed)]
    if limit:
        files = files[:limit]
    return files


def summarize(rows: List[dict]) -> dict:
    n = len(rows)
    exact_acc = sum(1 for r in rows if r.get("exact_ok") or r.get("ok")) / n if n else 0.0
    soft_vals = [float(r.get("soft_accuracy", 0.0)) for r in rows]
    soft_acc = sum(soft_vals) / n if n else 0.0
    soft_sem = 0.0
    if n > 1:
        mean = soft_acc
        var = sum((x - mean) ** 2 for x in soft_vals) / (n - 1)
        soft_sem = (var**0.5) / (n**0.5)
    by_task_exact: Dict[str, List[bool]] = defaultdict(list)
    by_task_soft: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        by_task_exact[r["task"]].append(bool(r.get("exact_ok") or r.get("ok")))
        by_task_soft[r["task"]].append(float(r.get("soft_accuracy", 0.0)))
    return {
        "mode": rows[0]["mode"] if rows else None,
        "n": n,
        "exact_accuracy": exact_acc,
        "soft_accuracy": soft_acc,
        "soft_sem": soft_sem,
        "accuracy": soft_acc,
        "per_task_exact": {t: sum(v) / len(v) for t, v in by_task_exact.items()},
        "per_task_soft": {t: sum(v) / len(v) for t, v in by_task_soft.items()},
        "per_task": {t: sum(v) / len(v) for t, v in by_task_soft.items()},
    }


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path("raw_data/onedarcraw/dataset"))
    ap.add_argument("--mode", default="block_primary", choices=list(MODES))
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--trials", type=str, default="", help="comma ids e.g. 0,1,2")
    ap.add_argument("--out", type=Path, default=Path("results/solver"))
    ap.add_argument(
        "--one",
        type=Path,
        default=None,
        help="Run a single JSON file (for parallel workers)",
    )
    args = ap.parse_args(argv)

    out_dir = args.out / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)

    run_meta = collect_run_meta(
        mode=args.mode,
        timeout=args.timeout,
        jobs=1,
        trials=args.trials or None,
        dataset=str(args.dataset),
        out=str(args.out),
        extra={"entry": "harness", "one": bool(args.one)},
    )
    # Campaign-level manifest: sequential harness owns it. Parallel --one
    # workers must not clobber a parent-written run_manifest.json.
    if args.one is None or not (out_dir / "run_manifest.json").exists():
        (out_dir / "run_manifest.json").write_text(json.dumps(run_meta, indent=2))

    if args.one is not None:
        path = args.one
        print(f"[1/1] {path}", flush=True)
        try:
            row = run_one(path, args.mode, args.timeout, out_dir, run_meta=run_meta)
        except Exception as e:
            soft_matrix = [0, 1, 0, 0]
            soft_acc = 0.0
            try:
                from solver.encoder import encode_instance
                from solver.paper_score import failure_matrix, soft_accuracy

                enc = encode_instance(path, out_dir / "_err_encode" / path.stem)
                soft_matrix = failure_matrix(enc.test_path)
                soft_acc = soft_accuracy(soft_matrix)
            except Exception:
                pass
            row = {
                "file": str(path),
                "task": path.parent.name,
                "mode": args.mode,
                "ok": False,
                "exact_ok": False,
                "soft_accuracy": soft_acc,
                "soft_matrix": soft_matrix,
                "level": "error",
                "confidence": "low",
                "verified_train": False,
                "elapsed": 0.0,
                "predicted": None,
                "gold": None,
                "error": str(e),
                "failure_reason": "popper_error",
                "failure_detail": {},
                "run_meta": slim_meta(run_meta),
            }
        (out_dir / f"{path.parent.name}_{path.stem}.json").write_text(
            json.dumps(row, indent=2)
        )
        print(json.dumps(row, indent=2), flush=True)
        return

    files = filter_files(discover(args.dataset), trials=args.trials, limit=args.limit)
    rows = []
    for i, f in enumerate(files):
        print(f"[{i+1}/{len(files)}] {f}")
        row = run_one(f, args.mode, args.timeout, out_dir, run_meta=run_meta)
        rows.append(row)
        (out_dir / f"{f.parent.name}_{f.stem}.json").write_text(
            json.dumps(row, indent=2)
        )

    summary = summarize(rows)
    summary["run_meta"] = mark_finished(run_meta)
    (out_dir / "run_manifest.json").write_text(
        json.dumps(summary["run_meta"], indent=2)
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
