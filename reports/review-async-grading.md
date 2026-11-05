# 异步初批实施者自检

| 用什么手段查 | 查什么 | 怎么判 | 证据 |
| --- | --- | --- | --- |
| 原业务回归 | 冻结评分依据、原卷折算、教师终评、重交、错题及学情 | 消费后保留原业务断言，不通过修改评分标准变绿 | 完整门禁、check_homework与check_quiz_homework |
| 故障注入及唯一约束检查 | 批量部分写入、20并发、重复消息、旧租约 | 回滚无半份任务；唯一任务；已完成结果不被覆盖 | risk-concurrency、risk-transaction |
| 故意改坏 | 临时移除写回时必须pending的保护 | C2教师终评场景必须红，恢复后源码指纹相同并重跑绿 | async-grading/mutation-red.json、offline-result.json |
| 实际代理进程实验 | stop/start、SIGKILL、代理不可达、死信 | 自动恢复，无需重交；3次失败进入dead，人工重试可恢复 | real-broker-result.json |
| 实际页面 | 排队、失败、重新排队、查询失败、切班、刷新、编辑保护 | 任务状态可见，旧班任务不回填，编辑88与评语不被AI建议70覆盖 | ui-*.txt、ui-completed.png |
| 新依赖核对 | pika 1.3.2许可与PyPI公开漏洞记录 | BSD-3-Clause；查询时未列漏洞 | dependency-audit.json，仅新增依赖范围 |

首轮真实代理失败源于就绪检查用root启动诊断工具，抢先生成root拥有的内部cookie；改为rabbitmq用户探测，重新建空临时卷后通过。最初的失败结果保存在first-broker-start-failure.json，未删除失败证据。随后还修正了隔离初始化脚本的模块路径。没有放宽通过判据。

新增任务表只增不改旧列，迁移前本机备份记录在.review/async-before.json；旧库两次迁移与历史评分保留由离线F1覆盖。正式外部评审仍需指定另一名组员；本文件不代签人工，不宣称已合并/发布或完成第11课全部提交事项。
