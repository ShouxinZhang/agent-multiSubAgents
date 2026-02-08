# risk-analyzer

## 目标

校验 LLM 风险报告是否结构完整、可被机器裁决。

## 输入

1. `input`（默认 `scripts/review/input/llm-review.json`）
2. `policy`（置信度阈值）
3. 可选 `output`

## 关键输出

1. `status`: `pass | block | human_required`
2. `valid`: 结构化校验结果
3. `reasons`: 阻断或人工介入原因
4. `parsed`: 原始报告快照

## 执行

MCP: `review_validate_llm`

fallback:

```bash
node scripts/review/scripts/validate-llm-report.mjs --project-root . --input scripts/review/input/llm-review.json
```
