# 03 - 持久化回合事件，修复重启后思考流丢失

## 用户请求

> nothing change?
>
> react + ShadUI + tailwind + vite 做前端怎么样？我觉得这样可能debug也方便一些，因为是动态加载的
>
> OK

## 背景与意图

截图中的“界面没变化”核心是数据问题：

- `state.json` 会持久化棋步
- 思考流日志此前仅在内存中，重启后无法回放历史日志

导致现象：棋盘与落子记录存在，但左右日志和步骤思考流退化为 fallback 文案。

本轮目标是先补齐数据底座：把每回合日志持久化到 runtime 文件，并在 GUI 侧从持久化事件重建回放模型。

## 修改时间

2026-02-09 10:52:00 – 2026-02-09 10:58:00 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/gomoku/turn_event_store.py` | 新增 | 新增 JSONL 回合事件存储，支持 clear/append/snapshot |
| `apps/gomoku_codex_cli/gomoku/gui.py` | 修改 | BattleCoordinator 增加事件缓冲与回合落盘；state 事件回传持久化 events；GUI 依据 events 重建日志-回合-步数映射 |
| `docs/architecture/repo-metadata.json` | 同步更新 | 结构同步脚本自动更新 |
| `docs/architecture/repository-structure.md` | 同步更新 | 结构同步脚本自动更新 |
| `docs/dev_logs/2026-02-09/03-persist-turn-events-for-replay.md` | 新增 | 记录本次开发循环 |

## 变更说明

### 1. 新增回合事件存储

新增 `TurnEventStore`：

- 文件：`runtime/turn_events.jsonl`
- 每条事件字段：`turn_id/player/seq/order/kind/text/ts`
- 能力：
  - `clear()` 清空当前对局事件
  - `append_turn_events()` 按回合追加
  - `snapshot()` 读取全部事件快照

### 2. 协调器写入持久化事件

在 `BattleCoordinator` 中：

- 日志先入 `pending_turn_events` 缓冲
- `on_turn_finished()` 计算本回合 `seq` 后批量落盘
- `start()` 与 `reset_board()` 时清空事件文件，避免跨局串线
- `emit_state()` 增加 `events` 字段，供 GUI 重建回放模型

### 3. GUI 从持久化事件重建回放模型

新增 `_rebuild_log_model(events)`：

- 从持久化事件重建 `player_logs/turns_by_player/move_to_turn`
- 使重启后依然能按步查看真实 `reasoning/tool/assistant/system`
- 对缺失映射的棋步仍保留 fallback 兜底

## 影响范围

- 仅 `gomoku` GUI/协调器层
- 未修改引擎规则、落子协议、MCP 工具定义

## 风险控制

- 对无效 JSONL 行做容错跳过，避免单行坏数据拖垮 UI
- 停止对局时会冲刷 pending 事件，减少中途日志丢失
- 新局会清空事件文件，保证回放与当前棋局一致

## 验证结果

```bash
python3 -m py_compile apps/gomoku_codex_cli/gomoku/gui.py apps/gomoku_codex_cli/gomoku/turn_event_store.py
# 结果：通过

bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 按脚本规则跳过）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
