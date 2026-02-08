import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import http from "node:http";
import { fileURLToPath } from "node:url";
import { LiveMatchRunner } from "./live-match.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WEB_REACT_DIR = path.join(__dirname, "web-react");
const WEB_REACT_DIST_DIR = path.join(WEB_REACT_DIR, "dist");

const PORT = Number(process.env.PORT || 8787);
const DEFAULT_MODEL = process.env.GOMOKU_MODEL || "gpt-5.3-codex";
const DEFAULT_BACKEND = "codex-cli";
const DEFAULT_GAMES = Number(process.env.GOMOKU_GAMES || 1);
const DEFAULT_TURN_DELAY_MS = Number(process.env.GOMOKU_TURN_DELAY_MS || 220);
const WORKSPACE_ROOT = path.resolve(__dirname, "..", "..");

const clients = new Set();
let isMatchRunning = false;
let eventCounter = 0;
const codexVersion = detectCodexVersion();

function detectCodexVersion() {
  const result = spawnSync("codex", ["--version"], { encoding: "utf8" });
  if (result.status === 0) return result.stdout.trim();
  return null;
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function broadcast(payload) {
  const msg = JSON.stringify({
    eventId: ++eventCounter,
    ts: new Date().toISOString(),
    ...payload,
  });
  for (const client of clients) {
    client.write(`data: ${msg}\n\n`);
  }
}

function serveStatic(res, filePath) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  const ext = path.extname(filePath);
  const contentType =
    {
      ".html": "text/html; charset=utf-8",
      ".js": "application/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".json": "application/json; charset=utf-8",
    }[ext] || "text/plain; charset=utf-8";

  res.writeHead(200, { "Content-Type": contentType });
  fs.createReadStream(filePath).pipe(res);
}

function isDistReady() {
  return fs.existsSync(path.join(WEB_REACT_DIST_DIR, "index.html"));
}

function resolveDistAsset(urlPath) {
  const normalized = decodeURIComponent(urlPath).replace(/^\/+/, "");
  const candidate = path.join(WEB_REACT_DIST_DIR, normalized);
  if (!candidate.startsWith(WEB_REACT_DIST_DIR)) return null;
  return candidate;
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (chunks.length === 0) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    return {};
  }
}

async function startMatch(config = {}) {
  if (isMatchRunning) {
    throw new Error("A match is already running.");
  }
  isMatchRunning = true;
  const model = config.model || DEFAULT_MODEL;
  const backend = DEFAULT_BACKEND;
  const games = Number(config.games || DEFAULT_GAMES);
  const turnDelayMs = Number(config.turnDelayMs ?? DEFAULT_TURN_DELAY_MS);

  const runner = new LiveMatchRunner({
    model,
    backend,
    games,
    turnDelayMs,
    workspaceRoot: WORKSPACE_ROOT,
  });

  broadcast({
    type: "server_status",
    running: true,
    model,
    backend,
    games,
  });

  try {
    await runner.run((evt) => broadcast(evt));
  } catch (error) {
    broadcast({
      type: "match_error",
      message: error.message,
    });
  } finally {
    isMatchRunning = false;
    broadcast({
      type: "server_status",
      running: false,
    });
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/events") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    });
    res.write(`data: ${JSON.stringify({ type: "hello", running: isMatchRunning, codexVersion, model: DEFAULT_MODEL })}\n\n`);

    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/config") {
    sendJson(res, 200, {
      ok: true,
      running: isMatchRunning,
      codexVersion,
      defaults: {
        model: DEFAULT_MODEL,
        backend: DEFAULT_BACKEND,
        games: DEFAULT_GAMES,
        turnDelayMs: DEFAULT_TURN_DELAY_MS,
      },
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/start") {
    const body = await readJsonBody(req);
    if (isMatchRunning) {
      sendJson(res, 409, { ok: false, message: "A match is already running." });
      return;
    }

    sendJson(res, 202, { ok: true, message: "Match started." });
    void startMatch(body);
    return;
  }

  if (req.method === "GET" && url.pathname === "/") {
    if (isDistReady()) {
      serveStatic(res, path.join(WEB_REACT_DIST_DIR, "index.html"));
      return;
    }

    res.writeHead(503, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("React build is missing. Run: npm run build:frontend");
    return;
  }

  if (req.method === "GET" && isDistReady()) {
    const distAsset = resolveDistAsset(url.pathname);
    if (distAsset && fs.existsSync(distAsset) && fs.statSync(distAsset).isFile()) {
      serveStatic(res, distAsset);
      return;
    }

    // SPA fallback for React Router / deep links.
    serveStatic(res, path.join(WEB_REACT_DIST_DIR, "index.html"));
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

server.listen(PORT, () => {
  console.log(`Gomoku live server on http://localhost:${PORT}`);
  console.log(`Default backend=${DEFAULT_BACKEND}, model=${DEFAULT_MODEL}`);
  console.log(`React dist: ${isDistReady() ? "ready" : "missing (run: npm run build:frontend)"}`);
  if (!codexVersion) {
    console.log("Warning: codex CLI not found in PATH.");
  } else {
    console.log(`Detected ${codexVersion}`);
  }
});
