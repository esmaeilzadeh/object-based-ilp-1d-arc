"""Unit tests for staged train paint checker."""

from __future__ import annotations

from pathlib import Path

from solver.encoder import encode_instance
from solver.paint_check import make_paint_checker, paint_ok_sync


def _tiny_denoise() -> dict:
    # Keep length-3 block; drop trailing noise 4.
    return {
        "train": [
            {
                "input": [[0, 4, 4, 4, 0, 4]],
                "output": [[0, 4, 4, 4, 0, 0]],
            }
        ],
        "test": [
            {
                "input": [[0, 3, 3, 3, 0, 3]],
                "output": [[0, 3, 3, 3, 0, 0]],
            }
        ],
    }


def test_paint_ok_accepts_correct_program(tmp_path: Path):
    enc = encode_instance(_tiny_denoise(), tmp_path / "enc")
    # b1 is the length-3 colored run at start 1 (runs: b0 empty, b1=4s, b2 empty, b3 noise)
    prog = (
        "out_block(A,B,C,D,E) :- largest(A,B), s0(C), block(A,B,D,E).\n"
    )
    assert paint_ok_sync(prog, enc.bk_path, enc.out_dir / "grids.json")


def test_paint_ok_rejects_overpaint(tmp_path: Path):
    enc = encode_instance(_tiny_denoise(), tmp_path / "enc")
    # Emit every colored input block at Off=0 (paints noise too).
    prog = "out_block(A,B,C,D,E) :- block(A,B,D,E), s0(C).\n"
    assert not paint_ok_sync(prog, enc.bk_path, enc.out_dir / "grids.json")


def test_make_paint_checker_true_means_bad(tmp_path: Path):
    enc = encode_instance(_tiny_denoise(), tmp_path / "enc")
    checker = make_paint_checker(enc.bk_path)
    assert checker is not None
    good = "out_block(A,B,C,D,E) :- largest(A,B), s0(C), block(A,B,D,E).\n"
    bad = "out_block(A,B,C,D,E) :- block(A,B,D,E), s0(C).\n"
    assert checker(good) is False
    assert checker(bad) is True


def test_make_paint_checker_none_without_grids(tmp_path: Path):
    bk = tmp_path / "bk.pl"
    bk.write_text("block(0,b0,s1,v1).\n")
    assert make_paint_checker(bk) is None
