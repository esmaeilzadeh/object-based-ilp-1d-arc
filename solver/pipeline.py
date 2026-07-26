"""Cheap-first ladder orchestration for one 1D-ARC instance."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from solver.bias_gen import write_bias_files
from solver.encoder import encode_instance
from solver.induce import induce
from solver.trivial import try_trivial
from solver.verify import apply_program, verify_on_train

PathLike = Union[str, Path]
_BIAS = Path(__file__).resolve().parent / "bias"


@dataclass
class SolveResult:
    predicted_grid: List[int]
    program: str
    level: str
    verified_train: bool
    confidence: str  # high | low

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def solve(
    instance: Union[PathLike, dict],
    *,
    timeout: int = 600,
    canonicalize_colors: bool = False,
    ladder: bool = True,
    work_dir: Optional[PathLike] = None,
    include_aggregations: bool = True,
    include_blocks: bool = True,
    include_pixels: bool = True,
    force_bias: Optional[str] = None,
) -> SolveResult:
    """Solve one ARC JSON instance. Returns prediction for the first test input."""
    write_bias_files()
    work_dir = Path(work_dir or Path("work") / "solve")
    work_dir.mkdir(parents=True, exist_ok=True)

    encoded = encode_instance(
        instance,
        work_dir / "encode",
        canonicalize_colors=canonicalize_colors,
        include_aggregations=include_aggregations,
        include_blocks=include_blocks,
        include_pixels=include_pixels,
    )
    test0 = encoded.test[0]
    deadline = time.time() + float(timeout)

    def _remaining() -> int:
        return max(int(deadline - time.time()), 0)

    def _ok(prog: str, level: str) -> Optional[SolveResult]:
        if not verify_on_train(prog, encoded):
            return None
        preds = apply_program(prog, encoded.bk_path, encoded.test)
        grid = preds[test0.ex_id]
        if canonicalize_colors and test0.ex_id in encoded.inv_color_maps:
            inv = encoded.inv_color_maps[test0.ex_id]
            grid = [0 if c == 0 else inv.get(c, c) for c in grid]
        return SolveResult(grid, prog, level, True, "high")

    if force_bias == "pixel":
        rem = _remaining()
        if rem > 0:
            prog = induce(
                encoded.exs_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                rem,
                work_dir / "popper",
            )
            if prog:
                r = _ok(prog, "pixel_ilp")
                if r:
                    return r
    elif not ladder:
        rem = _remaining()
        if rem > 0:
            prog = induce(
                encoded.exs_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                rem,
                work_dir / "popper",
            )
            if prog:
                r = _ok(prog, "dual_no_ladder")
                if r:
                    return r
    else:
        # Level 1 — trivial (constant time)
        triv = try_trivial(encoded)
        if triv:
            prog, name = triv
            r = _ok(prog, name)
            if r:
                return r

        # Level 2 — block-only ILP (cap ~40% of budget; relational prior pays here)
        if include_blocks and _remaining() > 0:
            budget = min(max(int(0.40 * timeout), 1), _remaining())
            prog = induce(
                encoded.exs_path,
                encoded.bk_path,
                _BIAS / "block.pl",
                budget,
                work_dir / "popper_block",
            )
            if prog:
                r = _ok(prog, "block_ilp")
                if r:
                    return r

        # Level 3 — pixel ILP (paper-comparable; remaining wall-clock)
        if include_pixels and _remaining() > 0:
            prog = induce(
                encoded.exs_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                _remaining(),
                work_dir / "popper_pixel",
            )
            if prog:
                r = _ok(prog, "pixel_ilp")
                if r:
                    return r

        # Level 4 — dual ILP (if any time left)
        if include_pixels and include_blocks and _remaining() > 0:
            prog = induce(
                encoded.exs_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                _remaining(),
                work_dir / "popper_dual",
            )
            if prog:
                r = _ok(prog, "dual_ilp")
                if r:
                    return r

    return SolveResult(
        list(test0.inp),
        "out(E,P,C) :- in(E,P,C).\n",
        "fallback_identity",
        False,
        "low",
    )
