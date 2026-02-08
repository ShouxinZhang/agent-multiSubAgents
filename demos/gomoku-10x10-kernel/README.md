# Gomoku 10x10 多 Agent 实时 Demo

这是一个最小可运行内核，目标是验证：

- `10x10` 五子棋裁判内核（连 5 判胜）
- 多 Agent 对弈（`alpha` vs `beta`）
- 实时思考上下文可视化（SSE 推流到 React UI）
- 本地记忆（`memory/*.json`）

## 技术形态

- 前端：`React + Vite`
- 后端：`Node.js` HTTP + SSE
- Agent 后端：`codex-cli`（唯一后端）
- 默认模型：`gpt-5.3-codex`

## 目录说明

- `engine.mjs`：棋盘规则、合法落子、胜负判定
- `memory-store.mjs`：本地 JSON 记忆持久化
- `codex-cli-agent.mjs`：基于 Codex CLI 的落子 Agent（流式事件）
- `live-match.mjs`：对局编排与事件分发
- `server.mjs`：API + SSE + 静态资源服务
- `web-react/`：React 前端工程
- `restart.sh`：一键重启 Web GUI（自动构建前端并重启服务）
- `scripts/selftest.mjs`：自动化自测脚本（起服、开局、等待结果）

## 运行（生产构建方式）

```bash
cd demos/gomoku-10x10-kernel
npm install
npm run build:frontend
node server.mjs
```

打开：

- `http://localhost:8787`

## 一键重启 GUI

```bash
cd demos/gomoku-10x10-kernel
./restart.sh
```

可选自定义端口：

```bash
cd demos/gomoku-10x10-kernel
PORT=8790 ./restart.sh
```

## 开发模式（前后端分离）

终端 1：

```bash
cd demos/gomoku-10x10-kernel
node server.mjs
```

终端 2：

```bash
cd demos/gomoku-10x10-kernel
npm run dev:frontend
```

开发地址：

- `http://localhost:5173`（Vite，已代理 `/api` 与 `/events` 到 `8787`）

## 环境变量

- `PORT`：后端端口（默认 `8787`）
- `GOMOKU_MODEL`：模型名（默认 `gpt-5.3-codex`）
- `GOMOKU_GAMES`：对局局数（默认 `1`）
- `GOMOKU_TURN_DELAY_MS`：每手延迟毫秒（默认 `220`）

## Codex CLI 鉴权说明

本 Demo 不使用 `OPENAI_API_KEY`。它依赖本机 `codex` CLI 登录态：

```bash
codex login
codex --version
```

若 `codex exec` 无法调用模型，后端会直接报错并在 UI 的 `System Timeline` 显示，不会再自动降级到本地 heuristic。

## 实时思考上下文

UI 展示的是 `codex exec --json` 流中的可见事件（如 `reasoning`、`agent_message`、`usage`），并非隐藏推理明文。

## 自动化自测

```bash
cd demos/gomoku-10x10-kernel
npm run selftest:codex-cli
```
