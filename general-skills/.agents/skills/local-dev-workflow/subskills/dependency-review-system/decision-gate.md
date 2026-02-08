# decision-gate

## 目标

把多源结果统一为单一结论，便于 CI 与人工处理。

## 判定顺序

1. 机械门禁失败 -> `BLOCK`
2. 机械门禁通过但 LLM 缺失/低置信度 -> `HUMAN`
3. 机械门禁通过且 LLM 阻断 -> `BLOCK`
4. 其余 -> `PASS`

## 输出

- `review-result.json`
- 默认退出码：`PASS=0`，`BLOCK/HUMAN=1`

## 执行

MCP: `review_run`

fallback:

```bash
node scripts/review/scripts/run-review.mjs --project-root . --llm-report scripts/review/input/llm-review.json
```
