"""Throwaway smoke: Decom-analogue span encoding (no Bid/Rank).

Both input and output use (Start, Len, Color) on the shared pixel ruler:
  block(E, Start, Len, Color)
  out_block(E, Start, Len, Color)

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

from solver.grid import flatten, segment_all_runs, segment_blocks
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


def _bk_for_row(ex: int, row: Sequence[int]) -> Tuple[List[str], Set[int], int]:
    """Lean object BK on one shared numeric ruler (Decom-style succ/add)."""
    facts: List[str] = []
    runs = segment_all_runs(row)
    w = len(row)
    colored = [(s, e, c) for s, e, c in runs if c != 0]
    observed: Set[int] = {0, 1}
    starts: Set[int] = set()

    for s, e, c in colored:
        L = e - s + 1
        observed.add(L)
        starts.add(s)
        facts.append(f"block({ex},{_n(s)},{_n(L)},{_v(c)}).")

    for (s1, e1, _c1), (s2, e2, _c2) in zip(colored, colored[1:]):
        L1 = e1 - s1 + 1
        L2 = e2 - s2 + 1
        g = s2 - e1 - 1
        observed.add(g)
        facts.append(f"obj_succ({ex},{_n(s1)},{_n(s2)}).")
        facts.append(f"gap({ex},{_n(s1)},{_n(s2)},{_n(g)}).")
        total = L1 + g + L2
        if total <= w:
            observed.add(total)

    for i in range(0, len(colored) - 1, 2):
        s1 = colored[i][0]
        s2 = colored[i + 1][0]
        facts.append(f"obj_pair({ex},{_n(s1)},{_n(s2)}).")

    if colored:
        max_L = max(e - s + 1 for s, e, _c in colored)
        for s, e, _c in colored:
            L = e - s + 1
            if L == max_L:
                facts.append(f"largest({ex},{_n(s)}).")
            else:
                facts.append(f"non_largest({ex},{_n(s)}).")

    for L in list(observed):
        if 2 <= L <= w:
            observed.add(L - 1)

    sizes = sorted(x for x in observed if x >= 0)
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({_n(a)},{_n(b)}).")

    # Decom-style functional arithmetic on the shared ruler: a succ chain
    # plus add over observed quantities (block starts, observed sizes, small
    # constants). Single pass, no closure, no position-by-offset product.
    base = sorted(observed | starts | {1, 2, 3})
    for i in range(w):
        facts.append(f"succ({_n(i)},{_n(i + 1)}).")
    for a in base:
        for b in base:
            c = a + b
            if c <= w:
                facts.append(f"add({_n(a)},{_n(b)},{_n(c)}).")

    return facts, observed, w


def _exs_for_train(
    train: List[Tuple[int, List[int], List[int]]], novel: Set[int]
) -> List[str]:
    pos: List[str] = []
    neg: List[str] = []
    for ex, inp, out in train:
        w = len(out)
        palette_ex = {c for c in inp if c != 0} | novel
        in_spans = [(s, e - s + 1, c) for s, e, c in segment_blocks(inp)]
        true: Set[Tuple[int, int, int]] = set()
        colors: Set[int] = set()
        observed = {0, 1}
        for s, e, c in segment_blocks(inp):
            observed.add(e - s + 1)
        for s, e, c in segment_blocks(out):
            L = e - s + 1
            true.add((s, L, c))
            colors.add(c)
            observed.add(L)
            observed.add(s)
            pos.append(f"pos(out_block({ex},{_n(s)},{_n(L)},{_v(c)})).")
        if not true:
            continue
        len_cands = sorted(set(observed) | set(range(1, min(w, 12) + 1)))
        start_cands = sorted(set(range(0, w)) | {s for s, _L, _c in in_spans})
        for s, L, c in true:
            for v in sorted(palette_ex):
                if v != c:
                    neg.append(f"neg(out_block({ex},{_n(s)},{_n(L)},{_v(v)})).")
            for L2 in len_cands:
                if L2 < 1 or L2 == L:
                    continue
                if (s, L2, c) in true:
                    continue
                neg.append(f"neg(out_block({ex},{_n(s)},{_n(L2)},{_v(c)})).")
            for s2 in start_cands:
                if s2 == s or not (0 <= s2 < w):
                    continue
                if (s2, L, c) in true:
                    continue
                neg.append(f"neg(out_block({ex},{_n(s2)},{_n(L)},{_v(c)})).")
        # Identity/prefix killers at each input span start.
        for s, Lin, c in in_spans:
            for L0 in range(1, Lin + 1):
                if (s, L0, c) not in true:
                    neg.append(f"neg(out_block({ex},{_n(s)},{_n(L0)},{_v(c)})).")
    seen: Set[str] = set()
    out_lines: List[str] = []
    for line in pos + neg:
        if line in seen:
            continue
        seen.add(line)
        out_lines.append(line)
    return out_lines


def _bias(bk_text: str, exs_text: str, novel: Set[int], consts: Set[int]) -> str:
    values = sorted(novel)
    preds = [
        ("block", 4, "('ex','num','num','value')"),
        ("obj_succ", 3, "('ex','num','num')"),
        ("obj_pair", 3, "('ex','num','num')"),
        ("gap", 4, "('ex','num','num','num')"),
        ("largest", 2, "('ex','num')"),
        ("non_largest", 2, "('ex','num')"),
        ("succ", 2, "('num','num')"),
        ("add", 3, "('num','num','num')"),
        ("size_lt", 2, "('num','num')"),
    ]
    present = {n for n, _a, _t in preds if f"{n}(" in bk_text}
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
    # Require some input block in the clause; do NOT pin head Start (that kills shifts).
    parts.append(":- clause(C), not body_literal(C, block, 4, (0,_,_,_)).")
    # Cut 1: head Start is copied from a block or constructed (succ/add/obj_succ).
    start_ok = ["body_literal(C, block, 4, (0,1,_,_))"]
    if "succ" in present:
        start_ok += [
            "body_literal(C, succ, 2, (1,_))",
            "body_literal(C, succ, 2, (_,1))",
        ]
    if "add" in present:
        start_ok += [
            "body_literal(C, add, 3, (1,_,_))",
            "body_literal(C, add, 3, (_,_,1))",
        ]
    if "obj_succ" in present:
        start_ok += [
            "body_literal(C, obj_succ, 3, (0,1,_))",
            "body_literal(C, obj_succ, 3, (0,_,1))",
        ]
    parts.append(":- clause(C), " + ", ".join(f"not {a}" for a in start_ok) + ".")
    # Cut 2: at most one succ/add literal per clause.
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
    # Tightened 5: succ/add must mention head Start (var 1) or Len (var 2).
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

    # Palette policy: only novel train-output colors (train-out minus all
    # train-in) become constants/unaries. Every other color reaches a clause
    # only through that example's own block/4 facts, so the per-example color
    # search space is exactly that example's own colors (+ novel).
    # Per-example wrong-color negs use input colors + novel.
    # Test output is never read.
    train_in_all: Set[int] = set()
    for _i, inp, _out in train:
        train_in_all |= {c for c in inp if c != 0}
    train_out_all: Set[int] = set()
    for _i, _inp, out in train:
        train_out_all |= {c for c in out if c != 0}
    novel = train_out_all - train_in_all

    bk_lines: List[str] = []
    test_bk: List[str] = []
    max_w = max(len(r) for _i, r, o in train for r in (r, o))
    max_w = max(max_w, len(test_in), len(test_out))
    observed_all: Set[int] = set()
    for ex, inp, out in train:
        facts, obs, _w = _bk_for_row(ex, inp)
        bk_lines.extend(facts)
        observed_all |= obs
    facts, obs, _w = _bk_for_row(test_id, test_in)
    test_bk.extend(facts)
    observed_all |= obs

    for i in sorted(novel):
        bk_lines.append(f"v{i}(v{i}).")
        test_bk.append(f"v{i}(v{i}).")
    consts = observed_all | {0, 1, 2, 3}
    for i in sorted(consts):
        bk_lines.append(f"n{i}(n{i}).")
        test_bk.append(f"n{i}(n{i}).")

    # Train output is checker-only: never a body pred, never in test_bk.
    # functional. asks non_functional/1, which rejects a complete hypothesis
    # unless each gold pixel belongs to at most one out_block (overlap) and
    # colored pixels are covered with the gold color (uncovered/extra/wrong).
    checker: List[str] = [":- dynamic out_block/4."]
    checker.extend(f"ord({_n(i)},{i})." for i in range(max_w + 1))
    for ex, _inp, out in train:
        for p, c in enumerate(out):
            checker.append(f"gold({ex},{_n(p)},{_v(c)}).")
    for ex, _inp, out in train:
        for s, e, c in segment_blocks(out):
            checker.append(
                f"need_block({ex},{_n(s)},{_n(e - s + 1)},{_v(c)})."
            )
    checker.extend(
        [
            "cover_start(E,P,S) :- out_block(E,S,L,_C), ord(S,Si), ord(L,Li), "
            "ord(P,Pi), Pi >= Si, Pi < Si+Li.",
            "overlap(E,P) :- cover_start(E,P,S1), cover_start(E,P,S2), S1 \\= S2.",
            "uncovered(E,P) :- gold(E,P,C), C \\= v0, \\+ cover_start(E,P,_).",
            "extra(E,P) :- cover_start(E,P,_), gold(E,P,v0).",
            "wrong(E,P) :- cover_start(E,P,S), out_block(E,S,_L,C), gold(E,P,G), G \\= C.",
            "stray(E,P) :- cover_start(E,P,_), \\+ gold(E,P,_).",
            "block_oob :- out_block(E,S,L,_), ord(S,Si), ord(L,Li), "
            "End is Si+Li-1, \\+ (ord(P,End), gold(E,P,_)).",
            "missing_head :- need_block(E,S,L,C), \\+ out_block(E,S,L,C).",
            "non_functional(_Atom) :- \\+ missing_head, overlap(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, uncovered(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, extra(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, wrong(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, stray(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, block_oob.",
        ]
    )

    bk_lines = sorted(set(bk_lines))
    test_bk = sorted(set(test_bk))
    exs = _exs_for_train(train, novel)
    (out_dir / "bk.pl").write_text("\n".join(bk_lines) + "\n" + "\n".join(checker) + "\n")
    (out_dir / "test_bk.pl").write_text("\n".join(test_bk) + "\n")
    (out_dir / "exs.pl").write_text("\n".join(exs) + "\n")
    (out_dir / "bias.pl").write_text(
        _bias("\n".join(bk_lines), "\n".join(exs), novel, consts)
    )
    meta = {
        "train": [{"id": e, "input": inp, "output": out} for e, inp, out in train],
        "test": {"id": test_id, "input": test_in, "output": test_out},
    }
    (out_dir / "grids.json").write_text(json.dumps(meta))
    return meta


def _collect(ex_id: int, width: int) -> List[Tuple[int, int, int]]:
    from janus_swi import query_once

    blocks = []
    for s in range(0, width):
        for L in range(1, width - s + 1):
            for c in range(1, 10):
                atom = f"out_block({ex_id},{_n(s)},{_n(L)},{_v(c)})"
                try:
                    res = query_once(atom)
                except Exception:
                    continue
                if res.get("truth"):
                    blocks.append((s, L, c))
    return blocks


def paint(program: str, bk_path: Path, examples: List[Tuple[int, int]]) -> Dict[int, List[int]]:
    """examples: (ex_id, width)."""
    from janus_swi import consult, query_once

    tmp = bk_path.parent / "_apply.pl"
    tmp.write_text(":- dynamic out_block/4.\n" + program)
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for ex_id, w in examples:
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect(ex_id, w):
                if s < 0 or s + L > w:
                    raise ValueError(f"OOB {ex_id} {s}+{L}")
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(f"overlap {ex_id}:{p}")
                    occupied[p] = c
                    row[p] = c
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
    train_ex = [(t["id"], len(t["output"])) for t in meta["train"]]
    try:
        preds = paint(ir.program, work / "encode" / "bk.pl", train_ex)
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
