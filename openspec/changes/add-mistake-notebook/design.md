## Context

`add-homework-grading` 变更已在 `MistakeNote` 表写入教师判错记录（`teacher_score < 60` 时插入/更新），表字段为 `id`、`class_id`、`student_id`、`subject`、`homework_id`（可空）、`question_stem`、`student_answer`（可空）、`reason`（可空）、`created_at`。学生端「错题」页目前是一张硬编码演示卡，无真实列表、筛选、讲解或掌握标记。本变更在已有数据基础上提供消费层。动机与范围见 [proposal.md](proposal.md)，行为契约见 [specs/mistake-notebook/spec.md](specs/mistake-notebook/spec.md)。

后端分层为 `routers → *_service → models/database`，新模块需在 `scripts/check_layering.py` 登记层级。表结构变更通过 `database.run_simple_migrations()` 手写 `ALTER TABLE`。AI 调用复用 `llm_service.generate_answer`，未配置 Key 时返回 None。

## Goals / Non-Goals

**Goals:**
- 在 `MistakeNote` 表新增 `mastered`、`mastered_at` 字段，支持掌握状态
- 实现学生错题列表、详情、掌握切换、AI 讲解四个接口，严格按本人隔离
- 前端「错题」页从演示改为真实数据，支持学科筛选、仅未掌握、掌握标记、AI 讲解
- 首页「我的错题」统计卡显示真实未掌握错题数

**Non-Goals:**
- 不实现教师端错题统计或班级错题画像（属学情诊断，后续变更）
- 不实现错题的手动添加或删除（错题只由作业批改自动收录）
- 不实现错题的知识点标签或相似度聚类
- 不实现错题导出或打印
- 不修改作业批改的错题收录逻辑（已由 `add-homework-grading` 完成）

## Decisions

### 1. 数据模型扩展

`MistakeNote` 表新增字段：
- `mastered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")`
- `mastered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)`

**选择理由**：掌握状态是错题本的核心交互，直接存在错题行上最简单，查询 `only_unmastered` 只需一个 WHERE 条件。`mastered_at` 记录掌握时间，便于后续学情分析统计。

**替代方案**：单独建 `mistake_mastery` 关联表——过度设计，当前一对一关系不需要独立表，放弃。

### 2. 业务层与路由层结构

新建 `mistake_service.py`，定义本地 `MistakeServiceError`（与 `HomeworkServiceError` 同构）和 `UserContext`（复用同名字段，避免业务层 import `deps`）。函数：
- `list_student_mistakes(db, ctx, subject=None, only_unmastered=False)` → 按 `student_id` 过滤，可选学科与未掌握过滤，`created_at` 倒序
- `get_mistake_or_404(db, mistake_id)` → 取行，不存在抛 404
- `assert_student_owns_mistake(ctx, note)` → 校验 `note.student_id == ctx.user_id`，不通过抛 403
- `get_mistake_detail(db, ctx, mistake_id)` → 取行 + 校验归属
- `toggle_mastered(db, ctx, mistake_id, mastered: bool)` → 取行 + 校验 + 更新 `mastered`/`mastered_at`
- `explain_mistake(db, ctx, mistake_id)` → 取行 + 校验 + 调用 AI

路由层 `routers/mistake.py` 全部使用 `Depends(get_current_student)`，端点：
- `GET /api/student/mistakes?subject=&only_unmastered=`
- `GET /api/student/mistakes/{mistake_id}`
- `PUT /api/student/mistakes/{mistake_id}/mastered`（body: `{mastered: bool}`）
- `POST /api/student/mistakes/{mistake_id}/explain`

**选择理由**：与 `homework_service.py` 模式一致，业务层不依赖 `deps`/`fastapi`，路由层只做参数转换与异常转译。

### 3. AI 错题讲解

调用 `llm_service.generate_answer(question, context_block, system_prompt=..., tutor_enabled=True)`。
- `question`：拼接题目题干、学生作答、教师评语，作为模型输入
- `context_block`：`None`（错题讲解不检索知识库，只基于题目与作答本身）
- `system_prompt`：要求模型分析错因、给出解题思路和关键知识点，不直接给最终答案
- `tutor_enabled=True`：复用解题引导风格

返回值：`generate_answer` 返回 `None`（未配置 Key）时，路由层返回 `{"explanation": None, "available": false}`；有返回时返回 `{"explanation": 文本, "available": true}`。

**选择理由**：错题讲解只需题目与作答上下文，不需要检索本班讲义，避免引入无关资料。`tutor_enabled=True` 保持与助手对话一致的引导风格。同步返回即可，单题讲解耗时可接受。

**替代方案**：流式 SSE 输出——当前页面单题讲解，同步更简单，放弃。

### 4. 权限隔离

所有接口通过 `deps.get_current_student` 获取身份，`student_id` 只从 JWT 取。按 ID 取错题时先取行再校验 `note.student_id == ctx.user_id`，不通过返回 403 并写审计日志（复用 `services.write_audit_log`）。`class_id`、`subject` 不用于授权，只用于列表过滤。

**选择理由**：错题的归属粒度是学生本人，比班级更细；学生只能看自己的错题，即使同班也不可见。

### 5. 前端结构

`frontend/lib/api.ts` 新增：
- `MistakeDTO` 类型（id, subject, question_stem, student_answer, reason, homework_title, created_at, mastered, mastered_at）
- `listStudentMistakes(subject?, onlyUnmastered?)`
- `getMistake(id)`
- `toggleMistakeMastered(id, mastered)`
- `explainMistake(id)`

`frontend/app/student/page.tsx`：
- `StudentMistakes` 改为调用 `listStudentMistakes` 渲染真实列表，移除演示卡
- 新增学科筛选（全部/数学/语文/英语/物理/化学）和「仅未掌握」开关
- 每条错题显示学科标签、题目、作答、错因、收录时间、掌握状态
- 「标记已掌握/取消掌握」按钮调用 `toggleMistakeMastered`
- 「AI 讲解」按钮调用 `explainMistake`，结果以 Markdown 展示
- 首页 `StudentDashboard` 的「我的错题」统计卡调用 `listStudentMistakes(onlyUnmastered=true)` 取 `.length`

**选择理由**：复用现有页面结构，最小化改动。AI 讲解结果用 Markdown 渲染，与助手对话一致。

## Risks / Trade-offs

- **[AI 讲解质量不稳定]** → 同一错题多次讲解可能内容不同。缓解：提示词要求结构化输出（错因、思路、知识点），不直接给答案；讲解结果不持久化，每次重新生成。
- **[ALTER TABLE 在已有数据表上失败]** → `mistake_notes` 表可能已有作业批改写入的记录。缓解：`PRAGMA table_info` 检测列是否存在，不存在才 `ALTER TABLE ADD COLUMN`；迁移前用 SQLite backup API 备份。
- **[错题列表随作业批改增长]** → 学生错题可能较多。缓解：当前班级规模小，暂不分页；列表查询加 `LIMIT`（如 200 条）防止极端情况，后续按需加分页。
- **[AI 讲解耗时]** → 单次讲解一次模型调用。缓解：提示词精简；未配置 Key 时直接降级，不阻塞页面。

## Migration Plan

1. **备份**：用 SQLite backup API 将 `data/current/app.db` 备份到 `data/current/before-mistake-notebook-<时间戳>.db`
2. **扩展模型**：在 `models.py` 为 `MistakeNote` 添加 `mastered`、`mastered_at` 字段
3. **手写迁移**：在 `database.run_simple_migrations()` 中用 `PRAGMA table_info` 检测列是否存在，不存在则 `ALTER TABLE ADD COLUMN mastered INTEGER DEFAULT 0` 和 `ALTER TABLE ADD COLUMN mastered_at DATETIME`
4. **建表兼容**：`Base.metadata.create_all` 会为新环境创建完整表；迁移逻辑只处理已有表的增列
5. **回滚**：若迁移失败，从备份恢复数据库；代码回滚到上一提交

## Open Questions

- 错题列表是否需要分页？当前班级规模小，暂不加；若错题量大再补。
