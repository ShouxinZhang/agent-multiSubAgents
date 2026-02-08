import { spawn } from "node:child_process";
import process from "node:process";
import { fileURLToPath } from "node:url";

const requestedBackend = process.argv[2];
const backend = "codex-cli";
const port = Number(process.env.SELFTEST_PORT || 8800 + Math.floor(Math.random() * 300));
const timeoutMs = Number(process.env.SELFTEST_TIMEOUT_MS || 300000);
const demoRoot = fileURLToPath(new URL("..", import.meta.url));

if (requestedBackend && requestedBackend !== backend) {
  console.warn(`[selftest] backend "${requestedBackend}" is ignored, forcing "${backend}".`);
}

const server = spawn("node", ["server.mjs"], {
  cwd: demoRoot,
  env: {
    ...process.env,
    PORT: String(port),
    GOMOKU_BACKEND: backend,
    GOMOKU_GAMES: "1",
    GOMOKU_TURN_DELAY_MS: "0",
  },
  stdio: ["ignore", "pipe", "pipe"],
});

server.stdout.setEncoding("utf8");
server.stderr.setEncoding("utf8");
server.stdout.on("data", (d) => process.stdout.write(`[server] ${d}`));
server.stderr.on("data", (d) => process.stderr.write(`[server:err] ${d}`));

const abortController = new AbortController();
let ssePromise = null;

try {
  await waitForServer(`http://localhost:${port}/api/config`, 20000);
  ssePromise = waitForMatchResult(`http://localhost:${port}/events`, abortController.signal, timeoutMs);

  const startRes = await fetch(`http://localhost:${port}/api/start`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      backend,
      games: 1,
      turnDelayMs: 0,
      model: "gpt-5.3-codex",
    }),
  });
  if (!startRes.ok) {
    throw new Error(`start failed: HTTP ${startRes.status}`);
  }

  const result = await ssePromise;
  console.log("[selftest] match result:", JSON.stringify(result));
  process.exitCode = 0;
} catch (error) {
  console.error("[selftest] failed:", error.message);
  process.exitCode = 1;
} finally {
  abortController.abort();
  if (ssePromise) {
    await ssePromise.catch(() => {});
  }
  await shutdown(server);
}

async function waitForServer(url, maxMs) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // ignore
    }
    await sleep(300);
  }
  throw new Error("server did not start in time");
}

async function waitForMatchResult(url, signal, timeoutMs) {
  const startedAt = Date.now();
  const response = await fetch(url, {
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`events stream open failed: HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf8");
  let buffer = "";
  let latest = null;

  while (Date.now() - startedAt < timeoutMs) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const dataLine = chunk
        .split(/\r?\n/)
        .map((x) => x.trim())
        .find((x) => x.startsWith("data: "));
      if (!dataLine) continue;
      const payload = JSON.parse(dataLine.slice(6));
      latest = payload;
      if (payload.type === "move_applied") {
        console.log(
          `[selftest] move #${payload.moveIndex} ${payload.player}(${payload.side}) -> (${payload.row},${payload.col})`
        );
      }
      if (payload.type === "game_finished") {
        console.log(
          `[selftest] game ${payload.gameNo} finished: ${payload.draw ? "draw" : `winner=${payload.winner}`}`
        );
      }
      if (payload.type === "match_error") {
        throw new Error(`match_error: ${payload.message}`);
      }
      if (payload.type === "match_finished") {
        return payload.result;
      }
    }
  }

  if (signal.aborted) {
    throw new Error("match stream aborted");
  }
  throw new Error(`match timeout or stream ended. latest=${JSON.stringify(latest)}`);
}

async function shutdown(child) {
  if (child.killed) return;
  child.kill("SIGTERM");
  await Promise.race([onceExit(child), sleep(3000)]);
  if (!child.killed) {
    child.kill("SIGKILL");
  }
}

function onceExit(child) {
  return new Promise((resolve) => {
    child.once("exit", resolve);
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
