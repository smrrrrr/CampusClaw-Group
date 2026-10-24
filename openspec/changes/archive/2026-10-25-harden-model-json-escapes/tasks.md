## 1. 共用解析函数

- [x] 1.1 新增 `backend/model_json.py`：`load_model_json(raw) -> (obj, repairs)` 与 `ModelJSONError`；剥除单层代码围栏；只在字符串字面量内按 design §2 规则逐字符修补反斜杠，含 `n` 开头命令白名单；失败消息带 json 报出的行列
- [x] 1.2 新增 `has_control_chars(text)`：检测退格（U+0008）、换页（U+000C）

## 2. 智能命题

- [x] 2.1 `question_service.parse_output` 改用 `load_model_json`，保留 `questions` / `gaps` 检查，返回修补次数；`OutputParseError` 消息带行列
- [x] 2.2 `QUESTION_PROMPT` 第 6 条补「JSON 字符串里每个 LaTeX 反斜杠写成两个」及示例
- [x] 2.3 `validate_question` 增加控制字符检查（`stem`、选项文本、字符串答案、`explanation`），原因「含不可见控制字符，疑似公式转义错误」
- [x] 2.4 `routers/quiz.py`：`generate` 事件 `detail` 增加 `escape_repairs`；失败记录 `error` 带行列，不写模型原文；SSE `error` 帧文案不变

## 3. 备课学生稿

- [x] 3.1 `lesson_service.parse_student_output` 改用 `load_model_json`，对外错误文案不变；修补次数写服务端日志（不含正文）
- [x] 3.2 `STUDENT_PROMPT` 补同样的双反斜杠示例
- [x] 3.3 `validate_student` 增加控制字符检查，命中时按未通过检查处理

## 4. 离线回归（不调用网关）

- [x] 4.1 新增 `apitest/check_model_json.py`：修补规则单元用例，覆盖 design §7 列出的全部情况（混用写法、`\f \b \t \r` + 字母、`\n` 白名单与非白名单、合法转义不变、字符串外不变、截断/正文/缺字段仍失败、修补计数）
- [x] 4.2 `apitest/check_question_bank.py`：虚构 `stream_chat` 返回由真实失败样本提炼的片段，断言生成成功、题干还原、`escape_repairs` 计数正确；含 U+000C 的题判未通过；截断输出的失败原因含行列且无原文
- [x] 4.3 `apitest/check_lesson_prep.py`：虚构学生稿输出含单反斜杠公式时保存成功；含 U+000C 时报错且旧稿不变
- [x] 4.4 回归 `check_question_bank`、`check_lesson_prep`、`check_research_materials`、`check_mcp_tools`、`check_sqlite_storage`、`check_lessons_2_5` 全部通过；`openspec validate harden-model-json-escapes --strict` 通过

## 5. 部署与真实复测（网关额度重置后）

- [x] 5.1 备份数据库；`docker compose up -d --build backend` 后确认容器内为新代码
- [x] 5.2 真实复测命题：与 2026-10-23 失败时相同的参数（1 份资料、立体几何 + 空间向量、5 题）至少生成 3 次，记录成功次数、各次 `escape_repairs`、未通过原因
- [x] 5.3 浏览器内对生成的题目逐题复核：公式渲染正常，通过 / 驳回 / 编辑各至少一次
- [x] 5.4 真实复测备课：生成教师教案 → 定稿 → 生成两份学生稿，检查公式渲染与去答案；不发布到真实班级
- [x] 5.5 编写 `validation.md`，按「实际跑过」记录命令、结果与未覆盖项；清理测试数据或说明保留原因

## 6. 归档前

- [x] 6.1 确认 `add-smart-question-generation` 已先归档，再核对本变更的 MODIFIED 块与主规约一致后归档
