from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent_orchestrator import AgentOrchestrator
from .auth import AuthService
from .models import CreatePostRequest, CreateReplyRequest, LoginRequest, RegisterRequest
from .skills_loader import SkillsLoader
from .store import ForumStore


class EventBus:
    def __init__(self, maxlen: int = 2000):
        self.maxlen = max(100, maxlen)
        self._events: deque[dict[str, Any]] = deque(maxlen=self.maxlen)
        self._lock = threading.Lock()
        self._next_id = 0

    def publish(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._next_id += 1
            event = {
                "id": self._next_id,
                "type": event_type,
                "payload": payload,
            }
            self._events.append(event)
            return dict(event)

    def snapshot_since(self, event_id: int, include_types: set[str] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            base = [dict(event) for event in self._events if int(event["id"]) > int(event_id)]
        if include_types is None:
            return base
        return [event for event in base if str(event.get("type")) in include_types]


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return ""
    return header[len("Bearer ") :].strip()


def create_app(
    *,
    workspace_root: Path,
    runtime_dir: Path,
    config_path: Path,
    codex_bin: str,
    python_bin: str,
    default_model: str,
    turn_timeout: int,
) -> FastAPI:
    workspace_root = Path(workspace_root)
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    app_root = workspace_root / "apps" / "human_thinking_forum_codex_cli"
    web_root = app_root / "web"
    skills_root = app_root / "skills"

    store = ForumStore(runtime_dir / "forum_data.json")
    auth_service = AuthService(store)
    event_bus = EventBus(maxlen=8000)

    def emit(event_type: str, payload: dict[str, Any]) -> None:
        event_bus.publish(event_type, payload)

    skills_loader = SkillsLoader(skills_root=skills_root, runtime_root=runtime_dir, emit=emit)
    orchestrator = AgentOrchestrator(
        store=store,
        skills_loader=skills_loader,
        emit=emit,
        config_path=config_path,
        workspace_root=workspace_root,
        codex_bin=codex_bin,
        python_bin=python_bin,
        default_model=default_model,
        timeout_sec=turn_timeout,
    )

    app = FastAPI(title="人类思考论坛")
    app.mount("/web", StaticFiles(directory=str(web_root)), name="web")

    @app.middleware("http")
    async def web_admin_compat_middleware(request: Request, call_next):
        # /web is mounted as static files; intercept legacy admin path before routing.
        if request.url.path in ("/web/admin", "/web/admin/"):
            return FileResponse(web_root / "admin.html")
        return await call_next(request)

    app.state.store = store
    app.state.auth_service = auth_service
    app.state.event_bus = event_bus
    app.state.skills_loader = skills_loader
    app.state.orchestrator = orchestrator

    def require_user(request: Request) -> dict[str, Any]:
        token = _extract_bearer_token(request)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        user = auth_service.authenticate(token)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
        return user

    def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
        return user

    def require_admin_token(admin_token: str) -> dict[str, Any]:
        user = auth_service.authenticate(admin_token)
        if not user or user.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
        return user

    @app.on_event("startup")
    async def on_startup() -> None:
        bootstrap = auth_service.bootstrap_admin_if_missing()
        emit("server_ready", {"message": "human-thinking-forum online", "admin_bootstrap": bootstrap})
        start_result = orchestrator.start_all()
        emit("agents_autostart", start_result)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        orchestrator.stop_all()

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(web_root / "index.html")

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(web_root / "admin.html")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True}

    @app.post("/api/auth/register")
    async def register(payload: RegisterRequest) -> dict[str, Any]:
        result = auth_service.register(payload.username, payload.password)
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "register failed"))
        emit("user_registered", {"username": result["user"]["username"]})
        return result

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest) -> dict[str, Any]:
        result = auth_service.login(payload.username, payload.password)
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("error", "login failed"))
        emit("user_login", {"username": result["user"]["username"], "role": result["user"]["role"]})
        return result

    @app.get("/api/auth/me")
    async def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return {"success": True, "user": user}

    @app.post("/api/auth/logout")
    async def logout(request: Request) -> dict[str, Any]:
        token = _extract_bearer_token(request)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        return auth_service.logout(token)

    @app.get("/api/forum/posts")
    async def list_posts(limit: int = 20, cursor: int | None = None) -> dict[str, Any]:
        page = store.list_posts(limit=limit, cursor=cursor)
        return {"success": True, **page}

    @app.post("/api/forum/posts")
    async def create_post(payload: CreatePostRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        result = store.create_post(
            author_type="human",
            author_id=user["username"],
            title=payload.title,
            content=payload.content,
        )
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "post failed"))
        emit("post_created", {"source": "human", "user": user["username"], "post": result["post"]})
        return result

    @app.post("/api/forum/posts/{post_id}/replies")
    async def create_reply(post_id: str, payload: CreateReplyRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        result = store.create_reply(
            author_type="human",
            author_id=user["username"],
            target_type="post",
            target_id=post_id,
            content=payload.content,
        )
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "reply failed"))
        emit("reply_created", {"source": "human", "user": user["username"], "reply": result["reply"]})
        return result

    @app.get("/api/agents/status")
    async def get_agents_status() -> dict[str, Any]:
        return {"success": True, "items": orchestrator.status_list()}

    @app.post("/api/agents/start")
    async def start_agents(admin_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        del admin_user
        return orchestrator.start_all()

    @app.post("/api/agents/stop")
    async def stop_agents(admin_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        del admin_user
        return orchestrator.stop_all()

    @app.post("/api/skills/reload")
    async def reload_skills(admin_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        del admin_user
        return orchestrator.reload_skills()

    @app.get("/api/admin/db/snapshot")
    async def admin_db_snapshot(admin_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        del admin_user
        return {"success": True, "data": store.admin_snapshot()}

    @app.get("/api/admin/agents/status")
    async def admin_agents_status(admin_user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
        del admin_user
        items = orchestrator.status_list()
        for item in items:
            state = auth_service.agent_auth_state(item["agent_id"])
            item["logged_in"] = state.get("logged_in", False)
            item["username"] = state.get("username")
            item["session_expires_at"] = state.get("expires_at")
        return {"success": True, "items": items}

    @app.get("/api/events/stream")
    async def events_stream(request: Request, last_id: int = 0):
        async def generator():
            cursor = int(last_id)
            while True:
                if await request.is_disconnected():
                    break

                events = event_bus.snapshot_since(cursor)
                if events:
                    for event in events:
                        cursor = int(event["id"])
                        data = json.dumps(event, ensure_ascii=False)
                        yield f"id: {cursor}\nevent: {event['type']}\ndata: {data}\n\n"
                else:
                    yield "event: ping\ndata: {}\n\n"

                await asyncio.sleep(0.8)

        return StreamingResponse(
            generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/admin/agents/thoughts/stream")
    async def admin_thoughts_stream(request: Request, last_id: int = 0, admin_token: str = ""):
        require_admin_token(admin_token)

        include_types = {
            "agent_log",
            "agent_status",
            "agents_started",
            "agents_stopped",
            "skills_synced",
            "skills_reloaded",
            "agents_autostart",
        }

        async def generator():
            cursor = int(last_id)
            while True:
                if await request.is_disconnected():
                    break

                events = event_bus.snapshot_since(cursor, include_types=include_types)
                if events:
                    for event in events:
                        cursor = int(event["id"])
                        data = json.dumps(event, ensure_ascii=False)
                        yield f"id: {cursor}\nevent: {event['type']}\ndata: {data}\n\n"
                else:
                    yield "event: ping\ndata: {}\n\n"

                await asyncio.sleep(0.8)

        return StreamingResponse(
            generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app
