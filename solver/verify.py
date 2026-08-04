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
