import { EMPTY, WIN_LENGTH, isWinningMove } from "./engine.mjs";

const DIRECTIONS = [
  [1, 0],
  [0, 1],
  [1, 1],
  [1, -1],
];

export class SimpleHeuristicAgent {
  constructor(name, side, memoryStore) {
    this.name = name;
    this.side = side;
    this.memoryStore = memoryStore;
  }

  chooseMove(context) {
    const { board, legalMoves } = context;
    const opponent = this.side === "B" ? "W" : "B";

    const immediateWin = findImmediate(board, legalMoves, this.side);
    if (immediateWin) {
      return makeDecision(immediateWin, "finish line", 0.99);
    }

    const immediateBlock = findImmediate(board, legalMoves, opponent);
    if (immediateBlock) {
      return makeDecision(immediateBlock, "block threat", 0.96);
    }

    const profile = this.memoryStore.getProfile(this.name);
    let best = legalMoves[0];
    let bestScore = Number.NEGATIVE_INFINITY;
    for (const move of legalMoves) {
      const score = evaluateMove(board, move[0], move[1], this.side, opponent, profile);
      if (score > bestScore) {
        bestScore = score;
        best = move;
      }
    }

    return makeDecision(best, "shape pressure", 0.7);
  }
}

function makeDecision(move, intent, confidence) {
  return {
    row: move[0],
    col: move[1],
    intent,
    confidence,
  };
}

function findImmediate(board, legalMoves, side) {
  for (const [row, col] of legalMoves) {
    if (wouldWin(board, row, col, side)) {
      return [row, col];
    }
  }
  return null;
}

function wouldWin(board, row, col, side) {
  if (board[row][col] !== EMPTY) return false;
  const nextBoard = board.map((line) => line.slice());
  nextBoard[row][col] = side;
  return isWinningMove(nextBoard, WIN_LENGTH, row, col, side);
}

function evaluateMove(board, row, col, own, opp, profile) {
  const size = board.length;
  const center = (size - 1) / 2;

  const centerBias = size - (Math.abs(row - center) + Math.abs(col - center));
  const ownNeighbors = countNearby(board, row, col, own);
  const oppNeighbors = countNearby(board, row, col, opp);
  const linePotential = longestLineIfPlaced(board, row, col, own);
  const defensePotential = longestLineIfPlaced(board, row, col, opp);
  const memoryBonus = (profile.hotMoves?.[`${row},${col}`] || 0) * 0.05;

  return (
    centerBias * 1.2 +
    ownNeighbors * 2.5 +
    oppNeighbors * 0.8 +
    linePotential * 3.0 +
    defensePotential * 1.6 +
    memoryBonus
  );
}

function countNearby(board, row, col, side) {
  let count = 0;
  for (let dr = -1; dr <= 1; dr += 1) {
    for (let dc = -1; dc <= 1; dc += 1) {
      if (dr === 0 && dc === 0) continue;
      const r = row + dr;
      const c = col + dc;
      if (r >= 0 && r < board.length && c >= 0 && c < board.length && board[r][c] === side) {
        count += 1;
      }
    }
  }
  return count;
}

function longestLineIfPlaced(board, row, col, side) {
  if (board[row][col] !== EMPTY) return 0;

  const size = board.length;
  let best = 1;
  for (const [dr, dc] of DIRECTIONS) {
    let line = 1;
    line += countDirection(board, row, col, dr, dc, side, size);
    line += countDirection(board, row, col, -dr, -dc, side, size);
    best = Math.max(best, line);
  }
  return best;
}

function countDirection(board, row, col, dr, dc, side, size) {
  let r = row + dr;
  let c = col + dc;
  let count = 0;

  while (r >= 0 && r < size && c >= 0 && c < size && board[r][c] === side) {
    count += 1;
    r += dr;
    c += dc;
  }
  return count;
}

