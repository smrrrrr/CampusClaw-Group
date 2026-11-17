"""第10课场景逐条映射：为每条主规约 Scenario 给出最具体的候选断言与缺口等级。

与 lesson10_matrix.py 的区别：不按"≥4 个二元组"一刀切，而是对每条 Scenario
都给出同能力检查文件中的最佳断言候选与重叠度，并按强度分档，便于人工逐条复核。
脚本只产出候选，不宣称覆盖；人工复核结论必须另填。

用法：
    backend/.venv/bin/python scripts/lesson10_scenario_map.py --out reports/scenario-coverage.md
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "openspec/specs"
OUT_DEFAULT = ROOT / "reports/scenario-coverage.md"

CAPABILITY_CHECKS = {
    "agent-assistant": ["check_lessons_2_5", "check_recent_history", "check_mcp_tools", "check_lesson10_skills",
                        "check_lesson10_scenario_gaps"],
    "async-homework-grading": ["check_async_grading", "check_homework", "check_quiz_homework"],
    "class-data-isolation": ["check_baseline", "check_injection", "check_lessons_2_5",
                             "check_lesson10_p0_scenarios"],
    "login-and-account-system": ["check_baseline", "check_route_guard", "check_security_gate",
                                 "check_lesson10_scenarios", "check_lesson10_p0_scenarios"],
    "material-upload": ["check_markdown_images", "check_lesson_prep", "check_research_materials",
                        "check_lessons_2_5", "check_lesson10_p0_scenarios",
                        "check_lesson10_scenario_gaps"],
    "mcp-tool-integration": ["check_mcp_tools", "check_security_gate", "check_mcp_server",
                              "check_lesson10_scenario_gaps"],
    "quiz-homework-publication": ["check_quiz_homework", "check_question_bank"],
    "rag-search": ["check_formula_retrieval", "check_lessons_2_5", "check_lesson10_skills",
                    "check_lesson10_scenarios", "check_lesson10_p0_scenarios"],
    "rbac-role-permissions": ["check_injection", "check_baseline", "check_security_gate",
                              "check_route_guard", "check_lessons_2_5", "check_analytics", "check_homework",
                              "check_lesson10_scenarios", "check_lesson10_p0_scenarios"],
    "research-materials": ["check_research_materials"],
    "runtime-reliability": ["check_baseline", "check_sqlite_storage", "check_lesson10_ops",
                            "check_lesson10_p0_scenarios"],
    "smart-lesson-prep": ["check_lesson_prep"],
    "smart-question-generation": ["check_question_bank", "check_lesson10_scenario_gaps", "check_markdown_blanks"],
    "student-workspace": ["check_recent_history", "check_homework", "check_lessons_2_5", "check_analytics",
                          "check_lesson10_scenario_gaps"],
    "teacher-identity-and-permissions": ["check_baseline", "check_security_gate", "check_lessons_2_5",
                                        "check_analytics", "check_lesson10_p0_scenarios"],
    "teacher-workspace": ["check_teacher_navigation", "check_assignment_history_ui", "check_analytics",
                          "check_lessons_2_5", "check_lesson10_p0_scenarios"],
}

HIGH_RISK_CAPABILITIES = {
    "class-data-isolation", "rbac-role-permissions", "login-and-account-system",
    "teacher-identity-and-permissions", "rag-search",
}

# 人工建立的等价映射初稿：Scenario 标题用词与断言名差异较大，但语义指向同一检查。
# 前三元组用于匹配（全部关键词出现），后两项是证据。仍需人工复核确认断言强度。
ALIASES = [
    (("学生", "其他班级", "资料", "被拒"), "check_lessons_2_5", "materials.subject_list_cross_class_denied"),
    (("教师", "非任教班级", "资料"), "check_lessons_2_5", "auth.teacher_cross_class_denied"),
    (("教师", "跨班", "布置"), "check_homework", "S1 失败：非任教班级布置 → 403"),
    (("学生", "提交", "本班"), "check_homework", "S3 正常：学生提交成功"),
    (("班级资料", "严格隔离"), "check_lessons_2_5", "materials.cross_class_download_denied"),
    (("学生", "登录", "本人班级"), "check_lessons_2_5", "auth.refresh_restores_full_user"),
    (("一人一号",), "check_lessons_2_5", "auth.csv_cannot_claim_other_student"),
    (("学生", "首次登录", "改密"), "check_lessons_2_5", "auth.first_password_blocks_business"),
    (("未改初始密码",), "check_lessons_2_5", "auth.first_password_blocks_business"),
    (("五次", "锁定"), "check_lessons_2_5", "auth.five_failures_lock"),
    (("连续5次", "锁定"), "check_lessons_2_5", "auth.five_failures_lock"),
    (("锁定期间",), "check_lessons_2_5", "auth.five_failures_lock"),
    (("锁定过期",), "check_lessons_2_5", "auth.five_failures_lock"),
    (("班主任", "重置"), "check_lessons_2_5", "auth.homeroom_reset"),
    (("班主任", "重置", "本班"), "check_lessons_2_5", "auth.homeroom_reset"),
    (("任课", "不能代替", "班主任"), "check_lessons_2_5", "auth.subject_teacher_reset_denied"),
    (("其他班主任", "重置"), "check_lessons_2_5", "auth.other_homeroom_reset_denied"),
    (("重置", "旧令牌"), "check_lessons_2_5", "auth.reset_immediately_blocks_old_token"),
    (("跨班", "下载"), "check_lessons_2_5", "materials.cross_class_download_denied"),
    (("学科", "越权", "资料"), "check_lessons_2_5", "materials.student_subject_scope_denied"),
    (("CSV", "其他班级", "更新"), "check_lessons_2_5", "auth.csv_other_class_update_denied"),
    (("CSV", "其他班级", "创建"), "check_lessons_2_5", "auth.csv_other_class_create_denied"),
    (("关键字检索",), "check_formula_retrieval", "keyword formula recalled despite coordinate distractor"),
    (("向量检索",), "check_formula_retrieval", "vector formula recalled despite coordinate distractor"),
    (("混合检索", "融合"), "check_formula_retrieval", "hybrid formula recalled despite coordinate distractor"),
    (("分块向量化", "存储"), "check_lessons_2_5", "rag.chunks_vectors_persisted"),
    (("无召回", "臆造"), "check_formula_retrieval", "no invented auto reference"),
    (("变更", "索引", "版本"), "check_formula_retrieval", "tampered source excluded"),
    (("无关", "资料"), "check_formula_retrieval", "irrelevant question not forced into chapter"),
    (("摘录", "真实分块"), "check_formula_retrieval", "raw excerpts unchanged"),
    (("引用", "检索一致"), "check_formula_retrieval", "real formula reference retained"),
    (("文件指纹",), "check_formula_retrieval", "source fingerprint exact"),
    (("其他班", "看不到"), "check_homework", "S2 正常：其他班学生看不到"),
    (("跨班", "提交"), "check_homework", "S3 失败：跨班提交 → 404"),
    (("学生", "越权", "发布"), "check_homework", "S1 失败：学生越权发布 → 403"),
    (("未登录", "作业"), "check_quiz_homework", "H/未登录读取作业或配图："),
    (("学生", "跨班", "读取"), "check_quiz_homework", "H/学生跨班读取或提交"),
    (("教师", "学科", "不符"), "check_quiz_homework", "H/教师班级或学科不符："),
    (("评分依据", "泄露"), "check_quiz_homework", "H/学生响应不泄露评分依据"),
    (("登出", "Cookie"), "check_lessons_2_5", "auth.logout_clears_cookie"),
    (("密码", "策略", "拒"), "check_lessons_2_5", "auth.weak_password_denied"),
    (("密码", "长度", "拒"), "check_lessons_2_5", "auth.weak_password_denied"),
    (("审计", "跨班"), "check_lessons_2_5", "auth.audit_logs_class_isolation"),
    (("审计", "其他班"), "check_lessons_2_5", "auth.audit_other_class_denied"),
    (("审计", "任课"), "check_lessons_2_5", "auth.audit_subject_teacher_denied"),
    (("会话", "其他学生"), "check_lessons_2_5", "agent.other_student_conversation_hidden"),
    (("未分配班级", "学生"), "check_lessons_2_5", "agent.unassigned_student_denied"),
    (("引用", "文件变更"), "check_lessons_2_5", "citations.changed_file_stale_index_excluded"),
    (("无效编号",), "check_lessons_2_5", "citations.invalid_number_removed"),
    (("摘录", "真实"), "check_lessons_2_5", "citations.excerpt_is_exact_chunk"),
    (("切换科目",), "check_lessons_2_5", "agent.physics_save_does_not_overwrite_math"),
    (("同科", "教师", "配置"), "check_lessons_2_5", "agent.same_subject_teacher_configs_independent"),
    (("追问", "限次"), "check_lessons_2_5", "agent.spec_40_question_limit"),
    (("多轮", "上下文"), "check_lessons_2_5", "agent.multiturn_context"),
    (("流式",), "check_lessons_2_5", "agent.sse_transport_mock_llm"),
    (("引用", "来源"), "check_lessons_2_5", "agent.citations_provenance"),
    (("失败", "降级"), "check_lessons_2_5", "agent.failure_fallback"),
    (("令牌", "重置", "失效"), "check_lessons_2_5", "auth.reset_immediately_blocks_old_token"),
    (("未登录", "拒绝"), "check_lessons_2_5", "auth.anonymous_denied"),
    (("学生", "教师接口"), "check_lessons_2_5", "auth.student_teacher_api_denied"),
    (("教师", "学生接口"), "check_lessons_2_5", "auth.teacher_student_api_denied"),
    (("CSV", "越权", "回滚"), "check_lessons_2_5", "auth.csv_forbidden_batch_rolled_back"),
    (("合法行", "越权"), "check_lessons_2_5", "auth.csv_forbidden_batch_rolled_back"),
    (("CSV", "任教范围"), "check_lessons_2_5", "auth.csv_assigned_class_allowed"),
    (("CSV", "缺少班级"), "check_lessons_2_5", "auth.csv_missing_class_cannot_bypass"),
    (("上传", "异步", "分块"), "check_lessons_2_5", "rag.chunks_vectors_persisted"),
    (("跨章节", "预筛"), "check_formula_retrieval", "irrelevant question not forced into chapter"),
    (("预筛", "回退"), "check_formula_retrieval", "irrelevant question not forced into chapter"),
    (("严格限定本班",), "check_formula_retrieval", "class and subject retained"),
    (("召回本班",), "check_formula_retrieval", "keyword formula recalled despite coordinate distractor"),
    (("无可用分块", "降级"), "check_formula_retrieval", "no invented auto reference"),
    (("未使用候选",), "check_lessons_2_5", "citations.uncited_candidates_not_attached"),
    (("重新索引",), "check_lessons_2_5", "citations.reindex_restores_verified_sources"),
    (("删除", "分块"), "check_lessons_2_5", "materials.delete_cleans_chunks"),
    (("伪造", "PDF"), "check_lessons_2_5", "materials.forged_pdf_denied"),
    (("学生", "上传"), "check_lessons_2_5", "materials.student_upload_denied"),
    (("跨班", "上传"), "check_lessons_2_5", "materials.cross_class_upload_denied"),
    (("跨班", "列表"), "check_lessons_2_5", "materials.cross_class_list_denied"),
    (("登录", "成功"), "check_lessons_2_5", "auth.login.<角色>（动态断言名）"),
    (("刷新后仍指向本人",), "check_lessons_2_5", "auth.refresh_restores_full_user"),
    (("登出", "重新登录"), "check_lessons_2_5", "auth.refresh_restores_full_user"),
    (("修改个人密码",), "check_lessons_2_5", "auth.change_password"),
    (("符合策略的密码",), "check_lessons_2_5", "auth.change_password"),
    (("审计字段",), "check_lessons_2_5", "auth.audit_logs_query"),
    (("任教范围内创建或更新",), "check_lessons_2_5", "auth.csv_assigned_class_allowed"),
    (("教材标准公式",), "check_formula_retrieval", "real formula reference retained"),
    (("依据不足",), "check_formula_retrieval", "no invented auto reference"),
    (("标注出处",), "check_lessons_2_5", "citations.excerpt_is_exact_chunk"),
    (("答案基于召回",), "check_formula_retrieval", "real formula reference retained"),
    (("解析材料", "多个分块"), "check_lessons_2_5", "rag.chunks_vectors_persisted"),
    (("达到上限", "被拒"), "check_lessons_2_5", "agent.spec_40_question_limit"),
    # 第10课 P0 高风险场景：由 check_lesson10_p0_scenarios 覆盖（离线源码/纯函数断言）
    (("教师未分配任教班级前端展示空状态",), "check_lesson10_p0_scenarios", "P0 前端：教师未分配任教班级时存在空状态提示"),
    (("用户忘记密码看到班主任提示",), "check_lesson10_p0_scenarios", "P0 前端：忘记密码显示「请联系班主任重置」提示"),
    (("公式渲染为数学符号",), "check_lesson10_p0_scenarios", "P0 前端：公式渲染使用 KaTeX 数学符号"),
    (("独立公式居中美化与长公式横向滚动",), "check_lesson10_p0_scenarios", "P0 前端：独立公式居中与长公式横向滚动样式存在"),
    (("多命中逐条展示保留溯源",), "check_lesson10_p0_scenarios", "P0 前端：参考资料独立区域逐条展示并保留溯源"),
    (("无引用时仅显示回答",), "check_lesson10_p0_scenarios", "P0 前端：无引用时仅显示回答（条件渲染）"),
    (("原生磁盘保留 WAL",), "check_lesson10_p0_scenarios", "P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖"),
    (("任课切班不改变带班上下文",), "check_lesson10_p0_scenarios", "P0 接口：任教班级与带班班级均由服务端令牌/数据库派生（不采信客户端参数）"),
    (("学校级公共资源不隔离",), "check_lesson10_p0_scenarios", "P0 接口：学科组素材按学科归属、不绑定班级"),
    (("系统公告不隔离",), "check_lesson10_p0_scenarios", "P0 接口：不存在按班级隔离的系统公告模型（特性未实现，无误隔离）"),
    (("多个学生使用相同联系方式",), "check_lesson10_p0_scenarios", "P0 接口：用户唯一约束仅限 role+identifier，不含 phone（联系方式可重复）"),
    (("向量化失败不阻塞上传",), "check_lesson10_p0_scenarios", "P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功"),
    (("回答与参考资料独立成卡",), "check_lesson10_p0_scenarios", "P0 接口：回答与参考资料在数据模型中分离（citations 独立字段）"),
    (("学生当日提问未达上限",), "check_lesson10_p0_scenarios", "P0 接口：AI 提问每日上限为 40 次"),
    (("次日提问次数重置",), "check_lesson10_p0_scenarios", "P0 接口：提问计数按中国时区自然日重置"),
    (("重新登录后新权限生效",), "check_lesson10_p0_scenarios", "P0 接口：权限从数据库实时读取（populate_existing=True）"),
    (("同一教师不同模块权限不同",), "check_lesson10_p0_scenarios", "P0 接口：题库/组卷模块校验任教学科（subject），班级模块校验任教班级（teaching_classes）"),
]

# ---------------------------------------------------------------------------
# 人工语义映射：中文 Scenario 与既有断言措辞差异大（且多为英文断言名），
# 按 bigram 无法判定覆盖。以下为逐条核对断言实现后建立的人工等价表，
# 命中即记为「别名候选」；仍需人工复核断言强度。
# 结构：(能力或 None, 关键词元组, 断言所在脚本, 断言名)
# ---------------------------------------------------------------------------
SEMANTIC_ALIASES = [
    # agent-assistant
    ("agent-assistant", ("在会话内连续追问",), "check_lessons_2_5", "agent.multiturn_context"),
    ("agent-assistant", ("新建与列出会话",), "check_mcp_tools", "学生建会话"),
    ("agent-assistant", ("多轮会话检索无命中时延续历史",), "check_lessons_2_5", "agent.followup_retrieves_original_topic_with_same_scope"),
    ("agent-assistant", ("回显历史消息",), "check_lessons_2_5", "agent.messages_persist"),
    ("agent-assistant", ("仅带最近若干轮作为上下文",), "check_lessons_2_5", "agent.multiturn_context"),
    ("agent-assistant", ("历史公式代码与实时回答一致",), "check_lessons_2_5", "agent.messages_persist"),
    ("agent-assistant", ("历史消息权限不变",), "check_lessons_2_5", "agent.other_student_conversation_hidden"),
    ("agent-assistant", ("切班回读配置",), "check_lessons_2_5", "agent.config_read"),
    ("agent-assistant", ("以技能文件注册技能",), "check_mcp_tools", "技能保存成功 201"),
    ("agent-assistant", ("没有该科配置",), "check_lessons_2_5", "agent.unconfigured_subject_reports_default"),
    ("agent-assistant", ("查看当前班级参考资料",), "check_lessons_2_5", "agent.citations_provenance"),
    ("agent-assistant", ("换题或无题目锚点",), "check_lessons_2_5", "agent.followup_without_anchor_unchanged"),
    ("agent-assistant", ("历史未标注来源的回答",), "check_lessons_2_5", "citations.no_context_cannot_cite_history"),
    # material-upload
    ("material-upload", ("教师上传资料成功",), "check_lessons_2_5", "materials.upload_md"),
    ("material-upload", ("上传允许格式的文件成功",), "check_lessons_2_5", "materials.upload_md"),
    ("material-upload", ("上传不允许的格式被拒",), "check_lessons_2_5", "materials.forged_pdf_denied"),
    ("material-upload", ("伪造扩展名",), "check_lessons_2_5", "materials.forged_pdf_denied"),
    ("material-upload", ("恶意文件头校验不通过被拒",), "check_lessons_2_5", "materials.forged_pdf_denied"),
    ("material-upload", ("教师选择任教班级上传成功",), "check_lessons_2_5", "materials.upload_md"),
    ("material-upload", ("上传元数据完整记录",), "check_lessons_2_5", "materials.upload_md"),
    ("material-upload", ("上传成功后异步解析为纯文本",), "check_lessons_2_5", "rag.chunks_vectors_persisted"),
    ("material-upload", ("学生查询本班材料成功",), "check_lessons_2_5", "materials.math_subject_list"),
    ("material-upload", ("教师查询任教班级材料成功",), "check_lessons_2_5", "materials.math_subject_list"),
    ("material-upload", ("学生尝试下载其他班材料被拒",), "check_lessons_2_5", "materials.cross_class_download_denied"),
    ("material-upload", ("引用原文的文件版本已变化",), "check_lessons_2_5", "citations.changed_file_stale_index_excluded"),
    ("material-upload", ("学生在线预览 PDF 成功",), "check_lessons_2_5", "materials.preview"),
    ("material-upload", ("学生在线预览图片成功",), "check_lessons_2_5", "materials.preview"),
    ("material-upload", ("学生下载材料成功",), "check_lessons_2_5", "materials.download"),
    ("material-upload", ("教师下载任教班级材料成功",), "check_lessons_2_5", "materials.download"),
    ("material-upload", ("删除后资料不可再访问",), "check_lessons_2_5", "materials.delete"),
    # mcp-tool-integration
    ("mcp-tool-integration", ("令牌缺失或错误",), "check_mcp_tools", "未配置 MCP_TOKEN_KEY 拒绝保存令牌"),
    ("mcp-tool-integration", ("换机后令牌不可用",), "check_mcp_tools", "换密钥后解密失败并提示重新填写令牌"),
    ("mcp-tool-integration", ("连续连接两次",), "check_mcp_tools", "重复连接工具不翻倍"),
    ("mcp-tool-integration", ("引用写法不合规",), "check_mcp_tools", "断开后引用记 denied"),
    ("mcp-tool-integration", ("只带技能内工具",), "check_mcp_tools", "候选集外工具 denied、不执行、不写审计"),
    ("mcp-tool-integration", ("两步任务连续两轮",), "check_mcp_tools", "meta.tool_calls 按序含两轮 ok 记录"),
    ("mcp-tool-integration", ("超过轮次上限",), "check_mcp_tools", "超出每问上限的调用写 denied 审计"),
    ("mcp-tool-integration", ("教师与错误归属执行对照",), "check_mcp_tools", "参数不符记 error 且未执行"),
    ("mcp-tool-integration", ("三种结果各有记录",), "check_mcp_tools", "写入 ok 审计记录"),
    ("mcp-tool-integration", ("记录只看自己的范围",), "check_mcp_tools", "同伴看不到我的记录"),
    # quiz-homework-publication
    ("quiz-homework-publication", ("M1 首次满分不入错题",), "check_assignment_history", "M1 正常：首次100分不入错题"),
    ("quiz-homework-publication", ("M2 低分改为及格或满分",), "check_quiz_homework", "H/教师覆盖 AI 分且后续初批跳过"),
    ("quiz-homework-publication", ("M3 修复历史残留不改成绩",), "check_assignment_history", "M3 正常：备份后修复且重复执行0条"),
    # research-materials
    ("research-materials", ("导入完善版图文资料包",), "check_research_materials", "import teacher package"),
    ("research-materials", ("同科同事选用素材",), "check_research_materials", "same subject colleagues share source"),
    ("research-materials", ("学生直接猜测教师原稿地址",), "check_research_materials", "student source read denied"),
    ("research-materials", ("现有结构化讲义生成学生版",), "check_research_materials", "student preview generated"),
    ("research-materials", ("编辑后重新核对",), "check_research_materials", "publication requires review"),
    ("research-materials", ("发布学生讲义到两个任教班级",), "check_research_materials", "authorized multi class batch succeeds"),
    ("research-materials", ("越权班级混入发布批次",), "check_research_materials", "mixed unauthorized classes entire request denied"),
    ("research-materials", ("标题未包含已知知识点",), "check_research_materials", "unknown topic does not guess label"),
    ("research-materials", ("学生预览和下载有图讲义",), "check_research_materials", "student bundle contains only student md and original figure"),
    ("research-materials", ("删除班级讲义",), "check_research_materials", "delete student publication"),
    ("research-materials", ("学生保存图文讲义",), "check_research_materials", "student bundle contains only student md and original figure"),
    ("research-materials", ("教师打印未发布的学生预览",), "check_research_materials", "publication requires review"),
    ("research-materials", ("同科同事复用共享教案",), "check_lesson_prep", "same subject colleague sees full teacher snapshot"),
    ("research-materials", ("下载教师图文包",), "check_lesson_prep", "shared teacher bundle includes snapshot and used original figure"),
    ("research-materials", ("绕过学生稿制作",), "check_lesson_prep", "shared teacher plan cannot bypass student workflow"),
    # runtime-reliability
    ("runtime-reliability", ("会话接口磁盘 I/O 故障修复",), "check_assignment_history", "H3 失败：历史依赖故障503"),
    # smart-lesson-prep
    ("smart-lesson-prep", ("尚未提供学情",), "check_lesson_prep", "selected class context and manual profile passed"),
    ("smart-lesson-prep", ("核对例题出处",), "check_lesson_prep", "reference excerpts exact and lines traceable"),
    ("smart-lesson-prep", ("多份资料均被选入",), "check_lesson_prep", "all selected sources contribute complete sections"),
    ("smart-lesson-prep", ("原题图的中文目录含空格",), "check_lesson_prep", "teacher generation fixes raw spaced image destinations"),
    ("smart-lesson-prep", ("生成与发布图文包",), "check_lesson_prep", "handout publishes both classes with index"),
    ("smart-lesson-prep", ("AI 完成教师草案",), "check_lesson_prep", "teacher draft saved with actual stream"),
    ("smart-lesson-prep", ("生成中断或无 Key",), "check_lesson_prep", "AI error produces error event"),
    ("smart-lesson-prep", ("重写教学过程",), "check_lesson_prep", "section rewrite changes only selected block"),
    ("smart-lesson-prep", ("审阅后再改正文",), "check_lesson_prep", "edit saved and remains draft"),
    ("smart-lesson-prep", ("第二次定稿",), "check_lesson_prep", "new final retains v1 and v2"),
    ("smart-lesson-prep", ("旧窗口写入",), "check_lesson_prep", "stale window cannot overwrite"),
    ("smart-lesson-prep", ("学生稿生成未通过检查",), "check_lesson_prep", "broken student response gives error"),
    ("smart-lesson-prep", ("教案和讲义均发布给学生",), "check_lesson_prep", "handout publishes both classes with index"),
    ("smart-lesson-prep", ("发布批次混入其他班",), "check_lesson_prep", "mixed unauthorized publication denied"),
    ("smart-lesson-prep", ("同学科同事访问私人教案",), "check_lesson_prep", "same subject colleague private plan denied"),
    ("smart-lesson-prep", ("删除私人教案",), "check_lesson_prep", "delete owned plan"),
    ("smart-lesson-prep", ("教师选择保留私有",), "check_lesson_prep", "default private plan has no group publication"),
    ("smart-lesson-prep", ("主动共享完整教师定稿",), "check_lesson_prep", "explicitly share current final"),
    ("smart-lesson-prep", ("重复发布或后续修改",), "check_lesson_prep", "same final share is idempotent"),
    ("smart-lesson-prep", ("删除私人原教案",), "check_lesson_prep", "shared final remains readable after deleting private original"),
    # smart-question-generation
    ("smart-question-generation", ("模型声明无依据的空位",), "check_question_bank", "validate_batch 遇到任意结构不抛异常、逐题拒绝"),
    ("smart-question-generation", ("题干泄露答案",), "check_question_bank", "学生卷不含答案/解析/S编号"),
    ("smart-question-generation", ("生成中模型超时",), "check_question_bank", "截断输出：返回 error 且不落题"),
    ("smart-question-generation", ("发布身份边界",), "check_quiz_homework", "Q/发布身份边界："),
    ("smart-question-generation", ("混合已有和新目标班级",), "check_quiz_homework", "Q/混合已有和新目标班级"),
    ("smart-question-generation", ("发布参数边界",), "check_quiz_homework", "Q/发布参数边界：缺少截止时间"),
    ("smart-question-generation", ("空位与公式下标共存",), "check_question_bank", "公式结构：转义、cases 与定界符正反用例"),
    ("smart-question-generation", ("选项含公式",), "check_question_bank", "单反斜杠 LaTeX：选项与解析同样还原"),
    ("smart-question-generation", ("选项缺右括号",), "check_question_bank", "修改引入不配对括号：400 且题目与 revision 不变"),
    ("smart-question-generation", ("转义括号与环境不被误判",), "check_question_bank", "公式结构：转义、cases 与定界符正反用例"),
    ("smart-question-generation", ("转义的美元符号",), "check_question_bank", "单反斜杠 LaTeX：题干还原为 LaTeX 命令"),
    ("smart-question-generation", ("选项各占一行",), "check_question_bank", "学生卷选择题：A–D 每项一行且行尾硬换行"),
    ("smart-question-generation", ("选项含块级公式",), "check_question_bank", "学生卷第 10 题：选项缩进 4 格"),
    # student-workspace
    ("student-workspace", ("学科标签过滤资料卡",), "check_lessons_2_5", "materials.math_subject_list"),
    ("student-workspace", ("预览和下载实际资料",), "check_lessons_2_5", "materials.preview"),
    ("student-workspace", ("从助手页连续追问",), "check_lessons_2_5", "agent.multiturn_context"),
    ("student-workspace", ("查看回答来源",), "check_lessons_2_5", "agent.citations_provenance"),
    ("student-workspace", ("H1 提交后进入历史并可刷新",), "check_assignment_history", "H1 正常：提交后历史输入与时间持久返回"),
    ("student-workspace", ("H3 历史读取隔离与失败",), "check_assignment_history", "H3 失败：他人提交不可读"),
    # teacher-workspace
    ("teacher-workspace", ("教师进入智能命题页",), "check_teacher_navigation", "R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航"),
    ("teacher-workspace", ("打开未接入的学情或教研模块",), "check_teacher_navigation", "R1 边界：没有任教班级仍只有三项教研入口"),
    ("teacher-workspace", ("在教研组内选择教师版发布学生稿",), "check_lesson_prep", "shared teacher plan cannot use simple student stripping"),
    ("teacher-workspace", ("检查系统菜单顺序",), "check_teacher_navigation", "R1 边界：没有任教班级仍只有三项教研入口"),
    ("teacher-workspace", ("教师检查顶栏",), "check_teacher_navigation", "R3 正常：切班保留现有页面行为"),
    ("teacher-workspace", ("发布与查看入口分开",), "check_teacher_navigation", "R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航"),
    ("teacher-workspace", ("旧教研链接有明确落点",), "check_teacher_navigation", "R2 失败路径：旧${old} / ${workspace} / ${classId}归一到既有备课跳转"),
]

# 明确不适用：前端交互/可视、真实模型语义、未实现特性、需容器/外部服务。
# 结构：(关键词元组, 不适用理由)；命中即记 N/A，不冒充覆盖。
NA_RULES = [
    (("教师预览技能文案",), "前端技能文案预览，属界面展示"),
    (("打开教师助手配置",), "前端配置页交互，非接口行为"),
    (("概念与学生公式作答",), "需真实模型语义质量抽查，非确定性断言可证"),
    (("多次卡住与完成",), "需真实模型语义质量抽查，非确定性断言可证"),
    (("学生只回复数字或不会",), "需真实模型语义质量抽查，非确定性断言可证"),
    (("按学习进度自适应引导",), "需真实模型语义质量抽查，非确定性断言可证"),
    (("多班级教师班级选择器展示所有任教班级",), "前端选择器展示，属界面交互"),
    (("网络中断前端提供重试",), "前端重试交互，属界面行为"),
    (("容器重启后文件不丢失",), "需容器重启，属部署环境验证"),
    (("前端仅教师展示删除入口",), "前端入口可见性，属界面展示"),
    (("命中工具并用到提示",), "前端提示展示，属界面交互"),
    (("配图尚未就绪",), "前端配图加载态，属界面展示"),
    (("首页进入助手对话",), "前端导航交互，属界面行为"),
    (("资料页返回其他模块",), "前端导航交互，属界面行为"),
    (("无效视图回退",), "前端路由回退，属界面行为"),
    (("浏览首页概览",), "前端概览浏览，属界面展示"),
    (("学生搜索本班讲义",), "前端本地搜索交互，属界面行为"),
    (("浏览演示作业结果",), "前端演示结果展示，属界面展示"),
    (("由错题进入助手",), "前端跳转交互，属界面行为"),
    (("浏览学习画像演示",), "前端画像展示，属界面展示"),
    (("从有资料切到空科目",), "前端科目切换布局，属界面行为"),
    (("E2 页面与刷新恢复",), "前端页面刷新恢复，属界面行为"),
    (("搜索加载与恢复",), "前端布局稳定性（同一容器与标题区不随是否渲染卡片变化），属界面布局"),
]


# 规格条款未被实现完全满足、但已有部分检查的条目：单独列出，不冒充覆盖。
# 结构：(关键词元组, 缺口说明, 作为部分证据的断言)
KNOWN_GAPS = [
    (("工具说明夹带指令",),
     "「远端工具说明要求模型先读取其他数据并放进参数」不在现有注入句式表内；"
     "检查只证明已知句式（忽略指令/扮演/泄露提示词）说明会被排除，"
     "按 mcp-tool-integration Requirement「本期只拦截已知写法」记为已知限制。",
     "工具说明夹带指令：含指令式说明的工具不进入候选清单并列入排除"),
]


def known_gap(scenario):
    for kws, reason, evidence in KNOWN_GAPS:
        if all(k in scenario for k in kws):
            return reason, evidence
    return None


def semantic_alias(capability, scenario):
    best = None
    for cap, kws, script, assertion in SEMANTIC_ALIASES:
        if (cap is None or cap == capability) and all(k in scenario for k in kws):
            if best is None or len(kws) > best[0]:
                best = (len(kws), script, assertion)
    return best


def na_reason(scenario):
    for kws, reason in NA_RULES:
        if all(k in scenario for k in kws):
            return reason
    return None


# 弱候选逐条人工复核表（192 条，覆盖生成时 bigram 重合 2–5 的全部 Scenario）。
# 结构：(capability, scenario) -> (结论, 检查脚本, 断言, 备注)
# 结论：确认覆盖 / 部分覆盖 / 已知缺口。
# 「部分覆盖」必须写明未断言的那一半；「已知缺口」必须说明实现缺什么。
REVIEWED = {
    # ---- agent-assistant ----
    ("agent-assistant", "留空回退默认提示词"):
        ("确认覆盖", "check_lessons_2_5", "agent.unconfigured_uses_default_prompt", ""),
    ("agent-assistant", "配置非任教班级被拒绝"):
        ("确认覆盖", "check_lessons_2_5", "agent.cross_class_config_denied", ""),
    ("agent-assistant", "开启解题引导技能"):
        ("确认覆盖", "check_lessons_2_5", "agent.tutor_overrides_custom_prompt", ""),
    ("agent-assistant", "访问他人会话被拒绝"):
        ("确认覆盖", "check_lessons_2_5", "agent.other_student_conversation_hidden", "403/404 均按不存在处理"),
    ("agent-assistant", "工具事件先于正文"):
        ("确认覆盖", "check_mcp_tools", "meta 事件先于 delta", ""),
    ("agent-assistant", "断开后的引用显示被拒"):
        ("确认覆盖", "check_mcp_tools", "断开后引用记 denied", ""),
    ("agent-assistant", "教师配置与班级检索共享隔离"):
        ("部分覆盖", "check_lessons_2_5", "agent.same_subject_teacher_configs_independent",
         "配置按教师隔离有断言；班级检索共享隔离只由班级过滤间接证明"),
    ("agent-assistant", "保存提示词及解题引导"):
        ("确认覆盖", "check_lessons_2_5", "agent.config_save", "config_read 同时校验提示词落库"),
    ("agent-assistant", "保存绑定 MCP 工具的技能"):
        ("确认覆盖", "check_mcp_tools", "技能保存成功 201", ""),
    ("agent-assistant", "他人技能不可见"):
        ("确认覆盖", "check_mcp_tools", "同伴删他人技能 404", ""),
    ("agent-assistant", "命中技能"):
        ("确认覆盖", "check_mcp_tools", "meta 含技能名", ""),
    ("agent-assistant", "未命中或技能停用"):
        ("确认覆盖", "check_mcp_tools", "未命中技能不发 meta", ""),
    ("agent-assistant", "在配置页登记并连接 MCP 服务器"):
        ("确认覆盖", "check_mcp_tools", "连接成功 200", "登记 201 与 connected=true 同文件"),
    ("agent-assistant", "调整预览技能不产生真实批改配置"):
        ("部分覆盖", "check_mcp_tools", "meta 含技能名", "只证明技能影响问答元数据；「不产生批改配置」无直接断言"),
    ("agent-assistant", "尚无任教班级"):
        ("确认覆盖", "check_lesson10_p0_scenarios", "P0 前端：教师未分配任教班级时存在空状态提示", ""),

    # ---- async-homework-grading ----
    ("async-homework-grading", "A1 正常提交不等待"):
        ("确认覆盖", "check_async_grading", "A1 正常：20次202无评分且P95小于200ms假执行，无请求内模型调用", ""),
    ("async-homework-grading", "A2 查询无副作用与空批次"):
        ("确认覆盖", "check_async_grading", "A2 正常：GET只读", "空批次由 A2 边界断言覆盖"),
    ("async-homework-grading", "A3 参数与资源失败"):
        ("确认覆盖", "check_async_grading", "A3 失败：非法任务编号422", "同文件另断言任务不存在 404 与活跃任务重试 409"),
    ("async-homework-grading", "B1 消费者停止再启动"):
        ("确认覆盖", "check_async_grading", "B1 正常：队列有消息、消费者未运行时pending", ""),
    ("async-homework-grading", "B2 队列故障后补投"):
        ("确认覆盖", "check_async_grading", "B2 正常：恢复后补投并可消费", ""),
    ("async-homework-grading", "B3 事务中途失败"):
        ("确认覆盖", "check_async_grading", "B3 失败：数据库错误503且不泄露内部信息", "第二项故障整批回滚同文件断言"),
    ("async-homework-grading", "B4 执行中杀进程与旧租约"):
        ("确认覆盖", "check_async_grading", "B4 失败：旧租约不能覆盖", ""),
    ("async-homework-grading", "C1 并发与重复投递"):
        ("确认覆盖", "check_async_grading", "C1 边界：20并发数据库唯一幂等", ""),
    ("async-homework-grading", "C2 重交及教师终评竞态"):
        ("确认覆盖", "check_quiz_homework", "H/初批期间提交被更新或教师改分：教师终评", "重交与旧结果跳过同组断言"),
    ("async-homework-grading", "D1 失败退避与死信"):
        ("确认覆盖", "check_async_grading", "D1 失败：死信投递失败不假确认", "退避时间与不写部分分数同组"),
    ("async-homework-grading", "D2 手动重试与合法模型恢复"):
        ("确认覆盖", "check_async_grading", "D2 正常：授权手动重试202", ""),
    ("async-homework-grading", "E1 未登录及越权"):
        ("确认覆盖", "check_async_grading", "E1 失败：", "模板按未登录/学生/他班/他科展开；403/404 审计同组"),
    ("async-homework-grading", "E3 初批反馈在当前作业卡片可见"):
        ("确认覆盖", "check_grading_feedback", "E3 正常：回执位于具有作业编号的卡片内，不在页面顶部",
         "回执文案、错误 alert 与换行同文件断言"),
    ("async-homework-grading", "E4 查看提交同步人数"):
        ("确认覆盖", "check_grading_feedback", "E4 正常：提交数量更新且不污染其他作业或原数组",
         "空列表/未知作业边界同文件断言"),
    ("async-homework-grading", "F1 一键复现和迁移保留"):
        ("部分覆盖", "check_async_grading", "F1 边界：重复迁移不改变旧数据",
         "迁移与旧库升级有机器断言；README 一键复现未在门禁内实际执行"),
    ("async-homework-grading", "Q1 暂停消费者不积攒副本"):
        ("确认覆盖", "check_async_grading", "Q1 边界：确认后跨越30分钟不积攒副本", ""),
    ("async-homework-grading", "Q2 未确认及过期运行恢复"):
        ("确认覆盖", "check_async_grading", "Q2 边界：同一过期租约只确认一条恢复消息", ""),
    ("async-homework-grading", "Q3 管理员明确恢复丢失消息"):
        ("确认覆盖", "check_async_grading", "Q3 正常：显式恢复只清待执行投递标记", ""),
    ("async-homework-grading", "Q4 界面不把消息数当批改数"):
        ("部分覆盖", "check_grading_feedback", "E4 正常：提交数量更新且不污染其他作业或原数组",
         "前端只同步提交数；队列消息数与批改数的后端分离无单独断言"),

    # ---- class-data-isolation ----
    ("class-data-isolation", "用户账号基础信息不隔离"):
        ("部分覆盖", "check_lesson10_review", "用户账号基础信息不隔离：不同班级学生均能读取本人姓名与班级",
         "登录/刷新返回本人姓名与班级；接口未返回学号字段"),
    ("class-data-isolation", "教师查看任教班级资料成功"):
        ("确认覆盖", "check_lessons_2_5", "materials.all_subject_list_preserved",
         "任教范围内跨班可见；越界由 subject_list_cross_class_denied 反证"),
    ("class-data-isolation", "学生查看本班资料成功"):
        ("确认覆盖", "check_lessons_2_5", "materials.download", "列表/预览/下载同文件断言"),
    ("class-data-isolation", "学生资料请求使用本人班级"):
        ("部分覆盖", "check_lesson10_review", "学生资料请求使用本人班级：学生端固定取本人 class_id，不提供跨班切换",
         "前端源码断言 + 后端 materials.student_subject_scope_denied 拒绝跨班；未跑浏览器"),
    ("class-data-isolation", "Windows Docker 共享目录读写"):
        ("部分覆盖", "check_sqlite_storage", "{mode} journal active",
         "DELETE 模式并发提交、持久化与完整性已断言；未在真实 Windows 共享目录运行"),
    ("class-data-isolation", "数据库暂不可用"):
        ("确认覆盖", "check_baseline", "R1 失败：数据库异常 → 503 与通用提示", ""),

    # ---- login-and-account-system ----
    ("login-and-account-system", "密码错误登录失败"):
        ("确认覆盖", "check_lesson10_review", "密码错误与账号不存在返回同一提示", "均为 401 且文案相同"),
    ("login-and-account-system", "账号不存在登录失败"):
        ("确认覆盖", "check_lesson10_review", "密码错误与账号不存在返回同一提示", "与密码错误逐字相同"),
    ("login-and-account-system", "Access Token 过期自动刷新"):
        ("部分覆盖", "check_lesson10_review", "Access Token 过期自动刷新：前端 401 后调用 refresh 并重试原请求",
         "后端 refresh 由 auth.refresh 断言；自动重试为源码断言，未跑浏览器"),
    ("login-and-account-system", "Refresh Token 过期需重新登录"):
        ("确认覆盖", "check_lesson10_review", "Refresh Token 过期需重新登录：过期刷新令牌返回 401", ""),
    ("login-and-account-system", "JWT Payload 包含必要字段"):
        ("确认覆盖", "check_lesson10_review", "JWT Payload 包含必要字段：教师令牌含七个声明",
         "学生令牌不带教师身份同组断言"),
    ("login-and-account-system", "未登录用户无法注册"):
        ("确认覆盖", "check_lesson10_review", "未登录用户无法注册：注册接口不存在且登录页无注册入口", ""),
    ("login-and-account-system", "教师通过 CSV 批量导入学生含手机号"):
        ("确认覆盖", "check_lesson10_review", "CSV 导入手机号：phone 字段落库", ""),
    ("login-and-account-system", "预置教师账号携带学科与班主任身份"):
        ("确认覆盖", "check_lesson10_review", "开发种子：教师学科与班主任身份写入", ""),
    ("login-and-account-system", "CSV 缺少学号列被拒绝"):
        ("确认覆盖", "check_lesson10_review", "CSV 缺少学号列被拒绝：400 且不创建账号", ""),
    ("login-and-account-system", "首次密码登录被拦截要求改密"):
        ("确认覆盖", "check_lessons_2_5", "auth.first_password_blocks_business", ""),
    ("login-and-account-system", "未改密时访问业务接口被拦截"):
        ("确认覆盖", "check_lessons_2_5", "auth.first_password_blocks_business", "会话/历史接口另两项同组断言"),
    ("login-and-account-system", "改密成功后恢复正常访问"):
        ("确认覆盖", "check_lessons_2_5", "auth.change_password", ""),
    ("login-and-account-system", "教师种子维护身份而不覆盖已改密码"):
        ("确认覆盖", "check_lesson10_review", "教师种子维护身份而不覆盖已改密码：重跑保留自定义口令并更新学科", ""),
    ("login-and-account-system", "教师刷新后保留页面"):
        ("部分覆盖", "check_lessons_2_5", "auth.refresh_restores_full_user",
         "完整身份恢复有断言；URL 与菜单保留属浏览器行为"),
    ("login-and-account-system", "刷新失败回登录"):
        ("确认覆盖", "check_route_guard", "身份恢复前不显示业务内容：缺少",
         "缺 accessToken/身份提示时拒绝显示业务页"),
    ("login-and-account-system", "修改非任教班级学生被拒绝"):
        ("确认覆盖", "check_lessons_2_5", "auth.csv_other_class_update_denied", ""),
    ("login-and-account-system", "导入非任教目标班级被拒绝"):
        ("确认覆盖", "check_lessons_2_5", "auth.csv_other_class_create_denied", ""),

    # ---- material-upload ----
    ("material-upload", "前端 accept 属性初步限制"):
        ("确认覆盖", "check_lesson10_review", "前端 accept 属性初步限制：ACCEPT 仅含允许格式且绑定文件输入", ""),
    ("material-upload", "SQLite 仅存储元数据"):
        ("确认覆盖", "check_lesson10_review", "SQLite 仅存储元数据：Material 表无二进制列", ""),
    ("material-upload", "教师删除任教班级资料成功"):
        ("确认覆盖", "check_lessons_2_5", "materials.delete", "MaterialContent/Chunk 清理同文件断言"),

    # ---- mcp-tool-integration ----
    ("mcp-tool-integration", "带令牌发现并调用工具"):
        ("确认覆盖", "check_mcp_tools", "确实带令牌调用了工具", "meta.tool_calls 记录 ok 同组"),
    ("mcp-tool-integration", "非法请求可读"):
        ("确认覆盖", "check_mcp_server", "非法请求可读：",
         "8 类非法请求逐项返回 JSON-RPC 错误码与中文说明"),
    ("mcp-tool-integration", "登记后响应不含令牌"):
        ("确认覆盖", "check_mcp_tools", "响应不含令牌", ""),
    ("mcp-tool-integration", "同名再登记"):
        ("确认覆盖", "check_mcp_tools", "同名再登记 400", ""),
    ("mcp-tool-integration", "连接自建服务发现工具"):
        ("确认覆盖", "check_mcp_tools", "连接成功 200", "工具清单不翻倍由「重复连接工具不翻倍」证明"),
    ("mcp-tool-integration", "令牌错误时连接失败"):
        ("确认覆盖", "check_mcp_tools", "连接失败 502", ""),
    ("mcp-tool-integration", "断开后不可调用"):
        ("确认覆盖", "check_mcp_tools", "断开后引用记 denied", ""),
    ("mcp-tool-integration", "同伴访问我的服务器"):
        ("确认覆盖", "check_mcp_tools", "同伴读取他人服务器 404", ""),
    ("mcp-tool-integration", "学生调用管理接口"):
        ("确认覆盖", "check_mcp_tools", "学生访问管理接口 403", ""),
    ("mcp-tool-integration", "工具不在清单或服务器未连接"):
        ("确认覆盖", "check_mcp_tools", "候选集外工具 denied、不执行、不写审计", ""),
    ("mcp-tool-integration", "工具超时"):
        ("确认覆盖", "check_mcp_tools", "工具超时：本次调用记 error 且原因写明失败", ""),
    ("mcp-tool-integration", "发现重连未知权限默认拒绝"):
        ("确认覆盖", "check_security_gate", "P0-5 正常/边界：真实发现分类保守且不信远端只读声明",
         "未知工具默认可写不等于可执行；重连不降级由分类断言覆盖"),
    ("mcp-tool-integration", "审计存储失败可观察"):
        ("确认覆盖", "check_security_gate", "审计故障：告警可见且不泄露异常原文", "工具存储回滚且不中断同组"),
    ("mcp-tool-integration", "决策轮用量可追溯"):
        ("确认覆盖", "check_security_gate", "P1-2 决策轮用量：", "合法/缺失/非法三类用量逐项断言"),
    ("mcp-tool-integration", "默认关闭文档"):
        ("确认覆盖", "check_lesson10_scenario_gaps",
         "默认关闭文档：代码默认值为关闭，/docs 与 /openapi.json 随之不暴露", ""),

    # ---- quiz-homework-publication ----
    ("quiz-homework-publication", "保留手工布置"):
        ("确认覆盖", "check_quiz_homework", "H/保留手工布置：草稿不可见", "两种作业同时展示同文件断言"),
    ("quiz-homework-publication", "提交命题作业"):
        ("确认覆盖", "check_quiz_homework", "H/提交命题作业", ""),
    ("quiz-homework-publication", "题面显示一致"):
        ("确认覆盖", "check_quiz_homework", "H/题面显示一致", "含第 10/12 题与填空空位"),
    ("quiz-homework-publication", "分数折算边界"):
        ("确认覆盖", "check_quiz_homework", "H/分数折算边界：", "合法/越界逐项断言"),
    ("quiz-homework-publication", "配图异常"):
        ("确认覆盖", "check_quiz_homework", "H/配图异常：非法名", "点路径、未知名与指纹变化同组"),
    ("quiz-homework-publication", "迁移重复执行"):
        ("确认覆盖", "check_quiz_homework", "H/迁移重复执行", ""),
    ("quiz-homework-publication", "M4 越权或事务失败不部分改分"):
        ("确认覆盖", "check_quiz_homework", "H/初批失败仍可人工改分：",
         "越权改分 403 与拒绝访问审计同组；失败批次无部分写入"),

    # ---- rag-search ----
    ("rag-search", "解析成功但向量化失败保持未索引"):
        ("确认覆盖", "check_lesson10_p0_scenarios",
         "P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功", ""),
    ("rag-search", "支持 Markdown 列表与加粗"):
        ("确认覆盖", "check_lesson10_review", "支持 Markdown 列表与加粗：解析保留列表与加粗原文", ""),

    # ---- rbac-role-permissions ----
    ("rbac-role-permissions", "教师管理自己任教的班级"):
        ("确认覆盖", "check_analytics", "S4 正常：任教范围内班级可查", ""),
    ("rbac-role-permissions", "教师上传资料并布置作业"):
        ("部分覆盖", "check_homework", "S1 正常：教师创建草稿作业 200",
         "布置有断言；上传由 materials.upload_md 另行断言，同一教师链路"),
    ("rbac-role-permissions", "教师批改作业并查看本班学生数据"):
        ("确认覆盖", "check_quiz_homework", "H/教师直接评分并联动错题学情",
         "学情计数由 check_analytics S1/U1 交叉断言"),
    ("rbac-role-permissions", "教师查看本班学生 AI 提问历史"):
        ("已知缺口", "", "",
         "教师端没有按班级查询 AI 提问历史的接口与页面；学情汇总只有提问数"),
    ("rbac-role-permissions", "教师不能代替学生发起 AI 提问"):
        ("部分覆盖", "check_lesson10_review", "教师不能代替学生发起 AI 提问：教师调用学生提问接口 403",
         "拒绝成立；提示文案为「仅学生可执行该操作」，规约写「AI 提问仅限学生发起」"),
    ("rbac-role-permissions", "教师重置本班学生密码"):
        ("确认覆盖", "check_lessons_2_5", "auth.homeroom_reset", ""),
    ("rbac-role-permissions", "教师不能查看非任教班级的学生数据"):
        ("确认覆盖", "check_analytics", "S3 失败：教师跨班访问 → 403", ""),
    ("rbac-role-permissions", "教师仅能访问本学科教研资料"):
        ("确认覆盖", "check_research_materials", "cross subject read denied", ""),
    ("rbac-role-permissions", "任课教师不能重置学生密码"):
        ("部分覆盖", "check_lessons_2_5", "auth.subject_teacher_reset_denied",
         "拒绝成立，实际返回 404（隐藏资源存在性），规约写 403"),
    ("rbac-role-permissions", "教师访问教师路由通过"):
        ("确认覆盖", "check_route_guard", "本角色页面正常渲染：teacher → /teacher", ""),
    ("rbac-role-permissions", "学生访问学生路由通过"):
        ("确认覆盖", "check_route_guard", "本角色页面正常渲染：student → /student", ""),
    ("rbac-role-permissions", "学生访问教师路由被拦截"):
        ("确认覆盖", "check_route_guard", "伪造角色提示不赋予页面权限：student → /teacher", ""),
    ("rbac-role-permissions", "教师访问学生路由被拦截"):
        ("确认覆盖", "check_route_guard", "伪造角色提示不赋予页面权限：teacher → /student", ""),
    ("rbac-role-permissions", "未登录用户访问业务路由重定向登录"):
        ("确认覆盖", "check_route_guard", "身份恢复前不显示业务内容：缺少",
         "缺 accessToken/身份提示时拒绝进入业务页"),
    ("rbac-role-permissions", "教师调用教师接口通过"):
        ("确认覆盖", "check_lessons_2_5", "materials.upload_md", ""),
    ("rbac-role-permissions", "学生调用学生接口通过"):
        ("确认覆盖", "check_homework", "S3 正常：学生提交成功", ""),
    ("rbac-role-permissions", "教师查询任教班级数据成功"):
        ("确认覆盖", "check_analytics", "S4 正常：任教范围内班级可查", ""),
    ("rbac-role-permissions", "教师查询非任教班级数据被拒"):
        ("确认覆盖", "check_analytics", "S3 失败：教师跨班访问 → 403", ""),
    ("rbac-role-permissions", "教师跨班操作被拒"):
        ("确认覆盖", "check_lessons_2_5", "materials.cross_class_upload_denied", ""),
    ("rbac-role-permissions", "教师选择任教班级操作成功"):
        ("确认覆盖", "check_lessons_2_5", "materials.upload_md", ""),
    ("rbac-role-permissions", "教师选择非任教班级操作被拒"):
        ("确认覆盖", "check_lessons_2_5", "materials.cross_class_upload_denied", ""),
    ("rbac-role-permissions", "多班级选择器展示所有任教班级"):
        ("确认覆盖", "check_teacher_navigation", "多班级选择器展示所有任教班级：选择器值来自任教班级列表",
         "接口返回全部任教班级另由 check_lesson10_review 断言"),
    ("rbac-role-permissions", "未刷新前旧权限仍有效"):
        ("确认覆盖", "check_lesson10_review", "未刷新前旧权限仍有效：旧令牌按旧任教班级校验，重新登录后生效", ""),
    ("rbac-role-permissions", "后端越权返回 403 并记录审计日志"):
        ("确认覆盖", "check_baseline", "R2 失败：403 访问日志 status=403 且标识一致", "响应 403 与审计字段同文件"),
    ("rbac-role-permissions", "审计日志异步写入不影响响应性能"):
        ("确认覆盖", "check_security_gate", "R2 审计异步：401响应正文发出后再写入", ""),
    ("rbac-role-permissions", "未登录请求留匿名审计"):
        ("确认覆盖", "check_lesson10_review", "未登录请求留匿名审计：401 落库 user_id 为空且 action 可识别", ""),
    ("rbac-role-permissions", "教师学科身份登录后进入教研组"):
        ("确认覆盖", "check_research_materials", "same subject colleagues share source", ""),
    ("rbac-role-permissions", "学生仅以学号密码登录"):
        ("确认覆盖", "check_lessons_2_5", "auth.login.S1", ""),
    ("rbac-role-permissions", "学生查看个人错题本"):
        ("确认覆盖", "check_mistake", "S1 正常：本人错题列表返回 2 条", ""),
    ("rbac-role-permissions", "学生发起 AI 提问并查看历史"):
        ("确认覆盖", "check_lesson10_review", "学生发起 AI 提问并查看历史：提问落库且历史仅本人可见", ""),
    ("rbac-role-permissions", "学生将 AI 解答加入错题本"):
        ("已知缺口", "", "",
         "错题本只有列表/详情/掌握/讲解四个接口，没有「加入错题本」写入接口与页面入口"),
    ("rbac-role-permissions", "学生不能越权查看其他学生数据"):
        ("确认覆盖", "check_mistake", "S4 正常：请求参数 student_id 被忽略，仍只返回本人错题", ""),
    ("rbac-role-permissions", "不同学生账号次数独立计算"):
        ("确认覆盖", "check_lesson10_review", "不同学生账号次数独立计算：两名学生各自计数互不影响", ""),
    ("rbac-role-permissions", "学生查询自己数据成功"):
        ("确认覆盖", "check_mistake", "S1 正常：本人错题列表返回 2 条", ""),
    ("rbac-role-permissions", "学生尝试查询他人数据被拒"):
        ("确认覆盖", "check_mistake", "S4 正常：请求参数 student_id 被忽略，仍只返回本人错题", ""),

    # ---- research-materials ----
    ("research-materials", "图片没有随 Markdown 导入"):
        ("确认覆盖", "check_research_materials", "invalid import bad.md", "缺图 Markdown 返回 400 且不落库"),
    ("research-materials", "完整教师 Markdown 误传班级"):
        ("确认覆盖", "check_research_materials", "legacy class upload rejects teacher answer content",
         "教师版文件名同样被拒，同文件断言"),

    # ---- runtime-reliability ----
    ("runtime-reliability", "Windows 共享目录运行小组服务"):
        ("部分覆盖", "check_sqlite_storage", "{mode} journal active",
         "DELETE 模式并发提交/持久化/完整性已断言；未在真实 Windows 共享目录运行"),
    ("runtime-reliability", "使用原生磁盘的 WAL 配置"):
        ("确认覆盖", "check_sqlite_storage", "{mode} journal active",
         "WAL 同步级别、并行提交与完整性同文件断言"),
    ("runtime-reliability", "无效日志模式"):
        ("确认覆盖", "check_sqlite_storage", "unsafe journal rejected", ""),
    ("runtime-reliability", "数据库存储异常"):
        ("确认覆盖", "check_baseline", "R1 失败：数据库异常 → 503 与通用提示", ""),
    ("runtime-reliability", "数据库读取正常"):
        ("确认覆盖", "check_baseline", "R1 正常：三项依赖为 ok/ok/configured", "健康检查不写业务记录同文件"),

    # ---- smart-lesson-prep ----
    ("smart-lesson-prep", "教师生成并修改学生讲义"):
        ("确认覆盖", "check_lesson_prep", "edit saved and remains draft", "学生稿生成/保存同文件"),
    ("smart-lesson-prep", "学生稿含漏网控制字符"):
        ("确认覆盖", "check_lesson_prep", "学生稿含 U+000C：返回 error",
         "旧稿保持不变与手工编辑同样拒绝同组"),
    ("smart-lesson-prep", "新修订尝试发布旧学生稿"):
        ("确认覆盖", "check_lesson_prep", "new final cannot publish old student drafts", ""),

    # ---- smart-question-generation ----
    ("smart-question-generation", "配比不一致或越界"):
        ("确认覆盖", "check_question_bank", "题型/难度合计不等 400", "另断言总题数 0/21 与单题型 11"),
    ("smart-question-generation", "选用他科资料"):
        ("确认覆盖", "check_question_bank", "选用他科资料 404", ""),
    ("smart-question-generation", "使用词表外的知识点"):
        ("确认覆盖", "check_question_bank", "词表外知识点 400", ""),
    ("smart-question-generation", "查看题目出处"):
        ("确认覆盖", "check_question_bank", "答案卷出处带原文行号与摘录（与题目快照一致）",
         "S 编号与资料名同组"),
    ("smart-question-generation", "原稿在入库后被替换"):
        ("确认覆盖", "check_lesson10_review",
         "原稿在入库后被替换：指纹变化标记 changed、缺失标记 deleted", ""),
    ("smart-question-generation", "全部题目通过校验"):
        ("确认覆盖", "check_question_bank", "全部通过 8 题落库", ""),
    ("smart-question-generation", "部分题目不合格"):
        ("确认覆盖", "check_question_bank", "部分不合格：6 通过 2 未通过", ""),
    ("smart-question-generation", "模型返回字面包含所选标签的表述"):
        ("确认覆盖", "check_question_bank", "细分知识点：落库知识点为所选标签", ""),
    ("smart-question-generation", "输出不是 JSON"):
        ("确认覆盖", "check_question_bank", "非 JSON 返回 error", "不保存题目与写失败记录同组"),
    ("smart-question-generation", "被误解码的公式命令被修补"):
        ("确认覆盖", "check_question_bank", "单反斜杠 LaTeX：generate 事件记录 escape_repairs=13", ""),
    ("smart-question-generation", "修补后仍不是合法 JSON"):
        ("确认覆盖", "check_question_bank", "截断输出：失败原因含第 12 行与列号", "不含模型原文同组"),
    ("smart-question-generation", "漏网的控制字符被拦截"):
        ("确认覆盖", "check_question_bank", "U+000C 题干：原因为含不可见控制字符", ""),
    ("smart-question-generation", "未配置模型 Key"):
        ("确认覆盖", "check_question_bank", "无 Key 返回 503", ""),
    ("smart-question-generation", "修改后通过"):
        ("确认覆盖", "check_question_bank", "补齐括号后保存并通过：进入题库且标记已修改", ""),
    ("smart-question-generation", "未确认即通过"):
        ("确认覆盖", "check_question_bank", "未确认即通过 400", ""),
    ("smart-question-generation", "重复题目"):
        ("确认覆盖", "check_question_bank", "重复题干通过 409", ""),
    ("smart-question-generation", "驳回后尝试通过"):
        ("确认覆盖", "check_question_bank", "驳回后通过 409", ""),
    ("smart-question-generation", "同科同事浏览题库"):
        ("确认覆盖", "check_question_bank", "同科同事可见题库", ""),
    ("smart-question-generation", "修改入库题目"):
        ("确认覆盖", "check_question_bank", "入库题目修改 409", ""),
    ("smart-question-generation", "下架后组卷"):
        ("确认覆盖", "check_lesson10_scenario_gaps",
         "下架后组卷：下架题不进入新试卷且返回缺口、不创建试卷", ""),
    ("smart-question-generation", "题库不足"):
        ("确认覆盖", "check_question_bank", "题库不足 422 并列出缺口", ""),
    ("smart-question-generation", "发布到两个任教班级"):
        ("确认覆盖", "check_question_bank", "发布到两个班 200", ""),
    ("smart-question-generation", "草稿试卷发布"):
        ("确认覆盖", "check_question_bank", "草稿发布 409", ""),
    ("smart-question-generation", "未确认核对或版本冲突"):
        ("确认覆盖", "check_question_bank", "未确认核对 400", ""),
    ("smart-question-generation", "重复发布"):
        ("确认覆盖", "check_question_bank", "重复发布复用作业", ""),
    ("smart-question-generation", "重复发布更换截止时间或遇到已关闭作业"):
        ("确认覆盖", "check_quiz_homework", "Q/重复发布更换截止时间或遇到已关闭作业：截止时间冲突",
         "已关闭 409 同组"),
    ("smart-question-generation", "原图校验或文件写入失败"):
        ("确认覆盖", "check_quiz_homework", "Q/原图校验或文件写入失败：数据库整批回滚",
         "文件整批回滚与指纹 409 同组"),
    ("smart-question-generation", "物理教师读取数学题目"):
        ("确认覆盖", "check_question_bank", "跨学科读取题目 404", ""),
    ("smart-question-generation", "作业发布审计"):
        ("确认覆盖", "check_quiz_homework", "Q/作业发布审计", ""),
    ("smart-question-generation", "无 Key 环境运行验收脚本"):
        ("部分覆盖", "check_question_bank",
         "无 Key 环境运行验收脚本：虚构模型完成生成且无外部模型请求",
         "脚本以占位 test-key 启动并替换 stream_chat；未验证完全不设置环境变量的路径"),
    ("smart-question-generation", "多空位填空题显示"):
        ("确认覆盖", "check_question_rendering", "多空位填空题显示：三个空位保留且无加粗斜体", ""),
    ("smart-question-generation", "填空与解答题答案含公式"):
        ("确认覆盖", "check_question_rendering", "填空与解答题答案含公式：答案以 KaTeX 渲染且无 katex-error", ""),
    ("smart-question-generation", "多空答案与选择判断答案"):
        ("确认覆盖", "check_question_bank", "答案卷含答案与解析", ""),
    ("smart-question-generation", "编辑答案时显示原文"):
        ("确认覆盖", "check_question_bank", "答案卷出处带原文行号与摘录（与题目快照一致）",
         "出处快照与编辑原文一致"),
    ("smart-question-generation", "解答题作答横线不变"):
        ("确认覆盖", "check_question_rendering", "解答题作答横线不变：整行下划线渲染为分隔线而非文字", ""),
    ("smart-question-generation", "学生端打开已发布试卷"):
        ("部分覆盖", "check_question_rendering", "学生端打开已发布试卷：多空位题干渲染后空位与发布时一致",
         "交作业与历史资料两种入口未逐一走浏览器，共用同一渲染组件"),
    ("smart-question-generation", "定界符不成对"):
        ("确认覆盖", "check_question_bank", "公式结构：转义、cases 与定界符正反用例", ""),
    ("smart-question-generation", "第 10 题以后"):
        ("确认覆盖", "check_quiz_homework", "H/题面显示一致", "学生卷 10.–12. 选项仍在题下"),
    ("smart-question-generation", "学生端打开新发布的试卷"):
        ("确认覆盖", "check_question_bank", "学生卷选择题：A–D 每项一行且行尾硬换行",
         "不含答案/解析/S 编号同组"),
    ("smart-question-generation", "已发布资料不被改写"):
        ("确认覆盖", "check_quiz_homework", "Q/已发布资料不被改写", ""),

    # ---- student-workspace ----
    ("student-workspace", "学生首页展示本人班级"):
        ("确认覆盖", "check_lesson10_review", "学生首页展示本人班级：班级名取自本人会话且无班级选择器", ""),
    ("student-workspace", "未分班学生访问"):
        ("确认覆盖", "check_lesson10_review", "未分班学生访问：空状态且不请求班级资料",
         "后端 agent.unassigned_student_denied 另行断言"),
    ("student-workspace", "H2 关闭后保留终评及配图"):
        ("确认覆盖", "check_assignment_history", "H2 正常：关闭后保留100分作答与评语",
         "配图可读与不可重交同组"),

    # ---- teacher-identity-and-permissions ----
    ("teacher-identity-and-permissions", "教师登录进入本学科教研组"):
        ("确认覆盖", "check_research_materials", "same subject colleagues share source", ""),
    ("teacher-identity-and-permissions", "教师学科身份随 JWT 生效"):
        ("部分覆盖", "check_lessons_2_5", "agent.teacher_subject_uses_current_database",
         "subject 实际取数据库当前值并覆盖令牌；请求体不声明学科时按服务端身份判定的行为成立"),
    ("teacher-identity-and-permissions", "数学教师访问数学教研资料成功"):
        ("确认覆盖", "check_research_materials", "same subject colleagues share source", ""),
    ("teacher-identity-and-permissions", "数学班主任跨学科访问英语资料被拒"):
        ("确认覆盖", "check_research_materials", "cross subject read denied", ""),
    ("teacher-identity-and-permissions", "跨学科教研资料不可见"):
        ("确认覆盖", "check_research_materials", "other subject sees no source", ""),
    ("teacher-identity-and-permissions", "班主任查看其他班级学情被拒"):
        ("确认覆盖", "check_analytics", "S3 失败：教师跨班访问 → 403", ""),
    ("teacher-identity-and-permissions", "班主任可见本班全部学生"):
        ("确认覆盖", "check_analytics", "S1 正常：班主任查看本班全科 101 学情", "total_students 计数"),
    ("teacher-identity-and-permissions", "任课老师仅见任教班级名单"):
        ("部分覆盖", "check_lessons_2_5", "auth.teacher_cross_class_denied",
         "越界 403 有断言；名单只含任教班级的完整集合未单独断言"),
    ("teacher-identity-and-permissions", "任课教学保留班主任模块"):
        ("确认覆盖", "check_teacher_navigation", "任课教学保留班主任模块：切到 102 仍显示带班 101 入口", ""),
    ("teacher-identity-and-permissions", "任课教师调用重置接口被拒"):
        ("部分覆盖", "check_lessons_2_5", "auth.subject_teacher_reset_denied",
         "拒绝成立，实际 404 而非规约写的 403"),

    # ---- teacher-workspace ----
    ("teacher-workspace", "教师打开资料页仍可访问其他模块"):
        ("确认覆盖", "check_teacher_navigation", "R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航",
         "共用导航在 /teacher/library、/upload、/materials 均断言"),
    ("teacher-workspace", "任课教学保留班主任入口"):
        ("确认覆盖", "check_teacher_navigation", "任课教学保留班主任模块：切到 102 仍显示带班 101 入口", ""),
    ("teacher-workspace", "非班主任只显示任课与教研功能"):
        ("确认覆盖", "check_teacher_navigation",
         "非班主任只显示任课与教研功能：无班主任工作台，保留任课/教研/助手配置", ""),
    ("teacher-workspace", "切换任课班级不切换带班班级"):
        ("确认覆盖", "check_teacher_navigation", "任课教学保留班主任模块：切到 102 仍显示带班 101 入口",
         "同一断言验证任课 102 与带班 101 并存"),
    ("teacher-workspace", "班主任进入全科资料总览"):
        ("部分覆盖", "check_teacher_navigation", "R1 正常：",
         "班主任工作台含「本班资料（全科）」入口；「总览不提供上传/删除」无直接断言"),
    ("teacher-workspace", "智能命题不再是占位"):
        ("确认覆盖", "check_teacher_navigation", "R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航",
         "命题入口指向 /teacher/quiz"),
    ("teacher-workspace", "查看当前任教班级本科目资料"):
        ("确认覆盖", "check_lessons_2_5", "materials.math_subject_list", "单科列表按 subject_only=true 断言"),
    ("teacher-workspace", "切班后保留资料视图"):
        ("确认覆盖", "check_teacher_navigation", "R3 正常：切班保留现有页面行为", ""),
    ("teacher-workspace", "R1 教研中心只有三个现有入口"):
        ("确认覆盖", "check_teacher_navigation", "R1 正常：", "六条路由 × 有/无带班逐项断言"),
    ("teacher-workspace", "R3 其他导航与班级不退化"):
        ("确认覆盖", "check_teacher_navigation", "R3 边界：其他view保持原值", ""),
    ("teacher-workspace", "在助手配置页切换班级"):
        ("部分覆盖", "check_lessons_2_5", "agent.class_switch_reads_and_saves_target",
         "切到 102 后读取/保存以 102 为目标且不影响 101 有断言；「保留配置视图」属前端行为"),

    # ---- 原「仅文件级」条目：本轮一并落到具体断言 ----
    ("agent-assistant", "关闭解题引导技能"):
        ("确认覆盖", "check_lessons_2_5", "agent.custom_prompt_without_tutor",
         "关闭引导后使用已保存自定义提示词；无配置时回退默认提示词同组"),
    ("agent-assistant", "引导求两向量夹角余弦"):
        ("部分覆盖", "check_lessons_2_5", "agent.citations_provenance",
         "来源编号与原文摘录保留有断言；「具体计算不伪称来自讲义」属模型语义"),
    ("agent-assistant", "数学与物理配置各自生效"):
        ("确认覆盖", "check_lessons_2_5", "agent.physics_save_does_not_overwrite_math",
         "同科不同教师配置独立另有 same_subject_teacher_configs_independent"),
    ("class-data-isolation", "篡改 URL 参数跨班访问被拦截"):
        ("确认覆盖", "check_lessons_2_5", "materials.cross_class_list_denied",
         "URL 参数跨班返回 403；审计由全局 403 记录断言"),
    ("login-and-account-system", "登出清除所有 Token 和状态"):
        ("确认覆盖", "check_lesson10_review", "登出清除所有 Token 和状态：前端清本地状态并跳转登录，后端清 Cookie",
         ""),
    ("material-upload", "学生尝试删除资料被拒"):
        ("确认覆盖", "check_lesson10_review", "学生尝试删除资料被拒：学生调用删除接口 403 且资料保留", ""),
    ("mcp-tool-integration", "打开 Swagger 试调"):
        ("N/A（不适用）", "", "需以 ENABLE_DOCS=true 启动并用浏览器携带教师令牌试调，属本地接口文档人工验证；"
                              "默认关闭已由 check_lesson10_scenario_gaps 断言", ""),
    ("mcp-tool-integration", "学生写入拒绝且 SSE 完整"):
        ("部分覆盖", "check_mcp_tools", "学生身份不能执行可写工具（不采信角色声明）",
         "拒绝与零执行有断言；SSE meta+done 完整性由同文件首帧与结束帧断言覆盖"),
    ("rag-search", "坐标题检索夹角余弦公式"):
        ("确认覆盖", "check_formula_retrieval", "{mode} formula recalled despite coordinate distractor",
         "原文摘录不变与来源指纹精确同文件"),
    ("research-materials", "立体几何章节带知识点标签"):
        ("确认覆盖", "check_research_materials", "geometry chapter creates knowledge topic", ""),
    ("smart-lesson-prep", "数学教师发起线面角备课"):
        ("确认覆盖", "check_lesson_prep", "teacher draft saved with actual stream",
         "出处摘录与行号可追溯同文件"),
    ("smart-question-generation", "数学教师按配比发起命题"):
        ("确认覆盖", "check_question_bank", "全部通过 8 题落库", "按数学学科组织上下文"),
    ("smart-question-generation", "学生调用命题接口"):
        ("确认覆盖", "check_question_bank", "学生访问题库 403", ""),
    ("smart-question-generation", "按 3:5:2 组卷"):
        ("确认覆盖", "check_question_bank", "组卷 13 题", "总分 80 同组断言"),
    ("smart-question-generation", "同一教师重复点击生成"):
        ("确认覆盖", "check_question_bank", "登记未过期：再次生成 409", ""),
    ("teacher-identity-and-permissions", "任课老师仅看本学科成绩"):
        ("确认覆盖", "check_analytics", "S1 正常：任课查看 102 数学学情", ""),
    ("teacher-workspace", "同一教师在任课页不展示重置操作"):
        ("确认覆盖", "check_lesson10_review",
         "同一教师在任课页不展示重置操作：操作列与按钮均受班主任身份控制", ""),
}


def reviewed(capability, scenario):
    return REVIEWED.get((capability, scenario))


def bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def load_check_names():
    names = {}
    # 同时匹配 check("...")、check('...')、check(`...`) 以及 Python 的 f-string 形式；
    # 反引号用于前端 .cjs 检查里的模板字符串断言名。
    pattern = r"""check\(\s*f?["'`]([^"'`]{2,160})["'`]"""
    for script in sorted((ROOT / "apitest").glob("check_*.py")):
        names[script.stem] = re.findall(pattern, script.read_text(encoding="utf-8"))
    for script in sorted((ROOT / "apitest").glob("check_*.cjs")):
        names[script.stem] = re.findall(pattern, script.read_text(encoding="utf-8"))
    return names


def load_corpus():
    corpus = {}
    for capability, scripts in CAPABILITY_CHECKS.items():
        for script in scripts:
            text = ""
            for path in sorted((ROOT / "apitest").glob(script + ".*")):
                text += path.read_text(encoding="utf-8", errors="ignore")
            if text:
                corpus.setdefault(capability, {})[script] = bigrams(text)
    return corpus


def parse_specs():
    rows = []
    for spec in sorted(SPECS.glob("*/spec.md")):
        capability = spec.parent.name
        requirement = "（未归入 Requirement）"
        for line in spec.read_text(encoding="utf-8").splitlines():
            if line.startswith("### Requirement:"):
                requirement = line.split(":", 1)[1].strip()
            elif line.startswith("#### Scenario:"):
                rows.append((capability, requirement, line.split(":", 1)[1].strip()))
    return rows


def best_assertion(capability, scenario, names):
    target = bigrams(scenario)
    best = None
    for script in CAPABILITY_CHECKS.get(capability, []):
        for name in names.get(script, []):
            overlap = len(target & bigrams(name))
            if best is None or overlap > best[2]:
                best = (script, name, overlap)
    return best


def alias_match(capability, scenario):
    """按人工等价表匹配；同一 Scenario 命中多条时取关键词最多的一条。"""
    best = None
    for keywords, script, assertion in ALIASES:
        if all(word in scenario for word in keywords):
            if best is None or len(keywords) > len(best[0]):
                best = (keywords, script, assertion)
    return best


def classify(capability, scenario, names, corpus):
    """返回 (判定, 候选脚本, 候选断言, 复核备注, 重叠数)。

    判定顺序：人工复核表 → 关键词别名 → 人工语义别名 → bigram 强匹配 → N/A
    → 弱候选 → 仅文件级 → 待补断言 / 无检查文件。人工复核表覆盖生成时
    bigram 只有 2–5 的全部弱候选，避免低重合噪声把未复核条目留在报告里。
    """
    review = reviewed(capability, scenario)
    if review:
        verdict, script, assertion, note = review
        if verdict == "已知缺口":
            return ("已知缺口", script, assertion, note, 0)
        if verdict == "N/A（不适用）":
            return ("N/A（不适用）", script, assertion, note, 0)
        return (f"人工复核（{verdict}）", script, assertion, note, 0)
    gap = known_gap(scenario)
    if gap:
        return ("已知缺口", "check_mcp_tools", gap[1], gap[0], 0)
    alias = alias_match(capability, scenario)
    if alias:
        return ("别名候选", alias[1], alias[2], "", len(alias[0]))
    semantic = semantic_alias(capability, scenario)
    if semantic:
        return ("语义别名候选", semantic[1], semantic[2], "", semantic[0])
    best = best_assertion(capability, scenario, names)
    if best and best[2] >= 6:
        return ("断言名候选", best[0], best[1], "", best[2])
    reason = na_reason(scenario)
    if reason:
        return ("N/A（不适用）", "", reason, "", 0)
    if best and best[2] >= 2:
        return ("弱候选", best[0], best[1], "", best[2])
    target = bigrams(scenario)
    file_best = None
    for script, grams in corpus.get(capability, {}).items():
        overlap = len(target & grams)
        if file_best is None or overlap > file_best[1]:
            file_best = (script, overlap)
    if file_best and file_best[1] >= 4:
        return ("仅文件级", file_best[0], "（未定位到具体断言）", "", file_best[1])
    if corpus.get(capability):
        return ("待补断言", "", "（同能力有检查文件但无相近断言）", "", 0)
    return ("无检查文件", "", "（该能力未登记检查文件）", "", 0)


FRONTEND_HINTS = ("前端", "页面", "界面", "展示", "显示", "渲染", "卡片", "按钮", "滚动",
                  "样式", "视觉", "刷新页面", "空状态", "逐字", "提示")


def gap_kind(scenario: str) -> str:
    return "前端/展示" if any(word in scenario for word in FRONTEND_HINTS) else "接口/逻辑"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()

    names = load_check_names()
    corpus = load_corpus()
    scenarios = parse_specs()

    rows = []
    for capability, requirement, scenario in scenarios:
        level, script, assertion, note, overlap = classify(capability, scenario, names, corpus)
        rows.append((capability, requirement, scenario, level, script, assertion, note, overlap))
    unmatched = sorted(set(REVIEWED) - {(row[0], row[2]) for row in rows})

    order = {"无检查文件": 0, "待补断言": 1, "已知缺口": 2, "N/A（不适用）": 3, "仅文件级": 4,
             "弱候选": 5, "断言名候选": 6, "语义别名候选": 7, "别名候选": 8,
             "人工复核（确认覆盖）": 9, "人工复核（部分覆盖）": 10}
    columns = ["人工复核（确认覆盖）", "人工复核（部分覆盖）", "断言名候选", "别名候选",
               "语义别名候选", "弱候选", "仅文件级", "N/A（不适用）", "已知缺口",
               "待补断言", "无检查文件"]
    counts = {key: sum(1 for r in rows if r[3] == key) for key in order}

    lines = [
        "# 第10课场景逐条映射（候选）",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 主规约 Scenario 总数：**{len(rows)}**",
        "",
        "| 判定 | 条数 | 含义 |",
        "| --- | --- | --- |",
        f"| 人工复核（确认覆盖） | {counts['人工复核（确认覆盖）']} | 弱候选逐条复核后确认现有断言覆盖，见「人工复核清单」 |",
        f"| 人工复核（部分覆盖） | {counts['人工复核（部分覆盖）']} | 现有断言只覆盖一半，备注写明未断言部分，不得计入完全覆盖 |",
        f"| 断言名候选（重叠≥6） | {counts['断言名候选']} | Scenario 与断言名 bigram 高度重合，仍需人工确认强度 |",
        f"| 别名候选（关键词表） | {counts['别名候选']} | 按标题关键词建立的等价映射 |",
        f"| 语义别名候选（人工表） | {counts['语义别名候选']} | 中文 Scenario 与英文/异措辞断言逐条核对后的人工等价 |",
        f"| 弱候选（2–5） | {counts['弱候选']} | bigram 低重合；本报告要求为 **0**，非 0 即仍有未复核条目 |",
        f"| 仅文件级 | {counts['仅文件级']} | 只能定位到检查文件，未定位断言 |",
        f"| N/A（不适用） | {counts['N/A（不适用）']} | 前端交互/真实模型语义/需容器或外部服务，见第三节理由 |",
        f"| 已知缺口 | {counts['已知缺口']} | 规格条款未被实现完全满足，见「已知缺口」节，不得计入覆盖 |",
        f"| 待补断言 | {counts['待补断言']} | 同能力有检查文件但无对应断言，**补检查优先队列** |",
        f"| 无检查文件 | {counts['无检查文件']} | 该能力未登记检查文件 |",
        "",
        "> 本表只给候选，不等于语义证明。人工复核须逐条确认断言强度、失败路径与边界；"
        "「别名候选」与「语义别名候选」都是人工建立的等价映射，同样需要人工确认；"
        "「待补断言」「无检查文件」是补检查的优先队列，不能当作已覆盖；"
        "「N/A（不适用）」只表示该场景无法用离线门禁断言证明，不表示已验证；"
        "「已知缺口」是规格已要求但实现只部分满足的条目，必须单列，不得计入覆盖。",
        "",
        "## 按能力统计",
        "",
        "| 能力 | 总数 | " + " | ".join(columns) + " |",
        "| --- | --- | " + " | ".join("---" for _ in columns) + " |",
    ]
    for capability in sorted({r[0] for r in rows}):
        subset = [r for r in rows if r[0] == capability]
        cells = [sum(1 for r in subset if r[3] == key) for key in columns]
        lines.append(f"| {capability} | {len(subset)} | " + " | ".join(str(c) for c in cells) + " |")

    lines += [
        "",
        "## 已知缺口（规格条款未被实现完全满足）",
        "",
        "| 能力 | Scenario | 缺口说明 | 部分证据 |",
        "| --- | --- | --- | --- |",
    ]
    known_rows = [r for r in rows if r[3] == "已知缺口"]
    for capability, requirement, scenario, _, script, assertion, note, _ in sorted(
            known_rows, key=lambda r: (r[0], r[2])):
        manual = reviewed(capability, scenario)
        reason = note if manual else (known_gap(scenario) or ("", ""))[0]
        evidence = f"{script}：{esc(assertion)}" if script else "—（未实现，无部分证据）"
        lines.append(f"| {capability} | {esc(scenario)} | {esc(reason)} | {evidence} |")
    if not known_rows:
        lines.append("| — | — | — | — |")

    lines += [
        "",
        "## 不适用清单（N/A，逐条理由）",
        "",
        "| 能力 | Scenario | 不适用理由 |",
        "| --- | --- | --- |",
    ]
    na_rows = [r for r in rows if r[3] == "N/A（不适用）"]
    for capability, requirement, scenario, _, _, reason, _, _ in sorted(na_rows, key=lambda r: (r[0], r[2])):
        lines.append(f"| {capability} | {esc(scenario)} | {esc(reason)} |")
    if not na_rows:
        lines.append("| — | — | — |")

    lines += [
        "",
        "## 人工复核清单（生成时 bigram 弱候选逐条，结论与证据）",
        "",
        "| 能力 | Scenario | 结论 | 检查脚本 | 断言 | 备注 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    reviewed_rows = [r for r in rows if r[3].startswith("人工复核") or
                     (r[3] in ("已知缺口", "N/A（不适用）") and reviewed(r[0], r[2]))]
    for capability, requirement, scenario, level, script, assertion, note, _ in sorted(
            reviewed_rows, key=lambda r: (r[0], r[2])):
        if level == "已知缺口":
            verdict = "已知缺口"
        elif level == "N/A（不适用）":
            verdict = "N/A"
        else:
            verdict = level.removeprefix("人工复核（").removesuffix("）")
        lines.append(f"| {capability} | {esc(scenario)} | {verdict} | {script} | "
                     f"{esc(assertion)} | {esc(note)} |")
    if not reviewed_rows:
        lines.append("| — | — | — | — | — | — |")

    lines += [
        "",
        "## 需要补检查的场景（待补断言 / 无检查文件，按高风险能力优先）",
        "",
        "| 优先级 | 类别 | 能力 | Requirement | Scenario | 判定 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    gaps = [r for r in rows if r[3] in ("待补断言", "无检查文件")]
    gaps.sort(key=lambda r: (0 if r[0] in HIGH_RISK_CAPABILITIES else 1, gap_kind(r[2]), r[0], r[1], r[2]))
    for capability, requirement, scenario, level, _, _, _, _ in gaps:
        priority = "P0" if capability in HIGH_RISK_CAPABILITIES else "P1"
        lines.append(f"| {priority} | {gap_kind(scenario)} | {capability} | {esc(requirement)} | "
                     f"{esc(scenario)} | {level} |")

    lines += [
        "",
        "## 逐条候选",
        "",
        "| 能力 | Requirement | Scenario | 判定 | 候选检查 | 候选断言 / N/A 理由 | 复核备注 | 重叠 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for capability, requirement, scenario, level, script, assertion, note, overlap in sorted(
            rows, key=lambda r: (r[0], r[1], r[2])):
        lines.append(f"| {capability} | {esc(requirement)} | {esc(scenario)} | {level} | {script} | "
                     f"{esc(assertion)} | {esc(note)} | {overlap} |")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), **counts,
                      "gaps": len(gaps),
                      "p0_gaps": sum(1 for r in gaps if r[0] in HIGH_RISK_CAPABILITIES),
                      "gap_api": sum(1 for r in gaps if gap_kind(r[2]) == "接口/逻辑"),
                      "gap_frontend": sum(1 for r in gaps if gap_kind(r[2]) == "前端/展示"),
                      "reviewed_total": len(REVIEWED),
                      "reviewed_unmatched": unmatched},
                     ensure_ascii=False))
    return 0


def esc(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
