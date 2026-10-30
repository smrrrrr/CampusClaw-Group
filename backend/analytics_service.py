"""学情诊断业务层：学生本人学情、学科掌握度、AI 画像、教师班级学情。

设计见 openspec/changes/add-learning-diagnostics/design.md。
规约见 openspec/changes/add-learning-diagnostics/specs/learning-diagnostics/spec.md。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from llm_service import generate_answer
from model_json import ModelJSONError, load_model_json
from models import Conversation, Homework, HomeworkSubmission, Message, MistakeNote, User

PORTRAIT_SYSTEM_PROMPT = (
    "你是一名资深学情分析师。根据学生的学习数据（各学科掌握度、累计提问、作业与错题情况），"
    "生成该学生的学习画像。请返回严格的 JSON 对象，包含以下字段：\n"
    '{"style": "学习风格标签（如归纳总结型、逻辑推理型等）", '
    '"strengths": ["优势学科列表，使用学科中文名"], '
    '"weaknesses": ["待提升学科列表，使用学科中文名"], '
    '"suggestion": "针对该生的具体学习建议，100字以内"}\n'
    "只返回 JSON，不要添加解释或 markdown 代码围栏。"
)


class AnalyticsServiceError(Exception):
    """业务层错误，由路由层转换为 HTTPException。"""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass
class UserContext:
    """学生上下文。"""

    user_id: int
    role: str
    class_id: int | None = None


@dataclass
class TeacherContext:
    """教师上下文。"""

    user_id: int
    role: str
    teaching_classes: list[int] | None = None
    subject: str | None = None
    homeroom_class_id: int | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _subject_mastery(
    scores: list[int], mistakes_total: int, mistakes_mastered: int
) -> int | None:
    """单学科掌握度（0-100）。无数据返回 None。

    成绩占 60%，错题掌握率占 40%；无作业退化为错题掌握率。
    """
    has_scores = len(scores) > 0
    has_mistakes = mistakes_total > 0

    if not has_scores and not has_mistakes:
        return None

    if has_scores:
        accuracy = sum(scores) / len(scores) / 100.0
        if has_mistakes:
            mastery_rate = mistakes_mastered / mistakes_total
            return round(accuracy * 60 + mastery_rate * 40)
        return round(accuracy * 100)

    # 仅有错题
    mastery_rate = mistakes_mastered / mistakes_total
    return round(mastery_rate * 100)


# ---------------------------------------------------------------------------
# 学生：学情概览
# ---------------------------------------------------------------------------


def get_student_overview(db: Session, ctx: UserContext) -> dict:
    """返回本人学情概览：累计提问、作业提交、作业正确率、错题累计。"""
    # 累计提问：本人会话中的 user 消息数
    question_count = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.student_id == ctx.user_id, Message.role == "user")
        .scalar()
        or 0
    )

    # 本人已批改提交
    graded_subs = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.student_id == ctx.user_id,
            HomeworkSubmission.teacher_score.isnot(None),
        )
        .all()
    )
    submission_count = len(graded_subs)

    accuracy: int | None = None
    if graded_subs:
        scores = [s.teacher_score for s in graded_subs if s.teacher_score is not None]
        if scores:
            accuracy = round(sum(scores) / len(scores))

    mistake_count = (
        db.query(func.count(MistakeNote.id))
        .filter(MistakeNote.student_id == ctx.user_id)
        .scalar()
        or 0
    )

    return {
        "questions": question_count,
        "submissions": submission_count,
        "accuracy": accuracy,
        "mistakes": mistake_count,
    }


# ---------------------------------------------------------------------------
# 学生：各学科掌握度
# ---------------------------------------------------------------------------


def get_student_mastery(db: Session, ctx: UserContext) -> dict:
    """返回各学科掌握度、综合掌握度、近期成绩趋势。"""
    # 取本人所有已批改提交，按学科分组
    subs = (
        db.query(HomeworkSubmission, Homework)
        .join(Homework, HomeworkSubmission.homework_id == Homework.id)
        .filter(
            HomeworkSubmission.student_id == ctx.user_id,
            HomeworkSubmission.teacher_score.isnot(None),
        )
        .all()
    )
    scores_by_subject: dict[str, list[int]] = {}
    for sub, hw in subs:
        scores_by_subject.setdefault(hw.subject, []).append(sub.teacher_score or 0)

    # 取本人错题，按学科分组
    notes = (
        db.query(MistakeNote)
        .filter(MistakeNote.student_id == ctx.user_id)
        .all()
    )
    mistakes_by_subject: dict[str, tuple[int, int]] = {}
    for n in notes:
        total, mastered = mistakes_by_subject.get(n.subject, (0, 0))
        total += 1
        if n.mastered:
            mastered += 1
        mistakes_by_subject[n.subject] = (total, mastered)

    subjects = []
    for subject_id in SUBJECT_NAMES:
        scores = scores_by_subject.get(subject_id, [])
        m_total, m_mastered = mistakes_by_subject.get(subject_id, (0, 0))
        mastery = _subject_mastery(scores, m_total, m_mastered)
        if mastery is not None:
            subjects.append(
                {
                    "subject": subject_id,
                    "subject_name": SUBJECT_NAMES[subject_id],
                    "mastery": mastery,
                    "homework_count": len(scores),
                    "mistake_count": m_total,
                    "unmastered_count": m_total - m_mastered,
                }
            )

    # 综合掌握度：所有非 null 学科的平均
    overall: int | None = None
    mastery_values = [s["mastery"] for s in subjects]
    if mastery_values:
        overall = round(sum(mastery_values) / len(mastery_values))

    # 近期趋势：按 teacher_graded_at 倒序最近 10 条
    trend_rows = (
        db.query(Homework.title, HomeworkSubmission.teacher_score, Homework.subject, HomeworkSubmission.teacher_graded_at)
        .join(Homework, HomeworkSubmission.homework_id == Homework.id)
        .filter(
            HomeworkSubmission.student_id == ctx.user_id,
            HomeworkSubmission.teacher_score.isnot(None),
        )
        .order_by(HomeworkSubmission.teacher_graded_at.desc())
        .limit(10)
        .all()
    )
    trend = [
        {
            "title": title,
            "score": score,
            "subject": subject,
            "subject_name": SUBJECT_NAMES.get(subject, subject),
            "graded_at": graded_at.isoformat() if graded_at else None,
        }
        for title, score, subject, graded_at in trend_rows
    ]

    return {
        "subjects": subjects,
        "overall": overall,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# 学生：AI 学习画像
# ---------------------------------------------------------------------------


def generate_student_portrait(db: Session, ctx: UserContext) -> tuple[dict | None, bool]:
    """返回 (画像 dict, AI 是否可用)。未配置 Key 返回 (None, False)。"""
    overview = get_student_overview(db, ctx)
    mastery = get_student_mastery(db, ctx)

    # 拼接统计摘要（不含题目/作答原文）
    lines = [f"累计提问：{overview['questions']}"]
    lines.append(f"作业提交：{overview['submissions']}")
    lines.append(f"作业正确率：{overview['accuracy'] if overview['accuracy'] is not None else '暂无'}")
    lines.append(f"错题累计：{overview['mistakes']}")
    if mastery["subjects"]:
        lines.append("各学科掌握度：")
        for s in mastery["subjects"]:
            lines.append(f"  {s['subject_name']}：{s['mastery']}分")
    if mastery["overall"] is not None:
        lines.append(f"综合掌握度：{mastery['overall']}分")
    summary = "\n".join(lines)

    raw = generate_answer(
        summary,
        None,
        system_prompt=PORTRAIT_SYSTEM_PROMPT,
        tutor_enabled=False,
    )
    if raw is None:
        return None, False

    try:
        obj, _ = load_model_json(raw)
    except ModelJSONError:
        return None, False

    return {
        "style": obj.get("style", ""),
        "strengths": obj.get("strengths", []),
        "weaknesses": obj.get("weaknesses", []),
        "suggestion": obj.get("suggestion", ""),
    }, True


# ---------------------------------------------------------------------------
# 教师：班级学情汇总
# ---------------------------------------------------------------------------


def _assert_teacher_can_view_class(
    teacher: TeacherContext, class_id: int, subject: str | None
) -> None:
    """校验教师是否有权查看该班级（及学科）学情。"""
    allowed = set(teacher.teaching_classes or [])
    if teacher.homeroom_class_id is not None:
        allowed.add(teacher.homeroom_class_id)
    if class_id not in allowed:
        raise AnalyticsServiceError(403, "无权查看该班级学情")
    if subject is not None and teacher.subject != subject:
        raise AnalyticsServiceError(403, "无权查看该学科学情")


def get_class_analytics(
    db: Session, teacher: TeacherContext, class_id: int, subject: str | None = None
) -> dict:
    """返回班级学情汇总。subject 非空时限定单科，否则全科。"""
    _assert_teacher_can_view_class(teacher, class_id, subject)

    # 班级学生列表
    students = (
        db.query(User)
        .filter(User.class_id == class_id, User.role == "student")
        .all()
    )
    student_ids = [s.id for s in students]
    total_students = len(students)

    # 班级提交（按学科过滤）
    sub_query = db.query(HomeworkSubmission).join(
        Homework, HomeworkSubmission.homework_id == Homework.id
    ).filter(Homework.class_id == class_id)
    if subject:
        sub_query = sub_query.filter(Homework.subject == subject)
    class_subs = sub_query.all()

    # 班级平均分
    scored = [s.teacher_score for s in class_subs if s.teacher_score is not None]
    class_average: int | None = None
    if scored:
        class_average = round(sum(scored) / len(scored))

    # 各学科平均分（仅全科视图）
    subject_averages: dict[str, int] = {}
    if subject is None:
        sub_by_hw: dict[str, list[int]] = {}
        for s in class_subs:
            if s.teacher_score is None:
                continue
            hw = db.get(Homework, s.homework_id)
            if hw:
                sub_by_hw.setdefault(hw.subject, []).append(s.teacher_score)
        for subj, scores in sub_by_hw.items():
            subject_averages[subj] = round(sum(scores) / len(scores))

    # 分数段分布（按提交记录计）
    distribution = {"lt60": 0, "60_79": 0, "80_100": 0}
    for s in scored:
        if s < 60:
            distribution["lt60"] += 1
        elif s < 80:
            distribution["60_79"] += 1
        else:
            distribution["80_100"] += 1

    # 提交率：至少提交过一次的学生数 / 总学生数
    submitted_student_ids = {s.student_id for s in class_subs if s.answer_text}
    submission_rate = (
        round(len(submitted_student_ids) / total_students * 100)
        if total_students
        else 0
    )

    # 错题率：至少有一条错题的学生数 / 总学生数
    mistake_query = db.query(MistakeNote).filter(MistakeNote.class_id == class_id)
    if subject:
        mistake_query = mistake_query.filter(MistakeNote.subject == subject)
    mistake_student_ids = {n.student_id for n in mistake_query.all()}
    mistake_rate = (
        round(len(mistake_student_ids) / total_students * 100)
        if total_students
        else 0
    )

    # 学生掌握度排行
    ranking = []
    for stu in students:
        stu_ctx = UserContext(user_id=stu.id, role="student", class_id=class_id)
        stu_mastery = get_student_mastery(db, stu_ctx)
        overall = stu_mastery["overall"]
        weak = [
            s["subject_name"]
            for s in stu_mastery["subjects"]
            if s["mastery"] < 60
        ]
        ranking.append(
            {
                "name": stu.name or stu.identifier,
                "overall": overall,
                "weak_subjects": weak,
            }
        )
    ranking.sort(key=lambda r: (r["overall"] is not None, r["overall"] or 0), reverse=True)

    return {
        "class_id": class_id,
        "subject": subject,
        "total_students": total_students,
        "class_average": class_average,
        "subject_averages": subject_averages,
        "score_distribution": distribution,
        "submission_rate": submission_rate,
        "mistake_rate": mistake_rate,
        "student_ranking": ranking,
    }
