# 07 - 修复 Web `match_running` 状态漂移

## 用户请求

> 如图

## 背景与意图

截图显示矛盾状态：

- `runtime: next turn: W`
- `match: stopped`

这会误导用户判断“Start 无效”，并导致按钮状态错误。

## 修改时间

2026-02-09 11:24:40 – 2026-02-09 11:25:50 (+0800)

## 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `apps/gomoku_codex_cli/web_api.py` | 修改 | `match_running` 改为从 `BattleCoordinator` 实时状态推导；移除基于 status 文案的脆弱判断 |
| `docs/dev_logs/2026-02-09/07-fix-match-running-status-drift.md` | 新增 | 本次修复记录 |

## 变更说明

### 根因

`match_running` 之前由状态文案推断（如 `stopped:*`），会被启动阶段 `stopped: restart` 等过渡文案污染，导致运行中显示为 stopped。

### 修复

- 新增 `_is_match_running()`：`not stop_event.is_set() and bool(workers)`
- `snapshot()/health` 统一使用该实时判定
- `start()` 幂等判断改用 `_is_match_running()`
- 删除 `_drain_ui_queue` 里对 `_match_running` 的文案驱动切换

## 影响范围

- 仅 Web API 状态呈现层
- 不影响对局线程/棋盘规则

## 验证结果

```bash
# 冒烟（端口 8891）
POST /api/match/start
sleep 4
GET /api/state
# 结果：runtime_status="B thinking..." 且 match_running=true

python3 -m py_compile apps/gomoku_codex_cli/web_api.py
# 通过

cd apps/gomoku_web && npm run lint
# 通过

cd apps/gomoku_web && npm run build
# 通过

bash scripts/check_errors.sh
# 通过
```

## Git 锚点

- 分支：`main`
- 基线提交：`84954da423242ddd585190bca7a4c36eb1f23483`
