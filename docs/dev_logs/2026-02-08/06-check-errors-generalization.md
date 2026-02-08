## 对话记录

### 第 1 轮
- 背景: 用户要求把仓库级质量门禁脚本 `scripts/check_errors.sh` 从固定 `web/` 路径改为通用模式。
- 用户:
  > check_errors进行通用化修复
- 用户的意图解析: 需要一个可复用的构建检查入口，能够在不同目录结构下自动定位可检查工程，避免因目录假设导致误失败。
- LLM思考摘要: 保持原有命令接口不变，改造目标识别与步骤执行策略（支持 skip），并用当前仓库场景做完整回归验证。

**修改时间**: 2026-02-08 09:39:27

## 概述
将 `scripts/check_errors.sh` 改造为自动识别目标工程的通用检查脚本，解决仓库无 `web/` 目录时的固定路径失败问题。

## 修改文件清单

| 文件 | 操作 | 修改时间 | 说明 |
|------|------|----------|------|
| `scripts/check_errors.sh` | 修改 | 2026-02-08 09:38:25 | 增加目标工程自动识别、脚本能力检测与 skip 机制 |

## 具体变更描述

- 问题:
  - 原脚本强依赖 `PROJECT_ROOT/web`，在当前仓库（仅有 `demos/gomoku-10x10-kernel`）下会直接失败。

- 方案:
  - 新增目标识别优先级：`CHECK_TARGET_DIR` 覆盖 > workspace > `web/` > 根目录 > 自动扫描子项目 `package.json`。
  - 子项目自动扫描时按路径与脚本能力打分，优先业务目录（如 `demos/*`），降低 `scripts/*` 工具目录优先级。
  - 检查逻辑改为能力感知：
    - TypeScript：`typecheck`/`tsc`/`tsconfig.json` 三层回退；缺失则 `skip`
    - Lint：`lint` 脚本优先，否则尝试 ESLint 配置；缺失则 `skip`
    - Build：`build` -> `build:frontend` -> `vite.config.*`；缺失则 `skip`
  - 结果汇总保留 `通过/失败` 并新增 `跳过` 统计。

- 影响范围:
  - 仅影响仓库级质量门禁脚本行为，不改业务代码。

## 验证结果

- ✔ `bash scripts/check_errors.sh`
- ✔ `bash scripts/check_errors.sh --lint`
- ✔ `bash scripts/check_errors.sh --build`
- ✔ `bash scripts/check_errors.sh --tsc`

验证结论：脚本已自动命中 `demos/gomoku-10x10-kernel`，并在缺少 TypeScript 配置时输出 `skip` 而非失败。

## Git 锚点

- branch: `N/A`（当前仓库工作区为未跟踪状态）
- commit: `N/A`（本轮未执行提交）
- tag/backup: `N/A`
