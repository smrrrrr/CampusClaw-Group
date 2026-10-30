## 1. 后端服务层（analytics_service.py）

- [x] 1.1 新建 `analytics_service.py`，定义 `AnalyticsServiceError`、`UserContext`（复用 homework_service 字段）、`TeacherContext` 辅助类型，以及 `_utcnow`、`_subject_mastery` 等内部函数。验证：`python -c "import analytics_service; print('ok')"` 无报错
- [x] 1.2 实现 `get_student_overview(db, ctx)`：聚合本人累计提问数（messages role=user via conversations）、作业提交数（teacher_score IS NOT NULL）、作业正确率（avg teacher_score，四舍五入到整数，无则 None）、错题累计数。验证：返回数据只含本人，无数据时正确率为 None、其余为 0
- [x] 1.3 实现 `get_student_mastery(db, ctx)`：按学科计算掌握度（成绩占 60% + 错题掌握率占 40%，无作业退化为错题掌握率，无数据为 null），返回各学科掌握度列表、综合掌握度、近期成绩趋势（按 teacher_graded_at 倒序最近 10 条，含作业标题、分数、学科、时间）。验证：掌握度在 0-100，综合为各非 null 学科平均
- [x] 1.4 实现 `generate_student_portrait(db, ctx)`：拼接本人统计摘要，调用 `llm_service.generate_answer(system_prompt=画像提示词, tutor_enabled=False)`，用 `model_json.parse_model_json` 解析 style/strengths/weaknesses/suggestion；未配置 Key 返回 `(None, False)`。验证：假模型返回画像 JSON，未配置 Key 返回可用标记 False
- [x] 1.5 实现 `get_class_analytics(db, teacher_ctx, class_id, subject=None)`：校验班级在任教范围（含 homeroom）、subject 为空或等于教师学科；聚合班级平均分、各学科平均分、分数段分布（<60/60-79/80-100）、提交率、错题率、学生掌握度排行（姓名、综合掌握度、薄弱学科）。验证：跨班/跨学科返回 403，不返回作答/评语原文

## 2. 后端路由层（routers/analytics.py + main.py）

- [x] 2.1 新建 `routers/analytics.py`，学生端点用 `Depends(get_current_student)`：`GET /api/student/analytics/overview`、`GET /api/student/analytics/mastery`、`POST /api/student/analytics/portrait`；教师端点用 `Depends(get_current_teacher)`：`GET /api/teacher/analytics/class`（query: class_id, subject 可选）。验证：用对应 token 调用返回正确数据
- [x] 2.2 在 `main.py` 注册 `analytics.router`，在 `scripts/check_layering.py` 登记 `analytics_service: BUSINESS`。验证：`/docs` 含新路由，`python scripts/check_layering.py` 通过

## 3. 前端 API 层（lib/api.ts）

- [x] 3.1 新增学情类型与方法：`StudentOverviewDTO`、`SubjectMasteryDTO`、`StudentPortraitDTO`、`ClassAnalyticsDTO`，以及 `getStudentAnalyticsOverview()`、`getStudentAnalyticsMastery()`、`getStudentAnalyticsPortrait()`、`getTeacherClassAnalytics(classId, subject?)`。验证：`npx tsc --noEmit` 无类型错误

## 4. 前端学生端学情分析页

- [x] 4.1 `StudentAnalytics` 改为调用 `getStudentAnalyticsOverview` 渲染四张统计卡（累计提问、作业提交、正确率、错题累计），无数据时显示 0 或"暂无"。验证：接口数据正确显示
- [x] 4.2 调用 `getStudentAnalyticsMastery` 渲染各学科掌握度雷达图、综合掌握环图、近期趋势折线、各学科掌握热力条。验证：图表数据来自接口，无数据学科不伪造
- [x] 4.3 调用 `getStudentAnalyticsPortrait` 渲染 AI 学习画像（学习风格、优势/待提升学科、建议），未配置 AI 时显示降级提示。验证：画像内容来自接口，降级时不阻塞其他图表

## 5. 前端教师端学情页面

- [x] 5.1 班主任「本班学情（全科）」入口改为调用 `getTeacherClassAnalytics(homeroomClassId)` 渲染班级学情汇总（平均分、分数段分布、提交率、错题率、学生排行）。验证：数据来自接口，不显示占位
- [x] 5.2 任课「学情分析（单科）」改为调用 `getTeacherClassAnalytics(classId, subject)` 渲染本学科学情汇总。验证：切班后数据更新，不显示其他学科数据

## 6. 测试（apitest/check_analytics.py）

- [x] 6.1 正常路径：学生查看学情概览、学科掌握度、AI 画像；教师查看班级全科/单科学情。验证：接口返回正确数据
- [x] 6.2 失败路径：无作业记录时正确率为 None、AI 未配置时画像降级、无数据学科掌握度为 null。验证：降级行为符合预期
- [x] 6.3 越权路径：学生查看班级学情返回 403、教师跨班/跨学科返回 403、请求参数 class_id/subject 被忽略。验证：均返回 403
- [x] 6.4 数据隔离：同班不同学生学情互不可见，班级学情不返回作答/评语原文。验证：聚合数据不含隐私原文

## 7. 验证与门禁

- [ ] 7.1 运行 `backend\.venv\Scripts\python.exe scripts\check.py`，全部子项 PASS（含 check_analytics）。验证：输出全绿
- [ ] 7.2 Docker 端到端验证：教师批改作业后，学生查看学情概览与掌握度、获取 AI 画像；教师查看班级学情。验证：流程走通，越权返回 403
