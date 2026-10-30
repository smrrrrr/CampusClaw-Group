## Context

作业批改（`add-homework-grading`）已写入 `Homework`、`HomeworkSubmission`、`MistakeNote` 真实数据，错题本（`add-mistake-notebook`）已提供 `mastered`/`mastered_at` 字段。学生端学情分析页与教师端学情入口仍为演示/占位。本变更复用现有五张表（`homeworks`、`homework_submissions`、`mistake_notes`、`conversations`、`messages`），不新增表结构。后端分层遵循 `routers → *_service → models/database`，新模块需在 `scripts/check_layering.py` 登记。

## Goals / Non-Goals

**Goals:**
- 学生本人学情概览、各学科掌握度、近期趋势、AI 学习画像
- 教师班级学情汇总（班主任全科 / 任课单科）
- 严格按身份、班级、学科、本人归属隔离，不返回隐私原文
- AI 画像复用 `llm_service.generate_answer`，未配置 Key 时降级

**Non-Goals:**
- 不新增数据库表或改表结构
- 不实现学情数据的定时缓存或预计算（实时聚合，数据量可控）
- 不实现知识点级别的细粒度诊断（仅到学科维度）
- 不实现学生间横向对比（教师排行只面向教师，学生只看本人）
- 不实现学情数据导出（CSV/PDF）

## Decisions

### 1. 数据来源与聚合

所有统计实时聚合自现有表，不新增缓存表：
- 累计提问：`messages` 表 `role='user'` 的消息数，通过 `conversation.student_id` 关联本人
- 作业提交/正确率：`homework_submissions` 中 `teacher_score IS NOT NULL` 的记录，按 `homework.subject` 分组
- 错题：`mistake_notes` 按 `student_id`、`subject` 聚合，区分 `mastered`
- 学科列表：取本人有数据的学科 ∪ 本班开设学科（`SUBJECT_NAMES` 键集合）

**选择理由**：单班数据量小（几十人 × 几学科 × 几次作业），实时聚合性能可接受，避免缓存一致性问题。

**替代方案**：定时任务预计算到 `analytics_snapshots` 表——当前无定时任务基础设施，且实时查询足够快，放弃。

### 2. 学科掌握度算法

单学科掌握度（0-100）：
```
若有该学科教师批改成绩:
  accuracy = avg(teacher_score) / 100
  若有该学科错题:
    mastery_rate = count(mastered=True) / count(total)
    subject_mastery = round(accuracy * 60 + mastery_rate * 40)
  否则:
    subject_mastery = round(accuracy * 100)
否则若有该学科错题:
  mastery_rate = count(mastered=True) / count(total)
  subject_mastery = round(mastery_rate * 100)
否则:
  subject_mastery = null
```

综合掌握度 = 所有非 null 学科掌握度的平均值（无数据时 null）。

**选择理由**：作业成绩占 60%（反映知识掌握），错题掌握率占 40%（反映订正情况），权重偏成绩但兼顾订正。纯错题场景（无作业）退化为错题掌握率。

**替代方案**：等权平均——作业成绩是核心指标，应占更高权重，放弃。

### 3. 服务层与路由层

新建 `analytics_service.py`（`BUSINESS` 层），导出：
- `get_student_overview(db, ctx) -> dict`
- `get_student_mastery(db, ctx) -> dict`（含各学科、综合、趋势）
- `generate_student_portrait(db, ctx) -> tuple[str|None, bool]`
- `get_class_analytics(db, teacher_ctx, class_id, subject=None) -> dict`

新建 `routers/analytics.py`：
- `GET /api/student/analytics/overview`（`Depends(get_current_student)`）
- `GET /api/student/analytics/mastery`（`Depends(get_current_student)`）
- `POST /api/student/analytics/portrait`（`Depends(get_current_student)`）
- `GET /api/teacher/analytics/class`（`Depends(get_current_teacher)`，query: `class_id`, `subject` 可选）

在 `main.py` 注册 `analytics.router`。

**权限校验**：
- 学生接口：`student_id` 只从 JWT 取，所有查询限定本人
- 教师接口：`class_id` 必须在 `teaching_classes`（班主任 `homeroom_class_id` 也算）；`subject` 非空时必须等于教师 `subject`；班主任全科接口 `subject` 留空
- 跨范围访问返回 403，由 `audit_403_middleware` 写审计

### 4. AI 学习画像

调用 `llm_service.generate_answer`，system prompt 要求模型返回 JSON：
```json
{"style": "学习风格标签", "strengths": ["优势学科"], "weaknesses": ["待提升学科"], "suggestion": "学习建议"}
```
输入上下文为该生的：各学科掌握度、累计提问、错题数/未掌握数、近期趋势摘要。不传入题目原文或作答原文。

使用 `model_json.parse_model_json()` 解析（复用命题功能的 JSON 修补逻辑）。未配置 Key 时 `generate_answer` 返回 None，接口返回 `(None, False)`。

**选择理由**：复用现有 LLM 调用链路和 JSON 解析工具，画像只基于聚合统计，不涉及隐私原文。

### 5. 教师班级学情数据结构

班级汇总返回：
- `class_average`: 全班所有 `teacher_score` 平均（null 若无）
- `subject_averages`: {subject: average}
- `score_distribution`: {`<60`: n, `60-79`: n, `80-100`: n}（按学生单科最高分计，或按提交计——本期按提交记录计）
- `submission_rate`: 已提交人数 / 班级人数
- `mistake_rate`: 有错题的学生数 / 班级人数
- `student_ranking`: [{name, overall_mastery, weak_subjects}] 按综合掌握度降序

**隐私边界**：只返回姓名、掌握度分值、薄弱学科列表，不返回作答原文、评语、题目。

## Risks / Trade-offs

- **[实时聚合性能]** → 单班数据量小（<50 人 × <10 次作业），SQLite 查询毫秒级；后续若数据量大可加索引或预计算
- **[AI 画像 JSON 解析失败]** → `parse_model_json` 已有兜底；解析失败时返回 `(None, False)` 并记录日志，不影响其他统计
- **[掌握度算法争议]** → 权重 60/40 为合理初始值，可在后续迭代调整；本期不做个性化权重
- **[班级人数统计]** → 需查询 `users` 表 `class_id` 且 `role='student'` 的人数；未分班学生不计入分母

## Migration Plan

1. **无表结构变更**：复用现有五张表，不跑迁移
2. **新增模块登记**：`scripts/check_layering.py` 加 `analytics_service: BUSINESS`
3. **部署**：后端重启后自动加载新路由；前端重新构建部署
4. **回滚**：移除 `analytics.router` 注册与前端调用即可，不影响已有数据
