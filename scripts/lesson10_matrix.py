"""第10课场景矩阵：把现行主规约的 Requirement/Scenario 与实际检查名对齐。

只读、可重复。匹配是关键词候选，不等于语义证明；输出把"候选"和"空项"分开，
避免把脚本存在说成 Scenario 已覆盖。人工复核后在 reports/scenario-matrix.md
的复核栏追加结论。
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "openspec/specs"
OUT_DEFAULT = ROOT / "reports/scenario-matrix.md"

# 能力 → 实际承担该能力检查的脚本。一个脚本可服务多个能力，但不会跨能力乱配。
CAPABILITY_CHECKS = {
    "agent-assistant": ["check_lessons_2_5", "check_recent_history", "check_mcp_tools"],
    "async-homework-grading": ["check_async_grading", "check_homework", "check_quiz_homework"],
    "class-data-isolation": ["check_baseline", "check_injection", "check_lessons_2_5"],
    "login-and-account-system": ["check_baseline", "check_route_guard"],
    "material-upload": ["check_markdown_images", "check_lesson_prep", "check_research_materials"],
    "mcp-tool-integration": ["check_mcp_tools", "check_security_gate"],
    "quiz-homework-publication": ["check_quiz_homework", "check_question_bank"],
    "rag-search": ["check_formula_retrieval", "check_lessons_2_5"],
    "rbac-role-permissions": ["check_injection", "check_baseline", "check_security_gate"],
    "research-materials": ["check_research_materials"],
    "runtime-reliability": ["check_baseline", "check_sqlite_storage"],
    "smart-lesson-prep": ["check_lesson_prep"],
    "smart-question-generation": ["check_question_bank"],
    "student-workspace": ["check_recent_history", "check_homework"],
    "teacher-identity-and-permissions": ["check_baseline", "check_security_gate"],
    "teacher-workspace": ["check_teacher_navigation", "check_assignment_history_ui"],
}

# 四项必做技能的显式证据，优先于关键词匹配。
MUST_DO = [
    ("解题引导不给最终答案", "agent-assistant", "check_lessons_2_5 / probe_tutor_guidance / 本次新增反例"),
    ("教师终评优先", "async-homework-grading", "check_async_grading（C2）/ 本次 mutation"),
    ("错题讲解不贴标准答案", "mistake-notebook（现存变更）", "check_mistake / 本次新增反例"),
    ("知识库跨班为空", "rag-search", "check_lessons_2_5 / probe_security_precheck（A/B）"),
]


def load_check_names():
    names = {}
    for script in sorted((ROOT / "apitest").glob("check_*.py")):
        text = script.read_text(encoding="utf-8")
        names[script.stem] = re.findall(r'check\(\s*"([^"]{2,120})"', text)
    for script in sorted((ROOT / "apitest").glob("check_*.cjs")):
        text = script.read_text(encoding="utf-8")
        names[script.stem] = re.findall(r"check\(\s*[`'\"]([^`'\"]{2,120})[`'\"]", text)
    return names


def load_corpus():
    """每个能力对应脚本的全文二元组：注释、docstring、断言名都算候选线索。"""
    corpus = {}
    for capability, scripts in CAPABILITY_CHECKS.items():
        per_script = {}
        for script in scripts:
            text = ""
            for path in sorted((ROOT / "apitest").glob(script + ".*")):
                text += path.read_text(encoding="utf-8", errors="ignore")
            if text:
                per_script[script] = bigrams(text)
        corpus[capability] = per_script
    return corpus


def bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def parse_specs():
    result = []
    for spec in sorted(SPECS.glob("*/spec.md")):
        capability = spec.parent.name
        requirement = None
        for line in spec.read_text(encoding="utf-8").splitlines():
            if line.startswith("### Requirement:"):
                requirement = line.split(":", 1)[1].strip()
            elif line.startswith("#### Scenario:"):
                result.append((capability, requirement or "（未归入 Requirement）", line.split(":", 1)[1].strip()))
    return result


def match(capability, scenario, names, corpus):
    """返回 (层级, 证据描述)。断言名命中优先，其次文件级候选，否则空项。"""
    target = bigrams(scenario)
    best = None
    for script in CAPABILITY_CHECKS.get(capability, []):
        for name in names.get(script, []):
            overlap = target & bigrams(name)
            if len(overlap) >= 4 and (best is None or len(overlap) > best[2]):
                best = (script, name, len(overlap))
    if best:
        return ("断言名候选", f"{best[0]}：{best[1]}（共享 {best[2]} 个二元组）")
    script_best = None
    for script, grams in corpus.get(capability, {}).items():
        overlap = len(target & grams)
        if overlap >= 4 and (script_best is None or overlap > script_best[1]):
            script_best = (script, overlap)
    if script_best:
        return ("文件级候选", f"{script_best[0]}（全文共享 {script_best[1]} 个二元组，未定位到具体断言）")
    if corpus.get(capability):
        return ("能力级待映射", "该能力已有检查文件，但未定位到具体 Scenario；需人工逐条确认")
    return ("空项", "该能力没有登记检查文件")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    names = load_check_names()
    corpus = load_corpus()
    scenarios = parse_specs()
    rows = []
    for capability, requirement, scenario in scenarios:
        level, evidence = match(capability, scenario, names, corpus)
        rows.append((capability, requirement, scenario, level, evidence))

    covered = [r for r in rows if r[3] in ("断言名候选", "文件级候选")]
    assertion_level = [r for r in covered if r[3] == "断言名候选"]
    file_level = [r for r in covered if r[3] == "文件级候选"]
    capability_pending = [r for r in rows if r[3] == "能力级待映射"]
    gaps = [r for r in rows if r[3] == "空项"]
    by_capability = {}
    for row in rows:
        bucket = {"断言名候选": 0, "文件级候选": 1, "能力级待映射": 2, "空项": 3}[row[3]]
        by_capability.setdefault(row[0], [0, 0, 0, 0])[bucket] += 1

    lines = [
        "# 第10课场景矩阵",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 主规约 Scenario 总数：**{len(rows)}**；断言名候选：**{len(assertion_level)}**；文件级候选：**{len(file_level)}**；能力级待映射：**{len(capability_pending)}**；空项：**{len(gaps)}**",
        "- 匹配规则：Scenario 标题与同能力检查的断言名/脚本全文共享 ≥4 个字符二元组。",
        "- **候选不等于语义证明**：断言名候选仍需确认断言强度与失败路径；文件级候选只说明脚本提到相关词；",
        "  能力级待映射表示该能力有检查文件但未定位到这条 Scenario，必须人工逐条确认，不能当作已覆盖；空项表示该能力没有登记检查文件。",
        "",
        "## 四项必做技能",
        "",
        "| 技能要求 | 能力 | 证据入口 | 状态 |",
        "| --- | --- | --- | --- |",
    ]
    for skill, capability, evidence in MUST_DO:
        lines.append(f"| {skill} | {capability} | {evidence} | 人工复核 |")

    lines += [
        "",
        "## 按能力统计",
        "",
        "| 能力 | Scenario 数 | 断言名候选 | 文件级候选 | 能力级待映射 | 空项 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for capability in sorted(by_capability):
        assertion, filelevel, pending, gap = by_capability[capability]
        lines.append(f"| {capability} | {assertion + filelevel + pending + gap} | {assertion} | {filelevel} | {pending} | {gap} |")

    lines += [
        "",
        "## 空项（该能力没有登记检查文件）",
        "",
        "| 能力 | Requirement | Scenario |",
        "| --- | --- | --- |",
    ]
    for capability, requirement, scenario, _, _ in gaps:
        lines.append(f"| {capability} | {requirement.replace('|', '\\|')} | {scenario.replace('|', '\\|')} |")

    lines += [
        "",
        "## 能力级待映射（需人工逐条确认）",
        "",
        "| 能力 | Requirement | Scenario |",
        "| --- | --- | --- |",
    ]
    for capability, requirement, scenario, _, _ in capability_pending:
        lines.append(f"| {capability} | {requirement.replace('|', '\\|')} | {scenario.replace('|', '\\|')} |")

    lines += [
        "",
        "## 候选映射（需人工复核）",
        "",
        "| 能力 | Requirement | Scenario | 层级 | 候选证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for capability, requirement, scenario, level, evidence in covered:
        lines.append(f"| {capability} | {requirement.replace('|', '\\|')} | {scenario.replace('|', '\\|')} | {level} | {evidence.replace('|', '\\|')} |")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), "assertion": len(assertion_level),
                      "file_level": len(file_level), "capability_pending": len(capability_pending),
                      "gaps": len(gaps)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
