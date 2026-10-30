## Why

学生端「交作业」和教师端「作业与改分」目前均为演示数据或占位页面，后端 `Homework`、`HomeworkSubmission` 两张表只有骨架字段（`id`、`class_id`、时间戳），没有任何作业业务字段和接口。教师无法布置作业，学生无法真实提交，也没有批改、评分和评语流程。错题本与学情诊断都依赖作业批改产生的判错结果和分数，因此作业批改是后续两块功能的前置基础。

## What Changes

- 扩展 `Homework` 表：新增 `subject`、`teacher_id`、`title`、`content_json`（题目结构化内容）、`due_at`、`status`（draft/published/closed）、`created_at`、`updated_at`
- 扩展 `HomeworkSubmission` 表：新增 `homework_id`、`answer_text`、`submitted_at`、`ai_score`、`ai_feedback`、`ai_graded_at`、`teacher_score`、`teacher_feedback`、`teacher_graded_at`、`status`（pending/ai_graded/teacher_graded）
- 新建 `homework_service.py`（业务层）和 `routers/homework.py`（接口层），在 `check_layering.py` 登记层级
- 教师接口：布置作业（草稿/发布）、查看本班本科目作业列表、查看某次作业的提交列表与批改状态、AI 初批、教师改分/评语、关闭作业
- 学生接口：查看本班待提交/已提交作业列表、提交作业答案、查看本人批改结果（分数+评语）
- AI 初批：调用 `llm_service` 对学生答案进行评分和评语生成，分数与评语仅供教师参考，教师可改分；AI 批改不直接作为最终成绩
- 前端：学生「交作业」页从演示数据改为真实接口；教师「作业与改分」页从占位改为真实接口（布置、批改、改分）
- 错题收录钩子：教师判错（或 AI 判错且教师确认）时，在 `MistakeNote` 表插入一条记录（错题本功能的前置接入点，错题本完整界面由后续变更实现）

## Capabilities

### New Capabilities
- `homework`: 作业布置、学生提交、AI 初批、教师改分与评语、作业状态管理，以及按班级和学科的数据隔离。

### Modified Capabilities
- `student-workspace`: 「交作业」从演示数据改为真实作业列表与提交；首页统计卡中的"进行中作业""待提交"改为真实计数。
- `teacher-workspace`: 「作业与改分」从占位改为真实布置与批改界面；「本班作业（总览）」从占位改为只读提交率与平均分统计。

## Impact

- **后端 (FastAPI)**：`models.py` 扩展 `Homework`、`HomeworkSubmission` 字段并新增 `MistakeNote` 业务字段；`database.py` `run_simple_migrations()` 增加 ALTER TABLE 增列；新增 `homework_service.py`、`routers/homework.py`；`main.py` 注册新路由；`scripts/check_layering.py` 登记新模块层级。
- **数据库 (SQLite)**：`homeworks`、`homework_submissions`、`mistake_notes` 三张表增列；改表前需用 SQLite backup API 备份到 `data/current/before-homework-grading-<时间>.db`。
- **前端 (Next.js)**：`frontend/lib/api.ts` 新增作业相关 API 方法；`frontend/app/student/page.tsx` 的 `StudentAssignments` 改为真实数据；`frontend/app/teacher/page.tsx` 新增 `tools` 视图的作业布置与批改界面。
- **AI**：复用 `llm_service.generate_answer` 进行初批；提示词要求返回 JSON（分数、评语、是否判错），使用 `model_json.py` 的反斜杠修补；AI 结果不写审计日志的原文。
- **安全**：所有接口按教师任教班级/学科、学生本人班级隔离；AI 批改结果不直接作为最终分，教师可改分；不暴露其他学生答案。
- **测试**：`apitest/check_homework.py` 覆盖正常/失败/越权三类场景，使用临时库和假模型。
