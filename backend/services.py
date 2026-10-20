"""业务服务：登录失败锁定、审计日志、AI 提问次数限制。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import AIQuestionLog, AuditLog, LoginAttempt

MAX_LOGIN_FAILURES = 5
LOCK_MINUTES = 15

# 校园场景按中国时区划分自然日
_CN_TZ = timezone(timedelta(hours=8))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_today_cn() -> datetime:
    """中国时区当日 0 点（返回对应 UTC aware 时间）。"""
    now_cn = _utcnow().astimezone(_CN_TZ)
    start_cn = now_cn.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_cn.astimezone(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    """SQLite 读出的时间可能是 naive，统一转为 UTC aware。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# 密码登录失败锁定
# ---------------------------------------------------------------------------


def is_locked(db: Session, identifier: str) -> bool:
    attempt = db.query(LoginAttempt).filter_by(identifier=identifier).one_or_none()
    if attempt is None or attempt.lock_until is None:
        return False
    return _as_aware(attempt.lock_until) > _utcnow()


def register_failure(db: Session, identifier: str) -> None:
    """登录失败：计数 +1，达到 5 次锁定 15 分钟。"""
    attempt = db.query(LoginAttempt).filter_by(identifier=identifier).one_or_none()
    if attempt is None:
        attempt = LoginAttempt(identifier=identifier, attempt_count=0)
        db.add(attempt)
    attempt.attempt_count += 1
    attempt.last_attempt_at = _utcnow()
    if attempt.attempt_count >= MAX_LOGIN_FAILURES:
        attempt.lock_until = _utcnow() + timedelta(minutes=LOCK_MINUTES)
    db.commit()


def reset_failures(db: Session, identifier: str) -> None:
    """登录成功：清零失败计数并解除锁定。"""
    attempt = db.query(LoginAttempt).filter_by(identifier=identifier).one_or_none()
    if attempt is not None:
        attempt.attempt_count = 0
        attempt.lock_until = None
        attempt.last_attempt_at = _utcnow()
        db.commit()


# ---------------------------------------------------------------------------
# 审计日志：异步写入（catch-and-log，不影响主请求）
# ---------------------------------------------------------------------------


def write_audit_log(
    db: Session,
    *,
    user_id: int | None,
    role: str | None,
    request_path: str,
    method: str,
    status_code: int,
    ip_address: str | None = None,
    subject: str | None = None,
    class_id: int | None = None,
) -> None:
    """同步写入审计日志（由 BackgroundTasks 调用，异常仅打印日志）。"""
    try:
        log = AuditLog(
            user_id=user_id,
            role=role,
            subject=subject,
            class_id=class_id,
            request_path=request_path,
            method=method,
            status_code=status_code,
            ip_address=ip_address,
        )
        db.add(log)
        db.commit()
    except Exception:
        # 审计日志写入失败 MUST NOT 影响主请求
        db.rollback()


# ---------------------------------------------------------------------------
# AI 提问次数限制：每日 20 次，按 student_id 计数，跨日重置
# ---------------------------------------------------------------------------

AI_DAILY_LIMIT = 40


def get_ai_daily_count(db: Session, student_id: int) -> int:
    """查询学生当日 AI 提问次数（中国时区自然日）。"""
    return (
        db.query(AIQuestionLog)
        .filter(
            AIQuestionLog.student_id == student_id,
            AIQuestionLog.created_at >= _start_of_today_cn(),
        )
        .count()
    )


def check_ai_limit(db: Session, student_id: int) -> tuple[bool, str]:
    """返回 (是否允许提问, 拒绝原因)。"""
    count = get_ai_daily_count(db, student_id)
    if count >= AI_DAILY_LIMIT:
        return False, f"今日提问次数已达上限（{AI_DAILY_LIMIT}次），请明日再试"
    return True, ""


def record_ai_question(
    db: Session,
    student_id: int,
    class_id: int,
    question: str,
    answer: str | None = None,
) -> AIQuestionLog:
    """记录一次 AI 提问并返回记录对象（含 class_id 用于班级数据隔离）。"""
    log = AIQuestionLog(
        student_id=student_id,
        class_id=class_id,
        question=question,
        answer=answer,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# 班级数据隔离辅助：边界检查与 class_id 一致性校验
# ---------------------------------------------------------------------------


def require_student_class_id(class_id: int | None) -> int:
    """学生未分配班级时拒绝查询（403）。返回有效的 class_id。"""
    if class_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您尚未分配班级，无法查看班级数据",
        )
    return class_id


def require_teacher_classes(teaching_classes: list[int] | None) -> list[int]:
    """教师未分配任教班级时拒绝查询（403）。返回有效的 teaching_classes 列表。"""
    if not teaching_classes:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您尚未分配任教班级，无法查看班级数据",
        )
    return teaching_classes


def check_class_id_consistency(
    request_class_id: int | None,
    jwt_class_id: int | None,
    teaching_classes: list[int] | None,
    role: str,
) -> None:
    """校验请求参数中的 class_id 与 JWT Payload 是否一致，不匹配返回 403。

    - 学生：request_class_id 必须等于 jwt_class_id
    - 教师：request_class_id 必须在 teaching_classes 中
    """
    if request_class_id is None:
        return  # 未传入 class_id 时不校验（由后端从 JWT 提取）

    from fastapi import HTTPException, status

    if role == "student":
        if request_class_id != jwt_class_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问其他班级的数据",
            )
    elif role == "teacher":
        tc = teaching_classes or []
        if request_class_id not in tc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问非任教班级的数据",
            )
