# 06 - 修复 Web Start 卡死与实时日志空白

## 用户请求

> ？？？restart_web后,点击start没用？

## 背景与意图

用户截图中出现：`runtime: B thinking...` 但棋盘 `0/0` 且左右日志 `(no logs)`，体感为 Start 无效。

定位后发现两个问题叠加：

1. `POST /api/match/start` 在“已运行”分支存在锁内递归调用 `snapshot()`，会死锁。
2. Web 端只展示已落盘 `events`，进行中回合日志未回传，导致开始阶段常见“无日志可见”。

## 修改时间

2026-02-09 11:18:00 – 2026-02-09 11:23:50 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/web_api.py` | 修改 | 修复 start 幂等分支死锁；新增 `live_logs` 与 `match_running` 状态输出 |
| `apps/gomoku_web/src/App.jsx` | 修改 | 接收并展示 `live_logs`；显示 match 状态；Start 按钮在运行中禁用 |
| `docs/dev_logs/2026-02-09/06-fix-web-start-deadlock-and-live-logs.md` | 新增 | 本次 debug 记录 |

## 变更说明

### 1. 修复 start 死锁

在 `RuntimeController.start()`：

- 原问题：在 `with self._lock` 内执行 `self.snapshot()`，二次加锁导致死锁。
- 修复：先在锁内判断 `already_running`，锁外再调用 `snapshot()` 构建返回。

业务效果：重复点击 Start 不会卡死，后端会返回 `message: match already running`。

### 2. 增加实时日志透出

在 `RuntimeController._drain_ui_queue()`：

- 把 `type=log` 事件写入内存 `live_logs`（按 B/W 分桶、限长）
- `snapshot()` 增加：
  - `live_logs`
  - `match_running`

业务效果：即使还没落子（`move_count=0`），前端也能显示实时思考日志，不再“空白”。

### 3. 前端可见性增强

在 `App.jsx`：

- 合并显示持久事件日志 + `live_logs`
- 状态栏新增 `match: running/stopped`
- `Start` 在 `match_running=true` 时禁用，避免重复触发

## 影响范围

- 仅 Web API / Web UI 交互层
- 不影响现有 Tk GUI 与引擎规则

## 验证结果

```bash
# 死锁回归测试（端口 8890）
POST /api/match/start 第一次 -> ok
POST /api/match/start 第二次 -> ok + message="match already running"

# 实时日志可见性
GET /api/state -> live_logs.B length > 0（在 move_count=0 阶段）

python3 -m py_compile apps/gomoku_codex_cli/web_api.py
# 通过

cd apps/gomoku_web && npm run lint
# 通过

cd apps/gomoku_web && npm run build
# 通过

bash scripts/check_errors.sh
# 通过
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
