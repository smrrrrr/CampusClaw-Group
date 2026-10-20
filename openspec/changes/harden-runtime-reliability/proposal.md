## Why

2026-10-20 学生会话接口出现 SQLite `disk I/O error`。旧健康检查只确认 HTTP 进程存活，不能反映数据库不可用；Windows Docker 挂载目录需要明确日志模式与数据保留措施。本变更将已经完成的修复写成可复用规约。

## What Changes

- SQLite 日志模式限定 WAL/DELETE，Compose 默认 DELETE/FULL；保留显式 WAL 配置和 15 秒锁等待。
- 健康检查实际读取 users 表，数据库异常返回 503，不暴露内部异常细节。
- 明确备份、切换与业务数据核对，保留账号、资料、教案和会话。

## Capabilities

### New Capabilities

- `runtime-reliability`: 数据库连接策略、读健康检查与保留数据的存储修复。

## Impact

已有实现位于 backend/config.py、database.py、main.py、docker-compose.yml 和环境变量示例。此轮仅补规约，不重新执行数据库切换、不改变容器运行配置、不调用 AI。
