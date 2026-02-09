from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from gomoku.gui import BattleCoordinator


class StateApiHandler(BaseHTTPRequestHandler):
    runtime_dir: Path
    controller: "RuntimeController"

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return {}
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._send_json(self.controller.health_payload())
            return

        if parsed.path == "/api/state":
            self._send_json(self.controller.snapshot())
            return

        if parsed.path == "/api/stream":
            self._handle_stream()
            return

        self._send_json({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        payload = self._read_json_body()

        if parsed.path == "/api/match/start":
            keep_memory = bool(payload.get("keep_memory", True))
            result = self.controller.start(keep_memory=keep_memory)
            self._send_json(result, status=HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/match/stop":
            self.controller.stop(reason="web stop")
            self._send_json(self.controller.snapshot())
            return

        if parsed.path == "/api/match/reset":
            self.controller.reset_board()
            self._send_json(self.controller.snapshot())
            return

        if parsed.path == "/api/match/clear-memory":
            self.controller.clear_memory()
            self._send_json(self.controller.snapshot())
            return

        self._send_json({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_version = -1
        heartbeat_at = time.time()
        try:
            while True:
                payload, version = self.controller.snapshot_with_version()
                if version != last_version:
                    body = json.dumps(payload, ensure_ascii=True)
                    self.wfile.write(f"event: state\ndata: {body}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    last_version = version
                    heartbeat_at = time.time()
                elif time.time() - heartbeat_at >= 10:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    heartbeat_at = time.time()
                time.sleep(0.4)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            return


class RuntimeController:
    def __init__(
        self,
        *,
        workspace: Path,
        runtime_dir: Path,
        board_size: int,
        model: str,
        codex_bin: str,
        python_bin: str,
        timeout_sec: int,
    ):
        self.workspace = Path(workspace)
        self.runtime_dir = Path(runtime_dir)
        self.ui_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self.coordinator = BattleCoordinator(
            workspace=self.workspace,
            runtime_dir=self.runtime_dir,
            board_size=board_size,
            model=model,
            codex_bin=codex_bin,
            python_bin=python_bin,
            timeout_sec=timeout_sec,
            ui_queue=self.ui_queue,
        )
        self.model = model
        self.board_size = board_size
        self.codex_bin = codex_bin
        self.python_bin = python_bin
        self.timeout_sec = timeout_sec

        self._lock = threading.Lock()
        self._runtime_status = "idle"
        self._version = 1
        self._stop_event = threading.Event()
        self._live_logs: dict[str, list[dict[str, Any]]] = {"B": [], "W": []}
        self._mcp_ready = False
        self._mcp_error = ""
        self._refresh_mcp_runtime_status()
        self._queue_thread = threading.Thread(target=self._drain_ui_queue, daemon=True)
        self._queue_thread.start()
        self.coordinator.emit_state()

    def _drain_ui_queue(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self.ui_queue.get(timeout=0.4)
            except queue.Empty:
                continue
            with self._lock:
                if event.get("type") == "status":
                    self._runtime_status = str(event.get("text", ""))
                elif event.get("type") == "log":
                    player = str(event.get("player", "")).upper()
                    if player in ("B", "W"):
                        bucket = self._live_logs[player]
                        bucket.append(
                            {
                                "player": player,
                                "kind": str(event.get("kind", "log")),
                                "text": str(event.get("text", "")),
                                "seq": None,
                                "turn_id": None,
                            }
                        )
                        if len(bucket) > 240:
                            del bucket[: len(bucket) - 240]
                self._version += 1

    def _is_match_running(self) -> bool:
        return (not self.coordinator.stop_event.is_set()) and bool(self.coordinator.workers)

    def _probe_mcp_runtime(self) -> tuple[bool, str]:
        app_dir = self.workspace / "apps" / "gomoku_codex_cli"
        cmd = [
            self.python_bin,
            "-c",
            "import mcp, gomoku.mcp_server; print('ok')",
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                check=False,
            )
        except FileNotFoundError:
            return False, f"python binary not found: {self.python_bin}"
        except subprocess.TimeoutExpired:
            return False, "python runtime probe timed out"
        except Exception as error:  # pragma: no cover - defensive
            return False, f"python runtime probe failed: {error}"

        if proc.returncode == 0:
            return True, ""
        details = (proc.stderr or proc.stdout or f"exit={proc.returncode}").strip()
        if len(details) > 240:
            details = details[:237] + "..."
        return False, details

    def _refresh_mcp_runtime_status(self) -> tuple[bool, str]:
        ready, error = self._probe_mcp_runtime()
        with self._lock:
            self._mcp_ready = ready
            self._mcp_error = error
            self._version += 1
        return ready, error

    def _read_json_file(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _read_events(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                events.append(item)
        return events

    def snapshot(self) -> dict[str, Any]:
        state_path = self.runtime_dir / "state.json"
        memory_path = self.runtime_dir / "memory.json"
        events_path = self.runtime_dir / "turn_events.jsonl"
        with self._lock:
            runtime_status = self._runtime_status
            version = self._version
            live_logs = {
                "B": list(self._live_logs["B"]),
                "W": list(self._live_logs["W"]),
            }
            mcp_ready = self._mcp_ready
            mcp_error = self._mcp_error
        match_running = self._is_match_running()
        return {
            "ok": True,
            "state": self._read_json_file(state_path, {}),
            "memory": self._read_json_file(memory_path, {"B": [], "W": []}),
            "events": self._read_events(events_path),
            "live_logs": live_logs,
            "runtime_status": runtime_status,
            "match_running": match_running,
            "version": version,
            "model": self.model,
            "board_size": self.board_size,
            "codex_available": self.coordinator.codex_available(),
            "mcp_ready": mcp_ready,
            "mcp_error": mcp_error,
            "python_bin": self.python_bin,
        }

    def snapshot_with_version(self) -> tuple[dict[str, Any], int]:
        payload = self.snapshot()
        version = int(payload.get("version", 0))
        return payload, version

    def health_payload(self) -> dict[str, Any]:
        with self._lock:
            runtime_status = self._runtime_status
            mcp_ready = self._mcp_ready
            mcp_error = self._mcp_error
        return {
            "ok": True,
            "runtime_dir": str(self.runtime_dir),
            "workspace": str(self.workspace),
            "runtime_status": runtime_status,
            "match_running": self._is_match_running(),
            "model": self.model,
            "board_size": self.board_size,
            "codex_available": self.coordinator.codex_available(),
            "mcp_ready": mcp_ready,
            "mcp_error": mcp_error,
            "python_bin": self.python_bin,
        }

    def _bump_version(self) -> None:
        with self._lock:
            self._version += 1

    def start(self, *, keep_memory: bool) -> dict[str, Any]:
        if not self.coordinator.codex_available():
            return {"ok": False, "error": f"Cannot find '{self.codex_bin}' in PATH", **self.snapshot()}
        mcp_ready, mcp_error = self._refresh_mcp_runtime_status()
        if not mcp_ready:
            return {
                "ok": False,
                "error": f"MCP runtime unavailable for '{self.python_bin}': {mcp_error}",
                **self.snapshot(),
            }
        if self._is_match_running():
            payload = self.snapshot()
            payload["message"] = "match already running"
            return payload
        with self._lock:
            self._live_logs = {"B": [], "W": []}
        self.coordinator.start(keep_memory=keep_memory)
        self._bump_version()
        return self.snapshot()

    def stop(self, *, reason: str) -> None:
        self.coordinator.stop(reason=reason)
        self._bump_version()

    def reset_board(self) -> None:
        with self._lock:
            self._live_logs = {"B": [], "W": []}
        self.coordinator.reset_board()
        self._bump_version()

    def clear_memory(self) -> None:
        self.coordinator.clear_memory()
        self._bump_version()

    def close(self) -> None:
        self._stop_event.set()
        self.coordinator.stop(reason="api shutdown")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gomoku runtime state API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--runtime-dir", default="apps/gomoku_codex_cli/runtime")
    parser.add_argument("--board-size", type=int, default=15)
    parser.add_argument("--model", default="gpt-5.3-codex")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--turn-timeout", type=int, default=180)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = Path(__file__).resolve().parents[2]
    runtime_dir = Path(args.runtime_dir).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    handler = StateApiHandler
    handler.runtime_dir = runtime_dir
    handler.controller = RuntimeController(
        workspace=workspace,
        runtime_dir=runtime_dir,
        board_size=args.board_size,
        model=args.model,
        codex_bin=args.codex_bin,
        python_bin=args.python_bin,
        timeout_sec=args.turn_timeout,
    )

    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"[gomoku-web-api] listening on http://{args.host}:{args.port}, runtime={runtime_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        handler.controller.close()
        server.server_close()


if __name__ == "__main__":
    main()
