# General Skills Pack

A reusable, repository-agnostic package containing:

- `AGENTS.md`（执行契约）
- `.agents/skills/`（单入口 Skill + subskills）
- `scripts/`（质量门禁、评审流水线、结构同步与治理脚本）

## Directory

```text
general-skills/
├── AGENTS.md
├── README.md
├── .agents/
│   └── skills/
│       └── local-dev-workflow/
│           ├── SKILL.md
│           └── subskills/
└── scripts/
    ├── lib/
    ├── review/
    ├── repo-metadata/
    └── modularization-governance/
```

## Skill Model

1. 仅保留一个顶层入口 Skill：`local-dev-workflow`。
2. 所有通用能力都在 `local-dev-workflow/subskills/` 中定义与触发。
3. `AGENTS.md` 负责声明触发条件与执行顺序，避免 README 承担流程指引职责。

## What Is Included

- 入口 Skill：`local-dev-workflow`
- Subskills：`build-check`、`repo-structure-sync`、`dev-logs`、`git-management`、`domain-data-update`、`modularization-governance`、`dependency-review-system`
- Script templates:
  - `scripts/lib/common.mjs`
  - `scripts/check_errors.sh`
  - `scripts/review/*`
  - `scripts/repo-metadata/*`
  - `scripts/modularization-governance/*`

## How To Use In Another Repository

1. Copy package contents to target repository root:

```bash
rsync -a general-skills/ <target-repo>/
```

2. Keep paths unchanged after copy:

- `<target-repo>/AGENTS.md`
- `<target-repo>/.agents/skills/local-dev-workflow/...`
- `<target-repo>/scripts/...`

3. Customize project settings:

- commands in `scripts/check_errors.sh`
- `scripts/review/config/policy.json`
- `scripts/modularization-governance/references/modularity-policy.template.json`

4. Smoke test:

```bash
bash scripts/check_errors.sh
node scripts/review/scripts/collect-context.mjs --project-root .
node scripts/review/scripts/dependency-gate.mjs --project-root . --policy scripts/review/config/policy.json
```

## Customization Checklist

- Replace module paths and layer rules with your project paths.
- Update build/test commands according to your stack.
- Remove scripts not needed by your repository.
- Keep domain-data constraints aligned with your own domain schema.
