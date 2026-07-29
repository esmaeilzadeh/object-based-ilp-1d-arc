"""Cheap-first ladder orchestration for one 1D-ARC instance."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from solver.bias_gen import write_bias_files
from solver.decode import apply_object_program
from solver.encoder import encode_instance
from solver.induce import induce
from solver.paper_score import grid_to_out_program, score_program_soft
from solver.trivial import try_trivial
from solver.verify import apply_program, verify_object_on_train, verify_on_train

PathLike = Union[str, Path]
_BIAS = Path(__file__).resolve().parent / "bias"


@dataclass
class SolveResult:
    predicted_grid: List[int]
    program: str
    level: str
    verified_train: bool
    confidence: str  # high | low
    soft_matrix: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    soft_accuracy: float = 0.0

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
    """Solve one ARC JSON instance. Returns prediction for the first test input.

    Acceptance matches the paper repo: an induced Popper program is scored even
    if it fails exact train verification. Soft accuracy uses ``test.pl``.
    """
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

    def _remap(grid: List[int]) -> List[int]:
        if canonicalize_colors and test0.ex_id in encoded.inv_color_maps:
            inv = encoded.inv_color_maps[test0.ex_id]
            return [0 if c == 0 else inv.get(c, c) for c in grid]
        return grid

    def _soft_for(prog: str, pred: List[int], *, object_head: bool) -> Tuple[List[int], float]:
        if not encoded.test_path.exists() or test0.out is None:
            return [0, 0, 0, 0], 0.0
        # Always score materialized out/3 from the predicted grid so soft
        # matches closed-world decode and avoids dirty Janus program state.
        del prog, object_head
        score_prog = grid_to_out_program(test0.ex_id, pred)
        return score_program_soft(
            score_prog,
            encoded.test_path,
            work_dir=work_dir / "soft_score",
        )

    def _finish(
        prog: str,
        level: str,
        *,
        object_head: bool,
        verified: bool,
    ) -> SolveResult:
        try:
            if object_head:
                preds = apply_object_program(
                    prog,
                    encoded.test_bk_path,
                    encoded.test,
                    typed_roles=encoded.typed_roles,
                    block_geometry=encoded.block_geometry,
                )
            else:
                preds = apply_program(prog, encoded.test_bk_path, encoded.test)
            pred = _remap(preds[test0.ex_id])
        except Exception:
            pred = _remap(list(test0.inp))
        matrix, soft = _soft_for(prog, pred, object_head=object_head)
        return SolveResult(
            pred,
            prog,
            level,
            verified,
            "high" if verified else "low",
            matrix,
            soft,
        )

    # Last induced program (paper acceptance): keep even if train-verify fails.
    candidate: Optional[Tuple[str, str, bool]] = None  # prog, level, object_head

    def _consider_pixel(prog: str, level: str) -> Optional[SolveResult]:
        nonlocal candidate
        candidate = (prog, level, False)
        if verify_on_train(prog, encoded):
            return _finish(prog, level, object_head=False, verified=True)
        return None

    def _consider_object(prog: str, level: str) -> Optional[SolveResult]:
        # Block-level path: only accept paint-verified out_block programs (no
        # unverified timeout artifacts counted as object_ilp solutions).
        if verify_object_on_train(prog, encoded):
            nonlocal candidate
            candidate = (prog, level, True)
            return _finish(prog, level, object_head=True, verified=True)
        return None

    if force_bias == "pixel":
        rem = _remaining()
        if rem > 0:
            prog = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                rem,
                work_dir / "popper",
            )
            if prog:
                r = _consider_pixel(prog, "pixel_ilp")
                if r:
                    return r
    elif force_bias == "object" or (include_blocks and not include_pixels):
        # Pure block-level: object ILP only (no pixel / trivial).
        # Denoise vocab first (fails fast when inapplicable, <1s when applicable),
        # then fill/merge vocab with the remaining budget (needs ~120s+).
        if include_blocks:
            # (bias_file, work_dir_name, max_seconds_cap_or_None)
            stages = (
                ("object_denoise.pl", "popper_object_denoise", 30),
                ("object_recolor.pl", "popper_object_recolor", 15),
                ("object_recolor_cnt.pl", "popper_object_recolor_cnt", 30),
                ("object_recolor_sz.pl", "popper_object_recolor_sz", 30),
                ("object_padded.pl", "popper_object_padded", 90),
                ("object.pl", "popper_object", None),
            )
            for bias_name, work_name, cap in stages:
                rem = _remaining()
                if rem <= 0:
                    break
                budget = min(rem, cap) if cap else rem
                prog = induce(
                    encoded.exs_object_path,
                    encoded.bk_path,
                    _BIAS / bias_name,
                    budget,
                    work_dir / work_name,
                )
                if prog:
                    r = _consider_object(prog, "object_ilp")
                    if r:
                        return r
    elif not ladder:
        rem = _remaining()
        if rem > 0:
            prog = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                rem,
                work_dir / "popper",
            )
            if prog:
                r = _consider_pixel(prog, "dual_no_ladder")
                if r:
                    return r
    else:
        # Legacy dual ladder (pixel+block) for ablation modes only.
        triv = try_trivial(encoded)
        if triv:
            prog, name = triv
            r = _consider_pixel(prog, name)
            if r:
                return r

        if include_blocks and _remaining() > 0:
            early_cap = (
                min(30, max(int(0.15 * timeout), 1))
                if timeout >= 120
                else min(70, max(int(0.35 * timeout), 1))
            )
            budget = min(early_cap, _remaining())
            budget = min(budget, max(_remaining() - max(timeout // 2, 1), 1))
            prog = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "block.pl",
                budget,
                work_dir / "popper_block",
            )
            if prog:
                r = _consider_pixel(prog, "block_ilp")
                if r:
                    return r

        if include_blocks and _remaining() > 0:
            early_cap = (
                min(30, max(int(0.15 * timeout), 1))
                if timeout >= 120
                else min(55, max(int(0.35 * timeout), 1))
            )
            budget = min(early_cap, _remaining())
            budget = min(budget, max(_remaining() - max(timeout // 2, 1), 1))
            prog = induce(
                encoded.exs_object_path,
                encoded.bk_path,
                _BIAS / "object.pl",
                budget,
                work_dir / "popper_object",
            )
            if prog:
                r = _consider_object(prog, "object_ilp")
                if r:
                    return r

        if include_pixels and _remaining() > 0:
            prog = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                _remaining(),
                work_dir / "popper_pixel",
            )
            if prog:
                r = _consider_pixel(prog, "pixel_ilp")
                if r:
                    return r

        if include_pixels and include_blocks and _remaining() > 0:
            prog = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                _remaining(),
                work_dir / "popper_dual",
            )
            if prog:
                r = _consider_pixel(prog, "dual_ilp")
                if r:
                    return r

    if candidate is not None:
        prog, level, object_head = candidate
        return _finish(prog, level, object_head=object_head, verified=False)

    # No induced program — identity fallback (same spirit as empty program.pl).
    prog = "out(E,P,C) :- in(E,P,C).\n"
    pred = _remap(list(test0.inp))
    matrix, soft = _soft_for(prog, pred, object_head=False)
    return SolveResult(
        pred,
        prog,
        "fallback_identity",
        False,
        "low",
        matrix,
        soft,
    )
