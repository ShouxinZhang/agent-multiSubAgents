# 01 - GUI 三栏布局与顶部回放思考流

## 用户请求

> 我希望把 app 的界面布局改为草图样式（顶部控制栏 + 左中右三栏）。
>
> 不是，顶部还应该有对局回放功能啊，可以逐步查看 agents 的思考流。

## 背景与意图

现有 GUI 为“左棋盘 + 右侧日志/记忆”双区结构，不满足目标的业务可视化诉求。用户明确要求：

1. 布局改为顶部控制栏 + 左右 Agent 聊天面板 + 中部棋盘/记录区
2. 顶部提供对局回放
3. 回放时能逐步查看每手对应的 Agent 思考流（reasoning/tool/assistant/system）

## 修改时间

2026-02-09 10:31:00 – 2026-02-09 10:39:20 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/gomoku/gui.py` | 修改 | 重构 UI 为三栏布局；新增顶部回放控件；新增按落子步回放与思考流映射逻辑 |
| `docs/architecture/repo-metadata.json` | 同步更新 | 执行仓库结构同步脚本后自动刷新元数据时间戳/描述字段 |
| `docs/architecture/repository-structure.md` | 同步更新 | 执行仓库结构同步脚本后自动生成结构树与注释 |
| `docs/dev_logs/2026-02-09/01-gui-three-column-replay.md` | 新增 | 记录本次开发循环 |

## 变更说明

### 1. 布局重构（对齐草图）

- 顶部：保留 `Start/Stop/Reset Board/Clear Memory`
- 主体：左 `Agent B`、中 `Board + Turn Records + Step Thinking Stream`、右 `Agent W`
- 移除原 `Memory` 双面板占位，避免与目标布局冲突

### 2. 顶部对局回放能力

新增回放控件：

- `|<` 首步
- `<` 上一步
- `>` 下一步
- `>|` 末步
- `Auto Play / Pause`
- `speed(ms)` 回放速度

回放维度按“落子步”（第 0..N 手）实现，支持停留在历史步并查看对应状态。

### 3. 逐步思考流查看

新增日志-步数映射与回放渲染机制：

- 解析每个 Agent 的 turn 日志流，按 turn 归档
- 依据 `state.history` 的新增落子把 move `seq` 绑定到对应 turn
- 回放到第 `k` 手时：
  - 中部 `Step Thinking Stream` 显示该手对应 turn 的 reasoning/tool/assistant/system 事件
  - 左右 Agent 面板仅显示截至该手的日志
  - 中部 `Turn Records` 高亮当前回放手

### 4. 状态呈现优化

- 区分运行状态与棋盘状态：`runtime_status_var` / `board_status_var`
- 回放状态实时显示：`replay: x/y (live|replay)`

## 影响范围

- 仅 GUI 表现层（`gomoku/gui.py`）
- 未改动对局引擎、MCP 工具接口、状态存储协议

## 风险控制

- 对“日志缺失或无法匹配到 turn”的情况使用占位文案兜底：`(no captured thinking stream for this move)`
- 对局重置/新开局时重置回放状态，避免跨局污染
- 回放与实时模式分离，手动回放不会破坏实时对局线程

## 验证结果

```bash
python3 -m py_compile apps/gomoku_codex_cli/gomoku/gui.py
# 结果：通过

bash scripts/check_errors.sh
# 结果：通过（Python 全通过；Node/TS 按脚本规则跳过）

node scripts/repo-metadata/scripts/scan.mjs --update
# 结果：通过（Metadata up to date, 0 added/0 removed）

node scripts/repo-metadata/scripts/generate-structure-md.mjs
# 结果：通过（repository-structure.md 已更新）

bash scripts/check_errors.sh
# 结果：通过（结构同步后复验）
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
- 工作区状态：存在用户侧未提交改动（含 `docs/architecture/*`）
