from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    TestClient = None

if TestClient is not None:
    from forum.web_app import create_app
else:  # pragma: no cover - environment dependent
    create_app = None


@unittest.skipIf(TestClient is None, "fastapi is not installed in current python environment")
class AdminApiTest(unittest.TestCase):
    def test_admin_snapshot_and_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(__file__).resolve().parents[3]
            runtime = Path(tmpdir) / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)

            config_path = Path(tmpdir) / "agents.json"
            config_path.write_text(json.dumps({"agents": []}, ensure_ascii=False), encoding="utf-8")

            app = create_app(
                workspace_root=root,
                runtime_dir=runtime,
                config_path=config_path,
                codex_bin="codex",
                python_bin="python3",
                default_model="gpt-5.3-codex",
                turn_timeout=10,
            )

            with TestClient(app) as client:
                bad = client.get("/api/admin/db/snapshot")
                self.assertEqual(bad.status_code, 401)

                login = client.post(
                    "/api/auth/login",
                    json={"username": "admin", "password": "1234"},
                )
                self.assertEqual(login.status_code, 200)
                token = login.json()["token"]

                res = client.get(
                    "/api/admin/db/snapshot",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(res.status_code, 200)
                payload = res.json()
                self.assertTrue(payload["success"])
                self.assertIn("agent_credentials", payload["data"])


if __name__ == "__main__":
    unittest.main()
