# 03 - 人类思考论坛二期：Agent账号体系 + 超管后台 + 独立思维调试页

## 用户原始请求

> PLEASE IMPLEMENT THIS PLAN: 人类思考论坛二期改造计划（Agent账号体系 + 超管后台 + 独立思维调试页）

## 轮次对话记录（背景/意图/LLM思考摘要）

1. 用户确认按完整二期方案实现，不做缩减。
2. 目标从“Agent直接发帖”升级为“Agent先注册登录再发帖”，并增加默认超管与后台查看能力。
3. 关键业务偏好：
   - 默认超管：`admin / 1234`
   - 超管可查看 Agent 明文账号密码（仅本地演示）
   - Agent 首轮自行注册登录 + 自动无感重登
   - 服务启动自动拉起 4 Agent
   - 独立调试页查看 chat/thinking/mcp/system 过程

## 修改时间

- 开始：2026-02-09 11:22:00 +0800
- 结束：2026-02-09 11:47:10 +0800

## 文件清单（路径 / 操作 / 说明）

| 路径 | 操作 | 说明 |
|---|---|---|
| `apps/human_thinking_forum_codex_cli/forum/store.py` | 重构 | 增加 `role/owner_agent_id`、`agent_credentials`、`agent_sessions`、`admin_snapshot`，并兼容旧数据读取 |
| `apps/human_thinking_forum_codex_cli/forum/auth.py` | 重构 | 增加超管引导、Agent 注册登录托管、Agent 登录态查询 |
| `apps/human_thinking_forum_codex_cli/forum/mcp_server.py` | 重构 | 新增 `forum_agent_register_login/forum_agent_auth_state/forum_agent_identity`；发帖回帖增加登录门禁 |
| `apps/human_thinking_forum_codex_cli/forum/codex_agent.py` | 修改 | 提示词改为“每轮先注册登录”；日志分类改为 `chat/thinking/tool/system` |
| `apps/human_thinking_forum_codex_cli/forum/agent_orchestrator.py` | 重构 | 自动化状态增强（`last_error_code/last_exception/last_event_ts`）、线程异常上报、全局内容游标 |
| `apps/human_thinking_forum_codex_cli/forum/web_app.py` | 重构 | 增加 `auth/me`、admin 只读接口、admin 思维流 SSE、startup 自动 bootstrap admin + autostart agents |
| `apps/human_thinking_forum_codex_cli/forum/models.py` | 修改 | 登录密码长度校验放宽以兼容 `admin/1234` |
| `apps/human_thinking_forum_codex_cli/web/index.html` | 修改 | 增加“思维调试页”按钮（admin 可见）、默认超管提示 |
| `apps/human_thinking_forum_codex_cli/web/app.js` | 重构 | 增加 `auth/me` 恢复登录态、admin 按钮权限、事件流去除 ping 展示、admin 状态接口接入 |
| `apps/human_thinking_forum_codex_cli/web/styles.css` | 修改 | 增加 link-btn/hidden、admin 页面网格与过滤样式 |
| `apps/human_thinking_forum_codex_cli/web/admin.html` | 新增 | 管理员独立调试页 |
| `apps/human_thinking_forum_codex_cli/web/admin.js` | 新增 | 管理员思维流与数据库只读快照页面逻辑 |
| `apps/human_thinking_forum_codex_cli/tests/test_store.py` | 修改 | 增加 agent credential/session 用例 |
| `apps/human_thinking_forum_codex_cli/tests/test_auth.py` | 修改 | 增加 admin bootstrap 与 agent login 用例 |
| `apps/human_thinking_forum_codex_cli/tests/test_mcp_tools.py` | 修改 | 增加“未登录不可发帖，注册登录后可发帖”用例 |
| `apps/human_thinking_forum_codex_cli/tests/test_admin_api.py` | 新增 | admin 接口鉴权与快照返回用例（环境无 fastapi 时 skip） |
| `apps/human_thinking_forum_codex_cli/README.md` | 更新 | 增加二期能力、默认超管、admin 页面说明 |
| `restart_forum.sh` | 更新 | 启动提示默认超管账号 |
| `docs/architecture/repo-metadata.json` | 更新 | 同步新增/改造路径元数据 |
| `docs/architecture/repository-structure.md` | 更新 | 结构树同步 |
| `docs/dev_logs/2026-02-09/03-forum-phase2-admin-agent-auth.md` | 新增 | 本轮开发日志 |

## 变更说明（方案 / 影响范围 / 风险控制）

### 1) 账号与权限升级

- 用户模型增加 `role` 与 `owner_agent_id`。
- 服务启动时自动创建默认超管（若不存在）：`admin / 1234`。
- 新增 `GET /api/auth/me` 便于前端恢复登录态和权限判断。

### 2) Agent 注册登录与持久化

- 引入服务端托管的 `agent_credentials`（含明文密码）和 `agent_sessions`。
- MCP 增加 `forum_agent_register_login`，首轮注册+登录，后续复用并自动重登。
- `forum_create_post/forum_reply_post` 增加“必须登录”门禁。

### 3) 自动启动与可观测性

- `startup` 自动执行：bootstrap admin + autostart agents。
- orchestrator 状态新增错误码、异常信息、事件时间戳，避免静默 idle。

### 4) 管理后台与独立调试页

- 新增 admin-only API：
  - `GET /api/admin/db/snapshot`
  - `GET /api/admin/agents/status`
  - `GET /api/admin/agents/thoughts/stream`
- 新增 `web/admin.html` 调试页，支持按类型过滤思维事件，并可查看数据库只读快照。

### 5) 风险控制

- 明文密码展示仅限 admin 接口，且定位本机演示环境。
- 保留 `POST /api/agents/stop` 紧急停止开关。
- 思维流高频事件通过 ring buffer + 前端过滤降低噪声。

## 验证结果

```bash
python3 -m py_compile apps/human_thinking_forum_codex_cli/main.py apps/human_thinking_forum_codex_cli/forum/*.py
# 结果：通过

cd apps/human_thinking_forum_codex_cli && PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
# 结果：通过（8 tests，1 skipped；skip 原因：当前 python 环境可能无 fastapi）

bash restart_forum.sh --turn-timeout 20
# 结果：服务可启动，接口可访问

curl http://127.0.0.1:8099/api/health
# 结果：{"ok":true}

POST /api/auth/login with admin/1234
# 结果：登录成功，role=admin

GET /api/admin/agents/status (Bearer token)
# 结果：成功，返回 4 个 agent 状态

GET /api/admin/db/snapshot (Bearer token)
# 结果：成功，返回 users/sessions/posts/replies/agent_credentials/agent_sessions

bash scripts/check_errors.sh
# 结果：通过

npm test
# 结果：失败（ENOENT: 根目录无 package.json）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
- 工作区说明：存在其他 agent 并行改动；本轮按用户授权继续并未回滚他人变更

## 补充修复记录

1. 修复了 Agent 历史迁移边界：当旧数据存在 Agent 用户但缺少托管凭据时，改为自动创建备用账号（`agent_<id>_acctN`）并托管凭据，避免无法登录。
2. 结构同步过程中误把 `.venv/__pycache__/runtime` 临时路径批量写入元数据，已执行清理并重新生成结构文档，最终 metadata 恢复到源码可维护规模。

## 追加烟测

- `GET /api/admin/agents/thoughts/stream?admin_token=<token>` 返回 200，已看到 `skills_synced/agents_started` 实时事件，确认独立调试流可连通。
