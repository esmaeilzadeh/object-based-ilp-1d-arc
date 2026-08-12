"""Train paint checker for staged induction (isolated from Popper's SWI session)."""

from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from solver.decode import apply_object_program
from solver.encoder import ExampleGrids
from solver.verify import grids_equal

PathLike = Union[str, Path]


def _load_train_from_grids(grids_path: Path) -> tuple[
    List[ExampleGrids],
    Dict[int, Dict[int, Tuple[int, int]]],
    bool,
]:
    meta = json.loads(grids_path.read_text())
    train = [
        ExampleGrids(int(e["id"]), list(e["input"]), list(e["output"]) if e.get("output") is not None else None)
        for e in meta["train"]
    ]
    typed = bool(meta.get("typed_roles", True))
    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = {}
    raw_geo = meta.get("block_geometry") or {}
    for eid_s, bids in raw_geo.items():
        block_geometry[int(eid_s)] = {
            int(bid): (int(span[0]), int(span[1])) for bid, span in bids.items()
        }
    return train, block_geometry, typed


def paint_ok_sync(
    program: str,
    bk_path: PathLike,
    grids_path: PathLike,
) -> bool:
    """Return True if program paints all train outputs exactly."""
    train, geo, typed = _load_train_from_grids(Path(grids_path))
    if not train or any(eg.out is None for eg in train):
        return False
    try:
        preds = apply_object_program(
            program,
            bk_path,
            train,
            typed_roles=typed,
            block_geometry=geo,
        )
    except Exception:
        return False
    for eg in train:
        assert eg.out is not None
        if not grids_equal(preds.get(eg.ex_id, []), eg.out):
            return False
    return True


def _paint_bad_worker(program: str, bk: str, grids: str, q: mp.Queue) -> None:
    try:
        q.put(not paint_ok_sync(program, bk, grids))
    except Exception:
        q.put(True)


def paint_is_bad_isolated(
    program: str,
    bk_path: PathLike,
    grids_path: PathLike,
    *,
    join_s: float = 60.0,
) -> bool:
    """True if paint fails. Runs in a child process to avoid SWI/janus clashes."""
    q: mp.Queue = mp.Queue()
    proc = mp.Process(
        target=_paint_bad_worker,
        args=(program, str(bk_path), str(grids_path), q),
    )
    proc.start()
    proc.join(join_s)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join(2)
        return True
    try:
        if not q.empty():
            return bool(q.get_nowait())
    except Exception:
        pass
    return True


def make_paint_checker(
    bk_path: PathLike,
    grids_path: Optional[PathLike] = None,
) -> Optional[Callable[[str], bool]]:
    """Build ``paint_checker(prog_str) -> bool`` (True = bad). None if no grids."""
    bk = Path(bk_path)
    grids = Path(grids_path) if grids_path is not None else bk.parent / "grids.json"
    if not grids.is_file():
        return None

    def _check(prog: str) -> bool:
        return paint_is_bad_isolated(prog, bk, grids)

    return _check
