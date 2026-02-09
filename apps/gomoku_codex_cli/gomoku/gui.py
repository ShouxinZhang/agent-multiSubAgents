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
from .turn_event_store import TurnEventStore


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
        self.turn_event_path = self.runtime_dir / "turn_events.jsonl"
        self.mcp_script = self.workspace / "apps" / "gomoku_codex_cli" / "gomoku" / "mcp_server.py"

        self.state_store = GameStateStore(self.state_path, board_size=self.board_size)
        self.memory_store = MemoryStore(self.memory_path)
        self.turn_event_store = TurnEventStore(self.turn_event_path)

        self.turn_condition = threading.Condition()
        self.stop_event = threading.Event()
        self.next_player = BLACK
        self.workers: dict[str, AgentWorker] = {}
        self.pending_turn_events: dict[str, list[dict[str, Any]]] = {BLACK: [], WHITE: []}
        self.next_turn_event_id = 1

    def emit(self, payload: dict[str, Any]) -> None:
        self.ui_queue.put(payload)

    def emit_status(self, text: str) -> None:
        self.emit({"type": "status", "text": text})

    def emit_log(self, player: str, kind: str, text: str) -> None:
        player = player if player in (BLACK, WHITE) else BLACK
        self.pending_turn_events[player].append({"kind": kind, "text": text})
        self.emit({"type": "log", "player": player, "kind": kind, "text": text})

    def emit_state(self) -> None:
        self.emit(
            {
                "type": "state",
                "state": self.state_store.load(),
                "memory": self.memory_store.snapshot(),
                "events": self.turn_event_store.snapshot(),
            }
        )

    def codex_available(self) -> bool:
        return shutil.which(self.codex_bin) is not None

    def start(self, keep_memory: bool = True) -> None:
        self.stop(reason="restart")
        self.stop_event.clear()
        self.next_player = BLACK

        self.state_store.reset(board_size=self.board_size)
        self.turn_event_store.clear()
        self.pending_turn_events = {BLACK: [], WHITE: []}
        self.next_turn_event_id = 1
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
        self._flush_all_pending_turn_events()

        self.emit_status(f"stopped: {reason}")
        self.emit_state()

    def reset_board(self) -> None:
        self.stop(reason="reset board")
        self.stop_event.clear()
        self.state_store.reset(board_size=self.board_size)
        self.turn_event_store.clear()
        self.pending_turn_events = {BLACK: [], WHITE: []}
        self.next_turn_event_id = 1
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
        state = self.state_store.load()
        seq = self._resolve_turn_seq(player=player, state=state)
        self._flush_pending_turn_events(player=player, seq=seq)
        if self.stop_event.is_set():
            self.emit_state()
            return

        self.emit_state()

        winner = state.get("winner")
        if winner:
            self.stop(reason=f"winner={winner}")
            return

        with self.turn_condition:
            self.next_player = other_player(player)
            self.turn_condition.notify_all()
        self.emit_status(f"next turn: {self.next_player}")

    def _resolve_turn_seq(self, *, player: str, state: dict[str, Any]) -> int | None:
        history = state.get("history", [])
        if not history:
            return None
        last = history[-1]
        if str(last.get("player", "")).upper() != player:
            return None
        try:
            return int(last.get("seq"))
        except (TypeError, ValueError):
            return None

    def _flush_pending_turn_events(self, *, player: str, seq: int | None) -> None:
        events = self.pending_turn_events.get(player, [])
        if not events:
            return
        turn_id = self.next_turn_event_id
        self.next_turn_event_id += 1
        self.turn_event_store.append_turn_events(
            turn_id=turn_id,
            player=player,
            seq=seq,
            events=events,
        )
        self.pending_turn_events[player] = []

    def _flush_all_pending_turn_events(self) -> None:
        for player in (BLACK, WHITE):
            self._flush_pending_turn_events(player=player, seq=None)


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
        self.root.geometry("1680x980")

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
        self.canvas_size = 620
        self.margin = 30
        self.cell = (self.canvas_size - 2 * self.margin) / (self.board_size - 1)

        self.runtime_status_var = tk.StringVar(value="idle")
        self.board_status_var = tk.StringVar(value=f"current_player: {BLACK} | moves: 0")
        self.info_var = tk.StringVar(value=f"model={model}, board={board_size}x{board_size}")
        self.replay_status_var = tk.StringVar(value="replay: 0/0 (live)")
        self.playback_speed_var = tk.IntVar(value=650)

        self.latest_state: dict[str, Any] = {}
        self.latest_history: list[dict[str, Any]] = []
        self.replay_index = 0
        self.follow_latest = True
        self.autoplay_running = False
        self.autoplay_job: str | None = None
        self.next_turn_id = 1
        self.player_logs: dict[str, list[dict[str, Any]]] = {BLACK: [], WHITE: []}
        self.turns_by_player: dict[str, list[dict[str, Any]]] = {BLACK: [], WHITE: []}
        self.active_turn: dict[str, dict[str, Any] | None] = {BLACK: None, WHITE: None}
        self.turn_cursor: dict[str, int] = {BLACK: 0, WHITE: 0}
        self.move_to_turn: dict[int, dict[str, Any]] = {}

        self._build_ui()
        self.coordinator.emit_state()
        self._poll_queue()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        controls = ttk.Frame(container)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Button(controls, text="Start", command=self._start_match).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Stop", command=self._stop_match).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Reset Board", command=self._reset_board).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Clear Memory", command=self._clear_memory).pack(side=tk.LEFT, padx=4)

        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(controls, text="|<", width=3, command=self._replay_first).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="<", width=3, command=self._replay_prev).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text=">", width=3, command=self._replay_next).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text=">|", width=3, command=self._replay_last).pack(side=tk.LEFT, padx=2)
        self.play_button = ttk.Button(controls, text="Auto Play", command=self._toggle_autoplay)
        self.play_button.pack(side=tk.LEFT, padx=(8, 2))
        ttk.Label(controls, text="speed(ms)").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Spinbox(controls, from_=200, to=3000, increment=100, textvariable=self.playback_speed_var, width=6).pack(
            side=tk.LEFT, padx=(0, 6)
        )

        status_box = ttk.Frame(controls)
        status_box.pack(side=tk.RIGHT, padx=4)
        ttk.Label(status_box, textvariable=self.replay_status_var).pack(anchor=tk.E)
        ttk.Label(status_box, textvariable=self.runtime_status_var).pack(anchor=tk.E)
        ttk.Label(status_box, textvariable=self.board_status_var).pack(anchor=tk.E)
        ttk.Label(status_box, textvariable=self.info_var).pack(anchor=tk.E)

        body = ttk.Frame(container)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=4)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        left_panel = ttk.LabelFrame(body, text="Agent B")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(0, weight=1)
        self.log_black = ScrolledText(left_panel, wrap=tk.WORD)
        self.log_black.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        center_panel = ttk.Frame(body)
        center_panel.grid(row=0, column=1, sticky="nsew")
        center_panel.columnconfigure(0, weight=1)
        center_panel.rowconfigure(0, weight=3)
        center_panel.rowconfigure(1, weight=2)

        board_frame = ttk.LabelFrame(center_panel, text="Board")
        board_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        board_frame.columnconfigure(0, weight=1)
        board_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(board_frame, width=self.canvas_size, height=self.canvas_size, bg="#d8b26e", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        timeline_panel = ttk.Frame(center_panel)
        timeline_panel.grid(row=1, column=0, sticky="nsew")
        timeline_panel.columnconfigure(0, weight=1)
        timeline_panel.rowconfigure(0, weight=1)
        timeline_panel.rowconfigure(1, weight=1)

        record_frame = ttk.LabelFrame(timeline_panel, text="Turn Records")
        record_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        record_frame.columnconfigure(0, weight=1)
        record_frame.rowconfigure(0, weight=1)
        self.turn_records = ScrolledText(record_frame, wrap=tk.NONE, height=8)
        self.turn_records.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        stream_frame = ttk.LabelFrame(timeline_panel, text="Step Thinking Stream")
        stream_frame.grid(row=1, column=0, sticky="nsew")
        stream_frame.columnconfigure(0, weight=1)
        stream_frame.rowconfigure(0, weight=1)
        self.step_stream = ScrolledText(stream_frame, wrap=tk.WORD, height=10)
        self.step_stream.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        right_panel = ttk.LabelFrame(body, text="Agent W")
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        self.log_white = ScrolledText(right_panel, wrap=tk.WORD)
        self.log_white.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def _start_match(self) -> None:
        if not self.coordinator.codex_available():
            messagebox.showerror("codex CLI missing", f"Cannot find '{self.coordinator.codex_bin}' in PATH.")
            return
        self._stop_autoplay()
        self._reset_replay_data()
        self.coordinator.start(keep_memory=True)

    def _stop_match(self) -> None:
        self._stop_autoplay()
        self.coordinator.stop(reason="manual stop")

    def _reset_board(self) -> None:
        self._stop_autoplay()
        self._reset_replay_data()
        self.coordinator.reset_board()

    def _clear_memory(self) -> None:
        self.coordinator.clear_memory()

    def _reset_replay_data(self) -> None:
        self.latest_state = {}
        self.latest_history = []
        self.replay_index = 0
        self.follow_latest = True
        self.next_turn_id = 1
        self.player_logs = {BLACK: [], WHITE: []}
        self.turns_by_player = {BLACK: [], WHITE: []}
        self.active_turn = {BLACK: None, WHITE: None}
        self.turn_cursor = {BLACK: 0, WHITE: 0}
        self.move_to_turn = {}
        self._render_from_replay()

    def _append_log(self, player: str, kind: str, text: str) -> None:
        player = player if player in (BLACK, WHITE) else BLACK
        turn = self._ensure_open_turn(player=player)

        entry: dict[str, Any] = {
            "player": player,
            "kind": kind,
            "text": text,
            "seq": turn.get("seq") if turn else None,
            "turn_id": turn.get("id") if turn else None,
        }
        if turn is not None:
            turn["entries"].append(entry)
        self.player_logs[player].append(entry)

        if kind == "system" and text.startswith("turn summary:"):
            self.active_turn[player] = None

        if self.follow_latest:
            self._render_from_replay()

    def _ensure_open_turn(self, player: str) -> dict[str, Any]:
        turn = self.active_turn[player]
        if turn is not None:
            return turn

        turns = self.turns_by_player[player]
        if turns:
            last_turn = turns[-1]
            if last_turn.get("seq") is None:
                self.active_turn[player] = last_turn
                return last_turn

        turn = {
            "id": self.next_turn_id,
            "player": player,
            "seq": None,
            "entries": [],
        }
        self.next_turn_id += 1
        turns.append(turn)
        self.active_turn[player] = turn
        return turn

    def _link_move_to_turn(self, move: dict[str, Any]) -> None:
        player = str(move.get("player", BLACK)).upper()
        if player not in (BLACK, WHITE):
            return

        seq_raw = move.get("seq")
        try:
            seq = int(seq_raw)
        except (TypeError, ValueError):
            seq = len(self.move_to_turn) + 1

        turns = self.turns_by_player[player]
        cursor = self.turn_cursor[player]
        while cursor < len(turns):
            turn = turns[cursor]
            cursor += 1
            if turn.get("seq") is None:
                turn["seq"] = seq
                for entry in turn.get("entries", []):
                    entry["seq"] = seq
                self.move_to_turn[seq] = turn
                self.turn_cursor[player] = cursor
                return

        turn_id = self.next_turn_id
        self.next_turn_id += 1
        fallback_entry = {
            "player": player,
            "kind": "system",
            "text": "(no captured thinking stream for this move)",
            "seq": seq,
            "turn_id": turn_id,
        }
        turn = {
            "id": turn_id,
            "player": player,
            "seq": seq,
            "entries": [fallback_entry],
        }
        turns.append(turn)
        self.player_logs[player].append(fallback_entry)
        self.move_to_turn[seq] = turn
        self.turn_cursor[player] = len(turns)

    def _set_text(self, widget: ScrolledText, text: str, *, stick_to_end: bool = False) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        if stick_to_end:
            widget.see(tk.END)
        widget.configure(state=tk.DISABLED)

    def _rebuild_log_model(self, events: list[dict[str, Any]]) -> None:
        self.next_turn_id = 1
        self.player_logs = {BLACK: [], WHITE: []}
        self.turns_by_player = {BLACK: [], WHITE: []}
        self.active_turn = {BLACK: None, WHITE: None}
        self.turn_cursor = {BLACK: 0, WHITE: 0}
        self.move_to_turn = {}

        turn_lookup: dict[tuple[str, int], dict[str, Any]] = {}
        max_turn_id = 0

        for raw in events:
            if not isinstance(raw, dict):
                continue
            player = str(raw.get("player", BLACK)).upper()
            if player not in (BLACK, WHITE):
                continue
            kind = str(raw.get("kind", "log"))
            text = str(raw.get("text", ""))

            turn_id_raw = raw.get("turn_id")
            try:
                turn_id = int(turn_id_raw)
            except (TypeError, ValueError):
                turn_id = 0
            if turn_id <= 0:
                turn_id = max_turn_id + 1
            max_turn_id = max(max_turn_id, turn_id)

            seq_raw = raw.get("seq")
            try:
                seq: int | None = int(seq_raw) if seq_raw is not None else None
            except (TypeError, ValueError):
                seq = None

            key = (player, turn_id)
            turn = turn_lookup.get(key)
            if turn is None:
                turn = {
                    "id": turn_id,
                    "player": player,
                    "seq": seq,
                    "entries": [],
                }
                turn_lookup[key] = turn
                self.turns_by_player[player].append(turn)
            elif turn.get("seq") is None and seq is not None:
                turn["seq"] = seq

            entry = {
                "player": player,
                "kind": kind,
                "text": text,
                "seq": seq,
                "turn_id": turn_id,
            }
            turn["entries"].append(entry)
            self.player_logs[player].append(entry)
            if seq is not None:
                self.move_to_turn[seq] = turn

        self.turn_cursor = {
            BLACK: len(self.turns_by_player[BLACK]),
            WHITE: len(self.turns_by_player[WHITE]),
        }
        self.next_turn_id = max_turn_id + 1

    def _build_board_snapshot(self, replay_index: int) -> dict[str, Any]:
        size = int(self.latest_state.get("board_size", self.board_size))
        if size != self.board_size:
            self.board_size = size
            self.cell = (self.canvas_size - 2 * self.margin) / (self.board_size - 1)

        board = [[EMPTY for _ in range(size)] for _ in range(size)]
        history = self.latest_history[:replay_index]
        for move in history:
            player = str(move.get("player", EMPTY)).upper()
            row = int(move.get("row", -1))
            col = int(move.get("col", -1))
            if player in (BLACK, WHITE) and 0 <= row < size and 0 <= col < size:
                board[row][col] = player

        current_player = self.latest_state.get("current_player", BLACK)
        if replay_index < len(self.latest_history):
            current_player = self.latest_history[replay_index].get("player", current_player)

        winner = self.latest_state.get("winner") if replay_index == len(self.latest_history) else None
        return {
            "board": board,
            "board_size": size,
            "history": history,
            "current_player": current_player,
            "winner": winner,
            "move_count": replay_index,
        }

    def _render_board(self, state: dict[str, Any]) -> None:
        board_rows = state.get("board", [])
        size = int(state.get("board_size", self.board_size))
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

        winner = state.get("winner", None)
        move_count = int(state.get("move_count", 0))
        if winner:
            self.board_status_var.set(f"winner: {winner} | moves: {move_count}")
        else:
            self.board_status_var.set(f"current_player: {state.get('current_player')} | moves: {move_count}")

    def _render_turn_records(self, replay_index: int) -> None:
        lines: list[str] = []
        for idx, move in enumerate(self.latest_history, start=1):
            prefix = ">>" if idx == replay_index else "  "
            mark = "*" if idx <= replay_index else " "
            player = str(move.get("player", "?"))
            row = move.get("row", "?")
            col = move.get("col", "?")
            source = move.get("source", "unknown")
            lines.append(f"{prefix}{mark} {idx:03d} {player} ({row},{col}) src={source}")
        if not lines:
            lines = ["(no moves yet)"]
        self._set_text(self.turn_records, "\n".join(lines) + "\n", stick_to_end=self.follow_latest)
        if replay_index > 0:
            self.turn_records.see(f"{replay_index}.0")

    def _render_step_stream(self, replay_index: int) -> None:
        if replay_index <= 0 or replay_index > len(self.latest_history):
            self._set_text(self.step_stream, "Step 0: waiting for moves.\n")
            return

        move = self.latest_history[replay_index - 1]
        seq = int(move.get("seq", replay_index))
        player = str(move.get("player", "?"))
        row = move.get("row", "?")
        col = move.get("col", "?")
        source = move.get("source", "unknown")
        lines = [f"Step {seq}: {player} ({row},{col}) src={source}"]
        turn = self.move_to_turn.get(seq)
        if turn:
            for entry in turn.get("entries", []):
                lines.append(f"[{entry.get('kind', 'log')}] {entry.get('text', '')}")
        else:
            lines.append("(thinking stream unavailable)")
        self._set_text(self.step_stream, "\n".join(lines) + "\n")

    def _render_agent_log(self, player: str, widget: ScrolledText, replay_index: int) -> None:
        total = len(self.latest_history)
        lines: list[str] = []
        for entry in self.player_logs.get(player, []):
            seq = entry.get("seq")
            if seq is None:
                if replay_index != total:
                    continue
                seq_label = "live"
            else:
                try:
                    seq_int = int(seq)
                except (TypeError, ValueError):
                    continue
                if seq_int > replay_index:
                    continue
                seq_label = f"{seq_int:03d}"
            lines.append(f"[{seq_label}][{entry.get('kind', 'log')}] {entry.get('text', '')}")
        if not lines:
            lines = ["(no logs)"]
        self._set_text(widget, "\n".join(lines) + "\n", stick_to_end=self.follow_latest and replay_index == total)

    def _render_from_replay(self) -> None:
        total = len(self.latest_history)
        replay_index = max(0, min(self.replay_index, total))
        snapshot = self._build_board_snapshot(replay_index)
        self._render_board(snapshot)
        self._render_turn_records(replay_index)
        self._render_step_stream(replay_index)
        self._render_agent_log(BLACK, self.log_black, replay_index)
        self._render_agent_log(WHITE, self.log_white, replay_index)
        mode = "live" if self.follow_latest and replay_index == total else "replay"
        self.replay_status_var.set(f"replay: {replay_index}/{total} ({mode})")

    def _set_replay_index(self, value: int, *, follow_latest: bool = False) -> None:
        total = len(self.latest_history)
        self.replay_index = max(0, min(value, total))
        self.follow_latest = bool(follow_latest and self.replay_index == total)
        if self.replay_index < total:
            self.follow_latest = False
        self._render_from_replay()

    def _replay_first(self) -> None:
        self._stop_autoplay()
        self._set_replay_index(0, follow_latest=False)

    def _replay_prev(self) -> None:
        self._stop_autoplay()
        self._set_replay_index(self.replay_index - 1, follow_latest=False)

    def _replay_next(self) -> None:
        self._stop_autoplay()
        self._set_replay_index(self.replay_index + 1, follow_latest=False)

    def _replay_last(self) -> None:
        self._stop_autoplay()
        self._set_replay_index(len(self.latest_history), follow_latest=True)

    def _toggle_autoplay(self) -> None:
        if self.autoplay_running:
            self._stop_autoplay()
            return
        if not self.latest_history:
            return
        self.follow_latest = False
        self.autoplay_running = True
        self.play_button.configure(text="Pause")
        self._schedule_autoplay_step()

    def _schedule_autoplay_step(self) -> None:
        delay = max(120, int(self.playback_speed_var.get() or 650))
        self.autoplay_job = self.root.after(delay, self._run_autoplay_step)

    def _run_autoplay_step(self) -> None:
        self.autoplay_job = None
        if not self.autoplay_running:
            return
        total = len(self.latest_history)
        if self.replay_index >= total:
            self._stop_autoplay()
            self._set_replay_index(total, follow_latest=True)
            return
        self._set_replay_index(self.replay_index + 1, follow_latest=False)
        self._schedule_autoplay_step()

    def _stop_autoplay(self) -> None:
        if self.autoplay_job:
            self.root.after_cancel(self.autoplay_job)
            self.autoplay_job = None
        self.autoplay_running = False
        self.play_button.configure(text="Auto Play")

    def _apply_state(self, state: dict[str, Any], events: list[dict[str, Any]] | None = None) -> None:
        previous_history_len = len(self.latest_history)
        history = state.get("history", [])
        if not isinstance(history, list):
            history = []

        if previous_history_len > 0 and not history:
            self._reset_replay_data()

        self.latest_state = state
        self.latest_history = history

        if events is not None:
            self._rebuild_log_model(events)
            for move in history:
                if isinstance(move, dict):
                    seq_raw = move.get("seq")
                    try:
                        seq = int(seq_raw)
                    except (TypeError, ValueError):
                        seq = -1
                    if seq not in self.move_to_turn:
                        self._link_move_to_turn(move)
        elif len(history) > previous_history_len:
            for move in history[previous_history_len:]:
                if isinstance(move, dict):
                    self._link_move_to_turn(move)

        if self.follow_latest:
            self.replay_index = len(self.latest_history)
        else:
            self.replay_index = min(self.replay_index, len(self.latest_history))

        self._render_from_replay()

    def _poll_queue(self) -> None:
        try:
            while True:
                event = self.ui_queue.get_nowait()
                event_type = event.get("type")
                if event_type == "status":
                    self.runtime_status_var.set(event.get("text", ""))
                elif event_type == "log":
                    self._append_log(event.get("player", "B"), event.get("kind", "log"), event.get("text", ""))
                elif event_type == "state":
                    event_items = event.get("events")
                    events = event_items if isinstance(event_items, list) else None
                    self._apply_state(event.get("state", {}), events=events)
        except queue.Empty:
            pass

        self.root.after(120, self._poll_queue)

    def _on_close(self) -> None:
        self._stop_autoplay()
        self.coordinator.stop(reason="window closed")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
