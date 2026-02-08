---
name: modularization-governance
description: 通用模块化治理 Skill。用于通过机械量化脚本检查模块边界、依赖方向、循环依赖与变更风险，并以 PASS/REFINE/BLOCK 输出可修复反馈。适用于 LLM 分治式开发中的框架校验、自动 review 闭环、以及模块重构验收。
---

# 模块化治理工作流（机械量化版）

目标：让 Agent 在分治开发中遵循固定闭环：
1. 先把框架（层级与边界）定义正确。
2. 每轮改动都得到机械 review 反馈。
3. 按反馈修复后继续分治，直到 `PASS`。

## Workflow（必须按顺序执行）

### Step 1：先定义框架契约（Framework Contract）

做什么：
1. 创建/复制策略文件：`references/modularity-policy.template.json`。
2. 明确目标模块层级顺序（`layerOrder`）与入口文件（`entryFiles`）。
3. 设定阈值（文件行数、扇出、循环依赖、反向依赖等）。

产出：
1. 机械策略文件（JSON）。

---

### Step 2：执行基线检查（脚本）

做什么：
1. 运行模块化检查脚本：

```bash
node .agents/skills/modularization-governance/scripts/check-modularity.mjs \
  --target web/src/features/knowledge \
  --policy .agents/skills/modularization-governance/references/modularity-policy.template.json \
  --output .agents/skills/modularization-governance/artifacts/knowledge.modularity-report.json
```

2. 读取输出报告中的 `summary` 与 `findings`。
3. 运行未使用符号检查（变量/参数/import/局部函数）：

```bash
node .agents/skills/modularization-governance/scripts/check-unused-symbols.mjs \
  --target web/src/features/knowledge \
  --tsconfig web/tsconfig.json \
  --export-ignore-files index.ts,index.tsx \
  --output .agents/skills/modularization-governance/artifacts/knowledge.unused-report.json
```

产出：
1. 结构化报告（JSON）。
2. 当前状态：`PASS | REFINE | BLOCK`（modularity）。
3. 未使用符号报告（unused）。

---

### Step 3：按机械反馈分治修复

做什么：
1. 优先修复 `BLOCK` 项（如 `CIRCULAR_DEPENDENCY`、`REVERSE_LAYER_IMPORT`）。
2. 每次只处理一个问题簇（一个 cycle 或一组反向依赖）。
3. 修复后立即回到 Step 2 重新跑脚本。
4. 处理 `UNUSED_EXPORT` 时，默认优先“移除 export 暴露”而不是删除定义本体。

判定：
1. 任何时刻若仍有 `BLOCK`，不得进入收尾阶段。

---

### Step 4：收敛优化项（REFINE）

做什么：
1. 对 `REFINE` 项按收益排序处理（大文件、高扇出、深层相对路径等）。
2. 无法当轮处理的项，必须记录为明确技术债（含文件与原因）。

判定：
1. 允许存在 `REFINE` 结束当轮，但必须可追踪。

---

### Step 5：执行最终门禁

做什么：
1. 再跑一次模块化脚本，确认无 `BLOCK`。
2. 跑仓库质量门禁：

```bash
bash scripts/check_errors.sh
```

---

### Step 6：输出可机读交付

做什么：
1. 交付 `modularity-report.json`（脚本产物）和修复清单。
2. 在日志中记录：本轮 `BLOCK` 清零情况、剩余 `REFINE`、下一轮入口。

## 交付模板

```markdown
## 模块化结论
- 目标模块: `<path>`
- 结论: `PASS | REFINE | BLOCK`
- 报告: `<report-path>`

## 关键风险
1. ...
2. ...

## 已执行动作
1. ...
2. ...

## 下一步（如需）
1. ...
```

## 机械规则说明

脚本输出字段与规则定义见：
- `references/scorecard.md`（机械规则与状态机，不含人工主观评分）
- `references/refactor-playbook.md`（问题码到修复动作映射）

## 安全修复约束

1. `UNUSED_EXPORT` 仅表示“导出未被消费”，不等于“定义无价值”。
2. 默认动作：先把符号降级为模块内私有（移除 `export`）。
3. 只有在“模块内也无引用”时，才删除定义本体。
