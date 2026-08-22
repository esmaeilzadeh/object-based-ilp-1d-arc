"""Tests for paper-style soft scoring and train/test BK split scoring path."""

from pathlib import Path

from solver.encoder import encode_instance
from solver.paper_score import (
    failure_matrix,
    grid_to_out_program,
    score_program_soft,
    soft_accuracy,
)


def test_soft_accuracy_formula():
    assert soft_accuracy([1, 0, 0, 0]) == 1.0
    assert soft_accuracy([0, 1, 0, 0]) == 0.0
    assert soft_accuracy([2, 2, 2, 2]) == 0.5


def test_score_perfect_out_program(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[1, 0, 2]], "output": [[1, 0, 2]]},
            {"input": [[3, 0, 0]], "output": [[3, 0, 0]]},
            {"input": [[0, 4, 0]], "output": [[0, 4, 0]]},
        ],
        "test": [{"input": [[5, 0, 6]], "output": [[5, 0, 6]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    # Perfect prediction as grounded out/3 facts for test ex_id=3.
    prog = grid_to_out_program(3, [5, 0, 6])
    matrix, acc = score_program_soft(prog, enc.test_path, work_dir=tmp_path / "score")
    assert matrix[1] == 0 and matrix[3] == 0  # no FN/FP
    assert acc == 1.0


def test_score_wrong_out_program(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[1, 0, 2]], "output": [[1, 0, 2]]},
            {"input": [[3, 0, 0]], "output": [[3, 0, 0]]},
            {"input": [[0, 4, 0]], "output": [[0, 4, 0]]},
        ],
        "test": [{"input": [[5, 0, 6]], "output": [[5, 0, 6]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    prog = grid_to_out_program(3, [5, 0, 7])  # wrong last color
    matrix, acc = score_program_soft(prog, enc.test_path, work_dir=tmp_path / "score")
    tp, fn, tn, fp = matrix
    assert fn >= 1 and fp >= 1
    assert 0.0 < acc < 1.0
    assert abs(acc - (tp + tn) / (tp + fn + tn + fp)) < 1e-9


def test_failure_matrix_nonzero_pos(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[1]], "output": [[1]]},
            {"input": [[2]], "output": [[2]]},
            {"input": [[3]], "output": [[3]]},
        ],
        "test": [{"input": [[4]], "output": [[4]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    m = failure_matrix(enc.test_path)
    assert m[0] == 0 and m[1] >= 1
