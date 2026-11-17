# 成员贡献与 AI 使用来源

2026-11-17 按 `main@8964200` 的 Git 署名、GitHub PR 和仓库验收记录核对。每位成员都按「交付内容、实现位置、提交与证据」记录。Jackler 是 PR #3 中的 Git 署名，hexzun1 是该 PR 的 GitHub 作者。

| Git 署名 / 账号 | 可核验的贡献样本 | 提交/记录 |
| --- | --- | --- |
| Jackler / hexzun1 | 智能命题、MCP、工程基线、安全复核、CI 验收、压测与性能优化、依赖及镜像交付 | [贡献明细](#jackler--hexzun1-的贡献明细) · [PR #3](https://github.com/smrrrrr/CampusClaw-Group/pull/3) |
| Grey_Wolf_King | 作业批改、学情与错题功能，跨班隔离、审计、工具授权、CSRF、密钥与依赖检查、安全回归与交接 | [贡献明细](#grey_wolf_king-的贡献明细) |
| smrrrrr | 智能备课与讲义发布、试卷发布为作业、异步初批、历史与错题同步、安全预检、交叉复验和镜像门禁修复 | `642242e`、`6bb70e1`、`68acf9a`、`3e7af04`、`55d18d3`、PR #3 Review、PR #5–#7 |

## Jackler / hexzun1 的贡献明细

| 工作范围 | 可核实的交付 | 证据 |
| --- | --- | --- |
| 学生助手工具接入 | 集成自托管 MCP 工具服务；学生助手经编排层发现与调用工具，新增工具链路接口和回归。 | [MCP 集成 99f476e](https://github.com/smrrrrr/CampusClaw-Group/commit/99f476e) · `backend/mcp_client.py`、`backend/mcp_orchestrator.py`、`apitest/check_mcp_tools.py` |
| 智能命题与公式 | 上线智能命题、题库相关流程，修正模型输出 JSON 中的反斜杠；加强题目公式结构校验和学生卷选项渲染。 | [命题 13c1cd2](https://github.com/smrrrrr/CampusClaw-Group/commit/13c1cd2) · [公式 a6a7c56](https://github.com/smrrrrr/CampusClaw-Group/commit/a6a7c56) · `backend/question_service.py`、`backend/model_json.py` |
| 工程基线 | 交付健康检查、JSON 日志、配置校验、一键门禁和八份工程规范，并留下基线验证。 | [基线 c056cb5](https://github.com/smrrrrr/CampusClaw-Group/commit/c056cb5) · `backend/logging_setup.py`、`apitest/check_baseline.py` · [基线验证](../docs/lesson-07/verification.md) |
| 安全交叉评审与修复 | 复核安全修复，归档工具授权、审计和漏洞门禁中的发现；随后修复角色上下文和权限分类，补相关回归，后续补齐审计文本字段的转义与长度上限。 | [评审 704b631](https://github.com/smrrrrr/CampusClaw-Group/commit/704b631) · [修复 97ba0f5](https://github.com/smrrrrr/CampusClaw-Group/commit/97ba0f5) · [字段保护 ae6328b](https://github.com/smrrrrr/CampusClaw-Group/commit/ae6328b) · [复核记录](review-03.md) |
| 交付验证与 CI | 将普通检查、安全检查和镜像扫描接入 GitHub Actions，补高风险场景断言和逐条覆盖核对；归档远端实跑、故障重放、换目录启动和备份回滚练习。 | [交付工程 e02e83f](https://github.com/smrrrrr/CampusClaw-Group/commit/e02e83f) · [场景核对 6ca88c4](https://github.com/smrrrrr/CampusClaw-Group/commit/6ca88c4) · [CI](pipeline.md) · [回滚证据](release-rollback.md) |
| 压测与检索优化 | 组织三接口压测与索引对照；预计算查询向量范数，合并关键词打分。在报告所列实验中，并发 10 的检索 P95 降 23.8%，并发 3 的 P95 上升 7.6%。 | [压测 0408862](https://github.com/smrrrrr/CampusClaw-Group/commit/0408862) · [优化 4b005e1](https://github.com/smrrrrr/CampusClaw-Group/commit/4b005e1) · [实验样本与参数](bench.md) |
| 依赖与镜像 | 升级 Next.js 至 15.5.28、迁移 JWT 库，处置可修复的镜像系统包风险，记录书面例外与发布证据。 | [JWT 378835f](https://github.com/smrrrrr/CampusClaw-Group/commit/378835f) · [Next.js f6d3a2b](https://github.com/smrrrrr/CampusClaw-Group/commit/f6d3a2b) · [镜像归档 4715d69](https://github.com/smrrrrr/CampusClaw-Group/commit/4715d69) · [PR #3](https://github.com/smrrrrr/CampusClaw-Group/pull/3) |

## Grey_Wolf_King 的贡献明细

| 工作范围 | 可核实的交付 | 证据 |
| --- | --- | --- |
| 作业批改 | 新增作业批改服务和接口，接入教师、学生页面，补作业业务检查。 | [功能实现 e10c81b](https://github.com/smrrrrr/CampusClaw-Group/commit/e10c81b) · `backend/homework_service.py`、`backend/routers/homework.py`、`apitest/check_homework.py` |
| 学情与错题 | 新增学习诊断、学情统计与错题本，补学情计算和错题流程检查。 | [功能实现 e10c81b](https://github.com/smrrrrr/CampusClaw-Group/commit/e10c81b) · `backend/analytics_service.py`、`backend/mistake_service.py`、`apitest/check_analytics_units.py`、`apitest/check_mistake.py` |
| 跨班资料与 XSS | 将涉及资料和业务对象的跨班访问按约定返回 404，补文本输出转义；更新权限探针和多类业务回归以兼容按接口约定返回的 404/403。 | [隔离修复 76be9f2](https://github.com/smrrrrr/CampusClaw-Group/commit/76be9f2) · [回归 62ef2aa](https://github.com/smrrrrr/CampusClaw-Group/commit/62ef2aa) · `backend/routers/materials.py`、`apitest/probe_security_precheck.py` |
| 审计、工具授权与 CSRF | 提交七列审计字段和迁移脚本，增加工具执行授权与 Cookie 写请求的 CSRF 防御。后续评审修复见 Jackler 条目。 | [安全实现 4cfaa15](https://github.com/smrrrrr/CampusClaw-Group/commit/4cfaa15) · `scripts/migrate_audit_fields.py`、`backend/mcp_orchestrator.py`、`backend/main.py` |
| 密钥与依赖治理 | 扩充密钥扫描范围，登记依赖审计发现及例外，归档密钥反例和恢复后的门禁结果。 | [扫描与登记 3d63e9b](https://github.com/smrrrrr/CampusClaw-Group/commit/3d63e9b) · `scripts/security_precheck.py` · [先红后绿](gate-red-green.md) |
| 注入反例 | 将 SQL 注入、XSS 和 CSRF 三组反例纳入 `make check`，把安全修复变成可重复检查的用例。 | [安全回归 efbfb67](https://github.com/smrrrrr/CampusClaw-Group/commit/efbfb67) · `apitest/check_injection.py`、`apitest/cases/csrf.py` |
| 修复复盘与交接 | 整理修复前后对照、SEC-08 实验、CSRF 返工、交接说明与评审模板，归档对应的 OpenSpec 变更。 | [实验与复盘 4ad52f5](https://github.com/smrrrrr/CampusClaw-Group/commit/4ad52f5) · [交接 70f0048](https://github.com/smrrrrr/CampusClaw-Group/commit/70f0048) · [修复对照](security-fix-log.md) · [工具实验](sec08-experiment.md) |

## smrrrrr 的贡献明细

| 工作范围 | 可核实的交付 | 证据 |
| --- | --- | --- |
| 教学功能 | 智能备课与讲义发布。 | [实现 642242e](https://github.com/smrrrrr/CampusClaw-Group/commit/642242e) · `backend/lesson_service.py`、`backend/routers/lesson_plans.py` · [备课验收脚本](../apitest/check_lesson_prep.py) |
| 作业业务闭环 | 让智能命题生成的试卷能直接发布为作业，冻结评分依据；教师发起异步初批并查看任务，保留教师终评和学生重交结果。 | [实现 6bb70e1](https://github.com/smrrrrr/CampusClaw-Group/commit/6bb70e1) · `backend/quiz_homework_service.py`、`backend/grading_service.py`、`backend/grading_worker.py` · [异步验收](async-grading/README.md) |
| 师生流程维护 | 保留学生已交作业历史，教师终评及格时移除对应旧错题；修复单科教师切班误进 403；从教师端移除教研问答、课例分析占位入口。 | [作业历史 68acf9a](https://github.com/smrrrrr/CampusClaw-Group/commit/68acf9a) · [切班修复 fcc618a](https://github.com/smrrrrr/CampusClaw-Group/commit/fcc618a) · [入口整理 28707e7](https://github.com/smrrrrr/CampusClaw-Group/commit/28707e7) |
| 工程规范与安全自查 | 补充工程规范、AI 评测用例与本机验收入口；交付安全预检脚本、权限探针和修复前基线，记录并发、事务、权限三查。 | [工程规范 3e7af04](https://github.com/smrrrrr/CampusClaw-Group/commit/3e7af04) · [安全基线 55d18d3](https://github.com/smrrrrr/CampusClaw-Group/commit/55d18d3) · [安全自查](security-precheck.md) |
| Windows 复验与交叉评审 | 新克隆目录启动七个服务，核对健康检查和登录页。复核组员交付、提交评审意见，修复后的候选通过 CI 后在 GitHub 正式批准。 | [独立复验提交 85f7573](https://github.com/smrrrrr/CampusClaw-Group/commit/85f7573) · [复核意见与正式批准](peer-review.md) |
| CI 与镜像门禁 | 修复空扫描报告被放行、同 CVE 下未登记包被放行的问题；补三镜像检查，处理两份运行镜像的 `infocmp` 风险，保留红绿证据。 | [PR #5](https://github.com/smrrrrr/CampusClaw-Group/pull/5) 中的 `cc5b0fc`、`b068cb9`、`3da68c5`，随 PR #3 进入主干 · [先红后绿](gate-red-green.md) |
| 交付与报告 | 整理教师验收和交叉复核记录；补项目报告、三查证据、录屏步骤和汇报提纲。 | [交付文档 PR #6](https://github.com/smrrrrr/CampusClaw-Group/pull/6) · [讨论稿 PR #7](https://github.com/smrrrrr/CampusClaw-Group/pull/7)，核查时均待合并。 |

从仓库根按同一基线核对三位成员的主干提交。

```text
git log 8964200 --no-merges --author=Jackler --oneline
git log 8964200 --no-merges --author=Grey_Wolf_King --oneline
git log 8964200 --no-merges --author=smrrrrr --oneline
```

协作交接可沿三条线核对。Jackler 的命题模块由 smrrrrr 接到试卷发布为作业。Grey_Wolf_King 的批改、学情与错题功能随后由 smrrrrr 扩展到异步初批、历史记录与错题同步。安全工作中，smrrrrr 做预检和基线，Grey_Wolf_King 提交实现与反例，Jackler 复核并完成后续修复。最终，Jackler 提交交付 PR #3，smrrrrr 交叉复验和批准并提交镜像门禁专项修复。[交叉评审](peer-review.md) · [GitHub 快照](project-evidence/github-snapshot.json)

## AI 辅助范围与 Harness

可追溯样本包括 `backend/grading_service.py` 的异步任务实现及自检（`reports/review-async-grading.md`），以及 `scripts/trivy_os_gate.py`、`apitest/check_os_vuln_gate.py` 的 Codex 辅助修复（`reports/review-04.md` 与 PR #5）。代码经过后续人工/代理修订，不能据 Git 作者名推断每一行究竟由谁生成。

本次材料整理与脚本复核使用 Codex，直接读取 `AGENTS.md` 与相应规范。仓库另有 `CLAUDE.md`、`.trae/rules/project_rules.md`、`.cursor/rules/project_rules.mdc` 入口；存在配置不等于本次实际运行过这些 Harness。历史每次对话的模型版本没有完整运行记录，报告不编造统一模型名称。

正式交作业前，如平台要求真实姓名/学号/组号，由成员提供后映射到以上署名；当前报告用已核实的仓库署名。

## 代码与规约之外的 AI 产出

| 仓库位置 | 写了什么 |
| --- | --- |
| `AGENTS.md` | 规则入口、七类核查问题、步骤、通过与失败信号。 |
| `apitest/check_async_grading.py`、`apitest/probe_security_precheck.py`、`apitest/check_os_vuln_gate.py` | 并发去重、第二条插入失败回滚、跨班资料拒绝、镜像报告完整性等自动检查。 |
| `reports/review-04.md`、`reports/review-05.md`、`reports/review-06.md` | 整理空扫描报告、MCP 写工具授权、镜像缓解三次发现及可核验证据。交叉评审的本人操作见 `reports/peer-review.md`。 |
| `reports/risk-concurrency.md`、`reports/risk-transaction.md`、`reports/risk-authz.md` | 分项记录风险检查的手段、对象、判据与实跑结果。 |
| `scripts/lesson10_api_bench.py`、`apitest/load/lesson10.py`、`reports/bench.md` | 用同参复测对照 P95、吞吐和错误率，标注模型、数据与负载范围。 |
| `Makefile`、`scripts/check.py`、`.github/workflows/lesson10.yml` | 编排规约、静态、类型、离线回归、密钥和安全检查。 |
| `README.md`、`report.md`、`reports/demo-recording.md`、`reports/presentation-notes.md` | 整理启动、项目报告、三分钟录屏与五分钟汇报。 |
