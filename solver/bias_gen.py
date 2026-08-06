"""Generate mechanical object Popper bias from instance BK/exs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import FrozenSet, Optional, Sequence, Set

from solver.predicates import (
    OBJECT_BODY_ALLOWLIST,
    Predicate,
    body_preds_for_level,
    head_pred_object,
)

_BIAS_DIR = Path(__file__).resolve().parent / "bias"

_FACT_PRED_RE = re.compile(r"^([a-z][a-z0-9_]*)\(")
_SIZE_CONST_RE = re.compile(r"\bs(\d+)\b")
_VALUE_CONST_RE = re.compile(r"\bv(\d+)\b")
_RANK_CONST_RE = re.compile(r"\br(\d+)\b")

OBJECT_MAX_VARS = 10
OBJECT_MAX_BODY = 6
OBJECT_MAX_CLAUSES = 3
OBJECT_MAX_LITERALS = (1 + OBJECT_MAX_BODY) * OBJECT_MAX_CLAUSES  # 21


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


def _preds_present_in_bk(bk_text: str, allow: FrozenSet[str]) -> Set[str]:
    present: Set[str] = set()
    for line in bk_text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        m = _FACT_PRED_RE.match(s)
        if m and m.group(1) in allow:
            present.add(m.group(1))
    return present


def _constants_present_in_texts(*texts: str) -> tuple[Set[int], Set[int], Set[int]]:
    sizes: Set[int] = set()
    values: Set[int] = set()
    ranks: Set[int] = set()
    blob = "\n".join(texts)
    for m in _SIZE_CONST_RE.finditer(blob):
        sizes.add(int(m.group(1)))
    for m in _VALUE_CONST_RE.finditer(blob):
        values.add(int(m.group(1)))
    for m in _RANK_CONST_RE.finditer(blob):
        ranks.add(int(m.group(1)))
    return sizes, values, ranks


def render_object_bias_from_bk(
    bk_text: str,
    *,
    exs_text: str = "",
    max_vars: int = OBJECT_MAX_VARS,
    max_body: int = OBJECT_MAX_BODY,
    max_clauses: int = OBJECT_MAX_CLAUSES,
) -> str:
    """Mechanical object bias from one instance's BK (+ optional exs)."""
    present = _preds_present_in_bk(bk_text, OBJECT_BODY_ALLOWLIST)
    if "block(" in bk_text or any(
        ln.strip().startswith("block(") for ln in bk_text.splitlines()
    ):
        present.add("block")
    bodies = tuple(p for p in body_preds_for_level(4) if p.name in present)
    if not bodies:
        bodies = tuple(p for p in body_preds_for_level(4) if p.name == "block")

    sizes, values, ranks = _constants_present_in_texts(bk_text, exs_text)
    sizes.add(0)
    sizes.add(1)
    ranks.add(0)

    hp = head_pred_object()
    all_typed = (hp,) + bodies
    parts = [
        f"max_vars({max_vars}).",
        f"max_body({max_body}).",
        f"max_clauses({max_clauses}).",
        "enable_multi_clause.",
        ":- not body_var(_,1).",
        ":- not body_var(_,2).",
        ":- not body_var(_,3).",
        "",
        f"head_pred({hp.name},{hp.arity}).",
    ]
    for p in bodies:
        parts.append(f"body_pred({p.name},{p.arity}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    for i in sorted(sizes):
        parts.append(f"constant(s{i}, 'size').")
    for i in sorted(values):
        parts.append(f"constant(v{i}, 'value').")
    for i in sorted(ranks):
        parts.append(f"constant(r{i}, 'rank').")
    parts.append("")
    parts.append(_types_block(all_typed))
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(_bad_body_for_ex_preds(bodies))
    parts.append("")
    # Start=var2, Len=var3: size_add/sum3 legal if any arg is head Start/Len.
    body_names = {p.name for p in bodies}
    if "size_add" in body_names:
        parts.append(
            "bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), "
            "A != 2, A != 3, B != 2, B != 3, R != 2, R != 3."
        )
    if "size_sum3" in body_names:
        parts.append(
            "bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), "
            "A != 2, A != 3, B != 2, B != 3, C != 2, C != 3, R != 2, R != 3."
        )
    parts.append("")
    return "\n".join(parts) + "\n"


def render_object_bias(
    *,
    max_vars: int = OBJECT_MAX_VARS,
    max_body: int = OBJECT_MAX_BODY,
    max_clauses: int = OBJECT_MAX_CLAUSES,
) -> str:
    """Static fallback: full lean allowlist (tests / non-instance paths only)."""
    bk_lines = [f"{name}(dummy)." for name in sorted(OBJECT_BODY_ALLOWLIST)]
    return render_object_bias_from_bk(
        "\n".join(bk_lines),
        exs_text="pos(out_block(0,r0,s0,s1,v1)).",
        max_vars=max_vars,
        max_body=max_body,
        max_clauses=max_clauses,
    )


def write_bias_files(out_dir: Optional[Path] = None) -> None:
    """Write static object bias fallback only."""
    out_dir = out_dir or _BIAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "object.pl").write_text(render_object_bias())


if __name__ == "__main__":
    write_bias_files()
    print(f"wrote {_BIAS_DIR}")
