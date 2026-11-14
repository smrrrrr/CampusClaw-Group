# Proposal

## Why

第10课「测试交付与运行验证」原始清单现已由用户提供。本次在既有 change `2026-11-12-lesson10-test-delivery-and-runtime-verification` 内扩写，将总要求、四项判定、1.1—7.7、apply页六份证据及五个当场动作逐项落到项目资产、拟交付物、验收判据和证据位置；原有文档方案缺少CI、观测、压测及真实反馈，不能作为完整课程交付。

## What Changes

- 以 [verification-plan.md](verification-plan.md) 为逐项覆盖表，严格区分“已有资产”“需新增”“需确认/阻塞”“不适用”与实际执行结果。课程已明确的根 `report.md` 和六份 `reports/*.md` 均列为必交材料，正文只写结论与路径索引，原始输出放根 `reports/lesson-10/<run-id>/`。
- 盘点全部可重复命令及可核实的最近执行时间；建立所有现行规约Scenario到至少一条用例的矩阵，空场景优先补。复用现有临时SQLite/假模型检查与异步三判据脚本，将适用的接口/单元测试全量收口到 `make check`，安全反例和完整审计由 `make check-security` 单列，明确课程“高危0条”强于“例外登记后脚本退出0”。
- 规划一条GitHub Actions流水线：检出同一提交→准备隔离环境→并列执行两条门禁→两者全绿后构建镜像，保存失败证据；补主干保护、先红后绿、镜像提交编号和实际运行镜像反查。
- 复用前端多阶段构建及七服务Compose；规划后端/MCP构建与运行分离、就绪检查、换目录/换机复现。课程MySQL/Qdrant/Golang示例按SQLite内嵌持久库、库内向量与FastAPI作等价方案；不默认迁移数据库、替换检索或改写语言。Python最终镜像仍需运行源码的字面差距单列待确认。
- 规划三个技能的统一计数/失败率、接口P95/队列深度面板、至少一条可真触发并送达的告警；复用审计七列和既有日志，缺少统一事件的路径须先补规约，不能把HTTP路由次数冒充真实技能执行次数。
- 规划H5复用现有页面/API/认证的验证、至少3名真实使用者反馈、环境变量驱动的提交/查询/检索压测、至少一项索引改进和同参数复测；保留学生交作业200、教师触发初批202的现行合同，字面不一致待确认，不改为学生自动触发。
- 将现有3份评审与并发/事务/授权报告作为历史资产复用，按当次版本追加证据；落实三人建议分工、交叉验收、七类Harness核查、另一人从新目录完成最终四步，以及五个现场动作。所有任务保持未勾选。

## Capabilities

### New Capabilities

本轮不新增业务规约文件，保留原有 `skip_specs: true` 元数据；本次交付是工程方案扩写，不代表后续新增观测行为已获规约豁免。

### Modified Capabilities

本轮不修改现行主规约或delta。复用 `agent-assistant`、`async-homework-grading`、`student-workspace`、`mcp-tool-integration`、`class-data-isolation`、`runtime-reliability` 等；错题讲解另有现存变更中的 `mistake-notebook` delta及实际代码。

**规约前置：** 三技能统一完成事件/成功路径七列覆盖、就绪流量隔离若需新行为，或课程坚持学生提交202/学生查任务等合同，必须在后续获准的规划阶段于同一change取消skip_specs并补相应delta、评审后才能实现。本轮只改四份规划文档，相关实施任务标记阻塞条件，不创建新change或假业务Scenario。

## Impact

- **本轮实际写入：** 仅本change中已有 `proposal.md`、`design.md`、`tasks.md`、`verification-plan.md`。不动元数据及上一轮 `planning-validation.md`，其14任务/旧文件检查结论只代表上一轮快照，不能当本次结果。
- **后续拟影响：** `reports/`、根 `report.md`、少量说明文档、用例/门禁胶水、`.github/workflows/`、现有Dockerfile/Compose及独立观测配置、压测脚本、Harness入口；需要应用行为或索引迁移时先过规约/数据变更前置，不进行业务重构。
- **主要风险：** 高危零条与现有安全例外不等价、Python源码排除/三服务要求存在字面差距、H5异步角色合同不一致、三技能完整事件缺口，以及远端权限/通知接收人/真实使用者未落实。清单已提供，不再以“缺课程清单”推迟这些必交项。
- 本轮不执行apply/archive，不实施测试、CI、构建/部署、故障注入、压测、模型调用、推送或通知。产物供评审，不能宣称课程验收完成。详见 [design.md](design.md)、[tasks.md](tasks.md) 和 [verification-plan.md](verification-plan.md)。
