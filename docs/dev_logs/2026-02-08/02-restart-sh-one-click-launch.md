# 开发日志：新增一键启动脚本 restart.sh

## 1. 用户原始请求（引用）

> 创建一个restart.sh, 一键启动

## 2. 轮次对话记录（背景/意图/LLM 思考摘要）

- 背景：`apps/gomoku_codex_cli` 已可运行，但启动步骤需要手动进入目录并处理环境。
- 意图：提供仓库根目录一键重启/启动能力，降低使用门槛。
- 关键决策：
  - 在仓库根目录新增 `restart.sh`，保持命令最短路径。
  - 脚本支持“重启”语义：尝试结束已有 `main.py` 进程后再启动。
  - 自动准备虚拟环境并在缺少 `mcp` 时自动安装依赖。

## 3. 修改时间（精确到秒）

- 主要修改时间：2026-02-08 11:09:53 +0800

## 4. 文件清单（路径/操作/时间/说明）

- `restart.sh`（新增）
  - 一键重启并启动五子棋：停旧进程、准备 venv、检查依赖、启动 GUI。
- `apps/gomoku_codex_cli/README.md`（修改）
  - 增加 `bash restart.sh` 的启动方式说明。
- `docs/architecture/repo-metadata.json`（更新）
  - 同步新增 `restart.sh` 与 `docs/dev_logs` 节点。
- `docs/architecture/repository-structure.md`（更新）
  - 结构文档自动生成更新。

## 5. 变更说明（方案、影响范围、风险控制）

- 方案：仅新增一份启动脚本并补充文档，不改核心对局逻辑。
- 影响范围：启动链路更短，便于演示和重复使用。
- 风险控制：
  - 仅按进程特征 `apps/gomoku_codex_cli/main.py` 进行停止，避免误杀范围扩大。
  - 缺少 `codex` 时给出警告，不阻断本地界面启动调试。

## 6. 验证结果（check/test/build）

- 脚本语法：
  - `bash -n restart.sh` 通过。
- Python 单元测试：
  - `PYTHONPATH=apps/gomoku_codex_cli python -m unittest discover -s apps/gomoku_codex_cli/tests -p 'test_*.py'`
  - 结果：`Ran 3 tests ... OK`。
- 质量门禁：
  - `QUALITY_DEPENDENCY_CMD=true bash scripts/check_errors.sh` 通过（typecheck/lint/build 按脚本逻辑跳过）。
- 结构文档同步：
  - `node scripts/repo-metadata/scripts/scan.mjs --update` 通过。
  - `node scripts/repo-metadata/scripts/generate-structure-md.mjs` 通过。

## 7. Git 锚点（branch/commit/tag）

- branch: `main`
- base commit: `3b6023ec486ce442641957e1eae9d4fe6b6b674b`
- tag/backup: 本轮未创建。
