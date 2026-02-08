from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

BLACK = "B"
WHITE = "W"
EMPTY = "."
WIN_LENGTH = 5


@dataclass(frozen=True)
class Move:
    player: str
    row: int
    col: int
    source: str = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def other_player(player: str) -> str:
    player = player.upper()
    if player == BLACK:
        return WHITE
    if player == WHITE:
        return BLACK
    raise ValueError(f"Unsupported player: {player}")


def new_game_state(board_size: int = 15) -> dict[str, Any]:
    if board_size < WIN_LENGTH:
        raise ValueError("Board size must be at least 5.")

    board = [[EMPTY for _ in range(board_size)] for _ in range(board_size)]
    return {
        "board_size": board_size,
        "board": board,
        "current_player": BLACK,
        "winner": None,
        "move_count": 0,
        "history": [],
        "updated_at": utc_now_iso(),
    }


def within_board(board_size: int, row: int, col: int) -> bool:
    return 0 <= row < board_size and 0 <= col < board_size


def legal_moves(board: list[list[str]]) -> list[tuple[int, int]]:
    moves: list[tuple[int, int]] = []
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            if cell == EMPTY:
                moves.append((r, c))
    return moves


def _count_in_direction(board: list[list[str]], row: int, col: int, dr: int, dc: int) -> int:
    player = board[row][col]
    if player == EMPTY:
        return 0

    size = len(board)
    count = 1

    r, c = row + dr, col + dc
    while within_board(size, r, c) and board[r][c] == player:
        count += 1
        r += dr
        c += dc

    r, c = row - dr, col - dc
    while within_board(size, r, c) and board[r][c] == player:
        count += 1
        r -= dr
        c -= dc

    return count


def has_winner(board: list[list[str]], row: int, col: int) -> bool:
    return any(
        _count_in_direction(board, row, col, dr, dc) >= WIN_LENGTH
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1))
    )


def _validate_move(state: dict[str, Any], move: Move) -> tuple[bool, str | None]:
    board = state["board"]
    size = state["board_size"]

    if state.get("winner"):
        return False, "Game already finished."
    if move.player not in (BLACK, WHITE):
        return False, f"Invalid player token: {move.player}"
    if move.player != state.get("current_player"):
        return False, f"Not {move.player}'s turn."
    if not within_board(size, move.row, move.col):
        return False, "Move is outside of board."
    if board[move.row][move.col] != EMPTY:
        return False, "Target position is occupied."
    return True, None


def apply_move(state: dict[str, Any], move: Move) -> dict[str, Any]:
    valid, reason = _validate_move(state, move)
    if not valid:
        return {
            "success": False,
            "error": reason,
            "winner": state.get("winner"),
            "current_player": state.get("current_player"),
            "move_count": state.get("move_count", 0),
        }

    board = state["board"]
    board[move.row][move.col] = move.player

    state["move_count"] = int(state.get("move_count", 0)) + 1
    state["history"].append(
        {
            "seq": state["move_count"],
            "player": move.player,
            "row": move.row,
            "col": move.col,
            "source": move.source,
            "ts": utc_now_iso(),
        }
    )

    winner: str | None = None
    if has_winner(board, move.row, move.col):
        winner = move.player
        state["winner"] = winner
    elif not legal_moves(board):
        winner = "DRAW"
        state["winner"] = winner
    else:
        state["current_player"] = other_player(move.player)

    state["updated_at"] = utc_now_iso()

    return {
        "success": True,
        "winner": winner,
        "current_player": state.get("current_player"),
        "move_count": state.get("move_count"),
        "row": move.row,
        "col": move.col,
        "player": move.player,
    }


def board_as_rows(board: list[list[str]]) -> list[str]:
    return ["".join(row) for row in board]
