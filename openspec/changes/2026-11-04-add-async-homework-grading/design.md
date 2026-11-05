## Context

初批逻辑集中在homework_service，路由同步等待；教师页直接使用批改数量。已有临时库假模型回归保留冻结依据、折算与竞态断言。现有SQLite适合本组规模，采用短写事务与单任务消费，不把模型调用包进事务。真实环境为groupv3/8083，另外三套部署不得操作。

## Goals / Non-Goals

实现新能力规约A1–F1。只改教师主动初批，不改学生提交流程、提示词、模型参数、人工改分及其他AI功能。无正式发布、提交、推送、归档或冒充人工评审；版本标签作为待授权交付步骤记录。

## Decisions

1. RabbitMQ 4.2-management + BSD许可pika 1.3.2，配置外置，broker仅内网，数据卷持久化。采用持久消息、publisher confirm及手动ack。参考[官方确认机制](https://www.rabbitmq.com/docs/confirms)、[Pika BlockingConnection](https://pika.readthedocs.io/en/1.3.2/modules/adapters/blocking.html)。本轮单节点不是高可用集群。
2. 新grade_tasks表兼作事务性发件箱：一行同时表示任务与待投递状态，不存在仅记录业务却忘记排队的两次提交。HTTP只提交数据库；独立dispatcher扫描未确认投递、到期重试及失效运行租约。确认后记last_published_at；窗口中崩溃只会重复，数据库幂等消除副作用。定时补投覆盖代理丢失后的恢复。
3. 每条任务保存submission_id、homework_id、class_id、subject、teacher_id、input_fingerprint及私有input_json（提交时间/作答/发布评分依据），唯一键为submission_id+input_fingerprint。批量创建先在SQLite取短BEGIN IMMEDIATE写锁，失败整批回滚，避免并发读后写锁升级。
4. 状态pending→running→succeeded/skipped/retrying/dead；running以随机claim_token及lease_until作条件更新。外部调用前提交领取，调用后短事务内同时条件更新任务与当前提交。重交、已终评或失效租约不写旧评分。一次任务对应一份作答，崩溃可重复调用模型，但生效结果一次（不承诺模型只调用一次）。
5. 默认3次模型执行，退避5、10秒（可配置基数）；attempts含已完成消息重复处理，execution_count为本次手动重试周期执行数。dead发布到独立持久队列，dead_published_at只有confirm后才写，失败补投。死信保留ID，原因在受权任务接口查询。手动重试重置执行周期，不清累计attempts。
6. POST原路径改202；GET homework/{id}/grade-tasks、GET grade-tasks/{id}只读；POST grade-tasks/{id}/retry只允许dead。接口仅公开状态、编号、时间、attempts和脱敏错误，不含input_json。学生无任务读取权限。
7. 前端按所选作业查询/轮询，切班清理并检查上下文版本；完成后更新提交但不覆盖教师编辑的评分。刷新通过GET恢复状态，不依赖内存任务编号。状态错误有重试按钮，死信有显式重试。
8. 普通make check用内存队列替身/假模型、临时库；额外reproduce脚本创建独立Compose项目、真实RabbitMQ及假HTTP模型，真实stop/kill/start。保留20请求P95与200ms假执行时间的区别，结果不冒充真实供应商性能。

## Risks / Trade-offs

- SQLite写并发有限：短事务+busy timeout，20并发复现；不宣称高吞吐生产能力。
- 单节点RabbitMQ卷与数据库都需备份；代理损坏时任务可由数据库补投，不代表机房级灾备。
- 运行租约必须大于模型超时并留余量；配置校验拒绝错误值。消费者被kill后等租约到期，不保证立即完成。
- 旧客户端同步返回契约变化：前端和旧检查一起迁移，不保留请求内评分旁路；原评分断言仍以消费者执行结果检查。
- 定时补投会产生少量重复消息；已完成重复仅更新attempts，不重新调用模型或改评分。

## Migration Plan

先保存本次前工作区指纹，真实库迁移前用SQLite backup API备份并integrity_check，保留匹配uploads指纹；新任务表只增不改旧字段。先在临时旧库执行两次启动验证，再在隔离Compose复现，通过完整门禁后更新groupv3。队列密码本机.env生成，不输出/入库。回滚停止新任务服务、用此前镜像恢复旧应用；保留新表不会影响旧代码，如需恢复数据库，先另备份更新后的数据并恢复匹配备份。

## Review

后续界面修正：实际极速浏览器确认原反馈位于页面顶部，字体小且长内容截断，不便在作业卡片旁验证。改为按homework_id保存反馈并在卡片内换行显示，包含新建/复用/跳过数量及编号；错误同处显示。查看提交和轮询更新时，以已返回的提交列表长度同步该卡片submitted_count，不发送额外初批请求。保持上下文版本保护，切班清空反馈。只更新前端，不启动用户为实验暂停的消费者，不写教学数据；提交人数同步失败不能把已经202受理的任务误报失败。

实施前自审：接口契约变更、已有评分边界、事务窗口、确认窗口、权限和故障场景均已列明；用户已明确要求加到作业AI批改并留证。本记录不代替另一名组员评审，合并/正式发布前仍需人工复核。
