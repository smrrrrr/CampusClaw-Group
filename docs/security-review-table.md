# 逐文件审核表（2026-11-05代理自查）

本页是源码人工式阅读加自动证据的代理记录，不是另一名组员签名。范围为安全基线和作业异步关键路径，其他文件没有全面审核。

| 文件/位置 | 要保证什么、当前机制 | 已运行证据或静态依据 | 分类与失效条件/后续建议 |
| --- | --- | --- | --- |
| backend/deps.py | 服务端解析Token并核对当前数据库身份；教师/学生依赖拒绝错误角色 | SEC-01/03/04和异步E1均拒绝，无业务写入 | 可用（所测范围）；未证明所有旧Token撤销场景 |
| backend/routers/materials.py `_check_material_access` | 按资源真实班级拒绝跨班，403审计；没有返回对方字节 | 本班200、跨班403无正文且审计新增；临时移除授权后探针变红 | 待修改：课程404与现行403需先统一合同，不是确认跨班泄漏 |
| backend/routers/student.py `_retrieve_context` | 会话班级参与检索，引用还核对分块班级和文件指纹 | 两班同问只命中本班；A独有知识在B无引用 | 可用（合成检索范围）；不代表真实模型抗注入通过 |
| backend/routers/skills.py、teacher.py、mcp.py | 教师依赖及资源归属限制配置写入 | 学生合法请求体403；有关业务状态快照不变 | 可用（所列接口）；并发建同名Skill的异常映射未专项验证 |
| backend/grading_service.py `enqueue_homework` | 同一短事务创建整批任务/发件箱，输入指纹唯一键去重 | B3故障整批回滚；C1的20并发单任务 | 可用；不能推断其他业务事务也安全 |
| backend/grading_service.py `process_task/finish` | 外呼前提交租约，外呼后按claim和提交版本写分；先持久化再确认消息 | B4旧租约拒写、C2新提交/教师终评保留、D1有限重试 | 可用；至少一次投递不能保证模型永远只调用一次 |
| backend/grading_service.py `dispatch`、grading_worker.py | 代理确认后标记已投递，断点可补投 | B2、Q1–Q3内存队列故障/恢复；旧真实MQ证据单列 | 可用（离线）；本轮真实代理与进程恢复待Docker可用后重跑 |
| backend/models.py GradeTask/HomeworkSubmission | DB唯一约束约束版本任务与每人每作业提交 | C1及F1重复迁移保留数据 | 可用（现有SQLite隔离案例）；未做其他数据库兼容验证 |
| backend/models.py McpToolCall、routers/mcp.py ToolCallItem | 持久日志应能追溯谁调用哪个Skill、结果和成本 | SEC-07真实合成调用落1行，缺skill标识、duration、usage | 待修改：新增字段须先定规约和迁移；SSE技能名不能替代持久记录 |
| backend/mcp_orchestrator.py `record_call`（约158–195行） | 审计写失败应可观测 | 静态阅读：commit异常只rollback，未记错误事件，主流程继续 | 风险：日志库失败可能有调用无记录；尚未注入失败验证，不写PASS；建议另定降级告警/可靠审计策略 |
| frontend/package-lock.json、backend/uv.lock | 运行依赖不存在未处置高危漏洞 | npm与pip-audit本次原始JSON | 风险：前端critical/high已检出；后端通告待判级/影响核查 |
| scripts/security_precheck.py、apitest/probe_security_precheck.py | 观察不污染教学数据，报告红项不伪装成功，网络失败不复用旧结果 | 临时库、假外部服务、只读SQLite、源码前后指纹；实际入口退出1 | 可用（本机自查工具）；需另一人审查新工具及在本人机器复现 |

分类是本次所查路径的判断，不是该文件永久安全背书。待修改/风险项未修复，不满足“正式合并/发布完成”的结论；后续修复要保留本表与新的前后证据。
