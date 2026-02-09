# 05 - Web 控制接口 + SSE 实时流

## 用户请求

> 下面两步都继续

## 背景与意图

上一轮已经完成 Web 壳与状态读取，但仍有两个缺口：

1. 前端按钮未接后端控制（Start/Stop/Reset）
2. 前端使用轮询，不利于实时调试与状态一致性

本轮目标：

- 在 `web_api.py` 内直接接入对局控制能力
- 用 SSE 推送替代前端轮询

## 修改时间

2026-02-09 11:10:00 – 2026-02-09 11:14:10 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/web_api.py` | 修改 | 增加 `RuntimeController`（内置 BattleCoordinator）；新增 `/api/stream` SSE；新增 `POST /api/match/*` 控制接口 |
| `apps/gomoku_web/src/App.jsx` | 修改 | 移除轮询，改为 EventSource 订阅 `/api/stream`；接入 Start/Stop/Reset/Clear Memory 按钮 |
| `apps/gomoku_web/README.md` | 修改 | 补充流式更新和控制接口说明 |
| `apps/gomoku_codex_cli/README.md` | 修改 | 补充 Web API 端点清单 |
| `restart_web.sh` | 修改 | 增加 codex 二进制自动探测并透传给 `web_api.py` |
| `.gitignore` | 修改 | 新增 runtime `*.jsonl` 忽略规则，避免事件文件进入未跟踪列表 |
| `docs/dev_logs/2026-02-09/05-web-control-api-and-sse-stream.md` | 新增 | 本次开发记录 |

## 变更说明

### 1. 后端：控制接口接入

`web_api.py` 新增 `RuntimeController`：

- 初始化并持有 `BattleCoordinator`
- 消费 `ui_queue` 更新运行状态与版本号
- 提供 `snapshot()` 统一读取 `state/memory/events`
- 新增控制接口：
  - `POST /api/match/start`
  - `POST /api/match/stop`
  - `POST /api/match/reset`
  - `POST /api/match/clear-memory`

### 2. 后端：SSE 实时流

新增：

- `GET /api/stream`（`text/event-stream`）
- 事件名：`state`
- 推送内容：与 `/api/state` 同结构（含 `runtime_status`、`codex_available`、`version`）
- 连接保活：周期性 `keep-alive` 注释帧

### 3. 前端：轮询改 SSE

`App.jsx` 从 `setInterval(fetch)` 改为：

- `EventSource('/api/stream')`
- 断开自动重连
- UI 展示 `stream connected/reconnecting`
- 保留回放逻辑（棋盘、回合记录、步骤思考流）

### 4. 前端：控制按钮接后端

新增按钮行为：

- Start -> `POST /api/match/start`
- Stop -> `POST /api/match/stop`
- Reset Board -> `POST /api/match/reset`
- Clear Memory -> `POST /api/match/clear-memory`

## 影响范围

- Web 模式可独立启停对局，不再依赖 Tk GUI 按钮
- 状态流由轮询改为推送，减少请求并提高实时性
- 不影响原有 Tk 本地 GUI 入口

## 风险控制

- SSE 断开自动重连，降低网络抖动影响
- API 请求返回统一 `ok/error`，前端统一错误展示
- 仍使用状态文件作为事实源，不引入额外状态副本

## 验证结果

```bash
python3 -m py_compile apps/gomoku_codex_cli/web_api.py
# 结果：通过

cd apps/gomoku_web && npm run lint
# 结果：通过

cd apps/gomoku_web && npm run build
# 结果：通过

# API 冒烟
curl http://127.0.0.1:8787/api/health
curl http://127.0.0.1:8787/api/state
curl -X POST http://127.0.0.1:8787/api/match/stop
curl -X POST http://127.0.0.1:8787/api/match/reset
curl -X POST http://127.0.0.1:8787/api/match/clear-memory
curl -N http://127.0.0.1:8787/api/stream
# 结果：全部返回正常（SSE 持续推送 state 事件）

bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 按仓库脚本规则跳过）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
