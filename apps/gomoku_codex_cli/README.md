# Dual Codex CLI Gomoku (Python)

Two Codex CLI worker threads play Gomoku against each other through MCP function calling.

## Features

- Two independent Codex CLI threads (`B` and `W`) take turns automatically.
- GUI board visualization via `tkinter`.
- MCP tools are the only board/move interface for the model:
  - `get_board_state`
  - `list_legal_moves`
  - `place_stone`
  - `get_memory`
  - `remember`
- Persistent memory store for both agents (`runtime/memory.json`).
- Trace panel showing Codex JSON events (reasoning/tool/assistant/system).
- Model defaults to `gpt-5.3-codex`.

## Prerequisites

1. Python 3.10+
2. Codex CLI installed and authenticated
3. Environment variable for API key or logged-in Codex session

## Setup

```bash
cd apps/gomoku_codex_cli
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Or from repo root:

```bash
bash restart.sh
```

If your GUI session cannot find `codex` in PATH, set it explicitly:

```bash
CODEX_BIN="$(which codex)" bash restart.sh
```

Optional arguments:

```bash
python main.py --board-size 15 --model gpt-5.3-codex --turn-timeout 180
```

## Notes

- Board coordinates are 0-indexed inside MCP tool calls.
- If a Codex turn does not produce a valid move, the coordinator applies one random fallback move to keep the game progressing.
- Runtime files:
  - `apps/gomoku_codex_cli/runtime/state.json`
  - `apps/gomoku_codex_cli/runtime/memory.json`
