---
name: local-dev-workflow
description: 本地开发唯一入口 Skill。通过 subskills 编排实现开发、验证、文档同步与追溯闭环。
---

# local-dev-workflow（单入口模式）

## 定位

- 本仓库只保留一个顶层 Skill：`local-dev-workflow`。
- 其他能力全部通过 `subskills/` 按条件触发，避免多入口分叉。

## 主流程

```text
需求澄清 -> 方案对齐 -> 编码实现 -> 质量验证 -> 结构同步 -> 日志归档 -> Git 锚点
```

## Subskills

1. `subskills/build-check.md`
2. `subskills/repo-structure-sync.md`
3. `subskills/dev-logs.md`
4. `subskills/git-management.md`
5. `subskills/domain-data-update.md`
6. `subskills/modularization-governance.md`
7. `subskills/dependency-review-system.md`

## 执行规则

1. 开始前读取 `AGENTS.md` 与目标模块现状。
2. 编码前必须明确：变更文件、实现方式、影响范围。
3. 任何代码变更后触发 `build-check`。
4. 涉及结构变化触发 `repo-structure-sync`。
5. 每轮开发结束触发 `dev-logs`。
6. 阶段成果或大改节点触发 `git-management`。
7. 修改核心领域数据触发 `domain-data-update`。
8. 架构风险提升时按需触发治理类 subskills。

## 退出标准

1. 质量门禁通过。
2. 结构文档已同步（如有结构变更）。
3. 日志与 Git 锚点可追溯。
