#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEMO_DIR="$PROJECT_ROOT/demos/gomoku-10x10-kernel"
DEMO_RESTART="$DEMO_DIR/restart.sh"

if [ ! -x "$DEMO_RESTART" ]; then
  echo "Error: $DEMO_RESTART not found or not executable." >&2
  echo "Tip: run chmod +x demos/gomoku-10x10-kernel/restart.sh" >&2
  exit 1
fi

echo "Restarting Gomoku GUI via $DEMO_RESTART ..."
exec bash "$DEMO_RESTART" "$@"

