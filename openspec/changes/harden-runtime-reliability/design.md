## Context

小组服务使用 FastAPI/SQLAlchemy/SQLite，数据库挂载到 Docker 容器。实际故障发生在当前 Windows 共享目录的 WAL 使用过程中，切换 DELETE 后并发检查恢复；不据此推论所有 Docker 或 Windows 文件系统均不支持 WAL。

## Decisions

1. 配置字段用 Literal 白名单 WAL/DELETE。应用默认 WAL，Compose 默认 DELETE；回滚日志保留 FULL 同步，不采用关闭日志或关闭同步的捷径。
2. 连接事件设置 SQLite PRAGMA，锁等待 15 秒。非 SQLite 不运行这些语句。
3. `/api/health` 执行 `SELECT id FROM users LIMIT 1`；捕获 SQLAlchemyError 返回 503，客户端只收到通用说明。该探针不进行写事务，也不测试 DeepSeek。
4. 实际修复先停后端写入并用 SQLite backup 备份、检查完整性，再切换模式；业务表行指纹与备份对照。持久化数据库和上传目录继续使用当前小组位置。

## Risks and Limits

读探针不能证明所有写请求正常；并发写仍受 SQLite 锁机制约束。文件系统、运行平台变化时应重新评估日志模式，不自动修改其他部署。多副本写入、高可用数据库迁移与自动故障恢复不在本期范围。
