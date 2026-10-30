"""错题本业务层：列表、详情、掌握标记、AI 讲解。

设计见 openspec/changes/add-mistake-notebook/design.md。
规约见 openspec/changes/add-mistake-notebook/specs/mistake-notebook/spec.md。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from llm_service import generate_answer
from models import Homework, MistakeNote

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
    if note.student_id != ctx.user_id:
        raise MistakeServiceError(403, "无权查看他人错题")


def _note_to_dict(note: MistakeNote, homework_title: str | None = None) -> dict:
    return {
        "id": note.id,
        "subject": note.subject,
        "question_stem": note.question_stem,
        "student_answer": note.student_answer,
        "reason": note.reason,
        "homework_id": note.homework_id,
        "homework_title": homework_title,
        "mastered": bool(note.mastered),
        "mastered_at": note.mastered_at.isoformat() if note.mastered_at else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


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

    # 批量取作业标题，避免 N+1
    homework_ids = {n.homework_id for n in notes if n.homework_id is not None}
    title_map: dict[int, str] = {}
    if homework_ids:
        rows = db.query(Homework.id, Homework.title).filter(Homework.id.in_(homework_ids)).all()
        title_map = {hid: title for hid, title in rows}

    return [_note_to_dict(n, title_map.get(n.homework_id)) for n in notes]


# ---------------------------------------------------------------------------
# 学生：错题详情
# ---------------------------------------------------------------------------


def get_mistake_detail(db: Session, ctx: UserContext, mistake_id: int) -> dict:
    note = _get_mistake_or_404(db, mistake_id)
    _assert_student_owns_mistake(ctx, note)

    homework_title = None
    if note.homework_id is not None:
        hw = db.get(Homework, note.homework_id)
        homework_title = hw.title if hw else None

    return _note_to_dict(note, homework_title)


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

    homework_title = None
    if note.homework_id is not None:
        hw = db.get(Homework, note.homework_id)
        homework_title = hw.title if hw else None

    return _note_to_dict(note, homework_title)


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
    if note.student_answer:
        question_parts.append(f"学生作答：{note.student_answer}")
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
