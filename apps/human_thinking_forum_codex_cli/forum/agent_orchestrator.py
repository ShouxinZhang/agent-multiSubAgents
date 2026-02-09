from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .codex_agent import CodexForumAgent
from .models import AgentDefinition
from .skills_loader import SkillsLoader
from .store import ForumStore


EmitCallback = Callable[[str, dict[str, Any]], None]


class AgentOrchestrator:
    def __init__(
        self,
        *,
        store: ForumStore,
        skills_loader: SkillsLoader,
        emit: EmitCallback,
        config_path: Path,
        workspace_root: Path,
        codex_bin: str,
        python_bin: str,
        default_model: str,
        timeout_sec: int,
    ):
        self.store = store
        self.skills_loader = skills_loader
        self.emit = emit
        self.config_path = Path(config_path)
        self.workspace_root = Path(workspace_root)
        self.codex_bin = codex_bin
        self.python_bin = python_bin
        self.default_model = default_model
        self.timeout_sec = timeout_sec

        self._status_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._threads: dict[str, threading.Thread] = {}
        self._status: dict[str, dict[str, Any]] = {}
        self._post_cursor = 0
        self._reply_cursor = 0

        self._agents = self._load_agents()
        self.mcp_server_script = self.workspace_root / "apps" / "human_thinking_forum_codex_cli" / "forum" / "mcp_server.py"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_agents(self) -> list[AgentDefinition]:
        if not self.config_path.exists():
            return []
        with open(self.config_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        agents: list[AgentDefinition] = []
        for item in payload.get("agents", []):
            agent_id = str(item.get("id", "")).strip()
            name = str(item.get("name", agent_id)).strip() or agent_id
            persona = str(item.get("persona", "")).strip() or "Balanced forum participant"
            model = str(item.get("model", self.default_model)).strip() or self.default_model
            if not agent_id:
                continue
            agents.append(AgentDefinition(agent_id=agent_id, name=name, persona=persona, model=model))
        return agents

    def _default_status(self, agent_id: str) -> dict[str, Any]:
        return {
            "agent_id": agent_id,
            "running": False,
            "last_turn_at": None,
            "last_event_ts": None,
            "last_error": None,
            "last_error_code": None,
            "last_exception": None,
            "last_summary": None,
            "last_action": None,
        }

    def _set_status(self, agent_id: str, **updates: Any) -> None:
        with self._status_lock:
            current = self._status.get(agent_id, self._default_status(agent_id))
            current.update(updates)
            self._status[agent_id] = current

    def _emit_agent_log(self, agent_id: str, kind: str, text: str) -> None:
        now = self._now()
        self._set_status(agent_id, last_event_ts=now, last_action=kind)
        self.emit(
            "agent_log",
            {
                "agent_id": agent_id,
                "kind": kind,
                "text": text,
                "ts": now,
            },
        )

    def _emit_new_forum_content(self, agent_id: str) -> None:
        delta = self.store.content_since(post_seq=self._post_cursor, reply_seq=self._reply_cursor)
        self._post_cursor = int(delta["latest_post_seq"])
        self._reply_cursor = int(delta["latest_reply_seq"])

        for post in delta["posts"]:
            self.emit("post_created", {"source": "agent", "agent_id": agent_id, "post": post})
        for reply in delta["replies"]:
            self.emit("reply_created", {"source": "agent", "agent_id": agent_id, "reply": reply})

    def _worker(self, agent: AgentDefinition) -> None:
        workspace = self.skills_loader.agent_workspace(agent.agent_id)
        runner = CodexForumAgent(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            persona=agent.persona,
            model=agent.model,
            codex_bin=self.codex_bin,
            python_bin=self.python_bin,
            workspace=workspace,
            mcp_server_script=self.mcp_server_script,
            data_path=self.store.data_path,
            timeout_sec=self.timeout_sec,
            log_callback=self._emit_agent_log,
        )

        while not self._stop_event.is_set():
            try:
                self._set_status(agent.agent_id, running=True, last_exception=None)
                self.skills_loader.sync_agent(agent.agent_id)

                result = runner.run_turn()
                error_code = None if result.ok else str(result.return_code)
                self._set_status(
                    agent.agent_id,
                    running=not self._stop_event.is_set(),
                    last_turn_at=self._now(),
                    last_error=None if result.ok else result.summary,
                    last_error_code=error_code,
                    last_summary=result.summary,
                )

                self.emit(
                    "agent_status",
                    {
                        "agent_id": agent.agent_id,
                        "running": not self._stop_event.is_set(),
                        "last_turn_at": self._status[agent.agent_id]["last_turn_at"],
                        "last_event_ts": self._status[agent.agent_id]["last_event_ts"],
                        "last_error": self._status[agent.agent_id]["last_error"],
                        "last_error_code": self._status[agent.agent_id]["last_error_code"],
                        "last_exception": self._status[agent.agent_id]["last_exception"],
                        "last_summary": result.summary,
                        "last_action": self._status[agent.agent_id]["last_action"],
                    },
                )
                self._emit_new_forum_content(agent.agent_id)

                # Terminal failure guard: avoid hot failure loop when codex binary is unavailable.
                if result.return_code == 127:
                    self._set_status(
                        agent.agent_id,
                        running=False,
                        last_error="codex CLI not found",
                        last_error_code="127",
                    )
                    self.emit(
                        "agent_status",
                        {
                            "agent_id": agent.agent_id,
                            "running": False,
                            "last_turn_at": self._status[agent.agent_id]["last_turn_at"],
                            "last_event_ts": self._status[agent.agent_id]["last_event_ts"],
                            "last_error": "codex CLI not found",
                            "last_error_code": "127",
                            "last_exception": self._status[agent.agent_id]["last_exception"],
                            "last_summary": result.summary,
                            "last_action": self._status[agent.agent_id]["last_action"],
                        },
                    )
                    break
            except Exception as error:  # pragma: no cover - defensive
                self._set_status(
                    agent.agent_id,
                    running=False,
                    last_turn_at=self._now(),
                    last_error="worker exception",
                    last_error_code="exception",
                    last_exception=str(error),
                    last_summary="worker exception",
                )
                self.emit(
                    "agent_status",
                    {
                        "agent_id": agent.agent_id,
                        "running": False,
                        "last_turn_at": self._status[agent.agent_id]["last_turn_at"],
                        "last_event_ts": self._status[agent.agent_id]["last_event_ts"],
                        "last_error": "worker exception",
                        "last_error_code": "exception",
                        "last_exception": str(error),
                        "last_summary": "worker exception",
                        "last_action": self._status[agent.agent_id]["last_action"],
                    },
                )
                break

        self._set_status(agent.agent_id, running=False)

    def start_all(self) -> dict[str, Any]:
        if any(thread.is_alive() for thread in self._threads.values()):
            return {"success": True, "message": "agents already running", "count": len(self._threads)}

        self._agents = self._load_agents()
        self._stop_event.clear()
        self._threads = {}
        self._post_cursor = 0
        self._reply_cursor = 0

        agent_ids = [agent.agent_id for agent in self._agents]
        self.skills_loader.sync_all(agent_ids, force=True)

        for agent in self._agents:
            self._set_status(
                agent.agent_id,
                running=True,
                last_turn_at=None,
                last_event_ts=None,
                last_error=None,
                last_error_code=None,
                last_exception=None,
                last_summary=None,
                last_action=None,
            )
            thread = threading.Thread(target=self._worker, args=(agent,), daemon=True)
            thread.start()
            self._threads[agent.agent_id] = thread

        self.emit("agents_started", {"agent_ids": agent_ids, "count": len(agent_ids)})
        return {"success": True, "message": "agents started", "count": len(agent_ids)}

    def stop_all(self) -> dict[str, Any]:
        self._stop_event.set()
        for thread in list(self._threads.values()):
            thread.join(timeout=0.5)
        self._threads = {}

        with self._status_lock:
            for agent_id in list(self._status.keys()):
                self._status[agent_id]["running"] = False

        self.emit("agents_stopped", {"ts": self._now()})
        return {"success": True, "message": "agents stopped"}

    def reload_skills(self) -> dict[str, Any]:
        agent_ids = [agent.agent_id for agent in self._agents]
        synced = self.skills_loader.sync_all(agent_ids, force=True)
        self.emit("skills_reloaded", {"synced": synced})
        return {"success": True, "synced": synced}

    def status_list(self) -> list[dict[str, Any]]:
        agent_ids = [agent.agent_id for agent in self._agents]
        with self._status_lock:
            result = []
            for agent_id in agent_ids:
                status = self._status.get(agent_id, self._default_status(agent_id))
                result.append(dict(status))
            return result
