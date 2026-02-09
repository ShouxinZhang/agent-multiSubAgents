from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from forum.web_app import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Human Thinking Forum - Codex Multi-Agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--model", default="gpt-5.3-codex")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--turn-timeout", type=int, default=180)
    parser.add_argument("--runtime-dir", default="apps/human_thinking_forum_codex_cli/runtime")
    parser.add_argument("--config", default="apps/human_thinking_forum_codex_cli/config/agents.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace_root = Path(__file__).resolve().parents[2]

    app = create_app(
        workspace_root=workspace_root,
        runtime_dir=workspace_root / args.runtime_dir,
        config_path=workspace_root / args.config,
        codex_bin=args.codex_bin,
        python_bin=args.python_bin,
        default_model=args.model,
        turn_timeout=args.turn_timeout,
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
