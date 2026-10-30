"""错题本接口（add-mistake-notebook）。

学生接口：错题列表、详情、掌握标记、AI 讲解。
权限按当前数据库身份校验：学生只能查看和操作本人错题。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from deps import CurrentUser, get_current_student
from mistake_service import (
    MistakeServiceError,
    UserContext,
    explain_mistake,
    get_mistake_detail,
    list_student_mistakes,
    toggle_mastered,
)

router = APIRouter(prefix="/api/student/mistakes", tags=["mistake"])


def _student_ctx(current: CurrentUser) -> UserContext:
    return UserContext(
        user_id=current.user_id,
        role=current.role,
        class_id=current.class_id,
    )


def _raise(err: MistakeServiceError) -> None:
    raise HTTPException(status_code=err.status_code, detail=err.detail)


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------


class MasteredRequest(BaseModel):
    mastered: bool


# ---------------------------------------------------------------------------
# 学生接口
# ---------------------------------------------------------------------------


@router.get("")
def api_list_mistakes(
    subject: str | None = Query(None, description="按学科过滤"),
    only_unmastered: bool = Query(False, description="仅查看未掌握错题"),
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        return list_student_mistakes(db, _student_ctx(current), subject, only_unmastered)
    except MistakeServiceError as e:
        _raise(e)


@router.get("/{mistake_id}")
def api_get_mistake(
    mistake_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        return get_mistake_detail(db, _student_ctx(current), mistake_id)
    except MistakeServiceError as e:
        _raise(e)


@router.put("/{mistake_id}/mastered")
def api_toggle_mastered(
    mistake_id: int,
    req: MasteredRequest,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        return toggle_mastered(db, _student_ctx(current), mistake_id, req.mastered)
    except MistakeServiceError as e:
        _raise(e)


@router.post("/{mistake_id}/explain")
def api_explain_mistake(
    mistake_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        explanation, available = explain_mistake(db, _student_ctx(current), mistake_id)
    except MistakeServiceError as e:
        _raise(e)
    return {"explanation": explanation, "available": available}
