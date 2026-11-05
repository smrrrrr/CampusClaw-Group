# 实施与验收记录（2026-11-04）

变更：`2026-11-04-publish-quiz-as-homework`。用户评审方案后回复「开始实施」，本次据此实施，并只更新本变更的任务状态。代码已构建并更新本机 **http://localhost:8083**；未归档变更，未提交或合并 Git。

## 交付行为

- 保留「作业与改分」的手工创建草稿、发布入口；智能命题的定稿卷新发布直接创建分班作业，不再创建学科资料、旧式试卷发布记录或检索切片。
- 学生在「交作业」提交整份答案；教师可查看冻结题面、原卷总分和私有评分依据，进行 AI 初批或直接终评。最终成绩仍是整份百分制，不提供逐题作答或逐题改分。
- 公开题面和私有答案分开；配图复制后独立鉴权读取。原资料变化不影响已发布作业；历史资料、图、标签、索引和发布记录均保留。
- 同一快照重复发布复用作业；截止时间冲突或已关闭时提示复制试卷开始新一轮；多班文件或数据库失败整批回滚。
- 初批不持有跨模型调用的读取事务，结果写入复核作答时间、文本和状态；期间重交或教师终评不会被旧建议覆盖。页面切班/切换身份后忽略旧上下文回包。
- 补齐继承的逐题生成审计，使题目详情有生成、修改、通过历史，删除候选后仍可追溯生成、驳回、删除；事件不含题面、答案或模型输入原文。

## 检查与证据

| 检查 | 本次结果 | 证据 |
| --- | --- | --- |
| 完整 `backend/.venv/Scripts/python.exe scripts/check.py` | **21 组全部 PASS**，含规约、分层、密钥、前端类型和全部业务回归 | `.review/quiz-homework-full-check.log` |
| 新增命题作业集成检查 | **98/98 PASS**，临时数据库、假模型 | `apitest/check_quiz_homework.py`、`.review/quiz-homework-expanded.log` |
| 原智能命题检查及补充审计 | **117/117 PASS** | `apitest/check_question_bank.py`、`.review/question-bank-new-publication.log` |
| 原手工作业检查 | **30/30 PASS** | `apitest/check_homework.py`、`.review/homework-existing.log`，最终门禁再次执行 |
| 提示词前后抽查 | 同一组 5 条合成用例前后均 **5/5**，无编造出处 | [抽查记录](../../../docs/eval/2026-11-04-publish-quiz-as-homework.md) |
| Scenario 覆盖 | **51 个**，新增 24、修改 Requirement 内 27；逐项对应当前检查或浏览器证据 | [对应表](scenario-coverage.md) |
| 旧结构迁移 | 临时旧库连续执行两次，账号、资料、成绩及文件指纹保持 | `H/迁移重复执行` |
| 构建与运行 | 前后端 Docker 构建通过；8083 的 `/health` 和 `/api/health` 均 `ok`，数据库/MCP 正常、模型已配置 | `.review/quiz-homework-build.log`、`.review/quiz-homework-deployment.json` |
| 格式 | `git diff --check` PASS | 本次终检 |

终检补充：运行容器内 6 个后端改动文件的 SHA-256 与本机最终源码逐一相同，8083 再次返回 `ok`；独立验收的 3009/8009 服务与页面已关闭，实际发布页面保留。证据 `.review/quiz-homework-final-state.json`。OpenSpec 最终全量校验 **27/27 PASS**，实施状态为 **22/22，all_done**。

本机 `.review/` 中为未入库的脱敏日志、截图和隔离验收数据；本记录保留可入库的结论。没有把搭建阶段的检查当成本变更通过依据。

### 失败验证及修复复跑

1. 发布改造前，新检查确认旧接口没有生成 Homework，作为原始失败证据保存在 `.review/quiz-homework-red.log`。
2. 首轮全门禁在历史夹具标签比较失败：原始 JSON 用 Unicode 转义。修正为解析 JSON 后检查「试卷」标签，保留全部资料、索引、发布记录和字节断言；最终全门禁通过。
3. 故意移除学生作业配图的班级/状态判断后，`H/学生跨班读取或提交` 按预期失败；恢复正确源代码后新集成检查与全门禁均通过。证据 `.review/quiz-homework-mutation.json`（`detected=true`、`source_restored=true`）。
4. 补充的两项继承审计检查先报 **115/117**：缺少逐题生成事件。补齐同一生成事务中的逐题事件后复跑 **117/117**；旧审计不改写。证据 `.review/quiz-homework-audit-red.log` 与最终命题日志。
5. 页面复核发现旧操作回调可在切班后重新加载旧班；先将延迟回包边界明确到筛选 Scenario 与 design，再加上下文代次保护，用 6 秒延迟回包进行浏览器复核，最终全门禁再次通过。

## 当前浏览器验收

使用 `127.0.0.1:3009` 的独立 Next/FastAPI 验收环境；数据库和上传目录均在忽略的 `.review/qa/`，账号、题目、作答及评分均为合成数据。模型调用在该环境使用固定建议分，真实模型另有上述 5 条前后抽查。验收未向实际教学班级新增作业或学生提交。

| 页面场景 | 观察结果 | 本机证据 |
| --- | --- | --- |
| 定稿→两班发布 | 草稿先定稿，页面下方出现「发布为作业」；未填截止时间时禁用；填写时间及核对后返回两班作业 #1/#2，班级链接进入正确改分列表 | `browser-checks.json:publication`、`qa/published.jpg` |
| 手工入口保留 | 创建「手工作业入口验收」草稿并发布，和命题作业同时展示来源 | `browser-checks.json:manual` |
| 教师题面及评分依据 | 原卷 80 分、配图正常、公式无错误；展开私有依据后显示标准答案、解析、选择/判断字母、多空答案及根式公式 | `teacherRender`、`qa/teacher-graded.jpg` |
| 学生题面与提交 | 12 个题号连续；公式与多空位正常、原图已加载；学生不见参考答案或私有依据；整份文字提交进入待批改 | `studentRender`、`studentAnswerLines`、`qa/student-submitted.jpg` |
| AI→教师终评 | 原卷 64/80 建议为 80；教师改为 55 并保存评语，学生看到 55 及教师评语 | `aiSuggestedPercent`、`teacherOverride`、`studentFinal` |
| 错题及学情 | 55 分整份作业进入本人的错题列表；学生学情为 1 份提交、55% 作业正确率、1 条错题 | `mistakeEntryVisible`、`analytics`、`qa/student-analytics.jpg` |
| 初批期间切班 | 将初批回包延迟 6 秒后切到空作业班 103；回包到达后仍为空，不重新显示 101 班题目或旧初批提示 | `delayedGradeClassSwitch`、`qa/class-switch.jpg` |
| 切换学生 | 102 班学生只见本班命题作业，未提交；不见 101 班手工作业或教师给另一学生的评语 | `otherStudent` |
| 加载、空、失败与恢复 | 出现「加载中…」、无作业学科出现空状态；模拟 503 显示「加载失败」及重试，恢复后重试加载正常 | `loadingState`、`emptyState`、`errorRetryVisible`、`retryRecovered` |
| 发布失败保留表单 | 模拟缺失原图返回中文说明；班级、截止时间和核对状态保留，不创建部分作业 | `failedPublish`、`qa/publication-failed.jpg` |
| 继承的显示场景 | 3 空位与公式下标共存、公式选项和块公式、填空/解答根式答案、多空答案 1、1、-1、选择 A/C 与判断「正确」、代码中下划线、解答横线均检查；编辑答案时仍显示 LaTeX 原文 | `teacherRender`、`studentRender`、`candidateFormulaRender`、`editFormulaSource` |
| 实际 8083 页面 | TEA001 打开既有定稿卷「渲染复测A：多空位填空」，实际显示班级、截止时间、核对框和「发布为作业」按钮；没有点击实际发布 | `production`、`.review/publish-homework-button.jpg` |

上表 JSON 均指 `.review/qa/browser-checks.json`；相对截图前缀为 `.review/`。继承的两位数选项缩进另由 `check_question_bank.py` 的「学生卷第 10 题：选项缩进 4 格」及新增 12 题快照检查覆盖；旧资料正文、原图和下载由独立历史夹具验证。

## 数据备份、迁移与回滚

首次结构变更前备份为 `data/backups/before-publish-quiz-as-homework-20261104-095211/`。构建完成、最终切换前再次停止本套后端，备份到 **`data/backups/before-publish-quiz-as-homework-final-20261104-103524/`**，含 `campusclaw.db`、`uploads.zip`；`PRAGMA integrity_check=ok`。

最终备份有 4 个账号、9 份资料、0 份作业、0 份提交、2 份试卷、2 条旧试卷资料发布记录，上传目录 32 个文件。升级后逐行对照账号、资料、配图、切片、试卷、试卷题项、旧发布、旧作业及提交均一致；32 个文件路径与 SHA-256 全部一致。只新增兼容列、唯一索引及作业图表；不运行种子脚本，不自动搬迁历史资料。

服务使用原项目名 `campusclaw-groupv3`、原端口 8083；其他 8080–8082 部署保持运行。旧镜像 ID 已保存于 `.review/quiz-homework-old-images.json`。若需回滚：

1. 先停写并停止本套后端，另行备份升级后的数据库与上传目录，保留更新后新提交。
2. 确认恢复目标均在本项目数据及上传目录内，再恢复上述匹配的旧库和 `uploads.zip`，不要将旧库与新文件混配。
3. 用记录中的旧 backend/frontend 镜像 ID 恢复本项目镜像标签，执行 `docker compose up -d --no-build backend frontend`，重启本套 Nginx 并检查 `/health`。
4. 回滚不通过删列或运行 `dev_seed.py` 实现。本次未执行回滚，旧结构重跑在临时库验证。

## 文档同步与评审结论

README 的功能、发布按钮路径和本地工作区记录已更新；OpenSpec 索引及两项主规约已同步。产品规范补齐师生作业页面，AI 规范补齐命题初批与确定性折算，数据规范说明公开/私有快照、配图与关闭后的留存；`models.py` 同步字段和生命周期注释。新增业务服务在分层检查中登记，未放宽任何检查。

| 完成定义 | 实施者检查结论 | 依据 |
| --- | --- | --- |
| 每个 Scenario 有检查，包含越权/失败 | 满足 | 51 项对应表、98 项集成、117 项命题及浏览器证据 |
| make check 全 PASS | 满足 | 最终 21/21 PASS |
| 提示词抽查归档 | 满足 | 5 条同组前后结果与 `docs/eval/` 记录 |
| 文档及模型注释同步 | 满足 | README、索引、两份主规约、01/06/07 规范、模型注释 |
| 验证记录可追溯 | 满足 | 本记录、对应表、脱敏日志与本机截图 |

授权检查：新增教师详情、师生配图和修改的发布/初批接口均使用当前服务端身份，按实际资源复核班级/学科/作者；未登录、错误角色、跨班、跨学科、他人资源、路径和坏图均有成对检查。数据与失败信息不回显物理路径、异常原文或评分私有字段。

本表为实施者自检和工具检查，不替代另一名组员的合并评审；尚未提交、合并或归档。改动 `openspec/`、`docs/standards/` 和 `scripts/check_layering.py` 的原因与证据均列在本记录，后续合并时须按项目规则交人工评审。

范围边界：现阶段仍按整份作业提交与评分；旧的重交后成绩/错题清理策略、错题页的整份题面文本展示沿用既有实现，此次未重设计。AI 建议仅为初批，真实作答仍由教师核对终评。
