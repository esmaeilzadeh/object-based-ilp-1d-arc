"""Generate Popper bias files from the predicate inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from solver.predicates import (
    Predicate,
    body_preds_for_level,
    head_pred,
    head_pred_object,
)

_BIAS_DIR = Path(__file__).resolve().parent / "bias"


def _types_block(preds: Sequence[Predicate]) -> str:
    return "\n".join(f"type({p.name},{p.types})." for p in preds)


def _bad_body_for_ex_preds(preds: Sequence[Predicate]) -> str:
    lines = []
    for p in preds:
        if not p.types or p.types[0] != "ex":
            continue
        n = p.arity
        if n < 2 or n > 6:
            continue
        slots = ",".join(["_"] * (n - 1))
        lines.append(
            f"bad_body({p.name}, Vars):- vars(_, Vars), Vars = (V0,{slots}), V0 != 0."
        )
    return "\n".join(lines)


def _constants_for_level(level: int) -> list[str]:
    """Typed constants. Block/object bias omit position/size constants to stop overfit.

    Object bias (level 4) also omits value constants — colors bind from ``block/4``.
    """
    lines = []
    if level != 4:
        for i in range(10):
            lines.append(f"constant(v{i}, value).")
    if level >= 3 and level != 4:
        for i in range(10):
            lines.append(f"constant(c{i}, position).")
        for i in range(10):
            lines.append(f"constant(s{i}, size).")
        for i in range(1, 10):
            lines.append(f"constant(r{i}, rank).")
    if level != 4:
        lines.append("constant(left, edge).")
        lines.append("constant(right, edge).")
    return lines


def _render(head: Predicate, bodies: Sequence[Predicate], *, max_vars: int, max_body: int, level: int) -> str:
    all_typed = (head,) + tuple(bodies)
    parts = [
        f"max_vars({max_vars}).",
        f"max_body({max_body}).",
        "non_datalog.",
        "",
        f"head_pred({head.name},{head.arity}).",
    ]
    for p in bodies:
        parts.append(f"body_pred({p.name},{p.arity}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    parts.extend(_constants_for_level(level))
    parts.append("")
    parts.append(_types_block(all_typed))
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(_bad_body_for_ex_preds(bodies))
    parts.append("")
    return "\n".join(parts) + "\n"


def render_bias(level: int, *, max_vars: int, max_body: int) -> str:
    return _render(
        head_pred(),
        body_preds_for_level(level),
        max_vars=max_vars,
        max_body=max_body,
        level=level,
    )


def render_object_bias(*, max_vars: int = 8, max_body: int = 10) -> str:
    """Object-head bias: block geometry + marker tools for short out_block rules."""
    return _render(
        head_pred_object(),
        body_preds_for_level(4),
        max_vars=max_vars,
        max_body=max_body,
        level=4,
    )


def _pixel_only_bias() -> str:
    """Paper-parity pixel bias (Decom relational decomposition)."""
    return """max_vars(7).
max_body(20).
non_datalog.

:- not body_var(_,1).
:- not body_var(_,2).

head_pred(out,3).
body_pred(in,3).
body_pred(empty,2).
body_pred(width,2).
body_pred(my_succ,2).
body_pred(lt,2).
body_pred(add,3).
body_pred(C,1):- constant(C,_).

constant(v0, value).
constant(v1, value).
constant(v2, value).
constant(v3, value).
constant(v4, value).
constant(v5, value).
constant(v6, value).
constant(v7, value).
constant(v8, value).
constant(v9, value).
constant(c0, position).
constant(c1, position).
constant(c2, position).
constant(c3, position).
constant(c4, position).
constant(c5, position).
constant(c6, position).
constant(c7, position).
constant(c8, position).
constant(c9, position).

type(out,(ex,position,value)).
type(in,(ex,position,value)).
type(empty,(ex,position)).
type(width,(ex,position)).
type(my_succ,(position,position)).
type(lt,(position,position)).
type(add,(position,position,position)).
type(C,(T,)):- constant(C,T).

bad_body(in, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(empty, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(width, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
"""


def write_bias_files(out_dir: Optional[Path] = None) -> None:
    out_dir = out_dir or _BIAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "block.pl").write_text(render_bias(2, max_vars=8, max_body=12))
    (out_dir / "dual.pl").write_text(render_bias(3, max_vars=9, max_body=16))
    (out_dir / "object.pl").write_text(render_object_bias(max_body=10))
    (out_dir / "pixel.pl").write_text(_pixel_only_bias())


if __name__ == "__main__":
    write_bias_files()
    print("wrote", _BIAS_DIR)
