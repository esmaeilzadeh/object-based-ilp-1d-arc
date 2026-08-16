"""Closed-world object decoder and exact train verifier."""

from __future__ import annotations

from typing import Sequence

from solver.decode import apply_object_program
from solver.encoder import EncodeResult


def grids_equal(pred: Sequence[int], gold: Sequence[int]) -> bool:
    return list(pred) == list(gold)


def verify_object_on_train(program: str, encoded: EncodeResult) -> bool:
    try:
        preds = apply_object_program(
            program,
            encoded.bk_path,
            encoded.train,
            typed_roles=encoded.typed_roles,
            block_geometry=encoded.block_geometry,
        )
    except Exception:
        return False
    for eg in encoded.train:
        assert eg.out is not None
        if not grids_equal(preds[eg.ex_id], eg.out):
            return False
    return True


def verify_hybrid_on_train(
    block_program: str,
    unit_program: str,
    encoded: EncodeResult,
) -> bool:
    from solver.decode import apply_hybrid_program

    try:
        preds = apply_hybrid_program(
            block_program,
            unit_program,
            encoded.bk_path,
            encoded.train,
            typed_roles=encoded.typed_roles,
            block_geometry=encoded.block_geometry,
            unit_geometry=encoded.unit_geometry,
            extra_offs=encoded.observed_offs,
        )
    except Exception:
        return False
    for eg in encoded.train:
        assert eg.out is not None
        if not grids_equal(preds[eg.ex_id], eg.out):
            return False
    return True


def verify_pixel_on_train(program: str, encoded: EncodeResult) -> bool:
    from solver.decode import apply_pixel_program

    try:
        preds = apply_pixel_program(program, encoded.bk_path, encoded.train)
    except Exception:
        return False
    for eg in encoded.train:
        assert eg.out is not None
        if not grids_equal(preds[eg.ex_id], eg.out):
            return False
    return True
