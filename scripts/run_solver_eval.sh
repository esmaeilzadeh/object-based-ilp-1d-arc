#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

MODE="${1:-dual}"
TIMEOUT="${2:-60}"
TRIALS="${3:-0,1,2}"
LIMIT="${LIMIT:-0}"

ARGS=(--mode "$MODE" --timeout "$TIMEOUT" --trials "$TRIALS")
if [[ "$LIMIT" != "0" ]]; then
  ARGS+=(--limit "$LIMIT")
fi

python -m solver.harness "${ARGS[@]}"
