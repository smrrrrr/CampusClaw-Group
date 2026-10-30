## Context

当前 `Homework`、`HomeworkSubmission`、`MistakeNote` 三张表只有骨架字段（`id`、`class_id`、时间戳），无任何业务字段。前端学生「交作业」和教师「作业与改分」均为演示/占位。本变更需扩展表结构、新增服务与路由、接入 AI 初批，并为错题本提供收录钩子。动机与范围见 [proposal.md](proposal.md)，行为契约见 [specs/homework/spec.md](specs/homework/spec.md)。

项目无 Alembic，表结构变更通过 `database.run_simple_migrations()` 手写 `ALTER TABLE`；后端分层为 `routers → *_service → models/database`，新模块需在 `scripts/check_layering.py` 登记层级。

## Goals / Non-Goals

**Goals:**
- 扩展三张骨架表的业务字段，通过 `ALTER TABLE` 平滑迁移（不丢数据）
- 实现作业布置、提交、AI 初批、教师改分的完整接口与前端
- 严格按班级/学科/本人归属隔离，身份只取自 JWT 会话
- AI 初批结果仅供参考，教师改分为最终成绩
- 教师判错时自动写入 `MistakeNote`，为错题本功能预留数据

**Non-Goals:**
- 不实现错题本的查看与讲解界面（后续变更）
- 不实现学情诊断的统计与画像（后续变更）
- 不实现作业题目的富文本/图片附件（本期仅文本题目与答案）
- 不实现作业截止的定时自动关闭（需手动关闭）

## Decisions

### 1. 数据模型扩展

`Homework` 表新增字段：`subject`、`teacher_id`（FK users）、`title`、`content_json`（题目结构化 JSON，预留多题扩展）、`due_at`、`status`（draft/published/closed）、`updated_at`。

`HomeworkSubmission` 表新增字段：`homework_id`（FK homeworks）、`answer_text`、`submitted_at`、`ai_score`、`ai_feedback`、`ai_graded_at`、`teacher_score`、`teacher_feedback`、`teacher_graded_at`、`status`（pending/ai_graded/teacher_graded）。唯一约束 `(homework_id, student_id)` 保证一人一份提交。

`MistakeNote` 表新增字段：`subject`、`homework_id`（FK homeworks，可空）、`question_stem`、`student_answer`、`reason`（教师评语或 AI 错因）。

**选择理由**：复用现有骨架表名，`ALTER TABLE ADD COLUMN` 即可迁移，无需 drop 重建。`content_json` 预留多题结构但本期只存单题文本，避免后续再次改表。

**替代方案**：新建独立表而非扩展骨架表——会导致骨架表残留且迁移更复杂，放弃。

### 2. AI 初批方案

调用 `llm_service.generate_answer`，提示词要求模型返回 JSON：`{"score": 0-100, "feedback": "评语", "is_wrong": true/false}`。使用 `model_json.parse_model_json()` 解析（复用命题功能的反斜杠修补与控制字符兜底）。

AI 初批为同步接口（教师点击后等待），对全部 `pending` 提交逐个调用。失败时跳过该提交并记录错误，不中断其他提交的批改。

**选择理由**：复用现有 LLM 服务和 JSON 修补逻辑，无需新增模型调用链路。同步实现简单，单次作业提交量不大（一个班几十人），可接受。

**替代方案**：异步队列 + 后台任务——当前项目无 Celery/RQ 基础设施，引入复杂度高，放弃。

### 3. 权限隔离

所有接口通过 `deps.get_current_teacher` / `deps.get_current_student` 获取身份，`class_id`、`subject` 只从 JWT 和数据库取。按 ID 取资源时先取行再校验：
- 教师布置/批改：校验 `homework.class_id ∈ current.teaching_classes` 且 `homework.subject == current.subject`
- 学生查看/提交：校验 `homework.class_id == current.class_id`
- 跨资源访问返回 403 并写审计日志（复用 `services.write_audit_log`）

### 4. 错题收录钩子

在教师改分接口中，当 `teacher_score < 60` 时，在同一事务内插入 `MistakeNote` 记录。AI 初批不触发收录，必须等教师确认。

**选择理由**：保证错题数据的准确性（教师确认而非 AI 自动），且与改分在同一事务保证一致性。

### 5. 前端结构

学生端 `StudentAssignments` 组件改为调用 `api.listStudentHomeworks()` 和 `api.submitHomework()`，按状态展示提交/批改结果。教师端 `TeacherHome` 的 `tools` 视图新增作业列表、布置表单、提交批改界面。

## Risks / Trade-offs

- **[AI 评分不一致]** → 同一答案多次调用 AI 可能分数不同。缓解：AI 分仅供参考，教师改分为最终成绩；提示词要求给出评分依据。
- **[ALTER TABLE 在已有数据表上失败]** → 骨架表目前无业务数据（空表），增列安全；但仍需在迁移前用 SQLite backup API 备份。
- **[AI 批改耗时长]** → 一次批改多个提交需多次模型调用。缓解：提示词精简，单次作业提交量控制在班级规模内；后续可考虑批处理。
- **[content_json 单题存 JSON 略重]** → 本期单题场景可直接用 `content_json` 存 `{"questions": [{"stem": "..."}]}`，预留扩展但当前只有一题。

## Migration Plan

1. **备份**：用 SQLite backup API 将 `data/current/app.db` 备份到 `data/current/before-homework-grading-<时间戳>.db`
2. **扩展模型**：在 `models.py` 为三张表添加新字段
3. **手写迁移**：在 `database.run_simple_migrations()` 中用 `PRAGMA table_info` 检测列是否存在，不存在则 `ALTER TABLE ADD COLUMN`
4. **建表兼容**：`Base.metadata.create_all` 会为新环境创建完整表；迁移逻辑只处理已有骨架表的增列
5. **回滚**：若迁移失败，从备份恢复数据库；代码回滚到上一提交

## Open Questions

- 作业题目是否需要支持图片/公式附件？本期按纯文本处理，公式用 LaTeX 字符串。
- 教师改分时是否需要"标记为错题"的显式开关，还是仅以分数 < 60 自动判定？本期采用分数阈值自动判定，评语作为错因。
