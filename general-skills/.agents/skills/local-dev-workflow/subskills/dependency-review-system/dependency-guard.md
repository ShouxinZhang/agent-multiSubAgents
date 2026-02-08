# dependency-guard

## 目标

将依赖约束文档转为可执行阻断规则。

## 输入

1. `scripts/review/config/policy.json`
2. 可选 `output`

## 判定

1. `summary.cycleCount` 是否超阈值
2. `summary.forbiddenCount` 是否超阈值
3. `summary.passed` 是否为 `true`

## 执行

MCP: `review_dependency_gate`

fallback:

```bash
node scripts/review/scripts/dependency-gate.mjs --project-root . --policy scripts/review/config/policy.json
```
