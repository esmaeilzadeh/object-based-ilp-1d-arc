"""B0: failure_reason + object bias literal budget."""

from __future__ import annotations

from pathlib import Path

from solver.bias_gen import (
    OBJECT_MAX_BODY,
    OBJECT_MAX_CLAUSES,
    OBJECT_MAX_LITERALS,
    OBJECT_MAX_VARS,
    render_object_bias,
)
from solver.induce import _literals_from_bias


def test_object_b0_budgets():
    assert OBJECT_MAX_VARS == 10
    assert OBJECT_MAX_BODY == 6
    assert OBJECT_MAX_CLAUSES == 4
    assert OBJECT_MAX_LITERALS == 28
    text = render_object_bias()
    assert "max_vars(10)." in text
    assert "max_body(6)." in text
    assert "max_clauses(4)." in text


def test_literals_from_bias_matches_formula(tmp_path: Path):
    bias = tmp_path / "bias.pl"
    bias.write_text("max_vars(10).\nmax_body(6).\nmax_clauses(4).\n")
    assert _literals_from_bias(bias) == 28
    assert _literals_from_bias(bias, override=18) == 18


def test_solve_result_has_failure_fields():
    from solver.pipeline import SolveResult

    r = SolveResult(
        [0],
        "",
        "fallback_identity",
        False,
        "low",
        failure_reason="popper_timeout",
        failure_detail={"max_literals": 28},
    )
    d = r.to_dict()
    assert d["failure_reason"] == "popper_timeout"
    assert d["failure_detail"]["max_literals"] == 28
