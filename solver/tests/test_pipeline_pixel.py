"""Census-fail pixel-road pipeline knobs (max_literals, scoring)."""

from __future__ import annotations

from pathlib import Path

from solver.induce import InduceResult
from solver.pipeline import solve_hybrid

# Census-fail: output gains a bar (unit/bulky counts change).
_SHORT = {
    "train": [
        {"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 0, 8, 8, 8]]},
    ],
    "test": [
        {"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 0, 8, 8, 8]]},
    ],
}

_MATCH = {
    "train": [
        {
            "input": [[0, 4, 8, 8, 8, 8, 8, 8, 8, 0]],
            "output": [[0, 8, 8, 8, 8, 8, 8, 8, 4, 0]],
        }
    ],
    "test": [
        {
            "input": [[0, 4, 8, 8, 8, 8, 8, 8, 8, 0]],
            "output": [[0, 8, 8, 8, 8, 8, 8, 8, 4, 0]],
        }
    ],
}


def test_mismatch_induce_uses_max_literals_40(tmp_path: Path, monkeypatch):
    captured: dict = {}

    def fake_induce(*_args, **kwargs):
        captured["max_literals"] = kwargs.get("max_literals")
        return InduceResult(
            None,
            "exhausted",
            0.01,
            max_literals=int(kwargs.get("max_literals") or 0),
        )

    monkeypatch.setattr("solver.pipeline.induce", fake_induce)
    solve_hybrid(_SHORT, timeout=5, work_dir=tmp_path / "w")
    assert captured["max_literals"] == 40


def test_census_match_induce_keeps_object_max_literals(tmp_path: Path, monkeypatch):
    captured: list = []

    def fake_induce(*_args, **kwargs):
        captured.append(kwargs.get("max_literals"))
        return InduceResult(
            None,
            "exhausted",
            0.01,
            max_literals=int(kwargs.get("max_literals") or 0),
        )

    monkeypatch.setattr("solver.pipeline.induce", fake_induce)
    solve_hybrid(_MATCH, timeout=5, work_dir=tmp_path / "w")
    from solver.bias_gen import OBJECT_MAX_LITERALS

    assert captured
    assert all(v == OBJECT_MAX_LITERALS for v in captured)
