"""持久作业批改：事务发件箱、版本幂等、租约栅栏与有限重试。"""
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
import homework_service as homework
from models import GradeTask, HomeworkSubmission

logger = logging.getLogger(__name__)
TERMINAL = {"succeeded", "skipped", "dead"}


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    if value is None:
        return None
    if value.tzinfo:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat() + "Z"


def begin_write(db: Session):
    """SQLite先取短写锁，避免并发请求从读事务升级造成BUSY。"""
    db.rollback()
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))


def serialize(task):
    return {"id": task.id, "homework_id": task.homework_id, "submission_id": task.submission_id,
            "status": task.status, "attempts": task.attempts, "execution_count": task.execution_count,
            "max_attempts": task.max_attempts, "error": task.error,
            **{key: iso(getattr(task, key)) for key in
               ("created_at", "updated_at", "started_at", "finished_at", "next_attempt_at")}}


def enqueue_homework(db, ctx, homework_id, request_id):
    begin_write(db)
    try:
        hw = homework._get_homework_or_404(db, homework_id)
        homework._assert_teacher_can_access_homework(ctx, hw)
        subs = db.query(HomeworkSubmission).filter_by(homework_id=hw.id).order_by(HomeworkSubmission.id).all()
        # 整批读取幂等索引，重复点击不逐份发SQL；输入快照共用冻结评分依据。
        existing_tasks = {(t.submission_id, t.input_fingerprint): t for t in
                          db.query(GradeTask).filter_by(homework_id=hw.id).all()}
        stem = homework.public_content(hw).get("stem", hw.title)
        grading = json.loads(hw.grading_snapshot_json) if hw.grading_snapshot_json else None
        ids, created, existing, skipped = [], 0, 0, 0
        for sub in subs:
            if sub.status != "pending":
                skipped += 1
                continue
            snapshot = {"answer_text": sub.answer_text, "submitted_at": iso(sub.submitted_at),
                        "source_type": hw.source_type, "stem": stem, "grading": grading}
            encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
            task = existing_tasks.get((sub.id, fingerprint))
            if task:
                existing += 1
            else:
                task = GradeTask(submission_id=sub.id, homework_id=hw.id, class_id=hw.class_id,
                                 subject=hw.subject, teacher_id=ctx.user_id, input_fingerprint=fingerprint,
                                 input_json=encoded, request_id=request_id, max_attempts=settings.grading_max_attempts)
                db.add(task)
                db.flush()
                created += 1
            ids.append(task.id)
        db.commit()
        return {"task_ids": ids, "created_count": created, "existing_count": existing, "skipped_count": skipped}
    except Exception:
        db.rollback()
        raise


def authorized_task(db, ctx, task_id):
    task = db.get(GradeTask, task_id)
    if task is None:
        raise homework.HomeworkServiceError(404, "批改任务不存在")
    hw = homework._get_homework_or_404(db, task.homework_id)
    homework._assert_teacher_can_access_homework(ctx, hw)
    return task


def list_tasks(db, ctx, homework_id):
    hw = homework._get_homework_or_404(db, homework_id)
    homework._assert_teacher_can_access_homework(ctx, hw)
    return [serialize(t) for t in db.query(GradeTask).filter_by(homework_id=homework_id)
            .order_by(GradeTask.id.desc()).limit(200).all()]


def retry_task(db, ctx, task_id):
    begin_write(db)
    try:
        task = authorized_task(db, ctx, task_id)
        if task.status != "dead":
            raise homework.HomeworkServiceError(409, "只有最终失败的任务可以重新排队")
        task.status, task.execution_count, task.error = "pending", 0, None
        task.claim_token = task.lease_until = task.last_published_at = task.dead_published_at = None
        task.started_at, task.finished_at, task.next_attempt_at = None, None, now()
        db.commit()
        return serialize(task)
    except Exception:
        db.rollback()
        raise


def dispatch(queue):
    """发送确认后标记；任何窗口崩溃均允许补投，不能漏投。"""
    moment = now()
    with SessionLocal() as db:
        tasks = db.query(GradeTask).filter(or_(
            (GradeTask.status.in_(["pending", "retrying"]) & (GradeTask.next_attempt_at <= moment)
             & GradeTask.last_published_at.is_(None)),
            ((GradeTask.status == "running") & (GradeTask.lease_until <= moment)
             & or_(GradeTask.last_published_at.is_(None), GradeTask.last_published_at <= GradeTask.lease_until)),
            ((GradeTask.status == "dead") & GradeTask.dead_published_at.is_(None)),
        )).order_by(GradeTask.id).limit(100).all()
        work = [(t.id, t.status == "dead", t.updated_at) for t in tasks]
    for task_id, dead, version in work:
        queue.publish(task_id, dead=dead)
        with SessionLocal() as db:
            # 不将上一周期的确认写入已经重试/重领的新周期。
            db.query(GradeTask).filter_by(id=task_id, updated_at=version).update(
                {"dead_published_at" if dead else "last_published_at": now()}, synchronize_session=False)
            db.commit()
    return len(work)


def recover_pending_deliveries(db):
    """管理员确认代理数据被清空后显式补投；正常停止消费者不调用此入口。"""
    begin_write(db)
    try:
        count = db.query(GradeTask).filter(GradeTask.status.in_(["pending", "retrying"]),
                                         GradeTask.last_published_at.isnot(None)).update(
            {"last_published_at": None}, synchronize_session=False)
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise


def matches(sub, snapshot):
    return (sub is not None and sub.status == "pending" and sub.answer_text == snapshot["answer_text"]
            and iso(sub.submitted_at) == snapshot["submitted_at"])


def finish(db, task_id, claim, snapshot, result=None, failed=False):
    begin_write(db)
    task = db.get(GradeTask, task_id)
    if task is None or task.status != "running" or task.claim_token != claim:
        db.rollback()
        return "lease_lost"
    sub = db.get(HomeworkSubmission, task.submission_id)
    if not matches(sub, snapshot):
        task.status, task.error = "skipped", "提交已更新或教师已终评，本次未写入"
    elif failed:
        task.error = "模型调用失败或评分格式无效，请检查模型配置后重试"
        task.status = "dead" if task.execution_count >= task.max_attempts else "retrying"
        task.next_attempt_at = now() + timedelta(seconds=settings.grading_retry_base_seconds * 2 ** (task.execution_count - 1))
        task.last_published_at = None
    else:
        sub.ai_score, sub.ai_feedback, sub.ai_graded_at = result[0], result[1], now()
        sub.status = "ai_graded"
        task.status, task.error = "succeeded", None
    task.claim_token = task.lease_until = None
    task.finished_at = now() if task.status in TERMINAL else None
    task.updated_at = now()
    state = task.status
    db.commit()
    return state


def process_task(task_id):
    """一次消息处理；返回前已持久提交，调用方之后才可ack。"""
    with SessionLocal() as db:
        begin_write(db)
        task = db.get(GradeTask, task_id)
        if task is None:
            db.rollback()
            return "missing"
        moment = now()
        if task.status in TERMINAL:
            task.attempts += 1
            state = task.status
            db.commit()
            return state
        if ((task.status == "running" and task.lease_until and task.lease_until > moment)
                or (task.status == "retrying" and task.next_attempt_at > moment)):
            db.rollback()
            return "deferred"
        task.attempts += 1
        if task.execution_count >= task.max_attempts:
            task.status, task.error, task.finished_at = "dead", "执行中断次数达到上限，请人工检查后重试", moment
            task.claim_token = task.lease_until = None
            db.commit()
            return "dead"
        snapshot = json.loads(task.input_json)
        claim = uuid.uuid4().hex
        task.claim_token, task.status = claim, "running"
        task.execution_count += 1
        task.started_at, task.lease_until = moment, moment + timedelta(seconds=settings.grading_lease_seconds)
        task.finished_at = None
        db.commit()
        sub = db.get(HomeworkSubmission, task.submission_id)
        valid = matches(sub, snapshot)
        db.rollback()
        if not valid:
            return finish(db, task_id, claim, snapshot)
        try:
            result = homework.score_snapshot(snapshot)
        except Exception:
            state = finish(db, task_id, claim, snapshot, failed=True)
            logger.warning("批改任务执行失败", extra={"task_id": task_id, "status": state})
            return state
        return finish(db, task_id, claim, snapshot, result=result)
