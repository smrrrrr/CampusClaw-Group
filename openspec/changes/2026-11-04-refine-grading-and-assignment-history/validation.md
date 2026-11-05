# 验证记录

日期：2026-11-04。本变更先写proposal/design/specs/tasks、自查需求和失败路径并通过strict校验，再实施。用户已明确要求修改。未执行opsx-apply/archive、未改tasks勾选、未提交或打标签。本记录表示本机实施与验证结果，不代替人工交叉评审。

## 场景与证据

| Scenario | 实现与可重放检查 |
| --- | --- |
| Q1 暂停不积攒副本 | check_async_grading：确认后跨30分钟无副本；真实队列暂停32秒20→20 |
| Q2 未确认/过期恢复 | check_async_grading：故障补投、同租约一次恢复、新租约再次恢复；真实SIGKILL/代理重建 |
| Q3 显式恢复 | check_async_grading：仅重置pending/retrying，终态与有效running不变，重复0 |
| Q4 显示执行计数 | check_assignment_history_ui及教师实际页面：attempts43显示批改尝试1，上限3 |
| H1 提交与刷新 | check_assignment_history返回本人持久答案/时间；UI分类检查；实际页面提交记录、筛选与刷新 |
| H2 关闭历史 | check_assignment_history：关闭后100分/评语/配图可读、禁止重交；实际关闭历史页面 |
| H3 隔离与依赖故障 | check_assignment_history：401/403/400/404/409/503，草稿/他班/他人不泄露；原权限审计门禁保留 |
| H4 空态/时间 | check_assignment_history_ui：未交、已交、无截止、恰好截止及超过截止分类；页面空历史与空错题文字 |
| M1 满分不收录 | check_assignment_history：首次100无错题；实际页面合成100分错题为空 |
| M2 改分同步 | check_assignment_history：59→60/99/100→59，数量1→0→1 |
| M3 限定修复 | check_assignment_history：dry-run/apply/repeat、保留其他记录及备份；真实数据限定删除1、再执行0 |
| M4 越权/事务失败 | check_assignment_history：未登录/学生/他班/他科拒绝；DELETE故障503且分数与错题一起回滚 |

## 已执行结果

- 全量 `backend\.venv\Scripts\python.exe scripts\check.py`：26组PASS，含类型、分层、密钥、strict及所有业务检查。
- 异步57项、历史/错题33项、前端6项PASS；原作业30、命题作业98项继续通过。
- 真实RabbitMQ复现14项PASS，使用合成数据及本地假模型，未调用真实提供商。镜像与关键源码指纹经过脚本核对。
- 故意改坏仅在隔离副本进行：恢复旧30秒重投使Q1失败；禁止及格清理使M2失败。当前实现全量为绿。
- 首次门禁发现repair_resolved_mistakes错误导入begin_write；改为显式SQLite事务后重新全部通过，原失败记录保留，没有放宽断言。
- 隔离3009/8009页面实际操作完成；截图/文本证据已归档。验收环境进程结束后清理，不写真实教学账号。
- 已构建并更新campusclaw-groupv3的backend、dispatcher、worker、frontend，刷新nginx。8083健康正常、7服务运行，其他3套部署未更新。
- 真实修复前完整备份，dry-run1、apply1、repeat0；仅mistake_notes变化，其他34张表及31个文件不变，SQLite integrity=ok。成功任务消息43/执行1审计不清零。

全部证据索引：[用户验证与完整报告](../../../reports/assignment-history-2026-11-04.md)、[原始记录目录](../../../reports/async-grading/README.md)、[最终文件核对](../../../reports/async-grading/history-final-audit.json)。源文件范围以本次design和报告为准；仓库原有未提交改动不混称为本次修改。

## 同步与剩余边界

已同步三个主能力规约、根README、规约索引、产品/运维/数据规范；不新增表结构/依赖，不改提示词，无需提示词质量评测。常规门禁外的真实模型准确率/成本/外网部署、另一机器从零复现和人工交叉评审仍未验证。未满足正式课程交付的外部评审及版本标签条件，不能把本机自检写成已完成那些要求。
