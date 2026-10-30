## 1. 数据模型与数据库迁移

- [x] 1.1 在 `models.py` 为 `Homework` 表新增 `subject`、`teacher_id`、`title`、`content_json`、`due_at`、`status`、`updated_at` 字段；为 `HomeworkSubmission` 新增 `homework_id`、`answer_text`、`submitted_at`、`ai_score`、`ai_feedback`、`ai_graded_at`、`teacher_score`、`teacher_feedback`、`teacher_graded_at`、`status` 字段及 `(homework_id, student_id)` 唯一约束；为 `MistakeNote` 新增 `subject`、`homework_id`、`question_stem`、`student_answer`、`reason` 字段。验证：`python -c "import models; print('ok')"` 无报错
- [x] 1.2 在 `database.run_simple_migrations()` 中为三张表增加 `ALTER TABLE ADD COLUMN` 迁移逻辑，用 `PRAGMA table_info` 检测列是否存在。验证：临时库启动后三张表包含全部新字段，`PRAGMA table_info` 查询确认
- [x] 1.3 在 `scripts/check_layering.py` 的 `LAYERS` 字典登记 `homework_service: BUSINESS`。验证：`python scripts/check_layering.py` 通过

## 2. 后端服务层（homework_service.py）

- [x] 2.1 实现 `create_homework`：校验教师任教班级与学科，创建 `draft` 状态作业。验证：单元测试确认非任教班级返回 403
- [x] 2.2 实现 `publish_homework` / `close_homework`：仅作者可操作，状态流转 draft→published→closed。验证：非作者操作返回 403
- [x] 2.3 实现 `list_teacher_homeworks`：按任教班级+学科过滤，含提交人数统计。验证：返回数据不含其他班级/学科
- [x] 2.4 实现 `list_student_homeworks`：按学生班级过滤已发布作业，含本人提交状态。验证：不返回草稿和其他班作业
- [x] 2.5 实现 `submit_homework`：校验班级与截止时间，upsert 提交记录（同一学生同一作业覆盖）。验证：截止后返回 400，跨班返回 403
- [x] 2.6 实现 `get_submission` / `list_submissions`：按作业 ID 取提交，校验归属。验证：学生只能取本人提交，教师只能取任教班级作业的提交
- [x] 2.7 实现 `ai_grade_homework`：对全部 `pending` 提交调用 `llm_service.generate_answer`，用 `model_json.parse_model_json` 解析 JSON 分数与评语，写入 `ai_score`/`ai_feedback`，状态变 `ai_graded`；跳过 `teacher_graded` 提交；失败不写入部分结果。验证：假模型返回固定分数，确认写入正确；失败时状态保持 pending
- [x] 2.8 实现 `teacher_grade_submission`：校验归属，写入 `teacher_score`/`teacher_feedback`，状态变 `teacher_graded`；当 `teacher_score < 60` 时在同一事务插入 `MistakeNote` 记录。验证：判错时 `MistakeNote` 表有新记录，判对时无

## 3. 后端路由层（routers/homework.py）

- [x] 3.1 教师路由：`POST /api/teacher/homeworks`（创建）、`PUT /api/teacher/homeworks/{id}/publish`、`PUT /api/teacher/homeworks/{id}/close`、`GET /api/teacher/homeworks`（列表）、`GET /api/teacher/homeworks/{id}/submissions`（提交列表）。验证：用教师 token 调用，越权返回 403
- [x] 3.2 教师批改路由：`POST /api/teacher/homeworks/{id}/ai-grade`、`PUT /api/teacher/submissions/{id}/grade`。验证：AI 批改后状态正确，教师改分覆盖 AI 分
- [x] 3.3 学生路由：`GET /api/student/homeworks`（列表）、`POST /api/student/homeworks/{id}/submit`（提交）、`GET /api/student/submissions/{id}`（查看结果）。验证：学生只能看本班作业，跨班提交 403
- [x] 3.4 在 `main.py` 注册 `homework.router`。验证：`/docs` 或 `openapi.json` 包含新路由（ENABLE_DOCS=true 时）

## 4. 前端 API 层（lib/api.ts）

- [x] 4.1 新增作业相关类型与方法：`HomeworkDTO`、`HomeworkSubmissionDTO`、`listTeacherHomeworks`、`createHomework`、`publishHomework`、`closeHomework`、`listHomeworkSubmissions`、`aiGradeHomework`、`gradeSubmission`、`listStudentHomeworks`、`submitHomework`、`getSubmission`。验证：`npx tsc --noEmit` 无类型错误

## 5. 前端学生端（app/student/page.tsx）

- [x] 5.1 `StudentAssignments` 改为调用 `listStudentHomeworks` 渲染真实作业列表，移除 `DEMO_ASSIGNMENTS`。验证：接口返回数据正确显示，空列表显示空状态
- [x] 5.2 实现提交表单：未截止作业显示文本输入框和提交按钮，调用 `submitHomework`。验证：提交后状态更新为"已提交"，截止后禁用提交
- [x] 5.3 显示批改结果：教师分优先，无教师分显示 AI 分，均无显示"待批改"。验证：已批改作业显示分数和评语
- [x] 5.4 首页统计卡"进行中作业""待提交"改为调用接口计数。验证：数值随真实作业数据变化

## 6. 前端教师端（app/teacher/page.tsx）

- [x] 6.1 `tools` 视图实现作业列表、布置表单（标题、题目、截止时间）、发布/关闭按钮。验证：创建草稿、发布、关闭流程正常
- [x] 6.2 实现提交列表与批改界面：查看学生答案、AI 初批按钮、教师改分输入框和评语。验证：AI 批改后显示 AI 分，教师改分后覆盖为最终分
- [x] 6.3 班主任 `class-homework` 视图实现只读统计：各科作业提交率和平均分。验证：不提供批改操作

## 7. 测试（apitest/check_homework.py）

- [x] 7.1 正常路径：教师创建/发布作业、学生提交、AI 初批、教师改分、学生查看结果。验证：全部状态流转正确
- [x] 7.2 失败路径：截止后提交、草稿不可见、AI 失败不写入、非作者关闭。验证：返回正确错误码和状态
- [x] 7.3 越权路径：学生查看他人提交、教师跨班批改、非任教班级布置。验证：均返回 403
- [x] 7.4 错题收录：教师判错（<60）写入 `MistakeNote`，判对不写入，AI 判错不自动写入。验证：`MistakeNote` 表记录数符合预期

## 8. 验证与门禁

- [x] 8.1 运行 `backend\.venv\Scripts\python.exe scripts\check.py`，全部子项 PASS（openspec 校验、分层、密钥扫描、tsc、全部 apitest）。验证：输出全绿
- [x] 8.2 Docker 端到端验证：教师发布作业→学生提交→AI 初批→教师改分→学生查看结果。验证：四个演示账号流程走通，越权返回 403
- [x] 8.3 数据库迁移验证：在已有数据包的库上重启后端，确认 `ALTER TABLE` 成功且无数据丢失。验证：`PRAGMA table_info(homeworks)` 含全部新字段，旧数据完整
