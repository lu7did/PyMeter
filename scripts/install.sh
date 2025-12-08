#!/usr/bin/env bash
set -e
PYTHON=${PYTHON:-python3}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON"
  exit 1
fi

echo "Creating virtualenv .venv..."
$PYTHON -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install pyqt5

echo "Done. To run the app: source .venv/bin/activate && scripts/PyMeter"
