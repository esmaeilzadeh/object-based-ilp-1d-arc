"""Cheap-first ladder orchestration for one 1D-ARC instance."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from solver.bias_gen import (
    OBJECT_MAX_BODY,
    OBJECT_MAX_CLAUSES,
    OBJECT_MAX_LITERALS,
    OBJECT_MAX_VARS,
    write_bias_files,
)
from solver.decode import apply_object_program
from solver.encoder import encode_instance
from solver.induce import InduceResult, induce
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
    failure_reason: Optional[str] = None
    failure_detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _bias_detail(ir: InduceResult, timeout_s: int) -> Dict[str, Any]:
    return {
        "popper_status": ir.status,
        "had_program": bool(ir.program),
        "program_chars": len(ir.program) if ir.program else 0,
        "max_vars": OBJECT_MAX_VARS,
        "max_body": OBJECT_MAX_BODY,
        "max_clauses": OBJECT_MAX_CLAUSES,
        "max_literals": ir.max_literals or OBJECT_MAX_LITERALS,
        "timeout_s": timeout_s,
        "induce_elapsed_s": round(ir.elapsed_s, 3),
        "error": ir.error,
    }


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
        failure_reason: Optional[str] = None,
        failure_detail: Optional[Dict[str, Any]] = None,
    ) -> SolveResult:
        detail = dict(failure_detail or {})
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
        except Exception as e:
            pred = _remap(list(test0.inp))
            if failure_reason is None and not verified:
                failure_reason = "decode_error"
                detail["decode_error"] = str(e)
        matrix, soft = _soft_for(prog, pred, object_head=object_head)
        return SolveResult(
            pred,
            prog,
            level,
            verified,
            "high" if verified else "low",
            matrix,
            soft,
            failure_reason,
            detail,
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
        if verify_object_on_train(prog, encoded):
            nonlocal candidate
            candidate = (prog, level, True)
            return _finish(prog, level, object_head=True, verified=True)
        return None

    def _object_fail(
        ir: InduceResult,
        rem: int,
        *,
        reason: str,
        prog: str = "",
    ) -> SolveResult:
        detail = _bias_detail(ir, rem)
        pred_prog = prog or "out(E,P,C) :- in(E,P,C).\n"
        pred = _remap(list(test0.inp))
        matrix, soft = _soft_for(pred_prog, pred, object_head=False)
        return SolveResult(
            pred,
            prog,
            "fallback_identity",
            False,
            "low",
            matrix,
            soft,
            reason,
            detail,
        )

    if force_bias == "pixel":
        rem = _remaining()
        if rem > 0:
            ir = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                rem,
                work_dir / "popper",
            )
            if ir.program:
                r = _consider_pixel(ir.program, "pixel_ilp")
                if r:
                    return r
    elif force_bias == "object" or (include_blocks and not include_pixels):
        # Pure block-level: one mechanical object bias from this instance's BK/exs.
        if include_blocks:
            bias_path = encoded.bias_object_path
            if bias_path is None or not bias_path.exists():
                from solver.bias_gen import render_object_bias_from_bk

                bias_path = work_dir / "bias_object.pl"
                bias_path.write_text(
                    render_object_bias_from_bk(
                        encoded.bk_path.read_text(),
                        exs_text=encoded.exs_object_path.read_text(),
                    )
                )
            rem = _remaining()
            if rem > 0:
                ir = induce(
                    encoded.exs_object_path,
                    encoded.bk_path,
                    bias_path,
                    rem,
                    work_dir / "popper_object",
                    max_literals=OBJECT_MAX_LITERALS,
                )
                if ir.program:
                    if verify_object_on_train(ir.program, encoded):
                        return _finish(
                            ir.program,
                            "object_ilp",
                            object_head=True,
                            verified=True,
                            failure_reason=None,
                            failure_detail=_bias_detail(ir, rem),
                        )
                    return _object_fail(
                        ir, rem, reason="paint_verify_failed", prog=ir.program
                    )
                if ir.status == "timeout":
                    return _object_fail(ir, rem, reason="popper_timeout")
                if ir.status == "error":
                    return _object_fail(ir, rem, reason="popper_error")
                return _object_fail(ir, rem, reason="popper_exhausted")
            return _object_fail(
                InduceResult(None, "timeout", 0.0, max_literals=OBJECT_MAX_LITERALS),
                rem,
                reason="popper_timeout",
            )
    elif not ladder:
        rem = _remaining()
        if rem > 0:
            ir = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                rem,
                work_dir / "popper",
            )
            if ir.program:
                r = _consider_pixel(ir.program, "dual_no_ladder")
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
            ir = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "block.pl",
                budget,
                work_dir / "popper_block",
            )
            if ir.program:
                r = _consider_pixel(ir.program, "block_ilp")
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
            bias_path = encoded.bias_object_path
            if bias_path is None or not Path(bias_path).exists():
                from solver.bias_gen import render_object_bias_from_bk

                bias_path = work_dir / "bias_object.pl"
                bias_path.write_text(
                    render_object_bias_from_bk(
                        encoded.bk_path.read_text(),
                        exs_text=encoded.exs_object_path.read_text(),
                    )
                )
            ir = induce(
                encoded.exs_object_path,
                encoded.bk_path,
                bias_path,
                budget,
                work_dir / "popper_object",
                max_literals=OBJECT_MAX_LITERALS,
            )
            if ir.program:
                r = _consider_object(ir.program, "object_ilp")
                if r:
                    return r

        if include_pixels and _remaining() > 0:
            ir = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "pixel.pl",
                _remaining(),
                work_dir / "popper_pixel",
            )
            if ir.program:
                r = _consider_pixel(ir.program, "pixel_ilp")
                if r:
                    return r

        if include_pixels and include_blocks and _remaining() > 0:
            ir = induce(
                encoded.exs_pixel_path,
                encoded.bk_path,
                _BIAS / "dual.pl",
                _remaining(),
                work_dir / "popper_dual",
            )
            if ir.program:
                r = _consider_pixel(ir.program, "dual_ilp")
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
        "fallback_identity",
        {},
    )
