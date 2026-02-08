---
name: repo-structure-sync
description: 仓库架构文档同步。当文件结构发生变化（新增/删除/移动文件或目录）时，必须使用此技能更新仓库元数据和架构文档。
---

# 仓库架构文档同步规范（v3 — MCP + repo-metadata）

`docs/architecture/repo-metadata.json` 是仓库结构元数据的 source of truth，`repository-structure.md` 是其自动生成的人类可读版本。

本技能通过 MCP Server `repo-metadata` 提供的工具直接操作，无需拼终端命令。

## 触发条件

以下操作后必须同步元数据：
- 新增文件或目录
- 删除文件或目录
- 移动或重命名文件
- 新增 npm 依赖（更新技术栈表格）
- 新增 npm scripts（更新命令列表）

## 执行流程（MCP Tools）

### 1. 扫描 + 更新元数据 JSON

调用 MCP 工具 `repo_metadata_scan`：

```
repo_metadata_scan({ update: true })
```

自动发现新增/删除的路径并更新 `repo-metadata.json`。

### 2. 补写新增条目的描述

对于扫描发现的新增条目（description 为空），调用 `repo_metadata_batch_set`：

```
repo_metadata_batch_set({
  items: [
    { path: "新增路径1", description: "一句话描述" },
    { path: "新增路径2", description: "一句话描述" }
  ]
})
```

或单条设置：

```
repo_metadata_set({ path: "xxx", description: "描述" })
```

### 3. 生成架构文档

调用 `repo_metadata_generate_md`：

```
repo_metadata_generate_md({})
```

更新 `repository-structure.md` 中的目录树（只展开 2 层）。

### 4. （可选）同步到 PostgreSQL

```
repo_metadata_sync_db({ direction: "json-to-pg" })
```

### 5. 手动维护其他章节

`repository-structure.md` 中除了 `<!-- REPO-TREE-START -->` 到 `<!-- REPO-TREE-END -->` 之间的自动生成内容外，其他章节（技术栈、开发命令等）仍需手动维护。

## MCP Tools 完整参考

| 工具 | 用途 |
|------|------|
| `repo_metadata_scan` | 扫描目录变化（update: true 自动更新 JSON） |
| `repo_metadata_get` | 获取单条元数据 |
| `repo_metadata_set` | 设置/更新描述 |
| `repo_metadata_batch_set` | 批量补写描述 |
| `repo_metadata_list` | 列出/查询条目（支持过滤） |
| `repo_metadata_delete` | 删除条目（级联删除子路径） |
| `repo_metadata_generate_md` | 生成 repository-structure.md |
| `repo_metadata_sync_db` | JSON ⇄ PG 同步 |

## 后备方案（CLI 命令）

如果 MCP 工具不可用，仍可通过终端运行：

```bash
node scripts/repo-metadata/scripts/scan.mjs --update
node scripts/repo-metadata/scripts/crud.mjs batch-set < descriptions.json
node scripts/repo-metadata/scripts/generate-structure-md.mjs
```

## 注意事项

- 不要手动编辑 `<!-- REPO-TREE-START -->` 到 `<!-- REPO-TREE-END -->` 之间的内容
- `config.scanIgnore` 控制哪些路径不被扫描
- 描述应简洁，一个文件/目录一句话
- 此步骤在开发日志记录之前完成
