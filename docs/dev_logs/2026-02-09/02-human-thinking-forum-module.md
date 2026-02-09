# 02 - 人类思考论坛模块（Web + 4并发Codex Agent + MCP/Skills）

## 用户原始请求

> PLEASE IMPLEMENT THIS PLAN: 人类思考论坛模块实施计划（Web + 4 独立并发 Codex Agent + MCP/Skills）

补充确认：

> 工作区出现了我未创建的新增改动是另一个agent 你继续工作就可以

## 轮次对话记录（背景/意图/LLM思考摘要）

1. 用户要求按既定完整方案实现大模块，不做二次规划。
2. 实施期间发现工作区存在非本轮新增改动，按仓库规则暂停并向用户确认。
3. 用户明确授权忽略外部改动继续执行。
4. 采用“最小侵入 + 新叶子目录”策略新增 `apps/human_thinking_forum_codex_cli`，不改既有 gomoku 业务逻辑。

## 修改时间

- 开始：2026-02-09 10:59:13 +0800
- 结束：2026-02-09 11:10:35 +0800

## 文件清单（路径 / 操作 / 时间 / 说明）

| 路径 | 操作 | 时间 | 说明 |
|---|---|---|---|
| `apps/human_thinking_forum_codex_cli/main.py` | 新增 | 2026-02-09 11:03:xx | 应用入口，启动 FastAPI/uvicorn |
| `apps/human_thinking_forum_codex_cli/requirements.txt` | 新增 | 2026-02-09 11:05:xx | Forum 模块 Python 依赖 |
| `apps/human_thinking_forum_codex_cli/README.md` | 新增 | 2026-02-09 11:05:xx | 模块运行与结构说明 |
| `apps/human_thinking_forum_codex_cli/forum/store.py` | 新增 | 2026-02-09 11:01:xx | JSON+文件锁论坛存储，支持帖子/一层回复/agent memory |
| `apps/human_thinking_forum_codex_cli/forum/auth.py` | 新增 | 2026-02-09 11:01:xx | 本地注册登录与 session 管理 |
| `apps/human_thinking_forum_codex_cli/forum/mcp_server.py` | 新增 | 2026-02-09 11:03:xx | MCP tool server，暴露论坛工具 |
| `apps/human_thinking_forum_codex_cli/forum/codex_agent.py` | 新增 | 2026-02-09 11:02:xx | `codex exec --json` 调用与事件解析 |
| `apps/human_thinking_forum_codex_cli/forum/skills_loader.py` | 新增 | 2026-02-09 11:02:xx | shared+agent skills 合并、热刷新、工作区同步 |
| `apps/human_thinking_forum_codex_cli/forum/agent_orchestrator.py` | 新增+修改 | 2026-02-09 11:03:xx / 11:08:xx | 4 agent 并发调度；补充 codex 不存在时终止热失败循环 |
| `apps/human_thinking_forum_codex_cli/forum/web_app.py` | 新增 | 2026-02-09 11:04:xx | HTTP API、SSE 事件流、静态页面挂载 |
| `apps/human_thinking_forum_codex_cli/forum/models.py` | 新增 | 2026-02-09 11:01:xx | 请求模型与 Agent 定义 |
| `apps/human_thinking_forum_codex_cli/web/index.html` | 新增 | 2026-02-09 11:05:xx | 论坛主页面 |
| `apps/human_thinking_forum_codex_cli/web/app.js` | 新增 | 2026-02-09 11:05:xx | 前端交互（注册登录、发帖回帖、Agent控制、SSE） |
| `apps/human_thinking_forum_codex_cli/web/styles.css` | 新增 | 2026-02-09 11:05:xx | 页面样式 |
| `apps/human_thinking_forum_codex_cli/config/agents.json` | 新增 | 2026-02-09 11:05:xx | 4 Agent 配置 |
| `apps/human_thinking_forum_codex_cli/skills/**/SKILL.md` | 新增 | 2026-02-09 11:05:xx | 共享技能与 Agent 覆写技能 |
| `apps/human_thinking_forum_codex_cli/tests/test_store.py` | 新增 | 2026-02-09 11:05:xx | 帖子与楼层规则测试 |
| `apps/human_thinking_forum_codex_cli/tests/test_auth.py` | 新增 | 2026-02-09 11:05:xx | 注册登录测试 |
| `apps/human_thinking_forum_codex_cli/tests/test_mcp_tools.py` | 新增 | 2026-02-09 11:05:xx | MCP 工具逻辑测试 |
| `restart_forum.sh` | 新增 | 2026-02-09 11:05:xx | 一键启动脚本 |
| `docs/architecture/repo-metadata.json` | 修改 | 2026-02-09 11:06:xx-11:09:xx | 新模块与脚本元数据同步（44 条） |
| `docs/architecture/repository-structure.md` | 修改 | 2026-02-09 11:09:xx | 结构树包含新论坛模块 |
| `docs/dev_logs/2026-02-09/02-human-thinking-forum-module.md` | 新增 | 2026-02-09 11:10:xx | 本轮开发日志 |

## 变更说明（方案、影响范围、风险控制）

### 1) 论坛业务闭环

- 实现本地账号注册/登录/登出。
- 支持人类发帖、回帖（强制仅回复主帖，禁止回复回复）。
- 帖子列表返回主帖+一层回复结构。

### 2) 4 Agent 并发与 MCP 工具链

- 每个 Agent 独立线程并行循环调用 `codex exec --json`，互不等待。
- Agent 写论坛只能走 MCP tools：`forum_get_recent_posts/forum_get_post/forum_create_post/forum_reply_post/forum_get_agent_memory/forum_remember`。
- 增加异常防护：`codex` 不存在时，终止对应 Agent 的热失败循环。

### 3) Skills 自动加载与热刷新

- 扫描 `skills/shared` + `skills/agents/<agent_id>`。
- 同名技能 Agent 覆写共享基座。
- 同步到 `runtime/agent_workspaces/<agent_id>/.codex/skills`。
- 自动生成每个 Agent 工作区 `AGENTS.md`。
- 提供 `POST /api/skills/reload` 手动热刷新。

### 4) Web 与可观测性

- FastAPI 提供鉴权、论坛、Agent 控制、Skills 重载 API。
- SSE `GET /api/events/stream` 推送帖子事件与 agent 日志事件（reasoning/tool/assistant/system）。
- 前端页面支持注册登录、发帖回帖、启动/停止 Agent、查看状态和实时事件流。

## 影响范围

- 新增独立模块 `apps/human_thinking_forum_codex_cli` 与 `restart_forum.sh`。
- 文档同步变更：`docs/architecture/repo-metadata.json`、`docs/architecture/repository-structure.md`。
- 未改动现有 gomoku 业务代码路径（除工作区中其他 agent 自身改动，已按用户授权忽略）。

## 验证结果

```bash
cd apps/human_thinking_forum_codex_cli && PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py'
# 结果：通过（4 tests, OK）

bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 因无 package.json/scrips 按规则跳过）

timeout 25 bash restart_forum.sh --turn-timeout 30
# 结果：成功创建 venv 并安装依赖，服务成功启动到 http://127.0.0.1:8099 后被 timeout 中断（预期）

npm test
# 结果：失败（ENOENT: 缺少 /package.json，仓库当前不具备 npm test 前置条件）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
- Tag/Backup：本轮未创建（用户未要求）
- 工作区说明：存在其他 agent 的并行改动，用户已明确授权继续
