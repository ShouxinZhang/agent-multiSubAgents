from __future__ import annotations

import hashlib
import secrets
from typing import Any

from .store import ForumStore


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


def hash_password(password: str, salt: str) -> str:
    data = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120000,
        dklen=32,
    )
    return data.hex()


class AuthService:
    def __init__(self, store: ForumStore):
        self.store = store

    def _create_user(self, *, username: str, password: str, role: str, owner_agent_id: str | None = None) -> dict[str, Any]:
        salt = secrets.token_hex(16)
        password_hash = hash_password(password, salt)
        return self.store.create_user(
            username=username,
            password_hash=password_hash,
            salt=salt,
            role=role,
            owner_agent_id=owner_agent_id,
        )

    def register(self, username: str, password: str) -> dict[str, Any]:
        clean_username = username.strip()
        if len(clean_username) < 3:
            return {"success": False, "error": "username too short"}
        if len(clean_username) > 32:
            return {"success": False, "error": "username too long"}
        if len(password) < 8:
            return {"success": False, "error": "password too short"}

        return self._create_user(username=clean_username, password=password, role="human")

    def bootstrap_admin_if_missing(self) -> dict[str, Any]:
        existing = self.store.get_user_by_username(ADMIN_USERNAME)
        if existing:
            return {"success": True, "created": False, "user": existing}

        result = self._create_user(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, role="admin")
        if not result.get("success"):
            return {"success": False, "created": False, "error": result.get("error", "bootstrap failed")}
        return {"success": True, "created": True, "user": result["user"]}

    def login(self, username: str, password: str, ttl_seconds: int = 86400) -> dict[str, Any]:
        user = self.store.get_user_by_username(username.strip())
        if not user:
            return {"success": False, "error": "invalid credentials"}

        expected = hash_password(password, user["salt"])
        if expected != user["password_hash"]:
            return {"success": False, "error": "invalid credentials"}

        token = secrets.token_urlsafe(32)
        session_result = self.store.create_session(user_id=user["id"], token=token, ttl_seconds=ttl_seconds)
        if not session_result.get("success"):
            return {"success": False, "error": "failed to create session"}

        session = session_result["session"]
        return {
            "success": True,
            "token": token,
            "expires_at": session["expires_at"],
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user.get("role", "human"),
                "owner_agent_id": user.get("owner_agent_id"),
            },
        }

    def logout(self, token: str) -> dict[str, Any]:
        return self.store.revoke_session(token)

    def authenticate(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        session = self.store.get_session(token)
        if not session:
            return None
        user = self.store.get_user_by_id(session["user_id"])
        if not user:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role", "human"),
            "owner_agent_id": user.get("owner_agent_id"),
        }

    def ensure_agent_login(self, agent_id: str, ttl_seconds: int = 86400) -> dict[str, Any]:
        existing_credential = self.store.get_agent_credential(agent_id)
        if existing_credential is None:
            username = f"agent_{agent_id}"
            password_plain = f"{username}_pass_2026"

            # If historical data has an agent user without stored plain password,
            # create a deterministic fallback account we can log in with.
            candidate = username
            suffix = 0
            while self.store.get_user_by_username(candidate) is not None:
                suffix += 1
                candidate = f"{username}_acct{suffix}"
            username = candidate
            password_plain = f"{username}_pass_2026"

            created = self._create_user(
                username=username,
                password=password_plain,
                role="agent",
                owner_agent_id=agent_id,
            )
            if not created.get("success"):
                return {"success": False, "error": created.get("error", "agent register failed")}
            user_id = created["user"]["id"]

            self.store.upsert_agent_credential(
                agent_id=agent_id,
                username=username,
                password_plain=password_plain,
                user_id=user_id,
            )
            existing_credential = self.store.get_agent_credential(agent_id)

        if existing_credential is None:
            return {"success": False, "error": "agent credential unavailable"}

        active_session = self.store.get_agent_session(agent_id)
        if active_session is not None:
            return {
                "success": True,
                "logged_in": True,
                "username": existing_credential["username"],
                "token": active_session["token"],
                "expires_at": active_session["expires_at"],
                "created": False,
            }

        login_result = self.login(
            username=existing_credential["username"],
            password=existing_credential["password_plain"],
            ttl_seconds=ttl_seconds,
        )
        if not login_result.get("success"):
            return {"success": False, "error": login_result.get("error", "agent login failed")}

        saved_session = self.store.set_agent_session(
            agent_id=agent_id,
            token=login_result["token"],
            user_id=existing_credential["user_id"],
            ttl_seconds=ttl_seconds,
        )
        return {
            "success": True,
            "logged_in": True,
            "username": existing_credential["username"],
            "token": saved_session["token"],
            "expires_at": saved_session["expires_at"],
            "created": True,
        }

    def agent_auth_state(self, agent_id: str) -> dict[str, Any]:
        credential = self.store.get_agent_credential(agent_id)
        if credential is None:
            return {
                "success": True,
                "logged_in": False,
                "agent_id": agent_id,
                "username": None,
                "expires_at": None,
            }

        session = self.store.get_agent_session(agent_id)
        return {
            "success": True,
            "logged_in": session is not None,
            "agent_id": agent_id,
            "username": credential["username"],
            "expires_at": None if session is None else session["expires_at"],
        }
