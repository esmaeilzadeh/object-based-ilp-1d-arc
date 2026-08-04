"""Object-only solver contracts (no ladder / pixel / dual kwargs)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from solver.pipeline import solve


_TINY = {
    "train": [
        {"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]},
        {"input": [[3, 0, 4, 4]], "output": [[3, 0, 4, 4]]},
    ],
    "test": [{"input": [[5, 5, 0, 6]], "output": [[5, 5, 0, 6]]}],
}


def test_solve_signature_rejects_ladder_flags():
    sig = inspect.signature(solve)
    for banned in ("ladder", "force_bias", "include_pixels", "include_blocks", "include_aggregations", "canonicalize_colors"):
        assert banned not in sig.parameters, banned


def test_solve_level_is_object_or_fallback(tmp_path: Path):
    r = solve(_TINY, timeout=1, work_dir=tmp_path / "w")
    assert r.level in {"object_ilp", "fallback_identity"}
    assert r.level not in {"pixel_ilp", "dual_ilp", "block_ilp", "dual_no_ladder"}


def test_fallback_never_verified(tmp_path: Path):
    r = solve(_TINY, timeout=1, work_dir=tmp_path / "w2")
    if r.level == "fallback_identity":
        assert r.verified_train is False
        assert r.confidence == "low"


def test_harness_modes_block_primary_only():
    from solver import harness

    assert list(harness.MODES.keys()) == ["block_primary"]
