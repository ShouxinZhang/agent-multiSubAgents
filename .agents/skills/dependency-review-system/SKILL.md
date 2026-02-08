---
name: dependency-review-system
description: 依赖关系优先的 AI Review 总调度 Skill。通过“机械门禁 + LLM 判读 + 人工兜底”输出可执行评审结论。
---

# dependency-review-system

用于把代码评审落地为可执行流水线，核心目标是：
- 机械门禁严格阻断（构建/测试/依赖违规）
- LLM 输出结构化风险结论（含证据与置信度）
- 人只处理低置信度或高影响冲突

## 执行策略

- 默认优先 MCP tools（`review-pipeline` server）
- MCP 不可用时再使用脚本 fallback
- 追求最简链路时优先调用 `review_run` 一次完成

## 子 Skills（同模块内）

1. `subskills/collect-context.md`：收集 diff、影响文件、Git 上下文
2. `subskills/dependency-guard.md`：依赖图与分层规则机械判定
3. `subskills/risk-analyzer.md`：校验 LLM 风险报告结构与质量
4. `subskills/test-gap-mapper.md`：把风险映射到测试缺口
5. `subskills/decision-gate.md`：统一输出 PASS / BLOCK / HUMAN

## MCP 工具映射

| 子 Skill | MCP Tool | 关键参数 | Fallback 脚本 |
|---|---|---|---|
| `collect-context` | `review_collect_context` | `base`, `head`, `output` | `node scripts/review/scripts/collect-context.mjs` |
| `dependency-guard` | `review_dependency_gate` | `policy`, `output` | `node scripts/review/scripts/dependency-gate.mjs` |
| `risk-analyzer` | `review_validate_llm` | `input`, `policy`, `output` | `node scripts/review/scripts/validate-llm-report.mjs` |
| `test-gap-mapper` | `review_validate_llm` | `input`, `output` | 读取 `llm-validation.json` 中 `parsed.advisories` |
| `decision-gate` | `review_run` | `llmReport`, `allowHuman`, `base`, `head`, `output` | `node scripts/review/scripts/run-review.mjs` |

## 推荐调用顺序（MCP）

1. `review_collect_context`
2. `review_dependency_gate`
3. `review_validate_llm`
4. `review_run`

最简模式：
1. 只调用 `review_run`（内部会串联构建检查、测试、依赖门禁、LLM 校验）

## MCP 最小调用示例

```text
Tool: review_run
Arguments: { "llmReport": "scripts/review/input/llm-review.json", "allowHuman": false }
```

## 一键执行

在仓库根目录运行：

```bash
bash scripts/review/run.sh
```

默认行为：
- 执行 `scripts/check_errors.sh`
- 执行 `npm run -w web test`
- 运行依赖关系门禁（循环依赖 + 禁止边）
- 校验 LLM 风险报告（缺失或低置信度会触发 `HUMAN`）
- 生成 `scripts/review/artifacts/<run-id>/review-result.json`

## 输入与输出

输入：
- 代码状态（工作区或 `--base/--head` diff）
- 依赖策略 `scripts/review/config/policy.json`
- LLM 报告（可选）`scripts/review/input/llm-review.json`

输出：
- `PASS`：机械门禁通过，且 LLM 报告通过阈值
- `BLOCK`：机械门禁失败或 LLM 提供阻断项
- `HUMAN`：LLM 报告缺失/低置信度，需要人工裁决
