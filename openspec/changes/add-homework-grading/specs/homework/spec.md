## Purpose

定义作业布置、学生提交、AI 初批、教师改分与评语的完整业务契约，以及按班级和学科的数据隔离边界，为错题本与学情诊断提供判错结果和分数数据来源。

## ADDED Requirements

### Requirement: 教师布置作业

教师 SHALL 能为本人任教班级的本科目布置作业，作业 MUST 包含标题、题目内容和截止时间。作业状态 MUST 为 `draft`（草稿）或 `published`（已发布）；草稿状态学生不可见，发布后本班学生可见且可提交。MUST NOT 允许教师为非任教班级或非本人学科布置作业。

#### Scenario: 教师发布作业到任教班级

- **WHEN** 数学教师张老师为任教的高二（2）班创建标题为"一元二次方程练习"的作业并发布
- **THEN** 作业以 `published` 状态保存，`class_id` 为高二（2）班、`subject` 为数学、`teacher_id` 为张老师；高二（2）班学生可在作业列表看到该作业

#### Scenario: 教师跨班布置被拒绝

- **WHEN** 张老师试图为高二（1）班（非任教班级）布置数学作业
- **THEN** 返回 403，作业不保存

#### Scenario: 草稿作业学生不可见

- **WHEN** 张老师创建一份作业但未发布（`status=draft`）
- **THEN** 学生端作业列表不包含该作业

### Requirement: 教师查看本班本科目作业列表

教师 SHALL 能查看本人任教班级本科目的全部作业列表，按创建时间倒序排列，每项 MUST 包含标题、截止时间、状态、提交人数与总人数。MUST NOT 返回其他班级或其他学科的作业。

#### Scenario: 教师查看本人作业列表

- **WHEN** 张老师选择任教班级高二（2）班查看数学作业
- **THEN** 返回该班数学作业列表，包含张老师本人布置的作业；不包含英语作业或其他班作业

### Requirement: 学生查看本班作业列表

学生 SHALL 能查看本人班级中已发布的作业列表，每项 MUST 包含标题、题目、截止时间和本人提交状态（未提交/已提交）。MUST NOT 展示草稿作业，MUST NOT 展示其他班级的作业。

#### Scenario: 学生查看本班作业

- **WHEN** 王芳（高二（2）班）登录后查看作业列表
- **THEN** 返回高二（2）班已发布的作业，显示每题截止时间和本人提交状态

#### Scenario: 学生看不到草稿作业

- **WHEN** 张老师在高二（2）班有一份草稿状态的数学作业
- **THEN** 王芳的作业列表不包含该草稿作业

### Requirement: 学生提交作业

学生 SHALL 能对本班已发布且未截止的作业提交答案文本。同一学生对同一作业多次提交时，MUST 覆盖上一次提交内容并更新提交时间。已截止或已关闭的作业 MUST NOT 接受新提交。MUST NOT 允许学生提交其他班级的作业。

#### Scenario: 学生提交作业答案

- **WHEN** 王芳对高二（2）班已发布的"一元二次方程练习"提交答案文本
- **THEN** 创建或更新一条 `HomeworkSubmission`，状态为 `pending`，记录 `student_id`、`homework_id`、`answer_text` 和 `submitted_at`

#### Scenario: 学生重复提交覆盖旧答案

- **WHEN** 王芳在截止前再次提交同一作业
- **THEN** 原有提交记录的 `answer_text` 被覆盖，`submitted_at` 更新，不新增记录

#### Scenario: 截止后提交被拒绝

- **WHEN** 作业已过 `due_at`，学生尝试提交
- **THEN** 返回 400，提示"作业已截止"，不保存提交

#### Scenario: 跨班提交被拒绝

- **WHEN** 李明（高二（1）班）尝试提交高二（2）班的作业
- **THEN** 返回 403，不保存提交

### Requirement: AI 初批

教师 SHALL 能触发对某次作业全部已提交答案的 AI 初批。AI 初批 MUST 返回分数（0–100 整数）、评语文本和是否判错标记。AI 结果 MUST 写入 `ai_score`、`ai_feedback`、`ai_graded_at`，提交状态变为 `ai_graded`。AI 分数 MUST NOT 直接作为最终成绩，最终成绩以教师改分为准。AI 批改失败时 MUST 保留原状态并记录错误，不写入部分分数。

#### Scenario: 教师触发 AI 初批

- **WHEN** 张老师对"一元二次方程练习"点击"AI 批改"
- **THEN** 系统对所有 `pending` 状态的提交调用 AI，返回分数和评语，写入对应提交记录，状态变为 `ai_graded`

#### Scenario: AI 初批不覆盖教师已改分

- **WHEN** 某提交已被教师改分（`status=teacher_graded`）
- **THEN** AI 初批跳过该提交，不覆盖教师分数与评语

#### Scenario: AI 服务失败不写入部分结果

- **WHEN** AI 调用失败或返回无效 JSON
- **THEN** 该提交保持 `pending` 状态，不写入 `ai_score` 或 `ai_feedback`

### Requirement: 教师改分与评语

教师 SHALL 能对已提交（含 `pending` 和 `ai_graded`）的作业进行人工评分和评语。教师评分 MUST 为 0–100 整数，评语 MUST 为文本。教师改分后提交状态变为 `teacher_graded`，记录 `teacher_score`、`teacher_feedback`、`teacher_graded_at`。MUST NOT 允许教师批改非任教班级或非本人学科的作业。教师改分 MUST 覆盖 AI 分数作为学生可见的最终成绩。

#### Scenario: 教师给学生改分

- **WHEN** 张老师对王芳的提交输入分数 85 和评语"过程完整，计算正确"
- **THEN** 提交记录 `teacher_score=85`、`teacher_feedback` 更新、`status=teacher_graded`、`teacher_graded_at` 记录时间

#### Scenario: 教师改分覆盖 AI 分数

- **WHEN** AI 给某提交打了 70 分，张老师改分为 90
- **THEN** 学生端看到的最终分数为 90（教师分），AI 的 70 分仍保留在 `ai_score` 字段供教师参考

#### Scenario: 跨班批改被拒绝

- **WHEN** 张老师尝试批改高二（1）班的作业提交
- **THEN** 返回 403，不修改提交记录

### Requirement: 学生查看批改结果

学生 SHALL 能查看本人作业提交的批改结果，MUST 包含最终分数（教师分优先，无教师分则显示 AI 分，均无则显示"待批改"）和评语。MUST NOT 展示其他学生的答案或分数。

#### Scenario: 学生查看已批改作业

- **WHEN** 王芳查看"一元二次方程练习"的提交结果，该提交已被教师改分为 85
- **THEN** 显示分数 85 和教师评语，不显示其他学生的提交

#### Scenario: 学生查看待批改作业

- **WHEN** 王芳的提交状态为 `pending`（AI 和教师均未批改）
- **THEN** 显示"待批改"，不显示分数或评语

### Requirement: 错题收录钩子

当教师改分将某提交判为错误（`teacher_score < 60` 或教师标记为错题）时，系统 MUST 在 `MistakeNote` 表插入一条记录，关联学生、班级、学科、题目和作答。AI 初批判错但教师未确认时，MUST NOT 自动写入错题本（仅当教师改分确认判错时写入）。错题本的完整查看与讲解界面由后续变更实现。

#### Scenario: 教师判错自动收录错题

- **WHEN** 张老师给王芳的提交打 50 分（低于 60）
- **THEN** 系统在 `MistakeNote` 表插入一条记录，包含学生 ID、班级、学科、题目题干和学生作答

#### Scenario: 教师判对不收录错题

- **WHEN** 张老师给王芳的提交打 85 分
- **THEN** 不创建 `MistakeNote` 记录

#### Scenario: AI 判错未经教师确认不收录

- **WHEN** AI 给某提交打 50 分但教师尚未改分
- **THEN** 不创建 `MistakeNote` 记录，等待教师确认

### Requirement: 作业关闭与状态

教师 SHALL 能将已发布的作业关闭（`status=closed`）。关闭后的作业 MUST NOT 接受新提交，但已有提交的批改和查看仍可进行。MUST NOT 允许非作者关闭作业。

#### Scenario: 教师关闭作业

- **WHEN** 张老师将"一元二次方程练习"状态改为 `closed`
- **THEN** 学生不能再提交该作业，但张老师仍可批改已有提交，学生仍可查看结果

#### Scenario: 非作者关闭被拒绝

- **WHEN** 李老师（英语）尝试关闭张老师布置的数学作业
- **THEN** 返回 403，作业状态不变

### Requirement: 数据隔离与归属

所有作业接口 MUST 按当前会话身份校验归属：教师只能操作本人任教班级的本人学科作业；学生只能查看和提交本人班级的作业。按 ID 取作业或提交时，MUST 先取行再校验 `class_id`、`subject` 和本人归属，不通过则返回 403。MUST NOT 采信请求体或查询参数中的 `class_id`、`subject` 字段作为授权依据。

#### Scenario: 学生越权查看他人提交被拒

- **WHEN** 王芳尝试通过提交 ID 查看李明的作业提交
- **THEN** 返回 403，不返回他人答案和分数

#### Scenario: 教师越权查看他科作业被拒

- **WHEN** 英语教师李老师尝试查看高二（2）班的数学作业
- **THEN** 返回 403，不返回数学作业数据
