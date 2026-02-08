# collect-context

## 目标

收集可复现的评审上下文，作为后续步骤统一输入。

## 输入

1. 可选 `base` / `head`
2. 可选 `output`

## 产出

1. `refs.branch` / `refs.commit`
2. `changedFiles` / `totalChangedFiles`

## 执行

MCP: `review_collect_context`

fallback:

```bash
node scripts/review/scripts/collect-context.mjs --project-root . --base main --head HEAD
```
