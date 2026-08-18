"""Census-fail pixel encode vs Decom NEG_GEN / test IDs."""

from __future__ import annotations

import re
from pathlib import Path

from solver.census import census_match
from solver.encoder import encode_instance
from solver.pixel_encode import encode_pixel_instance

# Width 4 identity-like pair that still fails census (output gains a bar).
_SHORT = {
    "train": [
        {"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 0, 8, 8, 8]]},
    ],
    "test": [
        {"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 0, 8, 8, 8]]},
    ],
}

_PCOPY = Path("raw_data/onedarcraw/dataset/1d_pcopy_1c/1d_pcopy_1c_0.json")

_POS = re.compile(r"pos\(out\((\d+),(\d+),(\d+)\)\)")
_NEG = re.compile(r"neg\(out\((\d+),(\d+),(\d+)\)\)")


def _atoms(text: str, pat: re.Pattern[str]) -> set[tuple[int, int, int]]:
    return {(int(a), int(b), int(c)) for a, b, c in pat.findall(text)}


def test_short_grid_neg_gen_covers_0_to_32(tmp_path: Path):
    assert census_match(_SHORT["train"]) is False
    enc = encode_pixel_instance(_SHORT, tmp_path / "enc")
    exs = enc.exs_pixel_path.read_text()
    negs = _atoms(exs, _NEG)
    poss = _atoms(exs, _POS)
    w = 7  # output width
    # Decom NEG_GEN: 33 positions × 10 colors minus one gold pos per cell.
    assert (0, 31, 1) in negs
    assert (0, 32, 9) in negs
    assert len(negs) == 33 * 10 - w
    assert all(c != 0 for _, _, c in poss)
    assert (0, 3, 0) not in poss  # gold zero is not a learning pos


def test_pixel_test_pl_uses_example_id_zero(tmp_path: Path):
    enc = encode_pixel_instance(_SHORT, tmp_path / "enc")
    test_txt = enc.test_path.read_text()
    poss = _atoms(test_txt, _POS)
    assert enc.test[0].ex_id == 0
    assert any(ex == 0 for ex, _, _ in poss)
    assert not any(ex == 1 for ex, _, _ in poss)


def test_pcopy_train_exs_has_tape_32_negs(tmp_path: Path):
    enc = encode_pixel_instance(_PCOPY, tmp_path / "pcopy")
    negs = _atoms(enc.exs_pixel_path.read_text(), _NEG)
    assert any(idx == 31 for _ex, idx, _c in negs)
    poss = _atoms(enc.exs_pixel_path.read_text(), _POS)
    assert all(c != 0 for _, _, c in poss)


def test_census_match_hybrid_has_no_out3_learning_negs(tmp_path: Path):
    inst = {
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
    assert census_match(inst["train"]) is True
    enc = encode_instance(inst, tmp_path / "enc")
    blob = enc.exs_object_path.read_text()
    assert enc.exs_unit_path is None or not enc.exs_unit_path.exists()
    assert not _atoms(blob, _NEG)
    assert "head_pred(out,3)." not in enc.bias_object_path.read_text()
    assert "head_pred(out_block,4)." in enc.bias_object_path.read_text()
