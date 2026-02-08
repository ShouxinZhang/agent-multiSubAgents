## 对话记录

### 第 1 轮
- 背景: 现有五子棋 Demo 前端是原生 JS 页面，用户担心长期可维护性，并关注 Agent SDK 的业务价值。
- 用户:
  > 用js三件套不用rea ct, 后患无穷，agent SDK用来做什么呢
- 用户的意图解析: 希望确认技术路线是否需要升级到 React，并明确 Agent SDK 在业务上的实际作用，不要停留在概念解释。
- LLM思考摘要: 先给出分层解释（前端框架与智能编排职责分离），再提出可执行落地方案（React 前端 + Agent SDK 后端）。

### 第 2 轮
- 背景: 技术方向已确认，进入执行阶段。
- 用户:
  > OK, build now
  > 然后就是，最好可以你自己自主测试一下对局，看看有没有问题
- 用户的意图解析: 要求立即开工实现，并要求代理自主完成对局回归验证，给出是否存在问题的结论。
- LLM思考摘要: 按本地开发 SOP 直接实施，完成 React 重构、Agent SDK 接入、自动化自测与架构文档同步闭环。

**修改时间**: 2026-02-08 06:28:40

## 概述

将 `demos/gomoku-10x10-kernel` 升级为 React 可视化前端，并新增 Agents SDK 后端模式（默认），实现可实时观察模型上下文事件的对局系统，同时补齐自动化自测与仓库结构文档同步。

## 修改文件清单

| 文件 | 操作 | 修改时间 | 说明 |
|------|------|----------|------|
| `demos/gomoku-10x10-kernel/package.json` | 新增/修改 | 2026-02-08 06:18:04 | 新增 React/Vite/Agents SDK 依赖与脚本 |
| `demos/gomoku-10x10-kernel/package-lock.json` | 新增 | 2026-02-08 06:18:23 | 锁定依赖版本 |
| `demos/gomoku-10x10-kernel/eslint.config.js` | 新增/修改 | 2026-02-08 06:19:05 | 前端 lint 规则配置 |
| `demos/gomoku-10x10-kernel/.gitignore` | 新增 | 2026-02-08 06:17:08 | 忽略 node_modules、dist、运行期 memory json |
| `demos/gomoku-10x10-kernel/agents-sdk-agent.mjs` | 新增 | 2026-02-08 06:16:47 | Agents SDK 落子 Agent（流式事件 + 结构化输出 + 兜底） |
| `demos/gomoku-10x10-kernel/live-match.mjs` | 修改 | 2026-02-08 06:14:24 | 新增 `agents-sdk` backend 分支 |
| `demos/gomoku-10x10-kernel/server.mjs` | 修改 | 2026-02-08 06:14:43 | 默认 backend 改为 `agents-sdk`，支持 React dist 静态托管 |
| `demos/gomoku-10x10-kernel/scripts/selftest.mjs` | 新增/修改 | 2026-02-08 06:26:50 | 自动化对局自测脚本（SSE 监听 + 超时控制） |
| `demos/gomoku-10x10-kernel/README.md` | 重写 | 2026-02-08 06:16:37 | 中文运行文档与验证说明 |
| `demos/gomoku-10x10-kernel/web-react/vite.config.mjs` | 新增 | 2026-02-08 06:11:56 | React 前端构建与代理配置 |
| `demos/gomoku-10x10-kernel/web-react/index.html` | 新增 | 2026-02-08 06:12:03 | React 入口页 |
| `demos/gomoku-10x10-kernel/web-react/src/main.jsx` | 新增/修改 | 2026-02-08 06:18:29 | React 挂载入口 |
| `demos/gomoku-10x10-kernel/web-react/src/App.jsx` | 新增/修改 | 2026-02-08 06:18:53 | 实时棋盘、控制台、日志可视化 |
| `demos/gomoku-10x10-kernel/web-react/src/styles.css` | 新增 | 2026-02-08 06:15:46 | React 页面样式 |
| `docs/architecture/repo-metadata.json` | 新增/修改 | 2026-02-08 06:28:06 | 仓库结构元数据同步 |
| `docs/architecture/repository-structure.md` | 新增/修改 | 2026-02-08 06:28:06 | 目录树文档同步 |

## 具体变更描述

### 1. 前端从原生 JS 升级为 React（业务价值：可维护性）
- 问题: 原生脚本随着交互复杂度提升，状态管理与事件编排成本会快速上升。
- 方案: 新建 `web-react` 子工程，保留原棋盘展示能力，同时将 SSE 事件流映射到 React 状态与日志组件。
- 影响范围: 仅影响 `demos/gomoku-10x10-kernel` 子模块，不污染仓库其他模块。

### 2. 新增 Agents SDK backend（业务价值：更稳健的多 Agent 编排）
- 问题: 单纯 CLI 串接在会话管理与结构化输出约束方面扩展性有限。
- 方案: 新增 `AgentsSdkAgent`，基于 `@openai/agents` + `MemorySession` + `zod` 输出约束，支持流式 thinking 事件透传。
- 风险与控制:
  - 风险: 本机未配置 `OPENAI_API_KEY` 时无法直接走 SDK 推理。
  - 控制: 自动降级到 heuristic 并输出可观测错误事件，不阻断对局流程。

### 3. 自动化自测闭环（业务价值：可回归）
- 方案: 新增 `scripts/selftest.mjs`，自动起服务、触发开局、监听 SSE，直到 `match_finished` 或 `match_error`。
- 结果: 可稳定覆盖 heuristic 与 agents-sdk（回退）场景；codex-cli 在当前环境下响应较慢，出现超时（见验证结果）。

## 验证结果

- ✔ `cd demos/gomoku-10x10-kernel && npm run lint`
- ✔ `cd demos/gomoku-10x10-kernel && npm run build:frontend`
- ✔ `cd demos/gomoku-10x10-kernel && CHOKIDAR_USEPOLLING=1 CHOKIDAR_INTERVAL=1000 timeout 8s npm run dev:frontend`（Vite 正常启动）
- ✔ `cd demos/gomoku-10x10-kernel && timeout 8s node server.mjs`（服务正常启动）
- ✔ `cd demos/gomoku-10x10-kernel && npm run selftest:heuristic`（完整一局结束）
- ✔ `cd demos/gomoku-10x10-kernel && npm run selftest:agents-sdk`（未配置 API Key 时按预期回退并完成一局）
- ⚠ `cd demos/gomoku-10x10-kernel && SELFTEST_TIMEOUT_MS=240000 node scripts/selftest.mjs codex-cli` 超时（走到 `moveIndex=10`）
- ⚠ `cd demos/gomoku-10x10-kernel && SELFTEST_TIMEOUT_MS=300000 node scripts/selftest.mjs codex-cli` 仍超时（走到 `moveIndex=11`，链路可运行但真实模型单手耗时偏高）
- ⚠ `bash scripts/check_errors.sh` 失败（仓库根无 `web/` 目录，脚本当前仅面向 `web` 工作区）

## Git 锚点

- branch: `main`
- commit: `N/A`（本轮未提交，用户未要求 commit）
- backup branch: `backup/20260208-061029-gomoku-react-agents`
- tag: `checkpoint/20260208-061033-gomoku-react-agents`
- base commit: `8e26ad4`
