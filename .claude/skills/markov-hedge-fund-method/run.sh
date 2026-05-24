#!/usr/bin/env bash
# Bootstrap venv on first run, then invoke markov.py with the given ticker.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
PY_BIN="$VENV/bin/python"

if [ "$#" -ne 1 ]; then
    echo "Usage: $(basename "$0") <TICKER>" >&2
    exit 2
fi

if [ ! -x "$PY_BIN" ]; then
    echo "Setting up venv at $VENV (first run)..." >&2
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip >&2
    "$VENV/bin/pip" install --quiet yfinance pandas numpy >&2
fi

exec "$PY_BIN" "$DIR/markov.py" "$1"
