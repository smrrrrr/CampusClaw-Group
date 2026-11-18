"""认证相关路由：密码登录、Token 刷新、改密、登出。"""

import json
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from deps import CurrentUser, get_authenticated_user
from models import Class, User
from schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshResponse,
    TokenResponse,
    UserInfo,
)
from security import (
    JWTError,
    REFRESH_COOKIE_NAME,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from services import is_locked, register_failure, reset_failures

router = APIRouter(prefix="/api/auth", tags=["auth"])

_REFRESH_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60


def _user_info(db: Session, user: User) -> UserInfo:
    classroom = db.get(Class, user.class_id) if user.class_id is not None else None
    return UserInfo(
        id=user.id,
        role=user.role.value,
        name=user.name,
        class_id=user.class_id,
        class_name=classroom.name if classroom else None,
        must_change_password=user.must_change_password,
        teaching_classes=_parse_teaching_classes(user.teaching_classes),
        subject=user.subject,
        homeroom_class_id=user.homeroom_class_id,
    )


def _parse_teaching_classes(raw: str | None) -> list[int] | None:
    """从 User.teaching_classes JSON 字段解析出整数列表。"""
    if not raw:
        return None
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else None
    except (ValueError, TypeError):
        return None


def _role_cookie(role: str) -> str:
    return f"{REFRESH_COOKIE_NAME}_{role}"


def _set_refresh_cookie(response: Response, name: str, token: str) -> None:
    response.set_cookie(
        key=name, value=token, max_age=_REFRESH_COOKIE_MAX_AGE,
        httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite,
        path="/api/auth",
    )


def _issue_tokens(response: Response, user: User) -> tuple[str, str]:
    """签发 Access Token（返回）+ Refresh Token（写入 HttpOnly Cookie）。
    返回 (access_token, csrf_token)。"""
    import secrets

    tc = _parse_teaching_classes(user.teaching_classes)
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        class_id=user.class_id,
        must_change_password=user.must_change_password,
        teaching_classes=tc,
        subject=user.subject,
        homeroom_class_id=user.homeroom_class_id,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        role=user.role.value,
        class_id=user.class_id,
        must_change_password=user.must_change_password,
        teaching_classes=tc,
    )
    _set_refresh_cookie(response, REFRESH_COOKIE_NAME, refresh_token)
    _set_refresh_cookie(response, _role_cookie(user.role.value), refresh_token)
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=_REFRESH_COOKIE_MAX_AGE,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return access_token, csrf_token


# ---------------------------------------------------------------------------
# 密码登录
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    identifier = body.identifier.strip()

    # 锁定期间即使密码正确也拒绝
    if is_locked(db, identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="账号已锁定，请15分钟后重试",
        )

    # identifier 在 (role, identifier) 维度唯一；同号跨角色时逐个验密
    candidates = db.query(User).filter(User.identifier == identifier).all()
    matched: User | None = None
    for user in candidates:
        if verify_password(body.password, user.password_hash):
            matched = user
            break

    if matched is None:
        # 账号不存在与密码错误返回完全相同的提示，防止账号枚举
        register_failure(db, identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    reset_failures(db, identifier)
    access_token, csrf_token = _issue_tokens(response, matched)
    return TokenResponse(
        access_token=access_token,
        must_change_password=matched.must_change_password,
        role=matched.role.value,
        user=_user_info(db, matched),
        csrf_token=csrf_token,
    )


# ---------------------------------------------------------------------------
# 刷新 Access Token
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    session_role: Literal["teacher", "student"] | None = Header(default=None, alias="X-Session-Role"),
):
    selected = request.cookies.get(_role_cookie(session_role)) if session_role else None
    refresh_token_cookie = selected or request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供刷新令牌")

    try:
        payload = decode_token(refresh_token_cookie)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已失效，请重新登录")

    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误")

    # 以数据库当前状态重新签发，确保权限 / 改密标记及时生效
    user = db.get(User, payload.get("user_id"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在")
    if session_role and (payload.get("role") != session_role or user.role.value != session_role):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录此身份，请重新登录")

    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        class_id=user.class_id,
        must_change_password=user.must_change_password,
        teaching_classes=_parse_teaching_classes(user.teaching_classes),
        subject=user.subject,
        homeroom_class_id=user.homeroom_class_id,
    )
    # 滑动续期：同时更新 Refresh Cookie
    new_refresh = create_refresh_token(
        user_id=user.id,
        role=user.role.value,
        class_id=user.class_id,
        must_change_password=user.must_change_password,
        teaching_classes=_parse_teaching_classes(user.teaching_classes),
    )
    _set_refresh_cookie(response, _role_cookie(user.role.value), new_refresh)
    if not selected:
        _set_refresh_cookie(response, REFRESH_COOKIE_NAME, new_refresh)
    return RefreshResponse(
        access_token=access_token,
        must_change_password=user.must_change_password,
        role=user.role.value,
        teaching_classes=_parse_teaching_classes(user.teaching_classes),
        subject=user.subject,
        homeroom_class_id=user.homeroom_class_id,
        user=_user_info(db, user),
    )


# ---------------------------------------------------------------------------
# 修改密码（改密端点不受 require_password_changed 限制）
# ---------------------------------------------------------------------------


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current: CurrentUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, current.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在")

    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    valid, reason = validate_password_policy(body.new_password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)

    access_token, csrf_token = _issue_tokens(response, user)
    return TokenResponse(
        access_token=access_token,
        must_change_password=False,
        role=user.role.value,
        user=_user_info(db, user),
        csrf_token=csrf_token,
    )


# ---------------------------------------------------------------------------
# 登出（清除 HttpOnly Cookie；Access Token 由前端内存清除）
# ---------------------------------------------------------------------------


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    current: CurrentUser = Depends(get_authenticated_user),
):
    cookies_to_clear = [_role_cookie(current.role)]
    legacy = request.cookies.get(REFRESH_COOKIE_NAME)
    if legacy:
        try:
            if decode_token(legacy).get("role") == current.role:
                cookies_to_clear.append(REFRESH_COOKIE_NAME)
        except JWTError:
            cookies_to_clear.append(REFRESH_COOKIE_NAME)
    for name in cookies_to_clear:
        response.delete_cookie(
            key=name, path="/api/auth", httponly=True,
            secure=settings.cookie_secure, samesite=settings.cookie_samesite,
        )
    other_role = "student" if current.role == "teacher" else "teacher"
    if not request.cookies.get(_role_cookie(other_role)):
        response.delete_cookie(
            key="csrf_token", path="/",
            secure=settings.cookie_secure, samesite=settings.cookie_samesite,
        )
    return MessageResponse(message="已登出")
