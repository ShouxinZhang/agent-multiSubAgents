---
name: build-check
description: 代码构建全链路质量门禁。当你完成代码修改后，必须使用此技能运行构建检查确保代码质量。适用于任何前端代码变更后的验证。
---

# 构建检查规范

每次代码修改后，必须运行全链路构建检查，确保不引入回归问题。

## 检查命令

### 完整检查（推荐）

```bash
bash scripts/check_errors.sh
```

此命令依次执行：
1. **依赖检查** — 优先检查根 workspace 依赖；缺失时仅在仓库根目录安装一次（有 lock 用 `npm ci`），避免在 `web/` 与 `scripts/repo-metadata/` 重复安装 `node_modules`
2. **TypeScript 类型检查** — `npx tsc --noEmit`
3. **ESLint 代码规范** — `npx eslint . --max-warnings 0`
4. **Vite 生产构建** — `npx vite build`

### 单项检查

```bash
bash scripts/check_errors.sh --tsc    # 仅 TypeScript
bash scripts/check_errors.sh --lint   # 仅 ESLint  
bash scripts/check_errors.sh --build  # 仅 Vite 构建
```

### 测试

```bash
cd web && npm run test
```

## 执行流程

1. 完成代码修改后，在项目根目录运行 `bash scripts/check_errors.sh`
2. 如果有测试文件变更，额外运行 `cd web && npm run test`
3. 查看汇总报告，确认所有步骤为 ✔ 通过
4. 如有失败，修复后重新运行直到全部通过
5. 将验证结果记录到开发日志中

## 错误处理

- **TypeScript 错误**：根据错误信息定位类型问题，修复代码
- **ESLint 错误**：遵循规则修复，不要随意 disable 规则
- **构建失败**：检查 import 路径、依赖版本和配置文件
- **测试失败**：检查断言和测试数据是否与代码变更一致

## 重要原则

- 绝不跳过检查直接提交代码
- 如检查脚本自身有问题（如提前退出），先修复脚本再继续
- 所有检查步骤必须通过后，才能认为本次开发任务完成
