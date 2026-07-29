"""Decode object-head programs (out_block) into pixel grids."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from solver.encoder import (
    ExampleGrids,
    _bid,
    _col,
    _sz,
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
) -> List[Tuple[int, int, int]]:
    """Enumerate grounded ``out_block(Ex, Bid, Off, Len, Color)``.

    Returns ``(paint_start, Len, Color)`` with ``paint_start = start(Bid)+Off``.
    """
    from janus_swi import query_once

    t = typed_roles
    blocks: List[Tuple[int, int, int]] = []
    for bid in bids:
        if bid not in geometry:
            continue
        start, _end = geometry[bid]
        for off in range(0, width + 1):
            for L in range(1, width + 1):
                if start + off + L > width + 1:
                    break
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
                        blocks.append((start + off, L, c))
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
    from janus_swi import consult

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_object_prog.pl"
    tmp.write_text(prog)

    consult(str(bk_path))
    consult(str(tmp))

    geo = block_geometry
    out: Dict[int, List[int]] = {}
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
