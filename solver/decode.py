"""Decode object-head programs (out_block) into pixel grids."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from solver.encoder import (
    ExampleGrids,
    _bid,
    _col,
    _sz,
    _uid,
    block_geometry_for_row,
)

PathLike = Union[str, Path]


def _strip_program(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def _collect_out_blocks(
    ex_id: int,
    width: int,
    bids: Sequence[int],
    geometry: Dict[int, Tuple[int, int]],
    *,
    typed_roles: bool = False,
    min_len: int = 1,
    extra_offs: Sequence[int] = (),
) -> List[Tuple[int, int, int]]:
    """Enumerate grounded ``out_block(Ex, Bid, Off, Len, Color)``.

    Returns ``(paint_start, Len, Color)`` with ``paint_start = start(Bid)+Off``.
    """
    from janus_swi import query_once

    t = typed_roles
    offs = set(range(0, width + 1))
    offs.update(int(x) for x in extra_offs)
    blocks: List[Tuple[int, int, int]] = []
    for bid in bids:
        if bid not in geometry:
            continue
        start, _end = geometry[bid]
        for off in sorted(offs):
            for L in range(max(min_len, 1), width + 1):
                paint = start + off
                if L < min_len or paint < 0 or paint + L > width:
                    continue
                for c in range(1, 10):
                    atom = (
                        f"out_block({ex_id},{_bid(bid, t)},"
                        f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)})"
                    )
                    try:
                        res = query_once(atom)
                    except Exception:
                        continue
                    if res.get("truth"):
                        blocks.append((paint, L, c))
    return blocks


def apply_object_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = False,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
) -> Dict[int, List[int]]:
    """Paint pixels from ``out_block(Ex, Bid, Off, Len, Color)``.

    Overlap, OOB, or ambiguous color raises ValueError (verify treats as fail).
    """
    from janus_swi import consult, query_once

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_object_prog.pl"
    # Dynamic so later Popper tester retractall(out_block(...)) can clean up.
    tmp.write_text(":- dynamic out_block/5.\n" + prog)

    consult(str(bk_path))
    consult(str(tmp))

    geo = block_geometry
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            if eg.out is not None:
                w = len(eg.out)
            else:
                w = len(eg.inp)
            eg_geo = (
                geo[eg.ex_id]
                if geo is not None and eg.ex_id in geo
                else block_geometry_for_row(eg.inp)
            )
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect_out_blocks(
                eg.ex_id, w, list(eg_geo.keys()), eg_geo, typed_roles=typed_roles
            ):
                if L <= 0 or s < 0 or s + L > w:
                    raise ValueError(
                        f"out_block({eg.ex_id},paint→{s},{L},{c}) out of bounds width={w}"
                    )
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(
                            f"ambiguous/overlap at {eg.ex_id}:{p} "
                            f"{occupied[p]} vs {c}"
                        )
                    occupied[p] = c
                    row[p] = c
            out[eg.ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out_block(_,_,_,_,_))")
        except Exception:
            pass
        try:
            query_once("abolish(out_block/5)")
        except Exception:
            pass


def _collect_out_pixels(
    ex_id: int,
    width: int,
    pids: Sequence[int],
    unit_starts: Dict[int, int],
    *,
    typed_roles: bool = False,
    extra_offs: Sequence[int] = (),
) -> List[Tuple[int, int]]:
    """Returns ``(paint_pos, Color)`` for grounded ``out_pixel/4``."""
    from janus_swi import query_once

    t = typed_roles
    offs = set(range(-width, width + 1))
    offs.update(int(x) for x in extra_offs)
    paints: List[Tuple[int, int]] = []
    for pid in pids:
        if pid not in unit_starts:
            continue
        start = unit_starts[pid]
        for off in sorted(offs):
            paint = start + off
            if paint < 0 or paint >= width:
                continue
            for c in range(1, 10):
                atom = (
                    f"out_pixel({ex_id},{_uid(pid, t)},{_sz(off, t)},{_col(c, t)})"
                )
                try:
                    res = query_once(atom)
                except Exception:
                    continue
                if res.get("truth"):
                    paints.append((paint, c))
    return paints


def apply_hybrid_program(
    block_program: str,
    unit_program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = True,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
    unit_geometry: Optional[Dict[int, Dict[int, int]]] = None,
    extra_offs: Sequence[int] = (),
) -> Dict[int, List[int]]:
    """Paint bulky spans then units. Overlap raises ValueError."""
    from janus_swi import consult, query_once

    tmp = Path(bk_path).parent / "_apply_hybrid_prog.pl"
    tmp.write_text(
        ":- dynamic out_block/5.\n:- dynamic out_pixel/4.\n"
        + _strip_program(block_program)
        + "\n"
        + _strip_program(unit_program)
        + "\n"
    )
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            w = len(eg.out) if eg.out is not None else len(eg.inp)
            bgeo = (
                block_geometry[eg.ex_id]
                if block_geometry is not None and eg.ex_id in block_geometry
                else {}
            )
            ugeo = (
                unit_geometry[eg.ex_id]
                if unit_geometry is not None and eg.ex_id in unit_geometry
                else {}
            )
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect_out_blocks(
                eg.ex_id,
                w,
                list(bgeo.keys()),
                bgeo,
                typed_roles=typed_roles,
                min_len=2,
                extra_offs=extra_offs,
            ):
                if L < 2 or s < 0 or s + L > w:
                    raise ValueError(
                        f"out_block({eg.ex_id},paint→{s},{L},{c}) invalid width={w}"
                    )
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(
                            f"ambiguous/overlap at {eg.ex_id}:{p} "
                            f"{occupied[p]} vs {c}"
                        )
                    occupied[p] = c
                    row[p] = c
            for p, c in _collect_out_pixels(
                eg.ex_id,
                w,
                list(ugeo.keys()),
                ugeo,
                typed_roles=typed_roles,
                extra_offs=extra_offs,
            ):
                if p in occupied:
                    raise ValueError(
                        f"unit/block overlap at {eg.ex_id}:{p} "
                        f"{occupied[p]} vs {c}"
                    )
                occupied[p] = c
                row[p] = c
            out[eg.ex_id] = row
        return out
    finally:
        for atom in (
            "retractall(out_block(_,_,_,_,_))",
            "retractall(out_pixel(_,_,_,_))",
            "abolish(out_block/5)",
            "abolish(out_pixel/4)",
        ):
            try:
                query_once(atom)
            except Exception:
                pass


def apply_pixel_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
) -> Dict[int, List[int]]:
    """Paint ``out(Ex, Pos, Color)``; overlap / two colours raise."""
    from janus_swi import consult, query_once

    tmp = Path(bk_path).parent / "_apply_pixel_prog.pl"
    tmp.write_text(":- dynamic out/3.\n" + _strip_program(program))
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            w = len(eg.out) if eg.out is not None else len(eg.inp)
            row = [0] * w
            occupied: Dict[int, int] = {}
            for i in range(w):
                for c in range(1, 10):
                    atom = f"out({eg.ex_id},{i},{c})"
                    try:
                        res = query_once(atom)
                    except Exception:
                        continue
                    if res.get("truth"):
                        if i in occupied and occupied[i] != c:
                            raise ValueError(
                                f"ambiguous out/3 at {eg.ex_id}:{i}"
                            )
                        occupied[i] = c
                        row[i] = c
            out[eg.ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out(_,_,_))")
        except Exception:
            pass
        try:
            query_once("abolish(out/3)")
        except Exception:
            pass

