# subskill: modularization-governance

## 触发条件

- 模块边界调整
- 架构重构验收
- 依赖方向风险升高

## 执行动作

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

## 判定原则

- 先清 `BLOCK`，再收敛 `REFINE`。
