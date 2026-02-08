from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fcntl


class MemoryStore:
    def __init__(self, memory_path: Path):
        self.memory_path = Path(memory_path)
        self.lock_path = self.memory_path.with_suffix(self.memory_path.suffix + ".lock")
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self.clear()

    @contextmanager
    def _locked(self):
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read_unlocked(self) -> dict[str, list[dict[str, Any]]]:
        if not self.memory_path.exists():
            return {"B": [], "W": []}
        with open(self.memory_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        data.setdefault("B", [])
        data.setdefault("W", [])
        return data

    def _write_unlocked(self, data: dict[str, list[dict[str, Any]]]) -> None:
        fd, temp_path = tempfile.mkstemp(prefix="gomoku_memory_", suffix=".json", dir=self.memory_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=True, indent=2)
            os.replace(temp_path, self.memory_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def clear(self) -> None:
        with self._locked():
            self._write_unlocked({"B": [], "W": []})

    def remember(self, player: str, note: str, kind: str = "strategy") -> dict[str, Any]:
        player = player.upper()
        if player not in ("B", "W"):
            return {"success": False, "error": f"Invalid player: {player}"}

        entry = {
            "ts": self._now(),
            "player": player,
            "kind": kind,
            "note": note.strip(),
        }

        with self._locked():
            data = self._read_unlocked()
            data[player].append(entry)
            self._write_unlocked(data)
            count = len(data[player])

        return {"success": True, "count": count, "entry": entry}

    def get_memory(self, player: str, limit: int = 8) -> list[dict[str, Any]]:
        player = player.upper()
        if player not in ("B", "W"):
            return []

        with self._locked():
            data = self._read_unlocked()
            items = data[player][-max(1, limit) :]
        return items

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self._locked():
            return self._read_unlocked()
