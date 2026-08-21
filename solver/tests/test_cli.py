"""CLI mode dispatch (hybrid_census default vs block_primary)."""

from __future__ import annotations

from pathlib import Path

from solver.cli import main
from solver.pipeline import SolveResult


def _fake_result() -> SolveResult:
    return SolveResult(
        [0, 1],
        "",
        "fallback_identity",
        False,
        "low",
        [0, 0, 0, 0],
        0.0,
        "popper_exhausted",
        {},
    )


def test_cli_default_mode_calls_solve_hybrid(tmp_path: Path, monkeypatch):
    json_path = tmp_path / "t.json"
    json_path.write_text("{}")
    called = {}

    def fake_hybrid(path, *, timeout, work_dir):
        called["hybrid"] = (path, timeout, work_dir)
        return _fake_result()

    def fake_solve(*_a, **_k):
        called["solve"] = True
        return _fake_result()

    monkeypatch.setattr("solver.cli.solve_hybrid", fake_hybrid)
    monkeypatch.setattr("solver.cli.solve", fake_solve)
    monkeypatch.setattr("builtins.print", lambda *_a, **_k: None)

    main([str(json_path), "--timeout", "12", "--work-dir", str(tmp_path / "w")])

    assert "hybrid" in called
    assert called["hybrid"][0] == json_path
    assert called["hybrid"][1] == 12
    assert "solve" not in called


def test_cli_block_primary_calls_solve(tmp_path: Path, monkeypatch):
    json_path = tmp_path / "t.json"
    json_path.write_text("{}")
    called = {}

    def fake_hybrid(*_a, **_k):
        called["hybrid"] = True
        return _fake_result()

    def fake_solve(path, *, timeout, work_dir):
        called["solve"] = (path, timeout, work_dir)
        return _fake_result()

    monkeypatch.setattr("solver.cli.solve_hybrid", fake_hybrid)
    monkeypatch.setattr("solver.cli.solve", fake_solve)
    monkeypatch.setattr("builtins.print", lambda *_a, **_k: None)

    main(
        [
            str(json_path),
            "--mode",
            "block_primary",
            "--timeout",
            "9",
            "--work-dir",
            str(tmp_path / "w"),
        ]
    )

    assert "solve" in called
    assert called["solve"][1] == 9
    assert "hybrid" not in called


def test_cli_writes_out_json(tmp_path: Path, monkeypatch):
    json_path = tmp_path / "t.json"
    json_path.write_text("{}")
    out = tmp_path / "pred.json"

    monkeypatch.setattr("solver.cli.solve_hybrid", lambda *_a, **_k: _fake_result())
    monkeypatch.setattr("builtins.print", lambda *_a, **_k: None)

    main([str(json_path), "--out", str(out)])
    assert out.exists()
    assert '"fallback_identity"' in out.read_text()
