## Purpose

为学生提供错题本能力：基于作业批改产生的判错记录，学生可查看本人错题列表、按学科筛选、标记已掌握，并获取 AI 错因讲解。所有数据严格按学生本人隔离。

## ADDED Requirements

### Requirement: 学生查看本人错题列表

学生 SHALL 能查看本人全部错题记录列表，每条记录 MUST 包含错题 ID、学科、题目题干、学生作答、错因（教师评语）、来源作业（可空）、收录时间、是否已掌握。列表 MUST 支持按学科过滤（可选）和仅查看未掌握错题（可选），按收录时间倒序排列。MUST NOT 返回其他学生的错题记录。空列表 MUST 返回空数组而非错误。

#### Scenario: 学生查看全部错题

- **WHEN** 王芳登录后请求错题列表
- **THEN** 返回王芳本人的全部错题记录，按 `created_at` 倒序，不包含李明或其他学生的错题

#### Scenario: 按学科过滤错题

- **WHEN** 王芳请求错题列表并指定 `subject=数学`
- **THEN** 仅返回王芳数学学科的错题记录

#### Scenario: 仅查看未掌握错题

- **WHEN** 王芳请求错题列表并指定 `only_unmastered=true`
- **THEN** 仅返回王芳 `mastered=false` 的错题记录

#### Scenario: 无错题时返回空列表

- **WHEN** 李明尚无任何错题记录
- **THEN** 返回空数组 `[]`，不报错

### Requirement: 学生查看错题详情

学生 SHALL 能通过错题 ID 查看单条错题详情，MUST 包含学科、题目题干、学生作答、错因、来源作业标题（可空）、收录时间、是否已掌握及掌握时间。按 ID 取错题时 MUST 先取行再校验 `student_id == current.user_id`，不通过则返回 403。MUST NOT 允许学生查看他人错题。

#### Scenario: 学生查看本人错题详情

- **WHEN** 王芳请求自己的某条错题详情
- **THEN** 返回该错题的完整字段，包括题目、作答、错因和掌握状态

#### Scenario: 学生越权查看他人错题被拒

- **WHEN** 王芳尝试通过错题 ID 查看李明的错题
- **THEN** 返回 403，不返回错题内容

#### Scenario: 错题不存在返回 404

- **WHEN** 王芳请求一个不存在的错题 ID
- **THEN** 返回 404

### Requirement: 学生标记错题已掌握或取消

学生 SHALL 能将本人错题标记为已掌握（`mastered=true`）或取消掌握（`mastered=false`）。标记已掌握时 MUST 记录 `mastered_at` 时间戳；取消掌握时 `mastered_at` 置空。MUST NOT 允许学生操作他人错题。

#### Scenario: 学生标记错题已掌握

- **WHEN** 王芳将自己的某条错题标记为已掌握
- **THEN** 该错题 `mastered=true`，`mastered_at` 记录当前时间

#### Scenario: 学生取消已掌握

- **WHEN** 王芳将已掌握的错题取消掌握
- **THEN** 该错题 `mastered=false`，`mastered_at` 置空

#### Scenario: 越权标记他人错题被拒

- **WHEN** 王芳尝试将李明的错题标记为已掌握
- **THEN** 返回 403，不修改该错题

### Requirement: AI 错题讲解

学生 SHALL 能对本人错题请求 AI 讲解。系统 MUST 将题目题干、学生作答、教师评语（错因）作为上下文传入 `llm_service.generate_answer`，要求模型返回错因分析与解题思路，MUST NOT 直接给出最终答案（默认采用解题引导风格）。未配置 API Key 时 MUST 返回降级提示而非报错。AI 讲解 MUST 只读取本人错题内容，MUST NOT 暴露其他学生数据。

#### Scenario: 学生请求错题讲解

- **WHEN** 王芳对自己的一道错题点击"AI 讲解"
- **THEN** 系统返回 AI 生成的错因分析与解题思路，不直接给出最终答案

#### Scenario: AI 未配置时降级

- **WHEN** 王芳请求讲解但服务端未配置 API Key
- **THEN** 返回降级提示（如"AI 讲解暂未配置，请联系教师"），不抛异常

#### Scenario: 越权讲解他人错题被拒

- **WHEN** 王芳尝试请求李明错题的 AI 讲解
- **THEN** 返回 403，不调用 AI

### Requirement: 数据隔离与归属

所有错题接口 MUST 按当前会话学生身份校验归属：`student_id` 只从 JWT 会话取，不采信请求体或查询参数中的同名字段。按 ID 取错题时 MUST 先取行再校验 `student_id == current.user_id`，不通过返回 403 并写审计日志。MUST NOT 采信请求中的 `student_id` 字段作为授权依据。

#### Scenario: 请求参数中的 student_id 被忽略

- **WHEN** 王芳在请求体或查询参数中传入 `student_id=李明的ID`
- **THEN** 系统忽略该字段，仍以王芳本人身份查询，不返回李明的错题

#### Scenario: 跨班学生互不可见错题

- **WHEN** 高二（1）班李明和高二（2）班王芳各自有错题
- **THEN** 李明只能看到本人错题，王芳只能看到本人错题，互不可见
