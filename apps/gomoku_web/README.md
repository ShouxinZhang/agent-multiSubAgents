# Gomoku Web Shell (React + Vite + Tailwind + shadcn-style UI)

## 目标

提供一个独立 Web 前端壳，实时读取并回放：

- `state.json`（棋盘/落子）
- `turn_events.jsonl`（每步思考流）

## 启动方式

1. 启动对局（原 Python GUI，可选）

```bash
bash restart.sh
```

2. 启动状态 API（读取 runtime 文件）

```bash
python3 apps/gomoku_codex_cli/web_api.py --port 8787
```

3. 启动前端

```bash
cd apps/gomoku_web
npm install
npm run dev
```

浏览器打开：`http://127.0.0.1:5173`

## 控制与流式更新

- 顶部控制按钮直接调用后端：
  - `Start` → `POST /api/match/start`
  - `Stop` → `POST /api/match/stop`
  - `Reset Board` → `POST /api/match/reset`
  - `Clear Memory` → `POST /api/match/clear-memory`
- 页面通过 `EventSource` 订阅 `/api/stream`，不再使用轮询。

## API

- `GET /api/health`
- `GET /api/state`
- `GET /api/stream` (SSE)
- `POST /api/match/start`
- `POST /api/match/stop`
- `POST /api/match/reset`
- `POST /api/match/clear-memory`

返回结构：

```json
{
  "ok": true,
  "state": {},
  "memory": {},
  "events": []
}
```
