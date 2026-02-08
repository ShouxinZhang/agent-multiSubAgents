import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { LiveMatchRunner } from "./live-match.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const model = process.env.GOMOKU_MODEL || "gpt-5.3-codex";
const games = Number(process.env.GOMOKU_GAMES || 1);
const turnDelayMs = Number(process.env.GOMOKU_TURN_DELAY_MS || 0);
const workspaceRoot = path.resolve(__dirname, "..", "..");

const runner = new LiveMatchRunner({
  model,
  backend: "codex-cli",
  games,
  turnDelayMs,
  workspaceRoot,
});

console.log("10x10 Gomoku Codex CLI Runner");
console.log(`backend=codex-cli model=${model} games=${games} turnDelayMs=${turnDelayMs}`);

await runner.run((event) => {
  if (event.type === "move_applied") {
    console.log(
      `#${String(event.moveIndex).padStart(2, "0")} game${event.gameNo} ${event.player}(${event.side}) -> (${event.row},${event.col})`
    );
    return;
  }

  if (event.type === "game_finished") {
    console.log(
      `game ${event.gameNo} finished: ${event.draw ? "draw" : `winner=${event.winner}(${event.winnerSide})`}`
    );
    return;
  }

  if (event.type === "match_finished") {
    const { alphaWins, betaWins, draws } = event.result;
    console.log(`match finished: alpha=${alphaWins}, beta=${betaWins}, draw=${draws}`);
    return;
  }

  if (event.type === "agent_event" && event.kind === "error") {
    console.error(`[agent:${event.player}] ${event.text}`);
  }
});
