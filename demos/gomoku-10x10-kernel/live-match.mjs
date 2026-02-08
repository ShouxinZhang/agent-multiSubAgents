import path from "node:path";
import { fileURLToPath } from "node:url";
import { CodexCliAgent } from "./codex-cli-agent.mjs";
import { BLACK, GomokuGame, WHITE } from "./engine.mjs";
import { JsonMemoryStore } from "./memory-store.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class LiveMatchRunner {
  constructor(options = {}) {
    this.model = options.model || "gpt-5.3-codex";
    this.games = options.games || 1;
    this.turnDelayMs = options.turnDelayMs ?? 220;
    this.backend = "codex-cli";
    this.workspaceRoot = options.workspaceRoot || path.resolve(__dirname, "..", "..");
    this.memoryStore = new JsonMemoryStore(path.join(__dirname, "memory"));
  }

  async run(emit) {
    const startedAt = new Date().toISOString();
    emit({
      type: "match_started",
      model: this.model,
      backend: this.backend,
      games: this.games,
      startedAt,
    });

    let alphaWins = 0;
    let betaWins = 0;
    let draws = 0;

    for (let gameNo = 1; gameNo <= this.games; gameNo += 1) {
      const game = new GomokuGame(10, 5);
      const sides = pickSides(gameNo);
      const agents = this.makeAgents(sides);

      emit({
        type: "game_started",
        gameNo,
        black: sides.blackName,
        white: sides.whiteName,
        board: cloneBoard(game.board),
      });

      while (!game.isFinished()) {
        const side = game.current;
        const active = agents[side];
        const opponent = side === BLACK ? agents[WHITE] : agents[BLACK];

        emit({
          type: "turn_started",
          gameNo,
          moveIndex: game.moveCount + 1,
          side,
          player: active.name,
        });

        const decision = await active.chooseMove(
          {
            board: game.board,
            legalMoves: game.getLegalMoves(),
            moveIndex: game.moveCount + 1,
            history: game.history,
            opponentProfile: this.memoryStore.getProfile(opponent.name),
          },
          (evt) =>
            emit({
              type: "agent_event",
              gameNo,
              moveIndex: game.moveCount + 1,
              player: active.name,
              side,
              ...evt,
            })
        );

        const applied = game.applyMove(decision.row, decision.col, {
          agent: active.name,
          intent: decision.intent,
          confidence: decision.confidence,
        });
        if (!applied.ok) {
          throw new Error(`Illegal move by ${active.name}: (${decision.row},${decision.col})`);
        }

        this.memoryStore.recordMove(active.name, decision.row, decision.col);
        emit({
          type: "move_applied",
          gameNo,
          moveIndex: game.moveCount,
          side,
          player: active.name,
          row: decision.row,
          col: decision.col,
          intent: decision.intent,
          confidence: decision.confidence,
          board: cloneBoard(game.board),
        });

        if (this.turnDelayMs > 0) {
          await sleep(this.turnDelayMs);
        }
      }

      const winnerName = game.winner === BLACK ? sides.blackName : game.winner === WHITE ? sides.whiteName : null;
      if (game.draw) draws += 1;
      if (winnerName === "alpha") alphaWins += 1;
      if (winnerName === "beta") betaWins += 1;

      this.memoryStore.recordGame("alpha", resultFor("alpha", winnerName, game.draw));
      this.memoryStore.recordGame("beta", resultFor("beta", winnerName, game.draw));

      emit({
        type: "game_finished",
        gameNo,
        draw: game.draw,
        winner: winnerName,
        winnerSide: game.winner,
        board: cloneBoard(game.board),
      });
    }

    const alphaProfile = this.memoryStore.getProfile("alpha");
    const betaProfile = this.memoryStore.getProfile("beta");

    emit({
      type: "match_finished",
      result: { alphaWins, betaWins, draws },
      profiles: {
        alpha: alphaProfile,
        beta: betaProfile,
      },
      endedAt: new Date().toISOString(),
    });
  }

  makeAgents({ blackName, whiteName }) {
    return {
      [BLACK]: new CodexCliAgent({
        name: blackName,
        side: BLACK,
        memoryStore: this.memoryStore,
        model: this.model,
        workspaceRoot: this.workspaceRoot,
      }),
      [WHITE]: new CodexCliAgent({
        name: whiteName,
        side: WHITE,
        memoryStore: this.memoryStore,
        model: this.model,
        workspaceRoot: this.workspaceRoot,
      }),
    };
  }
}

function pickSides(gameNo) {
  if (gameNo % 2 === 1) {
    return { blackName: "alpha", whiteName: "beta" };
  }
  return { blackName: "beta", whiteName: "alpha" };
}

function resultFor(name, winnerName, draw) {
  if (draw) return "draw";
  return name === winnerName ? "win" : "loss";
}

function cloneBoard(board) {
  return board.map((row) => row.slice());
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
