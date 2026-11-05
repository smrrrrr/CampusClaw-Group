# 高风险检查：并发

| 项目 | 内容 |
| --- | --- |
| 用什么手段查 | 离线check_async_grading及真实RabbitMQ复现脚本 |
| 查什么 | 同一提交版本20次并发初批；成功后同一消息再投一次 |
| 判据 | 20次返回相同任务编号，数据库仅一条任务；重复消息增加attempts，但不再调用模型改写有效评分 |
| 结果证据 | [离线结果](async-grading/offline-result.json)的C1；[真实队列结果](async-grading/real-broker-result.json)的C1，含实际次数与评分 |

实现依靠数据库唯一键、短写事务、运行租约和条件写回，不依靠禁用按钮。模型执行中断可能导致再次调用模型，保证的是生效结果一次，不承诺模型永远只调用一次。

从仓库根目录执行 `backend/.venv/Scripts/python.exe scripts/reproduce_async_grading.py`（Windows也可用反斜线）；全部使用合成数据，不对教学库做20并发。

## 2026-11-05安全专项追加

本轮重新运行现有`apitest/check_async_grading.py`，57条断言通过，原始结果见 [async-offline.json](security-evidence/async-offline.json)。C1验证20并发仅一条版本任务，重复消息不重写已生效分数；Q1–Q3验证长时间等待、租约补投和显式恢复的边界。合成20请求P95=0.0145秒，假模型成本约0.200656秒，不是实际模型延迟或生产容量。

源码复核：`GradeTask`有提交版本唯一约束；`enqueue_homework`使用短写事务；`process_task/finish`用运行租约和claim令牌防旧执行写回。这些保证最终生效一次，不保证外部模型只被调用一次。

本轮队列为内存替身，未使用正在运行的教学库。Docker引擎不可达，因此真实RabbitMQ及消费者进程故障未本次复跑；上文真实代理证据仍属历史记录。
