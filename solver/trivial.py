"""Closed-form trivial solvers that emit Prolog programs."""

from __future__ import annotations

from typing import List, Optional, Tuple

from solver.encoder import EncodeResult, ExampleGrids
from solver.verify import verify_on_train


def _identity_prog() -> str:
    return "out(E,P,C) :- in(E,P,C).\n"


def _recolor_prog(mapping: dict) -> str:
    lines = []
    for a, b in mapping.items():
        lines.append(f"out(E,P,{b}) :- in(E,P,{a}).")
    return "\n".join(lines) + "\n"


def _shift_prog(k: int) -> str:
    # out[i] = in[i-k] if in bounds else empty (no fact → 0)
    if k > 0:
        return (
            f"out(E,P,C) :- in(E,P2,C), add(P2,{k},P).\n"
        )
    kk = -k
    return (
        f"out(E,P,C) :- in(E,P2,C), add(P,{kk},P2).\n"
    )


def _reverse_prog() -> str:
    return "out(E,P,C) :- in(E,P2,C), from_right(E,P2,P).\n"


def _fit_recolor(train: List[ExampleGrids]) -> Optional[dict]:
    mapping = {}
    for eg in train:
        assert eg.out is not None
        if len(eg.inp) != len(eg.out):
            return None
        for a, b in zip(eg.inp, eg.out):
            if a == 0 and b != 0:
                return None
            if a == 0:
                continue
            if a in mapping and mapping[a] != b:
                return None
            mapping[a] = b
    # must be bijective on nonzero
    vals = list(mapping.values())
    if len(vals) != len(set(vals)):
        return None
    if all(mapping[k] == k for k in mapping):
        return None  # identity handled separately
    return mapping


def _fit_shift(train: List[ExampleGrids], k: int) -> bool:
    for eg in train:
        assert eg.out is not None
        w = len(eg.inp)
        if len(eg.out) != w:
            return False
        pred = [0] * w
        for i, c in enumerate(eg.inp):
            j = i + k
            if 0 <= j < w and c != 0:
                pred[j] = c
        if pred != eg.out:
            return False
    return True


def _fit_reverse(train: List[ExampleGrids]) -> bool:
    for eg in train:
        assert eg.out is not None
        if eg.out != list(reversed(eg.inp)):
            return False
    return True


def _fit_identity(train: List[ExampleGrids]) -> bool:
    return all(eg.out == eg.inp for eg in train)


def try_trivial(encoded: EncodeResult) -> Optional[Tuple[str, str]]:
    """Return (program, level_name) if a trivial solver verifies, else None."""
    train = encoded.train
    candidates: List[Tuple[str, str]] = []
    if _fit_identity(train):
        candidates.append((_identity_prog(), "trivial_identity"))
    m = _fit_recolor(train)
    if m is not None:
        candidates.append((_recolor_prog(m), "trivial_recolor"))
    max_k = min(3, max(len(eg.inp) for eg in train) - 1)
    for k in range(1, max_k + 1):
        if _fit_shift(train, k):
            candidates.append((_shift_prog(k), f"trivial_shift_+{k}"))
        if _fit_shift(train, -k):
            candidates.append((_shift_prog(-k), f"trivial_shift_-{k}"))
    if _fit_reverse(train):
        candidates.append((_reverse_prog(), "trivial_reverse"))

    for prog, name in candidates:
        if verify_on_train(prog, encoded):
            return prog, name
    return None
