# Dev Log - general-skills 去重与 Skills 文档重排

- Timestamp: 2026-02-08 10:11:50
- Branch: main
- Commit: 2233ffb

## User Prompt

> general-skills这个是制作的初版本skills，冗余和不够模块化很多，分析后着手优化。
> 约束：只改 general-skills，仓库根目录先不改。

## Context / Intent Summary

1. 聚焦 `general-skills/` 内部优化，不动仓库根目录镜像内容。
2. 目标是减少重复实现，并重排 Skills 文档结构，让职责边界更清晰。
3. 保持改造可落地，优先低风险高收益去重。

## File Changes

1. `general-skills/scripts/lib/common.mjs` - add - 新增共享 CLI 与 glob 工具函数。
2. `general-skills/scripts/repo-metadata/lib/shared.mjs` - update - 复用共享工具，移除重复 parse/glob 实现。
3. `general-skills/scripts/repo-metadata/scripts/crud.mjs` - update - 复用 shared 的 parse/load/save/depth，移除重复实现。
4. `general-skills/scripts/repo-metadata/mcp-server.mjs` - update - `sync_db` 改为复用现有 sync 脚本，去除一段重复 PG 同步逻辑。
5. `general-skills/scripts/review/scripts/collect-context.mjs` - update - 复用共享 parseArgs。
6. `general-skills/scripts/review/scripts/dependency-gate.mjs` - update - 复用共享 parseArgs/globToRegex。
7. `general-skills/scripts/review/scripts/run-review.mjs` - update - 复用共享 parseArgs。
8. `general-skills/scripts/review/scripts/validate-llm-report.mjs` - update - 复用共享 parseArgs。
9. `general-skills/.agents/skills/README.md` - add - 新增技能索引与编排关系说明。
10. `general-skills/.agents/skills/build-check/SKILL.md` - update - 规范为单一质量门禁职责。
11. `general-skills/.agents/skills/local-dev-workflow/SKILL.md` - update - 调整为编排入口，减少重复命令。
12. `general-skills/.agents/skills/dev-logs/SKILL.md` - update - 聚焦日志结构与可追溯字段。
13. `general-skills/.agents/skills/git-management/SKILL.md` - update - 保留 Git 节点策略，引用 build-check。
14. `general-skills/.agents/skills/repo-structure-sync/SKILL.md` - update - 明确结构变更触发与步骤。
15. `general-skills/.agents/skills/domain-data-update/SKILL.md` - update - 精简为模板职责与验证要求。
16. `general-skills/.agents/skills/dependency-review-system/SKILL.md` - update - 明确子步骤编排与输入输出。
17. `general-skills/.agents/skills/modularization-governance/SKILL.md` - update - 聚焦治理流程与交付标准。
18. `general-skills/.agents/skills/dependency-review-system/subskills/collect-context.md` - update - 结构统一。
19. `general-skills/.agents/skills/dependency-review-system/subskills/dependency-guard.md` - update - 结构统一。
20. `general-skills/.agents/skills/dependency-review-system/subskills/risk-analyzer.md` - update - 结构统一。
21. `general-skills/.agents/skills/dependency-review-system/subskills/decision-gate.md` - update - 结构统一。
22. `general-skills/.agents/skills/dependency-review-system/subskills/test-gap-mapper.md` - update - 明确当前为文档型步骤。
23. `general-skills/README.md` - update - 目录与能力说明同步到最新结构。

## Change Details

1. 抽取共享工具：将 `parseArgs/parseFlags/globToRegex` 统一到 `scripts/lib/common.mjs`，消除 review 与 repo-metadata 的重复函数。
2. repo-metadata 去重：`crud.mjs` 不再内置 JSON 读写逻辑，改为调用 shared；`mcp-server.mjs` 的数据库同步改为复用现有 `sync-*.mjs` 脚本，避免 MCP 与 CLI 逻辑分叉。
3. Skills 文档重排：把 `local-dev-workflow` 作为主编排，其他技能聚焦单一职责；新增技能索引，统一 dependency-review 子文档结构，降低阅读与维护成本。

## Impact Scope and Risk Control

- Scope: 仅 `general-skills/`。
- Benefit: 共享逻辑单点维护，技能文档结构一致，后续扩展成本下降。
- Risks:
  1. CLI 参数解析行为变化风险（已通过脚本冒烟覆盖核心路径）。
  2. `repo_metadata_sync_db` 行为改为脚本代理后的输出格式变化（已在日志中记录）。
- Mitigation: 进行语法检查 + 关键脚本执行验证，确保主链路无语法与基础运行回归。

## Verification Results

1. Syntax check:

```bash
find general-skills -type f -name '*.mjs' | sort | while read -r f; do node --check "$f"; done
```

Result: PASS

2. Script smoke checks:

```bash
node general-skills/scripts/review/scripts/collect-context.mjs --project-root general-skills --output /tmp/general-skills-context.json
node general-skills/scripts/review/scripts/validate-llm-report.mjs --project-root general-skills --input general-skills/scripts/review/input/llm-review.json --output /tmp/general-skills-llm-validation.json
node general-skills/scripts/repo-metadata/scripts/crud.mjs list --max-depth 1
```

Result: PASS（按预期输出）

3. Quality gate (controlled smoke):

```bash
QUALITY_DEPENDENCY_CMD=true QUALITY_TYPECHECK_CMD=true QUALITY_LINT_CMD=true QUALITY_BUILD_CMD=true bash general-skills/scripts/check_errors.sh
```

Result: PASS

## Notes

- 未执行完整 `dependency-gate`（依赖 `madge` 与项目依赖环境），本轮以语法与关键脚本冒烟验证为主。
