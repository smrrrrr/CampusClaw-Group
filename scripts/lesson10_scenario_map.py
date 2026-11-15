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


def bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def load_check_names():
    names = {}
    # 同时匹配 check("...")、check('...') 与 check(f"...")/check(f'...')（含占位符断言名）
    pattern = r"""check\(\s*f?["']([^"']{2,160})["']"""
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
    """返回 (判定, 候选脚本, 候选断言, 重叠数)。

    判定顺序：关键词别名 → 人工语义别名 → bigram 强匹配 → N/A → 弱候选 →
    仅文件级 → 待补断言 / 无检查文件。N/A 放在弱候选之前，避免 2–5 个
    bigram 的噪声把「本就不适用」的条目误算成覆盖。
    """
    gap = known_gap(scenario)
    if gap:
        return ("已知缺口", "check_mcp_tools", gap[1], 0)
    alias = alias_match(capability, scenario)
    if alias:
        return ("别名候选", alias[1], alias[2], len(alias[0]))
    semantic = semantic_alias(capability, scenario)
    if semantic:
        return ("语义别名候选", semantic[1], semantic[2], semantic[0])
    best = best_assertion(capability, scenario, names)
    if best and best[2] >= 6:
        return ("断言名候选", best[0], best[1], best[2])
    reason = na_reason(scenario)
    if reason:
        return ("N/A（不适用）", "", reason, 0)
    if best and best[2] >= 2:
        return ("弱候选", best[0], best[1], best[2])
    target = bigrams(scenario)
    file_best = None
    for script, grams in corpus.get(capability, {}).items():
        overlap = len(target & grams)
        if file_best is None or overlap > file_best[1]:
            file_best = (script, overlap)
    if file_best and file_best[1] >= 4:
        return ("仅文件级", file_best[0], "（未定位到具体断言）", file_best[1])
    if corpus.get(capability):
        return ("待补断言", "", "（同能力有检查文件但无相近断言）", 0)
    return ("无检查文件", "", "（该能力未登记检查文件）", 0)


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
        level, script, assertion, overlap = classify(capability, scenario, names, corpus)
        rows.append((capability, requirement, scenario, level, script, assertion, overlap))

    order = {"无检查文件": 0, "待补断言": 1, "已知缺口": 2, "N/A（不适用）": 3, "仅文件级": 4,
             "弱候选": 5, "断言名候选": 6, "语义别名候选": 7, "别名候选": 8}
    columns = ["断言名候选", "别名候选", "语义别名候选", "弱候选", "仅文件级",
               "N/A（不适用）", "已知缺口", "待补断言", "无检查文件"]
    counts = {key: sum(1 for r in rows if r[3] == key) for key in order}

    lines = [
        "# 第10课场景逐条映射（候选）",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 主规约 Scenario 总数：**{len(rows)}**",
        "",
        "| 判定 | 条数 | 含义 |",
        "| --- | --- | --- |",
        f"| 断言名候选（重叠≥6） | {counts['断言名候选']} | Scenario 与断言名 bigram 高度重合，仍需人工确认强度 |",
        f"| 别名候选（关键词表） | {counts['别名候选']} | 按标题关键词建立的等价映射 |",
        f"| 语义别名候选（人工表） | {counts['语义别名候选']} | 中文 Scenario 与英文/异措辞断言逐条核对后的人工等价 |",
        f"| 弱候选（2–5） | {counts['弱候选']} | bigram 低重合，噪声较多 |",
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
    for capability, requirement, scenario, _, script, assertion, _ in sorted(
            known_rows, key=lambda r: (r[0], r[2])):
        reason = (known_gap(scenario) or ("", ""))[0]
        lines.append(f"| {capability} | {esc(scenario)} | {esc(reason)} | {script}：{esc(assertion)} |")
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
    for capability, requirement, scenario, _, _, reason, _ in sorted(na_rows, key=lambda r: (r[0], r[2])):
        lines.append(f"| {capability} | {esc(scenario)} | {esc(reason)} |")
    if not na_rows:
        lines.append("| — | — | — |")

    lines += [
        "",
        "## 需要补检查的场景（待补断言 / 无检查文件，按高风险能力优先）",
        "",
        "| 优先级 | 类别 | 能力 | Requirement | Scenario | 判定 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    gaps = [r for r in rows if r[3] in ("待补断言", "无检查文件")]
    gaps.sort(key=lambda r: (0 if r[0] in HIGH_RISK_CAPABILITIES else 1, gap_kind(r[2]), r[0], r[1], r[2]))
    for capability, requirement, scenario, level, _, _, _ in gaps:
        priority = "P0" if capability in HIGH_RISK_CAPABILITIES else "P1"
        lines.append(f"| {priority} | {gap_kind(scenario)} | {capability} | {esc(requirement)} | "
                     f"{esc(scenario)} | {level} |")

    lines += [
        "",
        "## 逐条候选",
        "",
        "| 能力 | Requirement | Scenario | 判定 | 候选检查 | 候选断言 / N/A 理由 | 重叠 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for capability, requirement, scenario, level, script, assertion, overlap in sorted(
            rows, key=lambda r: (r[0], r[1], r[2])):
        lines.append(f"| {capability} | {esc(requirement)} | {esc(scenario)} | {level} | {script} | "
                     f"{esc(assertion)} | {overlap} |")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), **counts,
                      "gaps": len(gaps),
                      "p0_gaps": sum(1 for r in gaps if r[0] in HIGH_RISK_CAPABILITIES),
                      "gap_api": sum(1 for r in gaps if gap_kind(r[2]) == "接口/逻辑"),
                      "gap_frontend": sum(1 for r in gaps if gap_kind(r[2]) == "前端/展示")},
                     ensure_ascii=False))
    return 0


def esc(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
