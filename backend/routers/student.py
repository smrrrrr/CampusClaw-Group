"""学生相关路由：AI 提问（含每日次数限制 + 班级数据隔离）、多轮会话。"""

import json
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, get_db
from deps import CurrentUser, get_current_student
from llm_service import (
    LLMGenerationError,
    build_chat_messages,
    generate_answer,
    resolve_system_prompt,
    stream_chat,
)
from models import AgentConfig, AIQuestionLog, Conversation, Message, Material, MaterialChunk
from material_service import resolve_abs_path
from citation_service import file_sha256, validate_references
from agent_service import Subject, SUBJECT_NAMES, resolve_assistant, followup_retrieval_query
from rag_search_service import retrieve_top_k
from services import (
    AI_DAILY_LIMIT,
    check_ai_limit,
    get_ai_daily_count,
    record_ai_question,
    require_student_class_id,
    write_audit_log,
)

router = APIRouter(prefix="/api/student", tags=["student"])


class AIQuestionRequest(BaseModel):
    question: str
    subject: Subject = "math"


class Citation(BaseModel):
    material_id: int
    filename: str
    chunk_index: int
    excerpt: str
    score: float
    reference_id: int | None = None
    file_sha256: str | None = None


class AIQuestionResponse(BaseModel):
    id: int
    answer: str
    remaining: int
    citations: list[Citation] = []


class AIHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    created_at: str


@router.get("/assistant-config")
def student_assistant_config(
    subject: Subject = Query("math"),
    conversation_id: int | None = Query(None),
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    class_id = require_student_class_id(current.class_id)
    teacher_id = None
    if conversation_id is not None:
        convo = _coerce_conversation(db, conversation_id, current)
        if convo.subject != subject:
            raise HTTPException(status_code=404, detail="当前学科无此会话")
        teacher_id = convo.teacher_id
    cfg, teacher = resolve_assistant(db, class_id, subject, teacher_id)
    return {"class_id": class_id, "subject": subject,
            "teacher_id": teacher.id if teacher else None,
            "teacher_name": teacher.name if teacher else None,
            "configured": cfg is not None,
            "tutor_enabled": bool(cfg and cfg.tutor_enabled)}


@router.get("/ai-history", response_model=list[AIHistoryItem])
def ai_history(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """返回当前学生最近的历史提问（含问题与回答），按时间倒序。"""
    logs = (
        db.query(AIQuestionLog)
        .filter(AIQuestionLog.student_id == current.user_id)
        .order_by(AIQuestionLog.id.desc())
        .limit(20)
        .all()
    )
    return [
        AIHistoryItem(
            id=log.id,
            question=log.question,
            answer=log.answer or "",
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


@router.delete("/ai-history/{log_id}")
def delete_ai_history(
    log_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """删除当前学生的一条提问历史（仅允许删除自己的记录）。"""
    log = (
        db.query(AIQuestionLog)
        .filter(
            AIQuestionLog.id == log_id,
            AIQuestionLog.student_id == current.user_id,
        )
        .first()
    )
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    db.delete(log)
    db.commit()
    return {"ok": True}


@router.post("/ai-question", response_model=AIQuestionResponse)
def ask_ai(
    body: AIQuestionRequest,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """学生发起 AI 提问。每日上限 20 次，按 student_id 计数，跨日重置。

    班级数据隔离：未分配班级的学生（class_id=NULL）被拒绝（403），
    提问记录关联到学生所在班级 class_id。
    """
    # 无班级边界处理：class_id 为 NULL 时拒绝查询
    class_id = require_student_class_id(current.class_id)

    allowed, reason = check_ai_limit(db, current.user_id)
    if not allowed:
        # 越权/超限记录审计日志
        background.add_task(
            _async_audit,
            user_id=current.user_id,
            role=current.role,
            path=request.url.path,
            method=request.method,
            status_code=429,
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )

    context_block, citations = _retrieve_context(db, class_id, body.question, body.subject)
    if not citations:
        answer = f"暂无相关班级资料，暂无法回答「{body.question}」。"
    else:
        degraded = "AI 未返回有效回答，已展示可核对的资料原文：\n" + context_block
        # DeepSeek 生成解答；未配置 Key / 调用失败时降级为展示检索段落
        try:
            cfg, _ = resolve_assistant(db, class_id, body.subject)
            generated = generate_answer(body.question, context_block,
                system_prompt=resolve_system_prompt(cfg), tutor_enabled=bool(cfg and cfg.tutor_enabled))
        except LLMGenerationError:
            generated = None
            degraded = "AI 生成失败（服务暂不可用），已为你展示检索到的相关段落：\n" + context_block
        if generated:
            answer, citations = validate_references(generated, citations)
        elif settings.deepseek_api_key:
            answer = degraded
        else:
            answer = (
                "AI 生成服务未配置 API Key，暂仅展示检索到的相关段落：\n" + context_block
            )
    log = record_ai_question(
        db,
        student_id=current.user_id,
        class_id=class_id,
        question=body.question,
        answer=answer,
    )
    remaining = AI_DAILY_LIMIT - get_ai_daily_count(db, current.user_id)
    return AIQuestionResponse(
        id=log.id, answer=log.answer or "", remaining=remaining, citations=citations
    )


def _async_audit(
    *,
    user_id: int | None,
    role: str | None,
    path: str,
    method: str,
    status_code: int,
    ip: str | None,
) -> None:
    """BackgroundTasks 调用的异步审计写入。"""
    db = SessionLocal()
    try:
        write_audit_log(
            db,
            user_id=user_id,
            role=role,
            request_path=path,
            method=method,
            status_code=status_code,
            ip_address=ip,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 多轮会话（连续追问）+ SSE 流式生成
# ---------------------------------------------------------------------------

# 多轮历史作为上下文带入的最大消息条数（保留最近几轮，避免超长）
CHAT_HISTORY_TURNS = 6


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


class CreateConversationRequest(BaseModel):
    title: str = "新对话"
    subject: Subject = "math"


class ConversationItem(BaseModel):
    id: int
    title: str
    updated_at: str
    subject: str


class MessageItem(BaseModel):
    id: int
    role: str
    content: str
    sources: list[Citation] = []
    created_at: str


class ChatRequest(BaseModel):
    question: str


def _coerce_conversation(db: Session, conversation_id: int, current: CurrentUser) -> Conversation:
    """校验会话归属当前学生、且班级与 JWT 一致（隔离），返回该会话。"""
    convo = db.get(Conversation, conversation_id)
    if convo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if convo.student_id != current.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    class_id = require_student_class_id(current.class_id)
    if convo.class_id != class_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他班级的会话",
        )
    return convo


def _retrieve_context(db, class_id: int, question: str, subject: str) -> tuple[str | None, list[Citation]]:
    """检索本班已索引材料分块，返回 (context_block, citations)。"""
    hits = retrieve_top_k(db, [class_id], question, subject=subject)
    if not hits:
        return None, []
    lines = []
    citations = []
    hashes = {}
    for hit in hits:
        material = db.get(Material, hit["material_id"])
        if material is None or material.class_id != class_id or not material.is_indexed:
            continue
        chunk = db.query(MaterialChunk).filter_by(material_id=material.id, class_id=class_id, chunk_index=hit["chunk_index"]).first()
        if chunk is None or not chunk.content.strip():
            continue
        if material.id not in hashes:
            path = resolve_abs_path(material.file_path)
            try:
                hashes[material.id] = file_sha256(path)
            except OSError:
                continue
        if material.source_sha256 is None or hashes[material.id] != material.source_sha256:
            continue  # 不给旧索引/已替换文件挂引用。
        # 原文来自数据库真实分块，不用模型生成或改写“摘录”。
        excerpt = chunk.content
        i = len(citations) + 1
        lines.append(f"[{i}]《{hit['filename']}》(块{hit['chunk_index']}): {excerpt}")
        citations.append(
            Citation(
                material_id=hit["material_id"],
                filename=material.filename,
                chunk_index=hit["chunk_index"],
                excerpt=excerpt,
                score=hit["score"],
                reference_id=i,
                file_sha256=hashes[material.id],
            )
        )
    return ("\n".join(lines) if lines else None), citations


def _persist_assistant_message(
    conversation_id: int, content: str, sources: list[Citation], log_id: int
) -> None:
    """流式完成后用独立会话写回 assistant 消息与 AI 提问日志答案。"""
    db = SessionLocal()
    try:
        msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            sources=json.dumps([c.model_dump() for c in sources], ensure_ascii=False),
        )
        db.add(msg)
        log = db.get(AIQuestionLog, log_id)
        if log is not None:
            log.answer = content
        convo = db.get(Conversation, conversation_id)
        if convo is not None:
            convo.updated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@router.post("/conversations", response_model=ConversationItem)
def create_conversation(
    body: CreateConversationRequest,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """新建一个多轮会话（绑定当前学生与班级）。"""
    class_id = require_student_class_id(current.class_id)
    _, teacher = resolve_assistant(db, class_id, body.subject)
    convo = Conversation(
        student_id=current.user_id,
        class_id=class_id,
        title=(body.title or "新对话").strip()[:128] or "新对话",
        subject=body.subject,
        teacher_id=teacher.id if teacher else None,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return ConversationItem(
        id=convo.id,
        subject=convo.subject,
        title=convo.title,
        updated_at=convo.updated_at.isoformat() if convo.updated_at else "",
    )


@router.get("/conversations", response_model=list[ConversationItem])
def list_conversations(
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
    subject: Subject = Query("math"),
):
    """列出当前学生在当前班级下的会话（按最近更新倒序）。"""
    class_id = require_student_class_id(current.class_id)
    rows = (
        db.query(Conversation)
        .filter(Conversation.student_id == current.user_id, Conversation.class_id == class_id, Conversation.subject == subject)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )
    return [
        ConversationItem(
            id=c.id,
            subject=c.subject,
            title=c.title,
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )
        for c in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageItem])
def conversation_messages(
    conversation_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """读取某会话的完整消息记录（按时间正序）。"""
    convo = _coerce_conversation(db, conversation_id, current)
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.id.asc())
        .all()
    )
    return [
        MessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=[
                Citation(**item)
                for item in (json.loads(m.sources) if m.sources else [])
            ],
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in rows
    ]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """删除当前学生在当前班级下的一个会话（含其全部消息，CASCADE）。"""
    convo = _coerce_conversation(db, conversation_id, current)
    # SQLite 未启用外键级联，需先清空消息再删会话
    db.query(Message).filter(Message.conversation_id == convo.id).delete()
    db.delete(convo)
    db.commit()
    return {"ok": True}


@router.post("/conversations/{conversation_id}/chat")
def chat(
    conversation_id: int,
    body: ChatRequest,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """向某会话连续追问一条消息，SSE 流式返回 AI 回答。

    每日次数限制与旧 ask_ai 共用 AIQuestionLog（20 次/日）。流式结束后把
    user 消息 + assistant 消息写回会话，保证多轮上下文可续。
    """
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="问题不能为空")

    convo = _coerce_conversation(db, conversation_id, current)

    # 每日次数限制（复用 AIQuestionLog 计数）
    allowed, reason = check_ai_limit(db, current.user_id)
    if not allowed:
        background.add_task(
            _async_audit,
            user_id=current.user_id,
            role=current.role,
            path=request.url.path,
            method=request.method,
            status_code=429,
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )

    # 每轮核对当前任课配置；短追问结合最近用户题目重新检索，不复用旧来源编号。
    cfg, teacher = resolve_assistant(db, convo.class_id, convo.subject, convo.teacher_id)
    if convo.teacher_id is None and teacher is not None:
        convo.teacher_id = teacher.id
    # 读取历史（当前问题写入前读取，用于多轮上下文）
    prior = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.id.asc())
        .all()
    )
    history = [
        (m.role, m.content) for m in prior if m.role in ("user", "assistant")
    ][-CHAT_HISTORY_TURNS * 2 :]
    is_first = not prior
    retrieval_query = followup_retrieval_query(question, history) if cfg and cfg.tutor_enabled else question
    context_block, citations = _retrieve_context(db, convo.class_id, retrieval_query, convo.subject)

    # 记录提问（计入每日限额），并立即写入 user 消息
    log = record_ai_question(
        db,
        student_id=current.user_id,
        class_id=convo.class_id,
        question=question,
    )
    db.add(
        Message(
            conversation_id=convo.id,
            role="user",
            content=question,
            sources=None,
        )
    )
    # 首条消息时以问题截断作会话标题
    if is_first:
        convo.title = question[:20] if len(question) > 20 else question
    db.commit()

    remaining = AI_DAILY_LIMIT - get_ai_daily_count(db, current.user_id)

    # 解析该班级 AgentConfig 提示词（自定义 + 解题引导技能）
    system_prompt = f"你当前是{SUBJECT_NAMES[convo.subject]}学习助手。\n" + resolve_system_prompt(cfg)
    tutor_on = bool(cfg is not None and cfg.tutor_enabled)
    messages = build_chat_messages(system_prompt, history, question, context_block, tutor_on)

    async def event_stream():
        assistant_text = ""
        final_sources = []
        try:
            async for delta in stream_chat(messages):
                assistant_text += delta
                yield _sse({"type": "delta", "content": delta})
            assistant_text, final_sources = validate_references(assistant_text, citations)
            yield _sse(
                {
                    "type": "done",
                    "answer": assistant_text,
                    "citations": [c.model_dump() for c in final_sources],
                    "remaining": remaining,
                }
            )
        except LLMGenerationError:
            # 未配置 Key 或调用失败：降级为展示检索结果
            if assistant_text:
                assistant_text, final_sources = validate_references(assistant_text, citations)
                assistant_text += "\n\n（AI 生成中断）"
            else:
                head = "AI 生成服务暂不可用" if settings.deepseek_api_key else "AI 生成服务未配置 API Key"
                assistant_text = f"{head}，暂仅展示检索到的相关段落：\n{context_block or '无检索结果'}"
                final_sources = citations
            yield _sse({"type": "error", "message": assistant_text,
                        "citations": [c.model_dump() for c in final_sources], "remaining": remaining})
        finally:
            _persist_assistant_message(convo.id, assistant_text, final_sources, log.id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
