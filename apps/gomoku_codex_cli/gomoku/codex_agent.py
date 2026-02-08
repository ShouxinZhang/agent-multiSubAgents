from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any


LogCallback = Callable[[str, str, str], None]


@dataclass
class AgentTurnResult:
    ok: bool
    return_code: int
    timed_out: bool
    summary: str


class CodexAgent:
    def __init__(
        self,
        *,
        player: str,
        model: str,
        codex_bin: str,
        python_bin: str,
        workspace: Path,
        mcp_server_script: Path,
        state_path: Path,
        memory_path: Path,
        board_size: int,
        timeout_sec: int,
        log_callback: LogCallback,
    ):
        self.player = player.upper()
        self.model = model
        self.codex_bin = codex_bin
        self.python_bin = python_bin
        self.workspace = Path(workspace)
        self.mcp_server_script = Path(mcp_server_script)
        self.app_dir = self.mcp_server_script.parent.parent
        self.state_path = Path(state_path)
        self.memory_path = Path(memory_path)
        self.board_size = board_size
        self.timeout_sec = timeout_sec
        self.log = log_callback

    def _prompt(self) -> str:
        return (
            f"You are Gomoku player {self.player} on a {self.board_size}x{self.board_size} board. "
            "Coordinates are 0-indexed. You MUST use MCP tools to play.\n"
            "Required process for this turn:\n"
            "1) Call get_board_state and inspect current_player/winner.\n"
            "2) If game is finished or it's not your turn, explain briefly and stop.\n"
            "3) Call get_memory(player=<your token>) to recall strategy hints.\n"
            "4) Choose a legal move and call place_stone(player,row,col,reason).\n"
            "5) If place_stone fails, call get_board_state again and retry another legal move.\n"
            "6) Call remember with one short strategy note for future turns.\n"
            "Respond with one short sentence after tool calls."
        )

    def _build_command(self) -> list[str]:
        mcp_args = [
            "-m",
            "gomoku.mcp_server",
            "--state-path",
            str(self.state_path),
            "--memory-path",
            str(self.memory_path),
            "--board-size",
            str(self.board_size),
        ]

        return [
            self.codex_bin,
            "exec",
            "--json",
            "--model",
            self.model,
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "-c",
            "hide_agent_reasoning=false",
            "-c",
            f'mcp_servers.gomoku.command="{self.python_bin}"',
            "-c",
            f"mcp_servers.gomoku.args={json.dumps(mcp_args)}",
            "-c",
            f'mcp_servers.gomoku.cwd="{self.app_dir}"',
            "-c",
            "mcp_servers.gomoku.startup_timeout_sec=20",
            self._prompt(),
        ]

    def _extract_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("summary") or item.get("output_text")
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            return " ".join(parts).strip()
        if isinstance(value, dict):
            text = value.get("text") or value.get("summary") or value.get("content")
            if text:
                return self._extract_text(text)
        return ""

    def _trim(self, obj: Any, max_len: int = 220) -> str:
        text = json.dumps(obj, ensure_ascii=True)
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _event_to_log(self, event: dict[str, Any]) -> tuple[str, str] | None:
        event_type = str(event.get("type", ""))

        if event_type == "turn.started":
            return "system", "turn started"
        if event_type == "turn.failed":
            return "system", f"turn failed: {self._trim(event)}"
        if event_type == "turn.completed":
            return "system", "turn completed"

        if event_type in ("item.started", "item.completed"):
            item = event.get("item", {}) if isinstance(event.get("item"), dict) else {}
            item_type = str(item.get("type", ""))
            if item_type in ("reasoning", "analysis"):
                text = self._extract_text(item.get("summary")) or self._extract_text(item.get("content"))
                return "reasoning", text or "(reasoning event)"
            if item_type in ("mcp_tool_call", "function_call", "tool_call"):
                name = item.get("name") or item.get("tool_name") or item.get("tool") or "tool"
                args = item.get("arguments") or item.get("input") or {}
                return "tool", f"call {name} args={self._trim(args)}"
            if item_type in ("mcp_tool_result", "function_call_output", "tool_result"):
                out = item.get("output") or item.get("result") or {}
                return "tool", f"result {self._trim(out)}"
            if item_type in ("assistant_message", "agent_message", "message"):
                text = self._extract_text(item.get("content"))
                if not text:
                    text = self._extract_text(item.get("text"))
                return "assistant", text or "(assistant message)"

        if event_type in ("response.output_text.delta", "response.output_text.done"):
            delta = event.get("delta") or event.get("text") or ""
            if isinstance(delta, str) and delta.strip():
                return "assistant", delta.strip()

        return None

    def run_turn(self) -> AgentTurnResult:
        command = self._build_command()
        self.log(self.player, "system", "$ " + " ".join(shlex.quote(part) for part in command[:-1]) + " '<prompt>'")

        started = time.time()
        timed_out = False

        try:
            process = subprocess.Popen(
                command,
                cwd=self.workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            return AgentTurnResult(ok=False, return_code=127, timed_out=False, summary="codex CLI not found")
        except Exception as error:  # pragma: no cover - defensive
            return AgentTurnResult(ok=False, return_code=1, timed_out=False, summary=f"launch error: {error}")

        def reader() -> None:
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    self.log(self.player, "raw", line)
                    continue

                log_item = self._event_to_log(event)
                if log_item:
                    kind, text = log_item
                    self.log(self.player, kind, text)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

        try:
            process.wait(timeout=self.timeout_sec)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=10)

        thread.join(timeout=2)

        elapsed = round(time.time() - started, 2)
        rc = int(process.returncode or 0)
        ok = rc == 0 and not timed_out
        summary = f"return_code={rc}, elapsed={elapsed}s"
        if timed_out:
            summary = f"timeout after {self.timeout_sec}s"

        return AgentTurnResult(ok=ok, return_code=rc, timed_out=timed_out, summary=summary)
