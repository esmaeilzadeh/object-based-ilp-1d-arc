"""Throwaway smoke: index-only in/out blocks (empty runs count).

  in_block(E, Bid, Len, Color)
  out_block(E, Bid, Len, Color)   # head; not a body pred

Bids are left-to-right run indices, numbered independently on input vs output.
Does not modify solver/. Isolated under work/span_decom_smoke/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solver.grid import flatten, segment_all_runs
from solver.induce import induce

DATASET = ROOT / "raw_data/onedarcraw/dataset"
OUT_ROOT = Path(__file__).resolve().parent / "runs"

# Flip only until this encoding passes; other categories stay commented out.
TASKS = [
    ("1d_flip", 0),
]


def _n(i: int) -> str:
    return f"n{i}"


def _v(i: int) -> str:
    return f"v{i}"


def _runs(row: Sequence[int]) -> List[Tuple[int, int, int]]:
    """(bid, length, color) including empty (color 0) runs."""
    return [(i, e - s + 1, c) for i, (s, e, c) in enumerate(segment_all_runs(row))]


def _pred_in_bk(bk_text: str, name: str) -> bool:
    token = f"{name}("
    return any(
        line.startswith(token) or f" {token}" in line or f"({token}" in line
        for line in bk_text.splitlines()
    )


def _bk_for_row(ex: int, row: Sequence[int]) -> Tuple[List[str], Set[int], int]:
    """Input BK: in_block + succession on run indices; add/succ on bids and lengths."""
    facts: List[str] = []
    runs = _runs(row)
    w = len(row)
    bids = [b for b, _L, _c in runs]
    lengths = [L for _b, L, _c in runs]
    observed: Set[int] = {0, 1}
    observed.update(bids)
    observed.update(lengths)

    for b, L, c in runs:
        facts.append(f"in_block({ex},{_n(b)},{_n(L)},{_v(c)}).")
        if c == 0:
            facts.append(f"empty({ex},{_n(b)}).")

    for (b1, _L1, _c1), (b2, _L2, _c2) in zip(runs, runs[1:]):
        facts.append(f"in_succ({ex},{_n(b1)},{_n(b2)}).")

    colored = [(b, L, c) for b, L, c in runs if c != 0]
    for (b1, _L1, _c1), (b2, _L2, _c2) in zip(colored, colored[1:]):
        facts.append(f"in_col_succ({ex},{_n(b1)},{_n(b2)}).")

    for i in range(0, len(colored) - 1, 2):
        b1 = colored[i][0]
        b2 = colored[i + 1][0]
        facts.append(f"in_pair({ex},{_n(b1)},{_n(b2)}).")

    sizes = sorted(x for x in observed if x >= 0)
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({_n(a)},{_n(b)}).")

    # Small arithmetic on bids and lengths only (not the pixel ruler).
    base = sorted(observed | {1, 2, 3})
    cap = max([w, *base], default=w)
    for i in range(max(base) if base else 0):
        facts.append(f"succ({_n(i)},{_n(i + 1)}).")
    for a in base:
        for b in base:
            c = a + b
            if c <= cap:
                facts.append(f"add({_n(a)},{_n(b)},{_n(c)}).")

    return facts, observed, w


def _exs_for_train(
    train: List[Tuple[int, List[int], List[int]]], novel: Set[int]
) -> List[str]:
    pos: List[str] = []
    neg: List[str] = []
    for ex, inp, out in train:
        in_runs = _runs(inp)
        out_runs = _runs(out)
        true: Set[Tuple[int, int, int]] = {(b, L, c) for b, L, c in out_runs}
        palette = {c for _b, _L, c in in_runs} | {c for _b, _L, c in out_runs} | novel
        len_cands = sorted({L for _b, L, _c in in_runs} | {L for _b, L, _c in out_runs})
        for b, L, c in out_runs:
            pos.append(f"pos(out_block({ex},{_n(b)},{_n(L)},{_v(c)})).")
            for v in sorted(palette):
                if v != c:
                    neg.append(f"neg(out_block({ex},{_n(b)},{_n(L)},{_v(v)})).")
            for L2 in len_cands:
                if L2 < 1 or L2 == L:
                    continue
                if (b, L2, c) in true:
                    continue
                neg.append(f"neg(out_block({ex},{_n(b)},{_n(L2)},{_v(c)})).")
        # Same-index identity killers: input run at B is not the gold out run.
        for b, L, c in in_runs:
            if (b, L, c) not in true:
                neg.append(f"neg(out_block({ex},{_n(b)},{_n(L)},{_v(c)})).")
    seen: Set[str] = set()
    out_lines: List[str] = []
    for line in pos + neg:
        if line in seen:
            continue
        seen.add(line)
        out_lines.append(line)
    return out_lines


def _bias(bk_text: str, novel: Set[int], consts: Set[int]) -> str:
    values = sorted(novel)
    preds = [
        ("in_block", 4, "('ex','num','num','value')"),
        ("empty", 2, "('ex','num')"),
        ("in_succ", 3, "('ex','num','num')"),
        ("in_col_succ", 3, "('ex','num','num')"),
        ("in_pair", 3, "('ex','num','num')"),
        ("succ", 2, "('num','num')"),
        ("add", 3, "('num','num','num')"),
        ("size_lt", 2, "('num','num')"),
    ]
    present = {n for n, _a, _t in preds if _pred_in_bk(bk_text, n)}
    parts = [
        "max_vars(10).",
        "max_body(6).",
        "max_clauses(3).",
        "enable_multi_clause.",
        "functional.",
        ":- not body_var(_,1).",
        ":- not body_var(_,2).",
        ":- not body_var(_,3).",
        "",
        "head_pred(out_block,4).",
    ]
    for n, a, _t in preds:
        if n in present:
            parts.append(f"body_pred({n},{a}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    for i in sorted(consts):
        parts.append(f"constant(n{i}, 'num').")
    for i in values:
        parts.append(f"constant(v{i}, 'value').")
    parts.append("")
    parts.append("type(out_block,('ex','num','num','value')).")
    for n, _a, t in preds:
        if n in present:
            parts.append(f"type({n},{t}).")
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(":- clause(C), not body_literal(C, in_block, 4, (0,_,_,_)).")
    bid_ok = ["body_literal(C, in_block, 4, (0,1,_,_))"]
    if "succ" in present:
        bid_ok += [
            "body_literal(C, succ, 2, (1,_))",
            "body_literal(C, succ, 2, (_,1))",
        ]
    if "add" in present:
        bid_ok += [
            "body_literal(C, add, 3, (1,_,_))",
            "body_literal(C, add, 3, (_,_,1))",
        ]
    if "in_succ" in present:
        bid_ok += [
            "body_literal(C, in_succ, 3, (0,1,_))",
            "body_literal(C, in_succ, 3, (0,_,1))",
        ]
    if "in_col_succ" in present:
        bid_ok += [
            "body_literal(C, in_col_succ, 3, (0,1,_))",
            "body_literal(C, in_col_succ, 3, (0,_,1))",
        ]
    parts.append(":- clause(C), " + ", ".join(f"not {a}" for a in bid_ok) + ".")
    if "succ" in present:
        parts.append(
            ":- clause(C), body_literal(C, succ, 2, V1), "
            "body_literal(C, succ, 2, V2), V1 != V2."
        )
    if "add" in present:
        parts.append(
            ":- clause(C), body_literal(C, add, 3, V1), "
            "body_literal(C, add, 3, V2), V1 != V2."
        )
    if "succ" in present and "add" in present:
        parts.append(
            ":- clause(C), body_literal(C, succ, 2, _), "
            "body_literal(C, add, 3, _)."
        )
    if "add" in present:
        parts.append(
            "bad_body(add, Vars):- vars(_, Vars), Vars = (A,B,R), "
            "A != 1, B != 1, R != 1, A != 2, B != 2, R != 2."
        )
    if "succ" in present:
        parts.append(
            "bad_body(succ, Vars):- vars(_, Vars), Vars = (A,R), "
            "A != 1, R != 1, A != 2, R != 2."
        )
    parts.append("")
    return "\n".join(parts) + "\n"


def encode_task(src: Path, out_dir: Path) -> Dict:
    obj = json.loads(src.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    train = []
    for i, pair in enumerate(obj["train"]):
        train.append((i, flatten(pair["input"]), flatten(pair["output"])))
    test_in = flatten(obj["test"][0]["input"])
    test_out = flatten(obj["test"][0]["output"])
    test_id = len(train)

    train_in_all: Set[int] = set()
    for _i, inp, _out in train:
        train_in_all |= {c for c in inp if c != 0}
    train_out_all: Set[int] = set()
    for _i, _inp, out in train:
        train_out_all |= {c for c in out if c != 0}
    novel = train_out_all - train_in_all

    bk_lines: List[str] = []
    test_bk: List[str] = []
    observed_all: Set[int] = set()
    max_bid = 0
    max_len = 1
    max_w = max(len(r) for _i, r, o in train for r in (r, o))
    max_w = max(max_w, len(test_in), len(test_out))
    for ex, inp, _out in train:
        facts, obs, _w = _bk_for_row(ex, inp)
        bk_lines.extend(facts)
        observed_all |= obs
        max_bid = max(max_bid, max((b for b, _L, _c in _runs(inp)), default=0))
        max_len = max(max_len, max((L for _b, L, _c in _runs(inp)), default=1))
    facts, obs, _w = _bk_for_row(test_id, test_in)
    test_bk.extend(facts)
    observed_all |= obs
    max_bid = max(max_bid, max((b for b, _L, _c in _runs(test_in)), default=0))
    max_len = max(max_len, max((L for _b, L, _c in _runs(test_in)), default=1))
    for _e, _inp, out in train:
        max_bid = max(max_bid, max((b for b, _L, _c in _runs(out)), default=0))
        max_len = max(max_len, max((L for _b, L, _c in _runs(out)), default=1))

    for i in sorted(novel):
        bk_lines.append(f"v{i}(v{i}).")
        test_bk.append(f"v{i}(v{i}).")
    consts = observed_all | {0, 1, 2, 3}
    for i in sorted(consts):
        bk_lines.append(f"n{i}(n{i}).")
        test_bk.append(f"n{i}(n{i}).")

    # Train output is checker-only: never a body pred, never in test_bk.
    checker: List[str] = [":- dynamic out_block/4."]
    for ex, _inp, out in train:
        for b, L, c in _runs(out):
            checker.append(f"need_block({ex},{_n(b)},{_n(L)},{_v(c)}).")
    checker.extend(
        [
            "dup_bid :- out_block(E,B,L1,C1), out_block(E,B,L2,C2), "
            "(L1 \\= L2 ; C1 \\= C2).",
            "extra_head :- out_block(E,B,L,C), \\+ need_block(E,B,L,C).",
            "missing_head :- need_block(E,B,L,C), \\+ out_block(E,B,L,C).",
            "non_functional(_Atom) :- dup_bid.",
            "non_functional(_Atom) :- extra_head.",
        ]
    )

    bk_lines = sorted(set(bk_lines))
    test_bk = sorted(set(test_bk))
    exs = _exs_for_train(train, novel)
    learnable = "\n".join(bk_lines)
    (out_dir / "bk.pl").write_text(learnable + "\n" + "\n".join(checker) + "\n")
    (out_dir / "test_bk.pl").write_text("\n".join(test_bk) + "\n")
    (out_dir / "exs.pl").write_text("\n".join(exs) + "\n")
    (out_dir / "bias.pl").write_text(_bias(learnable, novel, consts))
    meta = {
        "train": [{"id": e, "input": inp, "output": out} for e, inp, out in train],
        "test": {"id": test_id, "input": test_in, "output": test_out},
        "max_bid": max_bid,
        "max_len": max_len,
        "width": max_w,
    }
    (out_dir / "grids.json").write_text(json.dumps(meta))
    return meta


def _collect(
    ex_id: int, max_bid: int, max_len: int
) -> List[Tuple[int, int, int]]:
    from janus_swi import query_once

    blocks = []
    for b in range(0, max_bid + 1):
        for L in range(1, max_len + 1):
            for c in range(0, 10):
                atom = f"out_block({ex_id},{_n(b)},{_n(L)},{_v(c)})"
                try:
                    res = query_once(atom)
                except Exception:
                    continue
                if res.get("truth"):
                    blocks.append((b, L, c))
    return sorted(blocks)


def paint(
    program: str,
    bk_path: Path,
    examples: List[Tuple[int, int]],
    max_bid: int,
    max_len: int,
) -> Dict[int, List[int]]:
    """examples: (ex_id, width). Concatenate out_blocks in bid order."""
    from janus_swi import consult, query_once

    tmp = bk_path.parent / "_apply.pl"
    tmp.write_text(":- dynamic out_block/4.\n" + program)
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for ex_id, w in examples:
            row: List[int] = []
            seen_bid: Set[int] = set()
            for b, L, c in _collect(ex_id, max_bid, max_len):
                if b in seen_bid:
                    raise ValueError(f"dup bid {ex_id}:{b}")
                seen_bid.add(b)
                row.extend([c] * L)
            if len(row) != w:
                raise ValueError(f"width {ex_id} {len(row)}!={w}")
            out[ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out_block(_,_,_,_))")
        except Exception:
            pass


def run_one(cat: str, trial: int, timeout: int) -> Dict:
    src = DATASET / cat / f"{cat}_{trial}.json"
    work = OUT_ROOT / f"{cat}_{trial}"
    if work.exists():
        import shutil

        shutil.rmtree(work)
    meta = encode_task(src, work / "encode")
    ir = induce(
        work / "encode" / "exs.pl",
        work / "encode" / "bk.pl",
        work / "encode" / "bias.pl",
        timeout,
        work / "popper",
    )
    result = {
        "task": f"{cat}_{trial}",
        "status": ir.status,
        "elapsed_s": round(ir.elapsed_s, 2),
        "error": ir.error,
        "program": ir.program,
        "train_exact": False,
        "test_exact": False,
        "failure": None,
    }
    if not ir.program:
        result["failure"] = ir.status
        return result
    max_bid = int(meta["max_bid"])
    max_len = int(meta["max_len"])
    train_ex = [(t["id"], len(t["output"])) for t in meta["train"]]
    try:
        preds = paint(
            ir.program, work / "encode" / "bk.pl", train_ex, max_bid, max_len
        )
    except Exception as e:
        result["failure"] = f"decode:{e}"
        return result
    for t in meta["train"]:
        if preds.get(t["id"]) != t["output"]:
            result["failure"] = "paint_verify_failed"
            (work / "program.pl").write_text(ir.program)
            return result
    result["train_exact"] = True
    tw = len(meta["test"]["output"])
    try:
        tpred = paint(
            ir.program,
            work / "encode" / "test_bk.pl",
            [(meta["test"]["id"], tw)],
            max_bid,
            max_len,
        )[meta["test"]["id"]]
    except Exception as e:
        result["failure"] = f"test_decode:{e}"
        return result
    result["test_exact"] = tpred == meta["test"]["output"]
    if not result["test_exact"]:
        result["failure"] = "test_mismatch"
    (work / "program.pl").write_text(ir.program)
    return result


def main() -> None:
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    print(
        f"span-decom smoke timeout={timeout}s sequential tasks={len(TASKS)}",
        flush=True,
    )
    rows: List[Dict] = []
    for cat, trial in TASKS:
        r = run_one(cat, trial, timeout)
        rows.append(r)
        prog = (r.get("program") or "").replace("\n", " | ")[:200]
        print(
            f"--- {r['task']} ---\n"
            f"  {r['status']:10} train={r['train_exact']} test={r['test_exact']} "
            f"{r['elapsed_s']}s fail={r['failure']}\n  {prog}",
            flush=True,
        )
    summary = {
        "timeout": timeout,
        "jobs": 1,
        "n": len(rows),
        "train_ok": sum(1 for r in rows if r["train_exact"]),
        "test_ok": sum(1 for r in rows if r["test_exact"]),
        "rows": [
            {k: v for k, v in r.items() if k != "program"} | {"program": r.get("program")}
            for r in rows
        ],
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"\nDONE train_exact {summary['train_ok']}/{summary['n']} "
        f"test_exact {summary['test_ok']}/{summary['n']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
