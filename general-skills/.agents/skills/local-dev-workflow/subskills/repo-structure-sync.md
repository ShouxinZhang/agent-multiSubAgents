# subskill: repo-structure-sync

## 触发条件

- 新增/删除/移动文件或目录。
- 新增依赖或 npm scripts。

## 执行动作

```bash
node scripts/repo-metadata/scripts/scan.mjs --update
node scripts/repo-metadata/scripts/generate-structure-md.mjs
```

## 约束

- 自动生成目录树区块禁止手工改写。
