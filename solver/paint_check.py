"""Partition train-paint checker for staged hybrid induction.

Gold lives in ``grids.json`` (train rows only). Not BK, not bias.
``True`` from a checker means *bad* paint (Popper ``paint_checker`` convention).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from solver.census import bulky_runs, unit_runs
from solver.decode import apply_hybrid_program
from solver.encoder import ExampleGrids

PathLike = Union[str, Path]
PaintMode = str  # "bulky" | "unit"


def _gold_cells(row: Sequence[int], *, bulky: bool) -> Set[int]:
    spans = bulky_runs(row) if bulky else unit_runs(row)
    cells: Set[int] = set()
    for s, e, _c in spans:
        cells.update(range(s, e + 1))
    return cells


def partition_rows_equal(
    painted: Sequence[int],
    gold: Sequence[int],
    mode: PaintMode,
) -> bool:
    """Compare one decoded row to gold on this head's partition (zeros included)."""
    if len(painted) != len(gold):
        return False
    match_cells = _gold_cells(gold, bulky=(mode == "bulky"))
    for i, (p, g) in enumerate(zip(painted, gold)):
        if i in match_cells:
            if int(p) != int(g):
                return False
        elif int(p) != 0:
            return False
    return True


def _load_hybrid_grids(grids_path: Path) -> tuple[
    List[ExampleGrids],
    Dict[int, Dict[int, Tuple[int, int]]],
    Dict[int, Dict[int, int]],
    bool,
    List[int],
]:
    meta = json.loads(grids_path.read_text())
    train = [
        ExampleGrids(
            int(e["id"]),
            list(e["input"]),
            list(e["output"]) if e.get("output") is not None else None,
        )
        for e in meta["train"]
    ]
    typed = bool(meta.get("typed_roles", True))
    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = {}
    for eid_s, bids in (meta.get("block_geometry") or {}).items():
        block_geometry[int(eid_s)] = {
            int(bid): (int(span[0]), int(span[1])) for bid, span in bids.items()
        }
    unit_geometry: Dict[int, Dict[int, int]] = {}
    for eid_s, pids in (meta.get("unit_geometry") or {}).items():
        unit_geometry[int(eid_s)] = {int(pid): int(start) for pid, start in pids.items()}
    offs = [int(x) for x in (meta.get("observed_offs") or [])]
    return train, block_geometry, unit_geometry, typed, offs


def partition_paint_ok(
    program: str,
    bk_path: PathLike,
    grids_path: PathLike,
    mode: PaintMode,
) -> bool:
    """True if this head's program paints its train partition exactly."""
    if mode not in ("bulky", "unit"):
        raise ValueError(f"mode must be bulky or unit, got {mode!r}")
    train, bgeo, ugeo, typed, offs = _load_hybrid_grids(Path(grids_path))
    if not train or any(eg.out is None for eg in train):
        return False
    block_prog = program if mode == "bulky" else ""
    unit_prog = program if mode == "unit" else ""
    try:
        preds = apply_hybrid_program(
            block_prog,
            unit_prog,
            bk_path,
            train,
            typed_roles=typed,
            block_geometry=bgeo,
            unit_geometry=ugeo,
            extra_offs=offs,
        )
    except Exception:
        return False
    for eg in train:
        assert eg.out is not None
        painted = preds.get(eg.ex_id, [])
        if not partition_rows_equal(painted, eg.out, mode):
            return False
    return True


def paint_is_bad_isolated(
    program: str,
    bk_path: PathLike,
    grids_path: PathLike,
    mode: PaintMode,
    *,
    join_s: float = 20.0,
) -> bool:
    """True if partition paint fails.

    Uses a fresh interpreter so this can run inside Popper's already-nested
    ``mp.Process`` (daemon children cannot spawn another ``mp.Process``).
    """
    import os
    import subprocess
    import sys
    import tempfile

    root = Path(__file__).resolve().parents[1]
    tmp = Path(tempfile.mkdtemp(prefix="paint_chk_"))
    prog_path = tmp / "prog.pl"
    prog_path.write_text(program if program.endswith("\n") else program + "\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "solver.paint_check",
                "--bk",
                str(bk_path),
                "--grids",
                str(grids_path),
                "--mode",
                mode,
                "--prog",
                str(prog_path),
            ],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=join_s,
        )
        return r.returncode != 0
    except Exception:
        return True
    finally:
        try:
            prog_path.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass


def _cli(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Partition paint check (exit 0 = ok)")
    p.add_argument("--bk", required=True)
    p.add_argument("--grids", required=True)
    p.add_argument("--mode", required=True, choices=("bulky", "unit"))
    p.add_argument("--prog", required=True)
    args = p.parse_args(argv)
    prog = Path(args.prog).read_text()
    ok = partition_paint_ok(prog, args.bk, args.grids, args.mode)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli())


def make_partition_paint_checker(
    bk_path: PathLike,
    grids_path: Optional[PathLike] = None,
    *,
    mode: PaintMode,
) -> Optional[Callable[[str], bool]]:
    """Build ``paint_checker(prog_str) -> bool`` (True = bad). None if no grids."""
    bk = Path(bk_path)
    grids = Path(grids_path) if grids_path is not None else bk.parent / "grids.json"
    if not grids.is_file():
        return None

    def _check(prog: str) -> bool:
        return paint_is_bad_isolated(prog, bk, grids, mode)

    return _check
