"""CLI: python -m solver.cli path/to.json --timeout 60 --out pred.json"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from solver.pipeline import solve


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Object-based ILP 1D-ARC solver")
    p.add_argument("json_path", type=Path)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--work-dir", type=Path, default=None)
    args = p.parse_args(argv)

    result = solve(
        args.json_path,
        timeout=args.timeout,
        work_dir=args.work_dir,
    )
    payload = result.to_dict()
    text = json.dumps(payload, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)


if __name__ == "__main__":
    main()
