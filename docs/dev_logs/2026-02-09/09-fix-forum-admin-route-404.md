# 09 - 修复思维调试页 404 与重启脚本误杀连接进程

## 用户原始请求

> ??? 思维调试为什么会失败呢？（`/web/admin` 返回 `{"detail":"Not Found"}`）

## 修改时间

- 开始：2026-02-09 12:48:00 +0800
- 结束：2026-02-09 12:51:54 +0800

## 文件清单（路径 / 操作 / 说明）

| 路径 | 操作 | 说明 |
|---|---|---|
| `restart_forum.sh` | 修改 | 端口清理从“杀所有连接进程”改为“仅杀监听进程”，避免误杀浏览器 |
| `docs/dev_logs/2026-02-09/09-fix-forum-admin-route-404.md` | 新增 | 记录本轮问题定位与修复 |

## 变更说明（问题根因 / 业务影响 / 修复）

1. 根因确认：
   - 运行中的论坛进程启动时间早于路由修复代码，仍在提供旧路由行为，导致 `/web/admin` 被静态挂载路径吞掉后返回 404。
2. 可用性验证：
   - 重启后确认 `200`：`/admin`、`/web/admin`、`/web/admin.html`。
   - 管理员登录后，`/api/admin/agents/thoughts/stream` 可拉到 `agent_log` 等真实思维事件。
3. 安全修复：
   - `restart_forum.sh` 原实现 `lsof -ti tcp:$PORT` 会包含客户端连接进程，存在误杀风险。
   - 已改为 `lsof -nP -iTCP:$PORT -sTCP:LISTEN -t`，仅杀监听进程。

## 验证结果

```bash
curl -i http://127.0.0.1:8099/admin
# 结果：200

curl -i http://127.0.0.1:8099/web/admin
# 结果：200

curl -i http://127.0.0.1:8099/web/admin.html
# 结果：200

curl -X POST http://127.0.0.1:8099/api/auth/login -d '{"username":"admin","password":"1234"}'
# 结果：登录成功

curl http://127.0.0.1:8099/api/admin/agents/thoughts/stream?admin_token=<token>
# 结果：返回 skills_synced/agents_started/agent_log(thinking/chat/tool/system)

bash -n restart_forum.sh
# 结果：通过

bash scripts/check_errors.sh
# 结果：通过
```

## 风险与后续建议

1. 本模块仍是本机演示级；管理员可见明文 Agent 密码，不可用于公网环境。
2. 若再次出现“页面404但代码已修复”，优先检查是否旧进程未重启（端口监听进程启动时间）。
