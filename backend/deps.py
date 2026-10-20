"""FastAPI 依赖：JWT 校验、当前用户、强制改密拦截、教研/班主任权限。"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import (
    JWTError,
    TOKEN_TYPE_ACCESS,
    decode_token,
)

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: int
    role: str
    class_id: int | None
    must_change_password: bool
    teaching_classes: list[int] | None = None
    subject: str | None = None
    homeroom_class_id: int | None = None


_credential_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="认证失效，请重新登录",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """解析 Authorization: Bearer <access_token>，校验有效性并返回当前用户上下文。"""
    if credentials is None or not credentials.credentials:
        raise _credential_exception

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise _credential_exception

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise _credential_exception

    user_id = payload.get("user_id")
    if user_id is None:
        raise _credential_exception

    # 用户必须仍存在
    user = db.get(User, user_id)
    if user is None:
        raise _credential_exception

    return CurrentUser(
        user_id=user_id,
        role=payload.get("role"),
        class_id=payload.get("class_id"),
        # 重置密码后立即拦截旧 Access Token，不能等其两小时过期。
        must_change_password=user.must_change_password,
        teaching_classes=payload.get("teaching_classes"),
        subject=user.subject,
        homeroom_class_id=payload.get("homeroom_class_id"),
    )


def get_current_user(current: CurrentUser = Depends(get_authenticated_user)) -> CurrentUser:
    """所有业务依赖统一执行首次改密检查；认证自身接口使用原始认证依赖。"""
    if current.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码",
        )
    return current


def require_password_changed(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """兼容已有业务依赖，改密检查统一在 get_current_user 执行。"""
    return current


def get_current_teacher(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """教师专用接口拦截：仅 role=teacher 可通过。"""
    if current.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅教师可执行该操作",
        )
    return current


def get_current_student(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """学生专用接口拦截：仅 role=student 可通过。"""
    if current.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅学生可执行该操作",
        )
    return current


def require_subject(
    required_subject: str,
    current: CurrentUser = Depends(get_current_teacher),
) -> CurrentUser:
    """教研端点学科隔离：请求目标学科必须等于 JWT 中的教师学科，否则 403。

    班主任身份不得突破学科壁垒（教研资料按学科隔离铁律）。
    """
    if not current.subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未分配学科，无法访问教研功能",
        )
    if current.subject != required_subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他学科的教研资料",
        )
    return current


def require_homeroom(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_teacher),
) -> CurrentUser:
    """班主任特权端点：必须是某班班主任（JWT homeroom_class_id 非空）才可通过。"""
    if current.homeroom_class_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅班主任可执行该操作",
        )
    return current
