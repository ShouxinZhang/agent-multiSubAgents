# 04 - Web 前端壳（React + Vite + Tailwind + shadcn 风格）接入事件流

## 用户请求

> 起一个前端壳并接这个事件流

## 背景与意图

当前 Tk GUI 适合本地运行，但对“动态调试与回放观察”不够高效。用户明确要求启用 Web 前端壳，并接入现有对局状态与思考流事件。

目标：

1. 建立可独立运行的 Web UI 壳
2. 接入 `state.json + turn_events.jsonl` 动态流
3. 提供与现有桌面版一致的回放视图（棋盘、回合记录、步骤思考流、左右 Agent 日志）

## 修改时间

2026-02-09 11:00:00 – 2026-02-09 11:08:40 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/web_api.py` | 新增 | 轻量 HTTP API，读取 runtime 下 `state.json/memory.json/turn_events.jsonl` 并提供 `/api/state` |
| `apps/gomoku_codex_cli/README.md` | 修改 | 增加 Web Shell 启动说明 |
| `apps/gomoku_web/package.json` | 新增/修改 | 新建 Vite React 工程并加入 Tailwind + shadcn 风格依赖 |
| `apps/gomoku_web/package-lock.json` | 新增/修改 | 前端依赖锁文件 |
| `apps/gomoku_web/tailwind.config.js` | 新增/修改 | Tailwind 主题与扫描路径配置 |
| `apps/gomoku_web/postcss.config.js` | 新增 | Tailwind PostCSS 配置 |
| `apps/gomoku_web/vite.config.js` | 新增/修改 | 配置 `/api` 代理到 `127.0.0.1:8787` |
| `apps/gomoku_web/index.html` | 新增 | Vite 入口 |
| `apps/gomoku_web/eslint.config.js` | 新增 | 前端 lint 配置 |
| `apps/gomoku_web/.gitignore` | 新增 | 前端忽略规则 |
| `apps/gomoku_web/README.md` | 新增/修改 | Web 壳使用说明 |
| `apps/gomoku_web/src/main.jsx` | 新增/修改 | React 入口 |
| `apps/gomoku_web/src/index.css` | 新增/修改 | Tailwind 基础样式与主题变量 |
| `apps/gomoku_web/src/App.jsx` | 新增/修改 | 三栏回放 UI、轮询 `/api/state`、回放控制逻辑 |
| `apps/gomoku_web/src/lib/utils.js` | 新增 | `cn()` 工具函数（clsx + tailwind-merge） |
| `apps/gomoku_web/src/lib/replay.js` | 新增 | 事件转回放模型、棋盘快照构建 |
| `apps/gomoku_web/src/components/gomoku-board.jsx` | 新增 | SVG 棋盘渲染组件 |
| `apps/gomoku_web/src/components/ui/button.jsx` | 新增 | shadcn 风格按钮组件 |
| `apps/gomoku_web/src/components/ui/card.jsx` | 新增 | shadcn 风格卡片组件 |
| `apps/gomoku_web/src/components/ui/badge.jsx` | 新增 | shadcn 风格标签组件 |
| `apps/gomoku_web/src/components/ui/separator.jsx` | 新增 | 分隔线组件 |
| `apps/gomoku_web/src/components/ui/scroll-area.jsx` | 新增 | Radix ScrollArea 封装 |
| `restart_web.sh` | 新增 | 一键启动 web_api + Vite dev server |
| `docs/architecture/repo-metadata.json` | 同步更新 | 结构同步脚本输出 |
| `docs/architecture/repository-structure.md` | 同步更新 | 结构同步脚本输出 |
| `docs/dev_logs/2026-02-09/04-web-shell-react-vite-tailwind-shadcn.md` | 新增 | 本次开发记录 |

## 变更说明

### 1. 新增 Web API（无额外 Python 依赖）

- 基于 `http.server` 实现轻量接口：
  - `GET /api/health`
  - `GET /api/state`
- `GET /api/state` 返回：`state + memory + events`
- 容错策略：文件不存在或 JSON 解析失败时使用安全默认值

### 2. 新增 React 前端壳

- 技术栈：`React + Vite + TailwindCSS + shadcn 风格组件 + Radix ScrollArea`
- UI 结构：
  - 顶部：回放控制（首步/前一步/后一步/末步/自动播放/速度）+ 状态徽标
  - 左右：Agent B / Agent W 日志
  - 中间：棋盘 + 回合记录 + 当前步思考流
- 数据流：每秒轮询 `/api/state`，并将 `events` 重建为 `seq -> turn entries` 映射

### 3. 启动脚本与说明

- 新增 `restart_web.sh`：
  - 启动 `web_api.py`
  - 启动 `apps/gomoku_web` 的 Vite dev server
- 在 `apps/gomoku_codex_cli/README.md` 中补充 Web Shell 启动说明

## 影响范围

- 新增一套独立 Web 观察壳，不影响现有 Tk GUI 主流程
- 读取同一 runtime 数据文件，可并行用于调试与回放

## 风险控制

- API 仅读取 runtime 文件，不更改对局状态
- 前端轮询模式实现简单稳定，避免引入额外实时通信依赖
- 对异常事件行做容错跳过，防止单条坏数据影响整体渲染

## 验证结果

```bash
# Python API 语法
python3 -m py_compile apps/gomoku_codex_cli/web_api.py
# 结果：通过

# 前端质量
cd apps/gomoku_web && npm run lint
# 结果：通过

cd apps/gomoku_web && npm run build
# 结果：通过

# API 冒烟
curl http://127.0.0.1:8787/api/health
curl http://127.0.0.1:8787/api/state
# 结果：返回 ok + state/events

# 仓库门禁
bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 按仓库脚本规则跳过）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
