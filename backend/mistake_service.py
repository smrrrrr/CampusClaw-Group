"""错题本业务层：列表、详情、掌握标记、AI 讲解。

设计见 openspec/changes/add-mistake-notebook/design.md。
规约见 openspec/changes/add-mistake-notebook/specs/mistake-notebook/spec.md。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from llm_service import generate_answer
from homework_service import quiz_question_numbers, submission_item_answers
from models import Homework, HomeworkSubmission, MistakeNote

MISTAKE_EXPLAIN_SYSTEM_PROMPT = (
    "你是一名耐心的学科辅导老师。学生给你一道他做错的题目、他的作答和老师的评语。"
    "请你：1）分析他做错的根本原因（概念混淆、计算错误、审题不清等）；"
    "2）给出解题思路和关键步骤提示；3）点出涉及的知识点。"
    "请用中文分点回答，不要直接给出最终答案，要引导学生自己思考。"
)


class MistakeServiceError(Exception):
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_mistake_or_404(db: Session, mistake_id: int) -> MistakeNote:
    note = db.get(MistakeNote, mistake_id)
    if note is None:
        raise MistakeServiceError(404, "错题不存在")
    return note


def _assert_student_owns_mistake(ctx: UserContext, note: MistakeNote) -> None:
    # fetch-then-check：非本人错题 → 404，不泄露存在性
    if note.student_id != ctx.user_id:
        raise MistakeServiceError(404, "错题不存在")


def _note_to_dict(note: MistakeNote, homework_title: str | None, student_answer: str | None) -> dict:
    return {
        "id": note.id,
        "subject": note.subject,
        "question_stem": note.question_stem,
        "student_answer": student_answer,
        "reason": note.reason,
        "homework_id": note.homework_id,
        "homework_title": homework_title,
        "question_number": note.question_number,
        "mastered": bool(note.mastered),
        "mastered_at": note.mastered_at.isoformat() if note.mastered_at else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def _describe_notes(db: Session, ctx: UserContext, notes: list[MistakeNote]) -> list[dict]:
    homework_ids = {note.homework_id for note in notes if note.homework_id is not None}
    rows = (
        db.query(Homework, HomeworkSubmission)
        .outerjoin(HomeworkSubmission, and_(HomeworkSubmission.homework_id == Homework.id,
                                            HomeworkSubmission.class_id == Homework.class_id,
                                            HomeworkSubmission.student_id == ctx.user_id))
        .filter(Homework.id.in_(homework_ids))
        .all()
    ) if homework_ids else []
    homework_by_id = {hw.id: (hw, sub) for hw, sub in rows}
    answers_by_id = {}
    result = []
    for note in notes:
        hw, sub = homework_by_id.get(note.homework_id, (None, None))
        answer = note.student_answer
        if note.question_number is not None:
            answer = None
            if hw is not None and sub is not None and hw.class_id == note.class_id and hw.subject == note.subject:
                if hw.id not in answers_by_id:
                    answers = submission_item_answers(sub, quiz_question_numbers(hw)) or []
                    answers_by_id[hw.id] = {item["number"]: item["answer_text"] for item in answers}
                answer = answers_by_id[hw.id].get(note.question_number)
        result.append(_note_to_dict(note, hw.title if hw is not None else None, answer))
    return result


# ---------------------------------------------------------------------------
# 学生：错题列表
# ---------------------------------------------------------------------------


def list_student_mistakes(
    db: Session,
    ctx: UserContext,
    subject: str | None = None,
    only_unmastered: bool = False,
) -> list[dict]:
    """返回当前学生的错题列表，按收录时间倒序，最多 200 条。"""
    query = db.query(MistakeNote).filter(MistakeNote.student_id == ctx.user_id)
    if subject:
        query = query.filter(MistakeNote.subject == subject)
    if only_unmastered:
        query = query.filter(MistakeNote.mastered.is_(False))

    notes = (
        query.order_by(MistakeNote.created_at.desc())
        .limit(200)
        .all()
    )

    return _describe_notes(db, ctx, notes)


# ---------------------------------------------------------------------------
# 学生：错题详情
# ---------------------------------------------------------------------------


def get_mistake_detail(db: Session, ctx: UserContext, mistake_id: int) -> dict:
    note = _get_mistake_or_404(db, mistake_id)
    _assert_student_owns_mistake(ctx, note)

    return _describe_notes(db, ctx, [note])[0]


# ---------------------------------------------------------------------------
# 学生：标记已掌握 / 取消
# ---------------------------------------------------------------------------


def toggle_mastered(
    db: Session, ctx: UserContext, mistake_id: int, mastered: bool
) -> dict:
    note = _get_mistake_or_404(db, mistake_id)
    _assert_student_owns_mistake(ctx, note)

    note.mastered = mastered
    note.mastered_at = _utcnow() if mastered else None
    db.commit()
    db.refresh(note)

    return _describe_notes(db, ctx, [note])[0]


# ---------------------------------------------------------------------------
# 学生：AI 错题讲解
# ---------------------------------------------------------------------------


def explain_mistake(
    db: Session, ctx: UserContext, mistake_id: int
) -> tuple[str | None, bool]:
    """返回 (讲解文本, AI 是否可用)。未配置 API Key 时 (None, False)。"""
    note = _get_mistake_or_404(db, mistake_id)
    _assert_student_owns_mistake(ctx, note)

    question_parts = [f"题目：{note.question_stem}"]
    answer = _describe_notes(db, ctx, [note])[0]["student_answer"]
    if answer is not None:
        question_parts.append(f"学生作答：{answer or '未作答'}")
    if note.reason:
        question_parts.append(f"教师评语/错因：{note.reason}")
    question = "\n".join(question_parts)

    explanation = generate_answer(
        question,
        None,
        system_prompt=MISTAKE_EXPLAIN_SYSTEM_PROMPT,
        tutor_enabled=True,
    )
    if explanation is None:
        return None, False
    return explanation, True
