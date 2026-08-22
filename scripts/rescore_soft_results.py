#!/usr/bin/env python3
"""Offline-rescore soft_matrix / soft_accuracy under per-label out soft (v1).

Walks results/*/hybrid_census and results/*/block_primary task JSONs, recomputes
soft via score_program_soft (same helper as the live pipeline), rebuilds
summary.json. Exact fields are left unchanged.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solver.encoder import encode_instance
from solver.harness import summarize
from solver.paper_score import grid_to_out_program, score_program_soft

SOFT_DEFINITION = "per_label_out_v1"
SKIP_NAMES = {"summary.json", "run_manifest.json"}
MODES = ("hybrid_census", "block_primary")


def _work_stem(row: dict) -> Optional[str]:
    f = row.get("file") or ""
    if f:
        return Path(f).stem
    # result file: 1d_flip_1d_flip_0.json → work dir 1d_flip_0
    task = row.get("task") or ""
    return None


def _resolve_test_pl(mode_dir: Path, row: dict, cache_dir: Path) -> Tuple[Path, int]:
    """Return (test.pl path, test ex_id)."""
    stem = Path(row["file"]).stem if row.get("file") else None
    if stem:
        candidate = mode_dir / stem / "encode" / "test.pl"
        if candidate.exists():
            return candidate, _ex_id_from_test(candidate)

    src = Path(row["file"]) if row.get("file") else None
    if src is None or not src.exists():
        # try dataset-relative from repo root
        if row.get("file"):
            alt = ROOT / row["file"]
            if alt.exists():
                src = alt
    if src is None or not src.exists():
        raise FileNotFoundError(f"cannot resolve instance for {row.get('file')}")

    enc_dir = cache_dir / mode_dir.name / src.parent.name / src.stem
    enc = encode_instance(src, enc_dir)
    return enc.test_path, enc.test[0].ex_id


def _ex_id_from_test(test_path: Path) -> int:
    text = test_path.read_text()
    m = re.search(r"pos\(out\((\d+),", text)
    if m:
        return int(m.group(1))
    m = re.search(r"neg\(out\((\d+),", text)
    if m:
        return int(m.group(1))
    return 3


def _score_payload(row: dict, test_path: Path, ex_id: int, work: Path) -> Tuple[List[int], float]:
    detail = row.get("failure_detail") or {}
    road = detail.get("road")
    prog = (row.get("program") or "").strip()
    use_program = road == "pixel" and prog.startswith("out(")
    if use_program:
        return score_program_soft(prog, test_path, work_dir=work)
    pred = row.get("predicted")
    if pred is None:
        raise ValueError("no predicted grid to score")
    facts = grid_to_out_program(ex_id, pred)
    return score_program_soft(facts, test_path, work_dir=work)


def _iter_task_jsons(results_root: Path) -> List[Path]:
    out: List[Path] = []
    for mode in MODES:
        for mode_dir in results_root.glob(f"*/{mode}"):
            if not mode_dir.is_dir():
                continue
            for p in sorted(mode_dir.glob("*.json")):
                if p.name in SKIP_NAMES:
                    continue
                out.append(p)
    return out


def rescore_one(
    path: Path,
    cache_dir: Path,
    *,
    dry_run: bool = False,
) -> Optional[dict]:
    row = json.loads(path.read_text())
    if "exact_ok" not in row and "ok" not in row:
        return None
    if row.get("predicted") is None and not (row.get("program") or "").strip():
        return None

    mode_dir = path.parent
    test_path, ex_id = _resolve_test_pl(mode_dir, row, cache_dir)
    work = cache_dir / "soft_score" / mode_dir.parent.name / mode_dir.name / path.stem
    matrix, acc = _score_payload(row, test_path, ex_id, work)

    old_m = row.get("soft_matrix")
    old_a = row.get("soft_accuracy")
    row["soft_matrix"] = matrix
    row["soft_accuracy"] = acc
    row["soft_definition"] = SOFT_DEFINITION
    detail = dict(row.get("failure_detail") or {})
    if "decom_solved" in detail or detail.get("road") == "pixel":
        detail["decom_solved"] = int(matrix[1]) == 0 and int(matrix[3]) == 0
        row["failure_detail"] = detail

    if not dry_run:
        path.write_text(json.dumps(row, indent=2) + "\n")
    return {
        "path": str(path),
        "old_matrix": old_m,
        "old_acc": old_a,
        "soft_matrix": matrix,
        "soft_accuracy": acc,
    }


def rebuild_summary(mode_dir: Path) -> None:
    rows: List[dict] = []
    for p in sorted(mode_dir.glob("*.json")):
        if p.name in SKIP_NAMES:
            continue
        row = json.loads(p.read_text())
        if "exact_ok" in row or "ok" in row:
            rows.append(row)
    if not rows:
        return
    summary_path = mode_dir / "summary.json"
    prev: Dict[str, Any] = {}
    if summary_path.exists():
        prev = json.loads(summary_path.read_text())
    summary = summarize(rows)
    for key in ("timeout", "jobs", "run_meta"):
        if key in prev:
            summary[key] = prev[key]
    summary["soft_definition"] = SOFT_DEFINITION
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--results",
        type=Path,
        default=ROOT / "results",
        help="results root (default: repo results/)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args(argv)

    paths = _iter_task_jsons(args.results)
    if args.limit:
        paths = paths[: args.limit]

    changed = 0
    errors = 0
    with tempfile.TemporaryDirectory(prefix="rescore_soft_") as tmp:
        cache = Path(tmp)
        for i, path in enumerate(paths, 1):
            try:
                info = rescore_one(path, cache, dry_run=args.dry_run)
                if info is None:
                    continue
                changed += 1
                if i % 50 == 0 or i == len(paths):
                    print(f"[{i}/{len(paths)}] rescored={changed} errors={errors}", flush=True)
            except Exception as e:
                errors += 1
                print(f"ERROR {path}: {e}", flush=True)

        if not args.dry_run:
            mode_dirs = {
                p.parent for p in paths if p.parent.name in MODES
            }
            for mode_dir in sorted(mode_dirs):
                rebuild_summary(mode_dir)
                print(f"summary rebuilt: {mode_dir / 'summary.json'}", flush=True)

    print(f"done. rescored={changed} errors={errors} dry_run={args.dry_run}", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
