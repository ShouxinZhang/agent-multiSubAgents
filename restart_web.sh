#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_SCRIPT="$ROOT_DIR/apps/gomoku_codex_cli/web_api.py"
WEB_DIR="$ROOT_DIR/apps/gomoku_web"
GOMOKU_REQ="$ROOT_DIR/apps/gomoku_codex_cli/requirements.txt"
API_PORT="${API_PORT:-8787}"
WEB_PORT="${WEB_PORT:-5173}"
CODEX_BIN_PATH="${CODEX_BIN:-}"
PYTHON_BIN_PATH="${PYTHON_BIN:-python3}"
VENV_DIR="$ROOT_DIR/.venv/gomoku_web"

python_has_mcp() {
  local py_bin="$1"
  "$py_bin" - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("mcp") else 1)
PY
}

if [ ! -f "$API_SCRIPT" ]; then
  echo "[ERROR] API script not found: $API_SCRIPT"
  exit 1
fi

if [ ! -d "$WEB_DIR" ]; then
  echo "[ERROR] Web app not found: $WEB_DIR"
  exit 1
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

if ! command -v "$PYTHON_BIN_PATH" >/dev/null 2>&1; then
  echo "[ERROR] Python not found in PATH: $PYTHON_BIN_PATH"
  exit 1
fi

if ! python_has_mcp "$PYTHON_BIN_PATH"; then
  echo "[WARN] '$PYTHON_BIN_PATH' missing python package 'mcp'; preparing isolated venv"
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    python3 -m venv "$VENV_DIR"
  fi
  if ! python_has_mcp "$VENV_DIR/bin/python"; then
    "$VENV_DIR/bin/python" -m pip install --upgrade pip >/tmp/gomoku_web_pip.log 2>&1
    "$VENV_DIR/bin/python" -m pip install -r "$GOMOKU_REQ" >>/tmp/gomoku_web_pip.log 2>&1
  fi
  PYTHON_BIN_PATH="$VENV_DIR/bin/python"
fi

if command -v pgrep >/dev/null 2>&1; then
  API_PIDS="$(pgrep -f "apps/gomoku_codex_cli/web_api.py.*--port $API_PORT" || true)"
  if [ -n "$API_PIDS" ]; then
    echo "[INFO] Stopping existing web API process: $API_PIDS"
    kill $API_PIDS || true
    sleep 1
  fi
fi

echo "[INFO] Starting web API on 127.0.0.1:$API_PORT"
echo "[INFO] Using python runtime: $PYTHON_BIN_PATH"
if [ -n "$CODEX_BIN_PATH" ] && [ -x "$CODEX_BIN_PATH" ]; then
  echo "[INFO] Using codex binary: $CODEX_BIN_PATH"
  "$PYTHON_BIN_PATH" "$API_SCRIPT" --host 127.0.0.1 --port "$API_PORT" --codex-bin "$CODEX_BIN_PATH" --python-bin "$PYTHON_BIN_PATH" >/tmp/gomoku_web_api.log 2>&1 &
else
  echo "[WARN] codex binary not found; web Start action may fail"
  "$PYTHON_BIN_PATH" "$API_SCRIPT" --host 127.0.0.1 --port "$API_PORT" --python-bin "$PYTHON_BIN_PATH" >/tmp/gomoku_web_api.log 2>&1 &
fi
API_PID=$!
echo "[INFO] web API pid=$API_PID (log: /tmp/gomoku_web_api.log)"

cleanup() {
  if kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

cd "$WEB_DIR"
if [ ! -d "node_modules" ]; then
  echo "[INFO] Installing web dependencies"
  npm install
fi

echo "[INFO] Starting Vite dev server on 127.0.0.1:$WEB_PORT"
npm run dev -- --host 127.0.0.1 --port "$WEB_PORT"
