"""Decode object-head programs (out_block) into pixel grids."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from solver.encoder import ExampleGrids, _col, _rank, _sz

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
    *,
    typed_roles: bool = False,
    max_rank: int = 16,
) -> List[Tuple[int, int, int]]:
    """Enumerate grounded ``out_block(Ex, Rank, Start, Len, Color)``.

    Returns ``(paint_start, Len, Color)`` with absolute ``paint_start = Start``.
    """
    from janus_swi import query_once

    t = typed_roles
    blocks: List[Tuple[int, int, int]] = []
    for rank in range(0, max_rank):
        for start in range(0, width + 1):
            for L in range(1, width + 1):
                if start + L > width:
                    break
                for c in range(0, 10):
                    atom = (
                        f"out_block({ex_id},{_rank(rank, t)},"
                        f"{_sz(start, t)},{_sz(L, t)},{_col(c, t)})"
                    )
                    try:
                        res = query_once(atom)
                    except Exception:
                        continue
                    if res.get("truth"):
                        blocks.append((start, L, c))
    return blocks


def apply_object_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = False,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
) -> Dict[int, List[int]]:
    """Paint pixels from ``out_block(Ex, Rank, Start, Len, Color)``.

    ``block_geometry`` is ignored (kept for call-site compatibility).
    Overlap, OOB, or ambiguous color raises ValueError (verify treats as fail).
    """
    del block_geometry  # independent-out decode uses absolute Start only
    from janus_swi import consult, query_once

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_object_prog.pl"
    # Dynamic so later Popper tester retractall(out_block(...)) can clean up.
    tmp.write_text(":- dynamic out_block/5.\n" + prog)

    consult(str(bk_path))
    consult(str(tmp))

    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            if eg.out is not None:
                w = len(eg.out)
            else:
                w = len(eg.inp)
            row = [0] * w
            occupied: Dict[int, int] = {}
            max_rank = max(w, 8)
            for s, L, c in _collect_out_blocks(
                eg.ex_id, w, typed_roles=typed_roles, max_rank=max_rank
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
