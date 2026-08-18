"""Tests for out_block → pixel decoder (concat runs, gaps as v0)."""

from pathlib import Path

import pytest

from solver.decode import apply_object_program
from solver.encoder import encode_instance


def test_object_decoder_concat_with_gap(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]},
        ],
        "test": [{"input": [[2, 2, 0, 9]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    # Out runs: b0 len2 v2, b1 len1 v0, b2 len1 v9
    prog = "out_block(0,b0,s2,v2).\nout_block(0,b1,s1,v0).\nout_block(0,b2,s1,v9).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
    )
    assert preds[0] == [2, 2, 0, 9]


def test_object_decoder_typed_roles_fill(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[7, 0, 7]], "output": [[7, 7, 7]]}],
            "test": [{"input": [[7, 0, 7]]}],
        },
        tmp_path / "enc",
    )
    assert enc.typed_roles
    prog = "out_block(0,b0,s3,v7).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
    )
    assert preds[0] == [7, 7, 7]


def test_object_decoder_rejects_wrong_width(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]}],
            "test": [{"input": [[1, 1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    prog = "out_block(0,b0,s3,v1).\n"  # width 3 != 4
    with pytest.raises(ValueError):
        apply_object_program(
            prog,
            enc.bk_path,
            enc.train,
            typed_roles=True,
        )


def test_train_then_test_apply_uses_fresh_engine(tmp_path: Path):
    """Consulting train bk then test_bk in one janus engine can SIGSEGV."""
    enc = encode_instance(
        {
            "train": [{"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]}],
            "test": [{"input": [[9, 0, 2, 2]], "output": [[9, 0, 2, 2]]}],
        },
        tmp_path / "enc",
    )
    train_prog = (
        "out_block(0,b0,s2,v2).\nout_block(0,b1,s1,v0).\nout_block(0,b2,s1,v9).\n"
    )
    test_prog = (
        "out_block(1,b0,s1,v9).\nout_block(1,b1,s1,v0).\nout_block(1,b2,s2,v2).\n"
    )
    train_preds = apply_object_program(
        train_prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
    )
    test_preds = apply_object_program(
        test_prog,
        enc.test_bk_path,
        enc.test,
        typed_roles=True,
    )
    assert train_preds[0] == [2, 2, 0, 9]
    assert test_preds[1] == [9, 0, 2, 2]
