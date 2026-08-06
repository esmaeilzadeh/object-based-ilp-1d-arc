"""Tests for out_block → pixel decoder (absolute Start)."""

from pathlib import Path

import pytest

from solver.decode import apply_object_program
from solver.encoder import encode_instance


def test_object_decoder_paints_blocks(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]},
        ],
        "test": [{"input": [[2, 2, 0, 9]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    # Independent out: Rank, absolute Start, Len, Color (incl. empty v0).
    prog = (
        "out_block(0,r0,s0,s2,v2).\n"
        "out_block(0,r1,s2,s1,v0).\n"
        "out_block(0,r2,s3,s1,v9).\n"
    )
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
    )
    assert preds[0] == [2, 2, 0, 9]


def test_object_decoder_typed_roles(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[7, 0, 7]], "output": [[7, 7, 7]]}],
            "test": [{"input": [[7, 0, 7]]}],
        },
        tmp_path / "enc",
    )
    assert enc.typed_roles
    prog = "out_block(0,r0,s0,s3,v7).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
    )
    assert preds[0] == [7, 7, 7]


def test_object_decoder_rejects_overlap(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]}],
            "test": [{"input": [[1, 1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    prog = "out_block(0,r0,s0,s3,v1).\nout_block(0,r1,s1,s2,v2).\n"
    with pytest.raises(ValueError):
        apply_object_program(
            prog,
            enc.bk_path,
            enc.train,
            typed_roles=True,
        )
