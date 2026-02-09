from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forum.auth import ADMIN_PASSWORD, ADMIN_USERNAME, AuthService
from forum.store import ForumStore


class AuthServiceTest(unittest.TestCase):
    def test_register_and_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            auth = AuthService(store)

            reg = auth.register("alice", "password123")
            self.assertTrue(reg["success"])

            reg_dup = auth.register("alice", "password123")
            self.assertFalse(reg_dup["success"])

            login_bad = auth.login("alice", "wrong-pass")
            self.assertFalse(login_bad["success"])

            login_ok = auth.login("alice", "password123")
            self.assertTrue(login_ok["success"])
            self.assertTrue(login_ok["token"])
            user = auth.authenticate(login_ok["token"])
            assert user is not None
            self.assertEqual(user["username"], "alice")
            self.assertEqual(user["role"], "human")

    def test_bootstrap_admin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            auth = AuthService(store)

            boot = auth.bootstrap_admin_if_missing()
            self.assertTrue(boot["success"])

            login = auth.login(ADMIN_USERNAME, ADMIN_PASSWORD)
            self.assertTrue(login["success"])
            self.assertEqual(login["user"]["role"], "admin")

    def test_ensure_agent_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ForumStore(Path(tmpdir) / "forum.json")
            auth = AuthService(store)

            result = auth.ensure_agent_login("socrates")
            self.assertTrue(result["success"])
            self.assertTrue(result["logged_in"])

            state = auth.agent_auth_state("socrates")
            self.assertTrue(state["logged_in"])
            self.assertTrue(state["username"].startswith("agent_socrates"))


if __name__ == "__main__":
    unittest.main()
