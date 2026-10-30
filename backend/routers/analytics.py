"""学情诊断接口（add-learning-diagnostics）。

学生接口：学情概览、学科掌握度、AI 学习画像。
教师接口：班级学情汇总（全科/单科）。

权限按当前数据库身份校验：学生只能查看本人数据；教师只能查看任教班级（含带班）且本人学科。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from analytics_service import (
    AnalyticsServiceError,
    TeacherContext,
    UserContext,
    generate_student_portrait,
    get_class_analytics,
    get_student_mastery,
    get_student_overview,
)
from database import get_db
from deps import CurrentUser, get_current_student, get_current_teacher

router = APIRouter(prefix="/api", tags=["analytics"])


def _student_ctx(current: CurrentUser) -> UserContext:
    return UserContext(
        user_id=current.user_id,
        role=current.role,
        class_id=current.class_id,
    )


def _teacher_ctx(current: CurrentUser) -> TeacherContext:
    return TeacherContext(
        user_id=current.user_id,
        role=current.role,
        teaching_classes=current.teaching_classes,
        subject=current.subject,
        homeroom_class_id=current.homeroom_class_id,
    )


def _raise(err: AnalyticsServiceError) -> None:
    raise HTTPException(status_code=err.status_code, detail=err.detail)


# ---------------------------------------------------------------------------
# 学生接口
# ---------------------------------------------------------------------------


@router.get("/student/analytics/overview")
def api_student_overview(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return get_student_overview(db, _student_ctx(current))


@router.get("/student/analytics/mastery")
def api_student_mastery(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return get_student_mastery(db, _student_ctx(current))


@router.post("/student/analytics/portrait")
def api_student_portrait(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    portrait, available = generate_student_portrait(db, _student_ctx(current))
    return {"portrait": portrait, "available": available}


# ---------------------------------------------------------------------------
# 教师接口
# ---------------------------------------------------------------------------


@router.get("/teacher/analytics/class")
def api_teacher_class_analytics(
    class_id: int = Query(..., description="班级 ID"),
    subject: str | None = Query(None, description="学科（空表示全科）"),
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        return get_class_analytics(db, _teacher_ctx(current), class_id, subject)
    except AnalyticsServiceError as e:
        _raise(e)
