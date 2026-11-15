# 第10课场景逐条映射（候选）

- 生成时间（UTC）：2026-11-15T16:01:38.963157+00:00
- 主规约 Scenario 总数：**505**

| 判定 | 条数 | 含义 |
| --- | --- | --- |
| 人工复核（确认覆盖） | 185 | 弱候选逐条复核后确认现有断言覆盖，见「人工复核清单」 |
| 人工复核（部分覆盖） | 22 | 现有断言只覆盖一半，备注写明未断言部分，不得计入完全覆盖 |
| 断言名候选（重叠≥6） | 77 | Scenario 与断言名 bigram 高度重合，仍需人工确认强度 |
| 别名候选（关键词表） | 89 | 按标题关键词建立的等价映射 |
| 语义别名候选（人工表） | 106 | 中文 Scenario 与英文/异措辞断言逐条核对后的人工等价 |
| 弱候选（2–5） | 0 | bigram 低重合；本报告要求为 **0**，非 0 即仍有未复核条目 |
| 仅文件级 | 0 | 只能定位到检查文件，未定位断言 |
| N/A（不适用） | 23 | 前端交互/真实模型语义/需容器或外部服务，见第三节理由 |
| 已知缺口 | 3 | 规格条款未被实现完全满足，见「已知缺口」节，不得计入覆盖 |
| 待补断言 | 0 | 同能力有检查文件但无对应断言，**补检查优先队列** |
| 无检查文件 | 0 | 该能力未登记检查文件 |

> 本表只给候选，不等于语义证明。人工复核须逐条确认断言强度、失败路径与边界；「别名候选」与「语义别名候选」都是人工建立的等价映射，同样需要人工确认；「待补断言」「无检查文件」是补检查的优先队列，不能当作已覆盖；「N/A（不适用）」只表示该场景无法用离线门禁断言证明，不表示已验证；「已知缺口」是规格已要求但实现只部分满足的条目，必须单列，不得计入覆盖。

## 按能力统计

| 能力 | 总数 | 人工复核（确认覆盖） | 人工复核（部分覆盖） | 断言名候选 | 别名候选 | 语义别名候选 | 弱候选 | 仅文件级 | N/A（不适用） | 已知缺口 | 待补断言 | 无检查文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| agent-assistant | 47 | 15 | 3 | 4 | 7 | 13 | 0 | 0 | 5 | 0 | 0 | 0 |
| async-homework-grading | 20 | 17 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| class-data-isolation | 34 | 4 | 3 | 12 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| login-and-account-system | 40 | 16 | 2 | 4 | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| material-upload | 39 | 4 | 0 | 10 | 3 | 18 | 0 | 0 | 4 | 0 | 0 | 0 |
| mcp-tool-integration | 31 | 15 | 1 | 2 | 0 | 10 | 0 | 0 | 2 | 1 | 0 | 0 |
| quiz-homework-publication | 28 | 7 | 0 | 14 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| rag-search | 32 | 3 | 0 | 1 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rbac-role-permissions | 56 | 30 | 3 | 11 | 10 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| research-materials | 19 | 3 | 0 | 0 | 0 | 15 | 0 | 0 | 1 | 0 | 0 | 0 |
| runtime-reliability | 6 | 4 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| smart-lesson-prep | 25 | 4 | 0 | 1 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 |
| smart-question-generation | 68 | 42 | 2 | 11 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 |
| student-workspace | 23 | 3 | 0 | 4 | 0 | 6 | 0 | 0 | 10 | 0 | 0 | 0 |
| teacher-identity-and-permissions | 14 | 8 | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| teacher-workspace | 23 | 10 | 2 | 2 | 2 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |

## 已知缺口（规格条款未被实现完全满足）

| 能力 | Scenario | 缺口说明 | 部分证据 |
| --- | --- | --- | --- |
| mcp-tool-integration | 工具说明夹带指令 | 「远端工具说明要求模型先读取其他数据并放进参数」不在现有注入句式表内；检查只证明已知句式（忽略指令/扮演/泄露提示词）说明会被排除，按 mcp-tool-integration Requirement「本期只拦截已知写法」记为已知限制。 | check_mcp_tools：工具说明夹带指令：含指令式说明的工具不进入候选清单并列入排除 |
| rbac-role-permissions | 学生将 AI 解答加入错题本 | 错题本只有列表/详情/掌握/讲解四个接口，没有「加入错题本」写入接口与页面入口 | —（未实现，无部分证据） |
| rbac-role-permissions | 教师查看本班学生 AI 提问历史 | 教师端没有按班级查询 AI 提问历史的接口与页面；学情汇总只有提问数 | —（未实现，无部分证据） |

## 不适用清单（N/A，逐条理由）

| 能力 | Scenario | 不适用理由 |
| --- | --- | --- |
| agent-assistant | 多次卡住与完成 | 需真实模型语义质量抽查，非确定性断言可证 |
| agent-assistant | 学生只回复数字或不会 | 需真实模型语义质量抽查，非确定性断言可证 |
| agent-assistant | 打开教师助手配置 | 前端配置页交互，非接口行为 |
| agent-assistant | 教师预览技能文案 | 前端技能文案预览，属界面展示 |
| agent-assistant | 概念与学生公式作答 | 需真实模型语义质量抽查，非确定性断言可证 |
| async-homework-grading | E2 页面与刷新恢复 | 前端页面刷新恢复，属界面行为 |
| material-upload | 前端仅教师展示删除入口 | 前端入口可见性，属界面展示 |
| material-upload | 多班级教师班级选择器展示所有任教班级 | 前端选择器展示，属界面交互 |
| material-upload | 容器重启后文件不丢失 | 需容器重启，属部署环境验证 |
| material-upload | 网络中断前端提供重试 | 前端重试交互，属界面行为 |
| mcp-tool-integration | 命中工具并用到提示 | 前端提示展示，属界面交互 |
| mcp-tool-integration | 打开 Swagger 试调 | 需以 ENABLE_DOCS=true 启动并用浏览器携带教师令牌试调，属本地接口文档人工验证；默认关闭已由 check_lesson10_scenario_gaps 断言 |
| research-materials | 配图尚未就绪 | 前端配图加载态，属界面展示 |
| student-workspace | 从有资料切到空科目 | 前端科目切换布局，属界面行为 |
| student-workspace | 学生搜索本班讲义 | 前端本地搜索交互，属界面行为 |
| student-workspace | 搜索加载与恢复 | 前端布局稳定性（同一容器与标题区不随是否渲染卡片变化），属界面布局 |
| student-workspace | 无效视图回退 | 前端路由回退，属界面行为 |
| student-workspace | 浏览学习画像演示 | 前端画像展示，属界面展示 |
| student-workspace | 浏览演示作业结果 | 前端演示结果展示，属界面展示 |
| student-workspace | 浏览首页概览 | 前端概览浏览，属界面展示 |
| student-workspace | 由错题进入助手 | 前端跳转交互，属界面行为 |
| student-workspace | 资料页返回其他模块 | 前端导航交互，属界面行为 |
| student-workspace | 首页进入助手对话 | 前端导航交互，属界面行为 |

## 人工复核清单（生成时 bigram 弱候选逐条，结论与证据）

| 能力 | Scenario | 结论 | 检查脚本 | 断言 | 备注 |
| --- | --- | --- | --- | --- | --- |
| agent-assistant | 他人技能不可见 | 确认覆盖 | check_mcp_tools | 同伴删他人技能 404 |  |
| agent-assistant | 保存提示词及解题引导 | 确认覆盖 | check_lessons_2_5 | agent.config_save | config_read 同时校验提示词落库 |
| agent-assistant | 保存绑定 MCP 工具的技能 | 确认覆盖 | check_mcp_tools | 技能保存成功 201 |  |
| agent-assistant | 关闭解题引导技能 | 确认覆盖 | check_lessons_2_5 | agent.custom_prompt_without_tutor | 关闭引导后使用已保存自定义提示词；无配置时回退默认提示词同组 |
| agent-assistant | 命中技能 | 确认覆盖 | check_mcp_tools | meta 含技能名 |  |
| agent-assistant | 在配置页登记并连接 MCP 服务器 | 确认覆盖 | check_mcp_tools | 连接成功 200 | 登记 201 与 connected=true 同文件 |
| agent-assistant | 尚无任教班级 | 确认覆盖 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 |  |
| agent-assistant | 工具事件先于正文 | 确认覆盖 | check_mcp_tools | meta 事件先于 delta |  |
| agent-assistant | 开启解题引导技能 | 确认覆盖 | check_lessons_2_5 | agent.tutor_overrides_custom_prompt |  |
| agent-assistant | 引导求两向量夹角余弦 | 部分覆盖 | check_lessons_2_5 | agent.citations_provenance | 来源编号与原文摘录保留有断言；「具体计算不伪称来自讲义」属模型语义 |
| agent-assistant | 教师配置与班级检索共享隔离 | 部分覆盖 | check_lessons_2_5 | agent.same_subject_teacher_configs_independent | 配置按教师隔离有断言；班级检索共享隔离只由班级过滤间接证明 |
| agent-assistant | 数学与物理配置各自生效 | 确认覆盖 | check_lessons_2_5 | agent.physics_save_does_not_overwrite_math | 同科不同教师配置独立另有 same_subject_teacher_configs_independent |
| agent-assistant | 断开后的引用显示被拒 | 确认覆盖 | check_mcp_tools | 断开后引用记 denied |  |
| agent-assistant | 未命中或技能停用 | 确认覆盖 | check_mcp_tools | 未命中技能不发 meta |  |
| agent-assistant | 留空回退默认提示词 | 确认覆盖 | check_lessons_2_5 | agent.unconfigured_uses_default_prompt |  |
| agent-assistant | 访问他人会话被拒绝 | 确认覆盖 | check_lessons_2_5 | agent.other_student_conversation_hidden | 403/404 均按不存在处理 |
| agent-assistant | 调整预览技能不产生真实批改配置 | 部分覆盖 | check_mcp_tools | meta 含技能名 | 只证明技能影响问答元数据；「不产生批改配置」无直接断言 |
| agent-assistant | 配置非任教班级被拒绝 | 确认覆盖 | check_lessons_2_5 | agent.cross_class_config_denied |  |
| async-homework-grading | A1 正常提交不等待 | 确认覆盖 | check_async_grading | A1 正常：20次202无评分且P95小于200ms假执行，无请求内模型调用 |  |
| async-homework-grading | A2 查询无副作用与空批次 | 确认覆盖 | check_async_grading | A2 正常：GET只读 | 空批次由 A2 边界断言覆盖 |
| async-homework-grading | A3 参数与资源失败 | 确认覆盖 | check_async_grading | A3 失败：非法任务编号422 | 同文件另断言任务不存在 404 与活跃任务重试 409 |
| async-homework-grading | B1 消费者停止再启动 | 确认覆盖 | check_async_grading | B1 正常：队列有消息、消费者未运行时pending |  |
| async-homework-grading | B2 队列故障后补投 | 确认覆盖 | check_async_grading | B2 正常：恢复后补投并可消费 |  |
| async-homework-grading | B3 事务中途失败 | 确认覆盖 | check_async_grading | B3 失败：数据库错误503且不泄露内部信息 | 第二项故障整批回滚同文件断言 |
| async-homework-grading | B4 执行中杀进程与旧租约 | 确认覆盖 | check_async_grading | B4 失败：旧租约不能覆盖 |  |
| async-homework-grading | C1 并发与重复投递 | 确认覆盖 | check_async_grading | C1 边界：20并发数据库唯一幂等 |  |
| async-homework-grading | C2 重交及教师终评竞态 | 确认覆盖 | check_quiz_homework | H/初批期间提交被更新或教师改分：教师终评 | 重交与旧结果跳过同组断言 |
| async-homework-grading | D1 失败退避与死信 | 确认覆盖 | check_async_grading | D1 失败：死信投递失败不假确认 | 退避时间与不写部分分数同组 |
| async-homework-grading | D2 手动重试与合法模型恢复 | 确认覆盖 | check_async_grading | D2 正常：授权手动重试202 |  |
| async-homework-grading | E1 未登录及越权 | 确认覆盖 | check_async_grading | E1 失败： | 模板按未登录/学生/他班/他科展开；403/404 审计同组 |
| async-homework-grading | E3 初批反馈在当前作业卡片可见 | 确认覆盖 | check_grading_feedback | E3 正常：回执位于具有作业编号的卡片内，不在页面顶部 | 回执文案、错误 alert 与换行同文件断言 |
| async-homework-grading | E4 查看提交同步人数 | 确认覆盖 | check_grading_feedback | E4 正常：提交数量更新且不污染其他作业或原数组 | 空列表/未知作业边界同文件断言 |
| async-homework-grading | F1 一键复现和迁移保留 | 部分覆盖 | check_async_grading | F1 边界：重复迁移不改变旧数据 | 迁移与旧库升级有机器断言；README 一键复现未在门禁内实际执行 |
| async-homework-grading | Q1 暂停消费者不积攒副本 | 确认覆盖 | check_async_grading | Q1 边界：确认后跨越30分钟不积攒副本 |  |
| async-homework-grading | Q2 未确认及过期运行恢复 | 确认覆盖 | check_async_grading | Q2 边界：同一过期租约只确认一条恢复消息 |  |
| async-homework-grading | Q3 管理员明确恢复丢失消息 | 确认覆盖 | check_async_grading | Q3 正常：显式恢复只清待执行投递标记 |  |
| async-homework-grading | Q4 界面不把消息数当批改数 | 部分覆盖 | check_grading_feedback | E4 正常：提交数量更新且不污染其他作业或原数组 | 前端只同步提交数；队列消息数与批改数的后端分离无单独断言 |
| class-data-isolation | Windows Docker 共享目录读写 | 部分覆盖 | check_sqlite_storage | {mode} journal active | DELETE 模式并发提交、持久化与完整性已断言；未在真实 Windows 共享目录运行 |
| class-data-isolation | 学生查看本班资料成功 | 确认覆盖 | check_lessons_2_5 | materials.download | 列表/预览/下载同文件断言 |
| class-data-isolation | 学生资料请求使用本人班级 | 部分覆盖 | check_lesson10_review | 学生资料请求使用本人班级：学生端固定取本人 class_id，不提供跨班切换 | 前端源码断言 + 后端 materials.student_subject_scope_denied 拒绝跨班；未跑浏览器 |
| class-data-isolation | 教师查看任教班级资料成功 | 确认覆盖 | check_lessons_2_5 | materials.all_subject_list_preserved | 任教范围内跨班可见；越界由 subject_list_cross_class_denied 反证 |
| class-data-isolation | 数据库暂不可用 | 确认覆盖 | check_baseline | R1 失败：数据库异常 → 503 与通用提示 |  |
| class-data-isolation | 用户账号基础信息不隔离 | 部分覆盖 | check_lesson10_review | 用户账号基础信息不隔离：不同班级学生均能读取本人姓名与班级 | 登录/刷新返回本人姓名与班级；接口未返回学号字段 |
| class-data-isolation | 篡改 URL 参数跨班访问被拦截 | 确认覆盖 | check_lessons_2_5 | materials.cross_class_list_denied | URL 参数跨班返回 403；审计由全局 403 记录断言 |
| login-and-account-system | Access Token 过期自动刷新 | 部分覆盖 | check_lesson10_review | Access Token 过期自动刷新：前端 401 后调用 refresh 并重试原请求 | 后端 refresh 由 auth.refresh 断言；自动重试为源码断言，未跑浏览器 |
| login-and-account-system | CSV 缺少学号列被拒绝 | 确认覆盖 | check_lesson10_review | CSV 缺少学号列被拒绝：400 且不创建账号 |  |
| login-and-account-system | JWT Payload 包含必要字段 | 确认覆盖 | check_lesson10_review | JWT Payload 包含必要字段：教师令牌含七个声明 | 学生令牌不带教师身份同组断言 |
| login-and-account-system | Refresh Token 过期需重新登录 | 确认覆盖 | check_lesson10_review | Refresh Token 过期需重新登录：过期刷新令牌返回 401 |  |
| login-and-account-system | 修改非任教班级学生被拒绝 | 确认覆盖 | check_lessons_2_5 | auth.csv_other_class_update_denied |  |
| login-and-account-system | 刷新失败回登录 | 确认覆盖 | check_route_guard | 身份恢复前不显示业务内容：缺少 | 缺 accessToken/身份提示时拒绝显示业务页 |
| login-and-account-system | 密码错误登录失败 | 确认覆盖 | check_lesson10_review | 密码错误与账号不存在返回同一提示 | 均为 401 且文案相同 |
| login-and-account-system | 导入非任教目标班级被拒绝 | 确认覆盖 | check_lessons_2_5 | auth.csv_other_class_create_denied |  |
| login-and-account-system | 改密成功后恢复正常访问 | 确认覆盖 | check_lessons_2_5 | auth.change_password |  |
| login-and-account-system | 教师刷新后保留页面 | 部分覆盖 | check_lessons_2_5 | auth.refresh_restores_full_user | 完整身份恢复有断言；URL 与菜单保留属浏览器行为 |
| login-and-account-system | 教师种子维护身份而不覆盖已改密码 | 确认覆盖 | check_lesson10_review | 教师种子维护身份而不覆盖已改密码：重跑保留自定义口令并更新学科 |  |
| login-and-account-system | 教师通过 CSV 批量导入学生含手机号 | 确认覆盖 | check_lesson10_review | CSV 导入手机号：phone 字段落库 |  |
| login-and-account-system | 未改密时访问业务接口被拦截 | 确认覆盖 | check_lessons_2_5 | auth.first_password_blocks_business | 会话/历史接口另两项同组断言 |
| login-and-account-system | 未登录用户无法注册 | 确认覆盖 | check_lesson10_review | 未登录用户无法注册：注册接口不存在且登录页无注册入口 |  |
| login-and-account-system | 登出清除所有 Token 和状态 | 确认覆盖 | check_lesson10_review | 登出清除所有 Token 和状态：前端清本地状态并跳转登录，后端清 Cookie |  |
| login-and-account-system | 账号不存在登录失败 | 确认覆盖 | check_lesson10_review | 密码错误与账号不存在返回同一提示 | 与密码错误逐字相同 |
| login-and-account-system | 预置教师账号携带学科与班主任身份 | 确认覆盖 | check_lesson10_review | 开发种子：教师学科与班主任身份写入 |  |
| login-and-account-system | 首次密码登录被拦截要求改密 | 确认覆盖 | check_lessons_2_5 | auth.first_password_blocks_business |  |
| material-upload | SQLite 仅存储元数据 | 确认覆盖 | check_lesson10_review | SQLite 仅存储元数据：Material 表无二进制列 |  |
| material-upload | 前端 accept 属性初步限制 | 确认覆盖 | check_lesson10_review | 前端 accept 属性初步限制：ACCEPT 仅含允许格式且绑定文件输入 |  |
| material-upload | 学生尝试删除资料被拒 | 确认覆盖 | check_lesson10_review | 学生尝试删除资料被拒：学生调用删除接口 403 且资料保留 |  |
| material-upload | 教师删除任教班级资料成功 | 确认覆盖 | check_lessons_2_5 | materials.delete | MaterialContent/Chunk 清理同文件断言 |
| mcp-tool-integration | 令牌错误时连接失败 | 确认覆盖 | check_mcp_tools | 连接失败 502 |  |
| mcp-tool-integration | 决策轮用量可追溯 | 确认覆盖 | check_security_gate | P1-2 决策轮用量： | 合法/缺失/非法三类用量逐项断言 |
| mcp-tool-integration | 发现重连未知权限默认拒绝 | 确认覆盖 | check_security_gate | P0-5 正常/边界：真实发现分类保守且不信远端只读声明 | 未知工具默认可写不等于可执行；重连不降级由分类断言覆盖 |
| mcp-tool-integration | 同伴访问我的服务器 | 确认覆盖 | check_mcp_tools | 同伴读取他人服务器 404 |  |
| mcp-tool-integration | 同名再登记 | 确认覆盖 | check_mcp_tools | 同名再登记 400 |  |
| mcp-tool-integration | 学生写入拒绝且 SSE 完整 | 部分覆盖 | check_mcp_tools | 学生身份不能执行可写工具（不采信角色声明） | 拒绝与零执行有断言；SSE meta+done 完整性由同文件首帧与结束帧断言覆盖 |
| mcp-tool-integration | 学生调用管理接口 | 确认覆盖 | check_mcp_tools | 学生访问管理接口 403 |  |
| mcp-tool-integration | 审计存储失败可观察 | 确认覆盖 | check_security_gate | 审计故障：告警可见且不泄露异常原文 | 工具存储回滚且不中断同组 |
| mcp-tool-integration | 工具不在清单或服务器未连接 | 确认覆盖 | check_mcp_tools | 候选集外工具 denied、不执行、不写审计 |  |
| mcp-tool-integration | 工具超时 | 确认覆盖 | check_mcp_tools | 工具超时：本次调用记 error 且原因写明失败 |  |
| mcp-tool-integration | 带令牌发现并调用工具 | 确认覆盖 | check_mcp_tools | 确实带令牌调用了工具 | meta.tool_calls 记录 ok 同组 |
| mcp-tool-integration | 打开 Swagger 试调 | N/A |  | 需以 ENABLE_DOCS=true 启动并用浏览器携带教师令牌试调，属本地接口文档人工验证；默认关闭已由 check_lesson10_scenario_gaps 断言 |  |
| mcp-tool-integration | 断开后不可调用 | 确认覆盖 | check_mcp_tools | 断开后引用记 denied |  |
| mcp-tool-integration | 登记后响应不含令牌 | 确认覆盖 | check_mcp_tools | 响应不含令牌 |  |
| mcp-tool-integration | 连接自建服务发现工具 | 确认覆盖 | check_mcp_tools | 连接成功 200 | 工具清单不翻倍由「重复连接工具不翻倍」证明 |
| mcp-tool-integration | 非法请求可读 | 确认覆盖 | check_mcp_server | 非法请求可读： | 8 类非法请求逐项返回 JSON-RPC 错误码与中文说明 |
| mcp-tool-integration | 默认关闭文档 | 确认覆盖 | check_lesson10_scenario_gaps | 默认关闭文档：代码默认值为关闭，/docs 与 /openapi.json 随之不暴露 |  |
| quiz-homework-publication | M4 越权或事务失败不部分改分 | 确认覆盖 | check_quiz_homework | H/初批失败仍可人工改分： | 越权改分 403 与拒绝访问审计同组；失败批次无部分写入 |
| quiz-homework-publication | 保留手工布置 | 确认覆盖 | check_quiz_homework | H/保留手工布置：草稿不可见 | 两种作业同时展示同文件断言 |
| quiz-homework-publication | 分数折算边界 | 确认覆盖 | check_quiz_homework | H/分数折算边界： | 合法/越界逐项断言 |
| quiz-homework-publication | 提交命题作业 | 确认覆盖 | check_quiz_homework | H/提交命题作业 |  |
| quiz-homework-publication | 迁移重复执行 | 确认覆盖 | check_quiz_homework | H/迁移重复执行 |  |
| quiz-homework-publication | 配图异常 | 确认覆盖 | check_quiz_homework | H/配图异常：非法名 | 点路径、未知名与指纹变化同组 |
| quiz-homework-publication | 题面显示一致 | 确认覆盖 | check_quiz_homework | H/题面显示一致 | 含第 10/12 题与填空空位 |
| rag-search | 坐标题检索夹角余弦公式 | 确认覆盖 | check_formula_retrieval | {mode} formula recalled despite coordinate distractor | 原文摘录不变与来源指纹精确同文件 |
| rag-search | 支持 Markdown 列表与加粗 | 确认覆盖 | check_lesson10_review | 支持 Markdown 列表与加粗：解析保留列表与加粗原文 |  |
| rag-search | 解析成功但向量化失败保持未索引 | 确认覆盖 | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 |  |
| rbac-role-permissions | 不同学生账号次数独立计算 | 确认覆盖 | check_lesson10_review | 不同学生账号次数独立计算：两名学生各自计数互不影响 |  |
| rbac-role-permissions | 任课教师不能重置学生密码 | 部分覆盖 | check_lessons_2_5 | auth.subject_teacher_reset_denied | 拒绝成立，实际返回 404（隐藏资源存在性），规约写 403 |
| rbac-role-permissions | 后端越权返回 403 并记录审计日志 | 确认覆盖 | check_baseline | R2 失败：403 访问日志 status=403 且标识一致 | 响应 403 与审计字段同文件 |
| rbac-role-permissions | 多班级选择器展示所有任教班级 | 确认覆盖 | check_teacher_navigation | 多班级选择器展示所有任教班级：选择器值来自任教班级列表 | 接口返回全部任教班级另由 check_lesson10_review 断言 |
| rbac-role-permissions | 学生不能越权查看其他学生数据 | 确认覆盖 | check_mistake | S4 正常：请求参数 student_id 被忽略，仍只返回本人错题 |  |
| rbac-role-permissions | 学生仅以学号密码登录 | 确认覆盖 | check_lessons_2_5 | auth.login.S1 |  |
| rbac-role-permissions | 学生发起 AI 提问并查看历史 | 确认覆盖 | check_lesson10_review | 学生发起 AI 提问并查看历史：提问落库且历史仅本人可见 |  |
| rbac-role-permissions | 学生将 AI 解答加入错题本 | 已知缺口 |  |  | 错题本只有列表/详情/掌握/讲解四个接口，没有「加入错题本」写入接口与页面入口 |
| rbac-role-permissions | 学生尝试查询他人数据被拒 | 确认覆盖 | check_mistake | S4 正常：请求参数 student_id 被忽略，仍只返回本人错题 |  |
| rbac-role-permissions | 学生查看个人错题本 | 确认覆盖 | check_mistake | S1 正常：本人错题列表返回 2 条 |  |
| rbac-role-permissions | 学生查询自己数据成功 | 确认覆盖 | check_mistake | S1 正常：本人错题列表返回 2 条 |  |
| rbac-role-permissions | 学生访问学生路由通过 | 确认覆盖 | check_route_guard | 本角色页面正常渲染：student → /student |  |
| rbac-role-permissions | 学生访问教师路由被拦截 | 确认覆盖 | check_route_guard | 伪造角色提示不赋予页面权限：student → /teacher |  |
| rbac-role-permissions | 学生调用学生接口通过 | 确认覆盖 | check_homework | S3 正常：学生提交成功 |  |
| rbac-role-permissions | 审计日志异步写入不影响响应性能 | 确认覆盖 | check_security_gate | R2 审计异步：401响应正文发出后再写入 |  |
| rbac-role-permissions | 教师上传资料并布置作业 | 部分覆盖 | check_homework | S1 正常：教师创建草稿作业 200 | 布置有断言；上传由 materials.upload_md 另行断言，同一教师链路 |
| rbac-role-permissions | 教师不能代替学生发起 AI 提问 | 部分覆盖 | check_lesson10_review | 教师不能代替学生发起 AI 提问：教师调用学生提问接口 403 | 拒绝成立；提示文案为「仅学生可执行该操作」，规约写「AI 提问仅限学生发起」 |
| rbac-role-permissions | 教师不能查看非任教班级的学生数据 | 确认覆盖 | check_analytics | S3 失败：教师跨班访问 → 403 |  |
| rbac-role-permissions | 教师仅能访问本学科教研资料 | 确认覆盖 | check_research_materials | cross subject read denied |  |
| rbac-role-permissions | 教师学科身份登录后进入教研组 | 确认覆盖 | check_research_materials | same subject colleagues share source |  |
| rbac-role-permissions | 教师批改作业并查看本班学生数据 | 确认覆盖 | check_quiz_homework | H/教师直接评分并联动错题学情 | 学情计数由 check_analytics S1/U1 交叉断言 |
| rbac-role-permissions | 教师查看本班学生 AI 提问历史 | 已知缺口 |  |  | 教师端没有按班级查询 AI 提问历史的接口与页面；学情汇总只有提问数 |
| rbac-role-permissions | 教师查询任教班级数据成功 | 确认覆盖 | check_analytics | S4 正常：任教范围内班级可查 |  |
| rbac-role-permissions | 教师查询非任教班级数据被拒 | 确认覆盖 | check_analytics | S3 失败：教师跨班访问 → 403 |  |
| rbac-role-permissions | 教师管理自己任教的班级 | 确认覆盖 | check_analytics | S4 正常：任教范围内班级可查 |  |
| rbac-role-permissions | 教师访问学生路由被拦截 | 确认覆盖 | check_route_guard | 伪造角色提示不赋予页面权限：teacher → /student |  |
| rbac-role-permissions | 教师访问教师路由通过 | 确认覆盖 | check_route_guard | 本角色页面正常渲染：teacher → /teacher |  |
| rbac-role-permissions | 教师调用教师接口通过 | 确认覆盖 | check_lessons_2_5 | materials.upload_md |  |
| rbac-role-permissions | 教师跨班操作被拒 | 确认覆盖 | check_lessons_2_5 | materials.cross_class_upload_denied |  |
| rbac-role-permissions | 教师选择任教班级操作成功 | 确认覆盖 | check_lessons_2_5 | materials.upload_md |  |
| rbac-role-permissions | 教师选择非任教班级操作被拒 | 确认覆盖 | check_lessons_2_5 | materials.cross_class_upload_denied |  |
| rbac-role-permissions | 教师重置本班学生密码 | 确认覆盖 | check_lessons_2_5 | auth.homeroom_reset |  |
| rbac-role-permissions | 未刷新前旧权限仍有效 | 确认覆盖 | check_lesson10_review | 未刷新前旧权限仍有效：旧令牌按旧任教班级校验，重新登录后生效 |  |
| rbac-role-permissions | 未登录用户访问业务路由重定向登录 | 确认覆盖 | check_route_guard | 身份恢复前不显示业务内容：缺少 | 缺 accessToken/身份提示时拒绝进入业务页 |
| rbac-role-permissions | 未登录请求留匿名审计 | 确认覆盖 | check_lesson10_review | 未登录请求留匿名审计：401 落库 user_id 为空且 action 可识别 |  |
| research-materials | 图片没有随 Markdown 导入 | 确认覆盖 | check_research_materials | invalid import bad.md | 缺图 Markdown 返回 400 且不落库 |
| research-materials | 完整教师 Markdown 误传班级 | 确认覆盖 | check_research_materials | legacy class upload rejects teacher answer content | 教师版文件名同样被拒，同文件断言 |
| research-materials | 立体几何章节带知识点标签 | 确认覆盖 | check_research_materials | geometry chapter creates knowledge topic |  |
| runtime-reliability | Windows 共享目录运行小组服务 | 部分覆盖 | check_sqlite_storage | {mode} journal active | DELETE 模式并发提交/持久化/完整性已断言；未在真实 Windows 共享目录运行 |
| runtime-reliability | 使用原生磁盘的 WAL 配置 | 确认覆盖 | check_sqlite_storage | {mode} journal active | WAL 同步级别、并行提交与完整性同文件断言 |
| runtime-reliability | 数据库存储异常 | 确认覆盖 | check_baseline | R1 失败：数据库异常 → 503 与通用提示 |  |
| runtime-reliability | 数据库读取正常 | 确认覆盖 | check_baseline | R1 正常：三项依赖为 ok/ok/configured | 健康检查不写业务记录同文件 |
| runtime-reliability | 无效日志模式 | 确认覆盖 | check_sqlite_storage | unsafe journal rejected |  |
| smart-lesson-prep | 学生稿含漏网控制字符 | 确认覆盖 | check_lesson_prep | 学生稿含 U+000C：返回 error | 旧稿保持不变与手工编辑同样拒绝同组 |
| smart-lesson-prep | 教师生成并修改学生讲义 | 确认覆盖 | check_lesson_prep | edit saved and remains draft | 学生稿生成/保存同文件 |
| smart-lesson-prep | 数学教师发起线面角备课 | 确认覆盖 | check_lesson_prep | teacher draft saved with actual stream | 出处摘录与行号可追溯同文件 |
| smart-lesson-prep | 新修订尝试发布旧学生稿 | 确认覆盖 | check_lesson_prep | new final cannot publish old student drafts |  |
| smart-question-generation | 下架后组卷 | 确认覆盖 | check_lesson10_scenario_gaps | 下架后组卷：下架题不进入新试卷且返回缺口、不创建试卷 |  |
| smart-question-generation | 作业发布审计 | 确认覆盖 | check_quiz_homework | Q/作业发布审计 |  |
| smart-question-generation | 使用词表外的知识点 | 确认覆盖 | check_question_bank | 词表外知识点 400 |  |
| smart-question-generation | 修改入库题目 | 确认覆盖 | check_question_bank | 入库题目修改 409 |  |
| smart-question-generation | 修改后通过 | 确认覆盖 | check_question_bank | 补齐括号后保存并通过：进入题库且标记已修改 |  |
| smart-question-generation | 修补后仍不是合法 JSON | 确认覆盖 | check_question_bank | 截断输出：失败原因含第 12 行与列号 | 不含模型原文同组 |
| smart-question-generation | 全部题目通过校验 | 确认覆盖 | check_question_bank | 全部通过 8 题落库 |  |
| smart-question-generation | 原图校验或文件写入失败 | 确认覆盖 | check_quiz_homework | Q/原图校验或文件写入失败：数据库整批回滚 | 文件整批回滚与指纹 409 同组 |
| smart-question-generation | 原稿在入库后被替换 | 确认覆盖 | check_lesson10_review | 原稿在入库后被替换：指纹变化标记 changed、缺失标记 deleted |  |
| smart-question-generation | 发布到两个任教班级 | 确认覆盖 | check_question_bank | 发布到两个班 200 |  |
| smart-question-generation | 同一教师重复点击生成 | 确认覆盖 | check_question_bank | 登记未过期：再次生成 409 |  |
| smart-question-generation | 同科同事浏览题库 | 确认覆盖 | check_question_bank | 同科同事可见题库 |  |
| smart-question-generation | 填空与解答题答案含公式 | 确认覆盖 | check_question_rendering | 填空与解答题答案含公式：答案以 KaTeX 渲染且无 katex-error |  |
| smart-question-generation | 多空位填空题显示 | 确认覆盖 | check_question_rendering | 多空位填空题显示：三个空位保留且无加粗斜体 |  |
| smart-question-generation | 多空答案与选择判断答案 | 确认覆盖 | check_question_bank | 答案卷含答案与解析 |  |
| smart-question-generation | 学生端打开已发布试卷 | 部分覆盖 | check_question_rendering | 学生端打开已发布试卷：多空位题干渲染后空位与发布时一致 | 交作业与历史资料两种入口未逐一走浏览器，共用同一渲染组件 |
| smart-question-generation | 学生端打开新发布的试卷 | 确认覆盖 | check_question_bank | 学生卷选择题：A–D 每项一行且行尾硬换行 | 不含答案/解析/S 编号同组 |
| smart-question-generation | 学生调用命题接口 | 确认覆盖 | check_question_bank | 学生访问题库 403 |  |
| smart-question-generation | 定界符不成对 | 确认覆盖 | check_question_bank | 公式结构：转义、cases 与定界符正反用例 |  |
| smart-question-generation | 已发布资料不被改写 | 确认覆盖 | check_quiz_homework | Q/已发布资料不被改写 |  |
| smart-question-generation | 按 3:5:2 组卷 | 确认覆盖 | check_question_bank | 组卷 13 题 | 总分 80 同组断言 |
| smart-question-generation | 数学教师按配比发起命题 | 确认覆盖 | check_question_bank | 全部通过 8 题落库 | 按数学学科组织上下文 |
| smart-question-generation | 无 Key 环境运行验收脚本 | 部分覆盖 | check_question_bank | 无 Key 环境运行验收脚本：虚构模型完成生成且无外部模型请求 | 脚本以占位 test-key 启动并替换 stream_chat；未验证完全不设置环境变量的路径 |
| smart-question-generation | 未确认即通过 | 确认覆盖 | check_question_bank | 未确认即通过 400 |  |
| smart-question-generation | 未确认核对或版本冲突 | 确认覆盖 | check_question_bank | 未确认核对 400 |  |
| smart-question-generation | 未配置模型 Key | 确认覆盖 | check_question_bank | 无 Key 返回 503 |  |
| smart-question-generation | 查看题目出处 | 确认覆盖 | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | S 编号与资料名同组 |
| smart-question-generation | 模型返回字面包含所选标签的表述 | 确认覆盖 | check_question_bank | 细分知识点：落库知识点为所选标签 |  |
| smart-question-generation | 漏网的控制字符被拦截 | 确认覆盖 | check_question_bank | U+000C 题干：原因为含不可见控制字符 |  |
| smart-question-generation | 物理教师读取数学题目 | 确认覆盖 | check_question_bank | 跨学科读取题目 404 |  |
| smart-question-generation | 第 10 题以后 | 确认覆盖 | check_quiz_homework | H/题面显示一致 | 学生卷 10.–12. 选项仍在题下 |
| smart-question-generation | 编辑答案时显示原文 | 确认覆盖 | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | 出处快照与编辑原文一致 |
| smart-question-generation | 草稿试卷发布 | 确认覆盖 | check_question_bank | 草稿发布 409 |  |
| smart-question-generation | 被误解码的公式命令被修补 | 确认覆盖 | check_question_bank | 单反斜杠 LaTeX：generate 事件记录 escape_repairs=13 |  |
| smart-question-generation | 解答题作答横线不变 | 确认覆盖 | check_question_rendering | 解答题作答横线不变：整行下划线渲染为分隔线而非文字 |  |
| smart-question-generation | 输出不是 JSON | 确认覆盖 | check_question_bank | 非 JSON 返回 error | 不保存题目与写失败记录同组 |
| smart-question-generation | 选用他科资料 | 确认覆盖 | check_question_bank | 选用他科资料 404 |  |
| smart-question-generation | 部分题目不合格 | 确认覆盖 | check_question_bank | 部分不合格：6 通过 2 未通过 |  |
| smart-question-generation | 配比不一致或越界 | 确认覆盖 | check_question_bank | 题型/难度合计不等 400 | 另断言总题数 0/21 与单题型 11 |
| smart-question-generation | 重复发布 | 确认覆盖 | check_question_bank | 重复发布复用作业 |  |
| smart-question-generation | 重复发布更换截止时间或遇到已关闭作业 | 确认覆盖 | check_quiz_homework | Q/重复发布更换截止时间或遇到已关闭作业：截止时间冲突 | 已关闭 409 同组 |
| smart-question-generation | 重复题目 | 确认覆盖 | check_question_bank | 重复题干通过 409 |  |
| smart-question-generation | 题库不足 | 确认覆盖 | check_question_bank | 题库不足 422 并列出缺口 |  |
| smart-question-generation | 驳回后尝试通过 | 确认覆盖 | check_question_bank | 驳回后通过 409 |  |
| student-workspace | H2 关闭后保留终评及配图 | 确认覆盖 | check_assignment_history | H2 正常：关闭后保留100分作答与评语 | 配图可读与不可重交同组 |
| student-workspace | 学生首页展示本人班级 | 确认覆盖 | check_lesson10_review | 学生首页展示本人班级：班级名取自本人会话且无班级选择器 |  |
| student-workspace | 未分班学生访问 | 确认覆盖 | check_lesson10_review | 未分班学生访问：空状态且不请求班级资料 | 后端 agent.unassigned_student_denied 另行断言 |
| teacher-identity-and-permissions | 任课教学保留班主任模块 | 确认覆盖 | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 |  |
| teacher-identity-and-permissions | 任课教师调用重置接口被拒 | 部分覆盖 | check_lessons_2_5 | auth.subject_teacher_reset_denied | 拒绝成立，实际 404 而非规约写的 403 |
| teacher-identity-and-permissions | 任课老师仅看本学科成绩 | 确认覆盖 | check_analytics | S1 正常：任课查看 102 数学学情 |  |
| teacher-identity-and-permissions | 任课老师仅见任教班级名单 | 部分覆盖 | check_lessons_2_5 | auth.teacher_cross_class_denied | 越界 403 有断言；名单只含任教班级的完整集合未单独断言 |
| teacher-identity-and-permissions | 教师学科身份随 JWT 生效 | 部分覆盖 | check_lessons_2_5 | agent.teacher_subject_uses_current_database | subject 实际取数据库当前值并覆盖令牌；请求体不声明学科时按服务端身份判定的行为成立 |
| teacher-identity-and-permissions | 教师登录进入本学科教研组 | 确认覆盖 | check_research_materials | same subject colleagues share source |  |
| teacher-identity-and-permissions | 数学教师访问数学教研资料成功 | 确认覆盖 | check_research_materials | same subject colleagues share source |  |
| teacher-identity-and-permissions | 数学班主任跨学科访问英语资料被拒 | 确认覆盖 | check_research_materials | cross subject read denied |  |
| teacher-identity-and-permissions | 班主任可见本班全部学生 | 确认覆盖 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | total_students 计数 |
| teacher-identity-and-permissions | 班主任查看其他班级学情被拒 | 确认覆盖 | check_analytics | S3 失败：教师跨班访问 → 403 |  |
| teacher-identity-and-permissions | 跨学科教研资料不可见 | 确认覆盖 | check_research_materials | other subject sees no source |  |
| teacher-workspace | R1 教研中心只有三个现有入口 | 确认覆盖 | check_teacher_navigation | R1 正常： | 六条路由 × 有/无带班逐项断言 |
| teacher-workspace | R3 其他导航与班级不退化 | 确认覆盖 | check_teacher_navigation | R3 边界：其他view保持原值 |  |
| teacher-workspace | 任课教学保留班主任入口 | 确认覆盖 | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 |  |
| teacher-workspace | 切换任课班级不切换带班班级 | 确认覆盖 | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 | 同一断言验证任课 102 与带班 101 并存 |
| teacher-workspace | 切班后保留资料视图 | 确认覆盖 | check_teacher_navigation | R3 正常：切班保留现有页面行为 |  |
| teacher-workspace | 同一教师在任课页不展示重置操作 | 确认覆盖 | check_lesson10_review | 同一教师在任课页不展示重置操作：操作列与按钮均受班主任身份控制 |  |
| teacher-workspace | 在助手配置页切换班级 | 部分覆盖 | check_lessons_2_5 | agent.class_switch_reads_and_saves_target | 切到 102 后读取/保存以 102 为目标且不影响 101 有断言；「保留配置视图」属前端行为 |
| teacher-workspace | 教师打开资料页仍可访问其他模块 | 确认覆盖 | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 | 共用导航在 /teacher/library、/upload、/materials 均断言 |
| teacher-workspace | 智能命题不再是占位 | 确认覆盖 | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 | 命题入口指向 /teacher/quiz |
| teacher-workspace | 查看当前任教班级本科目资料 | 确认覆盖 | check_lessons_2_5 | materials.math_subject_list | 单科列表按 subject_only=true 断言 |
| teacher-workspace | 班主任进入全科资料总览 | 部分覆盖 | check_teacher_navigation | R1 正常： | 班主任工作台含「本班资料（全科）」入口；「总览不提供上传/删除」无直接断言 |
| teacher-workspace | 非班主任只显示任课与教研功能 | 确认覆盖 | check_teacher_navigation | 非班主任只显示任课与教研功能：无班主任工作台，保留任课/教研/助手配置 |  |

## 需要补检查的场景（待补断言 / 无检查文件，按高风险能力优先）

| 优先级 | 类别 | 能力 | Requirement | Scenario | 判定 |
| --- | --- | --- | --- | --- | --- |

## 逐条候选

| 能力 | Requirement | Scenario | 判定 | 候选检查 | 候选断言 / N/A 理由 | 复核备注 | 重叠 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-assistant | SSE 流式回答 | DeepSeek 失败时降级为检索段落 | 别名候选 | check_lessons_2_5 | agent.failure_fallback |  | 2 |
| agent-assistant | SSE 流式回答 | 多轮会话检索无命中时延续历史 | 语义别名候选 | check_lessons_2_5 | agent.followup_retrieves_original_topic_with_same_scope |  | 1 |
| agent-assistant | SSE 流式回答 | 多轮调用只推送一次 meta | 断言名候选 | check_mcp_tools | 两轮调用只推送一次 meta 且为首帧 |  | 11 |
| agent-assistant | SSE 流式回答 | 工具事件先于正文 | 人工复核（确认覆盖） | check_mcp_tools | meta 事件先于 delta |  | 0 |
| agent-assistant | SSE 流式回答 | 断开后的引用显示被拒 | 人工复核（确认覆盖） | check_mcp_tools | 断开后引用记 denied |  | 0 |
| agent-assistant | SSE 流式回答 | 流式结束写回会话 | 别名候选 | check_lessons_2_5 | agent.sse_transport_mock_llm |  | 1 |
| agent-assistant | SSE 流式回答 | 流式逐字输出 | 别名候选 | check_lessons_2_5 | agent.sse_transport_mock_llm |  | 1 |
| agent-assistant | 「解题引导」技能开关 | 关闭解题引导技能 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.custom_prompt_without_tutor | 关闭引导后使用已保存自定义提示词；无配置时回退默认提示词同组 | 0 |
| agent-assistant | 「解题引导」技能开关 | 开启解题引导技能 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.tutor_overrides_custom_prompt |  | 0 |
| agent-assistant | 「解题引导」技能开关 | 教师预览技能文案 | N/A（不适用） |  | 前端技能文案预览，属界面展示 |  | 0 |
| agent-assistant | 使用已有公式依据时标注引用 | 历史未标注来源的回答 | 语义别名候选 | check_lessons_2_5 | citations.no_context_cannot_cite_history |  | 1 |
| agent-assistant | 使用已有公式依据时标注引用 | 引导求两向量夹角余弦 | 人工复核（部分覆盖） | check_lessons_2_5 | agent.citations_provenance | 来源编号与原文摘录保留有断言；「具体计算不伪称来自讲义」属模型语义 | 0 |
| agent-assistant | 兼容既有约束 | 教师配置与班级检索共享隔离 | 人工复核（部分覆盖） | check_lessons_2_5 | agent.same_subject_teacher_configs_independent | 配置按教师隔离有断言；班级检索共享隔离只由班级过滤间接证明 | 0 |
| agent-assistant | 兼容既有约束 | 未分配班级学生被拒 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied |  | 2 |
| agent-assistant | 兼容既有约束 | 追问计入每日限次 | 别名候选 | check_lessons_2_5 | agent.spec_40_question_limit |  | 2 |
| agent-assistant | 删除会话 | 删除会话并清理消息 | 断言名候选 | check_lesson10_scenario_gaps | 删除会话并清理消息：会话与其全部消息一并删除 |  | 8 |
| agent-assistant | 助手技能与 MCP 配置界面 | 以技能文件注册技能 | 语义别名候选 | check_mcp_tools | 技能保存成功 201 |  | 1 |
| agent-assistant | 助手技能与 MCP 配置界面 | 在配置页登记并连接 MCP 服务器 | 人工复核（确认覆盖） | check_mcp_tools | 连接成功 200 | 登记 201 与 connected=true 同文件 | 0 |
| agent-assistant | 助手技能与 MCP 配置界面 | 打开教师助手配置 | N/A（不适用） |  | 前端配置页交互，非接口行为 |  | 0 |
| agent-assistant | 助手技能与 MCP 配置界面 | 调整预览技能不产生真实批改配置 | 人工复核（部分覆盖） | check_mcp_tools | meta 含技能名 | 只证明技能影响问答元数据；「不产生批改配置」无直接断言 | 0 |
| agent-assistant | 多轮会话与上下文延续 | 在会话内连续追问 | 语义别名候选 | check_lessons_2_5 | agent.multiturn_context |  | 1 |
| agent-assistant | 多轮会话与上下文延续 | 新建与列出会话 | 语义别名候选 | check_mcp_tools | 学生建会话 |  | 1 |
| agent-assistant | 多轮会话与上下文延续 | 访问他人会话被拒绝 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.other_student_conversation_hidden | 403/404 均按不存在处理 | 0 |
| agent-assistant | 学生按科目切换教师助手 | 切换科目时隔离异步状态 | 别名候选 | check_lessons_2_5 | agent.physics_save_does_not_overwrite_math |  | 1 |
| agent-assistant | 学生按科目切换教师助手 | 同科教师不覆盖彼此配置 | 别名候选 | check_lessons_2_5 | agent.same_subject_teacher_configs_independent |  | 3 |
| agent-assistant | 学生按科目切换教师助手 | 数学与物理配置各自生效 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.physics_save_does_not_overwrite_math | 同科不同教师配置独立另有 same_subject_teacher_configs_independent | 0 |
| agent-assistant | 学生按科目切换教师助手 | 没有该科配置 | 语义别名候选 | check_lessons_2_5 | agent.unconfigured_subject_reports_default |  | 1 |
| agent-assistant | 学生提问的技能路由 | 命中技能 | 人工复核（确认覆盖） | check_mcp_tools | meta 含技能名 |  | 0 |
| agent-assistant | 学生提问的技能路由 | 未命中或技能停用 | 人工复核（确认覆盖） | check_mcp_tools | 未命中技能不发 meta |  | 0 |
| agent-assistant | 引导短追问重新检索依据 | 学生只回复数字或不会 | N/A（不适用） |  | 需真实模型语义质量抽查，非确定性断言可证 |  | 0 |
| agent-assistant | 引导短追问重新检索依据 | 换题或无题目锚点 | 语义别名候选 | check_lessons_2_5 | agent.followup_without_anchor_unchanged |  | 1 |
| agent-assistant | 按学习进度自适应引导 | 多次卡住与完成 | N/A（不适用） |  | 需真实模型语义质量抽查，非确定性断言可证 |  | 0 |
| agent-assistant | 按学习进度自适应引导 | 概念与学生公式作答 | N/A（不适用） |  | 需真实模型语义质量抽查，非确定性断言可证 |  | 0 |
| agent-assistant | 教师技能文件 | 他人技能不可见 | 人工复核（确认覆盖） | check_mcp_tools | 同伴删他人技能 404 |  | 0 |
| agent-assistant | 教师技能文件 | 保存绑定 MCP 工具的技能 | 人工复核（确认覆盖） | check_mcp_tools | 技能保存成功 201 |  | 0 |
| agent-assistant | 教师技能文件 | 技能文件格式错误 | 断言名候选 | check_lesson10_scenario_gaps | 技能文件格式错误：缺分隔空行、未知字段、缺必填均解析失败且接口返回 400 |  | 7 |
| agent-assistant | 教师的可配置提示词 | 教师保存某班自定义提示词 | 断言名候选 | check_lesson10_skills | T3 边界：未开启引导时保留教师自定义提示词 |  | 6 |
| agent-assistant | 教师的可配置提示词 | 留空回退默认提示词 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.unconfigured_uses_default_prompt |  | 0 |
| agent-assistant | 教师的可配置提示词 | 配置非任教班级被拒绝 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.cross_class_config_denied |  | 0 |
| agent-assistant | 消息与会话持久化 | 仅带最近若干轮作为上下文 | 语义别名候选 | check_lessons_2_5 | agent.multiturn_context |  | 1 |
| agent-assistant | 消息与会话持久化 | 历史公式代码与实时回答一致 | 语义别名候选 | check_lessons_2_5 | agent.messages_persist |  | 1 |
| agent-assistant | 消息与会话持久化 | 历史消息权限不变 | 语义别名候选 | check_lessons_2_5 | agent.other_student_conversation_hidden |  | 1 |
| agent-assistant | 消息与会话持久化 | 回显历史消息 | 语义别名候选 | check_lessons_2_5 | agent.messages_persist |  | 1 |
| agent-assistant | 独立的按班级助手配置界面 | 保存提示词及解题引导 | 人工复核（确认覆盖） | check_lessons_2_5 | agent.config_save | config_read 同时校验提示词落库 | 0 |
| agent-assistant | 独立的按班级助手配置界面 | 切班回读配置 | 语义别名候选 | check_lessons_2_5 | agent.config_read |  | 1 |
| agent-assistant | 自动检索班级学科参考资料 | 尚无任教班级 | 人工复核（确认覆盖） | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 |  | 0 |
| agent-assistant | 自动检索班级学科参考资料 | 查看当前班级参考资料 | 语义别名候选 | check_lessons_2_5 | agent.citations_provenance |  | 1 |
| async-homework-grading | 可复现与证据归档 | F1 一键复现和迁移保留 | 人工复核（部分覆盖） | check_async_grading | F1 边界：重复迁移不改变旧数据 | 迁移与旧库升级有机器断言；README 一键复现未在门禁内实际执行 | 0 |
| async-homework-grading | 可靠投递及进程恢复 | B1 消费者停止再启动 | 人工复核（确认覆盖） | check_async_grading | B1 正常：队列有消息、消费者未运行时pending |  | 0 |
| async-homework-grading | 可靠投递及进程恢复 | B2 队列故障后补投 | 人工复核（确认覆盖） | check_async_grading | B2 正常：恢复后补投并可消费 |  | 0 |
| async-homework-grading | 可靠投递及进程恢复 | B3 事务中途失败 | 人工复核（确认覆盖） | check_async_grading | B3 失败：数据库错误503且不泄露内部信息 | 第二项故障整批回滚同文件断言 | 0 |
| async-homework-grading | 可靠投递及进程恢复 | B4 执行中杀进程与旧租约 | 人工复核（确认覆盖） | check_async_grading | B4 失败：旧租约不能覆盖 |  | 0 |
| async-homework-grading | 幂等与原评分边界 | C1 并发与重复投递 | 人工复核（确认覆盖） | check_async_grading | C1 边界：20并发数据库唯一幂等 |  | 0 |
| async-homework-grading | 幂等与原评分边界 | C2 重交及教师终评竞态 | 人工复核（确认覆盖） | check_quiz_homework | H/初批期间提交被更新或教师改分：教师终评 | 重交与旧结果跳过同组断言 | 0 |
| async-homework-grading | 快速提交与只读查询 | A1 正常提交不等待 | 人工复核（确认覆盖） | check_async_grading | A1 正常：20次202无评分且P95小于200ms假执行，无请求内模型调用 |  | 0 |
| async-homework-grading | 快速提交与只读查询 | A2 查询无副作用与空批次 | 人工复核（确认覆盖） | check_async_grading | A2 正常：GET只读 | 空批次由 A2 边界断言覆盖 | 0 |
| async-homework-grading | 快速提交与只读查询 | A3 参数与资源失败 | 人工复核（确认覆盖） | check_async_grading | A3 失败：非法任务编号422 | 同文件另断言任务不存在 404 与活跃任务重试 409 | 0 |
| async-homework-grading | 有限重试与可处置死信 | D1 失败退避与死信 | 人工复核（确认覆盖） | check_async_grading | D1 失败：死信投递失败不假确认 | 退避时间与不写部分分数同组 | 0 |
| async-homework-grading | 有限重试与可处置死信 | D2 手动重试与合法模型恢复 | 人工复核（确认覆盖） | check_async_grading | D2 正常：授权手动重试202 |  | 0 |
| async-homework-grading | 权限与页面范围 | E1 未登录及越权 | 人工复核（确认覆盖） | check_async_grading | E1 失败： | 模板按未登录/学生/他班/他科展开；403/404 审计同组 | 0 |
| async-homework-grading | 权限与页面范围 | E2 页面与刷新恢复 | N/A（不适用） |  | 前端页面刷新恢复，属界面行为 |  | 0 |
| async-homework-grading | 权限与页面范围 | E3 初批反馈在当前作业卡片可见 | 人工复核（确认覆盖） | check_grading_feedback | E3 正常：回执位于具有作业编号的卡片内，不在页面顶部 | 回执文案、错误 alert 与换行同文件断言 | 0 |
| async-homework-grading | 权限与页面范围 | E4 查看提交同步人数 | 人工复核（确认覆盖） | check_grading_feedback | E4 正常：提交数量更新且不污染其他作业或原数组 | 空列表/未知作业边界同文件断言 | 0 |
| async-homework-grading | 确认后限次投递与执行计数 | Q1 暂停消费者不积攒副本 | 人工复核（确认覆盖） | check_async_grading | Q1 边界：确认后跨越30分钟不积攒副本 |  | 0 |
| async-homework-grading | 确认后限次投递与执行计数 | Q2 未确认及过期运行恢复 | 人工复核（确认覆盖） | check_async_grading | Q2 边界：同一过期租约只确认一条恢复消息 |  | 0 |
| async-homework-grading | 确认后限次投递与执行计数 | Q3 管理员明确恢复丢失消息 | 人工复核（确认覆盖） | check_async_grading | Q3 正常：显式恢复只清待执行投递标记 |  | 0 |
| async-homework-grading | 确认后限次投递与执行计数 | Q4 界面不把消息数当批改数 | 人工复核（部分覆盖） | check_grading_feedback | E4 正常：提交数量更新且不污染其他作业或原数组 | 前端只同步提交数；队列消息数与批改数的后端分离无单独断言 | 0 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | Windows Docker 共享目录读写 | 人工复核（部分覆盖） | check_sqlite_storage | {mode} journal active | DELETE 模式并发提交、持久化与完整性已断言；未在真实 Windows 共享目录运行 | 0 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | 原生磁盘保留 WAL | 别名候选 | check_lesson10_p0_scenarios | P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖 |  | 1 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | 数据库暂不可用 | 人工复核（确认覆盖） | check_baseline | R1 失败：数据库异常 → 503 与通用提示 |  | 0 |
| class-data-isolation | 一人一号班级上下文 | 学生登录建立本人班级上下文 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user |  | 3 |
| class-data-isolation | 一人一号班级上下文 | 登出后重新登录使用新的班级范围 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user |  | 2 |
| class-data-isolation | 前端班级数据渲染控制 | 任课切班不改变带班上下文 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：任教班级与带班班级均由服务端令牌/数据库派生（不采信客户端参数） |  | 1 |
| class-data-isolation | 前端班级数据渲染控制 | 学生资料请求使用本人班级 | 人工复核（部分覆盖） | check_lesson10_review | 学生资料请求使用本人班级：学生端固定取本人 class_id，不提供跨班切换 | 前端源码断言 + 后端 materials.student_subject_scope_denied 拒绝跨班；未跑浏览器 | 0 |
| class-data-isolation | 前端班级数据渲染控制 | 篡改 class_id 不能扩权 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 后端不信任请求参数中的 class_id | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 后端查询强制带 class_id 过滤 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 请求参数 class_id 与 JWT 不符被拒 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 学生班级数据范围控制 | 学生尝试查看其他班级资料被拒 | 别名候选 | check_lessons_2_5 | materials.subject_list_cross_class_denied |  | 4 |
| class-data-isolation | 学生班级数据范围控制 | 学生提交作业关联到本班 | 别名候选 | check_homework | S3 正常：学生提交成功 |  | 3 |
| class-data-isolation | 学生班级数据范围控制 | 学生查看本班资料成功 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.download | 列表/预览/下载同文件断言 | 0 |
| class-data-isolation | 教师班级数据范围控制 | 教师查看任教班级资料成功 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.all_subject_list_preserved | 任教范围内跨班可见；越界由 subject_list_cross_class_denied 反证 | 0 |
| class-data-isolation | 教师班级数据范围控制 | 教师查看非任教班级资料被拒 | 别名候选 | check_lessons_2_5 | auth.teacher_cross_class_denied |  | 3 |
| class-data-isolation | 教师班级数据范围控制 | 教师跨班布置作业被拒 | 别名候选 | check_homework | S1 失败：非任教班级布置 → 403 |  | 3 |
| class-data-isolation | 无班级分配边界处理 | 学生未分配班级前端展示空状态 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied |  | 2 |
| class-data-isolation | 无班级分配边界处理 | 学生未分配班级后端拒绝查询 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied |  | 2 |
| class-data-isolation | 无班级分配边界处理 | 教师未分配任教班级前端展示空状态 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 |  | 1 |
| class-data-isolation | 无班级分配边界处理 | 教师未分配任教班级后端拒绝查询 | 断言名候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 |  | 8 |
| class-data-isolation | 班级数据隔离模型与字段规范 | AI 提问记录表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 作业布置表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 作业提交记录表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 班级资料表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 错题本表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 跨班访问拦截与审计日志 | 教师篡改 class_id 跨班访问被拦截 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| class-data-isolation | 跨班访问拦截与审计日志 | 篡改 API Payload 中 class_id 被拦截 | 断言名候选 | check_lessons_2_5 | materials.cross_class_download_denied |  | 8 |
| class-data-isolation | 跨班访问拦截与审计日志 | 篡改 URL 参数跨班访问被拦截 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.cross_class_list_denied | URL 参数跨班返回 403；审计由全局 403 记录断言 | 0 |
| class-data-isolation | 跨班访问拦截与审计日志 | 跨班访问审计日志记录完整 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 2 |
| class-data-isolation | 隔离数据范围界定 | 学校级公共资源不隔离 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：学科组素材按学科归属、不绑定班级 |  | 1 |
| class-data-isolation | 隔离数据范围界定 | 班级资料严格隔离 | 别名候选 | check_lessons_2_5 | materials.cross_class_download_denied |  | 2 |
| class-data-isolation | 隔离数据范围界定 | 用户账号基础信息不隔离 | 人工复核（部分覆盖） | check_lesson10_review | 用户账号基础信息不隔离：不同班级学生均能读取本人姓名与班级 | 登录/刷新返回本人姓名与班级；接口未返回学号字段 | 0 |
| class-data-isolation | 隔离数据范围界定 | 系统公告不隔离 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：不存在按班级隔离的系统公告模型（特性未实现，无误隔离） |  | 1 |
| login-and-account-system | JWT 会话管理 | Access Token 过期自动刷新 | 人工复核（部分覆盖） | check_lesson10_review | Access Token 过期自动刷新：前端 401 后调用 refresh 并重试原请求 | 后端 refresh 由 auth.refresh 断言；自动重试为源码断言，未跑浏览器 | 0 |
| login-and-account-system | JWT 会话管理 | JWT Payload 包含必要字段 | 人工复核（确认覆盖） | check_lesson10_review | JWT Payload 包含必要字段：教师令牌含七个声明 | 学生令牌不带教师身份同组断言 | 0 |
| login-and-account-system | JWT 会话管理 | Refresh Token 过期需重新登录 | 人工复核（确认覆盖） | check_lesson10_review | Refresh Token 过期需重新登录：过期刷新令牌返回 401 |  | 0 |
| login-and-account-system | JWT 会话管理 | 登录成功签发双 Token | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） |  | 2 |
| login-and-account-system | 初始密码规则 | 学生账号初始密码生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 |  | 7 |
| login-and-account-system | 初始密码规则 | 教师账号初始密码生成 | 断言名候选 | check_lesson10_scenarios | 教师账号初始密码：前缀为学校缩写且结尾为工号末六位 |  | 7 |
| login-and-account-system | 刷新页面恢复完整会话 | 刷新失败回登录 | 人工复核（确认覆盖） | check_route_guard | 身份恢复前不显示业务内容：缺少 | 缺 accessToken/身份提示时拒绝显示业务页 | 0 |
| login-and-account-system | 刷新页面恢复完整会话 | 学生刷新后仍指向本人 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user |  | 1 |
| login-and-account-system | 刷新页面恢复完整会话 | 教师刷新后保留页面 | 人工复核（部分覆盖） | check_lessons_2_5 | auth.refresh_restores_full_user | 完整身份恢复有断言；URL 与菜单保留属浏览器行为 | 0 |
| login-and-account-system | 多端在线与登出 | 同一账号多端登录都成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） |  | 2 |
| login-and-account-system | 多端在线与登出 | 登出清除所有 Token 和状态 | 人工复核（确认覆盖） | check_lesson10_review | 登出清除所有 Token 和状态：前端清本地状态并跳转登录，后端清 Cookie |  | 0 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 任教范围内创建或更新 | 别名候选 | check_lessons_2_5 | auth.csv_assigned_class_allowed |  | 1 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 修改非任教班级学生被拒绝 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.csv_other_class_update_denied |  | 0 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 合法行之后出现越权行 | 别名候选 | check_lessons_2_5 | auth.csv_forbidden_batch_rolled_back |  | 2 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 导入非任教目标班级被拒绝 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.csv_other_class_create_denied |  | 0 |
| login-and-account-system | 密码安全策略与存储 | 不符合策略的密码被拒绝 | 别名候选 | check_lessons_2_5 | auth.weak_password_denied |  | 3 |
| login-and-account-system | 密码安全策略与存储 | 密码长度不足被拒绝 | 别名候选 | check_lessons_2_5 | auth.weak_password_denied |  | 3 |
| login-and-account-system | 密码安全策略与存储 | 符合策略的密码被接受 | 别名候选 | check_lessons_2_5 | auth.change_password |  | 1 |
| login-and-account-system | 密码登录 | 学生用学号和密码登录成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） |  | 2 |
| login-and-account-system | 密码登录 | 密码错误登录失败 | 人工复核（确认覆盖） | check_lesson10_review | 密码错误与账号不存在返回同一提示 | 均为 401 且文案相同 | 0 |
| login-and-account-system | 密码登录 | 教师用工号和密码登录成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） |  | 2 |
| login-and-account-system | 密码登录 | 账号不存在登录失败 | 人工复核（确认覆盖） | check_lesson10_review | 密码错误与账号不存在返回同一提示 | 与密码错误逐字相同 | 0 |
| login-and-account-system | 密码登录失败锁定 | 密码登录成功清零失败计数 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） |  | 2 |
| login-and-account-system | 密码登录失败锁定 | 连续5次密码失败后锁定 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock |  | 2 |
| login-and-account-system | 密码登录失败锁定 | 锁定期间正确密码也被拒 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock |  | 1 |
| login-and-account-system | 密码登录失败锁定 | 锁定过期后可正常登录 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock |  | 1 |
| login-and-account-system | 封闭注册与一人一号账号预置 | CSV 缺少学号列被拒绝 | 人工复核（确认覆盖） | check_lesson10_review | CSV 缺少学号列被拒绝：400 且不创建账号 |  | 0 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 多个学生使用相同联系方式 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：用户唯一约束仅限 role+identifier，不含 phone（联系方式可重复） |  | 1 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 教师通过 CSV 批量导入学生含手机号 | 人工复核（确认覆盖） | check_lesson10_review | CSV 导入手机号：phone 字段落库 |  | 0 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 未登录用户无法注册 | 人工复核（确认覆盖） | check_lesson10_review | 未登录用户无法注册：注册接口不存在且登录页无注册入口 |  | 0 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 预置教师账号携带学科与班主任身份 | 人工复核（确认覆盖） | check_lesson10_review | 开发种子：教师学科与班主任身份写入 |  | 0 |
| login-and-account-system | 开发种子账号与班级名称 | 教师种子维护身份而不覆盖已改密码 | 人工复核（确认覆盖） | check_lesson10_review | 教师种子维护身份而不覆盖已改密码：重跑保留自定义口令并更新学科 |  | 0 |
| login-and-account-system | 开发种子账号与班级名称 | 李明初始密码按学号末六位生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 |  | 7 |
| login-and-account-system | 开发种子账号与班级名称 | 王芳初始密码按学号末六位生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 |  | 7 |
| login-and-account-system | 强制首次改密（无验证码例外） | 改密成功后恢复正常访问 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.change_password |  | 0 |
| login-and-account-system | 强制首次改密（无验证码例外） | 未改密时访问业务接口被拦截 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.first_password_blocks_business | 会话/历史接口另两项同组断言 | 0 |
| login-and-account-system | 强制首次改密（无验证码例外） | 首次密码登录被拦截要求改密 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.first_password_blocks_business |  | 0 |
| login-and-account-system | 忘记密码与重置密码 | 任课权限不能代替班主任权限 | 别名候选 | check_lessons_2_5 | auth.subject_teacher_reset_denied |  | 3 |
| login-and-account-system | 忘记密码与重置密码 | 班主任重置本班学生密码 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset |  | 3 |
| login-and-account-system | 忘记密码与重置密码 | 用户忘记密码看到班主任提示 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：忘记密码显示「请联系班主任重置」提示 |  | 1 |
| material-upload | 上传元数据与班级选择 | 上传元数据完整记录 | 语义别名候选 | check_lessons_2_5 | materials.upload_md |  | 1 |
| material-upload | 上传元数据与班级选择 | 多班级教师班级选择器展示所有任教班级 | N/A（不适用） |  | 前端选择器展示，属界面交互 |  | 0 |
| material-upload | 上传元数据与班级选择 | 教师篡改 class_id 上传非任教班级被拒 | 断言名候选 | check_lesson10_p0_scenarios | P0 接口：题库/组卷模块校验任教学科（subject），班级模块校验任教班级（teaching_classes） |  | 7 |
| material-upload | 上传元数据与班级选择 | 教师选择任教班级上传成功 | 语义别名候选 | check_lessons_2_5 | materials.upload_md |  | 1 |
| material-upload | 下载与预览 | 学生下载材料成功 | 语义别名候选 | check_lessons_2_5 | materials.download |  | 1 |
| material-upload | 下载与预览 | 学生在线预览 PDF 成功 | 语义别名候选 | check_lessons_2_5 | materials.preview |  | 1 |
| material-upload | 下载与预览 | 学生在线预览图片成功 | 语义别名候选 | check_lessons_2_5 | materials.preview |  | 1 |
| material-upload | 下载与预览 | 学生尝试下载其他班材料被拒 | 语义别名候选 | check_lessons_2_5 | materials.cross_class_download_denied |  | 1 |
| material-upload | 下载与预览 | 引用原文的文件版本已变化 | 语义别名候选 | check_lessons_2_5 | citations.changed_file_stale_index_excluded |  | 1 |
| material-upload | 下载与预览 | 教师下载任教班级材料成功 | 语义别名候选 | check_lessons_2_5 | materials.download |  | 1 |
| material-upload | 教师上传权限控制 | 学生前端无上传入口 | 别名候选 | check_lessons_2_5 | materials.student_upload_denied |  | 2 |
| material-upload | 教师上传权限控制 | 学生尝试上传被拒 | 别名候选 | check_lessons_2_5 | materials.student_upload_denied |  | 2 |
| material-upload | 教师上传权限控制 | 教师上传资料成功 | 语义别名候选 | check_lessons_2_5 | materials.upload_md |  | 1 |
| material-upload | 教师删除资料 | 删除后资料不可再访问 | 语义别名候选 | check_lessons_2_5 | materials.delete |  | 1 |
| material-upload | 教师删除资料 | 前端仅教师展示删除入口 | N/A（不适用） |  | 前端入口可见性，属界面展示 |  | 0 |
| material-upload | 教师删除资料 | 学生尝试删除资料被拒 | 人工复核（确认覆盖） | check_lesson10_review | 学生尝试删除资料被拒：学生调用删除接口 403 且资料保留 |  | 0 |
| material-upload | 教师删除资料 | 教师删除任教班级资料成功 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.delete | MaterialContent/Chunk 清理同文件断言 | 0 |
| material-upload | 教师删除资料 | 教师尝试删除非任教班级资料被拒 | 别名候选 | check_lessons_2_5 | auth.teacher_cross_class_denied |  | 3 |
| material-upload | 文件存储策略 | SQLite 仅存储元数据 | 人工复核（确认覆盖） | check_lesson10_review | SQLite 仅存储元数据：Material 表无二进制列 |  | 0 |
| material-upload | 文件存储策略 | 容器重启后文件不丢失 | N/A（不适用） |  | 需容器重启，属部署环境验证 |  | 0 |
| material-upload | 文件存储策略 | 文件存储在挂载目录 | 断言名候选 | check_lesson10_scenario_gaps | 文件存储在挂载目录：按班级子目录写入 UPLOAD_DIR |  | 8 |
| material-upload | 文件存储策略 | 文件按 class_id 分子目录存储 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| material-upload | 文件类型与大小限制 | 上传不允许的格式被拒 | 语义别名候选 | check_lessons_2_5 | materials.forged_pdf_denied |  | 1 |
| material-upload | 文件类型与大小限制 | 上传允许格式的文件成功 | 语义别名候选 | check_lessons_2_5 | materials.upload_md |  | 1 |
| material-upload | 文件类型与大小限制 | 上传超大文件被拒 | 断言名候选 | check_lesson10_scenario_gaps | 上传超大文件被拒：上限为 50MB |  | 7 |
| material-upload | 文件类型与大小限制 | 伪造扩展名被后端 MIME 校验拦截 | 语义别名候选 | check_lessons_2_5 | materials.forged_pdf_denied |  | 1 |
| material-upload | 文件类型与大小限制 | 前端 accept 属性初步限制 | 人工复核（确认覆盖） | check_lesson10_review | 前端 accept 属性初步限制：ACCEPT 仅含允许格式且绑定文件输入 |  | 0 |
| material-upload | 文件重名与异常处理 | DB 写入失败时回滚删除物理文件 | 断言名候选 | check_lesson10_scenario_gaps | DB 写入失败时回滚删除物理文件：返回 500、数据库回滚且磁盘文件已清理 |  | 14 |
| material-upload | 文件重名与异常处理 | 同名文件自动重命名 | 断言名候选 | check_lesson10_scenario_gaps | 同名文件自动重命名：同秒同名文件追加计数器不覆盖 |  | 8 |
| material-upload | 文件重名与异常处理 | 恶意文件头校验不通过被拒 | 语义别名候选 | check_lessons_2_5 | materials.forged_pdf_denied |  | 1 |
| material-upload | 文件重名与异常处理 | 网络中断前端提供重试 | N/A（不适用） |  | 前端重试交互，属界面行为 |  | 0 |
| material-upload | 材料数据隔离 | 学生尝试下载其他班材料被拒 | 语义别名候选 | check_lessons_2_5 | materials.cross_class_download_denied |  | 1 |
| material-upload | 材料数据隔离 | 学生查询本班材料成功 | 语义别名候选 | check_lessons_2_5 | materials.math_subject_list |  | 1 |
| material-upload | 材料数据隔离 | 学生篡改 class_id 查询被拒 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| material-upload | 材料数据隔离 | 教师查询任教班级材料成功 | 语义别名候选 | check_lessons_2_5 | materials.math_subject_list |  | 1 |
| material-upload | 知识库索引关联 | 上传成功后异步解析为纯文本 | 语义别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted |  | 1 |
| material-upload | 知识库索引关联 | 仅 is_indexed=true 的材料被 AI 检索 | 断言名候选 | check_lesson10_scenario_gaps | 解析失败的材料保持未索引：is_indexed 为 False 且 parse_error 落库 |  | 11 |
| material-upload | 知识库索引关联 | 解析失败的材料保持未索引 | 断言名候选 | check_lesson10_scenario_gaps | 解析失败的材料保持未索引：is_indexed 为 False 且 parse_error 落库 |  | 11 |
| material-upload | 知识库索引关联 | 解析完成后标记 is_indexed 为 true | 断言名候选 | check_lesson10_scenario_gaps | 解析失败的材料保持未索引：is_indexed 为 False 且 parse_error 落库 |  | 11 |
| mcp-tool-integration | MCP 与技能接口文档 | 打开 Swagger 试调 | N/A（不适用） |  | 需以 ENABLE_DOCS=true 启动并用浏览器携带教师令牌试调，属本地接口文档人工验证；默认关闭已由 check_lesson10_scenario_gaps 断言 |  | 0 |
| mcp-tool-integration | MCP 与技能接口文档 | 默认关闭文档 | 人工复核（确认覆盖） | check_lesson10_scenario_gaps | 默认关闭文档：代码默认值为关闭，/docs 与 /openapi.json 随之不暴露 |  | 0 |
| mcp-tool-integration | MCP 工具调用审计 | 三种结果各有记录 | 语义别名候选 | check_mcp_tools | 写入 ok 审计记录 |  | 1 |
| mcp-tool-integration | MCP 工具调用审计 | 决策轮用量可追溯 | 人工复核（确认覆盖） | check_security_gate | P1-2 决策轮用量： | 合法/缺失/非法三类用量逐项断言 | 0 |
| mcp-tool-integration | MCP 工具调用审计 | 审计存储失败可观察 | 人工复核（确认覆盖） | check_security_gate | 审计故障：告警可见且不泄露异常原文 | 工具存储回滚且不中断同组 | 0 |
| mcp-tool-integration | MCP 工具调用审计 | 记录只看自己的范围 | 语义别名候选 | check_mcp_tools | 同伴看不到我的记录 |  | 1 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 不在允许清单的地址 | 断言名候选 | check_lesson10_scenario_gaps | 不在允许清单的地址：清单外主机、回环、本机与元数据地址均被拒 |  | 8 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 同名再登记 | 人工复核（确认覆盖） | check_mcp_tools | 同名再登记 400 |  | 0 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 换机后令牌不可用 | 语义别名候选 | check_mcp_tools | 换密钥后解密失败并提示重新填写令牌 |  | 1 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 登记后响应不含令牌 | 人工复核（确认覆盖） | check_mcp_tools | 响应不含令牌 |  | 0 |
| mcp-tool-integration | 候选工具与工具声明 | 只带技能内工具 | 语义别名候选 | check_mcp_tools | 候选集外工具 denied、不执行、不写审计 |  | 1 |
| mcp-tool-integration | 工具内容的信任边界 | 工具说明夹带指令 | 已知缺口 | check_mcp_tools | 工具说明夹带指令：含指令式说明的工具不进入候选清单并列入排除 | 「远端工具说明要求模型先读取其他数据并放进参数」不在现有注入句式表内；检查只证明已知句式（忽略指令/扮演/泄露提示词）说明会被排除，按 mcp-tool-integration Requirement「本期只拦截已知写法」记为已知限制。 | 0 |
| mcp-tool-integration | 工具内容的信任边界 | 工具返回夹带指令 | 断言名候选 | check_mcp_tools | 工具返回夹带指令：工具事件记 error 且原因为未通过安全检查 |  | 7 |
| mcp-tool-integration | 工具引用格式与保存期校验 | 工具不在清单或服务器未连接 | 人工复核（确认覆盖） | check_mcp_tools | 候选集外工具 denied、不执行、不写审计 |  | 0 |
| mcp-tool-integration | 工具引用格式与保存期校验 | 引用写法不合规 | 语义别名候选 | check_mcp_tools | 断开后引用记 denied |  | 1 |
| mcp-tool-integration | 服务器与调用记录的归属隔离 | 同伴访问我的服务器 | 人工复核（确认覆盖） | check_mcp_tools | 同伴读取他人服务器 404 |  | 0 |
| mcp-tool-integration | 服务器与调用记录的归属隔离 | 学生调用管理接口 | 人工复核（确认覆盖） | check_mcp_tools | 学生访问管理接口 403 |  | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 两步任务连续两轮 | 语义别名候选 | check_mcp_tools | meta.tool_calls 按序含两轮 ok 记录 |  | 1 |
| mcp-tool-integration | 服务端调用循环与上限 | 发现重连未知权限默认拒绝 | 人工复核（确认覆盖） | check_security_gate | P0-5 正常/边界：真实发现分类保守且不信远端只读声明 | 未知工具默认可写不等于可执行；重连不降级由分类断言覆盖 | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 命中工具并用到提示 | N/A（不适用） |  | 前端提示展示，属界面交互 |  | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 学生写入拒绝且 SSE 完整 | 人工复核（部分覆盖） | check_mcp_tools | 学生身份不能执行可写工具（不采信角色声明） | 拒绝与零执行有断言；SSE meta+done 完整性由同文件首帧与结束帧断言覆盖 | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 工具超时 | 人工复核（确认覆盖） | check_mcp_tools | 工具超时：本次调用记 error 且原因写明失败 |  | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 教师与错误归属执行对照 | 语义别名候选 | check_mcp_tools | 参数不符记 error 且未执行 |  | 1 |
| mcp-tool-integration | 服务端调用循环与上限 | 超过轮次上限 | 语义别名候选 | check_mcp_tools | 超出每问上限的调用写 denied 审计 |  | 1 |
| mcp-tool-integration | 自建 MCP 工具服务 | 令牌缺失或错误 | 语义别名候选 | check_mcp_tools | 未配置 MCP_TOKEN_KEY 拒绝保存令牌 |  | 1 |
| mcp-tool-integration | 自建 MCP 工具服务 | 带令牌发现并调用工具 | 人工复核（确认覆盖） | check_mcp_tools | 确实带令牌调用了工具 | meta.tool_calls 记录 ok 同组 | 0 |
| mcp-tool-integration | 自建 MCP 工具服务 | 非法请求可读 | 人工复核（确认覆盖） | check_mcp_server | 非法请求可读： | 8 类非法请求逐项返回 JSON-RPC 错误码与中文说明 | 0 |
| mcp-tool-integration | 连接、发现与断开 | 令牌错误时连接失败 | 人工复核（确认覆盖） | check_mcp_tools | 连接失败 502 |  | 0 |
| mcp-tool-integration | 连接、发现与断开 | 断开后不可调用 | 人工复核（确认覆盖） | check_mcp_tools | 断开后引用记 denied |  | 0 |
| mcp-tool-integration | 连接、发现与断开 | 连接自建服务发现工具 | 人工复核（确认覆盖） | check_mcp_tools | 连接成功 200 | 工具清单不翻倍由「重复连接工具不翻倍」证明 | 0 |
| mcp-tool-integration | 连接、发现与断开 | 连续连接两次 | 语义别名候选 | check_mcp_tools | 重复连接工具不翻倍 |  | 1 |
| quiz-homework-publication | 作业及配图逐资源授权 | 学生跨班读取或提交 | 别名候选 | check_quiz_homework | H/学生跨班读取或提交 |  | 3 |
| quiz-homework-publication | 作业及配图逐资源授权 | 教师班级或学科不符 | 别名候选 | check_quiz_homework | H/教师班级或学科不符： |  | 3 |
| quiz-homework-publication | 作业及配图逐资源授权 | 未登录读取作业或配图 | 别名候选 | check_quiz_homework | H/未登录读取作业或配图： |  | 2 |
| quiz-homework-publication | 作业及配图逐资源授权 | 访问他人的提交或教师接口 | 断言名候选 | check_quiz_homework | H/访问他人的提交或教师接口：教师接口 |  | 11 |
| quiz-homework-publication | 作业及配图逐资源授权 | 配图异常 | 人工复核（确认覆盖） | check_quiz_homework | H/配图异常：非法名 | 点路径、未知名与指纹变化同组 | 0 |
| quiz-homework-publication | 作业终评与错题同步 | M1 首次满分不入错题 | 语义别名候选 | check_assignment_history | M1 正常：首次100分不入错题 |  | 1 |
| quiz-homework-publication | 作业终评与错题同步 | M2 低分改为及格或满分 | 语义别名候选 | check_quiz_homework | H/教师覆盖 AI 分且后续初批跳过 |  | 1 |
| quiz-homework-publication | 作业终评与错题同步 | M3 修复历史残留不改成绩 | 语义别名候选 | check_assignment_history | M3 正常：备份后修复且重复执行0条 |  | 1 |
| quiz-homework-publication | 作业终评与错题同步 | M4 越权或事务失败不部分改分 | 人工复核（确认覆盖） | check_quiz_homework | H/初批失败仍可人工改分： | 越权改分 403 与拒绝访问审计同组；失败批次无部分写入 | 0 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 更新后旧资料仍可访问 | 断言名候选 | check_quiz_homework | H/更新后旧资料仍可访问 |  | 9 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 老试卷主动重新发布 | 断言名候选 | check_quiz_homework | H/老试卷主动重新发布 |  | 8 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 迁移重复执行 | 人工复核（确认覆盖） | check_quiz_homework | H/迁移重复执行 |  | 0 |
| quiz-homework-publication | 发布内容和教师评分依据分离冻结 | 原题和原资料后续变化 | 断言名候选 | check_quiz_homework | H/原题和原资料后续变化 |  | 9 |
| quiz-homework-publication | 发布内容和教师评分依据分离冻结 | 学生响应不泄露评分依据 | 别名候选 | check_quiz_homework | H/学生响应不泄露评分依据 |  | 2 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | AI 使用发布时的评分依据 | 断言名候选 | check_quiz_homework | H/AI 使用发布时的评分依据 |  | 11 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 分数折算边界 | 人工复核（确认覆盖） | check_quiz_homework | H/分数折算边界： | 合法/越界逐项断言 | 0 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 初批失败仍可人工改分 | 断言名候选 | check_quiz_homework | H/初批失败仍可人工改分： |  | 9 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 初批期间提交被更新或教师改分 | 断言名候选 | check_quiz_homework | H/初批期间提交被更新或教师改分：重交 |  | 13 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 教师直接评分并联动错题学情 | 断言名候选 | check_quiz_homework | H/教师直接评分并联动错题学情 |  | 12 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 教师覆盖 AI 分且后续初批跳过 | 断言名候选 | check_quiz_homework | H/教师覆盖 AI 分且后续初批跳过 |  | 13 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 非百分制原卷折算 | 断言名候选 | check_quiz_homework | H/非百分制原卷折算 |  | 7 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 截止前重新提交 | 断言名候选 | check_quiz_homework | H/截止前重新提交 |  | 6 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 提交命题作业 | 人工复核（确认覆盖） | check_quiz_homework | H/提交命题作业 |  | 0 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 逾期或关闭后提交 | 断言名候选 | check_quiz_homework | H/逾期或关闭后提交：逾期 |  | 7 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 题面显示一致 | 人工复核（确认覆盖） | check_quiz_homework | H/题面显示一致 | 含第 10/12 题与填空空位 | 0 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 两种作业同时展示 | 断言名候选 | check_quiz_homework | H/两种作业同时展示 |  | 7 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 保留手工布置 | 人工复核（确认覆盖） | check_quiz_homework | H/保留手工布置：草稿不可见 | 两种作业同时展示同文件断言 | 0 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 学科与班级筛选 | 断言名候选 | check_quiz_homework | H/学科与班级筛选 |  | 6 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 公式渲染为数学符号 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：公式渲染使用 KaTeX 数学符号 |  | 1 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 支持 Markdown 列表与加粗 | 人工复核（确认覆盖） | check_lesson10_review | 支持 Markdown 列表与加粗：解析保留列表与加粗原文 |  | 0 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 独立公式居中美化与长公式横向滚动 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：独立公式居中与长公式横向滚动样式存在 |  | 1 |
| rag-search | 上传材料的索引流程扩展 | 上传成功后异步解析并分块向量化 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted |  | 3 |
| rag-search | 上传材料的索引流程扩展 | 解析成功但向量化失败保持未索引 | 人工复核（确认覆盖） | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 |  | 0 |
| rag-search | 关键字、向量与混合检索 | 关键字检索返回字面命中的分块 | 别名候选 | check_formula_retrieval | keyword formula recalled despite coordinate distractor |  | 1 |
| rag-search | 关键字、向量与混合检索 | 向量检索按哈希向量相似度排序 | 别名候选 | check_formula_retrieval | vector formula recalled despite coordinate distractor |  | 1 |
| rag-search | 关键字、向量与混合检索 | 混合检索融合两路排序 | 别名候选 | check_formula_retrieval | hybrid formula recalled despite coordinate distractor |  | 2 |
| rag-search | 内容溯源 | 回答标注引用来源 | 别名候选 | check_lessons_2_5 | agent.citations_provenance |  | 2 |
| rag-search | 内容溯源 | 引用来源与检索一致 | 别名候选 | check_formula_retrieval | real formula reference retained |  | 2 |
| rag-search | 内容溯源 | 文件变更或历史索引无版本 | 别名候选 | check_formula_retrieval | tampered source excluded |  | 3 |
| rag-search | 内容溯源 | 无效编号与未使用候选 | 别名候选 | check_lessons_2_5 | citations.invalid_number_removed |  | 1 |
| rag-search | 向量化存储 | 分块向量化并存储 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted |  | 2 |
| rag-search | 向量化存储 | 向量化失败不阻塞上传 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 |  | 1 |
| rag-search | 回答不包含检索过程元话语 | 用户直接询问教材标准公式 | 别名候选 | check_formula_retrieval | real formula reference retained |  | 1 |
| rag-search | 回答不包含检索过程元话语 | 资料未含公式本体时说明依据不足 | 别名候选 | check_formula_retrieval | no invented auto reference |  | 1 |
| rag-search | 回答正文与参考资料分离展示 | 命中可标注出处并回溯到原文 | 别名候选 | check_lessons_2_5 | citations.excerpt_is_exact_chunk |  | 1 |
| rag-search | 回答正文与参考资料分离展示 | 回答与参考资料独立成卡 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：回答与参考资料在数据模型中分离（citations 独立字段） |  | 1 |
| rag-search | 回答正文与参考资料分离展示 | 多命中逐条展示保留溯源 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：参考资料独立区域逐条展示并保留溯源 |  | 1 |
| rag-search | 回答正文与参考资料分离展示 | 引用摘录保留真实分块 | 别名候选 | check_formula_retrieval | raw excerpts unchanged |  | 2 |
| rag-search | 回答正文与参考资料分离展示 | 无引用时仅显示回答 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：无引用时仅显示回答（条件渲染） |  | 1 |
| rag-search | 基于限定的被检索资料回答 | 无召回分块不臆造依据 | 别名候选 | check_formula_retrieval | no invented auto reference |  | 2 |
| rag-search | 基于限定的被检索资料回答 | 答案基于召回分块生成 | 别名候选 | check_formula_retrieval | real formula reference retained |  | 1 |
| rag-search | 数值题公式检索与原文保持 | 坐标题检索夹角余弦公式 | 人工复核（确认覆盖） | check_formula_retrieval | {mode} formula recalled despite coordinate distractor | 原文摘录不变与来源指纹精确同文件 | 0 |
| rag-search | 数值题公式检索与原文保持 | 无关或变更资料 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter |  | 2 |
| rag-search | 文本分块 | 短材料生成单个分块 | 断言名候选 | check_lesson10_scenarios | 文本分块：短材料生成单个分块 |  | 8 |
| rag-search | 文本分块 | 解析材料生成多个分块 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted |  | 2 |
| rag-search | 跨章节检索预筛 (Cross-Chapter Prefilter) | 跨章节无关材料被预筛排除 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter |  | 2 |
| rag-search | 跨章节检索预筛 (Cross-Chapter Prefilter) | 预筛无保留时回退全保留 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter |  | 2 |
| rag-search | 限定班级的知识库检索 | 学生提问召回本班相关分块 | 别名候选 | check_formula_retrieval | keyword formula recalled despite coordinate distractor |  | 1 |
| rag-search | 限定班级的知识库检索 | 无可用分块时降级 | 别名候选 | check_formula_retrieval | no invented auto reference |  | 2 |
| rag-search | 限定班级的知识库检索 | 检索严格限定本班范围 | 别名候选 | check_formula_retrieval | class and subject retained |  | 1 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 不同学生账号次数独立计算 | 人工复核（确认覆盖） | check_lesson10_review | 不同学生账号次数独立计算：两名学生各自计数互不影响 |  | 0 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 学生当日提问未达上限 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：AI 提问每日上限为 40 次 |  | 1 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 学生当日提问达到上限被拒 | 别名候选 | check_lessons_2_5 | agent.spec_40_question_limit |  | 2 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 次日提问次数重置 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：提问计数按中国时区自然日重置 |  | 1 |
| rbac-role-permissions | 前端路由级权限拦截 | 伪造角色提示不赋予页面权限 | 断言名候选 | check_route_guard | 伪造角色提示不赋予页面权限：提示仅允许启动校验 |  | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 刷新恢复后的角色仍须匹配 | 断言名候选 | check_route_guard | 刷新恢复后的角色仍须匹配： |  | 11 |
| rbac-role-permissions | 前端路由级权限拦截 | 双标签提示变化后的单科切班 | 断言名候选 | check_route_guard | 双标签提示变化后的单科切班：教师页面不被学生提示拒绝 |  | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 学生访问学生路由通过 | 人工复核（确认覆盖） | check_route_guard | 本角色页面正常渲染：student → /student |  | 0 |
| rbac-role-permissions | 前端路由级权限拦截 | 学生访问教师路由被拦截 | 人工复核（确认覆盖） | check_route_guard | 伪造角色提示不赋予页面权限：student → /teacher |  | 0 |
| rbac-role-permissions | 前端路由级权限拦截 | 教师访问学生路由被拦截 | 人工复核（确认覆盖） | check_route_guard | 伪造角色提示不赋予页面权限：teacher → /student |  | 0 |
| rbac-role-permissions | 前端路由级权限拦截 | 教师访问教师路由通过 | 人工复核（确认覆盖） | check_route_guard | 本角色页面正常渲染：teacher → /teacher |  | 0 |
| rbac-role-permissions | 前端路由级权限拦截 | 未登录用户访问业务路由重定向登录 | 人工复核（确认覆盖） | check_route_guard | 身份恢复前不显示业务内容：缺少 | 缺 accessToken/身份提示时拒绝进入业务页 | 0 |
| rbac-role-permissions | 前端路由级权限拦截 | 角色目录按完整路径边界判断 | 断言名候选 | check_route_guard | 角色目录按完整路径边界判断：${route} / ${role} |  | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 身份恢复前不显示业务内容 | 断言名候选 | check_route_guard | 身份恢复前不显示业务内容：缺少 |  | 11 |
| rbac-role-permissions | 前端路由级权限拦截 | 辅助提示缺失但会话有效 | 断言名候选 | check_route_guard | 辅助提示缺失但会话有效：允许启动并恢复 ${route} |  | 10 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 学生仅以学号密码登录 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.login.S1 |  | 0 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 教师学科身份登录后进入教研组 | 人工复核（确认覆盖） | check_research_materials | same subject colleagues share source |  | 0 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 系统不创建独立家长角色 | 断言名候选 | check_lesson10_scenarios | 双角色定义：系统不创建独立家长角色 |  | 10 |
| rbac-role-permissions | 后端接口级权限拦截 | 学生调用学生接口通过 | 人工复核（确认覆盖） | check_homework | S3 正常：学生提交成功 |  | 0 |
| rbac-role-permissions | 后端接口级权限拦截 | 学生调用教师接口返回 403 | 别名候选 | check_lessons_2_5 | auth.student_teacher_api_denied |  | 2 |
| rbac-role-permissions | 后端接口级权限拦截 | 教师调用学生接口返回 403 | 别名候选 | check_lessons_2_5 | auth.teacher_student_api_denied |  | 2 |
| rbac-role-permissions | 后端接口级权限拦截 | 教师调用教师接口通过 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.upload_md |  | 0 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生不能越权查看其他学生数据 | 人工复核（确认覆盖） | check_mistake | S4 正常：请求参数 student_id 被忽略，仍只返回本人错题 |  | 0 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生修改个人密码 | 别名候选 | check_lessons_2_5 | auth.change_password |  | 1 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生发起 AI 提问并查看历史 | 人工复核（确认覆盖） | check_lesson10_review | 学生发起 AI 提问并查看历史：提问落库且历史仅本人可见 |  | 0 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生将 AI 解答加入错题本 | 已知缺口 |  |  | 错题本只有列表/详情/掌握/讲解四个接口，没有「加入错题本」写入接口与页面入口 | 0 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生查看个人错题本 | 人工复核（确认覆盖） | check_mistake | S1 正常：本人错题列表返回 2 条 |  | 0 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生查看本班资料并提交作业 | 别名候选 | check_homework | S3 正常：学生提交成功 |  | 3 |
| rbac-role-permissions | 学生数据权限 - 个人数据隔离（一人一号） | 学生尝试查询他人数据被拒 | 人工复核（确认覆盖） | check_mistake | S4 正常：请求参数 student_id 被忽略，仍只返回本人错题 |  | 0 |
| rbac-role-permissions | 学生数据权限 - 个人数据隔离（一人一号） | 学生查询自己数据成功 | 人工复核（确认覆盖） | check_mistake | S1 正常：本人错题列表返回 2 条 |  | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 任课教师不能重置学生密码 | 人工复核（部分覆盖） | check_lessons_2_5 | auth.subject_teacher_reset_denied | 拒绝成立，实际返回 404（隐藏资源存在性），规约写 403 | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师上传资料并布置作业 | 人工复核（部分覆盖） | check_homework | S1 正常：教师创建草稿作业 200 | 布置有断言；上传由 materials.upload_md 另行断言，同一教师链路 | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师不能代替学生发起 AI 提问 | 人工复核（部分覆盖） | check_lesson10_review | 教师不能代替学生发起 AI 提问：教师调用学生提问接口 403 | 拒绝成立；提示文案为「仅学生可执行该操作」，规约写「AI 提问仅限学生发起」 | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师不能查看非任教班级的学生数据 | 人工复核（确认覆盖） | check_analytics | S3 失败：教师跨班访问 → 403 |  | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师仅能访问本学科教研资料 | 人工复核（确认覆盖） | check_research_materials | cross subject read denied |  | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师批改作业并查看本班学生数据 | 人工复核（确认覆盖） | check_quiz_homework | H/教师直接评分并联动错题学情 | 学情计数由 check_analytics S1/U1 交叉断言 | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师查看本班学生 AI 提问历史 | 已知缺口 |  |  | 教师端没有按班级查询 AI 提问历史的接口与页面；学情汇总只有提问数 | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师管理自己任教的班级 | 人工复核（确认覆盖） | check_analytics | S4 正常：任教范围内班级可查 |  | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师重置本班学生密码 | 人工复核（确认覆盖） | check_lessons_2_5 | auth.homeroom_reset |  | 0 |
| rbac-role-permissions | 教师功能权限矩阵 | 班主任跨学科查看本班学情 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 |  | 6 |
| rbac-role-permissions | 教师多班级操作校验 | 多班级选择器展示所有任教班级 | 人工复核（确认覆盖） | check_teacher_navigation | 多班级选择器展示所有任教班级：选择器值来自任教班级列表 | 接口返回全部任教班级另由 check_lesson10_review 断言 | 0 |
| rbac-role-permissions | 教师多班级操作校验 | 教师选择任教班级操作成功 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.upload_md |  | 0 |
| rbac-role-permissions | 教师多班级操作校验 | 教师选择非任教班级操作被拒 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.cross_class_upload_denied |  | 0 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 后端不信任请求体中的 class_id | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 6 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师查询任教班级数据成功 | 人工复核（确认覆盖） | check_analytics | S4 正常：任教范围内班级可查 |  | 0 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师查询非任教班级数据被拒 | 人工复核（确认覆盖） | check_analytics | S3 失败：教师跨班访问 → 403 |  | 0 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师跨班操作被拒 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.cross_class_upload_denied |  | 0 |
| rbac-role-permissions | 权限变更生效机制 | Refresh Token 刷新后新权限生效 | 断言名候选 | check_lessons_2_5 | auth.refresh_cookie_httponly |  | 6 |
| rbac-role-permissions | 权限变更生效机制 | 未刷新前旧权限仍有效 | 人工复核（确认覆盖） | check_lesson10_review | 未刷新前旧权限仍有效：旧令牌按旧任教班级校验，重新登录后生效 |  | 0 |
| rbac-role-permissions | 权限变更生效机制 | 重新登录后新权限生效 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：权限从数据库实时读取（populate_existing=True） |  | 1 |
| rbac-role-permissions | 越权处理与审计日志 | 前端越权跳转 403 页面 | 断言名候选 | check_route_guard | 前端越权跳转 403 页面：已就绪页面角色变化时先隐藏业务 |  | 10 |
| rbac-role-permissions | 越权处理与审计日志 | 后端越权返回 403 并记录审计日志 | 人工复核（确认覆盖） | check_baseline | R2 失败：403 访问日志 status=403 且标识一致 | 响应 403 与审计字段同文件 | 0 |
| rbac-role-permissions | 越权处理与审计日志 | 审计日志异步写入不影响响应性能 | 人工复核（确认覆盖） | check_security_gate | R2 审计异步：401响应正文发出后再写入 |  | 0 |
| rbac-role-permissions | 越权处理与审计日志 | 技能审计字段查询与范围 | 别名候选 | check_lessons_2_5 | auth.audit_logs_query |  | 1 |
| rbac-role-permissions | 越权处理与审计日志 | 教师跨班操作记录审计日志 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 2 |
| rbac-role-permissions | 越权处理与审计日志 | 未登录请求留匿名审计 | 人工复核（确认覆盖） | check_lesson10_review | 未登录请求留匿名审计：401 落库 user_id 为空且 action 可识别 |  | 0 |
| research-materials | 原班级直传入口阻止明显教师版 | 完整教师 Markdown 误传班级 | 人工复核（确认覆盖） | check_research_materials | legacy class upload rejects teacher answer content | 教师版文件名同样被拒，同文件断言 | 0 |
| research-materials | 发布时生成知识点标签 | 标题未包含已知知识点 | 语义别名候选 | check_research_materials | unknown topic does not guess label |  | 1 |
| research-materials | 发布时生成知识点标签 | 立体几何章节带知识点标签 | 人工复核（确认覆盖） | check_research_materials | geometry chapter creates knowledge topic |  | 0 |
| research-materials | 学生版按任教班级独立发布 | 发布学生讲义到两个任教班级 | 语义别名候选 | check_research_materials | authorized multi class batch succeeds |  | 1 |
| research-materials | 学生版按任教班级独立发布 | 越权班级混入发布批次 | 语义别名候选 | check_research_materials | mixed unauthorized classes entire request denied |  | 1 |
| research-materials | 学生版题干提取与教师核对 | 现有结构化讲义生成学生版 | 语义别名候选 | check_research_materials | student preview generated |  | 1 |
| research-materials | 学生版题干提取与教师核对 | 编辑后重新核对 | 语义别名候选 | check_research_materials | publication requires review |  | 1 |
| research-materials | 学生讲义打印与另存 PDF | 学生保存图文讲义 | 语义别名候选 | check_research_materials | student bundle contains only student md and original figure |  | 1 |
| research-materials | 学生讲义打印与另存 PDF | 教师打印未发布的学生预览 | 语义别名候选 | check_research_materials | publication requires review |  | 1 |
| research-materials | 学生讲义打印与另存 PDF | 配图尚未就绪 | N/A（不适用） |  | 前端配图加载态，属界面展示 |  | 0 |
| research-materials | 教师资料先导入学科组 | 图片没有随 Markdown 导入 | 人工复核（确认覆盖） | check_research_materials | invalid import bad.md | 缺图 Markdown 返回 400 且不落库 | 0 |
| research-materials | 教师资料先导入学科组 | 导入完善版图文资料包 | 语义别名候选 | check_research_materials | import teacher package |  | 1 |
| research-materials | 班级配图与图文包受权访问 | 删除班级讲义 | 语义别名候选 | check_research_materials | delete student publication |  | 1 |
| research-materials | 班级配图与图文包受权访问 | 学生预览和下载有图讲义 | 语义别名候选 | check_research_materials | student bundle contains only student md and original figure |  | 1 |
| research-materials | 组内共享教案查阅与复用 | 下载教师图文包 | 语义别名候选 | check_lesson_prep | shared teacher bundle includes snapshot and used original figure |  | 1 |
| research-materials | 组内共享教案查阅与复用 | 同科同事复用共享教案 | 语义别名候选 | check_lesson_prep | same subject colleague sees full teacher snapshot |  | 1 |
| research-materials | 组内共享教案查阅与复用 | 绕过学生稿制作 | 语义别名候选 | check_lesson_prep | shared teacher plan cannot bypass student workflow |  | 1 |
| research-materials | 组内教师共享与学生隔离 | 同科同事选用素材 | 语义别名候选 | check_research_materials | same subject colleagues share source |  | 1 |
| research-materials | 组内教师共享与学生隔离 | 学生直接猜测教师原稿地址 | 语义别名候选 | check_research_materials | student source read denied |  | 1 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | Windows 共享目录运行小组服务 | 人工复核（部分覆盖） | check_sqlite_storage | {mode} journal active | DELETE 模式并发提交/持久化/完整性已断言；未在真实 Windows 共享目录运行 | 0 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | 使用原生磁盘的 WAL 配置 | 人工复核（确认覆盖） | check_sqlite_storage | {mode} journal active | WAL 同步级别、并行提交与完整性同文件断言 | 0 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | 无效日志模式 | 人工复核（确认覆盖） | check_sqlite_storage | unsafe journal rejected |  | 0 |
| runtime-reliability | 存储修复保留业务数据 | 会话接口磁盘 I/O 故障修复 | 语义别名候选 | check_assignment_history | H3 失败：历史依赖故障503 |  | 1 |
| runtime-reliability | 数据库可读性纳入健康检查 | 数据库存储异常 | 人工复核（确认覆盖） | check_baseline | R1 失败：数据库异常 → 503 与通用提示 |  | 0 |
| runtime-reliability | 数据库可读性纳入健康检查 | 数据库读取正常 | 人工复核（确认覆盖） | check_baseline | R1 正常：三项依赖为 ok/ok/configured | 健康检查不写业务记录同文件 | 0 |
| smart-lesson-prep | 两种学生文稿分班发布 | 发布批次混入其他班 | 语义别名候选 | check_lesson_prep | mixed unauthorized publication denied |  | 1 |
| smart-lesson-prep | 两种学生文稿分班发布 | 教案和讲义均发布给学生 | 语义别名候选 | check_lesson_prep | handout publishes both classes with index |  | 1 |
| smart-lesson-prep | 两种学生文稿分班发布 | 新修订尝试发布旧学生稿 | 人工复核（确认覆盖） | check_lesson_prep | new final cannot publish old student drafts |  | 0 |
| smart-lesson-prep | 中文空格图片路径兼容 | 原题图的中文目录含空格 | 语义别名候选 | check_lesson_prep | teacher generation fixes raw spaced image destinations |  | 1 |
| smart-lesson-prep | 中文空格图片路径兼容 | 生成与发布图文包 | 语义别名候选 | check_lesson_prep | handout publishes both classes with index |  | 1 |
| smart-lesson-prep | 从学科组教师资料发起备课 | 尚未提供学情 | 语义别名候选 | check_lesson_prep | selected class context and manual profile passed |  | 1 |
| smart-lesson-prep | 从学科组教师资料发起备课 | 数学教师发起线面角备课 | 人工复核（确认覆盖） | check_lesson_prep | teacher draft saved with actual stream | 出处摘录与行号可追溯同文件 | 0 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿中的单反斜杠公式被修补 | 断言名候选 | check_lesson_prep | 单反斜杠学生稿：修补次数写入服务端日志且不含正文 |  | 6 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿含漏网控制字符 | 人工复核（确认覆盖） | check_lesson_prep | 学生稿含 U+000C：返回 error | 旧稿保持不变与手工编辑同样拒绝同组 | 0 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿生成未通过检查 | 语义别名候选 | check_lesson_prep | broken student response gives error |  | 1 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 教师生成并修改学生讲义 | 人工复核（确认覆盖） | check_lesson_prep | edit saved and remains draft | 学生稿生成/保存同文件 | 0 |
| smart-lesson-prep | 完整片段与出处核对 | 多份资料均被选入 | 语义别名候选 | check_lesson_prep | all selected sources contribute complete sections |  | 1 |
| smart-lesson-prep | 完整片段与出处核对 | 核对例题出处 | 语义别名候选 | check_lesson_prep | reference excerpts exact and lines traceable |  | 1 |
| smart-lesson-prep | 定稿快照与并发保护 | 旧窗口写入 | 语义别名候选 | check_lesson_prep | stale window cannot overwrite |  | 1 |
| smart-lesson-prep | 定稿快照与并发保护 | 第二次定稿 | 语义别名候选 | check_lesson_prep | new final retains v1 and v2 |  | 1 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 主动共享完整教师定稿 | 语义别名候选 | check_lesson_prep | explicitly share current final |  | 1 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 删除私人原教案 | 语义别名候选 | check_lesson_prep | shared final remains readable after deleting private original |  | 1 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 教师选择保留私有 | 语义别名候选 | check_lesson_prep | default private plan has no group publication |  | 1 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 重复发布或后续修改 | 语义别名候选 | check_lesson_prep | same final share is idempotent |  | 1 |
| smart-lesson-prep | 教案隔离删除与审计 | 删除私人教案 | 语义别名候选 | check_lesson_prep | delete owned plan |  | 1 |
| smart-lesson-prep | 教案隔离删除与审计 | 同学科同事访问私人教案 | 语义别名候选 | check_lesson_prep | same subject colleague private plan denied |  | 1 |
| smart-lesson-prep | 流式生成与失败处理 | AI 完成教师草案 | 语义别名候选 | check_lesson_prep | teacher draft saved with actual stream |  | 1 |
| smart-lesson-prep | 流式生成与失败处理 | 生成中断或无 Key | 语义别名候选 | check_lesson_prep | AI error produces error event |  | 1 |
| smart-lesson-prep | 编辑审阅与章节重写 | 审阅后再改正文 | 语义别名候选 | check_lesson_prep | edit saved and remains draft |  | 1 |
| smart-lesson-prep | 编辑审阅与章节重写 | 重写教学过程 | 语义别名候选 | check_lesson_prep | section rewrite changes only selected block |  | 1 |
| smart-question-generation | 候选题逐题复核 | 修改后通过 | 人工复核（确认覆盖） | check_question_bank | 补齐括号后保存并通过：进入题库且标记已修改 |  | 0 |
| smart-question-generation | 候选题逐题复核 | 未确认即通过 | 人工复核（确认覆盖） | check_question_bank | 未确认即通过 400 |  | 0 |
| smart-question-generation | 候选题逐题复核 | 重复题目 | 人工复核（确认覆盖） | check_question_bank | 重复题干通过 409 |  | 0 |
| smart-question-generation | 候选题逐题复核 | 驳回后尝试通过 | 人工复核（确认覆盖） | check_question_bank | 驳回后通过 409 |  | 0 |
| smart-question-generation | 公式结构校验 | 修改时引入不配对括号 | 断言名候选 | check_question_bank | 修改引入不配对括号：400 且题目与 revision 不变 |  | 7 |
| smart-question-generation | 公式结构校验 | 修改补齐括号后通过 | 断言名候选 | check_question_bank | 补齐括号后保存并通过：进入题库且标记已修改 |  | 6 |
| smart-question-generation | 公式结构校验 | 定界符不成对 | 人工复核（确认覆盖） | check_question_bank | 公式结构：转义、cases 与定界符正反用例 |  | 0 |
| smart-question-generation | 公式结构校验 | 转义括号与环境不被误判 | 语义别名候选 | check_question_bank | 公式结构：转义、cases 与定界符正反用例 |  | 1 |
| smart-question-generation | 公式结构校验 | 转义的美元符号 | 语义别名候选 | check_question_bank | 单反斜杠 LaTeX：题干还原为 LaTeX 命令 |  | 1 |
| smart-question-generation | 公式结构校验 | 选项缺右括号 | 语义别名候选 | check_question_bank | 修改引入不配对括号：400 且题目与 revision 不变 |  | 1 |
| smart-question-generation | 发起命题生成 | 使用词表外的知识点 | 人工复核（确认覆盖） | check_question_bank | 词表外知识点 400 |  | 0 |
| smart-question-generation | 发起命题生成 | 数学教师按配比发起命题 | 人工复核（确认覆盖） | check_question_bank | 全部通过 8 题落库 | 按数学学科组织上下文 | 0 |
| smart-question-generation | 发起命题生成 | 选用他科资料 | 人工复核（确认覆盖） | check_question_bank | 选用他科资料 404 |  | 0 |
| smart-question-generation | 发起命题生成 | 配比不一致或越界 | 人工复核（确认覆盖） | check_question_bank | 题型/难度合计不等 400 | 另断言总题数 0/21 与单题型 11 | 0 |
| smart-question-generation | 命题审计记录 | 作业发布审计 | 人工复核（确认覆盖） | check_quiz_homework | Q/作业发布审计 |  | 0 |
| smart-question-generation | 命题审计记录 | 删除候选题后追溯 | 断言名候选 | check_question_bank | 删除候选题后追溯 |  | 7 |
| smart-question-generation | 命题审计记录 | 查看入库题目的复核历史 | 断言名候选 | check_question_bank | 查看入库题目的复核历史 |  | 10 |
| smart-question-generation | 命题接口文档与验收脚本 | 无 Key 环境运行验收脚本 | 人工复核（部分覆盖） | check_question_bank | 无 Key 环境运行验收脚本：虚构模型完成生成且无外部模型请求 | 脚本以占位 test-key 启动并替换 stream_chat；未验证完全不设置环境变量的路径 | 0 |
| smart-question-generation | 命题范围隔离 | 同科同事读取他人候选题 | 断言名候选 | check_question_bank | 同科同事读取他人候选题 404 |  | 10 |
| smart-question-generation | 命题范围隔离 | 学生调用命题接口 | 人工复核（确认覆盖） | check_question_bank | 学生访问题库 403 |  | 0 |
| smart-question-generation | 命题范围隔离 | 物理教师读取数学题目 | 人工复核（确认覆盖） | check_question_bank | 跨学科读取题目 404 |  | 0 |
| smart-question-generation | 学生卷选项排版 | 学生端打开新发布的试卷 | 人工复核（确认覆盖） | check_question_bank | 学生卷选择题：A–D 每项一行且行尾硬换行 | 不含答案/解析/S 编号同组 | 0 |
| smart-question-generation | 学生卷选项排版 | 已发布资料不被改写 | 人工复核（确认覆盖） | check_quiz_homework | Q/已发布资料不被改写 |  | 0 |
| smart-question-generation | 学生卷选项排版 | 第 10 题以后 | 人工复核（确认覆盖） | check_quiz_homework | H/题面显示一致 | 学生卷 10.–12. 选项仍在题下 | 0 |
| smart-question-generation | 学生卷选项排版 | 选项各占一行 | 语义别名候选 | check_question_bank | 学生卷选择题：A–D 每项一行且行尾硬换行 |  | 1 |
| smart-question-generation | 学生卷选项排版 | 选项含块级公式 | 语义别名候选 | check_question_bank | 学生卷第 10 题：选项缩进 4 格 |  | 1 |
| smart-question-generation | 学科题库 | 下架后组卷 | 人工复核（确认覆盖） | check_lesson10_scenario_gaps | 下架后组卷：下架题不进入新试卷且返回缺口、不创建试卷 |  | 0 |
| smart-question-generation | 学科题库 | 修改入库题目 | 人工复核（确认覆盖） | check_question_bank | 入库题目修改 409 |  | 0 |
| smart-question-generation | 学科题库 | 同科同事浏览题库 | 人工复核（确认覆盖） | check_question_bank | 同科同事可见题库 |  | 0 |
| smart-question-generation | 按配比组卷 | 手工替换为下架题 | 断言名候选 | check_lesson10_scenario_gaps | 手工替换为下架题：返回 400 且草稿题数与版本不变 |  | 7 |
| smart-question-generation | 按配比组卷 | 按 3:5:2 组卷 | 人工复核（确认覆盖） | check_question_bank | 组卷 13 题 | 总分 80 同组断言 | 0 |
| smart-question-generation | 按配比组卷 | 题库不足 | 人工复核（确认覆盖） | check_question_bank | 题库不足 422 并列出缺口 |  | 0 |
| smart-question-generation | 来源片段与出处快照 | 原稿在入库后被替换 | 人工复核（确认覆盖） | check_lesson10_review | 原稿在入库后被替换：指纹变化标记 changed、缺失标记 deleted |  | 0 |
| smart-question-generation | 来源片段与出处快照 | 查看题目出处 | 人工复核（确认覆盖） | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | S 编号与资料名同组 | 0 |
| smart-question-generation | 流式进度与失败处理 | 同一教师重复点击生成 | 人工复核（确认覆盖） | check_question_bank | 登记未过期：再次生成 409 |  | 0 |
| smart-question-generation | 流式进度与失败处理 | 未配置模型 Key | 人工复核（确认覆盖） | check_question_bank | 无 Key 返回 503 |  | 0 |
| smart-question-generation | 流式进度与失败处理 | 生成中模型超时 | 语义别名候选 | check_question_bank | 截断输出：返回 error 且不落题 |  | 1 |
| smart-question-generation | 结构化输出与逐题校验 | 修补后仍不是合法 JSON | 人工复核（确认覆盖） | check_question_bank | 截断输出：失败原因含第 12 行与列号 | 不含模型原文同组 | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 全部题目通过校验 | 人工复核（确认覆盖） | check_question_bank | 全部通过 8 题落库 |  | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 单反斜杠 LaTeX 被修补后通过 | 断言名候选 | check_question_bank | 单反斜杠 LaTeX：生成成功且题目保存 |  | 8 |
| smart-question-generation | 结构化输出与逐题校验 | 模型声明无依据的空位 | 语义别名候选 | check_question_bank | validate_batch 遇到任意结构不抛异常、逐题拒绝 |  | 1 |
| smart-question-generation | 结构化输出与逐题校验 | 模型返回不构成字面包含的细分说法 | 断言名候选 | check_question_bank | 非字面包含的细分术语：判超出范围 |  | 6 |
| smart-question-generation | 结构化输出与逐题校验 | 模型返回字面包含所选标签的表述 | 人工复核（确认覆盖） | check_question_bank | 细分知识点：落库知识点为所选标签 |  | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 漏网的控制字符被拦截 | 人工复核（确认覆盖） | check_question_bank | U+000C 题干：原因为含不可见控制字符 |  | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 细分知识点与所选知识点无关 | 断言名候选 | check_question_bank | 细分知识点：归一到所选知识点后通过 |  | 6 |
| smart-question-generation | 结构化输出与逐题校验 | 被误解码的公式命令被修补 | 人工复核（确认覆盖） | check_question_bank | 单反斜杠 LaTeX：generate 事件记录 escape_repairs=13 |  | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 输出不是 JSON | 人工复核（确认覆盖） | check_question_bank | 非 JSON 返回 error | 不保存题目与写失败记录同组 | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 部分题目不合格 | 人工复核（确认覆盖） | check_question_bank | 部分不合格：6 通过 2 未通过 |  | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 题干泄露答案 | 语义别名候选 | check_question_bank | 学生卷不含答案/解析/S编号 |  | 1 |
| smart-question-generation | 试卷定稿与分班发布 | 原图校验或文件写入失败 | 人工复核（确认覆盖） | check_quiz_homework | Q/原图校验或文件写入失败：数据库整批回滚 | 文件整批回滚与指纹 409 同组 | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 发布到两个任教班级 | 人工复核（确认覆盖） | check_question_bank | 发布到两个班 200 |  | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 发布参数边界 | 语义别名候选 | check_quiz_homework | Q/发布参数边界：缺少截止时间 |  | 1 |
| smart-question-generation | 试卷定稿与分班发布 | 发布身份边界 | 语义别名候选 | check_quiz_homework | Q/发布身份边界： |  | 1 |
| smart-question-generation | 试卷定稿与分班发布 | 批次混入非任教班级 | 断言名候选 | check_question_bank | 批次混入非任教班级 403 |  | 8 |
| smart-question-generation | 试卷定稿与分班发布 | 未确认核对或版本冲突 | 人工复核（确认覆盖） | check_question_bank | 未确认核对 400 |  | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 混合已有和新目标班级 | 语义别名候选 | check_quiz_homework | Q/混合已有和新目标班级 |  | 1 |
| smart-question-generation | 试卷定稿与分班发布 | 草稿试卷发布 | 人工复核（确认覆盖） | check_question_bank | 草稿发布 409 |  | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 重复发布 | 人工复核（确认覆盖） | check_question_bank | 重复发布复用作业 |  | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 重复发布更换截止时间或遇到已关闭作业 | 人工复核（确认覆盖） | check_quiz_homework | Q/重复发布更换截止时间或遇到已关闭作业：截止时间冲突 | 已关闭 409 同组 | 0 |
| smart-question-generation | 题目内容显示 | 代码中的下划线 | 断言名候选 | check_markdown_blanks | 代码中的下划线：正文填空空位转义为字面下划线 |  | 6 |
| smart-question-generation | 题目内容显示 | 填空与解答题答案含公式 | 人工复核（确认覆盖） | check_question_rendering | 填空与解答题答案含公式：答案以 KaTeX 渲染且无 katex-error |  | 0 |
| smart-question-generation | 题目内容显示 | 多空位填空题显示 | 人工复核（确认覆盖） | check_question_rendering | 多空位填空题显示：三个空位保留且无加粗斜体 |  | 0 |
| smart-question-generation | 题目内容显示 | 多空答案与选择判断答案 | 人工复核（确认覆盖） | check_question_bank | 答案卷含答案与解析 |  | 0 |
| smart-question-generation | 题目内容显示 | 学生端打开已发布试卷 | 人工复核（部分覆盖） | check_question_rendering | 学生端打开已发布试卷：多空位题干渲染后空位与发布时一致 | 交作业与历史资料两种入口未逐一走浏览器，共用同一渲染组件 | 0 |
| smart-question-generation | 题目内容显示 | 空位与公式下标共存 | 语义别名候选 | check_question_bank | 公式结构：转义、cases 与定界符正反用例 |  | 1 |
| smart-question-generation | 题目内容显示 | 编辑答案时显示原文 | 人工复核（确认覆盖） | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | 出处快照与编辑原文一致 | 0 |
| smart-question-generation | 题目内容显示 | 解答题作答横线不变 | 人工复核（确认覆盖） | check_question_rendering | 解答题作答横线不变：整行下划线渲染为分隔线而非文字 |  | 0 |
| smart-question-generation | 题目内容显示 | 选项含公式 | 语义别名候选 | check_question_bank | 单反斜杠 LaTeX：选项与解析同样还原 |  | 1 |
| student-workspace | 作业界面先展示演示结果 | 浏览演示作业结果 | N/A（不适用） |  | 前端演示结果展示，属界面展示 |  | 0 |
| student-workspace | 助手对话保留真实会话能力 | 从助手页连续追问 | 语义别名候选 | check_lessons_2_5 | agent.multiturn_context |  | 1 |
| student-workspace | 助手对话保留真实会话能力 | 查看回答来源 | 语义别名候选 | check_lessons_2_5 | agent.citations_provenance |  | 1 |
| student-workspace | 学情分析演示界面 | 浏览学习画像演示 | N/A（不适用） |  | 前端画像展示，属界面展示 |  | 0 |
| student-workspace | 学生作业历史持续可查 | H1 提交后进入历史并可刷新 | 语义别名候选 | check_assignment_history | H1 正常：提交后历史输入与时间持久返回 |  | 1 |
| student-workspace | 学生作业历史持续可查 | H2 关闭后保留终评及配图 | 人工复核（确认覆盖） | check_assignment_history | H2 正常：关闭后保留100分作答与评语 | 配图可读与不可重交同组 | 0 |
| student-workspace | 学生作业历史持续可查 | H3 历史读取隔离与失败 | 语义别名候选 | check_assignment_history | H3 失败：他人提交不可读 |  | 1 |
| student-workspace | 学生作业历史持续可查 | H4 空历史与时间边界 | 断言名候选 | check_lesson10_scenario_gaps | H4 空历史与时间边界：无历史学生返回空列表，逾期未交在历史且标记已截止 |  | 9 |
| student-workspace | 学生导航与路由 | 无效视图回退 | N/A（不适用） |  | 前端路由回退，属界面行为 |  | 0 |
| student-workspace | 学生导航与路由 | 资料页返回其他模块 | N/A（不适用） |  | 前端导航交互，属界面行为 |  | 0 |
| student-workspace | 学生导航与路由 | 首页进入助手对话 | N/A（不适用） |  | 前端导航交互，属界面行为 |  | 0 |
| student-workspace | 学生本地搜索与提问历史 | 助手历史不自动发送 | 断言名候选 | check_recent_history | 助手历史不自动发送：历史按钮仅回填并聚焦，渲染时不触发发送，清空只移除快捷记录 |  | 8 |
| student-workspace | 学生本地搜索与提问历史 | 搜索后刷新与再次使用 | 断言名候选 | check_recent_history | 搜索后刷新与再次使用：重复关键词只保留一条、重建存储后可见且点击调用原搜索 |  | 9 |
| student-workspace | 学生本地搜索与提问历史 | 科目和账号隔离 | 断言名候选 | check_recent_history | 科目和账号隔离：不同学生、班级、科目与入口的历史互不可见且原范围可恢复 |  | 6 |
| student-workspace | 学生身份与班级上下文 | 学生首页展示本人班级 | 人工复核（确认覆盖） | check_lesson10_review | 学生首页展示本人班级：班级名取自本人会话且无班级选择器 |  | 0 |
| student-workspace | 学生身份与班级上下文 | 未分班学生访问 | 人工复核（确认覆盖） | check_lesson10_review | 未分班学生访问：空状态且不请求班级资料 | 后端 agent.unassigned_student_denied 另行断言 | 0 |
| student-workspace | 本班讲义列表与检索界面 | 学生搜索本班讲义 | N/A（不适用） |  | 前端本地搜索交互，属界面行为 |  | 0 |
| student-workspace | 本班讲义列表与检索界面 | 学科标签过滤资料卡 | 语义别名候选 | check_lessons_2_5 | materials.math_subject_list |  | 1 |
| student-workspace | 本班讲义列表与检索界面 | 预览和下载实际资料 | 语义别名候选 | check_lessons_2_5 | materials.preview |  | 1 |
| student-workspace | 本班首页概览 | 浏览首页概览 | N/A（不适用） |  | 前端概览浏览，属界面展示 |  | 0 |
| student-workspace | 讲义页科目切换布局稳定 | 从有资料切到空科目 | N/A（不适用） |  | 前端科目切换布局，属界面行为 |  | 0 |
| student-workspace | 讲义页科目切换布局稳定 | 搜索加载与恢复 | N/A（不适用） |  | 前端布局稳定性（同一容器与标题区不随是否渲染卡片变化），属界面布局 |  | 0 |
| student-workspace | 错题界面及助手跳转 | 由错题进入助手 | N/A（不适用） |  | 前端跳转交互，属界面行为 |  | 0 |
| teacher-identity-and-permissions | 双重身份权限判定规则 | 同一教师不同模块权限不同 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：题库/组卷模块校验任教学科（subject），班级模块校验任教班级（teaching_classes） |  | 1 |
| teacher-identity-and-permissions | 学生密码重置仅限本班班主任 | 任课教师调用重置接口被拒 | 人工复核（部分覆盖） | check_lessons_2_5 | auth.subject_teacher_reset_denied | 拒绝成立，实际 404 而非规约写的 403 | 0 |
| teacher-identity-and-permissions | 学生密码重置仅限本班班主任 | 班主任重置本人带班学生密码 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset |  | 2 |
| teacher-identity-and-permissions | 教师学科身份 | 教师学科身份随 JWT 生效 | 人工复核（部分覆盖） | check_lessons_2_5 | agent.teacher_subject_uses_current_database | subject 实际取数据库当前值并覆盖令牌；请求体不声明学科时按服务端身份判定的行为成立 | 0 |
| teacher-identity-and-permissions | 教师学科身份 | 教师登录进入本学科教研组 | 人工复核（确认覆盖） | check_research_materials | same subject colleagues share source |  | 0 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 数学教师访问数学教研资料成功 | 人工复核（确认覆盖） | check_research_materials | same subject colleagues share source |  | 0 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 数学班主任跨学科访问英语资料被拒 | 人工复核（确认覆盖） | check_research_materials | cross subject read denied |  | 0 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 跨学科教研资料不可见 | 人工复核（确认覆盖） | check_research_materials | other subject sees no source |  | 0 |
| teacher-identity-and-permissions | 班主任身份不随工作区消失 | 任课教学保留班主任模块 | 人工复核（确认覆盖） | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 |  | 0 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 任课老师仅看本学科成绩 | 人工复核（确认覆盖） | check_analytics | S1 正常：任课查看 102 数学学情 |  | 0 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 班主任查看其他班级学情被拒 | 人工复核（确认覆盖） | check_analytics | S3 失败：教师跨班访问 → 403 |  | 0 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 班主任查看本班全科学情 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 |  | 9 |
| teacher-identity-and-permissions | 班级管理边界 | 任课老师仅见任教班级名单 | 人工复核（部分覆盖） | check_lessons_2_5 | auth.teacher_cross_class_denied | 越界 403 有断言；名单只含任教班级的完整集合未单独断言 | 0 |
| teacher-identity-and-permissions | 班级管理边界 | 班主任可见本班全部学生 | 人工复核（确认覆盖） | check_analytics | S1 正常：班主任查看本班全科 101 学情 | total_students 计数 | 0 |
| teacher-workspace | 两种学生名单的操作差异 | 同一教师在任课页不展示重置操作 | 人工复核（确认覆盖） | check_lesson10_review | 同一教师在任课页不展示重置操作：操作列与按钮均受班主任身份控制 |  | 0 |
| teacher-workspace | 两种学生名单的操作差异 | 班主任学生页展示重置操作 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset |  | 2 |
| teacher-workspace | 任课与带班上下文独立 | 切换任课班级不切换带班班级 | 人工复核（确认覆盖） | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 | 同一断言验证任课 102 与带班 101 并存 | 0 |
| teacher-workspace | 任课管理的单科资料列表 | 切班后保留资料视图 | 人工复核（确认覆盖） | check_teacher_navigation | R3 正常：切班保留现有页面行为 |  | 0 |
| teacher-workspace | 任课管理的单科资料列表 | 发布与查看入口分开 | 语义别名候选 | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 |  | 1 |
| teacher-workspace | 任课管理的单科资料列表 | 查看当前任教班级本科目资料 | 人工复核（确认覆盖） | check_lessons_2_5 | materials.math_subject_list | 单科列表按 subject_only=true 断言 | 0 |
| teacher-workspace | 全科总览与单科教学入口区分 | 在教研组内选择教师版发布学生稿 | 语义别名候选 | check_lesson_prep | shared teacher plan cannot use simple student stripping |  | 1 |
| teacher-workspace | 全科总览与单科教学入口区分 | 打开未接入的学情或教研模块 | 语义别名候选 | check_teacher_navigation | R1 边界：没有任教班级仍只有三项教研入口 |  | 1 |
| teacher-workspace | 全科总览与单科教学入口区分 | 智能命题不再是占位 | 人工复核（确认覆盖） | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 | 命题入口指向 /teacher/quiz | 0 |
| teacher-workspace | 全科总览与单科教学入口区分 | 班主任进入全科资料总览 | 人工复核（部分覆盖） | check_teacher_navigation | R1 正常： | 班主任工作台含「本班资料（全科）」入口；「总览不提供上传/删除」无直接断言 | 0 |
| teacher-workspace | 助手配置独立入口及菜单顺序 | 在助手配置页切换班级 | 人工复核（部分覆盖） | check_lessons_2_5 | agent.class_switch_reads_and_saves_target | 切到 102 后读取/保存以 102 为目标且不影响 101 有断言；「保留配置视图」属前端行为 | 0 |
| teacher-workspace | 助手配置独立入口及菜单顺序 | 检查系统菜单顺序 | 语义别名候选 | check_teacher_navigation | R1 边界：没有任教班级仍只有三项教研入口 |  | 1 |
| teacher-workspace | 教师共用工作空间导航 | 教师打开资料页仍可访问其他模块 | 人工复核（确认覆盖） | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 | 共用导航在 /teacher/library、/upload、/materials 均断言 | 0 |
| teacher-workspace | 教师共用工作空间导航 | 教师进入智能命题页 | 语义别名候选 | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 |  | 1 |
| teacher-workspace | 教师教研占位入口移除 | R1 教研中心只有三个现有入口 | 人工复核（确认覆盖） | check_teacher_navigation | R1 正常： | 六条路由 × 有/无带班逐项断言 | 0 |
| teacher-workspace | 教师教研占位入口移除 | R2 旧教研链接有明确落点 | 语义别名候选 | check_teacher_navigation | R2 失败路径：旧${old} / ${workspace} / ${classId}归一到既有备课跳转 |  | 1 |
| teacher-workspace | 教师教研占位入口移除 | R3 其他导航与班级不退化 | 人工复核（确认覆盖） | check_teacher_navigation | R3 边界：其他view保持原值 |  | 0 |
| teacher-workspace | 教师页移除快捷切换账号 | 教师检查顶栏 | 语义别名候选 | check_teacher_navigation | R3 正常：切班保留现有页面行为 |  | 1 |
| teacher-workspace | 本地预览包含静态资源 | standalone 服务交付登录样式 | 断言名候选 | check_lessons_2_5 | citations.changed_file_stale_index_excluded |  | 6 |
| teacher-workspace | 本班审计日志页面与接口 | 任课身份或跨班审计被拒绝 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation |  | 2 |
| teacher-workspace | 本班审计日志页面与接口 | 班主任查看本班日志 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 |  | 6 |
| teacher-workspace | 班主任模块按身份常驻 | 任课教学保留班主任入口 | 人工复核（确认覆盖） | check_teacher_navigation | 任课教学保留班主任模块：切到 102 仍显示带班 101 入口 |  | 0 |
| teacher-workspace | 班主任模块按身份常驻 | 非班主任只显示任课与教研功能 | 人工复核（确认覆盖） | check_teacher_navigation | 非班主任只显示任课与教研功能：无班主任工作台，保留任课/教研/助手配置 |  | 0 |
