from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import fcntl


class ForumStore:
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.lock_path = self.data_path.with_suffix(self.data_path.suffix + ".lock")
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            with self._locked():
                self._write_unlocked(self._bootstrap_data())

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _bootstrap_data(self) -> dict[str, Any]:
        return {
            "users": [],
            "sessions": [],
            "agent_credentials": [],
            "agent_sessions": [],
            "posts": [],
            "replies": [],
            "agent_memory": {},
            "counters": {
                "user": 0,
                "session": 0,
                "post": 0,
                "reply": 0,
            },
            "updated_at": self._now(),
        }

    @contextmanager
    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.data_path.exists():
            return self._bootstrap_data()

        with open(self.data_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        data.setdefault("users", [])
        data.setdefault("sessions", [])
        data.setdefault("agent_credentials", [])
        data.setdefault("agent_sessions", [])
        data.setdefault("posts", [])
        data.setdefault("replies", [])
        data.setdefault("agent_memory", {})
        data.setdefault("counters", {"user": 0, "session": 0, "post": 0, "reply": 0})
        data.setdefault("updated_at", self._now())

        for user in data["users"]:
            user.setdefault("role", "human")
            user.setdefault("owner_agent_id", None)

        return data

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        data["updated_at"] = self._now()
        fd, temp_path = tempfile.mkstemp(prefix="forum_data_", suffix=".json", dir=self.data_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=True, indent=2)
            os.replace(temp_path, self.data_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _next_id(self, data: dict[str, Any], kind: str, prefix: str) -> tuple[str, int]:
        counters = data["counters"]
        counters[kind] = int(counters.get(kind, 0)) + 1
        seq = int(counters[kind])
        return f"{prefix}-{seq}", seq

    def _clean_expired_human_sessions(self, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        kept: list[dict[str, Any]] = []
        for session in data["sessions"]:
            expires = session.get("expires_at")
            if not expires:
                continue
            try:
                expire_ts = datetime.fromisoformat(expires)
            except ValueError:
                continue
            if expire_ts > now:
                kept.append(session)
        data["sessions"] = kept

    def _clean_expired_agent_sessions(self, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        kept: list[dict[str, Any]] = []
        for session in data["agent_sessions"]:
            expires = session.get("expires_at")
            if not expires:
                continue
            try:
                expire_ts = datetime.fromisoformat(expires)
            except ValueError:
                continue
            if expire_ts > now:
                kept.append(session)
        data["agent_sessions"] = kept

    def create_user(
        self,
        username: str,
        password_hash: str,
        salt: str,
        role: str = "human",
        owner_agent_id: str | None = None,
    ) -> dict[str, Any]:
        username = username.strip()
        with self._locked():
            data = self._read_unlocked()
            for user in data["users"]:
                if user["username"] == username:
                    return {"success": False, "error": "username already exists"}

            user_id, seq = self._next_id(data, "user", "user")
            new_user = {
                "id": user_id,
                "seq": seq,
                "username": username,
                "password_hash": password_hash,
                "salt": salt,
                "role": role,
                "owner_agent_id": owner_agent_id,
                "created_at": self._now(),
            }
            data["users"].append(new_user)
            self._write_unlocked(data)

        return {
            "success": True,
            "user": {
                "id": user_id,
                "username": username,
                "role": role,
                "owner_agent_id": owner_agent_id,
                "created_at": new_user["created_at"],
            },
        }

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            for user in data["users"]:
                if user["username"] == username:
                    return dict(user)
        return None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            for user in data["users"]:
                if user["id"] == user_id:
                    return dict(user)
        return None

    def create_session(self, user_id: str, token: str, ttl_seconds: int = 86400) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            self._clean_expired_human_sessions(data)
            session_id, seq = self._next_id(data, "session", "session")
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=max(300, ttl_seconds))).isoformat()
            session = {
                "id": session_id,
                "seq": seq,
                "token": token,
                "user_id": user_id,
                "created_at": self._now(),
                "expires_at": expires_at,
            }
            data["sessions"].append(session)
            self._write_unlocked(data)
        return {"success": True, "session": session}

    def get_session(self, token: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            self._clean_expired_human_sessions(data)
            found = None
            for session in data["sessions"]:
                if session["token"] == token:
                    found = dict(session)
                    break
            self._write_unlocked(data)
            return found

    def revoke_session(self, token: str) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            before = len(data["sessions"])
            data["sessions"] = [session for session in data["sessions"] if session.get("token") != token]
            removed = before - len(data["sessions"])
            self._write_unlocked(data)
        return {"success": True, "removed": removed}

    def get_agent_credential(self, agent_id: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            for credential in data["agent_credentials"]:
                if credential.get("agent_id") == agent_id:
                    return dict(credential)
        return None

    def upsert_agent_credential(
        self,
        *,
        agent_id: str,
        username: str,
        password_plain: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            now = self._now()
            updated = None
            for credential in data["agent_credentials"]:
                if credential.get("agent_id") == agent_id:
                    credential["username"] = username
                    credential["password_plain"] = password_plain
                    credential["user_id"] = user_id
                    credential["updated_at"] = now
                    updated = dict(credential)
                    break

            if updated is None:
                created = {
                    "agent_id": agent_id,
                    "username": username,
                    "password_plain": password_plain,
                    "user_id": user_id,
                    "created_at": now,
                }
                data["agent_credentials"].append(created)
                updated = dict(created)

            self._write_unlocked(data)
            return updated

    def set_agent_session(self, *, agent_id: str, token: str, user_id: str, ttl_seconds: int = 86400) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            self._clean_expired_agent_sessions(data)
            now = self._now()
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=max(300, ttl_seconds))).isoformat()

            data["agent_sessions"] = [item for item in data["agent_sessions"] if item.get("agent_id") != agent_id]
            session = {
                "agent_id": agent_id,
                "token": token,
                "user_id": user_id,
                "last_login_at": now,
                "expires_at": expires_at,
            }
            data["agent_sessions"].append(session)
            self._write_unlocked(data)
            return dict(session)

    def get_agent_session(self, agent_id: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            self._clean_expired_agent_sessions(data)
            found = None
            for session in data["agent_sessions"]:
                if session.get("agent_id") == agent_id:
                    found = dict(session)
                    break
            self._write_unlocked(data)
            return found

    def revoke_agent_session(self, agent_id: str) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            before = len(data["agent_sessions"])
            data["agent_sessions"] = [item for item in data["agent_sessions"] if item.get("agent_id") != agent_id]
            removed = before - len(data["agent_sessions"])
            self._write_unlocked(data)
            return {"success": True, "removed": removed}

    def _build_post_payload(self, data: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
        post_id = post["id"]
        replies = [
            dict(item)
            for item in sorted(
                [reply for reply in data["replies"] if reply["post_id"] == post_id],
                key=lambda reply_item: int(reply_item.get("seq", 0)),
            )
        ]
        return {
            "id": post["id"],
            "seq": int(post.get("seq", 0)),
            "author_type": post["author_type"],
            "author_id": post["author_id"],
            "title": post["title"],
            "content": post["content"],
            "created_at": post["created_at"],
            "replies": replies,
        }

    def list_posts(self, limit: int = 20, cursor: int | None = None) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            safe_limit = max(1, min(int(limit), 100))

            posts_sorted = sorted(data["posts"], key=lambda item: int(item.get("seq", 0)), reverse=True)
            if cursor is not None:
                posts_sorted = [item for item in posts_sorted if int(item.get("seq", 0)) < int(cursor)]

            page = posts_sorted[:safe_limit]
            items = [self._build_post_payload(data, post) for post in page]
            next_cursor = None
            if len(posts_sorted) > safe_limit and page:
                next_cursor = int(page[-1].get("seq", 0))
            return {"items": items, "next_cursor": next_cursor}

    def get_post(self, post_id: str) -> dict[str, Any] | None:
        with self._locked():
            data = self._read_unlocked()
            for post in data["posts"]:
                if post["id"] == post_id:
                    return self._build_post_payload(data, post)
        return None

    def create_post(self, author_type: str, author_id: str, title: str, content: str) -> dict[str, Any]:
        title = title.strip()
        content = content.strip()
        if not title:
            return {"success": False, "error": "title is empty"}
        if not content:
            return {"success": False, "error": "content is empty"}

        with self._locked():
            data = self._read_unlocked()
            post_id, seq = self._next_id(data, "post", "post")
            post = {
                "id": post_id,
                "seq": seq,
                "author_type": author_type,
                "author_id": author_id,
                "title": title,
                "content": content,
                "created_at": self._now(),
            }
            data["posts"].append(post)
            self._write_unlocked(data)

        return {"success": True, "post": {**post, "replies": []}}

    def create_reply(
        self,
        *,
        author_type: str,
        author_id: str,
        target_type: str,
        target_id: str,
        content: str,
    ) -> dict[str, Any]:
        content = content.strip()
        if not content:
            return {"success": False, "error": "content is empty"}

        if target_type != "post":
            return {"success": False, "error": "only one-level replies are allowed"}

        with self._locked():
            data = self._read_unlocked()
            target_post = None
            for post in data["posts"]:
                if post["id"] == target_id:
                    target_post = post
                    break
            if target_post is None:
                return {"success": False, "error": "post not found"}

            reply_id, seq = self._next_id(data, "reply", "reply")
            reply = {
                "id": reply_id,
                "seq": seq,
                "post_id": target_id,
                "author_type": author_type,
                "author_id": author_id,
                "content": content,
                "created_at": self._now(),
            }
            data["replies"].append(reply)
            self._write_unlocked(data)

        return {"success": True, "reply": reply}

    def remember_agent(self, agent_id: str, note: str, kind: str = "strategy") -> dict[str, Any]:
        note = note.strip()
        if not note:
            return {"success": False, "error": "note is empty"}

        with self._locked():
            data = self._read_unlocked()
            memory_bucket = data["agent_memory"].setdefault(agent_id, [])
            entry = {
                "id": f"mem-{agent_id}-{len(memory_bucket) + 1}",
                "agent_id": agent_id,
                "kind": kind,
                "note": note,
                "created_at": self._now(),
            }
            memory_bucket.append(entry)
            self._write_unlocked(data)
        return {"success": True, "entry": entry}

    def get_agent_memory(self, agent_id: str, limit: int = 8) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with self._locked():
            data = self._read_unlocked()
            memory_bucket = data["agent_memory"].get(agent_id, [])
            return [dict(item) for item in memory_bucket[-safe_limit:]]

    def content_since(self, *, post_seq: int, reply_seq: int) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            new_posts = [dict(post) for post in data["posts"] if int(post.get("seq", 0)) > int(post_seq)]
            new_replies = [dict(reply) for reply in data["replies"] if int(reply.get("seq", 0)) > int(reply_seq)]
            latest_post_seq = max([int(item.get("seq", 0)) for item in data["posts"]] + [int(post_seq)])
            latest_reply_seq = max([int(item.get("seq", 0)) for item in data["replies"]] + [int(reply_seq)])

        new_posts.sort(key=lambda item: int(item.get("seq", 0)))
        new_replies.sort(key=lambda item: int(item.get("seq", 0)))
        return {
            "posts": new_posts,
            "replies": new_replies,
            "latest_post_seq": latest_post_seq,
            "latest_reply_seq": latest_reply_seq,
        }

    def admin_snapshot(self) -> dict[str, Any]:
        with self._locked():
            data = self._read_unlocked()
            return {
                "users": [dict(item) for item in data["users"]],
                "sessions": [dict(item) for item in data["sessions"]],
                "agent_credentials": [dict(item) for item in data["agent_credentials"]],
                "agent_sessions": [dict(item) for item in data["agent_sessions"]],
                "posts": [dict(item) for item in data["posts"]],
                "replies": [dict(item) for item in data["replies"]],
                "agent_memory": {key: [dict(entry) for entry in value] for key, value in data["agent_memory"].items()},
                "updated_at": data.get("updated_at"),
            }
