# 04 - 增强 check_errors.sh 支持 Python 质量检查

## 用户请求

> 增强 check_errors.sh, 使得它能够检查 python 错误

## 背景与意图

原 `check_errors.sh` 仅支持 Node.js/TypeScript 项目的质量门禁（依赖检查、typecheck、lint、build）。项目中包含 Python 应用（`apps/gomoku_codex_cli`）及 Python 工具（`scripts/tools/check_errors/`），需要将 Python 检查纳入统一门禁流程。

## 修改时间

2026-02-08 11:30:00 – 11:33:31

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `scripts/check_errors.sh` | 修改 | 新增 Python 质量检查（语法检查、未使用导入、`__all__` 校验、测试）；新增 `--python` 参数；修复无 `package.json` 时 JS/TS 检查报错；优化多应用仓库测试发现 |
| `scripts/tools/check_errors/validate_dunder_all.py` | 修改 | 新增 AST 预检查，跳过无 `__all__` 声明的 `__init__.py`，避免不必要的 import 失败 |

## 变更说明

### check_errors.sh 新增能力

1. **Python 语法检查** (`py_compile`)：遍历所有 `.py` 文件，检测语法错误
2. **未使用导入检查**：调用 `scripts/tools/check_errors/unused_imports.py`
3. **`__all__` 导出校验**：调用 `scripts/tools/check_errors/validate_dunder_all.py`，按应用根目录（含 `requirements.txt`/`setup.py`/`pyproject.toml`）分别运行，正确设置 `PYTHONPATH`
4. **Python 测试自动发现**：查找 `test_*.py`/`*_test.py`，定位应用根目录，自动选择 pytest 或 unittest，支持无 `__init__.py` 的 tests 目录
5. **`--python` 参数**：仅运行 Python 检查
6. **修复**：`check_dependencies` / `detect_*_cmd` 函数在无 `package.json` 时优雅跳过

### 支持的环境变量

- `QUALITY_PYTHON_TEST_CMD` - 自定义 Python 测试命令
- `QUALITY_PYTHON_EXCLUDE_DIRS` - 逗号分隔的排除目录名

### validate_dunder_all.py 修复

- 新增 `_file_has_dunder_all()` AST 预检查函数
- 对无 `__all__` 声明的 `__init__.py` 直接返回空列表，避免触发 `importlib.import_module()` 导致的模块路径不可达错误

### 影响范围

- `bash scripts/check_errors.sh` 全模式自动包含 Python 检查
- `bash scripts/check_errors.sh --python` 仅 Python 检查
- 原有 `--lint`/`--tsc`/`--build` 行为不变
- 无 Python 文件的仓库自动跳过

### 风险控制

- 所有新增检查在无 Python 解释器/文件时优雅降级为跳过
- 不修改任何业务代码

## 验证结果

```
bash scripts/check_errors.sh --python
✔ Python 语法检查 通过
✔ Python 未使用导入检查 通过
✔ Python __all__ 校验 通过
✔ Python 测试 通过
通过: 4  失败: 0  跳过: 0

bash scripts/check_errors.sh
通过: 4  失败: 0  跳过: 4
```

## Git 锚点

- 分支: main
