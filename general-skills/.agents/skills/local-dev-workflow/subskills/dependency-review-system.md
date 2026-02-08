# subskill: dependency-review-system

## 触发条件

- 高风险改动
- 发版前评审
- 需要统一 PASS/BLOCK/HUMAN 结论

## 执行动作

```bash
bash scripts/review/run.sh
```

## 子步骤说明

详见：

- `subskills/dependency-review-system/collect-context.md`
- `subskills/dependency-review-system/dependency-guard.md`
- `subskills/dependency-review-system/risk-analyzer.md`
- `subskills/dependency-review-system/decision-gate.md`
- `subskills/dependency-review-system/test-gap-mapper.md`
