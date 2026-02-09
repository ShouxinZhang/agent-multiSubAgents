# 02 - Debug: 回放思考流映射缺失与棋盘裁切

## 用户请求

> debug

## 背景与意图

用户截图显示两类问题：

1. 左右 Agent 面板大量出现 `[system] (no captured thinking stream for this move)`，说明“落子步 -> 思考流”映射失败，影响回放可解释性。
2. 中间棋盘在三栏布局下被横向挤压，存在显示裁切，影响操作与观感。

## 修改时间

2026-02-09 10:41:30 – 2026-02-09 10:44:20 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/gomoku/gui.py` | 修改 | 回合映射容错修复（不再依赖 turn.started）；调整棋盘尺寸与中栏权重避免裁切 |
| `docs/dev_logs/2026-02-09/02-debug-replay-mapping-and-board-fit.md` | 新增 | 记录本次 debug 循环 |

## 变更说明

### 1. 回放映射容错修复

问题根因：此前映射逻辑默认依赖 `turn started` 事件开回合；当上游事件格式变化或事件缺失时，`_link_move_to_turn` 找不到未绑定回合，触发 fallback 文案。

修复策略：

- 新增 `_ensure_open_turn(player)`，保证“只要收到玩家日志就一定挂载到一个打开回合”。
- `_append_log()` 中统一调用 `_ensure_open_turn()`，不再要求先收到 `turn started`。
- 回合仍在 `turn summary:` 时收口，保持每手落子与回合绑定顺序稳定。

业务效果：即使 `turn started` 事件缺失，也能把 summary/tool/reasoning 等日志绑定到对应步，显著降低 fallback 占比。

### 2. 三栏布局下棋盘裁切修复

- `canvas_size`：`700 -> 620`
- 三栏权重：`2:3:2 -> 2:4:2`

业务效果：在常见 1600 宽窗口下中栏可完整容纳棋盘，避免右侧被裁切。

## 影响范围

- 仅 `gomoku/gui.py` UI 展示与回放映射逻辑
- 未改动对局引擎、存储格式和 MCP 协议

## 验证结果

```bash
python3 -m py_compile apps/gomoku_codex_cli/gomoku/gui.py
# 结果：通过

bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 按脚本规则跳过）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
