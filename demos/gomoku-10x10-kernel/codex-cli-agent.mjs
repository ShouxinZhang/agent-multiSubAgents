import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUTPUT_SCHEMA = path.join(__dirname, "move.schema.json");

export class CodexCliAgent {
  constructor({ name, side, memoryStore, model, workspaceRoot }) {
    this.name = name;
    this.side = side;
    this.memoryStore = memoryStore;
    this.model = model;
    this.workspaceRoot = workspaceRoot;
    this.threadId = null;
  }

  async chooseMove(context, onEvent) {
    const prompt = buildPrompt({
      ...context,
      selfName: this.name,
      side: this.side,
      selfProfile: this.memoryStore.getProfile(this.name),
    });

    let rawText = "";
    try {
      const result = await runCodexExec({
        prompt,
        model: this.model,
        threadId: this.threadId,
        cwd: this.workspaceRoot,
        outputSchemaPath: OUTPUT_SCHEMA,
        onEvent: (event) => onEvent?.({ agent: this.name, side: this.side, ...event }),
      });
      this.threadId = result.threadId || this.threadId;
      rawText = result.lastAgentMessage;
    } catch (error) {
      onEvent?.({
        agent: this.name,
        side: this.side,
        kind: "error",
        text: `Codex exec failed: ${error.message}`,
      });
      throw new Error(`Codex exec failed: ${error.message}`);
    }

    const parsed = parseMovePayload(rawText);
    if (!parsed) {
      onEvent?.({
        agent: this.name,
        side: this.side,
        kind: "error",
        text: "Invalid JSON from model output.",
      });
      throw new Error("Invalid JSON from model output.");
    }

    const legalSet = new Set(context.legalMoves.map(([row, col]) => `${row},${col}`));
    if (!legalSet.has(`${parsed.row},${parsed.col}`)) {
      onEvent?.({
        agent: this.name,
        side: this.side,
        kind: "error",
        text: `Model returned illegal move (${parsed.row},${parsed.col}).`,
      });
      throw new Error(`Model returned illegal move (${parsed.row},${parsed.col}).`);
    }

    return {
      row: parsed.row,
      col: parsed.col,
      intent: parsed.rationale,
      confidence: parsed.confidence,
    };
  }
}

function buildPrompt({
  board,
  legalMoves,
  moveIndex,
  history,
  opponentProfile,
  selfProfile,
  selfName,
  side,
}) {
  const boardText = renderBoardWithAxes(board);
  const legalText = legalMoves.map(([row, col]) => `${row},${col}`).join(" ");
  const recentHistory = history
    .slice(-8)
    .map((m) => `${m.player}@${m.row},${m.col}`)
    .join(" | ");

  const selfHot = topHotMoves(selfProfile.hotMoves);
  const oppHot = topHotMoves(opponentProfile.hotMoves);

  return [
    `You are ${selfName}, playing Gomoku side ${side} on a 10x10 board.`,
    "Goal: connect 5 in a row. Win immediately if possible; otherwise block immediate opponent win.",
    "Final answer must be exactly one JSON object: {row,col,rationale,confidence}.",
    "Do not add markdown fences or surrounding text.",
    "Before final JSON, include one short plain-text reasoning summary of your tactical intent.",
    "Use concise public rationale in JSON, <= 16 words.",
    `Move index: ${moveIndex}`,
    "",
    "Board (rows and cols are 0..9):",
    boardText,
    "",
    `Legal moves (${legalMoves.length}):`,
    legalText,
    "",
    `Recent moves: ${recentHistory || "none"}`,
    `Self profile: games=${selfProfile.games}, winRate=${selfProfile.winRate.toFixed(2)}, topMoves=${selfHot}`,
    `Opponent profile: games=${opponentProfile.games}, winRate=${opponentProfile.winRate.toFixed(2)}, topMoves=${oppHot}`,
  ].join("\n");
}

function renderBoardWithAxes(board) {
  const size = board.length;
  const lines = [];
  lines.push(`    ${Array.from({ length: size }, (_, i) => String(i).padStart(2, " ")).join(" ")}`);
  for (let row = 0; row < size; row += 1) {
    lines.push(`${String(row).padStart(2, " ")}: ${board[row].map((v) => v.padStart(2, " ")).join(" ")}`);
  }
  return lines.join("\n");
}

function topHotMoves(hotMoves = {}) {
  const top = Object.entries(hotMoves)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([pos, count]) => `${pos}(${count})`);
  return top.length ? top.join(",") : "none";
}

function parseMovePayload(text) {
  if (!text || typeof text !== "string") return null;
  const trimmed = text.trim();
  const direct = tryParseJson(trimmed);
  if (direct) return sanitizeMove(direct);

  const fenced = trimmed.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/, "");
  const fencedParsed = tryParseJson(fenced);
  if (fencedParsed) return sanitizeMove(fencedParsed);

  const match = trimmed.match(/\{[\s\S]*\}/);
  if (!match) return null;
  return sanitizeMove(tryParseJson(match[0]));
}

function tryParseJson(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

function sanitizeMove(obj) {
  if (!obj || typeof obj !== "object") return null;
  const row = Number(obj.row);
  const col = Number(obj.col);
  const rationale = String(obj.rationale ?? "").trim();
  const confidence = Number(obj.confidence);
  if (!Number.isInteger(row) || row < 0 || row > 9) return null;
  if (!Number.isInteger(col) || col < 0 || col > 9) return null;
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) return null;
  return { row, col, rationale: rationale || "no rationale", confidence };
}

async function runCodexExec({ prompt, model, threadId, cwd, outputSchemaPath, onEvent }) {
  const args = threadId
    ? ["exec", "resume", "--json", "--model", model, threadId, prompt]
    : [
        "exec",
        "--json",
        "--model",
        model,
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--output-schema",
        outputSchemaPath,
        prompt,
      ];

  const child = spawn("codex", args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
  let resolvedThreadId = threadId;
  let lastAgentMessage = "";
  let stderrText = "";

  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");

  let stdoutBuf = "";
  child.stdout.on("data", (chunk) => {
    stdoutBuf += chunk;
    let idx = stdoutBuf.indexOf("\n");
    while (idx >= 0) {
      const line = stdoutBuf.slice(0, idx).trim();
      stdoutBuf = stdoutBuf.slice(idx + 1);
      handleStdoutLine(line);
      idx = stdoutBuf.indexOf("\n");
    }
  });

  child.stderr.on("data", (chunk) => {
    const text = chunk.toString();
    stderrText += text;
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (trimmed) {
        onEvent?.({ kind: "stderr", text: trimmed });
      }
    }
  });

  function handleStdoutLine(line) {
    if (!line) return;
    const event = tryParseJson(line);
    if (!event) {
      onEvent?.({ kind: "stdout", text: line });
      return;
    }

    if (event.type === "thread.started" && event.thread_id) {
      resolvedThreadId = event.thread_id;
      onEvent?.({ kind: "thread", text: `thread started: ${event.thread_id}` });
      return;
    }

    if (event.type === "item.completed" || event.type === "item.started") {
      const itemType = event.item?.type || "unknown";
      const itemText = event.item?.text || event.item?.command || "";
      onEvent?.({
        kind: itemType,
        text: itemText || `${itemType} event`,
      });
      if (itemType === "agent_message" && event.item?.text) {
        lastAgentMessage = event.item.text;
      }
      return;
    }

    if (event.type === "turn.completed") {
      const usage = event.usage
        ? `tokens(in=${event.usage.input_tokens}, out=${event.usage.output_tokens})`
        : "turn completed";
      onEvent?.({ kind: "usage", text: usage });
      return;
    }

    if (event.type === "error" || event.type === "turn.failed") {
      onEvent?.({ kind: "error", text: JSON.stringify(event) });
      return;
    }
  }

  const exitCode = await new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("close", resolve);
  });

  if (exitCode !== 0) {
    throw new Error(`codex exited with code ${exitCode}. ${stderrText.trim()}`);
  }
  if (!lastAgentMessage) {
    throw new Error("No agent_message returned by codex.");
  }

  return {
    threadId: resolvedThreadId,
    lastAgentMessage,
  };
}
