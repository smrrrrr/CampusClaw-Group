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
    "agent-assistant": ["check_lessons_2_5", "check_recent_history", "check_mcp_tools", "check_lesson10_skills"],
    "async-homework-grading": ["check_async_grading", "check_homework", "check_quiz_homework"],
    "class-data-isolation": ["check_baseline", "check_injection", "check_lessons_2_5",
                             "check_lesson10_p0_scenarios"],
    "login-and-account-system": ["check_baseline", "check_route_guard", "check_security_gate",
                                 "check_lesson10_scenarios", "check_lesson10_p0_scenarios"],
    "material-upload": ["check_markdown_images", "check_lesson_prep", "check_research_materials"],
    "mcp-tool-integration": ["check_mcp_tools", "check_security_gate"],
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
    "smart-question-generation": ["check_question_bank"],
    "student-workspace": ["check_recent_history", "check_homework", "check_lessons_2_5", "check_analytics"],
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


def bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def load_check_names():
    names = {}
    for script in sorted((ROOT / "apitest").glob("check_*.py")):
        names[script.stem] = re.findall(r'check\(\s*"([^"]{2,120})"', script.read_text(encoding="utf-8"))
    for script in sorted((ROOT / "apitest").glob("check_*.cjs")):
        names[script.stem] = re.findall(r"check\(\s*[`'\"]([^`'\"]{2,120})[`'\"]",
                                        script.read_text(encoding="utf-8"))
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
    """返回 (判定, 候选脚本, 候选断言, 重叠数)。"""
    alias = alias_match(capability, scenario)
    if alias:
        return ("别名候选", alias[1], alias[2], len(alias[0]))
    best = best_assertion(capability, scenario, names)
    if best and best[2] >= 6:
        return ("断言名候选", best[0], best[1], best[2])
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
        return ("无匹配断言", "", "（同能力有检查文件但无相近断言）", 0)
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

    order = {"无检查文件": 0, "无匹配断言": 1, "仅文件级": 2, "弱候选": 3, "断言名候选": 4, "别名候选": 5}
    columns = ["断言名候选", "别名候选", "弱候选", "仅文件级", "无匹配断言", "无检查文件"]
    counts = {key: sum(1 for r in rows if r[3] == key) for key in order}

    lines = [
        "# 第10课场景逐条映射（候选）",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 主规约 Scenario 总数：**{len(rows)}**",
        f"- 断言名候选（重叠≥6）：**{counts['断言名候选']}**；别名候选（人工等价初稿）：**{counts['别名候选']}**；"
        f"弱候选（2–5）：**{counts['弱候选']}**；仅文件级：**{counts['仅文件级']}**；"
        f"无匹配断言：**{counts['无匹配断言']}**；无检查文件：**{counts['无检查文件']}**",
        "",
        "> 本表只给候选，不等于语义证明。人工复核须逐条确认断言强度、失败路径与边界；"
        "「别名候选」是按标题关键词建立的等价映射初稿，同样需要人工确认；"
        "「无匹配断言」与「无检查文件」是补检查的优先队列，不能当作已覆盖。",
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
        "## 需要补检查的场景（无匹配断言 / 无检查文件，按高风险能力优先）",
        "",
        "| 优先级 | 类别 | 能力 | Requirement | Scenario | 判定 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    gaps = [r for r in rows if r[3] in ("无匹配断言", "无检查文件")]
    gaps.sort(key=lambda r: (0 if r[0] in HIGH_RISK_CAPABILITIES else 1, gap_kind(r[2]), r[0], r[1], r[2]))
    for capability, requirement, scenario, level, _, _, _ in gaps:
        priority = "P0" if capability in HIGH_RISK_CAPABILITIES else "P1"
        lines.append(f"| {priority} | {gap_kind(scenario)} | {capability} | {esc(requirement)} | "
                     f"{esc(scenario)} | {level} |")

    lines += [
        "",
        "## 逐条候选",
        "",
        "| 能力 | Requirement | Scenario | 判定 | 候选检查 | 候选断言 | 重叠 |",
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
