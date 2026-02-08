# Dev Log - 单入口 Skill 收敛与 AGENTS 全中文化

- Timestamp: 2026-02-08 10:32:24
- Branch: main
- Commit: 2233ffb

## User Prompt

> 更激进；此外，AGENTS.md 全部使用中文，方便检阅。

## Context / Intent Summary

1. 对 Skill 结构做更激进收敛：仅保留 `local-dev-workflow` 一个顶层入口。
2. 其他能力全部下沉为 `local-dev-workflow/subskills/`。
3. `AGENTS.md` 全量中文，并与单入口技能编排完全对齐。

## File Changes

### 删除

1. `general-skills/.agents/skills/build-check/SKILL.md`
2. `general-skills/.agents/skills/dev-logs/SKILL.md`
3. `general-skills/.agents/skills/git-management/SKILL.md`
4. `general-skills/.agents/skills/repo-structure-sync/SKILL.md`
5. `general-skills/.agents/skills/domain-data-update/SKILL.md`
6. `general-skills/.agents/skills/dependency-review-system/SKILL.md`
7. `general-skills/.agents/skills/dependency-review-system/subskills/*`
8. `general-skills/.agents/skills/modularization-governance/SKILL.md`
9. `general-skills/.agents/skills/modularization-governance/references/*`
10. `general-skills/.agents/skills/modularization-governance/scripts/*`

### 新增

1. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system/collect-context.md`
2. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system/dependency-guard.md`
3. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system/risk-analyzer.md`
4. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system/decision-gate.md`
5. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system/test-gap-mapper.md`
6. `general-skills/scripts/modularization-governance/README.md`
7. `general-skills/scripts/modularization-governance/references/modularity-policy.template.json`
8. `general-skills/scripts/modularization-governance/references/refactor-playbook.md`
9. `general-skills/scripts/modularization-governance/references/scorecard.md`
10. `general-skills/scripts/modularization-governance/scripts/check-modularity.mjs`
11. `general-skills/scripts/modularization-governance/scripts/check-unused-symbols.mjs`

### 修改

1. `general-skills/.agents/skills/local-dev-workflow/SKILL.md` - 重写为单入口模式说明。
2. `general-skills/.agents/skills/local-dev-workflow/subskills/build-check.md` - 扩充执行标准。
3. `general-skills/.agents/skills/local-dev-workflow/subskills/repo-structure-sync.md` - 扩充触发条件与动作。
4. `general-skills/.agents/skills/local-dev-workflow/subskills/dev-logs.md` - 明确日志结构。
5. `general-skills/.agents/skills/local-dev-workflow/subskills/git-management.md` - 明确锚点策略。
6. `general-skills/.agents/skills/local-dev-workflow/subskills/domain-data-update.md` - 明确数据约束。
7. `general-skills/.agents/skills/local-dev-workflow/subskills/modularization-governance.md` - 切换到 `scripts/modularization-governance` 路径。
8. `general-skills/.agents/skills/local-dev-workflow/subskills/dependency-review-system.md` - 指向下沉后的子步骤文档。
9. `general-skills/scripts/modularization-governance/scripts/check-unused-symbols.mjs` - 默认输出目录改为 `scripts/modularization-governance/artifacts/`。
10. `general-skills/AGENTS.md` - 全量改为中文，并改写为单入口 Skill 契约。
11. `general-skills/README.md` - 同步单入口模型与目录结构。

## Change Details

1. 技能层从“多顶层 Skill”收敛为“单入口 Skill + subskills”，降低入口分叉和规则漂移。
2. 治理类脚本资产从 `.agents/skills/` 下沉至 `scripts/`，使 Skill 目录聚焦说明与编排，脚本目录聚焦执行实现。
3. `AGENTS.md` 改为纯中文，且触发条件、顺序、约束完全与入口 Skill 对齐。

## Impact Scope and Risk Control

- Scope: 仅 `general-skills/`。
- 影响：旧路径（`.agents/skills/modularization-governance/...`）迁移到 `scripts/modularization-governance/...`。
- 风险控制：同步修正 subskills 命令路径，并验证全部 mjs 语法与质量门禁脚本。

## Verification Results

1. 结构检查：

```bash
find general-skills/.agents/skills -maxdepth 4 -type f | sort
find general-skills/scripts/modularization-governance -maxdepth 4 -type f | sort
```

Result: PASS（仅保留单入口 Skill，治理脚本已下沉）

2. 语法检查：

```bash
find general-skills -type f -name '*.mjs' | sort | while read -r f; do node --check "$f"; done
```

Result: PASS

3. 质量门禁（controlled smoke）：

```bash
QUALITY_DEPENDENCY_CMD=true QUALITY_TYPECHECK_CMD=true QUALITY_LINT_CMD=true QUALITY_BUILD_CMD=true bash general-skills/scripts/check_errors.sh
```

Result: PASS
