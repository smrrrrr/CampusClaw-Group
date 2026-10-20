"""Pydantic 请求 / 响应模型。"""

from pydantic import BaseModel, Field


# --- 密码登录 ---


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="学号 / 工号")
    password: str


class UserInfo(BaseModel):
    id: int
    role: str
    name: str | None = None
    class_id: int | None = None
    must_change_password: bool
    teaching_classes: list[int] | None = None
    subject: str | None = None
    homeroom_class_id: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    role: str
    user: UserInfo


# --- 改密 ---


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    role: str
    teaching_classes: list[int] | None = None
    subject: str | None = None
    homeroom_class_id: int | None = None
    user: UserInfo


class MessageResponse(BaseModel):
    message: str
