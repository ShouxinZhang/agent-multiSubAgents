# modularization-governance scripts

模块化治理脚本资产（从 Skill 目录下沉到 `scripts/` 以支持单入口 Skill 架构）。

## 包含内容

- `scripts/check-modularity.mjs`
- `scripts/check-unused-symbols.mjs`
- `references/modularity-policy.template.json`
- `references/scorecard.md`
- `references/refactor-playbook.md`

## 常用命令

```bash
node scripts/modularization-governance/scripts/check-modularity.mjs \
  --target <module-path> \
  --policy scripts/modularization-governance/references/modularity-policy.template.json \
  --output scripts/modularization-governance/artifacts/<module>.modularity-report.json

node scripts/modularization-governance/scripts/check-unused-symbols.mjs \
  --target <module-path> \
  --tsconfig <tsconfig-path> \
  --export-ignore-files index.ts,index.tsx \
  --output scripts/modularization-governance/artifacts/<module>.unused-report.json
```
