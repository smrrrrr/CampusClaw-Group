"""MCP 服务器管理、连接发现与调用记录（add-mcp-tool-integration）。

权限口径（与现有教师接口一致，见 deps.get_current_teacher）：
- 仅教师可访问；学生 403
- 服务器归属 ``teacher_id + class_id``，且班级必须在 ``teaching_classes`` 内
- 按编号访问不存在、他人或他班的服务器统一返回 404（与不存在一致，不泄露存在性）
- 任何响应都不含令牌原文或密文，只返回布尔 ``has_auth``
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from config import settings
from database import get_db
from deps import CurrentUser, get_current_teacher
from mcp_client import (
    SERVER_NAME_RE,
    McpClient,
    McpClientError,
    looks_like_injection,
)
from mcp_crypto import (
    TokenDecryptError,
    TokenKeyNotConfigured,
    decrypt_token,
    encrypt_token,
    validate_base_url,
)
from models import Class, McpServer, McpTool, McpToolCall, Role, User
from services import require_teacher_classes

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# 响应模型（响应中绝不出现令牌字段）
# ---------------------------------------------------------------------------


class ServerItem(BaseModel):
    id: int
    class_id: int
    name: str
    base_url: str
    connected: bool
    has_auth: bool
    tool_count: int
    last_error: str | None = None
    connected_at: str | None = None


class ServerListResponse(BaseModel):
    items: list[ServerItem]


class ServerCreateRequest(BaseModel):
    class_id: int
    name: str = Field(min_length=1, max_length=32)
    base_url: str = Field(min_length=1, max_length=512)
    auth_token: str = Field(default="", max_length=4096)


class ServerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    base_url: str | None = Field(default=None, min_length=1, max_length=512)
    # 留空表示保留原令牌
    auth_token: str | None = Field(default=None, max_length=4096)


class ToolItem(BaseModel):
    name: str
    description: str
    input_schema: dict


class ToolsResponse(BaseModel):
    connected: bool
    items: list[ToolItem]


class ConnectResponse(BaseModel):
    server: ServerItem
    excluded: list[str] = []


class ToolCallItem(BaseModel):
    id: int
    server_name: str
    tool_ref: str
    status: str
    user_id: int | None = None
    conversation_id: int | None = None
    round: int | None = None
    detail: str | None = None
    created_at: str


class ToolCallListResponse(BaseModel):
    items: list[ToolCallItem]


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------


def _serialize_server(db: Session, server: McpServer) -> ServerItem:
    tool_count = db.query(McpTool).filter(McpTool.server_id == server.id).count()
    return ServerItem(
        id=server.id,
        class_id=server.class_id,
        name=server.name,
        base_url=server.base_url,
        connected=server.connected,
        has_auth=server.auth_token_enc is not None,
        tool_count=tool_count,
        last_error=server.last_error,
        connected_at=server.connected_at.isoformat() if server.connected_at else None,
    )


def _require_subject(current: CurrentUser) -> str:
    if not current.subject:
        raise HTTPException(status_code=403, detail="请先分配任教学科")
    return current.subject


def _require_class(current: CurrentUser, class_id: int) -> list[int]:
    tc = require_teacher_classes(current.teaching_classes)
    if class_id not in tc:
        raise HTTPException(status_code=403, detail="只能操作本人任教班级的 MCP 服务器")
    return tc


def _owned_server(db: Session, server_id: int, current: CurrentUser) -> McpServer:
    """按编号 + 归属查询；查不到统一 404（不泄露存在性）。"""
    server = (
        db.query(McpServer)
        .filter(
            McpServer.id == server_id,
            McpServer.teacher_id == current.user_id,
            McpServer.class_id.in_(current.teaching_classes or []),
        )
        .one_or_none()
    )
    if server is None:
        raise HTTPException(status_code=404, detail="MCP 服务器不存在")
    return server


def _validate_name(db: Session, current: CurrentUser, class_id: int, name: str, exclude_id: int | None = None) -> str:
    clean = (name or "").strip()
    if not SERVER_NAME_RE.match(clean):
        raise HTTPException(
            status_code=400,
            detail="服务器名称须为 1–32 位小写字母、数字或连字符，且以字母或数字开头",
        )
    query = db.query(McpServer).filter(
        McpServer.teacher_id == current.user_id,
        McpServer.class_id == class_id,
        McpServer.name == clean,
    )
    if exclude_id is not None:
        query = query.filter(McpServer.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="该班级下已存在同名服务器")
    return clean


def _clear_tools(db: Session, server_id: int) -> None:
    db.query(McpTool).filter(McpTool.server_id == server_id).delete(synchronize_session=False)


def _token_for(server: McpServer) -> str:
    if not server.auth_token_enc:
        raise HTTPException(status_code=400, detail="该服务器尚未配置令牌，请先填写令牌")
    try:
        return decrypt_token(server.auth_token_enc)
    except TokenDecryptError as exc:
        # 密钥轮换：置未连接，提示重新填写
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TokenKeyNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 服务器 CRUD
# ---------------------------------------------------------------------------


@router.get("/servers", response_model=ServerListResponse,
    summary="列出本人某班 MCP 服务器",
    responses={403: {"description": "非教师或非任教班级"}, 401: {"description": "未认证"}},
)
def list_servers(
    class_id: int = Query(...),
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """列出本人在某任教班级登记的 MCP 服务器。"""
    _require_subject(current)
    _require_class(current, class_id)
    rows = (
        db.query(McpServer)
        .filter(McpServer.teacher_id == current.user_id, McpServer.class_id == class_id)
        .order_by(McpServer.id.asc())
        .all()
    )
    return ServerListResponse(items=[_serialize_server(db, s) for s in rows])


@router.post("/servers", response_model=ServerItem, status_code=status.HTTP_201_CREATED,
    summary="登记 MCP 服务器",
    responses={400: {"description": "名称/地址非法或令牌密钥未配置"}, 403: {"description": "非任教班级"}},
)
def create_server(
    body: ServerCreateRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """登记 MCP 服务器。令牌加密落库，响应不含令牌。"""
    subject = _require_subject(current)
    _require_class(current, body.class_id)
    name = _validate_name(db, current, body.class_id, body.name)
    try:
        base_url = validate_base_url(body.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    auth_token = (body.auth_token or "").strip()
    enc: str | None = None
    if auth_token:
        try:
            enc = encrypt_token(auth_token)
        except TokenKeyNotConfigured as exc:
            raise HTTPException(status_code=400, detail=f"{exc}，请联系管理员配置后再登记") from exc

    server = McpServer(
        class_id=body.class_id,
        subject=subject,
        teacher_id=current.user_id,
        name=name,
        base_url=base_url,
        auth_token_enc=enc,
        connected=False,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return _serialize_server(db, server)


@router.put("/servers/{server_id}", response_model=ServerItem,
    summary="修改 MCP 服务器",
    responses={400: {"description": "名称/地址非法"}, 404: {"description": "不存在或非本人"}},
)
def update_server(
    server_id: int,
    body: ServerUpdateRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """修改名称/地址/令牌。地址或令牌变更即断开并清空工具缓存。"""
    server = _owned_server(db, server_id, current)
    if body.name is not None:
        server.name = _validate_name(db, current, server.class_id, body.name, exclude_id=server.id)
    if body.base_url is not None:
        try:
            new_url = validate_base_url(body.base_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if new_url != server.base_url:
            server.base_url = new_url
            server.connected = False
            server.last_error = None
            server.connected_at = None
            _clear_tools(db, server.id)
    if body.auth_token is not None and body.auth_token.strip():
        try:
            server.auth_token_enc = encrypt_token(body.auth_token.strip())
        except TokenKeyNotConfigured as exc:
            raise HTTPException(status_code=400, detail=f"{exc}，请联系管理员配置后再登记") from exc
        server.connected = False
        server.last_error = None
        server.connected_at = None
        _clear_tools(db, server.id)
    db.commit()
    db.refresh(server)
    return _serialize_server(db, server)


@router.delete("/servers/{server_id}",
    summary="删除 MCP 服务器",
    responses={404: {"description": "不存在或非本人"}},
)
def delete_server(
    server_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """删除服务器与工具缓存；已有调用记录保留 server_name 文本。"""
    server = _owned_server(db, server_id, current)
    _clear_tools(db, server.id)
    db.delete(server)
    db.commit()
    return {"message": "MCP 服务器已删除", "id": server_id}


# ---------------------------------------------------------------------------
# 连接 / 断开 / 工具
# ---------------------------------------------------------------------------


@router.post("/servers/{server_id}/connect", response_model=ConnectResponse,
    summary="连接并发现工具",
    responses={400: {"description": "未配令牌或密钥不可用"}, 404: {"description": "不存在或非本人"}, 502: {"description": "握手/发现失败"}},
)
def connect_server(
    server_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """握手 + 发现工具；事务内整体替换缓存。失败 502 且置未连接。"""
    server = _owned_server(db, server_id, current)
    token = _token_for(server)
    client = McpClient(server.base_url, token, timeout=settings.mcp_call_timeout)
    try:
        tools, excluded = client.connect_and_discover()
    except McpClientError as exc:
        server.connected = False
        server.last_error = str(exc)
        server.connected_at = None
        _clear_tools(db, server.id)
        db.commit()
        raise HTTPException(
            status_code=502, detail=f"无法连接 MCP 服务器，请检查地址与令牌：{exc}"
        ) from exc

    if not tools:
        server.connected = False
        server.last_error = "远端未返回可用工具"
        server.connected_at = None
        _clear_tools(db, server.id)
        db.commit()
        raise HTTPException(status_code=502, detail="已连接但未发现可用工具，请检查服务配置")

    try:
        _clear_tools(db, server.id)
        for tool in tools:
            db.add(
                McpTool(
                    server_id=server.id,
                    name=tool.name,
                    description=tool.description,
                    input_schema=json.dumps(tool.input_schema, ensure_ascii=False),
                )
            )
        server.connected = True
        server.last_error = None
        server.connected_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        _clear_tools(db, server.id)
        server.connected = False
        server.last_error = "写入工具缓存失败"
        db.commit()
        raise HTTPException(status_code=502, detail="保存工具清单失败，请重试")
    db.refresh(server)
    return ConnectResponse(server=_serialize_server(db, server), excluded=excluded)


@router.post("/servers/{server_id}/disconnect", response_model=ServerItem,
    summary="断开 MCP 服务器",
    responses={404: {"description": "不存在或非本人"}},
)
def disconnect_server(
    server_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """断开服务器：清空工具缓存并置未连接。"""
    server = _owned_server(db, server_id, current)
    _clear_tools(db, server.id)
    server.connected = False
    server.connected_at = None
    server.last_error = None
    db.commit()
    db.refresh(server)
    return _serialize_server(db, server)


@router.get("/servers/{server_id}/tools", response_model=ToolsResponse,
    summary="查看已发现的工具",
    responses={404: {"description": "不存在或非本人"}},
)
def list_server_tools(
    server_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """已发现工具（含完整说明与 inputSchema）。"""
    server = _owned_server(db, server_id, current)
    rows = db.query(McpTool).filter(McpTool.server_id == server.id).order_by(McpTool.name.asc()).all()
    items = [
        ToolItem(name=t.name, description=t.description, input_schema=json.loads(t.input_schema or "{}"))
        for t in rows
    ]
    return ToolsResponse(connected=server.connected, items=items)


# ---------------------------------------------------------------------------
# 调用记录
# ---------------------------------------------------------------------------


@router.get("/tool-calls", response_model=ToolCallListResponse,
    summary="查看本人服务器调用记录",
    responses={403: {"description": "非教师或非任教班级"}},
)
def list_tool_calls(
    class_id: int = Query(...),
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """本人服务器在该班的最近 50 条调用记录（时间倒序）。"""
    _require_subject(current)
    _require_class(current, class_id)
    server_ids = [
        row[0]
        for row in db.query(McpServer.id).filter(
            McpServer.teacher_id == current.user_id, McpServer.class_id == class_id
        )
    ]
    if not server_ids:
        return ToolCallListResponse(items=[])
    rows = (
        db.query(McpToolCall)
        .filter(McpToolCall.class_id == class_id, McpToolCall.server_id.in_(server_ids))
        .order_by(McpToolCall.created_at.desc(), McpToolCall.id.desc())
        .limit(50)
        .all()
    )
    return ToolCallListResponse(
        items=[
            ToolCallItem(
                id=r.id,
                server_name=r.server_name,
                tool_ref=r.tool_ref,
                status=r.status,
                user_id=r.user_id,
                conversation_id=r.conversation_id,
                round=r.round,
                detail=r.detail,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ]
    )
