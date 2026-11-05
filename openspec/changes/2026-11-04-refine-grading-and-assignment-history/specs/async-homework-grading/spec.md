## ADDED Requirements

### Requirement: 确认后限次投递与执行计数

已获持久队列确认、尚在排队的任务 MUST NOT 仅因时间经过重复投递；未确认的投递失败 MUST 可重试。一次running租约过期 MUST 最多确认一次恢复消息，新领取后若再次中断仍可恢复。确认前崩溃的不确定窗口允许重复，但 MUST 保留原有幂等、死信及事务保护。教师界面 MUST 显示本轮execution_count为“批改尝试”，不得把attempts消息累计数写成批改次数；历史attempts不清零。管理员故意清空代理持久数据后 MUST 能显式恢复pending/retrying投递，不修改成功任务或有效running，不因查询状态触发执行。

#### Scenario: Q1 暂停消费者不积攒副本
- **GIVEN** 一条pending任务已发送并确认，消费者暂停
- **WHEN** 跨越原30秒间隔反复运行投递器
- **THEN** 不新增该任务消息，队列仍一条；消费者恢复后一次有效评分

#### Scenario: Q2 未确认及过期运行恢复
- **GIVEN** 首次投递失败，或消费者在running时中断
- **WHEN** 代理恢复，或运行租约到期
- **THEN** 未确认任务补投；过期租约只确认一条恢复消息，反复扫描不再加副本；重新领取后再中断仍可恢复

#### Scenario: Q3 管理员明确恢复丢失消息
- **GIVEN** 管理员已停消费者且确认代理数据被清空
- **WHEN** 执行显式恢复命令
- **THEN** 只清除pending/retrying发送标记，不改成绩、累计计数、成功或有效running；投递器可重新发送

#### Scenario: Q4 界面不把消息数当批改数
- **GIVEN** 任务attempts=43、execution_count=1、max_attempts=3
- **WHEN** 教师查看进度
- **THEN** 显示批改尝试1次及上限3次，不能显示批改43次；API仍可查消息累计43
