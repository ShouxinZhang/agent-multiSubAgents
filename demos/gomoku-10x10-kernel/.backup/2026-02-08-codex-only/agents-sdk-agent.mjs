import { Agent, MemorySession, run } from "@openai/agents";
import { z } from "zod";
import { SimpleHeuristicAgent } from "./agents.mjs";

const MoveSchema = z.object({
  row: z.number().int().min(0).max(9),
  col: z.number().int().min(0).max(9),
  rationale: z.string().min(1).max(120),
  confidence: z.number().min(0).max(1),
});

export class AgentsSdkAgent {
  constructor({ name, side, memoryStore, model }) {
    this.name = name;
    this.side = side;
    this.memoryStore = memoryStore;
    this.model = model;
    this.session = new MemorySession();
    this.fallback = new SimpleHeuristicAgent(name, side, memoryStore);
    this.agent = new Agent({
      name: `gomoku-${name}`,
      model,
      instructions: [
        "You are a Gomoku player in a 10x10 connect-5 game.",
        "Think tactically: immediate win first, immediate block second, then strongest shape.",
        "Return only the structured output. Keep rationale concise and practical.",
      ].join(" "),
      outputType: MoveSchema,
    });
  }

  async chooseMove(context, onEvent) {
    if (!process.env.OPENAI_API_KEY) {
      onEvent?.({
        agent: this.name,
        side: this.side,
        kind: "error",
        text: "OPENAI_API_KEY not set, fallback to heuristic.",
      });
      return this.fallback.chooseMove(context);
    }

    const prompt = buildPrompt({
      ...context,
      selfName: this.name,
      side: this.side,
      selfProfile: this.memoryStore.getProfile(this.name),
    });

    try {
      const result = await run(this.agent, prompt, {
        stream: true,
        session: this.session,
        maxTurns: 4,
      });

      for await (const event of result) {
        emitStreamEvent(event, onEvent, this.name, this.side);
      }
      await result.completed;

      const parsed = MoveSchema.safeParse(result.finalOutput);
      if (!parsed.success) {
        onEvent?.({
          agent: this.name,
          side: this.side,
          kind: "error",
          text: "Agents SDK returned invalid structured output, fallback to heuristic.",
        });
        return this.fallback.chooseMove(context);
      }

      const move = parsed.data;
      const legal = new Set(context.legalMoves.map(([row, col]) => `${row},${col}`));
      if (!legal.has(`${move.row},${move.col}`)) {
        onEvent?.({
          agent: this.name,
          side: this.side,
          kind: "error",
          text: `Agents SDK returned illegal move (${move.row},${move.col}), fallback to heuristic.`,
        });
        return this.fallback.chooseMove(context);
      }

      return {
        row: move.row,
        col: move.col,
        intent: move.rationale,
        confidence: move.confidence,
      };
    } catch (error) {
      onEvent?.({
        agent: this.name,
        side: this.side,
        kind: "error",
        text: `Agents SDK run failed, fallback to heuristic: ${error.message}`,
      });
      return this.fallback.chooseMove(context);
    }
  }
}

function emitStreamEvent(event, onEvent, name, side) {
  if (!onEvent) return;

  if (event.type === "run_item_stream_event") {
    if (event.name === "reasoning_item_created") {
      const text = extractReasoningText(event.item?.rawItem);
      if (text) {
        onEvent({
          agent: name,
          side,
          kind: "reasoning",
          text,
        });
      }
      return;
    }

    if (event.name === "message_output_created") {
      const text = extractMessageText(event.item?.rawItem);
      if (text) {
        onEvent({
          agent: name,
          side,
          kind: "agent_message",
          text,
        });
      }
      return;
    }

    if (event.name === "tool_called" || event.name === "tool_output") {
      onEvent({
        agent: name,
        side,
        kind: event.name,
        text: JSON.stringify(event.item?.rawItem ?? {}),
      });
    }
    return;
  }

  if (event.type === "raw_model_stream_event") {
    const t = event.data?.type;
    if (typeof t === "string" && t.includes("response.completed")) {
      onEvent({
        agent: name,
        side,
        kind: "usage",
        text: "response completed",
      });
    }
  }
}

function extractReasoningText(rawItem) {
  if (!rawItem || rawItem.type !== "reasoning") return "";
  if (Array.isArray(rawItem.rawContent) && rawItem.rawContent.length > 0) {
    return rawItem.rawContent
      .map((x) => x?.text)
      .filter(Boolean)
      .join(" ")
      .trim();
  }
  if (Array.isArray(rawItem.content) && rawItem.content.length > 0) {
    return rawItem.content
      .map((x) => x?.text)
      .filter(Boolean)
      .join(" ")
      .trim();
  }
  return "";
}

function extractMessageText(rawItem) {
  if (!rawItem) return "";
  const isAssistantMessage = rawItem.type === "message" || rawItem.role === "assistant";
  if (!isAssistantMessage) return "";
  if (!Array.isArray(rawItem.content)) return "";
  return rawItem.content
    .filter((x) => x.type === "output_text")
    .map((x) => x.text)
    .join(" ")
    .trim();
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
    `You are ${selfName}, side ${side}.`,
    "Task: choose one legal move for this turn.",
    "Decision policy: win now > block opponent immediate win > best shape pressure.",
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
