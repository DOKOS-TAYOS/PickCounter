#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
"$ROOT/.venv/bin/python" "$ROOT/src/pick_counter.py"
