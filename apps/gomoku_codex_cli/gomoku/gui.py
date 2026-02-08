from __future__ import annotations

import queue
import random
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from .codex_agent import CodexAgent
from .engine import BLACK, EMPTY, WHITE, other_player
from .memory_store import MemoryStore
from .state_store import GameStateStore


class AgentWorker(threading.Thread):
    def __init__(self, player: str, coordinator: "BattleCoordinator", agent: CodexAgent):
        super().__init__(daemon=True)
        self.player = player
        self.coordinator = coordinator
        self.agent = agent

    def run(self) -> None:
        while True:
            with self.coordinator.turn_condition:
                self.coordinator.turn_condition.wait_for(
                    lambda: self.coordinator.stop_event.is_set() or self.coordinator.next_player == self.player
                )
                if self.coordinator.stop_event.is_set():
                    return

            state_before = self.coordinator.state_store.load()
            if state_before.get("winner"):
                self.coordinator.stop(reason=f"game already finished: {state_before['winner']}")
                return
            if state_before.get("current_player") != self.player:
                continue

            self.coordinator.emit_status(f"{self.player} thinking...")
            move_count_before = int(state_before.get("move_count", 0))

            result = self.agent.run_turn()
            state_after = self.coordinator.state_store.load()

            moved = (
                int(state_after.get("move_count", 0)) > move_count_before
                and bool(state_after.get("history"))
                and state_after["history"][-1].get("player") == self.player
            )

            if not moved and not state_after.get("winner"):
                fallback = self.coordinator.apply_fallback_move(player=self.player)
                moved = bool(fallback.get("success"))
                if moved:
                    self.coordinator.emit_log(
                        self.player,
                        "system",
                        f"Codex did not place a valid move; fallback move used at ({fallback['row']}, {fallback['col']}).",
                    )
                else:
                    self.coordinator.emit_log(
                        self.player,
                        "system",
                        f"No valid move produced: {fallback.get('error', 'unknown error')}",
                    )

            self.coordinator.on_turn_finished(self.player, result.summary)


class BattleCoordinator:
    def __init__(
        self,
        *,
        workspace: Path,
        runtime_dir: Path,
        board_size: int,
        model: str,
        codex_bin: str,
        python_bin: str,
        timeout_sec: int,
        ui_queue: "queue.Queue[dict[str, Any]]",
    ):
        self.workspace = Path(workspace)
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.board_size = board_size
        self.model = model
        self.codex_bin = codex_bin
        self.python_bin = python_bin
        self.timeout_sec = timeout_sec
        self.ui_queue = ui_queue

        self.state_path = self.runtime_dir / "state.json"
        self.memory_path = self.runtime_dir / "memory.json"
        self.mcp_script = self.workspace / "apps" / "gomoku_codex_cli" / "gomoku" / "mcp_server.py"

        self.state_store = GameStateStore(self.state_path, board_size=self.board_size)
        self.memory_store = MemoryStore(self.memory_path)

        self.turn_condition = threading.Condition()
        self.stop_event = threading.Event()
        self.next_player = BLACK
        self.workers: dict[str, AgentWorker] = {}

    def emit(self, payload: dict[str, Any]) -> None:
        self.ui_queue.put(payload)

    def emit_status(self, text: str) -> None:
        self.emit({"type": "status", "text": text})

    def emit_log(self, player: str, kind: str, text: str) -> None:
        self.emit({"type": "log", "player": player, "kind": kind, "text": text})

    def emit_state(self) -> None:
        self.emit(
            {
                "type": "state",
                "state": self.state_store.load(),
                "memory": self.memory_store.snapshot(),
            }
        )

    def codex_available(self) -> bool:
        return shutil.which(self.codex_bin) is not None

    def start(self, keep_memory: bool = True) -> None:
        self.stop(reason="restart")
        self.stop_event.clear()
        self.next_player = BLACK

        self.state_store.reset(board_size=self.board_size)
        if not keep_memory:
            self.memory_store.clear()

        self.emit_status(f"match started, model={self.model}")
        self.emit_state()

        self.workers = {}
        for player in (BLACK, WHITE):
            agent = CodexAgent(
                player=player,
                model=self.model,
                codex_bin=self.codex_bin,
                python_bin=self.python_bin,
                workspace=self.workspace,
                mcp_server_script=self.mcp_script,
                state_path=self.state_path,
                memory_path=self.memory_path,
                board_size=self.board_size,
                timeout_sec=self.timeout_sec,
                log_callback=self.emit_log,
            )
            worker = AgentWorker(player=player, coordinator=self, agent=agent)
            worker.start()
            self.workers[player] = worker

        with self.turn_condition:
            self.turn_condition.notify_all()

    def stop(self, reason: str = "manual") -> None:
        self.stop_event.set()
        with self.turn_condition:
            self.turn_condition.notify_all()

        for worker in list(self.workers.values()):
            worker.join(timeout=0.2)
        self.workers.clear()

        self.emit_status(f"stopped: {reason}")
        self.emit_state()

    def reset_board(self) -> None:
        self.stop(reason="reset board")
        self.stop_event.clear()
        self.state_store.reset(board_size=self.board_size)
        self.emit_state()
        self.emit_status("board reset")

    def clear_memory(self) -> None:
        self.memory_store.clear()
        self.emit_state()
        self.emit_status("memory cleared")

    def apply_fallback_move(self, player: str) -> dict[str, Any]:
        legal = self.state_store.legal_moves()
        if not legal:
            return {"success": False, "error": "No legal moves"}

        choice = random.choice(legal)
        return self.state_store.apply_move(
            player=player,
            row=choice["row"],
            col=choice["col"],
            source="fallback_random",
        )

    def on_turn_finished(self, player: str, summary: str) -> None:
        self.emit_log(player, "system", f"turn summary: {summary}")
        if self.stop_event.is_set():
            self.emit_state()
            return

        state = self.state_store.load()
        self.emit_state()

        winner = state.get("winner")
        if winner:
            self.stop(reason=f"winner={winner}")
            return

        with self.turn_condition:
            self.next_player = other_player(player)
            self.turn_condition.notify_all()
        self.emit_status(f"next turn: {self.next_player}")


class GomokuApp:
    def __init__(
        self,
        *,
        workspace: Path,
        runtime_dir: Path,
        board_size: int,
        model: str,
        codex_bin: str,
        python_bin: str,
        timeout_sec: int,
    ):
        self.root = tk.Tk()
        self.root.title("Dual Codex CLI Gomoku")
        self.root.geometry("1400x860")

        self.ui_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self.coordinator = BattleCoordinator(
            workspace=workspace,
            runtime_dir=runtime_dir,
            board_size=board_size,
            model=model,
            codex_bin=codex_bin,
            python_bin=python_bin,
            timeout_sec=timeout_sec,
            ui_queue=self.ui_queue,
        )

        self.board_size = board_size
        self.canvas_size = 760
        self.margin = 30
        self.cell = (self.canvas_size - 2 * self.margin) / (self.board_size - 1)

        self.status_var = tk.StringVar(value="idle")
        self.info_var = tk.StringVar(value=f"model={model}, board={board_size}x{board_size}")

        self._build_ui()
        self.coordinator.emit_state()
        self._poll_queue()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        right = ttk.Frame(container)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left, width=self.canvas_size, height=self.canvas_size, bg="#d8b26e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=False)

        controls = ttk.Frame(right)
        controls.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(controls, text="Start", command=self._start_match).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Stop", command=self._stop_match).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Reset Board", command=self._reset_board).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Clear Memory", command=self._clear_memory).pack(side=tk.LEFT, padx=4)

        ttk.Label(right, textvariable=self.status_var).pack(anchor=tk.W)
        ttk.Label(right, textvariable=self.info_var).pack(anchor=tk.W, pady=(0, 6))

        log_frame = ttk.LabelFrame(right, text="Codex Trace")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_black = ScrolledText(log_frame, height=18, wrap=tk.WORD)
        self.log_black.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.log_white = ScrolledText(log_frame, height=18, wrap=tk.WORD)
        self.log_white.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        memory_frame = ttk.LabelFrame(right, text="Memory")
        memory_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.memory_black = ScrolledText(memory_frame, height=8, wrap=tk.WORD)
        self.memory_black.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.memory_white = ScrolledText(memory_frame, height=8, wrap=tk.WORD)
        self.memory_white.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _start_match(self) -> None:
        if not self.coordinator.codex_available():
            messagebox.showerror("codex CLI missing", f"Cannot find '{self.coordinator.codex_bin}' in PATH.")
            return
        self.coordinator.start(keep_memory=True)

    def _stop_match(self) -> None:
        self.coordinator.stop(reason="manual stop")

    def _reset_board(self) -> None:
        self.coordinator.reset_board()

    def _clear_memory(self) -> None:
        self.coordinator.clear_memory()

    def _append_log(self, player: str, kind: str, text: str) -> None:
        target = self.log_black if player == BLACK else self.log_white
        target.insert(tk.END, f"[{kind}] {text}\n")
        target.see(tk.END)

    def _render_memory(self, memory: dict[str, list[dict[str, Any]]]) -> None:
        for player, widget in ((BLACK, self.memory_black), (WHITE, self.memory_white)):
            widget.delete("1.0", tk.END)
            for item in memory.get(player, []):
                line = f"{item.get('ts', '')} [{item.get('kind', '')}] {item.get('note', '')}\n"
                widget.insert(tk.END, line)

    def _render_board(self, state: dict[str, Any]) -> None:
        board_rows = state.get("board", [])
        size = int(state.get("board_size", self.board_size))
        if size != self.board_size:
            self.board_size = size
            self.cell = (self.canvas_size - 2 * self.margin) / (self.board_size - 1)

        self.canvas.delete("all")

        for idx in range(size):
            offset = self.margin + idx * self.cell
            self.canvas.create_line(self.margin, offset, self.canvas_size - self.margin, offset, fill="#3d2b1f")
            self.canvas.create_line(offset, self.margin, offset, self.canvas_size - self.margin, fill="#3d2b1f")

        for row in range(size):
            for col in range(size):
                cell = board_rows[row][col]
                if cell == EMPTY:
                    continue
                x = self.margin + col * self.cell
                y = self.margin + row * self.cell
                radius = self.cell * 0.4
                fill = "#111111" if cell == BLACK else "#f7f7f7"
                outline = "#ffffff" if cell == BLACK else "#111111"
                self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill, outline=outline, width=1.5)

        history = state.get("history", [])
        if history:
            last = history[-1]
            x = self.margin + last["col"] * self.cell
            y = self.margin + last["row"] * self.cell
            marker = self.cell * 0.15
            self.canvas.create_oval(x - marker, y - marker, x + marker, y + marker, outline="#d32f2f", width=2)

        winner = state.get("winner")
        if winner:
            self.status_var.set(f"winner: {winner}")
        else:
            self.status_var.set(f"current_player: {state.get('current_player')} | moves: {state.get('move_count')}")

    def _poll_queue(self) -> None:
        try:
            while True:
                event = self.ui_queue.get_nowait()
                event_type = event.get("type")
                if event_type == "status":
                    self.status_var.set(event.get("text", ""))
                elif event_type == "log":
                    self._append_log(event.get("player", "B"), event.get("kind", "log"), event.get("text", ""))
                elif event_type == "state":
                    self._render_board(event.get("state", {}))
                    self._render_memory(event.get("memory", {}))
        except queue.Empty:
            pass

        self.root.after(120, self._poll_queue)

    def _on_close(self) -> None:
        self.coordinator.stop(reason="window closed")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
