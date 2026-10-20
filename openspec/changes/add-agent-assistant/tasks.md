## 1. 数据模型

- [x] 1.1 在 models.py 新增 AgentConfig 表（id, class_id, subject, teacher_id FK 联合唯一, system_prompt, tutor_enabled, updated_at）；新增 Conversation（id, student_id FK, class_id FK, subject, teacher_id, title, created_at, updated_at + (student_id, class_id) 索引）；新增 Message（id, conversation_id FK CASCADE, role, content, sources JSON, created_at + conversation_id 索引），验证三表经 create_all 创建成功
- [x] 1.2 验证 SQLite 未启用外键级联时删除会话需先清空 messages 再删 conversations

## 2. LLM 服务：可配置提示词与流式

- [x] 2.1 llm_service 新增 resolve_system_prompt(config)：自定义提示词或默认 DEFAULT_SYSTEM_PROMPT，tutor_enabled 时固定引导框架替代自定义提示词（「解题引导」只给思路）;原有 SYSTEM_PROMPT 保留为默认别名，generate_answer 兼容旧 ask_ai
- [x] 2.2 新增 build_chat_messages(system_prompt, history, question, context_block)：system + 最近历史轮次 + 当前检索上下文 user 消息
- [x] 2.3 新增 stream_chat(messages)（httpx.AsyncClient stream）：逐行解析 data delta 并 yield；非 2xx/网络错误抛 LLMGenerationError

## 3. 教师配置接口

- [x] 3.1 teacher.py 新增 GET /api/teacher/agent-config?class_id=（校验 class_id ∈ teaching_classes，回读配置或默认空/真）
- [x] 3.2 新增 PUT /api/teacher/agent-config（upsert AgentConfig，写老师编辑人；system_prompt 空则回退默认）
- [x] 3.3 新增 GET /api/teacher/agent-config/default-prompt 返回默认提示词与技能文案供界面预览

## 4. 学生多轮会话接口

- [x] 4.1 student.py 新增 POST /api/student/conversations（建会话，绑定 student_id + class_id，require_student_class_id）
- [x] 4.2 新增 GET /api/student/conversations（当前学生当前班级，按 updated_at 倒序 limit 50）
- [x] 4.3 新增 GET /api/student/conversations/{id}/messages（归属+班级校验，时间正序，assistant 解析 sources）
- [x] 4.4 新增 DELETE /api/student/conversations/{id}（清空 messages 再删会话，非本人 404）

## 5. 学生流式提问接口

- [x] 5.1 新增 POST /api/student/conversations/{id}/chat：校验会话归属/班级；check_ai_limit 复用 AIQuestionLog（超限 429，超限审计仍待补齐）；retrieve_top_k 检索本班本科目上下文与 citations
- [x] 5.2 读取历史最近若干轮、resolve_system_prompt 按该班 AgentConfig 取提示词、build_chat_messages 组装
- [x] 5.3 返回 StreamingResponse：delta/done/error 三种 SSE 事件 JSON；本轮无命中仍用历史调用模型；DeepSeek 失败/无 Key→error 展示检索段落，来源保存到历史
- [x] 5.4 finally 用独立 SessionLocal 写回 assistant 消息（含 sources）并更新 AIQuestionLog.answer、会话 updated_at；remaining = 40 - 当日计数

## 6. 前端 API 层

- [x] 6.1 api.ts 新增 getAgentConfig/saveAgentConfig/getAgentDefaultPrompt、createConversation/listConversations/getConversationMessages/deleteConversation 及对应类型
- [x] 6.2 新增 streamChat(cid, q, cb)：fetch+ReadableStream 解析 SSE，自动刷新 token，onDelta/onDone/onError 分发

## 7. 前端学生端多轮会话

- [x] 7.1 /student?view=assistant 展示「会话列表 + 消息线程」布局；进入助手视图或当前学生变化时重载会话、清空消息（学生首页已独立）
- [x] 7.2 发送时乐观插入 user 消息，流式 delta 追加到当前 assistant 占位，onDone 落盘并刷新会话列表与剩余次数；onError 保留已吐出部分
- [x] 7.3 每条 assistant 消息按 sources 渲染「参考资料」并支持「查看原文」；无 sources 不渲染资料卡

## 8. 前端教师端配置

- [x] 8.1 /teacher?workspace=teaching&view=agent 提供独立「助手配置」主菜单，位于审计上方，页面内选择任教班级并加载配置；提示词 textarea（可填默认/清空）+ 技能开关 + 技能文案预览 + 保存
- [x] 8.2 保存成功后提示"学生端下次提问将使用此提示词与技能设置"

## 9. 部署与集成验证

- [x] 9.1 Nginx /api/ 增设 proxy_http_version 1.1 + proxy_buffering off + proxy_cache off + proxy_set_header Connection ""，保证 SSE 流式
- [x] 9.2 后端 import/建表通过、前端 npm run build 通过
- [x] 9.3 端到端冒烟：学生建会话→流式降级→user+assistant 消息持久化→会话列表→删除会话后读取 404；教师配置端点在被学生 token 访问时 403（班级隔离/越权）

## 10. 2026-10-16 界面边界

- [x] 10.1 教师配置页展示提示词、技能/助手参考资料和 MCP 分区，提示词与 tutor_enabled 仍使用已有接口。
- [x] 10.2 未接入的技能注册与 MCP 添加按钮仅反馈预览提示，不返回真实密钥。
- [x] 10.3 学生问答已移动到独立助手视图，保留原有多轮、SSE、历史与来源能力。
- [ ] 10.4 接入作业批改/错题讲解技能、MCP 服务；指定资料绑定和安全密钥状态接口按后续需求再考虑。
- [x] 10.5 学生学科标签实际切换助手、回读教师配置的技能状态（2026-10-18 已接入，见 subject-teacher-assistants）。

界面与待办的完整契约见 align-teacher-student-workspaces；旧静态“已绑定”已移除，作业/错题预览徽标不作为接口验收依据。

## 2026-10-20 助手参考资料界面简化

- [x] 移除示例密钥、显示按钮及无用样式，后端环境密钥保留。
- [x] 删除静态“已绑定”清单，说明真实班级/科目自动检索范围。
- [x] 提供查看本班单科资料入口，按配置班级更新，空班级提示。

## 2026-10-20 解题引导完善

- [x] 固定引导框架按学习进度回应、概念先解释、每轮最多一问、接受学生公式、逐级提示、完成后结束，保留教师提示词忽略规则。
- [x] 引导短追问结合最近用户题目重新检索，保留班级/科目隔离和每轮真实来源验证；普通模式检索保持。
- [x] 增补纯函数及真实路由隔离检查，涵盖数值/公式、短追问、新话题、无锚点、长题目和原始消息保留。

## 2026-10-20 规约对齐

- [x] 核对当前实现与主规约，更新已实现状态和边界，接入 openspec/README.md 统一索引。
- [x] 本次主规约/变更的官方严格校验与内部链接检查，见 openspec/validation-2026-10-20.md。

- [x] 学生提问快捷历史与后端会话独立，最近 10 条、点击仅回填、当前范围清空；验收见工作空间变更。
- [x] 公式引用提示、数值检索降噪与真实章节辅助排序；验收见 add-rag-search/validation.md。
- [ ] 补齐 429 超限审计（当前仅限额与 429 已实现）。
