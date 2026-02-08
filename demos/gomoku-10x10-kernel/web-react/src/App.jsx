import { useCallback, useEffect, useMemo, useState } from "react";

const BOARD_SIZE = 10;

function newBoard() {
  return Array.from({ length: BOARD_SIZE }, () => Array(BOARD_SIZE).fill("."));
}

function nowText(ts) {
  if (!ts) return "--:--:--";
  try {
    return new Date(ts).toLocaleTimeString();
  } catch {
    return "--:--:--";
  }
}

function appendLog(setter, max = 200) {
  return (entry) => {
    setter((prev) => {
      const next = [...prev, entry];
      return next.length > max ? next.slice(next.length - max) : next;
    });
  };
}

export function App() {
  const [board, setBoard] = useState(newBoard());
  const [lastMove, setLastMove] = useState(null);
  const [running, setRunning] = useState(false);
  const backend = "codex-cli";
  const [model, setModel] = useState("gpt-5.3-codex");
  const [games, setGames] = useState(1);
  const [turnDelayMs, setTurnDelayMs] = useState(220);
  const [codexVersion, setCodexVersion] = useState("");
  const [gameText, setGameText] = useState("No game running");
  const [score, setScore] = useState({ alphaWins: 0, betaWins: 0, draws: 0 });

  const [alphaLogs, setAlphaLogs] = useState([]);
  const [betaLogs, setBetaLogs] = useState([]);
  const [timeline, setTimeline] = useState([]);

  const pushAlpha = useMemo(() => appendLog(setAlphaLogs, 240), []);
  const pushBeta = useMemo(() => appendLog(setBetaLogs, 240), []);
  const pushTimeline = useMemo(() => appendLog(setTimeline, 300), []);

  const handleEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "hello":
          setRunning(Boolean(event.running));
          if (event.codexVersion) setCodexVersion(event.codexVersion);
          break;
        case "server_status":
          setRunning(Boolean(event.running));
          break;
        case "match_started":
          setScore({ alphaWins: 0, betaWins: 0, draws: 0 });
          pushTimeline({
            tag: "match",
            text: `${nowText(event.ts)} started | backend=${event.backend} | model=${event.model}`,
            ts: event.ts,
          });
          break;
        case "game_started":
          setBoard(event.board);
          setLastMove(null);
          setGameText(`Game ${event.gameNo}: B=${event.black}, W=${event.white}`);
          pushTimeline({ tag: "game", text: `${nowText(event.ts)} game ${event.gameNo} started`, ts: event.ts });
          break;
        case "turn_started":
          pushTimeline({
            tag: "turn",
            text: `${nowText(event.ts)} #${event.moveIndex} ${event.player}(${event.side}) thinking`,
            ts: event.ts,
          });
          break;
        case "agent_event": {
          const line = {
            tag: event.kind,
            text: `${nowText(event.ts)} ${event.text || ""}`,
            ts: event.ts,
          };
          if (event.player === "alpha") pushAlpha(line);
          if (event.player === "beta") pushBeta(line);
          break;
        }
        case "move_applied":
          setBoard(event.board);
          setLastMove({ row: event.row, col: event.col });
          pushTimeline({
            tag: "move",
            text: `${nowText(event.ts)} #${event.moveIndex} ${event.player} -> (${event.row},${event.col})`,
            ts: event.ts,
          });
          break;
        case "game_finished":
          setScore((prev) => {
            const next = { ...prev };
            if (event.draw) next.draws += 1;
            else if (event.winner === "alpha") next.alphaWins += 1;
            else if (event.winner === "beta") next.betaWins += 1;
            return next;
          });
          pushTimeline({
            tag: "result",
            text: `${nowText(event.ts)} game ${event.gameNo} ${event.draw ? "draw" : `winner=${event.winner}`}`,
            ts: event.ts,
          });
          break;
        case "match_finished":
          setScore(event.result);
          setGameText("Match finished");
          pushTimeline({
            tag: "match",
            text: `${nowText(event.ts)} match finished`,
            ts: event.ts,
          });
          break;
        case "match_error":
          pushTimeline({
            tag: "error",
            text: `${nowText(event.ts)} ${event.message}`,
            ts: event.ts,
          });
          break;
        default:
          break;
      }
    },
    [pushAlpha, pushBeta, pushTimeline]
  );

  useEffect(() => {
    let alive = true;
    fetch("/api/config")
      .then((r) => r.json())
      .then((data) => {
        if (!alive || !data?.ok) return;
        setRunning(Boolean(data.running));
        if (data.codexVersion) setCodexVersion(data.codexVersion);
        if (data.defaults) {
          setModel(data.defaults.model);
          setGames(data.defaults.games);
          setTurnDelayMs(data.defaults.turnDelayMs);
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const es = new EventSource("/events");
    es.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      handleEvent(event);
    };
    es.onerror = () => {
      pushTimeline({ tag: "stream", text: "SSE disconnected, retrying...", ts: new Date().toISOString() });
    };
    return () => es.close();
  }, [handleEvent, pushTimeline]);

  async function startMatch() {
    if (running) return;
    setAlphaLogs([]);
    setBetaLogs([]);
    setTimeline([]);
    await fetch("/api/start", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        backend,
        model,
        games: Number(games),
        turnDelayMs: Number(turnDelayMs),
      }),
    });
  }

  return (
    <div className="page">
      <div className="bg bg-a" />
      <div className="bg bg-b" />

      <main className="layout">
        <section className="panel board-panel">
          <h1>Gomoku 10x10 Live</h1>
          <p className="subtitle">React UI + Codex CLI backend + 实时思考上下文</p>
          <div className="board">
            {board.map((row, rowIdx) =>
              row.map((cell, colIdx) => {
                const last = lastMove && lastMove.row === rowIdx && lastMove.col === colIdx;
                return (
                  <div key={`${rowIdx}-${colIdx}`} className={`cell ${last ? "last" : ""}`}>
                    {cell === "B" && <i className="stone black" />}
                    {cell === "W" && <i className="stone white" />}
                  </div>
                );
              })
            )}
          </div>
        </section>

        <section className="panel control-panel">
          <h2>控制台</h2>
          <label>
            Backend
            <input value={backend} readOnly disabled />
          </label>
          <label>
            Model
            <input value={model} onChange={(e) => setModel(e.target.value)} disabled={running} />
          </label>
          <label>
            Games
            <input
              type="number"
              min={1}
              max={9}
              value={games}
              onChange={(e) => setGames(Number(e.target.value || 1))}
              disabled={running}
            />
          </label>
          <label>
            Turn Delay (ms)
            <input
              type="number"
              min={0}
              max={3000}
              value={turnDelayMs}
              onChange={(e) => setTurnDelayMs(Number(e.target.value || 0))}
              disabled={running}
            />
          </label>

          <button type="button" onClick={startMatch} disabled={running}>
            {running ? "Running..." : "Start Match"}
          </button>

          <div className="server-info">
            Server: {running ? "running" : "idle"}
            {codexVersion ? ` | ${codexVersion}` : ""}
          </div>

          <div className="score">
            <div className="score-main">
              alpha {score.alphaWins} : beta {score.betaWins} (draw {score.draws})
            </div>
            <div className="score-sub">{gameText}</div>
          </div>
        </section>

        <section className="panel logs-panel">
          <h2>实时模型上下文</h2>
          <div className="log-grid">
            <LogBox title="Alpha Thinking" logs={alphaLogs} />
            <LogBox title="Beta Thinking" logs={betaLogs} />
          </div>
          <LogBox title="System Timeline" logs={timeline} className="timeline" />
        </section>
      </main>
    </div>
  );
}

function LogBox({ title, logs, className = "" }) {
  return (
    <div>
      <h3>{title}</h3>
      <div className={`log ${className}`}>
        {logs.map((l, idx) => (
          <div className="entry" key={`${title}-${idx}-${l.ts}`}>
            <span className="tag">[{l.tag}]</span> {l.text}
          </div>
        ))}
      </div>
    </div>
  );
}
