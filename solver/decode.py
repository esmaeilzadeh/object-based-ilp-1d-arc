"""Decode object-head programs (out_block) into pixel grids."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Union

from solver.encoder import ExampleGrids

PathLike = Union[str, Path]


def _strip_program(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def _collect_out_blocks(ex_id: int, width: int) -> List[Tuple[int, int, int]]:
    """Enumerate grounded ``out_block`` atoms for one example (janus-safe)."""
    from janus_swi import query_once

    blocks: List[Tuple[int, int, int]] = []
    for s in range(width):
        for L in range(1, width - s + 1):
            for c in range(1, 10):
                try:
                    res = query_once(f"out_block({ex_id},{s},{L},{c})")
                except Exception:
                    continue
                if res.get("truth"):
                    blocks.append((s, L, c))
    return blocks


def apply_object_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
) -> Dict[int, List[int]]:
    """Paint pixels from derived ``out_block(Ex, Start, Len, Color)`` atoms.

    Overlap, OOB, or ambiguous color raises ValueError (verify treats as fail).
    """
    from janus_swi import consult

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_object_prog.pl"
    tmp.write_text(prog)

    consult(str(bk_path))
    consult(str(tmp))

    out: Dict[int, List[int]] = {}
    for eg in examples:
        if eg.out is not None:
            w = len(eg.out)
        else:
            w = len(eg.inp)
        row = [0] * w
        occupied: Dict[int, int] = {}
        for s, L, c in _collect_out_blocks(eg.ex_id, w):
            if L <= 0 or s < 0 or s + L > w:
                raise ValueError(
                    f"out_block({eg.ex_id},{s},{L},{c}) out of bounds width={w}"
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
