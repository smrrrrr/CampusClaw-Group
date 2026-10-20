# 学生助手实现设计（2026-10-20 对齐）

## Context

FastAPI、SQLite、Next.js 与 Nginx 已承载教师配置、学生会话和班级资料检索。当前设计覆盖学科教师配置、多轮引导、来源校验及前端状态隔离；检索算法详情另见 rag-search，快捷历史另见 student-workspace。

## 配置选择与身份

AgentConfig 的 class_id/subject/teacher_id 联合唯一。教师仅能读取及编辑本人当前学科和任教班级配置；数据库任教关系即时校验。resolve_assistant 先筛当前本班本科目教师，新会话使用最近保存的有效配置，无配置则选编号最小的该科教师；无教师时默认助手。会话记录 subject 和 teacher_id，不随其他同科教师保存而自动换绑，绑定任课关系失效返回 409 要求新建。

学生 GET /api/student/assistant-config 仅取得教师显示信息、configured 与 tutor_enabled，不得到私有系统提示词或密钥。会话归属不符/不存在返回 404，属于本人但班级变化返回 403；列表按当前学生/班级/科目过滤。删除先清 messages 再清 conversations，不能依赖未开启的 SQLite 外键级联。

## 提示词与教学规则

resolve_system_prompt 在已保存配置 tutor_enabled=true 时采用 TUTOR_SKILL_PROMPT 和格式/溯源要求，保留但忽略自定义提示词；关闭时使用自定义或 DEFAULT_SYSTEM_PROMPT。无配置行时使用普通默认提示词，界面初始勾选 true 不代表已启用。build_chat_messages 统一追加 CITATION_POLICY，角色提示词不能允许伪造来源。

引导框架先判断进度，概念先解释，必要时每轮最多一个问题；接受数值和公式，卡住逐级帮助，不代做整题。学生已正确完成且理由充分时核对总结，不追加机械追问。模型遵循不是程序保证，有限真实 AI 样例只是评估证据。

## 历史、短追问与检索

生成上下文最多取最近 6 轮/12 条消息；仅在模型输入副本去掉历史 assistant 的数字来源编号，持久化原消息不改。引导模式遇明确短语、数字或简短公式时，followup_retrieval_query 在最近用户历史中寻找独立题目；锚点不超过 2000 字符，过长则不截断拼接，独立新题和普通模式仍使用当前问题。此规则是有限匹配，不是通用对话理解。

检索始终限定本班本科目已索引学生资料，校验文件 SHA。候选片段仅用于本轮上下文，最终 citations 只取正文实际使用的有效编号，摘录来自原始分块；不自动把全部命中或旧历史来源附给回答。定义/公式有本轮直接依据时提示模型标注 [n]，具体代入计算不能伪称讲义原题。细粒度语义证明与自动补旧引用未实现。

## SSE、失败与持久化

POST /api/student/conversations/{id}/chat 复用每日 40 次 AIQuestionLog 额度，返回 delta、done 或 error。delta 尚未完成来源校验；done 含最终 answer/citations/remaining，error 含最终 message/citations/remaining，不保证另发 done。无新片段仍可带历史调用模型；无 Key 或模型完全失败时展示服务器整理的检索段落，部分中断也需核对已有文本来源。消息与实际来源写回 SQLite，旧单次 ai-question 行为独立兼容。

Nginx /api/ 关闭 proxy_buffering/proxy_cache，使用 HTTP/1.1。没有 SSE 断点续传或自动切换成一次性 JSON 的实现。健康检查与 SQLite 故障处理见 runtime-reliability，不能把数据库不可用等同于模型故障。

## 页面与快捷历史

教师独立主菜单助手配置位于审计上方，页面选择班级；提示词编辑框默认 18 行、最小 420px，可纵向拖动。真实提示词/引导保存沿用接口；示例 API Key 与虚构已绑定列表已移除，参考资料说明自动检索并链接本班单科资料。作业/错题开关、技能注册与 MCP 仅预览，不冒称服务端已配置。

学生 URL 保存科目，切换后清旧输入/消息，配置和会话加载完成再允许发送。请求版本号防旧异步结果覆盖新科目，流式生成时禁止切科。提问快捷历史按学生/班级/科目在浏览器保存最近 10 条，点击只回填聚焦；清空不删真实会话。存储拒绝时内存回退，长记录省略显示但回填原文。

## 迁移与后续

配置与会话升级保留旧数学配置、历史消息和账号密码；主规约及 subject-teacher-assistants 记录联合唯一和教师绑定规则。待接入项包括作业批改/错题技能、技能注册、MCP、429 超限审计，以及完整真实学生浏览器端到端验收。部署验证和历史测试见 validation.md，本次文档同步不重跑 AI 或迁移真实数据。
