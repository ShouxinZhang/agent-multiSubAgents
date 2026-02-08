from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gomoku.gui import GomokuApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dual Codex CLI Gomoku")
    parser.add_argument("--board-size", type=int, default=15)
    parser.add_argument("--model", default="gpt-5.3-codex")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--turn-timeout", type=int, default=180)
    parser.add_argument("--runtime-dir", default="apps/gomoku_codex_cli/runtime")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = Path(__file__).resolve().parents[2]
    app = GomokuApp(
        workspace=workspace,
        runtime_dir=workspace / args.runtime_dir,
        board_size=args.board_size,
        model=args.model,
        codex_bin=args.codex_bin,
        python_bin=args.python_bin,
        timeout_sec=args.turn_timeout,
    )
    app.run()


if __name__ == "__main__":
    main()
