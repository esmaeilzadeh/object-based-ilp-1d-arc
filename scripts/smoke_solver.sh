#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt
pip install -q -e ./popper

JSON="${1:-raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json}"
# Denoising needs ~60s of pixel ILP; ladder spends a little on block first.
TIMEOUT="${TIMEOUT:-90}"

python -m solver.cli "$JSON" --timeout "$TIMEOUT" --out pred.json --work-dir work/smoke
echo "Wrote pred.json"
