# 开发日志：修复 GUI 报错 "Cannot find 'codex' in PATH"

## 1. 用户原始请求（引用）

> ???（附截图：点击 Start 后弹窗 `Cannot find 'codex' in PATH.`）

## 2. 轮次对话记录（背景/意图/LLM 思考摘要）

- 背景：五子棋 GUI 可启动，但点击 Start 时触发 `codex_available()` 检查失败。
- 意图：让一键脚本在不同启动上下文（终端/GUI 会话）都能稳定找到 codex。
- 关键诊断：
  - 当前环境 `which codex` 可找到：`/home/wudizhe001/.vscode-insiders/extensions/openai.chatgpt-0.5.72-linux-x64/bin/linux-x86_64/codex`
  - `codex --version` 返回 `codex-cli 0.99.0-alpha.5`
  - 说明是“运行时 PATH 不稳定”问题，而非彻底未安装。

## 3. 修改时间（精确到秒）

- 主要修改时间：2026-02-08 11:13:01 +0800

## 4. 文件清单（路径/操作/时间/说明）

- `restart.sh`（修改）
  - 新增 `CODEX_BIN` 显式路径支持。
  - 自动探测 `codex` 绝对路径（`command -v codex` + VSCode 扩展路径兜底）。
  - 启动时向 `main.py` 透传 `--codex-bin <absolute-path>`，避免 GUI 内再依赖 PATH。
- `apps/gomoku_codex_cli/README.md`（修改）
  - 增加 `CODEX_BIN="$(which codex)" bash restart.sh` 的说明。

## 5. 变更说明（方案、影响范围、风险控制）

- 方案：在启动脚本层解决路径不一致，不改核心对局逻辑。
- 影响范围：仅影响启动链路，稳定性提升。
- 风险控制：
  - 若仍无法探测到 `codex`，保持告警并允许 GUI 启动。
  - 不强依赖单一安装路径，加入通配符兜底探测。

## 6. 验证结果（check/test/build）

- 环境诊断：
  - `which codex` 成功。
  - `codex --version` 成功。
- 脚本语法：
  - `bash -n restart.sh` 通过。
- Python 单测：
  - `PYTHONPATH=apps/gomoku_codex_cli python -m unittest discover -s apps/gomoku_codex_cli/tests -p 'test_*.py'`
  - 结果：`Ran 3 tests ... OK`。
- 质量门禁：
  - `QUALITY_DEPENDENCY_CMD=true bash scripts/check_errors.sh` 通过（typecheck/lint/build 按脚本逻辑跳过）。

## 7. Git 锚点（branch/commit/tag）

- branch: `main`
- base commit: `3b6023ec486ce442641957e1eae9d4fe6b6b674b`
- tag/backup: 本轮未创建。
