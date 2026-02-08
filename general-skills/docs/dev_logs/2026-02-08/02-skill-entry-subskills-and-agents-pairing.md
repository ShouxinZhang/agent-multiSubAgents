# Dev Log - local-dev-workflow 入口化与 AGENTS 配对调整

- Timestamp: 2026-02-08 10:25:18
- Branch: main
- Commit: 2233ffb

## User Prompt

> README 不能作为指引；如果 local-dev-workflow 作为入口，其他 skills 应作为其 subskills；AGENTS.md 需要和 skills 搭配。

## Context / Intent Summary

1. 采用 GitHub Agent Skills 的语义，将行为约束收敛到 `AGENTS.md` + `SKILL.md`。
2. 让 `local-dev-workflow` 成为唯一默认入口，其余能力以 subskills 形式挂接。
3. 移除技能层级额外导引 README，避免多来源规范。

## File Changes

1. `general-skills/.agents/skills/README.md` - delete - 删除 skills 层导引文件。
2. `general-skills/.agents/skills/local-dev-workflow/SKILL.md` - update - 定义入口定位、subskills 映射、触发规则。
3. `general-skills/.agents/skills/local-dev-workflow/subskills/build-check.md` - add - 子技能映射。
4. `general-skills/.agents/skills/local-dev-workflow/subskills/repo-structure-sync.md` - add - 子技能映射。
5. `general-skills/.agents/skills/local-dev-workflow/subskills/dev-logs.md` - add - 子技能映射。
6. `general-skills/.agents/skills/local-dev-workflow/subskills/git-management.md` - add - 子技能映射。
7. `general-skills/.agents/skills/local-dev-workflow/subskills/domain-data-update.md` - add - 子技能映射。
8. `general-skills/.agents/skills/local-dev-workflow/subskills/modularization-governance.md` - add - 子技能映射。
9. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system.md` - add - 子技能映射。
10. `general-skills/AGENTS.md` - update - 增加 AGENTS + Skills 配对规则与 mandatory workflow 对应关系。
11. `general-skills/README.md` - update - 改为结构说明，不再把 README 当作流程指引。

## Change Details

1. 把 `local-dev-workflow` 明确成默认入口 Skill，其他技能按条件通过 `subskills/*` 触发，形成可执行编排层。
2. 将“执行契约”固定在 `AGENTS.md`，并用配对规则约束触发逻辑，降低多文档冲突。
3. 保留各技能独立 `SKILL.md`（支持显式点名调用），但主路径由入口 Skill 的 subskills 统一串联。

## Impact Scope and Risk Control

- Scope: 仅 `general-skills/` 文档与技能结构。
- Risks:
  1. 迁移方若依赖旧的 skills README，会出现路径变化。
  2. 子技能目录增加后，维护者需要遵循新的入口编排。
- Mitigation:
  1. 在 `general-skills/README.md` 明确 Skill Model。
  2. 在 `AGENTS.md` 固化触发条件和优先级。

## Verification Results

1. 结构检查：

```bash
find general-skills/.agents/skills -maxdepth 4 -type f | sort
```

Result: PASS（`local-dev-workflow/subskills/` 已生效，skills README 已删除）

2. 质量门禁（controlled smoke）：

```bash
QUALITY_DEPENDENCY_CMD=true QUALITY_TYPECHECK_CMD=true QUALITY_LINT_CMD=true QUALITY_BUILD_CMD=true bash general-skills/scripts/check_errors.sh
```

Result: PASS

## External Reference

- GitHub Docs: About agent skills
  - https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
