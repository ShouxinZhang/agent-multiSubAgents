## 对话记录

### 第 1 轮
- 背景: 五子棋 Demo 已有 React 版本与旧版原生前端并存，用户希望收敛到单一前端实现并提升运维便利性。
- 用户:
  > 哦哦，那把那个什么来着，对，把旧版本的删除掉，保留最新版本的react就可以了
  > 创建一个restart.sh, 方便我可以重启web GUI
- 用户的意图解析: 删除历史前端资产，仅保留 React GUI，并增加一键重启入口，降低本地调试与演示操作成本。
- LLM思考摘要: 先做删除前备份，再移除 `web/` 旧页面并将服务端改为 React-only，最后新增 `restart.sh` 并完成可运行验证。

**修改时间**: 2026-02-08 07:13:10

## 概述

已移除 `demos/gomoku-10x10-kernel/web/` 旧版原生页面，统一到 React 前端，并新增 `restart.sh` 支持一键构建+重启 GUI。

## 修改文件清单

| 文件 | 操作 | 修改时间 | 说明 |
|------|------|----------|------|
| `demos/gomoku-10x10-kernel/web/index.html` | 删除 | 2026-02-08 07:10:36 | 删除旧版原生页面入口 |
| `demos/gomoku-10x10-kernel/web/app.js` | 删除 | 2026-02-08 07:10:31 | 删除旧版原生前端脚本 |
| `demos/gomoku-10x10-kernel/web/styles.css` | 删除 | 2026-02-08 07:10:45 | 删除旧版原生样式 |
| `demos/gomoku-10x10-kernel/server.mjs` | 修改 | 2026-02-08 07:10:10 | 移除 legacy web fallback，改为 React-only 静态托管 |
| `demos/gomoku-10x10-kernel/restart.sh` | 新增 | 2026-02-08 07:10:20 | 一键重启 GUI（构建前端 + 重启 server） |
| `demos/gomoku-10x10-kernel/package.json` | 修改 | 2026-02-08 07:11:08 | 新增 `restart:gui` 脚本 |
| `demos/gomoku-10x10-kernel/.gitignore` | 修改 | 2026-02-08 07:12:47 | 忽略运行时 `.run/` 目录 |
| `demos/gomoku-10x10-kernel/README.md` | 修改 | 2026-02-08 07:11:00 | 增加 `restart.sh` 使用说明 |
| `docs/architecture/repo-metadata.json` | 修改 | 2026-02-08 07:11:56 | 同步结构元数据（含 `restart.sh` 与 `web-react` 描述） |
| `docs/architecture/repository-structure.md` | 修改 | 2026-02-08 07:11:56 | 重新生成目录结构文档 |

## 具体变更描述

### 1. 删除旧版前端并保留 React
- 问题: 同一 demo 内存在两套 GUI（原生 + React），维护路径重复，容易出现行为不一致。
- 方案: 删除 `web/` 目录全部旧文件，`server.mjs` 不再回退到 legacy 页面，仅服务 React 构建产物。
- 风险控制: 删除前已做备份到 `/tmp/gomoku-legacy-web-backup-20260208-071000`。

### 2. 新增一键重启脚本
- 方案: 新增 `demos/gomoku-10x10-kernel/restart.sh`，执行流程为：停止旧进程 → 释放端口 → 构建 React → 启动 server。
- 业务收益: 演示时无需手动敲多条命令，降低重启失败概率与操作成本。

## 验证结果

- ✔ `node --check demos/gomoku-10x10-kernel/server.mjs`
- ✔ `cd demos/gomoku-10x10-kernel && npm run lint`
- ✔ `cd demos/gomoku-10x10-kernel && npm run build:frontend`
- ✔ `cd demos/gomoku-10x10-kernel && ./restart.sh`（可启动并返回 `/api/config`）
- ✔ `cd demos/gomoku-10x10-kernel && npm run selftest:heuristic`（对局完成）
- ✔ `cd demos/gomoku-10x10-kernel && ./restart.sh` 二次回归（重启后 `api/config` 正常）

## Git 锚点

- branch: `main`
- commit: `N/A`（本轮未提交，用户未要求 commit）
- backup branch: `backup/20260208-070952-remove-legacy-web`
- tag: `checkpoint/20260208-070952-remove-legacy-web`
- base commit: `8e26ad4`
