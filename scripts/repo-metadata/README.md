# Repo Metadata — 仓库元数据管理系统

## 业务目标

自动扫描仓库目录结构，以结构化方式管理每个目录/文件的描述信息，并自动生成架构文档。

- **扫描器**: 自动发现目录树变化（新增/删除），免去人工维护
- **CRUD**: 对每个路径维护描述、标签等元数据，支持人工精细修改和 LLM 批量补写
- **JSON 产物**: `docs/architecture/repo-metadata.json` 作为结构化元数据源
- **MD 产物**: `docs/architecture/repository-structure.md` 自动生成（只展开 2 层）
- **PG 同步**: 可选的 PostgreSQL 双向同步，支持结构化查询

## 架构

```
目录树（git ls-files）
    ↓ scan.mjs --update
repo-metadata.json（结构化元数据）
    ↓ generate-structure-md.mjs
repository-structure.md（人类可读，2 层）

可选 PG 同步:
  repo-metadata.json ⇄ PostgreSQL repo_metadata_nodes
    sync-json-to-postgres.mjs（JSON → PG）
    sync-to-json.mjs（PG → JSON）
```

## 目录结构

```
scripts/repo-metadata/
├── package.json                       # 依赖管理（pg）
├── README.md                          # 本文件
├── sql/
│   └── 001_init.sql                   # PostgreSQL 表定义
└── scripts/
    ├── scan.mjs                       # 扫描目录树，对比 JSON
    ├── crud.mjs                       # 元数据 CRUD（JSON 直接操作）
    ├── sync-json-to-postgres.mjs      # JSON → PG 同步
    ├── sync-to-json.mjs               # PG → JSON 同步
    └── generate-structure-md.mjs      # JSON → repository-structure.md
```

## 快速开始

### 1. 安装依赖（PG 同步功能需要）

```bash
cd scripts/repo-metadata && npm install
```

> scan / crud / generate 无需外部依赖，可直接使用。

### 2. 首次扫描

```bash
# 从仓库根目录运行
node scripts/repo-metadata/scripts/scan.mjs --update
```

这会扫描所有 git 追踪的文件和目录，生成初始 `docs/architecture/repo-metadata.json`。

### 3. 补写描述

```bash
# 单条设置
node scripts/repo-metadata/scripts/crud.mjs set --path web/src --description "前端源代码" --tags "frontend,react"

# 批量设置（通过 stdin JSON）
echo '[
  {"path": "web", "description": "知识图谱前端网站"},
  {"path": "docs", "description": "项目文档"}
]' | node scripts/repo-metadata/scripts/crud.mjs batch-set

# 查看未描述的条目
node scripts/repo-metadata/scripts/crud.mjs list --undescribed
```

### 4. 生成架构文档

```bash
node scripts/repo-metadata/scripts/generate-structure-md.mjs
```

会更新 `docs/architecture/repository-structure.md` 中 `<!-- REPO-TREE-START -->` 和 `<!-- REPO-TREE-END -->` 标记之间的目录树。

### 5. PG 同步（可选）

```bash
# 初始化数据库表
psql "$DATABASE_URL" -f scripts/repo-metadata/sql/001_init.sql

# JSON → PG
DATABASE_URL='postgres://...' node scripts/repo-metadata/scripts/sync-json-to-postgres.mjs

# PG → JSON
DATABASE_URL='postgres://...' node scripts/repo-metadata/scripts/sync-to-json.mjs
```

## npm 脚本（从 web/ 目录运行）

```bash
cd web
npm run repo:scan           # 扫描并报告变化
npm run repo:scan-update    # 扫描并自动更新 JSON
npm run repo:crud -- <args> # CRUD 操作
npm run repo:generate-md    # 生成 repository-structure.md
npm run repo:sync-to-db     # JSON → PG（需要 DATABASE_URL）
npm run repo:sync-from-db   # PG → JSON（需要 DATABASE_URL）
```

## JSON 数据格式

`docs/architecture/repo-metadata.json`:

```json
{
  "version": 1,
  "config": {
    "scanIgnore": ["docs/dev_logs/**", "docs/knowledge/_archive/**"],
    "generateMdDepth": 2
  },
  "updatedAt": "2026-02-07T12:00:00.000Z",
  "nodes": {
    "web": {
      "type": "directory",
      "description": "知识图谱前端网站 (Vite + React + TS)",
      "detail": "包含前端源码、构建配置、知识同步工具",
      "tags": ["frontend", "react"],
      "updatedBy": "llm",
      "updatedAt": "2026-02-07T12:00:00.000Z"
    }
  }
}
```

## 配置

在 `repo-metadata.json` 的 `config` 字段中配置:

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `scanIgnore` | 扫描时忽略的 glob 模式 | `["docs/dev_logs/**", "docs/knowledge/_archive/**"]` |
| `generateMdDepth` | 生成 MD 的默认展开深度 | `2` |

## Agent Skill 集成

`repo-structure-sync` skill 在 LLM 完成代码变更后自动:

1. 运行 `scan --update` 发现新增/删除条目
2. LLM 通过 `crud batch-set` 补写新增条目的描述
3. 运行 `generate-structure-md` 更新架构文档
