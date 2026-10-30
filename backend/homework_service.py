"""作业批改业务层：布置、提交、AI 初批、教师改分、错题收录。

设计见 openspec/changes/add-homework-grading/design.md。
规约见 openspec/changes/add-homework-grading/specs/homework/spec.md。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from llm_service import generate_answer
from model_json import ModelJSONError, load_model_json
from models import Homework, HomeworkSubmission, MistakeNote

HOMEWORK_STATUSES = ("draft", "published", "closed")
SUBMISSION_STATUSES = ("pending", "ai_graded", "teacher_graded")


class HomeworkServiceError(Exception):
    """业务层错误，由路由层转换为 HTTPException。"""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass
class UserContext:
    """轻量用户上下文，避免业务层依赖 deps（接口层）。"""

    user_id: int
    role: str
    class_id: int | None = None
    teaching_classes: list[int] | None = None
    subject: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_content(content: str) -> dict:
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        raise HomeworkServiceError(400, "作业题目内容不是合法 JSON")


def _get_homework_or_404(db: Session, homework_id: int) -> Homework:
    hw = db.get(Homework, homework_id)
    if hw is None:
        raise HomeworkServiceError(404, "作业不存在")
    return hw


def _get_submission_or_404(db: Session, submission_id: int) -> HomeworkSubmission:
    sub = db.get(HomeworkSubmission, submission_id)
    if sub is None:
        raise HomeworkServiceError(404, "提交记录不存在")
    return sub


def _assert_teacher_can_access_homework(ctx: UserContext, hw: Homework) -> None:
    teaching = ctx.teaching_classes or []
    if hw.class_id not in teaching:
        raise HomeworkServiceError(403, "无权操作非任教班级的作业")
    if hw.subject != ctx.subject:
        raise HomeworkServiceError(403, "无权操作非本人学科的作业")


# ---------------------------------------------------------------------------
# 教师：布置作业
# ---------------------------------------------------------------------------


def create_homework(
    db: Session,
    ctx: UserContext,
    class_id: int,
    title: str,
    content: str,
    due_at: datetime,
) -> Homework:
    teaching = ctx.teaching_classes or []
    if not teaching:
        raise HomeworkServiceError(403, "您尚未分配任教班级")
    if class_id not in teaching:
        raise HomeworkServiceError(403, "无权为非任教班级布置作业")
    if not ctx.subject:
        raise HomeworkServiceError(403, "当前账号未分配学科")
    _parse_content(content)
    if not title.strip():
        raise HomeworkServiceError(400, "作业标题不能为空")
    hw = Homework(
        class_id=class_id,
        subject=ctx.subject,
        teacher_id=ctx.user_id,
        title=title.strip(),
        content_json=content,
        due_at=due_at,
        status="draft",
    )
    db.add(hw)
    db.commit()
    db.refresh(hw)
    return hw


def publish_homework(db: Session, ctx: UserContext, homework_id: int) -> Homework:
    hw = _get_homework_or_404(db, homework_id)
    _assert_teacher_can_access_homework(ctx, hw)
    if hw.teacher_id != ctx.user_id:
        raise HomeworkServiceError(403, "仅作业作者可发布")
    if hw.status != "draft":
        raise HomeworkServiceError(400, "只有草稿状态的作业可发布")
    hw.status = "published"
    hw.updated_at = _utcnow()
    db.commit()
    db.refresh(hw)
    return hw


def close_homework(db: Session, ctx: UserContext, homework_id: int) -> Homework:
    hw = _get_homework_or_404(db, homework_id)
    _assert_teacher_can_access_homework(ctx, hw)
    if hw.teacher_id != ctx.user_id:
        raise HomeworkServiceError(403, "仅作业作者可关闭")
    if hw.status != "published":
        raise HomeworkServiceError(400, "只有已发布的作业可关闭")
    hw.status = "closed"
    hw.updated_at = _utcnow()
    db.commit()
    db.refresh(hw)
    return hw


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------


def list_teacher_homeworks(db: Session, ctx: UserContext, class_id: int) -> list[dict]:
    teaching = ctx.teaching_classes or []
    if not teaching:
        raise HomeworkServiceError(403, "您尚未分配任教班级")
    if class_id not in teaching:
        raise HomeworkServiceError(403, "无权查看非任教班级的作业")
    if not ctx.subject:
        raise HomeworkServiceError(403, "当前账号未分配学科")
    rows = (
        db.query(Homework)
        .filter(Homework.class_id == class_id, Homework.subject == ctx.subject)
        .order_by(Homework.created_at.desc())
        .all()
    )
    total_students = _count_class_students(db, class_id)
    result = []
    for hw in rows:
        submitted = (
            db.query(HomeworkSubmission)
            .filter(HomeworkSubmission.homework_id == hw.id)
            .count()
        )
        result.append(
            {
                "id": hw.id,
                "title": hw.title,
                "due_at": hw.due_at.isoformat() if hw.due_at else None,
                "status": hw.status,
                "submitted_count": submitted,
                "total_count": total_students,
                "created_at": hw.created_at.isoformat(),
            }
        )
    return result


def list_student_homeworks(db: Session, ctx: UserContext) -> list[dict]:
    if ctx.class_id is None:
        raise HomeworkServiceError(403, "您尚未分配班级")
    rows = (
        db.query(Homework)
        .filter(
            Homework.class_id == ctx.class_id,
            Homework.status == "published",
        )
        .order_by(Homework.due_at.asc())
        .all()
    )
    result = []
    for hw in rows:
        sub = (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id == hw.id,
                HomeworkSubmission.student_id == ctx.user_id,
            )
            .one_or_none()
        )
        content = _parse_content(hw.content_json)
        final_score = None
        feedback = None
        graded = False
        if sub:
            if sub.teacher_score is not None:
                final_score = sub.teacher_score
                feedback = sub.teacher_feedback
                graded = sub.status == "teacher_graded"
            else:
                final_score = sub.ai_score
                feedback = sub.ai_feedback
        result.append(
            {
                "id": hw.id,
                "title": hw.title,
                "subject": hw.subject,
                "content": content,
                "due_at": hw.due_at.isoformat() if hw.due_at else None,
                "status": sub.status if sub else "not_submitted",
                "submission_id": sub.id if sub else None,
                "final_score": final_score,
                "feedback": feedback,
                "graded": graded,
            }
        )
    return result


def _count_class_students(db: Session, class_id: int) -> int:
    from models import User

    return (
        db.query(User)
        .filter(User.class_id == class_id, User.role == "student")
        .count()
    )


# ---------------------------------------------------------------------------
# 学生提交
# ---------------------------------------------------------------------------


def submit_homework(
    db: Session,
    ctx: UserContext,
    homework_id: int,
    answer_text: str,
) -> HomeworkSubmission:
    if ctx.class_id is None:
        raise HomeworkServiceError(403, "您尚未分配班级")
    hw = _get_homework_or_404(db, homework_id)
    if hw.class_id != ctx.class_id:
        raise HomeworkServiceError(403, "无权提交其他班级的作业")
    if hw.status != "published":
        raise HomeworkServiceError(400, "作业未发布或已关闭，无法提交")
    due = hw.due_at
    if due is not None:
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if _utcnow() > due:
            raise HomeworkServiceError(400, "作业已截止")
    if not answer_text.strip():
        raise HomeworkServiceError(400, "答案不能为空")

    sub = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == ctx.user_id,
        )
        .one_or_none()
    )
    now = _utcnow()
    if sub is None:
        sub = HomeworkSubmission(
            class_id=ctx.class_id,
            student_id=ctx.user_id,
            homework_id=homework_id,
            answer_text=answer_text,
            submitted_at=now,
            status="pending",
        )
        db.add(sub)
    else:
        sub.answer_text = answer_text
        sub.submitted_at = now
        sub.status = "pending"
    db.commit()
    db.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# 查看提交
# ---------------------------------------------------------------------------


def get_student_submission(
    db: Session, ctx: UserContext, submission_id: int
) -> HomeworkSubmission:
    sub = _get_submission_or_404(db, submission_id)
    if sub.student_id != ctx.user_id:
        raise HomeworkServiceError(403, "无权查看他人的提交")
    return sub


def list_homework_submissions(
    db: Session, ctx: UserContext, homework_id: int
) -> list[dict]:
    hw = _get_homework_or_404(db, homework_id)
    _assert_teacher_can_access_homework(ctx, hw)
    rows = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == homework_id)
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
    )
    result = []
    for sub in rows:
        result.append(
            {
                "id": sub.id,
                "student_id": sub.student_id,
                "answer_text": sub.answer_text,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "ai_score": sub.ai_score,
                "ai_feedback": sub.ai_feedback,
                "teacher_score": sub.teacher_score,
                "teacher_feedback": sub.teacher_feedback,
                "status": sub.status,
            }
        )
    return result


# ---------------------------------------------------------------------------
# AI 初批
# ---------------------------------------------------------------------------

AI_GRADE_PROMPT = """你是一位高中学科教师。请对学生的作业作答进行评分和评语。

只输出一个 JSON 对象，不要任何解释文字、不要 Markdown 代码块。结构：
{"score": 0-100的整数, "feedback": "评语（50字以内，指出优点和不足）", "is_wrong": true或false}

规则：
1. score 必须是 0 到 100 的整数。
2. is_wrong 为 true 表示作答有明显错误，为 false 表示基本正确。
3. feedback 用中文，简洁指出问题或肯定。
"""


def ai_grade_homework(db: Session, ctx: UserContext, homework_id: int) -> int:
    hw = _get_homework_or_404(db, homework_id)
    _assert_teacher_can_access_homework(ctx, hw)

    pending_subs = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.status == "pending",
        )
        .all()
    )
    if not pending_subs:
        return 0

    content = _parse_content(hw.content_json)
    question_text = content.get("stem", hw.title)
    now = _utcnow()
    graded = 0

    for sub in pending_subs:
        question = f"题目：{question_text}\n\n学生作答：{sub.answer_text}\n\n请评分。"
        try:
            raw = generate_answer(question, None, system_prompt=AI_GRADE_PROMPT)
        except Exception:
            continue
        if raw is None:
            continue
        try:
            obj, _ = load_model_json(raw)
        except ModelJSONError:
            continue
        score = obj.get("score")
        feedback = obj.get("feedback")
        if not isinstance(score, int) or not (0 <= score <= 100):
            continue
        if not isinstance(feedback, str):
            feedback = ""
        sub.ai_score = score
        sub.ai_feedback = feedback
        sub.ai_graded_at = now
        sub.status = "ai_graded"
        graded += 1

    db.commit()
    return graded


# ---------------------------------------------------------------------------
# 教师改分
# ---------------------------------------------------------------------------


def teacher_grade_submission(
    db: Session,
    ctx: UserContext,
    submission_id: int,
    score: int,
    feedback: str | None,
) -> HomeworkSubmission:
    sub = _get_submission_or_404(db, submission_id)
    hw = _get_homework_or_404(db, sub.homework_id)
    _assert_teacher_can_access_homework(ctx, hw)

    if not isinstance(score, int) or not (0 <= score <= 100):
        raise HomeworkServiceError(400, "分数必须是 0-100 的整数")

    now = _utcnow()
    sub.teacher_score = score
    sub.teacher_feedback = feedback or ""
    sub.teacher_graded_at = now
    sub.status = "teacher_graded"

    if score < 60:
        content = _parse_content(hw.content_json)
        stem = content.get("stem", hw.title)
        existing = (
            db.query(MistakeNote)
            .filter(
                MistakeNote.homework_id == hw.id,
                MistakeNote.student_id == sub.student_id,
            )
            .one_or_none()
        )
        if existing:
            existing.question_stem = stem
            existing.student_answer = sub.answer_text
            existing.reason = feedback or ""
        else:
            note = MistakeNote(
                class_id=hw.class_id,
                student_id=sub.student_id,
                subject=hw.subject,
                homework_id=hw.id,
                question_stem=stem,
                student_answer=sub.answer_text,
                reason=feedback or "",
            )
            db.add(note)

    db.commit()
    db.refresh(sub)
    return sub
