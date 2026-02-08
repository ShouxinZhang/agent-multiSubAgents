---
name: git-management
description: Git 管理规范。出现阶段性成果或准备进行大改动时，使用此技能建立可回滚、可追溯的版本控制节奏。
---

# Git 管理规范

## 目标

在阶段性交付和大改动场景下，确保代码始终可回滚、可追溯、可交接。

## 触发条件

满足以下任一条件时调用本技能：

- 已形成阶段性成果（功能跑通、Bug 闭环、文档更新自洽）。
- 准备进行大改动（跨模块重构、批量文件改动、核心链路调整）。

## 执行流程

### 1) 阶段性成果提交

```bash
git add -A
git commit -m "<type>: <milestone-summary>"
```

要求：

- 提交信息必须表达业务结果，不只写技术动作。
- 一次提交只聚焦一个目标，避免混合无关内容。

提交后立即获取锚点：

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
```

### 2) 大改动前保护点

至少执行一项，建议两项都执行：

```bash
git branch backup/<date>-<topic>
git tag -a checkpoint/<date>-<topic> -m "before large change"
```

### 3) 大改动中提交节奏

- 每完成一个可验证子目标即提交一次。
- 避免“超大单提交”，降低回滚与定位成本。

### 4) 回写开发日志（必做）

- 将本轮 `branch / commit / tag / backup branch` 回写到对应 `docs/dev_logs/...` 日志的“Git 锚点”章节。
- 若本轮未提交，写明 `commit: N/A` 与原因，保证后续追溯链不丢失。

## 质量门禁

提交到主开发分支前必须通过：

```bash
bash scripts/check_errors.sh
```

若涉及测试变更，补充：

```bash
cd web && npm run test
```

## 禁止行为

- 无备份点直接执行破坏性改动。
- 多个无关目标混入同一次提交。
- 跳过开发日志 `docs/dev_logs` 直接结束任务。
