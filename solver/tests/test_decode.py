"""Tests for out_block → pixel decoder."""

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
    prog = "out_block(0,b0,s0,s2,v2).\nout_block(0,b2,s0,s1,v9).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
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
    prog = "out_block(0,b0,s0,s3,v7).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert preds[0] == [7, 7, 7]


def test_object_decoder_signed_offset(tmp_path: Path):
    """Grow-left Off=-1 paints one cell before the input run start."""

    inst = {
        "train": [
            {
                "input": [[0, 0, 0, 4, 8, 8, 8, 0]],
                "output": [[0, 0, 0, 8, 8, 8, 8, 4]],
            }
        ],
        "test": [{"input": [[0, 0, 0, 4, 8, 8, 8, 0]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    assert "sm1(sm1)." in enc.bk_path.read_text()
    # Input runs: b1 color4 at 3; b2 color8 at 4 len 3.
    prog = "out_block(0,b2,sm1,s4,v8).\nout_block(0,b1,s4,s1,v4).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert preds[0] == [0, 0, 0, 8, 8, 8, 8, 4]


def test_object_decoder_rejects_overlap(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]}],
            "test": [{"input": [[1, 1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    prog = "out_block(0,b0,s0,s3,v1).\nout_block(0,b0,s1,s2,v2).\n"
    with pytest.raises(ValueError):
        apply_object_program(
            prog,
            enc.bk_path,
            enc.train,
            typed_roles=True,
            block_geometry=enc.block_geometry,
        )
