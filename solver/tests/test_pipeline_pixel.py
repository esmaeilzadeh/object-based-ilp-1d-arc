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

    assert captured == [OBJECT_MAX_LITERALS]


def test_census_match_uses_single_out_block_head(tmp_path: Path, monkeypatch):
    def fake_induce(*_args, **kwargs):
        return InduceResult(
            None,
            "exhausted",
            0.01,
            max_literals=int(kwargs.get("max_literals") or 0),
        )

    monkeypatch.setattr("solver.pipeline.induce", fake_induce)
    r = solve_hybrid(_MATCH, timeout=5, work_dir=tmp_path / "w")
    assert r.failure_detail.get("census_match") is True
    assert r.failure_detail.get("road") == "object"
    enc = tmp_path / "w" / "encode"
    assert (enc / "exs_object.pl").exists()
    assert not (enc / "exs_unit.pl").exists()
    bias = (enc / "bias_object.pl").read_text()
    assert "head_pred(out_block,4)." in bias
    assert "head_pred(out_pixel,4)." not in bias
    assert "pos(out_block(" in (enc / "exs_object.pl").read_text()
    assert "pos(out_pixel(" not in (enc / "exs_object.pl").read_text()


def test_mismatch_paint_verify_is_not_sole_success_gate(tmp_path: Path, monkeypatch):
    def fake_induce(*_args, **_kwargs):
        return InduceResult(
            "out(A,B,C) :- in(A,B,C).\n",
            "ok",
            0.01,
            max_literals=40,
        )

    monkeypatch.setattr("solver.pipeline.induce", fake_induce)
    monkeypatch.setattr(
        "solver.verify.verify_pixel_on_train",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "solver.pipeline.score_program_soft",
        lambda *_a, **_k: ([5, 0, 20, 0], 1.0),
    )
    monkeypatch.setattr(
        "solver.decode.apply_pixel_program",
        lambda _prog, _bk, examples: {
            eg.ex_id: list(eg.out or eg.inp) for eg in examples
        },
    )
    r = solve_hybrid(_SHORT, timeout=5, work_dir=tmp_path / "w")
    assert r.failure_reason != "paint_verify_failed"
    assert r.level == "pixel_ilp"
    assert r.soft_matrix == [5, 0, 20, 0]
    assert r.soft_accuracy == 1.0
    assert r.failure_detail.get("decom_solved") is True
