"""Cheap object-head orchestration for one 1D-ARC instance."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from solver.bias_gen import (
    OBJECT_MAX_BODY,
    OBJECT_MAX_CLAUSES,
    OBJECT_MAX_LITERALS,
    OBJECT_MAX_VARS,
)
from solver.decode import apply_object_program
from solver.encoder import encode_instance
from solver.induce import InduceResult, induce
from solver.paper_score import grid_to_out_program, score_program_soft
from solver.verify import verify_object_on_train

PathLike = Union[str, Path]


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
    work_dir: Optional[PathLike] = None,
) -> SolveResult:
    """Induce ``out_block/5``, paint-verify on train, decode test, soft-score."""
    work_dir = Path(work_dir or Path("work") / "solve")
    work_dir.mkdir(parents=True, exist_ok=True)

    encoded = encode_instance(instance, work_dir / "encode")
    test0 = encoded.test[0]
    rem = max(int(timeout), 0)

    def _soft(pred: List[int]) -> tuple:
        if not encoded.test_path.exists() or test0.out is None:
            return [0, 0, 0, 0], 0.0
        score_prog = grid_to_out_program(test0.ex_id, pred)
        return score_program_soft(
            score_prog,
            encoded.test_path,
            work_dir=work_dir / "soft_score",
        )

    def _fallback(reason: str, ir: InduceResult, prog: str = "") -> SolveResult:
        pred = list(test0.inp)
        matrix, soft = _soft(pred)
        return SolveResult(
            pred,
            prog,
            "fallback_identity",
            False,
            "low",
            matrix,
            soft,
            reason,
            _bias_detail(ir, rem),
        )

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

    if rem <= 0:
        return _fallback(
            "popper_timeout",
            InduceResult(None, "timeout", 0.0, max_literals=OBJECT_MAX_LITERALS),
        )

    t0 = time.time()
    ir = induce(
        encoded.exs_object_path,
        encoded.bk_path,
        bias_path,
        rem,
        work_dir / "popper_object",
        max_literals=OBJECT_MAX_LITERALS,
    )
    _ = time.time() - t0

    if ir.program:
        if verify_object_on_train(ir.program, encoded):
            try:
                preds = apply_object_program(
                    ir.program,
                    encoded.test_bk_path,
                    encoded.test,
                    typed_roles=encoded.typed_roles,
                    block_geometry=encoded.block_geometry,
                )
                pred = preds[test0.ex_id]
            except Exception as e:
                detail = _bias_detail(ir, rem)
                detail["decode_error"] = str(e)
                pred = list(test0.inp)
                matrix, soft = _soft(pred)
                return SolveResult(
                    pred,
                    ir.program,
                    "fallback_identity",
                    False,
                    "low",
                    matrix,
                    soft,
                    "decode_error",
                    detail,
                )
            matrix, soft = _soft(pred)
            return SolveResult(
                pred,
                ir.program,
                "object_ilp",
                True,
                "high",
                matrix,
                soft,
                None,
                _bias_detail(ir, rem),
            )
        return _fallback("paint_verify_failed", ir, prog=ir.program)

    if ir.status == "timeout":
        return _fallback("popper_timeout", ir)
    if ir.status == "error":
        return _fallback("popper_error", ir)
    return _fallback("popper_exhausted", ir)


def solve_hybrid(
    instance: Union[PathLike, dict],
    *,
    timeout: int = 600,
    work_dir: Optional[PathLike] = None,
) -> SolveResult:
    """Census gate → parallel two-head object road or one ``out/3``. No failure ladder."""
    from solver.census import census_match, unit_runs
    from solver.decode import apply_hybrid_program, apply_pixel_program
    from solver.encoder_hybrid import encode_hybrid_block
    from solver.pixel_encode import encode_pixel_instance
    from solver.verify import verify_hybrid_on_train, verify_pixel_on_train

    work_dir = Path(work_dir or Path("work") / "solve_hybrid")
    work_dir.mkdir(parents=True, exist_ok=True)

    from solver.encoder import _load_json

    obj = instance if isinstance(instance, dict) else _load_json(instance)
    match = census_match(obj["train"])
    rem = max(int(timeout), 0)

    def _soft_from(encoded, test0, pred):
        if not encoded.test_path.exists() or test0.out is None:
            return [0, 0, 0, 0], 0.0
        score_prog = grid_to_out_program(test0.ex_id, pred)
        return score_program_soft(
            score_prog,
            encoded.test_path,
            work_dir=work_dir / "soft_score",
        )

    def _fail(reason, encoded, test0, ir, prog="", detail_extra=None):
        pred = list(test0.inp)
        matrix, soft = _soft_from(encoded, test0, pred)
        detail = _bias_detail(ir, rem)
        detail["census_match"] = match
        if detail_extra:
            detail.update(detail_extra)
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

    if rem <= 0:
        encoded = encode_hybrid_block(instance, work_dir / "encode") if match else encode_pixel_instance(instance, work_dir / "encode")
        test0 = encoded.test[0]
        return _fail(
            "popper_timeout",
            encoded,
            test0,
            InduceResult(None, "timeout", 0.0, max_literals=OBJECT_MAX_LITERALS),
        )

    if not match:
        encoded = encode_pixel_instance(instance, work_dir / "encode")
        test0 = encoded.test[0]
        ir = induce(
            encoded.exs_pixel_path,
            encoded.bk_path,
            encoded.bias_pixel_path,
            rem,
            work_dir / "popper_pixel",
        )
        if not ir.program:
            reason = {
                "timeout": "popper_timeout",
                "error": "popper_error",
            }.get(ir.status, "popper_exhausted")
            return _fail(reason, encoded, test0, ir)
        if not verify_pixel_on_train(ir.program, encoded):
            return _fail("paint_verify_failed", encoded, test0, ir, prog=ir.program)
        try:
            preds = apply_pixel_program(
                ir.program, encoded.test_bk_path, encoded.test
            )
            pred = preds[test0.ex_id]
        except Exception as e:
            return _fail(
                "decode_error",
                encoded,
                test0,
                ir,
                prog=ir.program,
                detail_extra={"decode_error": str(e)},
            )
        matrix, soft = _soft_from(encoded, test0, pred)
        detail = _bias_detail(ir, rem)
        detail["census_match"] = False
        detail["road"] = "pixel"
        return SolveResult(
            pred,
            ir.program,
            "pixel_ilp",
            True,
            "high",
            matrix,
            soft,
            None,
            detail,
        )

    encoded = encode_hybrid_block(instance, work_dir / "encode")
    test0 = encoded.test[0]
    n_unit = max(len(unit_runs(eg.inp)) for eg in encoded.train)
    from concurrent.futures import ThreadPoolExecutor

    if n_unit > 0:
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_b = pool.submit(
                induce,
                encoded.exs_object_path,
                encoded.bk_path,
                encoded.bias_object_path,
                rem,
                work_dir / "popper_object",
                max_literals=OBJECT_MAX_LITERALS,
            )
            fut_u = pool.submit(
                induce,
                encoded.exs_unit_path,
                encoded.bk_path,
                encoded.bias_unit_path,
                rem,
                work_dir / "popper_unit",
                max_literals=OBJECT_MAX_LITERALS,
            )
            ir_b = fut_b.result()
            ir_u = fut_u.result()
    else:
        ir_b = induce(
            encoded.exs_object_path,
            encoded.bk_path,
            encoded.bias_object_path,
            rem,
            work_dir / "popper_object",
            max_literals=OBJECT_MAX_LITERALS,
        )
        ir_u = InduceResult("", "ok", 0.0, max_literals=OBJECT_MAX_LITERALS)

    if not ir_b.program:
        reason = {
            "timeout": "popper_timeout",
            "error": "popper_error",
        }.get(ir_b.status, "popper_exhausted")
        return _fail(
            reason,
            encoded,
            test0,
            ir_b,
            detail_extra={"head": "out_block", "parallel": n_unit > 0, "t_each": rem},
        )

    unit_prog = ""
    if n_unit > 0:
        if not ir_u.program:
            reason = {
                "timeout": "popper_timeout",
                "error": "popper_error",
            }.get(ir_u.status, "popper_exhausted")
            return _fail(
                reason,
                encoded,
                test0,
                ir_u,
                prog=ir_b.program or "",
                detail_extra={"head": "out_pixel", "parallel": True, "t_each": rem},
            )
        unit_prog = ir_u.program

    combined = (ir_b.program or "") + ("\n" + unit_prog if unit_prog else "")
    if not verify_hybrid_on_train(ir_b.program or "", unit_prog, encoded):
        return _fail(
            "paint_verify_failed",
            encoded,
            test0,
            ir_u if n_unit > 0 else ir_b,
            prog=combined,
            detail_extra={"head": "hybrid", "parallel": n_unit > 0, "t_each": rem},
        )
    try:
        preds = apply_hybrid_program(
            ir_b.program or "",
            unit_prog,
            encoded.test_bk_path,
            encoded.test,
            typed_roles=encoded.typed_roles,
            block_geometry=encoded.block_geometry,
            unit_geometry=encoded.unit_geometry,
            extra_offs=encoded.observed_offs,
        )
        pred = preds[test0.ex_id]
    except Exception as e:
        return _fail(
            "decode_error",
            encoded,
            test0,
            ir_b,
            prog=combined,
            detail_extra={"decode_error": str(e)},
        )
    matrix, soft = _soft_from(encoded, test0, pred)
    detail = _bias_detail(ir_b, rem)
    detail["census_match"] = True
    detail["road"] = "hybrid_block"
    detail["n_unit"] = n_unit
    detail["parallel"] = n_unit > 0
    detail["t_each"] = rem
    detail["unit_popper_status"] = ir_u.status if n_unit > 0 else "skipped"
    return SolveResult(
        pred,
        combined,
        "hybrid_ilp",
        True,
        "high",
        matrix,
        soft,
        None,
        detail,
    )

