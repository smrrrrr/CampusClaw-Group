# 高风险检查：并发

## 当前复跑（2026-11-18）

| 项目 | 本次记录 |
| --- | --- |
| 手段 | 脚本 `backend/.venv/Scripts/python.exe apitest/check_async_grading.py` 的 C1。另用 `backend/.venv/Scripts/python.exe scripts/reproduce_async_grading.py` 复跑隔离的真实 RabbitMQ。 |
| 对象 | 20 个并发请求对同一份提交的同一版本发起初批，成功后重新投递同一消息。 |
| 判据 | 请求返回相同任务编号且只创建一条任务。重复投递不得改写已生效评分。 |
| 结果 | [离线检查](security-evidence/20261118-high-risk-async.json) 57/57，[真实队列](async-grading/20261118-high-risk-real-broker-result.json) 14/14，均退出 0。真实队列的 20 个请求共用任务编号 21；重投后处理次数由 1 变 2，评分仍为 70。 |

源码使用提交编号和输入指纹唯一键、SQLite 短写事务以及租约校验。两个测试均使用合成数据和假模型。A1 的耗时来自顺序重复请求，C1 验幂等；两者都不能用于估算生产并发容量。

## 历史记录

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

---

## 第10课复跑（2026-11-14）

在真实 RabbitMQ + 独立 Compose 项目 + 临时库上重跑 `scripts/reproduce_async_grading.py`，14 项全 PASS，退出码 0：

- `C1 同一提交20并发只创建一个任务`
- `C1 重复投递不重复生效`
- `B4 杀进程后任务仍在`、`B4 租约到期后自动重投恢复`
- `B2 代理停止仍持久接收`、`B2 代理恢复后自动补投`

证据：`reports/lesson-10/20261114T072100Z-apply/async/reproduce2.txt`、`reports/async-grading/lesson10-apply2real-broker-result.json`。

结论不变：保证最终生效一次，不保证外部模型只被调用一次；未做生产并发容量结论。
