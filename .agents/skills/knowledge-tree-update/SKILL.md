---
name: knowledge-tree-update
description: 知识图谱数据维护规范。当需要添加、修改或删除知识树节点时使用此技能。适用于编辑 web/src/data/knowledge-tree.ts 文件。
---

# 知识树数据维护规范

知识图谱的数据存储在 `web/src/data/knowledge-tree.ts`，所有节点的增删改必须遵循以下规范。

## 数据结构

```typescript
interface KnowledgeNode {
  id: string;           // 唯一标识
  label: string;        // 节点显示名称
  description?: string; // 节点描述（点击时显示）
  children?: KnowledgeNode[]; // 子节点
  color?: string;       // 颜色（仅根节点需要设置）
}
```

## ID 命名规范

| 层级 | 前缀 | 示例 |
|------|------|------|
| 根节点 | 类别英文 | `vibe-coding`, `agent-dev`, `llm-fundamental` |
| 二级节点 | 根缩写 + 类别 | `vc-prompt-engineering`, `ad-tools`, `llm-training` |
| 三级节点 | 二级缩写 + 名称 | `vc-pe-context`, `ad-tools-mcp`, `llm-train-sft` |

规则：
- 全小写，用连字符 `-` 分隔单词
- **全局唯一**，不能重复
- 前缀体现父级层级关系

## 颜色体系

根节点颜色（水果色系）：
- 🍊 Vibe Coding Skills: `#f97316` (橘橙)
- 🥝 Agent Dev: `#22c55e` (猕猴桃绿)
- 🫐 LLM Fundamental: `#a855f7` (蓝莓紫)

子节点自动继承父级颜色，无需手动设置。

## 操作流程

### 添加知识点

1. 确定归属的父类别
2. 按命名规范生成 `id`
3. 在对应 `children` 数组中添加节点对象
4. 运行 `cd web && npm run test` 确保 ID 唯一性测试通过
5. 运行 `bash scripts/check_errors.sh` 确保构建通过

### 修改知识点

1. 只修改 `label` 或 `description`，不要轻易改 `id`（会破坏已有引用）
2. 如需改 `id`，需全局搜索确认无其他引用

### 删除知识点

1. 删除节点及其所有子节点
2. 确认无其他代码引用该节点的 `id`

## 注意事项

- 每个根类别至少保持 3 个二级分类
- 每个二级分类建议 3-5 个子节点
- `description` 中文简述，控制在 30 字以内
- 添加新的根类别时，需要同步更新 `KnowledgeGraph.tsx` 中的 `FRUIT_ICONS` 映射和图例面板
