"""教师技能文件接口（add-mcp-tool-integration）。

- 技能按班级、学科、教师隔离，同一范围内名称唯一
- 以技能文件原文提交（见 skill_service.parse_skill_file）
- 保存期校验 MCP 引用：服务器属于同教师同班、已连接、工具在最近一次发现清单内
- 学生访问 403；他人或他班技能按编号访问返回与不存在一致的 404
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from database import get_db
from deps import CurrentUser, get_current_teacher
from models import AssistantSkill, McpServer, McpTool
from services import require_teacher_classes
from skill_service import ParsedSkill, SkillParseError, parse_skill_file

router = APIRouter(
    prefix="/api/teacher/skills",
    tags=["skills"],
    responses={401: {"description": "未登录或令牌无效"}, 403: {"description": "非教师或非任教班级"}},
)


class SkillRequest(BaseModel):
    class_id: int
    source: str = Field(min_length=1, max_length=8000)


class SkillUpdateRequest(BaseModel):
    source: str = Field(min_length=1, max_length=8000)


class SkillItem(BaseModel):
    id: int
    class_id: int
    subject: str
    name: str
    trigger: str
    tools: list[str]
    enabled: bool
    description: str
    source: str
    updated_at: str


def _serialize(skill: AssistantSkill) -> SkillItem:
    return SkillItem(
        id=skill.id,
        class_id=skill.class_id,
        subject=skill.subject,
        name=skill.name,
        trigger=skill.trigger,
        tools=json.loads(skill.tools or "[]"),
        enabled=skill.enabled,
        description=skill.description,
        source=skill.source,
        updated_at=skill.updated_at.isoformat() if skill.updated_at else "",
    )


def _require_subject(current: CurrentUser) -> str:
    if not current.subject or current.subject not in SUBJECT_NAMES:
        raise HTTPException(status_code=403, detail="请先分配任教学科")
    return current.subject


def _require_class(current: CurrentUser, class_id: int) -> None:
    tc = require_teacher_classes(current.teaching_classes)
    if class_id not in tc:
        raise HTTPException(status_code=403, detail="只能操作本人任教班级的技能")


def _owned_skill(db: Session, skill_id: int, current: CurrentUser) -> AssistantSkill:
    skill = (
        db.query(AssistantSkill)
        .filter(
            AssistantSkill.id == skill_id,
            AssistantSkill.teacher_id == current.user_id,
            AssistantSkill.class_id.in_(current.teaching_classes or []),
        )
        .one_or_none()
    )
    if skill is None:
        raise HTTPException(status_code=404, detail="技能不存在")
    return skill


def _validate_tool_refs(db: Session, current: CurrentUser, class_id: int, parsed: ParsedSkill) -> None:
    """保存期校验：服务器归属 + 已连接 + 工具在发现清单内。"""
    for tool_name, server_name in parsed.tool_refs:
        server = (
            db.query(McpServer)
            .filter(
                McpServer.teacher_id == current.user_id,
                McpServer.class_id == class_id,
                McpServer.name == server_name,
            )
            .one_or_none()
        )
        ref = f"{tool_name}@{server_name}"
        if server is None:
            raise HTTPException(status_code=400, detail=f"引用「{ref}」的服务器不存在或不属于本人本班")
        if not server.connected:
            raise HTTPException(status_code=400, detail=f"引用「{ref}」的服务器尚未连接")
        tool = (
            db.query(McpTool)
            .filter(McpTool.server_id == server.id, McpTool.name == tool_name)
            .one_or_none()
        )
        if tool is None:
            raise HTTPException(status_code=400, detail=f"引用「{ref}」的工具不在服务器最近一次发现清单中")


def _check_name_unique(db: Session, current: CurrentUser, class_id: int, subject: str, name: str, exclude_id: int | None = None) -> None:
    query = db.query(AssistantSkill).filter(
        AssistantSkill.teacher_id == current.user_id,
        AssistantSkill.class_id == class_id,
        AssistantSkill.subject == subject,
        AssistantSkill.name == name,
    )
    if exclude_id is not None:
        query = query.filter(AssistantSkill.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="本班本科目下已存在同名技能")


def _parse_or_400(source: str, subject: str) -> ParsedSkill:
    try:
        parsed = parse_skill_file(source)
    except SkillParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # 资料字段若填写，必须等于当前学科
    if parsed.subject is not None and parsed.subject != SUBJECT_NAMES[subject]:
        raise HTTPException(status_code=400, detail="资料字段必须等于本科目名称")
    return parsed


@router.get("", response_model=dict,
    summary="列出本人某班技能",
)
def list_skills(
    class_id: int = Query(...),
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    subject = _require_subject(current)
    _require_class(current, class_id)
    rows = (
        db.query(AssistantSkill)
        .filter(
            AssistantSkill.teacher_id == current.user_id,
            AssistantSkill.class_id == class_id,
            AssistantSkill.subject == subject,
        )
        .order_by(AssistantSkill.id.asc())
        .all()
    )
    return {"items": [_serialize(s) for s in rows]}


@router.post("", response_model=SkillItem, status_code=status.HTTP_201_CREATED,
    summary="新建技能文件",
    responses={400: {"description": "技能文件或工具引用校验失败"}},
)
def create_skill(
    body: SkillRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    subject = _require_subject(current)
    _require_class(current, body.class_id)
    parsed = _parse_or_400(body.source, subject)
    _check_name_unique(db, current, body.class_id, subject, parsed.name)
    _validate_tool_refs(db, current, body.class_id, parsed)
    skill = AssistantSkill(
        class_id=body.class_id,
        subject=subject,
        teacher_id=current.user_id,
        name=parsed.name,
        trigger=parsed.trigger,
        tools=json.dumps(parsed.tools, ensure_ascii=False),
        enabled=parsed.enabled,
        description=parsed.description,
        source=parsed.raw,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _serialize(skill)


@router.put("/{skill_id}", response_model=SkillItem,
    summary="改写技能文件",
    responses={400: {"description": "技能文件校验失败"}, 404: {"description": "不存在或非本人"}},
)
def update_skill(
    skill_id: int,
    body: SkillUpdateRequest,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    skill = _owned_skill(db, skill_id, current)
    parsed = _parse_or_400(body.source, skill.subject)
    _check_name_unique(db, current, skill.class_id, skill.subject, parsed.name, exclude_id=skill.id)
    _validate_tool_refs(db, current, skill.class_id, parsed)
    skill.name = parsed.name
    skill.trigger = parsed.trigger
    skill.tools = json.dumps(parsed.tools, ensure_ascii=False)
    skill.enabled = parsed.enabled
    skill.description = parsed.description
    skill.source = parsed.raw
    db.commit()
    db.refresh(skill)
    return _serialize(skill)


@router.delete("/{skill_id}",
    summary="删除技能",
    responses={404: {"description": "不存在或非本人"}},
)
def delete_skill(
    skill_id: int,
    current: CurrentUser = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    skill = _owned_skill(db, skill_id, current)
    db.delete(skill)
    db.commit()
    return {"message": "技能已删除", "id": skill_id}
