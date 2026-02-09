from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forum.store import ForumStore


class ForumStoreTest(unittest.TestCase):
    def test_create_post_and_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            post_result = store.create_post(
                author_type="human",
                author_id="alice",
                title="第一帖",
                content="你好论坛",
            )
            self.assertTrue(post_result["success"])
            post_id = post_result["post"]["id"]

            reply_result = store.create_reply(
                author_type="agent",
                author_id="agent_socrates",
                target_type="post",
                target_id=post_id,
                content="欢迎你",
            )
            self.assertTrue(reply_result["success"])

            post = store.get_post(post_id)
            assert post is not None
            self.assertEqual(len(post["replies"]), 1)
            self.assertEqual(post["replies"][0]["content"], "欢迎你")

    def test_reject_reply_to_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            result = store.create_reply(
                author_type="human",
                author_id="alice",
                target_type="reply",
                target_id="reply-1",
                content="不应允许",
            )
            self.assertFalse(result["success"])
            self.assertIn("one-level", result["error"])

    def test_agent_credential_and_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            created = store.create_user(
                username="agent_socrates",
                password_hash="h",
                salt="s",
                role="agent",
                owner_agent_id="socrates",
            )
            self.assertTrue(created["success"])
            user_id = created["user"]["id"]

            cred = store.upsert_agent_credential(
                agent_id="socrates",
                username="agent_socrates",
                password_plain="agent_socrates_pass_2026",
                user_id=user_id,
            )
            self.assertEqual(cred["username"], "agent_socrates")

            session = store.set_agent_session(
                agent_id="socrates",
                token="tok-1",
                user_id=user_id,
                ttl_seconds=3600,
            )
            self.assertEqual(session["token"], "tok-1")

            active = store.get_agent_session("socrates")
            assert active is not None
            self.assertEqual(active["token"], "tok-1")


if __name__ == "__main__":
    unittest.main()
