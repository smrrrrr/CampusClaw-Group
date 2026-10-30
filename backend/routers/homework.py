"""作业批改接口（add-homework-grading）。

教师接口：布置、发布、关闭、列表、提交列表、AI 初批、教师改分。
学生接口：作业列表、提交、查看批改结果。

权限按当前数据库身份校验：教师只能操作任教班级本科目作业；学生只能操作本班作业。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from deps import CurrentUser, get_current_student, get_current_teacher
from homework_service import (
    HomeworkServiceError,
    UserContext,
    ai_grade_homework,
    close_homework,
    create_homework,
    get_student_submission,
    list_homework_submissions,
    list_student_homeworks,
    list_teacher_homeworks,
    publish_homework,
    submit_homework,
    teacher_grade_submission,
)

router = APIRouter(prefix="/api", tags=["homework"])


def _teacher_ctx(current: CurrentUser) -> UserContext:
    return UserContext(
        user_id=current.user_id,
        role=current.role,
        class_id=current.class_id,
        teaching_classes=current.teaching_classes,
        subject=current.subject,
    )


def _student_ctx(current: CurrentUser) -> UserContext:
    return UserContext(
        user_id=current.user_id,
        role=current.role,
        class_id=current.class_id,
    )


def _raise(err: HomeworkServiceError) -> None:
    raise HTTPException(status_code=err.status_code, detail=err.detail)


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------


class CreateHomeworkRequest(BaseModel):
    class_id: int
    title: str = Field(..., min_length=1, max_length=200)
    content: str  # JSON 字符串，如 {"stem": "题目..."}
    due_at: datetime


class SubmitHomeworkRequest(BaseModel):
    answer_text: str = Field(..., min_length=1)


class GradeSubmissionRequest(BaseModel):
    score: int = Field(..., ge=0, le=100)
    feedback: str | None = None


# ---------------------------------------------------------------------------
# 教师接口
# ---------------------------------------------------------------------------


@router.post("/teacher/homeworks")
def api_create_homework(
    req: CreateHomeworkRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        hw = create_homework(
            db, _teacher_ctx(current), req.class_id, req.title, req.content, req.due_at
        )
    except HomeworkServiceError as e:
        _raise(e)
    return {
        "id": hw.id,
        "title": hw.title,
        "status": hw.status,
        "class_id": hw.class_id,
        "subject": hw.subject,
        "due_at": hw.due_at.isoformat(),
    }


@router.put("/teacher/homeworks/{homework_id}/publish")
def api_publish_homework(
    homework_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        hw = publish_homework(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)
    return {"id": hw.id, "status": hw.status}


@router.put("/teacher/homeworks/{homework_id}/close")
def api_close_homework(
    homework_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        hw = close_homework(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)
    return {"id": hw.id, "status": hw.status}


@router.get("/teacher/homeworks")
def api_list_teacher_homeworks(
    class_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        return list_teacher_homeworks(db, _teacher_ctx(current), class_id)
    except HomeworkServiceError as e:
        _raise(e)


@router.get("/teacher/homeworks/{homework_id}/submissions")
def api_list_submissions(
    homework_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        return list_homework_submissions(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)


@router.post("/teacher/homeworks/{homework_id}/ai-grade")
def api_ai_grade(
    homework_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        count = ai_grade_homework(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)
    return {"graded_count": count}


@router.put("/teacher/submissions/{submission_id}/grade")
def api_grade_submission(
    submission_id: int,
    req: GradeSubmissionRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        sub = teacher_grade_submission(
            db, _teacher_ctx(current), submission_id, req.score, req.feedback
        )
    except HomeworkServiceError as e:
        _raise(e)
    return {
        "id": sub.id,
        "teacher_score": sub.teacher_score,
        "teacher_feedback": sub.teacher_feedback,
        "status": sub.status,
    }


# ---------------------------------------------------------------------------
# 学生接口
# ---------------------------------------------------------------------------


@router.get("/student/homeworks")
def api_list_student_homeworks(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        return list_student_homeworks(db, _student_ctx(current))
    except HomeworkServiceError as e:
        _raise(e)


@router.post("/student/homeworks/{homework_id}/submit")
def api_submit_homework(
    homework_id: int,
    req: SubmitHomeworkRequest,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        sub = submit_homework(db, _student_ctx(current), homework_id, req.answer_text)
    except HomeworkServiceError as e:
        _raise(e)
    return {
        "id": sub.id,
        "status": sub.status,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
    }


@router.get("/student/submissions/{submission_id}")
def api_get_submission(
    submission_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        sub = get_student_submission(db, _student_ctx(current), submission_id)
    except HomeworkServiceError as e:
        _raise(e)
    return {
        "id": sub.id,
        "answer_text": sub.answer_text,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "final_score": sub.teacher_score if sub.teacher_score is not None else sub.ai_score,
        "feedback": sub.teacher_feedback if sub.teacher_feedback is not None else sub.ai_feedback,
        "status": sub.status,
    }
