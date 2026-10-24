## 1. 准备

- [x] 1.1 新建分支 `feat/smart-question-generation`。用 SQLite backup API 备份 `data/current/campusclaw.db`，文件名为 `before-smart-question-generation-<时间>.db`；`PRAGMA integrity_check` 返回 ok，记录表数与主要行数。
- [x] 1.2 确认 `knowledge_tags.TOPICS` 覆盖六个学科，并在 `question_service.py` 中以它作为唯一词表来源。为 `GET /knowledge-points` 写断言：数学返回数学词表，未分配学科的教师返回 403。

## 2. 数据模型

- [x] 2.1 在 `models.py` 新增 `QuestionGeneration`、`QuestionItem`、`QuestionPaper`、`QuestionPaperItem`、`QuizPublication`、`QuestionEvent`，包括唯一键与索引。在数据库副本上启动后，六张表被创建，旧表结构与行数不变。
- [x] 2.2 实现 `stem_key`（NFKC 规范化、去空白、SHA-256）与 `content_sha256`。单元断言：全角与半角、多余空格得到相同的 key。

## 3. 生成与校验

- [x] 3.1 在 `question_service.py` 实现 `QUESTION_PROMPT` 与用户消息组装（配额表、知识点、补充要求、`context_text`）。
- [x] 3.2 实现 `parse_output`：剥除单层代码围栏后解析 JSON，必须包含 `questions` 和 `gaps` 两个数组，否则整体失败。
- [x] 3.3 实现 `validate_question`，覆盖五种题型的选项、答案、空位规则，以及字段集合、枚举、知识点子集、S 引用、长度、答案标记、链接、配图。为规约每条规则至少写一条正例和一条反例断言。
- [x] 3.4 实现按数组顺序计算配额与「超出配比」，并归一化 `answer_json`。断言规约「部分题目不合格」场景得到 6 道通过、2 道未通过。
- [x] 3.5 实现 `routers/quiz.py` 的 `POST /generations`，按以下顺序处理：请求校验（400）→ 本学科资料（404）→ 无 Key（503）→ 单任务（409）→ `build_resources` → `stream_chat` 加 `progress` → 解析与校验 → 单事务落库 → `done`。失败时写入 `failed` 记录并发送 `error`，`finally` 释放任务锁。用虚构模型验证成功、部分通过、非 JSON、超时、重复提交五条路径。
- [x] 3.6 实现 `GET /generations` 与 `GET /generations/{id}`：仅作者可见，其他人返回 404。

## 4. 复核与题库

- [x] 4.1 实现 `GET /items`（候选只返回本人，`approved` 返回本学科，支持筛选与分页，每页最多 50 条）与 `GET /items/{id}`（出处快照、原稿状态「一致 / 已变化 / 已删除」、事件历史）。
- [x] 4.2 实现 `PUT /items/{id}`：仅限 `pending`，重新校验，出处只能是原快照的子集，用 `revision` 条件更新；对 `approved` 返回 409 并提示复制。
- [x] 4.3 实现 `approve`（`confirmed`、重新校验、查重 409、记录复核人和时间以及 `modified_in_review`）与 `reject`（附原因）。驳回后再通过返回 409。确认路由中不存在批量通过接口。
- [x] 4.4 实现 `copy`（生成新的 `pending` 题并记录 `derived_from_id`）、`archive` / `restore`（仅原作者）和 `DELETE`（仅 `pending` / `rejected`）。

## 5. 组卷与发布

- [x] 5.1 实现 `allocate`（最大余数法），以及按 `(used_count, id)` 排序、跨分组去重的组卷逻辑。断言规约「按 3:5:2 组卷」场景得到 13 题、总分 80，「题库不足」场景返回 422 并列出全部缺口且不建卷。
- [x] 5.2 实现 `POST /papers`、`GET /papers`、`GET /papers/{id}` 和 `PUT /papers/{id}`。修改草稿时，每道题必须是本学科 `approved` 且未下架，不得重复，题数不超过 50，分值在 0.5–100 之间、步长 0.5，并携带 `revision`。下架题返回 400。
- [x] 5.3 实现 `finalize`、`copy` 和 `DELETE`（仅草稿）。定稿后修改返回 409。
- [x] 5.4 实现 `render_student_paper`、`GET /preview` 和 `GET /answer-key`。断言学生卷不含答案、解析、S 编号或题目编号，并通过 `validate_student_text` 与 `validate_links`。
- [x] 5.5 实现 `POST /papers/{id}/publish`，具体要求如下：
  - 草稿返回 409，`reviewed` 缺失返回 400，任一班级越权时整批返回 403；
  - 原图指纹不一致时返回 409；
  - 每班独立创建 `Material` 和 `MaterialAsset`，`is_indexed=False`，标签依次为学科、知识点、「试卷」「学生版」；
  - 写入 `quiz_publications`，重复发布时复用；
  - 失败时清理已写文件。

## 6. 隔离与审计

- [x] 6.1 实现 `visible_item`、`owned_paper` 和 `owned_generation`：跨学科与非作者访问返回 404，学生返回 403，列表先按范围过滤。修改数据库中教师的学科或任教班级后，复测立即生效。
- [x] 6.2 在规约列出的每个动作中写入 `question_events`，明细不含提示词与 Key。实现 `GET /events`。验证题目删除后事件仍可查。

## 7. 前端

- [x] 7.1 新建 `/teacher/quiz` 页面与四个标签页，侧栏「智能命题」指向新路由并高亮，`view=lesson-quiz` 重定向；教研问答和课例分析仍为占位。
- [x] 7.2 生成命题页：
  - 题型合计与难度合计实时比对；
  - 显示 DeepSeek 发送提示与进度；
  - 结果摘要展示通过题、未通过原因与「待补充」缺口；
  - 中断（无 `done` 帧）时提示，并保留表单。
- [x] 7.3 待复核和学科题库页：
  - 题目卡片支持 Markdown / KaTeX，并显示出处摘录与原稿状态；
  - 支持编辑、确认后通过、驳回，没有「全部通过」；
  - 题库提供筛选、分页、历史、复制、下架 / 恢复。
- [x] 7.4 组卷与发布页：
  - 填写蓝图，展示 422 缺口表；
  - 编辑草稿（替换、删除、排序、改分值）后定稿；
  - 预览学生卷，勾选核对后选择任教班级发布；
  - 下载答案卷。
- [x] 7.5 `tsc --noEmit` 与 `next build` 通过。

## 8. 文档与测试

- [x] 8.1 为所有 `/api/teacher/quiz/*` 接口补充 OpenAPI 摘要、模型与错误码。开启 `ENABLE_DOCS` 后，Swagger 中能看到这些接口。
- [x] 8.2 编写 `apitest/check_question_bank.py`，使用临时数据库和虚构 `stream_chat`，逐条覆盖规约各 Scenario、越权 404 / 403、组卷示例、学生卷去答案。不配置 Key 也能全部通过，并输出通过数。
- [x] 8.3 回归运行 `check_lesson_prep`、`check_research_materials`、`check_mcp_tools`、`check_lessons_2_5`、`check_sqlite_storage`，全部通过。
- [x] 8.4 更新相关规约的 Implementation Status，以及 README 中的模块说明。

## 9. 验收

- [x] 9.1 Docker 端到端：`docker compose up -d --build` 后，经 8081 入口登录 TEA001，完成以下链路：生成（需有效 Key；无 Key 时验证 503 提示）→ 复核通过 → 组卷 → 定稿 → 发布到 101 班 → 学生 20260001 在资料页看到不含答案的试卷，且助手检索不命中试卷。
- [x] 9.2 用 TEA002 或其他学科教师账号验证：读取 TEA001 的候选题和试卷返回 404，跨学科题目返回 404，学生调用命题接口返回 403。
- [ ] 9.3 编写 `validation.md`，按「实际跑过」口径记录命令、结果与未覆盖项；由验收角色交叉复核并签字。
