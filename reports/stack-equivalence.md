# 技术栈等价与差距记录（任务 6.2）

- 日期：2026-11-14
- 依据：课程口径第 5 条——**不用迁移**，记录等价与差距即可
- 结论：保持 SQLite + FastAPI + 库内向量，不引入 MySQL/Qdrant/Golang，不新增空服务

## 一、逐项对照

| 课程示例 | 本项目实现 | 等价点 | 差距与影响 | 处置 |
| --- | --- | --- | --- | --- |
| MySQL | SQLite（文件库，WAL/事务） | 关系模型、事务、外键约束、索引、迁移 | 单写者：并发写串行；无网络协议与独立用户权限；备份靠文件快照 | 演示规模可接受；并发 20 档已出现饱和（`reports/bench.md`），不宣称生产容量 |
| Qdrant | 库内向量（`material_chunks.embedding` BLOB + 余弦暴力检索） | 按班级/学科过滤、Top-K、相关度下限 | 无 ANN 索引，检索复杂度随分块数线性增长；无分布式与副本 | 当前 500 分块单班级毫秒级；已做热点优化，瓶颈档 P95 −23.8% |
| Golang | Python 3.12 + FastAPI/uvicorn | HTTP 接口、异步任务（RabbitMQ 消费者）、健康检查 | 解释执行，单进程 GIL；无静态编译产物 | 以多服务拆分（nginx/backend/frontend/mcp/rabbitmq/worker/dispatcher）弥补单进程限制 |

## 二、七服务与数据持久化

- `nginx` 单一入口；`backend`、`frontend`、`mcp-tools`、`rabbitmq`、`grading-dispatcher`、`grading-worker` 各自独立容器。
- 健康依赖：`depends_on` 使用 `service_healthy`；`/api/health` 另报 `database`、`mcp_tools`、`model` 三态。
- 数据独立持久化：`./data` 挂载为 SQLite 卷，`./backend/uploads` 挂载材料文件，`./logs` 供采集器只读。
- DB 未就绪时不切流量：健康检查 503 + 反代只指向 `backend:8000`；新实例接入需显式改反代。

## 三、未迁移的理由与边界

1. 课程已明确不强制迁移，本项目不新增 MySQL/Qdrant/Golang 服务，避免空服务凑数。
2. 差距集中在**并发写**与**检索规模**：单机演示足够，生产需重新评估。
3. 若后续课程改口径要求迁移，需单独立项，不在第10课内偷改。
4. 本记录不改变任何架构事实，仅作为等价说明与风险边界。
