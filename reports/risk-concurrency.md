# 高风险检查：并发

| 项目 | 内容 |
| --- | --- |
| 用什么手段查 | 离线check_async_grading及真实RabbitMQ复现脚本 |
| 查什么 | 同一提交版本20次并发初批；成功后同一消息再投一次 |
| 判据 | 20次返回相同任务编号，数据库仅一条任务；重复消息增加attempts，但不再调用模型改写有效评分 |
| 结果证据 | [离线结果](async-grading/offline-result.json)的C1；[真实队列结果](async-grading/real-broker-result.json)的C1，含实际次数与评分 |

实现依靠数据库唯一键、短写事务、运行租约和条件写回，不依靠禁用按钮。模型执行中断可能导致再次调用模型，保证的是生效结果一次，不承诺模型永远只调用一次。

从仓库根目录执行 `backend/.venv/Scripts/python.exe scripts/reproduce_async_grading.py`（Windows也可用反斜线）；全部使用合成数据，不对教学库做20并发。
