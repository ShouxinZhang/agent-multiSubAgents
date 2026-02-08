from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as error:  # pragma: no cover - runtime dependency guard
    raise SystemExit(
        "Missing dependency 'mcp'. Install with: pip install -r apps/gomoku_codex_cli/requirements.txt"
    ) from error

from .memory_store import MemoryStore
from .state_store import GameStateStore


def build_server(state_store: GameStateStore, memory_store: MemoryStore) -> FastMCP:
    mcp = FastMCP("gomoku-tools")

    @mcp.tool()
    def get_board_state() -> dict[str, Any]:
        """Return a compact board snapshot and game metadata."""
        return state_store.public_state()

    @mcp.tool()
    def list_legal_moves(limit: int = 225) -> list[dict[str, int]]:
        """Return available moves as row/col pairs (0-indexed)."""
        moves = state_store.legal_moves()
        safe_limit = max(1, min(limit, len(moves)))
        return moves[:safe_limit]

    @mcp.tool()
    def place_stone(player: str, row: int, col: int, reason: str = "") -> dict[str, Any]:
        """Place a stone for player B or W at 0-indexed row/col."""
        result = state_store.apply_move(player=player, row=row, col=col, source="codex_mcp")
        if result.get("success") and reason.strip():
            memory_store.remember(player=player, note=reason, kind="move_reason")
        return result

    @mcp.tool()
    def get_memory(player: str, limit: int = 8) -> list[dict[str, Any]]:
        """Read recent memory items for a player token (B/W)."""
        safe_limit = max(1, min(limit, 100))
        return memory_store.get_memory(player=player, limit=safe_limit)

    @mcp.tool()
    def remember(player: str, note: str, kind: str = "strategy") -> dict[str, Any]:
        """Store a memory note for player B/W."""
        return memory_store.remember(player=player, note=note, kind=kind)

    return mcp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gomoku MCP server for Codex CLI")
    parser.add_argument("--state-path", required=True, help="Path to JSON file for game state")
    parser.add_argument("--memory-path", required=True, help="Path to JSON file for memory store")
    parser.add_argument("--board-size", type=int, default=15, help="Board size for state bootstrap")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state_store = GameStateStore(Path(args.state_path), board_size=args.board_size)
    memory_store = MemoryStore(Path(args.memory_path))
    server = build_server(state_store=state_store, memory_store=memory_store)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
