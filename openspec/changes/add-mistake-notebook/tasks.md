## 1. 数据模型与数据库迁移

- [x] 1.1 在 `models.py` 为 `MistakeNote` 表新增 `mastered`（Boolean，默认 False，`server_default="0"`）、`mastered_at`（DateTime，可空）字段。验证：`python -c "import models; print('ok')"` 无报错
- [x] 1.2 在 `database.run_simple_migrations()` 中为 `mistake_notes` 表增加 `ALTER TABLE ADD COLUMN mastered INTEGER DEFAULT 0` 和 `ALTER TABLE ADD COLUMN mastered_at DATETIME` 迁移逻辑，用 `PRAGMA table_info` 检测列是否存在。验证：临时库启动后 `mistake_notes` 表包含两列新字段，已有记录 `mastered=0`、`mastered_at=NULL`
- [x] 1.3 在 `scripts/check_layering.py` 的 `LAYERS` 字典登记 `mistake_service: BUSINESS`。验证：`python scripts/check_layering.py` 通过

## 2. 后端服务层（mistake_service.py）

- [x] 2.1 新建 `mistake_service.py`，定义 `MistakeServiceError`（status_code + detail）和 `UserContext` dataclass（复用 homework_service 的同名字段），以及 `_utcnow`、`_get_mistake_or_404`、`_assert_student_owns_mistake` 辅助函数。验证：`python -c "import mistake_service; print('ok')"` 无报错
- [x] 2.2 实现 `list_student_mistakes(db, ctx, subject=None, only_unmastered=False)`：按 `student_id == ctx.user_id` 过滤，可选 `subject` 与 `mastered=False` 过滤，`created_at` 倒序，`LIMIT 200`。验证：返回数据只含本人错题，学科过滤和仅未掌握过滤正确
- [x] 2.3 实现 `get_mistake_detail(db, ctx, mistake_id)`：取行后校验 `student_id == ctx.user_id`，不通过抛 403。验证：本人错题返回详情，他人错题返回 403，不存在返回 404
- [x] 2.4 实现 `toggle_mastered(db, ctx, mistake_id, mastered: bool)`：取行 + 校验归属，更新 `mastered` 和 `mastered_at`（掌握时设当前时间，取消时置空）。验证：标记后 `mastered=True` 且 `mastered_at` 非空，取消后 `mastered=False` 且 `mastered_at` 为空
- [x] 2.5 实现 `explain_mistake(db, ctx, mistake_id)`：取行 + 校验归属，拼接题目/作答/评语调用 `llm_service.generate_answer(question, None, system_prompt=错题讲解提示词, tutor_enabled=True)`；返回 None 时返回 `(None, False)`，有结果返回 `(文本, True)`。验证：假模型返回讲解文本，未配置 Key 时返回可用标记 False

## 3. 后端路由层（routers/mistake.py）

- [x] 3.1 新建 `routers/mistake.py`，全部端点使用 `Depends(get_current_student)`；实现 `GET /api/student/mistakes`（query: `subject`, `only_unmastered`）、`GET /api/student/mistakes/{mistake_id}`、`PUT /api/student/mistakes/{mistake_id}/mastered`（body: `{mastered: bool}`）、`POST /api/student/mistakes/{mistake_id}/explain`。验证：用学生 token 调用，列表/详情/掌握/讲解均正常
- [x] 3.2 在 `main.py` 注册 `mistake.router`。验证：`/docs` 或 `openapi.json` 包含新路由（ENABLE_DOCS=true 时）

## 4. 前端 API 层（lib/api.ts）

- [x] 4.1 新增错题相关类型与方法：`MistakeDTO`、`listStudentMistakes(subject?, onlyUnmastered?)`、`getMistake(id)`、`toggleMistakeMastered(id, mastered)`、`explainMistake(id)`。验证：`npx tsc --noEmit` 无类型错误

## 5. 前端学生端（app/student/page.tsx）

- [x] 5.1 `StudentMistakes` 改为调用 `listStudentMistakes` 渲染真实错题列表，移除演示卡。验证：接口返回数据正确显示，空列表显示空状态
- [x] 5.2 实现学科筛选（全部/数学/语文/英语/物理/化学）和「仅未掌握」开关。验证：切换筛选条件后列表正确更新
- [x] 5.3 实现掌握标记：每条错题提供「标记已掌握/取消掌握」按钮，调用 `toggleMistakeMastered` 并更新本地状态。验证：点击后掌握状态切换，`mastered_at` 正确显示
- [x] 5.4 实现 AI 讲解：每条错题提供「AI 讲解」按钮，调用 `explainMistake` 并以 Markdown 展示结果。验证：点击后显示讲解内容，未配置 AI 时显示降级提示
- [x] 5.5 首页 `StudentDashboard` 的「我的错题」统计卡改为调用 `listStudentMistakes(onlyUnmastered=true)` 取 `.length`。验证：数值随真实未掌握错题数变化

## 6. 测试（apitest/check_mistake.py）

- [x] 6.1 正常路径：学生查看错题列表（含学科过滤、仅未掌握）、查看详情、标记掌握/取消、AI 讲解。验证：全部接口返回正确数据与状态
- [x] 6.2 失败路径：错题不存在返回 404、AI 未配置时降级、空列表返回空数组。验证：错误码与降级行为符合预期
- [x] 6.3 越权路径：学生查看他人错题、标记他人错题、讲解他人错题均返回 403。验证：均返回 403，不泄露他人数据
- [x] 6.4 数据隔离：同班不同学生互不可见错题，请求参数中的 `student_id` 被忽略。验证：返回数据只含本人错题

## 7. 验证与门禁

- [x] 7.1 运行 `backend\.venv\Scripts\python.exe scripts\check.py`，全部子项 PASS（openspec 校验、分层、密钥扫描、tsc、全部 apitest）。验证：输出全绿
- [x] 7.2 Docker 端到端验证：教师判错 → 学生查看错题列表 → 标记掌握 → AI 讲解。验证：流程走通，越权返回 403
- [x] 7.3 数据库迁移验证：在已有数据包的库上重启后端，确认 `ALTER TABLE` 成功且无数据丢失。验证：`PRAGMA table_info(mistake_notes)` 含 `mastered`、`mastered_at`，旧错题记录完整
