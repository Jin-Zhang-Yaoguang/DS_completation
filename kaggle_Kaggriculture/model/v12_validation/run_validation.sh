#!/usr/bin/env bash
set -euo pipefail

# This file is an explicit command contract.  Merely building assets never
# starts an environment run.  Invoke one stage at a time after reviewing the
# frozen hashes and prior-stage gate.

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
WORKERS="${WORKERS:-12}"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
FROZEN="$HERE/frozen_v5"
RUNS="$HERE/runs_v5"

preflight() {
  "$PYTHON" - "$FROZEN/validation_config.json" <<'PY'
import json, sys
from pathlib import Path
from kaggle_Kaggriculture.model.v12_validation.protocol import preflight
print(json.dumps(preflight(Path(sys.argv[1])), ensure_ascii=False, sort_keys=True))
PY
}

case "${1:-}" in
  build)
    "$PYTHON" "$HERE/build_validation_assets.py"
    ;;
  preflight)
    preflight
    ;;
  formal)
    if [[ "${2:-}" != "--execute-formal" || "$#" -ne 2 ]]; then
      echo "formal is locked; after independent red-team review use: $0 formal --execute-formal" >&2
      exit 64
    fi
    preflight
    mkdir -p "$RUNS/formal"
    "$PYTHON" "$HERE/targeted_evaluate.py" \
      --config "$FROZEN/validation_config.json" \
      --execute-formal \
      --workers "$WORKERS" --resume \
      --jsonl "$RUNS/formal/games.jsonl" \
      --output "$RUNS/formal/collection_summary.json"
    ;;
  audit)
    preflight
    "$PYTHON" "$HERE/audit_results.py" \
      --config "$FROZEN/validation_config.json" \
      --jsonl "$RUNS/formal/games.jsonl" \
      --output "$RUNS/formal/audit.json"
    ;;
  *)
    echo "usage: $0 {build|preflight|formal --execute-formal|audit}" >&2
    exit 64
    ;;
esac
