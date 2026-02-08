#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$SCRIPT_DIR/.run"
PID_FILE="$RUN_DIR/server.pid"
LOG_FILE="$RUN_DIR/server.log"
PORT="${PORT:-8787}"
READY_TIMEOUT_SEC="${READY_TIMEOUT_SEC:-15}"

mkdir -p "$RUN_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing server (pid=$OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

# Clean up stale process occupying the target port.
if command -v lsof >/dev/null 2>&1; then
  PORT_PID="$(lsof -ti tcp:$PORT || true)"
  if [ -n "${PORT_PID:-}" ]; then
    echo "Releasing port $PORT (pid=$PORT_PID)..."
    kill "$PORT_PID" 2>/dev/null || true
    sleep 1
  fi
fi

echo "Building React frontend..."
(
  cd "$SCRIPT_DIR"
  npm run build:frontend >/dev/null
)

echo "Starting server on port $PORT..."
(
  cd "$SCRIPT_DIR"
  nohup env PORT="$PORT" node server.mjs >"$LOG_FILE" 2>&1 &
  echo "$!" >"$PID_FILE"
)

PID="$(cat "$PID_FILE")"

# Wait for server readiness to avoid "started but immediately disconnected" confusion.
for _ in $(seq 1 "$READY_TIMEOUT_SEC"); do
  if curl -sf "http://localhost:$PORT/api/config" >/dev/null 2>&1; then
    echo "Server restarted."
    echo "URL: http://localhost:$PORT"
    echo "PID: $PID"
    echo "LOG: $LOG_FILE"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Server process exited unexpectedly. Recent log:"
    tail -n 60 "$LOG_FILE" || true
    exit 1
  fi
  sleep 1
done

echo "Server did not become ready within ${READY_TIMEOUT_SEC}s. Recent log:"
tail -n 60 "$LOG_FILE" || true
exit 1

