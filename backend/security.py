"""安全工具：密码哈希、密码策略、初始密码、JWT 签发与解析。"""

import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from jwt import PyJWTError
from passlib.context import CryptContext

from config import settings

# 保留 security.JWTError 导出，调用方（main/deps/routers）无需改动。
JWTError = PyJWTError

# ---------------------------------------------------------------------------
# 密码哈希（bcrypt 加盐）
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(plain, password_hash)


# ---------------------------------------------------------------------------
# 密码策略：至少 8 位，必须同时包含大写字母、小写字母、数字、特殊字符
# ---------------------------------------------------------------------------

_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~"
_POLICY_PATTERN = re.compile(
    rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[{re.escape(_SPECIAL_CHARS)}]).{{8,}}$"
)


def validate_password_policy(password: str) -> tuple[bool, str]:
    """返回 (是否合规, 不合规原因)。"""
    if len(password) < 8:
        return False, "密码长度至少为 8 位"
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含小写字母"
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含大写字母"
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    if not re.search(rf"[{re.escape(_SPECIAL_CHARS)}]", password):
        return False, "密码必须包含特殊字符"
    if not _POLICY_PATTERN.match(password):
        return False, "密码不符合安全策略"
    return True, ""


# ---------------------------------------------------------------------------
# 初始密码：学校三位小写缩写 + 学号/工号后 6 位，例如 thu123456
# ---------------------------------------------------------------------------


def generate_initial_password(identifier: str) -> str:
    tail = identifier[-6:]
    return f"{settings.school_abbr.lower()}{tail}"


# ---------------------------------------------------------------------------
# JWT：Access Token(2h) / Refresh Token(7d) / Temp Token(5min)
# ---------------------------------------------------------------------------

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

REFRESH_COOKIE_NAME = "refresh_token"


def _create_token(
    data: dict,
    expires_delta: timedelta,
    token_type: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    *,
    user_id: int,
    role: str,
    class_id: int | None,
    must_change_password: bool,
    teaching_classes: list[int] | None = None,
    subject: str | None = None,
    homeroom_class_id: int | None = None,
) -> str:
    """正式 Access Token：user_id / role / class_id / must_change_password / teaching_classes / subject / homeroom_class_id，2h。"""
    payload: dict = {
        "user_id": user_id,
        "role": role,
        "class_id": class_id,
        "must_change_password": must_change_password,
    }
    if teaching_classes is not None:
        payload["teaching_classes"] = teaching_classes
    if subject is not None:
        payload["subject"] = subject
    if homeroom_class_id is not None:
        payload["homeroom_class_id"] = homeroom_class_id
    return _create_token(
        payload,
        timedelta(minutes=settings.access_token_expire_minutes),
        TOKEN_TYPE_ACCESS,
    )


def create_refresh_token(
    *,
    user_id: int,
    role: str,
    class_id: int | None,
    must_change_password: bool,
    teaching_classes: list[int] | None = None,
) -> str:
    """Refresh Token：7d，HttpOnly Cookie 存放。"""
    payload: dict = {
        "user_id": user_id,
        "role": role,
        "class_id": class_id,
        "must_change_password": must_change_password,
    }
    if teaching_classes is not None:
        payload["teaching_classes"] = teaching_classes
    return _create_token(
        payload,
        timedelta(days=settings.refresh_token_expire_days),
        TOKEN_TYPE_REFRESH,
    )


# 旧 python-jose 的时间判据是整数秒：exp 用 `当前秒 > exp` 判过期（exp==当前秒仍有效），
# iat 只要求可转整数（不拒绝未来时间），nbf 用 `nbf > 当前秒`。PyJWT 默认在相等秒即判过期，
# 且拒绝未来 iat。这里关闭 PyJWT 的时间校验，由 _validate_legacy_time_claims 完整复刻旧语义，
# 避免替换库改变既有 token 的边界行为；签名与算法白名单仍由 PyJWT 执行。
_LEGACY_DECODE_OPTIONS = {
    "verify_exp": False,
    "verify_iat": False,
    "verify_nbf": False,
    "verify_aud": False,
    "require": [],
}


def _as_int_claim(claims: dict, name: str) -> int | None:
    if name not in claims:
        return None
    try:
        return int(claims[name])
    except (TypeError, ValueError):
        raise JWTError(f"{name} must be an integer")


def _validate_legacy_time_claims(claims: dict) -> None:
    now = int(time.time())
    exp = _as_int_claim(claims, "exp")
    if exp is not None and now > exp:
        raise JWTError("Signature has expired")
    nbf = _as_int_claim(claims, "nbf")
    if nbf is not None and nbf > now:
        raise JWTError("The token is not yet valid (nbf)")
    # iat 只做可转整数校验，允许未来时间，与旧库一致。
    _as_int_claim(claims, "iat")


def decode_token(token: str) -> dict:
    """解析并校验 JWT，失败抛出 JWTError。

    保持旧库时间边界：exp==当前整数秒仍有效；未来 iat 不拒绝；nbf 按整数秒比较。
    """
    claims = pyjwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options=_LEGACY_DECODE_OPTIONS,
    )
    _validate_legacy_time_claims(claims)
    return claims


__all__ = [
    "JWTError",
    "REFRESH_COOKIE_NAME",
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_REFRESH",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_initial_password",
    "hash_password",
    "validate_password_policy",
    "verify_password",
]
