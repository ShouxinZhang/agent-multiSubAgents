from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


LogCallback = Callable[[str, str, str], None]


@dataclass
class AgentTurnResult:
    ok: bool
    return_code: int
    timed_out: bool
    summary: str


class CodexForumAgent:
    def __init__(
        self,
        *,
        agent_id: str,
        agent_name: str,
        persona: str,
        model: str,
        codex_bin: str,
        python_bin: str,
        workspace: Path,
        mcp_server_script: Path,
        data_path: Path,
        timeout_sec: int,
        log_callback: LogCallback,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.persona = persona
        self.model = model
        self.codex_bin = codex_bin
        self.python_bin = python_bin
        self.workspace = Path(workspace)
        self.mcp_server_script = Path(mcp_server_script)
        self.app_dir = self.mcp_server_script.parent.parent
        self.data_path = Path(data_path)
        self.timeout_sec = timeout_sec
        self.log = log_callback

    def _prompt(self) -> str:
        return (
            f"You are forum agent '{self.agent_name}' (id={self.agent_id}). Persona: {self.persona}. "
            "You MUST use MCP tools only."
            "\nProcess per turn:"
            "\n1) Call forum_agent_register_login() first."
            "\n2) Call forum_agent_auth_state() and continue only when logged_in=true."
            "\n3) Call forum_get_recent_posts(limit=12)."
            "\n4) Optionally call forum_get_post(post_id) for one target thread."
            "\n5) Decide ONE action: create a post OR reply to one existing post."
            "\n6) If posting, call forum_create_post(title,content)."
            "\n7) If replying, call forum_reply_post(post_id,content)."
            "\n8) Call forum_remember(note,kind='strategy') with one concise reflection."
            "\n9) Return one short sentence summary."
            "\nRules: no unsafe content; no spam title duplicates in same turn; keep content under 400 Chinese characters."
        )

    def _build_command(self) -> list[str]:
        mcp_args = [
            "-m",
            "forum.mcp_server",
            "--data-path",
            str(self.data_path),
            "--agent-id",
            self.agent_id,
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
            f'mcp_servers.forum.command="{self.python_bin}"',
            "-c",
            f"mcp_servers.forum.args={json.dumps(mcp_args)}",
            "-c",
            f'mcp_servers.forum.cwd="{self.app_dir}"',
            "-c",
            "mcp_servers.forum.startup_timeout_sec=20",
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

    def _trim(self, obj: Any, max_len: int = 260) -> str:
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
                return "thinking", text or "(thinking event)"

            if item_type in ("mcp_tool_call", "function_call", "tool_call"):
                name = item.get("name") or item.get("tool_name") or item.get("tool") or "tool"
                args = item.get("arguments") or item.get("input") or {}
                return "tool", f"call {name} args={self._trim(args)}"

            if item_type in ("mcp_tool_result", "function_call_output", "tool_result"):
                output = item.get("output") or item.get("result") or {}
                return "tool", f"result {self._trim(output)}"

            if item_type in ("assistant_message", "agent_message", "message"):
                text = self._extract_text(item.get("content"))
                if not text:
                    text = self._extract_text(item.get("text"))
                return "chat", text or "(assistant message)"

        if event_type in ("response.output_text.delta", "response.output_text.done"):
            delta = event.get("delta") or event.get("text") or ""
            if isinstance(delta, str) and delta.strip():
                return "chat", delta.strip()

        return None

    def run_turn(self) -> AgentTurnResult:
        command = self._build_command()
        self.log(self.agent_id, "system", "$ " + " ".join(shlex.quote(part) for part in command[:-1]) + " '<prompt>'")

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
        except Exception as error:  # pragma: no cover
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
                    self.log(self.agent_id, "raw", line)
                    continue

                item = self._event_to_log(event)
                if item:
                    kind, text = item
                    self.log(self.agent_id, kind, text)

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
