"""Closed-world decoder and exact train verifier."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from solver.encoder import EncodeResult, ExampleGrids

PathLike = Union[str, Path]


def _strip_program(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def apply_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
) -> Dict[int, List[int]]:
    """Derive output grids via SWI-Prolog (janus). Background cells default to 0."""
    from janus_swi import consult, query_once

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_prog.pl"
    tmp.write_text(prog)

    consult(str(bk_path))
    consult(str(tmp))

    out: Dict[int, List[int]] = {}
    for eg in examples:
        w = len(eg.inp) if eg.out is None else max(len(eg.inp), len(eg.out or []))
        if eg.out is not None:
            w = len(eg.out)
        else:
            w = len(eg.inp)
        row = [0] * w
        for pos in range(w):
            colors = []
            # query all possible colors 0..9
            for c in range(10):
                try:
                    res = query_once(f"out({eg.ex_id},{pos},{c})")
                    if res.get("truth"):
                        colors.append(c)
                except Exception:
                    pass
            if len(colors) > 1:
                raise ValueError(
                    f"ambiguous out({eg.ex_id},{pos},_) -> {colors}"
                )
            if len(colors) == 1:
                row[pos] = colors[0]
        out[eg.ex_id] = row
    return out


def grids_equal(pred: Sequence[int], gold: Sequence[int]) -> bool:
    return list(pred) == list(gold)


def verify_on_train(program: str, encoded: EncodeResult) -> bool:
    try:
        preds = apply_program(program, encoded.bk_path, encoded.train)
    except Exception:
        return False
    for eg in encoded.train:
        assert eg.out is not None
        if not grids_equal(preds[eg.ex_id], eg.out):
            return False
    return True
