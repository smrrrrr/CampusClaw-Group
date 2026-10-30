"""学情诊断单元测试：纯函数与可 mock 的解析逻辑（add-learning-diagnostics）。

聚焦 analytics_service 中不依赖数据库的逻辑：
  - _subject_mastery：掌握度算法（成绩 60% + 错题掌握率 40%）
  - _assert_teacher_can_view_class：教师班级/学科权限判定
  - AnalyticsServiceError：业务异常属性
  - generate_student_portrait：LLM JSON 解析与降级（mock 掉 DB 与模型）

不创建表、不连 HTTP、不调用真实模型。
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


with tempfile.TemporaryDirectory(prefix="analytics-unit-", ignore_cleanup_errors=True) as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'unit.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")

    import analytics_service
    from analytics_service import (
        AnalyticsServiceError,
        TeacherContext,
        UserContext,
        _assert_teacher_can_view_class,
        _subject_mastery,
    )

    # ==================================================================
    # _subject_mastery：掌握度算法
    # ==================================================================

    # --- 无数据 ---
    check("U1 边界：无成绩无错题 → None", _subject_mastery([], 0, 0) is None)

    # --- 仅有成绩 ---
    check("U1 正常：单条成绩直接取平均分", _subject_mastery([80], 0, 0) == 80)
    check("U1 正常：多条成绩取平均", _subject_mastery([60, 80], 0, 0) == 70)
    check("U1 边界：满分成绩 → 100", _subject_mastery([100], 0, 0) == 100)
    check("U1 边界：零分成绩 → 0", _subject_mastery([0], 0, 0) == 0)
    check("U1 边界：99 分四舍五入为 99", _subject_mastery([99], 0, 0) == 99)

    # --- 仅有错题 ---
    check("U1 正常：错题全部掌握 → 100", _subject_mastery([], 2, 2) == 100)
    check("U1 正常：错题全未掌握 → 0", _subject_mastery([], 3, 0) == 0)
    check("U1 正常：错题半掌握 → 50", _subject_mastery([], 4, 2) == 50)

    # --- 成绩 + 错题：accuracy*60 + mastery_rate*40 ---
    # 成绩满分(1.0) + 错题全掌握(1.0) → 60+40 = 100
    check("U1 正常：成绩满分且错题全掌握 → 100", _subject_mastery([100], 2, 2) == 100)
    # 成绩零分(0) + 错题全未掌握(0) → 0
    check("U1 正常：成绩零分且错题全未掌握 → 0", _subject_mastery([0], 2, 0) == 0)
    # 成绩 50(0.5) + 错题半掌握(0.5) → 30+20 = 50
    check("U1 正常：成绩半分错题半掌握 → 50", _subject_mastery([50], 4, 2) == 50)
    # 成绩 100(1.0) + 错题半掌握(0.5) → 60+20 = 80
    check("U1 正常：成绩满分错题半掌握 → 80", _subject_mastery([100], 2, 1) == 80)
    # 成绩 80(0.8) + 错题全掌握(1.0) → 48+40 = 88
    check("U1 正常：成绩 80 错题全掌握 → 88", _subject_mastery([80], 1, 1) == 88)

    # ==================================================================
    # _assert_teacher_can_view_class：权限判定
    # ==================================================================

    teacher = TeacherContext(
        user_id=1, role="teacher",
        teaching_classes=[101, 102], subject="math", homeroom_class_id=101,
    )

    # 班级在任教列表内 → 不抛
    ok = True
    try:
        _assert_teacher_can_view_class(teacher, 102, None)
    except AnalyticsServiceError:
        ok = False
    check("U2 正常：任教班级可查看", ok)

    # 班级是班主任班（不在 teaching_classes 显式列表也允许）→ 不抛
    ok = True
    try:
        _assert_teacher_can_view_class(teacher, 101, None)
    except AnalyticsServiceError:
        ok = False
    check("U2 正常：班主任班级可查看", ok)

    # 班级既不在任教也不是班主任班 → 403
    raised = False
    try:
        _assert_teacher_can_view_class(teacher, 999, None)
    except AnalyticsServiceError as e:
        raised = e.status_code == 403
    check("U2 失败：跨班访问 → 403", raised)

    # 学科匹配 → 不抛
    ok = True
    try:
        _assert_teacher_can_view_class(teacher, 102, "math")
    except AnalyticsServiceError:
        ok = False
    check("U2 正常：同学科可查看", ok)

    # 学科不匹配 → 403
    raised = False
    try:
        _assert_teacher_can_view_class(teacher, 102, "english")
    except AnalyticsServiceError as e:
        raised = e.status_code == 403
    check("U2 失败：跨学科访问 → 403", raised)

    # teaching_classes 为空、无班主任班 → 任何班级都 403
    empty_teacher = TeacherContext(
        user_id=2, role="teacher",
        teaching_classes=None, subject="math", homeroom_class_id=None,
    )
    raised = False
    try:
        _assert_teacher_can_view_class(empty_teacher, 101, None)
    except AnalyticsServiceError as e:
        raised = e.status_code == 403
    check("U2 边界：无任教班级时访问 → 403", raised)

    # ==================================================================
    # AnalyticsServiceError：异常属性
    # ==================================================================
    err = AnalyticsServiceError(403, "无权查看")
    check("U3 正常：异常携带 status_code", err.status_code == 403)
    check("U3 正常：异常携带 detail", err.detail == "无权查看")
    check("U3 正常：异常消息为 detail", str(err) == "无权查看")

    # ==================================================================
    # generate_student_portrait：LLM JSON 解析与降级
    # ==================================================================

    # mock 掉 DB 依赖的两个函数，固定返回统计摘要
    original_overview = analytics_service.get_student_overview
    original_mastery = analytics_service.get_student_mastery
    original_generate = analytics_service.generate_answer
    original_load = analytics_service.load_model_json

    analytics_service.get_student_overview = lambda db, ctx: {
        "questions": 5, "submissions": 3, "accuracy": 75, "mistakes": 2,
    }
    analytics_service.get_student_mastery = lambda db, ctx: {
        "subjects": [
            {"subject": "math", "subject_name": "数学", "mastery": 88,
             "homework_count": 2, "mistake_count": 1, "unmastered_count": 0},
        ],
        "overall": 88,
        "trend": [],
    }

    # --- 正常：模型返回合法 JSON ---
    analytics_service.generate_answer = lambda *a, **k: (
        '{"style":"逻辑推理型","strengths":["数学"],"weaknesses":["物理"],'
        '"suggestion":"多做物理基础题"}'
    )
    portrait, available = analytics_service.generate_student_portrait(db=None, ctx=UserContext(user_id=1, role="student"))
    check("U4 正常：画像可用且解析正确", available is True and portrait is not None)
    check("U4 正常：画像 style 字段", portrait and portrait["style"] == "逻辑推理型")
    check("U4 正常：画像 strengths 列表", portrait and portrait["strengths"] == ["数学"])
    check("U4 正常：画像 weaknesses 列表", portrait and portrait["weaknesses"] == ["物理"])
    check("U4 正常：画像 suggestion 字段", portrait and portrait["suggestion"] == "多做物理基础题")

    # --- 验证发给模型的摘要不含题目/作答原文 ---
    captured = {}

    def capture_generate(question, context_block, *, system_prompt=None, tutor_enabled=False):
        captured["summary"] = question
        return '{"style":"x","strengths":[],"weaknesses":[],"suggestion":"y"}'

    analytics_service.generate_answer = capture_generate
    analytics_service.generate_student_portrait(db=None, ctx=UserContext(user_id=1, role="student"))
    summary = captured.get("summary", "")
    check("U4 正常：摘要含累计提问数", "累计提问：5" in summary)
    check("U4 正常：摘要含作业提交数", "作业提交：3" in summary)
    check("U4 正常：摘要含作业正确率", "作业正确率：75" in summary)
    check("U4 正常：摘要含错题累计", "错题累计：2" in summary)
    check("U4 正常：摘要含学科掌握度", "数学：88分" in summary)
    check("U4 正常：摘要含综合掌握度", "综合掌握度：88分" in summary)

    # --- 失败：模型未配置（返回 None）---
    analytics_service.generate_answer = lambda *a, **k: None
    portrait, available = analytics_service.generate_student_portrait(db=None, ctx=UserContext(user_id=1, role="student"))
    check("U4 失败：模型未配置 → 不可用", available is False and portrait is None)

    # --- 失败：模型返回非法 JSON ---
    from model_json import ModelJSONError

    analytics_service.generate_answer = lambda *a, **k: "not-a-json"
    analytics_service.load_model_json = lambda raw: (_ for _ in ()).throw(ModelJSONError("bad"))
    portrait, available = analytics_service.generate_student_portrait(db=None, ctx=UserContext(user_id=1, role="student"))
    check("U4 失败：模型返回非法 JSON → 降级不可用", available is False and portrait is None)

    # --- 边界：JSON 缺字段时使用默认值 ---
    analytics_service.generate_answer = lambda *a, **k: '{"style":"归纳型"}'
    analytics_service.load_model_json = lambda raw: ({"style": "归纳型"}, None)
    portrait, available = analytics_service.generate_student_portrait(db=None, ctx=UserContext(user_id=1, role="student"))
    check("U4 边界：缺字段时 style 仍可取", available is True and portrait["style"] == "归纳型")
    check("U4 边界：缺 strengths 时默认为空列表", portrait["strengths"] == [])
    check("U4 边界：缺 weaknesses 时默认为空列表", portrait["weaknesses"] == [])
    check("U4 边界：缺 suggestion 时默认为空串", portrait["suggestion"] == "")

    # 恢复
    analytics_service.get_student_overview = original_overview
    analytics_service.get_student_mastery = original_mastery
    analytics_service.generate_answer = original_generate
    analytics_service.load_model_json = original_load


passed = sum(1 for _, p in checks if p)
total = len(checks)
print(f"\n结果：{passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
