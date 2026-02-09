from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forum.auth import AuthService
from forum.mcp_server import ForumMcpTools
from forum.store import ForumStore


class ForumMcpToolsTest(unittest.TestCase):
    def test_post_requires_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            auth = AuthService(store)
            tools = ForumMcpTools(store=store, auth_service=auth, agent_id="socrates")

            denied = tools.forum_create_post("主题", "内容")
            self.assertFalse(denied["success"])
            self.assertIn("not logged in", denied["error"])

            login = tools.forum_agent_register_login()
            self.assertTrue(login["success"])

            created = tools.forum_create_post("主题", "内容")
            self.assertTrue(created["success"])
            post_id = created["post"]["id"]

            replied = tools.forum_reply_post(post_id, "这是回复")
            self.assertTrue(replied["success"])

            post = tools.forum_get_post(post_id)
            self.assertTrue(post["success"])
            self.assertEqual(len(post["post"]["replies"]), 1)

            mem = tools.forum_remember("记录一个策略", "strategy")
            self.assertTrue(mem["success"])
            memory = tools.forum_get_agent_memory(limit=5)
            self.assertEqual(len(memory), 1)


if __name__ == "__main__":
    unittest.main()
