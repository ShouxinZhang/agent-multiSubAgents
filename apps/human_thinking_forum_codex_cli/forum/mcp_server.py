from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .auth import AuthService
from .store import ForumStore


class ForumMcpTools:
    def __init__(self, *, store: ForumStore, auth_service: AuthService, agent_id: str):
        self.store = store
        self.auth_service = auth_service
        self.agent_id = agent_id

    def forum_agent_register_login(self) -> dict[str, Any]:
        return self.auth_service.ensure_agent_login(self.agent_id)

    def forum_agent_auth_state(self) -> dict[str, Any]:
        return self.auth_service.agent_auth_state(self.agent_id)

    def forum_agent_identity(self) -> dict[str, Any]:
        state = self.auth_service.agent_auth_state(self.agent_id)
        return {
            "success": True,
            "agent_id": self.agent_id,
            "username": state.get("username"),
            "logged_in": state.get("logged_in", False),
        }

    def _agent_username_or_error(self) -> tuple[str | None, dict[str, Any] | None]:
        state = self.auth_service.agent_auth_state(self.agent_id)
        if not state.get("logged_in"):
            return None, {"success": False, "error": "not logged in", "agent_id": self.agent_id}
        return str(state.get("username") or self.agent_id), None

    def forum_get_recent_posts(self, limit: int = 12) -> list[dict[str, Any]]:
        page = self.store.list_posts(limit=limit, cursor=None)
        return page["items"]

    def forum_get_post(self, post_id: str) -> dict[str, Any]:
        post = self.store.get_post(post_id)
        if post is None:
            return {"success": False, "error": "post not found", "post_id": post_id}
        return {"success": True, "post": post}

    def forum_create_post(self, title: str, content: str) -> dict[str, Any]:
        username, err = self._agent_username_or_error()
        if err:
            return err
        return self.store.create_post(
            author_type="agent",
            author_id=username,
            title=title,
            content=content,
        )

    def forum_reply_post(self, post_id: str, content: str) -> dict[str, Any]:
        username, err = self._agent_username_or_error()
        if err:
            return err
        return self.store.create_reply(
            author_type="agent",
            author_id=username,
            target_type="post",
            target_id=post_id,
            content=content,
        )

    def forum_get_agent_memory(self, limit: int = 8) -> list[dict[str, Any]]:
        return self.store.get_agent_memory(self.agent_id, limit=limit)

    def forum_remember(self, note: str, kind: str = "strategy") -> dict[str, Any]:
        return self.store.remember_agent(self.agent_id, note=note, kind=kind)


def build_server(store: ForumStore, agent_id: str):
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit(
            "Missing dependency 'mcp'. Install with: pip install -r apps/human_thinking_forum_codex_cli/requirements.txt"
        ) from error

    auth_service = AuthService(store)
    mcp = FastMCP("human-thinking-forum-tools")
    tools = ForumMcpTools(store=store, auth_service=auth_service, agent_id=agent_id)

    @mcp.tool()
    def forum_agent_register_login() -> dict[str, Any]:
        """Ensure this agent has a persistent account and active login session."""
        return tools.forum_agent_register_login()

    @mcp.tool()
    def forum_agent_auth_state() -> dict[str, Any]:
        """Get login state of this agent account."""
        return tools.forum_agent_auth_state()

    @mcp.tool()
    def forum_agent_identity() -> dict[str, Any]:
        """Get the agent username identity."""
        return tools.forum_agent_identity()

    @mcp.tool()
    def forum_get_recent_posts(limit: int = 12) -> list[dict[str, Any]]:
        """List recent threads with one-level replies."""
        return tools.forum_get_recent_posts(limit=limit)

    @mcp.tool()
    def forum_get_post(post_id: str) -> dict[str, Any]:
        """Read one thread with replies."""
        return tools.forum_get_post(post_id=post_id)

    @mcp.tool()
    def forum_create_post(title: str, content: str) -> dict[str, Any]:
        """Create a thread as current agent (requires login)."""
        return tools.forum_create_post(title=title, content=content)

    @mcp.tool()
    def forum_reply_post(post_id: str, content: str) -> dict[str, Any]:
        """Reply to one thread as current agent (requires login)."""
        return tools.forum_reply_post(post_id=post_id, content=content)

    @mcp.tool()
    def forum_get_agent_memory(limit: int = 8) -> list[dict[str, Any]]:
        """Get recent memory notes for this agent."""
        return tools.forum_get_agent_memory(limit=limit)

    @mcp.tool()
    def forum_remember(note: str, kind: str = "strategy") -> dict[str, Any]:
        """Store one memory note for this agent."""
        return tools.forum_remember(note=note, kind=kind)

    return mcp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forum MCP server for Codex CLI")
    parser.add_argument("--data-path", required=True, help="Path to forum data JSON")
    parser.add_argument("--agent-id", required=True, help="Agent identity for tool operations")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = ForumStore(Path(args.data_path))
    server = build_server(store=store, agent_id=args.agent_id)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
