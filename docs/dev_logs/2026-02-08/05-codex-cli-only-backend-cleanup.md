## 对话记录

### 第 1 轮
- 背景: Gomoku 10x10 Demo 已有 `agents-sdk/codex-cli/heuristic` 三后端并存，用户希望确认鉴权与真实调用路径。
- 用户:
  > 这三个后端里，我记得agent-sdk没有api key无法使用吧？还有两个呢？
- 用户的意图解析: 需要区分各后端的鉴权依赖，避免“看似在调模型、实际走本地兜底”的误判。
- LLM思考摘要: 先定位代码中所有后端分支与 fallback，再把系统收敛到单一可信链路。

### 第 2 轮
- 背景: 用户确认要做架构收敛，并要求去掉非目标模块。
- 用户:
  > 删除掉agents-sdk和heuristic的模块
  > 此外，我发现codex-cli好想并不是真实api调用？
- 用户的意图解析: 只保留 `codex-cli`，并且要求失败时显式报错，不允许 silently fallback。
- LLM思考摘要: 删除 `agents-sdk/heuristic` 文件与入口，改 `codex-cli` 为严格模式，补充自测证明链路确实在走 CLI 模型调用。

**修改时间**: 2026-02-08 08:17:20

## 概述
将 Gomoku Demo 收敛为 `codex-cli` 单后端，移除 `agents-sdk/heuristic` 模块与前端切换入口，并通过自测验证真实 CLI 模型对弈链路。

## 修改文件清单

| 文件 | 操作 | 修改时间 | 说明 |
|------|------|----------|------|
| `demos/gomoku-10x10-kernel/live-match.mjs` | 修改 | 2026-02-08 08:05:34 | 对局编排仅创建 `CodexCliAgent` |
| `demos/gomoku-10x10-kernel/codex-cli-agent.mjs` | 修改 | 2026-02-08 08:05:44 | 删除 heuristic fallback，异常改为直接抛错 |
| `demos/gomoku-10x10-kernel/server.mjs` | 修改 | 2026-02-08 08:05:53 | 默认/实际后端固定为 `codex-cli` |
| `demos/gomoku-10x10-kernel/web-react/src/App.jsx` | 修改 | 2026-02-08 08:06:04 | 移除后端下拉，UI 固定显示 `codex-cli` |
| `demos/gomoku-10x10-kernel/scripts/selftest.mjs` | 修改 | 2026-02-08 08:10:55 | 自测固定 `codex-cli`，默认超时提升到 300000ms |
| `demos/gomoku-10x10-kernel/package.json` | 修改 | 2026-02-08 08:06:24 | 删除 `selftest:heuristic/agents-sdk`，新增 `selftest:codex-cli` |
| `demos/gomoku-10x10-kernel/package-lock.json` | 修改 | 2026-02-08 08:07:34 | 同步依赖，移除 `@openai/agents` 直依赖 |
| `demos/gomoku-10x10-kernel/README.md` | 修改 | 2026-02-08 08:06:55 | 文档改为 codex-cli only，并补充鉴权说明 |
| `demos/gomoku-10x10-kernel/index.mjs` | 修改 | 2026-02-08 08:06:39 | 示例入口改为 `LiveMatchRunner + codex-cli` |
| `demos/gomoku-10x10-kernel/agents-sdk-agent.mjs` | 删除 | 2026-02-08 08:07:06 | 移除 Agents SDK 模块 |
| `demos/gomoku-10x10-kernel/agents.mjs` | 删除 | 2026-02-08 08:07:09 | 移除 heuristic 模块 |
| `demos/gomoku-10x10-kernel/.backup/2026-02-08-codex-only/agents-sdk-agent.mjs` | 新增 | 2026-02-08 08:04:57 | 删除前备份 |
| `demos/gomoku-10x10-kernel/.backup/2026-02-08-codex-only/agents.mjs` | 新增 | 2026-02-08 08:04:57 | 删除前备份 |
| `docs/architecture/repo-metadata.json` | 修改 | 2026-02-08 08:16:33 | 同步仓库元数据（保留 16 节点一致性） |
| `docs/architecture/repository-structure.md` | 修改 | 2026-02-08 08:16:39 | 重新生成目录树区块 |

## 具体变更描述

- 问题:
  - `codex-cli-agent.mjs` 原先存在 fallback 到本地 heuristic 的路径，导致出现“看起来在调用模型，实际本地落子”的可观测偏差。
  - 前端与后端同时暴露三后端选择，和当前业务目标（只验证 codex-cli）冲突。

- 方案:
  - 删除 `agents-sdk-agent.mjs` 与 `agents.mjs`，并在 `live-match/server/App` 三级入口上全部收敛为 `codex-cli`。
  - 将 `codex-cli-agent.mjs` 改为 strict 模式：`codex exec` 失败、返回 JSON 非法、返回落子非法时全部抛错并上报 `agent_event/match_error`。
  - 更新 README 与自测脚本，明确本 Demo 鉴权依赖 `codex login` 的本机 CLI 登录态，而非 `OPENAI_API_KEY`。

- 影响范围:
  - `demos/gomoku-10x10-kernel` 子模块（后端编排、前端控制台、自测脚本、文档）。
  - 不影响仓库其他业务模块。

## 验证结果

- ✔ `cd demos/gomoku-10x10-kernel && npm run lint`
- ✔ `cd demos/gomoku-10x10-kernel && npm run build:frontend`
- ✔ `bash scripts/restart.sh && curl -sf http://localhost:8787/api/config`（返回 `defaults.backend=codex-cli`）
- ✔ `cd demos/gomoku-10x10-kernel && npm run selftest:codex-cli`（完成 1 局，`winner=beta`）
- ⚠ `bash scripts/check_errors.sh` 失败：脚本硬编码 `web/` 子工程，但当前仓库不存在该目录（非本次改动引入）

## Git 锚点

- branch: `N/A`（当前仓库仅 `.gitattributes` / `LICENSE` 被 Git 跟踪，开发内容处于未跟踪工作区）
- commit: `N/A`（本轮未执行提交）
- tag/backup: `demos/gomoku-10x10-kernel/.backup/2026-02-08-codex-only`
