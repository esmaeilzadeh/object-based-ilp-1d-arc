#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .venv/bin/activate ]] && source .venv/bin/activate

TIMEOUT="${TIMEOUT:-180}"
FIX="$ROOT/tests/fixtures"
OUT="$ROOT/work/block_hard"
mkdir -p "$OUT"

pass=0
fail=0
for name in fill_gap_with_shorter move_left_block_past_pivot hollow_largest_keep_rest; do
  json="$FIX/${name}.json"
  echo "======== $name (timeout=$TIMEOUT) ========"
  python -m solver.cli "$json" --timeout "$TIMEOUT" \
    --work-dir "$OUT/$name" --out "$OUT/$name/pred.json"
  if python - "$OUT/$name/pred.json" "$json" <<'PY'
import json, sys
from pathlib import Path
from solver.grid import flatten
pred = json.loads(Path(sys.argv[1]).read_text())
gold = flatten(json.loads(Path(sys.argv[2]).read_text())["test"][0]["output"])
ok = list(pred["predicted_grid"]) == list(gold)
print(f"level={pred['level']} verified={pred['verified_train']} match={ok}")
print("prog:", pred["program"][:240].replace("\n", " | "))
sys.exit(0 if ok else 1)
PY
  then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
  fi
  echo
done

echo "RESULT: pass=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
