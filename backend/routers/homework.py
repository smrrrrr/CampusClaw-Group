"""作业批改接口（add-homework-grading）。

教师接口：布置、发布、关闭、列表、提交列表、AI 初批、教师改分。
学生接口：作业列表、提交、查看批改结果。

权限按当前数据库身份校验：教师只能操作任教班级本科目作业；学生只能操作本班作业。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from deps import CurrentUser, get_current_student, get_current_teacher
from homework_service import (
    HomeworkServiceError,
    UserContext,
    close_homework,
    create_homework,
    get_student_submission,
    get_teacher_homework,
    get_homework_asset,
    list_homework_submissions,
    list_student_homeworks,
    list_teacher_homeworks,
    publish_homework,
    submit_homework,
    teacher_grade_submission,
)
from grading_service import enqueue_homework, list_tasks, authorized_task, retry_task, serialize
from logging_setup import request_id_var

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
    score: int = Field(..., ge=0, le=100, strict=True)
    feedback: str | None = None


class HomeworkContent(BaseModel):
    stem: str = ""
    format: str = "text"
    original_total: float | None = None


class TeacherHomeworkDetail(BaseModel):
    id: int
    class_id: int
    subject: str
    title: str
    source_type: str
    status: str
    due_at: str | None
    content: HomeworkContent
    grading: dict | None


class StudentHomeworkItem(BaseModel):
    id: int
    title: str
    subject: str
    source_type: str
    content: HomeworkContent
    due_at: str | None
    status: str
    homework_status: str
    answer_text: str | None
    submitted_at: str | None
    submission_id: int | None
    final_score: int | None
    feedback: str | None
    graded: bool


class AiGradeResult(BaseModel):
    task_ids: list[int]
    created_count: int
    existing_count: int
    skipped_count: int


class GradeTaskResult(BaseModel):
    id: int
    homework_id: int
    submission_id: int
    status: str
    attempts: int
    execution_count: int
    max_attempts: int
    error: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    next_attempt_at: str


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


@router.get("/teacher/homeworks/{homework_id}", response_model=TeacherHomeworkDetail,
            summary="查看有权作业题面和教师评分依据",
            responses={401: {"description": "未登录"}, 403: {"description": "班级或学科不符"},
                       404: {"description": "作业不存在"}})
def api_teacher_homework(homework_id: int, current: CurrentUser = Depends(get_current_teacher),
                         db: Session = Depends(get_db)):
    try:
        return get_teacher_homework(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)


@router.get("/teacher/homeworks/{homework_id}/assets", summary="读取有权作业的原图副本",
            response_class=Response,
            responses={400: {"description": "名称非法"}, 401: {"description": "未登录"},
                       403: {"description": "班级或学科不符"}, 404: {"description": "配图不存在"},
                       409: {"description": "配图缺失或指纹变化"}})
def api_teacher_homework_asset(homework_id: int, name: str = Query(min_length=1, max_length=500),
                              current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    try:
        content, mime = get_homework_asset(db, _teacher_ctx(current), homework_id, name)
        return Response(content=content, media_type=mime, headers={"X-Content-Type-Options": "nosniff"})
    except HomeworkServiceError as e:
        _raise(e)


@router.post("/teacher/homeworks/{homework_id}/ai-grade", response_model=AiGradeResult,
             status_code=202, summary="提交后台初批任务，教师终评不覆盖",
             responses={401: {"description": "未登录"}, 403: {"description": "无权初批"},
                        404: {"description": "作业不存在"}})
def api_ai_grade(
    homework_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    try:
        return enqueue_homework(db, _teacher_ctx(current), homework_id, request_id_var.get() or "grading-request")
    except HomeworkServiceError as e:
        _raise(e)
    except SQLAlchemyError:
        raise HTTPException(503, detail="批改任务暂时无法保存，请稍后重试") from None


@router.get("/teacher/homeworks/{homework_id}/grade-tasks", response_model=list[GradeTaskResult],
            summary="只读查询作业初批任务，最新200条",
            responses={401: {"description": "未登录"}, 403: {"description": "无权查询"}, 404: {"description": "作业不存在"}})
def api_grade_tasks(homework_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    try:
        return list_tasks(db, _teacher_ctx(current), homework_id)
    except HomeworkServiceError as e:
        _raise(e)
    except SQLAlchemyError:
        raise HTTPException(503, detail="批改任务暂时无法查询，请稍后重试") from None


@router.get("/teacher/grade-tasks/{task_id}", response_model=GradeTaskResult, summary="只读查询初批任务详情",
            responses={401: {"description": "未登录"}, 403: {"description": "无权查询"}, 404: {"description": "任务不存在"}})
def api_grade_task(task_id: int = Path(gt=0), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    try:
        return serialize(authorized_task(db, _teacher_ctx(current), task_id))
    except HomeworkServiceError as e:
        _raise(e)
    except SQLAlchemyError:
        raise HTTPException(503, detail="批改任务暂时无法查询，请稍后重试") from None


@router.post("/teacher/grade-tasks/{task_id}/retry", response_model=GradeTaskResult, status_code=202,
             summary="最终失败任务由教师重新排队",
             responses={401: {"description": "未登录"}, 403: {"description": "无权重试"},
                        404: {"description": "任务不存在"}, 409: {"description": "不是最终失败状态"}})
def api_retry_grade_task(task_id: int = Path(gt=0), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    try:
        return retry_task(db, _teacher_ctx(current), task_id)
    except HomeworkServiceError as e:
        _raise(e)
    except SQLAlchemyError:
        raise HTTPException(503, detail="批改任务暂时无法重新排队，请稍后重试") from None


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
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, detail="评分暂时无法保存，请稍后重试") from None
    return {
        "id": sub.id,
        "teacher_score": sub.teacher_score,
        "teacher_feedback": sub.teacher_feedback,
        "status": sub.status,
    }


# ---------------------------------------------------------------------------
# 学生接口
# ---------------------------------------------------------------------------


@router.get("/student/homeworks", response_model=list[StudentHomeworkItem], summary="本人班级作业与本人已提交历史")
def api_list_student_homeworks(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        return list_student_homeworks(db, _student_ctx(current))
    except HomeworkServiceError as e:
        _raise(e)
    except SQLAlchemyError:
        raise HTTPException(503, detail="作业历史暂时无法查询，请稍后重试") from None


@router.get("/student/homeworks/{homework_id}/assets", summary="读取本班已发布作业或本人已提交历史配图",
            response_class=Response,
            responses={400: {"description": "名称非法"}, 401: {"description": "未登录"},
                       403: {"description": "非本班或未发布"}, 404: {"description": "配图不存在"},
                       409: {"description": "配图缺失或指纹变化"}})
def api_student_homework_asset(homework_id: int, name: str = Query(min_length=1, max_length=500),
                              current: CurrentUser = Depends(get_current_student), db: Session = Depends(get_db)):
    try:
        content, mime = get_homework_asset(db, _student_ctx(current), homework_id, name)
        return Response(content=content, media_type=mime, headers={"X-Content-Type-Options": "nosniff"})
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
