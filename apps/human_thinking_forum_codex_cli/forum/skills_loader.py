from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable


EmitCallback = Callable[[str, dict], None]


class SkillsLoader:
    def __init__(self, *, skills_root: Path, runtime_root: Path, emit: EmitCallback | None = None):
        self.skills_root = Path(skills_root)
        self.runtime_root = Path(runtime_root)
        self.emit = emit
        self.snapshot_cache: dict[str, dict[str, float]] = {}

    def _skill_dirs(self, root: Path) -> dict[str, Path]:
        if not root.exists():
            return {}
        result: dict[str, Path] = {}
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if child.is_dir() and (child / "SKILL.md").exists():
                result[child.name] = child
        return result

    def _collect_skill_map(self, agent_id: str) -> dict[str, Path]:
        shared = self._skill_dirs(self.skills_root / "shared")
        agent_specific = self._skill_dirs(self.skills_root / "agents" / agent_id)
        merged = dict(shared)
        merged.update(agent_specific)
        return merged

    def _snapshot_files(self, roots: list[Path]) -> dict[str, float]:
        snapshot: dict[str, float] = {}
        for root in roots:
            if not root.exists():
                continue
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    path = Path(dirpath) / filename
                    try:
                        snapshot[str(path.resolve())] = float(path.stat().st_mtime)
                    except FileNotFoundError:
                        continue
        return snapshot

    def _current_snapshot(self, agent_id: str) -> dict[str, float]:
        shared_root = self.skills_root / "shared"
        agent_root = self.skills_root / "agents" / agent_id
        return self._snapshot_files([shared_root, agent_root])

    def _needs_reload(self, agent_id: str) -> bool:
        current = self._current_snapshot(agent_id)
        previous = self.snapshot_cache.get(agent_id)
        if previous is None:
            return True
        return current != previous

    def _write_agents_md(self, workspace: Path, agent_id: str) -> None:
        content = (
            "# Agent Workspace Instructions\n\n"
            f"- Agent ID: {agent_id}\n"
            "- You must use MCP forum tools to read and write forum content.\n"
            "- Do not fabricate posts, always inspect current forum state first.\n"
            "- Keep responses concise and useful.\n"
        )
        (workspace / "AGENTS.md").write_text(content, encoding="utf-8")

    def agent_workspace(self, agent_id: str) -> Path:
        workspace = self.runtime_root / "agent_workspaces" / agent_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def sync_agent(self, agent_id: str, force: bool = False) -> bool:
        if not force and not self._needs_reload(agent_id):
            return False

        workspace = self.agent_workspace(agent_id)
        target_root = workspace / ".codex" / "skills"
        target_root.parent.mkdir(parents=True, exist_ok=True)
        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.mkdir(parents=True, exist_ok=True)

        skill_map = self._collect_skill_map(agent_id)
        for name, source_dir in skill_map.items():
            shutil.copytree(source_dir, target_root / name)

        self._write_agents_md(workspace, agent_id)
        self.snapshot_cache[agent_id] = self._current_snapshot(agent_id)

        if self.emit:
            self.emit(
                "skills_synced",
                {
                    "agent_id": agent_id,
                    "skills": sorted(skill_map.keys()),
                    "workspace": str(workspace),
                },
            )
        return True

    def sync_all(self, agent_ids: list[str], force: bool = False) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for agent_id in agent_ids:
            result[agent_id] = self.sync_agent(agent_id, force=force)
        return result
