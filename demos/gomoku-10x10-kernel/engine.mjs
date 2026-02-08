export const BOARD_SIZE = 10;
export const WIN_LENGTH = 5;
export const EMPTY = ".";
export const BLACK = "B";
export const WHITE = "W";

const DIRECTIONS = [
  [1, 0],
  [0, 1],
  [1, 1],
  [1, -1],
];

export class GomokuGame {
  constructor(size = BOARD_SIZE, winLength = WIN_LENGTH) {
    this.size = size;
    this.winLength = winLength;
    this.board = Array.from({ length: size }, () => Array(size).fill(EMPTY));
    this.current = BLACK;
    this.winner = null;
    this.draw = false;
    this.moveCount = 0;
    this.lastMove = null;
    this.history = [];
  }

  isInside(row, col) {
    return row >= 0 && row < this.size && col >= 0 && col < this.size;
  }

  isLegalMove(row, col) {
    return this.isInside(row, col) && this.board[row][col] === EMPTY && !this.isFinished();
  }

  getLegalMoves() {
    if (this.isFinished()) return [];
    const moves = [];
    for (let row = 0; row < this.size; row += 1) {
      for (let col = 0; col < this.size; col += 1) {
        if (this.board[row][col] === EMPTY) {
          moves.push([row, col]);
        }
      }
    }
    return moves;
  }

  isFinished() {
    return this.winner !== null || this.draw;
  }

  applyMove(row, col, meta = {}) {
    if (!this.isLegalMove(row, col)) {
      return { ok: false, error: "Illegal move." };
    }

    const player = this.current;
    this.board[row][col] = player;
    this.moveCount += 1;
    this.lastMove = { row, col, player };
    this.history.push({ row, col, player, meta });

    if (isWinningMove(this.board, this.winLength, row, col, player)) {
      this.winner = player;
    } else if (this.moveCount === this.size * this.size) {
      this.draw = true;
    } else {
      this.current = player === BLACK ? WHITE : BLACK;
    }

    return {
      ok: true,
      winner: this.winner,
      draw: this.draw,
      next: this.current,
    };
  }

  render() {
    const header = ["   "];
    for (let col = 0; col < this.size; col += 1) {
      header.push(String(col).padStart(2, " "));
    }

    const lines = [header.join(" ")];
    for (let row = 0; row < this.size; row += 1) {
      lines.push(`${String(row).padStart(2, " ")} ${this.board[row].map((x) => x.padStart(2, " ")).join(" ")}`);
    }
    return lines.join("\n");
  }
}

export function isWinningMove(board, winLength, row, col, player) {
  for (const [dr, dc] of DIRECTIONS) {
    let count = 1;
    count += countDirection(board, row, col, dr, dc, player);
    count += countDirection(board, row, col, -dr, -dc, player);
    if (count >= winLength) return true;
  }
  return false;
}

function countDirection(board, row, col, dr, dc, player) {
  const size = board.length;
  let r = row + dr;
  let c = col + dc;
  let count = 0;

  while (r >= 0 && r < size && c >= 0 && c < size && board[r][c] === player) {
    count += 1;
    r += dr;
    c += dc;
  }
  return count;
}

