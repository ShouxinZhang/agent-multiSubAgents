## 对话记录

### 第 1 轮
- 背景: 用户在 GUI 页面看到 SSE 持续断连，怀疑 `restart.sh` 与手工启动行为不一致。
- 用户:
  > 不对啊，restart.sh和终端启动应该是一致的才对
- 用户的意图解析: 需要确认重启脚本是否存在行为偏差，并修复“看起来启动成功但前端不断断连”的不确定性。
- LLM思考摘要: 先做两种启动方式的存活对比，再增强脚本为“启动后健康检查”，避免假成功状态。

**修改时间**: 2026-02-08 07:56:40

## 概述

增强 `demos/gomoku-10x10-kernel/restart.sh`：新增启动后 `/api/config` 健康探测与失败日志回显，确保脚本返回成功时后端一定可用。

## 修改文件清单

| 文件 | 操作 | 修改时间 | 说明 |
|------|------|----------|------|
| `demos/gomoku-10x10-kernel/restart.sh` | 修改 | 2026-02-08 07:55:18 | 新增 readiness 检查、失败回显日志、超时退出 |

## 具体变更描述

### 问题
- 原脚本在启动后台进程后立即打印成功，若后端随后退出，前端会进入 SSE 重连风暴，用户误判为“脚本成功但服务不可用”。

### 方案
- 启动后轮询 `http://localhost:$PORT/api/config`，默认等待 `15s`（可通过 `READY_TIMEOUT_SEC` 覆盖）。
- 若进程中途退出，立即输出 `server.log` 末尾并返回失败。
- 超时未就绪也返回失败并回显日志。

### 影响范围
- 仅影响 `gomoku-10x10-kernel` 的重启体验，不影响对局内核与前端逻辑。

## 验证结果

- ✔ `bash scripts/restart.sh`（可成功启动并返回 PID/URL）
- ✔ `curl -s http://localhost:8787/api/config`（健康检查通过）
- ✔ `cd demos/gomoku-10x10-kernel && npm run lint`
- ✔ `cd demos/gomoku-10x10-kernel && npm run build:frontend`

## Git 锚点

- branch: `main`
- commit: `N/A`（本轮未提交，用户未要求 commit）
- tag/backup: `N/A`

