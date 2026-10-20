## ADDED Requirements


### Requirement: 可配置且受限的 SQLite 日志模式

SQLite 连接 MUST 只接受 `SQLITE_JOURNAL_MODE=WAL` 或 `DELETE`，拒绝其他模式。应用配置默认 WAL，当前 Docker Compose 默认 DELETE，允许环境变量显式覆盖。DELETE MUST 使用 `synchronous=FULL`；WAL MUST 使用 `synchronous=NORMAL` 与 `wal_autocheckpoint=1000`。SQLite 连接 MUST 设置 15 秒锁等待，MUST NOT 为绕过故障关闭事务日志或改成 OFF 同步。非 SQLite 连接不执行 SQLite PRAGMA。

#### Scenario: Windows 共享目录运行小组服务

- **WHEN** Compose 没有显式覆盖 SQLite 日志模式
- **THEN** 使用 DELETE/FULL 打开已挂载数据库，保留现有账号、配置、资料、教案与消息

#### Scenario: 使用原生磁盘的 WAL 配置

- **WHEN** 运维显式设置 WAL
- **THEN** 使用 WAL/NORMAL 与自动检查点，保持同一业务模型和接口

#### Scenario: 无效日志模式

- **WHEN** 配置为 OFF 或其他白名单外值
- **THEN** 配置校验失败，不以关闭日志的方式继续启动

### Requirement: 数据库可读性纳入健康检查

`GET /api/health` MUST 实际连接数据库并查询 users 表，成功返回 `{"status":"ok","database":"ok"}`。SQLAlchemy 数据库异常 MUST 返回 HTTP 503 与通用“数据库暂不可用，请稍后重试”提示，MUST NOT 将异常误报为健康或在响应中泄露路径、SQL 或凭据。Compose 后端健康检查 MUST 调用该接口。该检查只验证当前读取能力，不宣称完整读写事务或模型服务可用。

#### Scenario: 数据库存储异常

- **WHEN** 健康检查的数据库读取抛出 SQLAlchemyError
- **THEN** 返回 503，容器健康探针识别失败，不再仅凭 HTTP 进程存活报告正常

#### Scenario: 数据库读取正常

- **WHEN** 能完成 users 表读取
- **THEN** 返回 200 和数据库正常状态，不调用 AI 或写入业务记录

### Requirement: 存储修复保留业务数据

切换现有数据库日志模式的运维修复 MUST 在停写并备份后执行，核对备份完整性和修复前后业务数据。MUST NOT 将删除数据库、重建种子、重置用户密码或手工删除有效 WAL 当作常规修复。数据库与上传目录 MUST 持久化挂载，容器重建不应替换为演示库。后续迁移仍须单独核对，不将一次成功修复当作所有文件系统均支持同一模式的保证。

#### Scenario: 会话接口磁盘 I/O 故障修复

- **WHEN** 当前 Windows Docker 共享目录发生数据库磁盘 I/O 错误并需要切换日志模式
- **THEN** 先备份及校验，再切换并复查事务/读取与业务行指纹，不清空真实会话或账号
