# 项目规则

本文件每次会话都会被读到。`CLAUDE.md` 通过 `@AGENTS.md` 引入本文件，`.trae/rules/project_rules.md` 指向本文件；只改这里，不要在别处另写一份。

规范总索引、检查方式及工具入口见 [docs/standards/README.md](docs/standards/README.md)；第 7 课当前核查与待验项见 [docs/lesson-07/README.md](docs/lesson-07/README.md)。常驻约束维护在本文件及其索引的规范，按场景执行的步骤维护在既有技能，不复制成多套规则。

新增或修改条款必须写明：适用范围、具体约束、检查步骤、通过/失败信号和证据位置。区分“要求”“当前实现”“本次验证”；没有运行记录不得写 PASS。纯文档整理可在 OpenSpec 明确 `skip_specs: true`，不得为了文件数量编造业务能力；任何功能行为变化仍先写业务规约。

## 规约优先

1. **无规约不写代码**：任何行为变更，先在 `openspec/changes/YYYY-MM-DD-<短横小写英文名>/` 中写好并评审 proposal / design / specs / tasks，再实现。
2. 要改行为，先改规约 Markdown，再按规约改代码；不得只在对话里口头追加需求。
3. 实现以 `openspec/specs/**/spec.md` 与变更中的 Scenario 为验收标准；“模型说完成了”不等于完成。
4. 未经明确指示，不执行 `/opsx-apply`、`/opsx-archive`，不修改 tasks.md 的勾选状态。

## 安全三条硬约束（全文见 docs/standards/03-安全开发规范.md）

1. **默认拒绝，逐资源判定归属**：业务接口默认要求登录；按 ID 取资源先取行再校验班级、学科、本人归属。跨班访问返回 403 并写审计（书面例外，见 03 规范）。
2. **身份只取自服务端会话**：`class_id`、`teaching_classes`、`subject`、`role` 只从令牌与数据库取，不采信 query、body、请求头中的同名字段；前端隐藏按钮不是授权。
3. **密钥只在本机 `.env`**：不进代码、提示词、日志、响应、前端产物、镜像与提交历史；口令只存哈希。泄露即轮换，不是删文件。

## 改代码前先读对应规范

| 改动范围 | 必读 |
| --- | --- |
| `frontend/app/**`、`frontend/components/**`、界面文案 | `docs/standards/01-产品设计规范.md` |
| `backend/**/*.py`、任何接口 | `docs/standards/02-后端开发规范.md` |
| 登录、权限、上传、出站请求、依赖 | `docs/standards/03-安全开发规范.md` |
| `apitest/**`，以及实现任何 tasks.md 任务之后 | `docs/standards/04-测试规范.md` |
| Dockerfile、`docker-compose.yml`、`deploy/`、`.env.example`、发版 | `docs/standards/05-部署运维规范.md` |
| 提示词、`llm_service.py`、`lesson_service.py`、`question_service.py`、`mcp_orchestrator.py`、检索 | `docs/standards/06-AI应用规范.md` |
| `models.py`、`database.py`、表结构、`uploads/`、数据包 | `docs/standards/07-数据规范.md` |
| 提交、评审、归档 | `docs/standards/08-评审与完成定义规范.md` |

最常用的几条（细节以规范全文为准）：

- 后端分层只能自上而下：`routers/` → `*_service.py` → `models.py` / `database.py`；外部能力（模型、向量、MCP）只在 `llm_service`、`embedding_service`、`mcp_client`。新模块先在 `scripts/check_layering.py` 登记层级。
- 失败一律 `HTTPException(status_code, detail="中文说明")`，detail 不含 SQL、路径、异常原文。
- 日志用 `logging.getLogger(__name__)`，自动为单行 JSON 带 `request_id`；不记令牌、口令、提问原文、资料正文。
- 配置只从 `config.Settings` 读；密钥不给默认值。
- 测试写在 `apitest/check_<能力>.py`，临时库 + 假模型，按正常 / 失败 / 边界三类，检查名写清对应的 Scenario。

## 完成定义与门禁（全文见 docs/standards/08-评审与完成定义规范.md）

一条变更同时满足才算完成：① 每个 Scenario 都有对应检查（含越权与失败路径）；② `make check` 全部 PASS；③ 改提示词已附评测或抽查记录；④ README、主规约、规范、模型注释已同步；⑤ 验证记录已归档。

- 合并前必须跑 `make check`（Windows：`backend\.venv\Scripts\python.exe scripts\check.py`）。不得为了变绿放宽检查、删断言或跳过子项。
- 不符合规范又确需保留的写法，写进对应规范的“例外（书面）”，注明理由与失效条件；口头豁免无效。
- 提交信息末尾写 `Change:` / `Verify:` / `Evidence:` 三行，值必须查得到。

## 技能（`.claude/skills/`，按场景调用）

| 技能 | 什么时候用 |
| --- | --- |
| `add-endpoint` | 按规范新增或修改一个后端接口 |
| `add-tests` | 实现一组任务之后，按测试规范补齐三类检查 |
| `data-change` | 改表结构或删除数据 |
| `prompt-change` | 修改任何提示词或模型参数 |
| `release` | 发一次版本、打标签 |
| `review-change` | 合并前按评审检查表审一次变更 |
| `fresh-start` | 在新机器上从零克隆、启动并验证 `/health` |

## 数据安全

已有数据的库不运行 `backend/dev_seed.py`（会重置学生账号）；改表结构前先备份数据库；`.env`、数据库、`backend/uploads/`、组内数据包不进 Git。

## 第10课：七类代码核查责任

本节只定义责任分工，不复制规范正文；具体要求仍以本文件与 `docs/standards/` 为准。AI 自审指实现者在提交前逐条对照；脚本指门禁/检查；人工确认指非实施者按证据复核。缺任一层不得宣称该类已核查。

适用范围：AI 辅助新增或修改的代码及其评审。以下为既有责任的可执行说明，命令从仓库根运行；`python` 指已安装锁定依赖的后端解释器，准备步骤见 `reports/reproduce-checks.md`。不改变现有门禁判定。

| 类别 | 核查问题 / AI 自审 | 脚本与检查步骤 | 通过/失败信号及证据 | 人工确认 |
| --- | --- | --- | --- | --- |
| 接口入口 | 身份来自会话吗？参数、角色、状态码是否符合对应 Scenario？ | `python apitest/check_async_grading.py` 的 A/E 类；`python apitest/probe_security_precheck.py --output .review/security-probe.json` | 合法请求有预期副作用；未登录 401、任务越权 403、跨班资料 404；非法请求不得写入。见 `reports/risk-authz.md`。 | 实际页面可完成操作、接口语义一致。 |
| 业务逻辑 | 是否幂等？旧 AI 结果是否覆盖重交或教师终评？ | AI 对照 `openspec/specs/async-homework-grading/spec.md`；脚本 `apitest/check_async_grading.py` C1/C2 与 `apitest/check_quiz_homework.py` | 20 并发仅一条版本任务，重复消息不重复生效；终评/重交保护断言通过。红绿证据见 `reports/gate-red-green.md`。 | 终评优先与需求意图是否一致，确认后固化规则/用例。 |
| 数据库 | 写事务是否短？中途失败是否整体回滚？迁移能重跑吗？ | `python apitest/check_async_grading.py` B3/F1；`python apitest/check_sqlite_storage.py`；迁移与 EXPLAIN 记录 | 故障回滚无半份任务；两次迁移保留旧数据；查询计划与数据指纹可核对。见 `reports/risk-transaction.md`、`reports/bench.md`。 | 备份范围、回退边界。 |
| 公共函数 | 是否重复实现、反向依赖？空值、边界与单位是否明确？ | `python scripts/check_layering.py`；`python apitest/check_formula_retrieval.py`；`python apitest/check_audit_field_bounds.py` | 分层退出 0，空向量/边界/长度断言通过。现有门禁未设全仓覆盖率百分比，不能声称达到某阈值。见 `reports/project-validation.md`。 | 抽象必要性与影响范围。 |
| 错误处理 | 超时、重投、SSE失败是否能恢复？是否泄漏内部异常？ | `python apitest/check_async_grading.py` B/D/Q 类；`python apitest/check_lesson10_skills.py` | 503 脱敏、失败不写半份分数、死信/恢复可判定、模型不可用不伪造成功。见 `reports/risk-transaction.md`。 | 页面提示、恢复操作是否可理解。 |
| 安全 | 是否信任客户端角色、越界检索、放行写工具或无效扫描报告？ | `make check-security`；`python apitest/check_injection.py`；`python apitest/check_os_vuln_gate.py`；CI 三镜像扫描 | 未授权不得执行/写入；依赖按安全判据；缺报告退出 2、未登记 HIGH/任一 CRITICAL 退出 1，例外期限有效且不扩大。见 `reports/review-04.md`、`reports/review-05.md`、`reports/review-06.md`。 | 风险取舍、书面例外与有效期。 |
| 性能 | 是否在请求内等待模型？P95和吞吐来自什么负载、是否把去重吞吐当创建吞吐？ | `python apitest/check_async_grading.py` A1/C1；独立同参脚本 `scripts/lesson10_api_bench.py` 与 `apitest/load/lesson10.py` | A1要求20请求P95小于200ms假执行；历史压测按负载档记录P95/错误率。全局API P95阈值尚未接入CI。见 `reports/bench.md`。 | 饱和点、性能收益与真实模型成本合理性。 |

人工确认只填写真实参与人的结论，并指出新增/确认的规则或用例。报告引用三层结果时应分别标记，不得以脚本日志替代人工参与。

第10课的观测口径、面板与告警见 `deploy/observability/` 与 `reports/observe-alert.md`；采集器只读，不写业务库。
