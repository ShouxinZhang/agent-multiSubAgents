#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/apps/gomoku_codex_cli"
VENV_DIR="$APP_DIR/.venv"
CODEX_BIN_PATH="${CODEX_BIN:-}"

if [ ! -d "$APP_DIR" ]; then
  echo "[ERROR] App directory not found: $APP_DIR"
  exit 1
fi

if command -v pgrep >/dev/null 2>&1; then
  PIDS="$(pgrep -f "apps/gomoku_codex_cli/main.py" || true)"
  if [ -n "$PIDS" ]; then
    echo "[INFO] Stopping existing Gomoku process: $PIDS"
    kill $PIDS || true
    sleep 1
  fi
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[INFO] Creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! python -c "import mcp" >/dev/null 2>&1; then
  echo "[INFO] Installing Python dependencies"
  pip install -r "$APP_DIR/requirements.txt"
fi

if [ -z "$CODEX_BIN_PATH" ]; then
  if command -v codex >/dev/null 2>&1; then
    CODEX_BIN_PATH="$(command -v codex)"
  else
    for candidate in \
      "$HOME"/.vscode-insiders/extensions/openai.chatgpt-*/bin/linux-x86_64/codex \
      "$HOME"/.vscode/extensions/openai.chatgpt-*/bin/linux-x86_64/codex; do
      if [ -x "$candidate" ]; then
        CODEX_BIN_PATH="$candidate"
        break
      fi
    done
  fi
fi

if [ -z "$CODEX_BIN_PATH" ] || [ ! -x "$CODEX_BIN_PATH" ]; then
  echo "[WARN] 'codex' command not found. Install Codex CLI and login before starting AI match."
  echo "[WARN] You can also pass explicit path: CODEX_BIN=/abs/path/to/codex bash restart.sh"
else
  echo "[INFO] Using codex binary: $CODEX_BIN_PATH"
fi

echo "[INFO] Starting Dual Codex CLI Gomoku..."
cd "$APP_DIR"
if [ -n "$CODEX_BIN_PATH" ] && [ -x "$CODEX_BIN_PATH" ]; then
  exec python main.py --codex-bin "$CODEX_BIN_PATH" "$@"
else
  exec python main.py "$@"
fi
