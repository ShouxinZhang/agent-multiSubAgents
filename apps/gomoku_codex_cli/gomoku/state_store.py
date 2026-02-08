from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import fcntl

from .engine import Move, apply_move, board_as_rows, legal_moves, new_game_state


class GameStateStore:
    def __init__(self, state_path: Path, board_size: int = 15):
        self.state_path = Path(state_path)
        self.board_size = board_size
        self.lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self.reset(board_size=board_size)

    @contextmanager
    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return new_game_state(self.board_size)
        with open(self.state_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        fd, temp_path = tempfile.mkstemp(prefix="gomoku_state_", suffix=".json", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=True, indent=2)
            os.replace(temp_path, self.state_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def reset(self, board_size: int | None = None) -> dict[str, Any]:
        size = board_size or self.board_size
        state = new_game_state(size)
        with self._locked():
            self._write_unlocked(state)
        return state

    def load(self) -> dict[str, Any]:
        with self._locked():
            return self._read_unlocked()

    def apply_move(self, player: str, row: int, col: int, source: str = "mcp") -> dict[str, Any]:
        with self._locked():
            state = self._read_unlocked()
            result = apply_move(state, Move(player=player.upper(), row=row, col=col, source=source))
            if result.get("success"):
                self._write_unlocked(state)
            return {**result, "state": self._public_state(state)}

    def _public_state(self, state: dict[str, Any]) -> dict[str, Any]:
        board = state["board"]
        history = state.get("history", [])
        return {
            "board_size": state["board_size"],
            "board_rows": board_as_rows(board),
            "current_player": state.get("current_player"),
            "winner": state.get("winner"),
            "move_count": state.get("move_count", 0),
            "last_move": history[-1] if history else None,
            "updated_at": state.get("updated_at"),
        }

    def public_state(self) -> dict[str, Any]:
        with self._locked():
            return self._public_state(self._read_unlocked())

    def legal_moves(self) -> list[dict[str, int]]:
        with self._locked():
            state = self._read_unlocked()
            return [{"row": row, "col": col} for row, col in legal_moves(state["board"])]
