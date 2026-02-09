# 08 - 修复 Web Start 假可用（MCP 运行时未就绪）

## 用户请求

> ???

## 背景与意图

用户截图里 `Start` 可点击，但棋局长时间不落子。日志显示模型反复执行 `list_mcp_resources`，没有进入 `place_stone`。

业务影响：

- 用户误以为前端按钮无效
- 实际是后端 Python 运行时缺 `mcp` 依赖，导致 gomoku MCP 握手失败
- 状态栏只显示 `codex ready`，缺少对 MCP 可用性的透明提示

## 修改时间

2026-02-09 11:38:00 – 2026-02-09 11:46:13 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `restart_web.sh` | 修改 | 启动时自动检测 `mcp` 依赖；缺失时创建 `.venv/gomoku_web` 并安装 requirements；统一将该 Python 传给 API 与 Codex MCP |
| `apps/gomoku_codex_cli/web_api.py` | 修改 | 新增 MCP 运行时预检（`import mcp, gomoku.mcp_server`）；在 `health/state` 暴露 `mcp_ready/mcp_error/python_bin`；`start` 前置失败快速返回 |
| `apps/gomoku_web/src/App.jsx` | 修改 | 接入 `mcp_ready/mcp_error`；Start 按钮在 MCP 未就绪时禁用；新增 MCP 状态与错误徽标 |
| `docs/dev_logs/2026-02-09/08-fix-web-mcp-runtime-readiness.md` | 新增 | 本轮开发日志 |

## 变更说明

### 根因

`restart_web.sh` 使用系统 `/usr/bin/python3` 启动 API；该解释器未安装 `mcp`。Codex 调用 gomoku MCP 时握手失败（`initialize response`），导致回合长时间停留在“探测资源”而非直接落子。

### 修复策略

1. 启动链路自愈：自动准备含 `mcp` 的独立虚拟环境，避免污染系统 Python。
2. 运行前失败快返：Web API 的 `start` 在 MCP 不可用时直接返回明确错误，不再进入“假运行”。
3. 前端状态透明：新增 `mcp` readiness 徽标，避免“只看 codex ready 误判可运行”。

## 影响范围

- 影响：`restart_web` 启动链路、Web API 状态契约、Web 控件禁用逻辑
- 不影响：棋盘规则、对局引擎判定、Tk GUI 行为

## 验证结果

```bash
python3 -m py_compile apps/gomoku_codex_cli/web_api.py
# 通过

cd apps/gomoku_web && npm run lint
# 通过

cd apps/gomoku_web && npm run build
# 通过

# 冒烟：restart_web 自动补齐 mcp
# 输出包含：
# [WARN] 'python3' missing python package 'mcp'; preparing isolated venv
# [INFO] Using python runtime: .../.venv/gomoku_web/bin/python

# 冒烟：API 健康检查
curl http://127.0.0.1:8791/api/health
# 返回包含："mcp_ready": true

bash scripts/check_errors.sh
# 失败（非本次改动引入）：
# apps/human_thinking_forum_codex_cli/tests/test_mcp_tools.py
# TypeError: ForumMcpTools.__init__() missing 1 required keyword-only argument: 'auth_service'
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da`
