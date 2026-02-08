#!/usr/bin/env node
/**
 * crud.mjs — 仓库元数据 CRUD（直接操作 repo-metadata.json）
 *
 * 用法:
 *   node crud.mjs get    --path <path>
 *   node crud.mjs set    --path <path> [--description <text>] [--detail <text>] [--tags <a,b,c>] [--type <file|directory>] [--updated-by <scan|llm|human>]
 *   node crud.mjs delete --path <path>
 *   node crud.mjs list   [--undescribed] [--type <file|directory>] [--max-depth <n>] [--tag <tag>]
 *   node crud.mjs batch-set < descriptions.json
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { depthOf, loadMetadata, parseFlags, saveMetadata } from '../lib/shared.mjs';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '../../../');
const metadataPath = path.join(repoRoot, 'docs', 'architecture', 'repo-metadata.json');

function printUsage() {
  console.log(`
仓库元数据 CRUD

用法:
  node crud.mjs get    --path <path>
  node crud.mjs set    --path <path> [--description <text>] [--detail <text>] [--tags <a,b,c>] [--type <file|directory>] [--updated-by <scan|llm|human>]
  node crud.mjs delete --path <path>
  node crud.mjs list   [--undescribed] [--type <file|directory>] [--max-depth <n>] [--tag <tag>]
  node crud.mjs batch-set < descriptions.json

batch-set 输入格式 (JSON):
  [
    { "path": "src", "description": "源代码目录", "detail": "...", "tags": ["core"] },
    ...
  ]
`);
}

/* ------------------------------------------------------------------ */
/*  CRUD 操作                                                          */
/* ------------------------------------------------------------------ */

async function getNode(flags) {
  const p = flags.path;
  if (!p) throw new Error('get 需要 --path');

  const metadata = await loadMetadata(metadataPath);
  const node = metadata.nodes[p];

  if (!node) {
    console.error(`❌ 路径不存在: ${p}`);
    process.exitCode = 1;
    return;
  }

  console.log(JSON.stringify({ path: p, ...node }, null, 2));
}

async function setNode(flags) {
  const p = flags.path;
  if (!p) throw new Error('set 需要 --path');

  const metadata = await loadMetadata(metadataPath);
  const now = new Date().toISOString();

  const existing = metadata.nodes[p] ?? {
    type: flags.type ?? 'directory',
    description: '',
    detail: '',
    tags: [],
    updatedBy: 'human',
    updatedAt: now,
  };

  if ('description' in flags) existing.description = flags.description;
  if ('detail' in flags) existing.detail = flags.detail;
  if ('tags' in flags) existing.tags = flags.tags.split(',').map((t) => t.trim()).filter(Boolean);
  if ('type' in flags) existing.type = flags.type;
  existing.updatedBy = flags['updated-by'] ?? 'human';
  existing.updatedAt = now;

  metadata.nodes[p] = existing;
  await saveMetadata(metadataPath, metadata);

  console.log(`✅ 已更新: ${p}`);
}

async function deleteNode(flags) {
  const p = flags.path;
  if (!p) throw new Error('delete 需要 --path');

  const metadata = await loadMetadata(metadataPath);

  if (!metadata.nodes[p]) {
    console.error(`❌ 路径不存在: ${p}`);
    process.exitCode = 1;
    return;
  }

  delete metadata.nodes[p];

  // 级联删除子路径
  const prefix = `${p}/`;
  let cascaded = 0;
  for (const key of Object.keys(metadata.nodes)) {
    if (key.startsWith(prefix)) {
      delete metadata.nodes[key];
      cascaded++;
    }
  }

  await saveMetadata(metadataPath, metadata);
  console.log(`✅ 已删除: ${p}${cascaded > 0 ? ` (+ ${cascaded} 个子路径)` : ''}`);
}

async function listNodes(flags) {
  const metadata = await loadMetadata(metadataPath);
  const maxDepth = flags['max-depth'] ? parseInt(flags['max-depth'], 10) : null;
  const filterType = flags.type ?? null;
  const filterTag = flags.tag ?? null;
  const onlyUndescribed = flags.undescribed === 'true';

  const entries = Object.entries(metadata.nodes)
    .filter(([p, node]) => {
      if (maxDepth && depthOf(p) > maxDepth) return false;
      if (filterType && node.type !== filterType) return false;
      if (filterTag && !node.tags?.includes(filterTag)) return false;
      if (onlyUndescribed && node.description) return false;
      return true;
    })
    .sort(([a], [b]) => a.localeCompare(b));

  if (entries.length === 0) {
    console.log('没有匹配的条目。');
    return;
  }

  const maxPathLen = Math.min(
    Math.max(...entries.map(([p]) => p.length)),
    60,
  );

  for (const [p, node] of entries) {
    const typeIcon = node.type === 'directory' ? '📁' : '📄';
    const desc = node.description || '(未描述)';
    const padding = ' '.repeat(Math.max(1, maxPathLen - p.length + 2));
    console.log(`${typeIcon} ${p}${padding}${desc}`);
  }

  console.log(`\n共 ${entries.length} 条`);
}

async function batchSet() {
  // 从 stdin 读取 JSON 数组
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const input = Buffer.concat(chunks).toString('utf8');

  let items;
  try {
    items = JSON.parse(input);
  } catch {
    throw new Error('无法解析 stdin JSON，格式应为 [{ "path": "...", "description": "..." }, ...]');
  }

  if (!Array.isArray(items)) {
    throw new Error('输入应为 JSON 数组');
  }

  const metadata = await loadMetadata(metadataPath);
  const now = new Date().toISOString();
  let updated = 0;

  for (const item of items) {
    if (!item.path) {
      console.warn(`⚠️ 跳过: 缺少 path 字段`);
      continue;
    }

    const existing = metadata.nodes[item.path];
    if (!existing) {
      console.warn(`⚠️ 跳过: 路径不在元数据中: ${item.path}`);
      continue;
    }

    if (item.description !== undefined) existing.description = item.description;
    if (item.detail !== undefined) existing.detail = item.detail;
    if (item.tags !== undefined) existing.tags = item.tags;
    existing.updatedBy = item.updatedBy ?? 'llm';
    existing.updatedAt = now;

    metadata.nodes[item.path] = existing;
    updated++;
  }

  await saveMetadata(metadataPath, metadata);
  console.log(`✅ 批量更新完成: ${updated}/${items.length} 条`);
}

/* ------------------------------------------------------------------ */
/*  主入口                                                             */
/* ------------------------------------------------------------------ */

async function main() {
  const [command, ...rest] = process.argv.slice(2);

  if (!command) {
    printUsage();
    process.exit(1);
  }

  const flags = parseFlags(rest);

  switch (command) {
    case 'get':
      await getNode(flags);
      break;
    case 'set':
      await setNode(flags);
      break;
    case 'delete':
      await deleteNode(flags);
      break;
    case 'list':
      await listNodes(flags);
      break;
    case 'batch-set':
      await batchSet();
      break;
    default:
      printUsage();
      process.exit(1);
  }
}

main().catch((err) => {
  console.error(`❌ 执行失败: ${err.message}`);
  process.exitCode = 1;
});
