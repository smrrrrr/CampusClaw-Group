"""智能命题接口（add-smart-question-generation）。

所有接口基于当前数据库身份校验：
- 学生访问 403（get_current_teacher）
- 题库题目对本学科教师可见
- 候选题、生成记录、试卷仅作者可见；越权按编号访问返回与不存在一致的 404
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from config import settings
from database import get_db
from deps import CurrentUser, get_current_teacher
from lesson_service import build_resources, context_text
from llm_service import LLMGenerationError, stream_chat
from material_service import resolve_abs_path, write_physical_file
from models import (
    Material,
    MaterialAsset,
    QuestionEvent,
    QuestionGeneration,
    QuestionItem,
    QuestionPaper,
    QuestionPaperItem,
    QuizPublication,
    ResearchMaterial,
    Role,
    User,
)
from question_service import (
    DIFFICULTIES,
    QUESTION_PROMPT,
    QUESTION_TYPES,
    OutputParseError,
    allocate,
    build_user_message,
    content_sha256,
    parse_output,
    render_answer_key,
    render_student_paper,
    stem_key,
    subject_knowledge_points,
    validate_batch,
    validate_question,
    validate_student_paper,
)

router = APIRouter(prefix="/api/teacher/quiz", tags=["quiz"])

# 同一教师同时只允许一个命题任务：teacher_id → (令牌, 开始时间)。
# 检查与登记在同一把锁内完成；生成本身 180 秒超时，超过 TTL 的登记视为残留
# （例如流式响应尚未开始就被取消，生成器的 finally 不会执行），允许重新登记。
active_quiz_generations: dict[int, tuple[str, float]] = {}
_generation_guard = threading.Lock()
GENERATION_LOCK_TTL = 300


def acquire_generation(teacher_id: int) -> str | None:
    """登记一个命题任务；已有未过期任务时返回 None。"""
    now = time.monotonic()
    with _generation_guard:
        held = active_quiz_generations.get(teacher_id)
        if held is not None and now - held[1] < GENERATION_LOCK_TTL:
            return None
        token = uuid.uuid4().hex
        active_quiz_generations[teacher_id] = (token, now)
        return token


def release_generation(teacher_id: int, token: str) -> None:
    """只释放本任务自己的登记，不误删过期后被新任务接替的登记。"""
    with _generation_guard:
        held = active_quiz_generations.get(teacher_id)
        if held is not None and held[0] == token:
            del active_quiz_generations[teacher_id]

QUESTION_TYPES_ALL = list(QUESTION_TYPES.keys())


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------


def current_teacher(db: Session, current: CurrentUser) -> User:
    teacher = db.get(User, current.user_id, populate_existing=True)
    if teacher is None or teacher.role != Role.teacher:
        raise HTTPException(status_code=403, detail="仅教师可执行该操作")
    if not teacher.subject or teacher.subject not in SUBJECT_NAMES:
        raise HTTPException(status_code=403, detail="请先分配任教学科")
    return teacher


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


def record_event(db: Session, *, actor_id: int, subject: str | None, target_type: str,
                 target_id: int | None, action: str, detail: dict) -> None:
    db.add(QuestionEvent(actor_id=actor_id, subject=subject, target_type=target_type,
                         target_id=target_id, action=action,
                         detail_json=json.dumps(detail, ensure_ascii=False)))


def visible_item(db: Session, item_id: int, teacher: User) -> QuestionItem:
    """同学科且（approved，或作者是本人）才可见，否则 404。"""
    item = db.get(QuestionItem, item_id)
    if item is None or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status != "approved" and item.author_id != teacher.id:
        raise HTTPException(status_code=404, detail="题目不存在")
    return item


def owned_paper(db: Session, paper_id: int, teacher: User) -> QuestionPaper:
    paper = db.get(QuestionPaper, paper_id)
    if paper is None or paper.teacher_id != teacher.id or paper.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="试卷不存在")
    return paper


def owned_generation(db: Session, gen_id: int, teacher: User) -> QuestionGeneration:
    gen = db.get(QuestionGeneration, gen_id)
    if gen is None or gen.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return gen


def serialize_item(item: QuestionItem, with_sources: bool = False) -> dict:
    data = dict(
        id=item.id, subject=item.subject, author_id=item.author_id,
        type=item.type, difficulty=item.difficulty,
        knowledge_points=json.loads(item.knowledge_points_json or "[]"),
        stem=item.stem, options=json.loads(item.options_json or "[]"),
        answer=json.loads(item.answer_json), explanation=item.explanation,
        origin=item.origin, status=item.status, archived=item.archived,
        modified_in_review=item.modified_in_review,
        reject_reason=item.reject_reason, revision=item.revision,
        created_at=_iso(item.created_at), updated_at=_iso(item.updated_at),
    )
    if with_sources:
        data["sources"] = json.loads(item.sources_json or "[]")
        data["assets"] = json.loads(item.assets_json or "[]")
        data["source_status"] = source_status(item)
    return data


def source_status(item: QuestionItem) -> str:
    """原稿状态：一致 / 已变化 / 已删除（按入库时 SHA 与当前文件对比）。"""
    sources = json.loads(item.sources_json or "[]")
    if not sources:
        return "empty"
    changed = False
    missing = False
    for src in sources:
        rm = src.get("research_material_id")
        sha = src.get("file_sha256")
        if not rm:
            continue
        # 通过资料 id 查不到时，退化为按快照判断
        path_rel = src.get("file_path")
        if path_rel:
            path = resolve_abs_path(path_rel)
            if not path.is_file():
                missing = True
                continue
            from citation_service import file_sha256
            if sha and file_sha256(path) != sha:
                changed = True
    if missing:
        return "deleted"
    if changed:
        return "changed"
    return "consistent"


def serialize_paper(db: Session, paper: QuestionPaper, detail: bool = False) -> dict:
    items = db.query(QuestionPaperItem).filter_by(paper_id=paper.id).order_by(QuestionPaperItem.position).all()
    data = dict(
        id=paper.id, title=paper.title, subject=paper.subject, duration=paper.duration,
        status=paper.status, revision=paper.revision, item_count=len(items),
        total_score=round(sum(float(i.score) for i in items), 2),
        created_at=_iso(paper.created_at), updated_at=_iso(paper.updated_at),
        finalized_at=_iso(paper.finalized_at),
    )
    if detail:
        data["blueprint"] = json.loads(paper.blueprint_json or "{}")
        data["items"] = [
            dict(position=i.position, question_item_id=i.question_item_id,
                 score=i.score, snapshot=json.loads(i.snapshot_json or "{}"))
            for i in items
        ]
    return data


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False, default=str) + "\n\n"


# ---------------------------------------------------------------------------
# 知识点词表（tasks 1.2 / 3.1）
# ---------------------------------------------------------------------------


@router.get("/knowledge-points", summary="本学科知识点词表",
            responses={403: {"description": "未分配学科"}})
def knowledge_points(current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    return {"subject": teacher.subject, "knowledge_points": subject_knowledge_points(teacher.subject)}


# ---------------------------------------------------------------------------
# 生成请求模型
# ---------------------------------------------------------------------------


class GenerationRequest(BaseModel):
    research_material_ids: list[int] = Field(min_length=1, max_length=5)
    knowledge_points: list[str] = Field(min_length=1, max_length=5)
    type_counts: dict[str, int] = Field(default_factory=dict)
    difficulty_counts: dict[str, int] = Field(default_factory=dict)
    requirements: str = Field(default="", max_length=2000)


def _validate_generation_request(body: GenerationRequest, subject: str) -> dict:
    """校验配额与知识点；返回规范化 quotas。"""
    types = {t: 0 for t in QUESTION_TYPES_ALL}
    for t, n in body.type_counts.items():
        if t not in QUESTION_TYPES:
            raise HTTPException(status_code=400, detail=f"未知题型：{t}")
        if not isinstance(n, int) or n < 0 or n > 10:
            raise HTTPException(status_code=400, detail=f"题型 {t} 题数须为 0–10")
        types[t] = n
    diffs = {d: 0 for d in DIFFICULTIES}
    for d, n in body.difficulty_counts.items():
        if d not in DIFFICULTIES:
            raise HTTPException(status_code=400, detail=f"未知难度：{d}")
        if not isinstance(n, int) or n < 0 or n > 20:
            raise HTTPException(status_code=400, detail=f"难度 {d} 题数须为 0–20")
        diffs[d] = n
    total_type = sum(types.values())
    total_diff = sum(diffs.values())
    if total_type != total_diff:
        raise HTTPException(status_code=400, detail=f"题型合计（{total_type}）与难度合计（{total_diff}）不相等")
    if not (1 <= total_type <= 20):
        raise HTTPException(status_code=400, detail="总题数须为 1–20")
    vocab = set(subject_knowledge_points(subject))
    for kp in body.knowledge_points:
        if kp not in vocab:
            raise HTTPException(status_code=400, detail=f"知识点「{kp}」不在本学科词表中，请从词表选择")
    return {"types": types, "difficulties": diffs}


def _load_sources(db: Session, ids: list[int], teacher: User) -> list[ResearchMaterial]:
    """按学科过滤读取资料；任何一份不属于本学科或不存在 → 404。"""
    sources = []
    for mid in ids:
        m = db.get(ResearchMaterial, mid)
        if m is None or m.subject != teacher.subject:
            raise HTTPException(status_code=404, detail="资料不存在")
        sources.append(m)
    return sources


@router.post("/generations", summary="发起命题生成（SSE）",
             responses={400: {"description": "配额/知识点非法"}, 403: {"description": "未配学科"},
                        404: {"description": "资料不存在或跨学科"}, 409: {"description": "已有生成任务"},
                        503: {"description": "未配置模型 Key"}})
def create_generation(body: GenerationRequest, request: Request,
                      current: CurrentUser = Depends(get_current_teacher),
                      db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    quotas = _validate_generation_request(body, teacher.subject)

    # 资料校验在文件操作前完成（404 优先于 503）
    sources = _load_sources(db, list(dict.fromkeys(body.research_material_ids)), teacher)

    if not settings.deepseek_api_key:
        raise HTTPException(status_code=503, detail="AI 服务尚未配置，请配置 DeepSeek 后重试")

    try:
        resources = build_resources(sources, " ".join(body.knowledge_points), body.requirements)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request_json = body.model_dump()
    context = context_text(resources)
    user_message = build_user_message(quotas, body.knowledge_points, body.requirements, context)
    messages = [{"role": "system", "content": QUESTION_PROMPT}, {"role": "user", "content": user_message}]
    ctx = {
        "knowledge_points": body.knowledge_points,
        "source_refs": {ref["ref"] for ref in resources["references"]},
        "assets": [a["name"] for a in resources.get("assets", [])],
    }
    assets_by_name = {a["name"]: a for a in _asset_files(sources, resources)}

    # 登记放在所有可能抛错的准备工作之后，登记成功即交给生成流在 finally 中释放
    lock_token = acquire_generation(teacher.id)
    if lock_token is None:
        raise HTTPException(status_code=409, detail="已有命题任务正在生成，请等待完成")

    async def stream():
        accepted_ids: list[int] = []
        # 已写入成功或失败记录后置 True；断开 / 取消时据此补写一条失败记录
        settled = False

        def fail(error: str) -> None:
            nonlocal settled
            settled = True
            _persist_failed(db, teacher, request_json, resources, error)

        try:
            yield _sse({"type": "progress", "chars": 0})
            raw = ""
            last_emit = 0
            try:
                async with asyncio.timeout(180):
                    async for delta in stream_chat(messages, timeout=90, temperature=0.2):
                        if await request.is_disconnected():
                            fail(DISCONNECTED)
                            return
                        raw += delta
                        if len(raw) - last_emit >= 500:
                            last_emit = len(raw)
                            yield _sse({"type": "progress", "chars": len(raw)})
            except (LLMGenerationError, TimeoutError) as exc:
                fail(str(exc))
                yield _sse({"type": "error", "message": "模型生成失败或超时，未保存任何题目，请重试"})
                return

            try:
                parsed, escape_repairs = parse_output(raw)
            except OutputParseError as exc:
                # SSE 文案不变；落库的失败原因带行列，并去掉夹带非 ASCII 的原文片段
                fail(_json_error_reason(str(exc)))
                yield _sse({"type": "error", "message": f"模型输出格式错误：{exc}，未保存任何题目"})
                return

            # 生成后再核对一次资料与原图指纹：生成期间资料被删除或替换则整批作废
            changed = _changed_sources(db, resources, teacher)
            if changed:
                fail(f"资料在生成期间已变化：{'、'.join(changed)}")
                yield _sse({"type": "error", "message": "所选资料在生成期间已变化，未保存任何题目，请重新生成"})
                return

            accepted, rejected = validate_batch(parsed["questions"], ctx, quotas)
            gaps = [g for g in parsed["gaps"] if isinstance(g, dict)]

            # 单事务落库：生成记录 + 通过题目 + 事件
            try:
                gen = QuestionGeneration(
                    teacher_id=teacher.id, subject=teacher.subject,
                    request_json=json.dumps(request_json, ensure_ascii=False),
                    resources_json=json.dumps(resources, ensure_ascii=False),
                    status="succeeded", accepted_count=len(accepted),
                    rejected_count=len(rejected),
                    gaps_json=json.dumps(gaps, ensure_ascii=False),
                )
                db.add(gen)
                db.flush()
                accepted_ids = _insert_items(db, teacher, gen.id, accepted, resources, assets_by_name)
                record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="generation",
                             target_id=gen.id, action="generate",
                             detail={"accepted": len(accepted), "rejected": len(rejected), "gaps": len(gaps),
                                     "escape_repairs": escape_repairs})
                db.commit()
                settled = True
            except Exception:
                db.rollback()
                fail("保存题目失败")
                yield _sse({"type": "error", "message": "保存题目失败，请重试"})
                return

            yield _sse({"type": "done", "generation_id": gen.id, "accepted_ids": accepted_ids,
                        "rejected": rejected, "gaps": gaps})
        except (asyncio.CancelledError, GeneratorExit):
            # 服务端取消流（客户端断开）时同步补写失败记录，再继续向上抛出
            if not settled:
                db.rollback()
                fail(DISCONNECTED)
            raise
        except Exception as exc:
            # 其余意外错误：同样不落题、写失败记录并告知客户端；结果已落库则照常抛出
            if settled:
                raise
            db.rollback()
            fail(f"生成过程出错：{type(exc).__name__}")
            yield _sse({"type": "error", "message": "生成过程出错，未保存任何题目，请重试"})
        finally:
            release_generation(teacher.id, lock_token)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


DISCONNECTED = "客户端断开连接，生成中止"
# 「模型输出不是合法 JSON（第 L 行第 C 列：<错误类型>）」：行列与错误类型都是 ASCII
JSON_ERROR_PREFIX = "模型输出不是合法 JSON（"
JSON_POSITION = re.compile(r"^第 (\d+) 行第 (\d+) 列：([A-Za-z_]+)$")
# parse_output 自己给出的结构说明：不含模型原文，落库时原样保留
OUTPUT_STRUCTURE_ERRORS = frozenset({"模型输出不是 JSON 对象", "JSON 必须包含 questions 与 gaps 两个数组"})


def _json_error_reason(message: str) -> str:
    """把解析失败原因写成带行列的形式，不夹带模型原文。

    json 的报错文案会摘取出错位置的原文片段（可能含资料摘录或答案），落库与审计
    只留行列与错误类型；服务端自己给的说明（缺字段等）不含模型原文，原样保留。
    """
    if isinstance(message, str) and message.startswith(JSON_ERROR_PREFIX):
        position = message[len(JSON_ERROR_PREFIX):].rstrip("）) ")
        matched = JSON_POSITION.match(position)
        if matched:
            return f"模型输出不是合法 JSON（第 {matched.group(1)} 行第 {matched.group(2)} 列：{matched.group(3)}）"
        return "模型输出不是合法 JSON（位置无法确定）"
    if isinstance(message, str) and message in OUTPUT_STRUCTURE_ERRORS:
        return message
    return "模型输出不是合法 JSON（位置无法确定）"


def _changed_sources(db: Session, resources: dict, teacher: User) -> list[str]:
    """与生成前的资源快照比对：资料被删除、改学科、正文指纹或所用原图指纹变化都算变化。"""
    db.expire_all()
    changed = []
    for sid in resources["source_ids"]:
        source = db.get(ResearchMaterial, sid)
        if source is None or source.subject != teacher.subject:
            changed.append(f"资料 {sid} 已删除")
            continue
        if source.source_sha256 != resources["source_hashes"][str(sid)]:
            changed.append(source.filename)
            continue
        originals = {a["name"]: a.get("sha256") for a in json.loads(source.assets_json or "[]")}
        if any(originals.get(a["source_name"]) != a["sha256"]
               for a in resources.get("assets", []) if a["source_id"] == sid):
            changed.append(f"{source.filename} 的配图")
    return changed


def _asset_files(sources: list[ResearchMaterial], resources: dict) -> list[dict]:
    """给上下文配图清单补上原图存储路径与类型，发布时据此复制并核对指纹。"""
    originals = {s.id: {a["name"]: a for a in json.loads(s.assets_json or "[]")} for s in sources}
    result = []
    for asset in resources.get("assets", []):
        original = originals.get(asset["source_id"], {}).get(asset["source_name"], {})
        result.append(dict(asset, path=original.get("path"), mime=original.get("mime")))
    return result


def _item_assets(q: dict, sources: list[dict], assets_by_name: dict) -> list[dict]:
    """本题的配图清单：出处所在资料的配图，加上题面实际引用的配图（不整批照抄）。"""
    from question_service import IMAGE, safe_name
    cited = {s.get("research_material_id") for s in sources}
    text = "\n".join([q["stem"], q["explanation"], json.dumps(q["answer"], ensure_ascii=False),
                      *(o["text"] for o in q["options"])])
    used = {safe_name(m.group(2).strip()) for m in IMAGE.finditer(text)}
    return [a for name, a in assets_by_name.items() if a.get("source_id") in cited or name in used]


def _persist_failed(db: Session, teacher: User, request_json: dict, resources: dict, error: str) -> None:
    try:
        gen = QuestionGeneration(teacher_id=teacher.id, subject=teacher.subject,
                                 request_json=json.dumps(request_json, ensure_ascii=False),
                                 resources_json=json.dumps(resources, ensure_ascii=False),
                                 status="failed", error=error[:500])
        db.add(gen)
        db.flush()
        record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="generation",
                     target_id=gen.id, action="generate_failed", detail={"error": error[:200]})
        db.commit()
    except Exception:
        db.rollback()


def _snapshot_sources(db: Session, accepted_item: dict, resources: dict) -> list[dict]:
    """把题目 source_refs 对应的引用条目写成快照（含资料 file_path，用于原稿状态核对）。"""
    ref_by_name = {ref["ref"]: ref for ref in resources["references"]}
    snapshots = []
    for ref in accepted_item["source_refs"]:
        src = ref_by_name.get(ref)
        if not src:
            continue
        rm = db.get(ResearchMaterial, src["research_material_id"])
        snapshots.append(dict(
            ref=src["ref"], research_material_id=src["research_material_id"],
            filename=src["filename"], start_line=src["start_line"], end_line=src["end_line"],
            excerpt=src["excerpt"], file_sha256=src["file_sha256"],
            file_path=rm.file_path if rm else None,
        ))
    return snapshots


def _content(q: dict) -> dict:
    """参与内容指纹的字段：校验后的题目本身，不含批次内序号。生成与修改用同一口径。"""
    return {k: v for k, v in q.items() if k != "index"}


def _insert_items(db: Session, teacher: User, generation_id: int, accepted: list[dict],
                  resources: dict, assets_by_name: dict) -> list[int]:
    ids = []
    for q in accepted:
        sources = _snapshot_sources(db, q, resources)
        item = QuestionItem(
            subject=teacher.subject, author_id=teacher.id, generation_id=generation_id,
            type=q["type"], difficulty=q["difficulty"],
            knowledge_points_json=json.dumps(q["knowledge_points"], ensure_ascii=False),
            stem=q["stem"], options_json=json.dumps(q["options"], ensure_ascii=False),
            answer_json=json.dumps(q["answer"], ensure_ascii=False),
            explanation=q["explanation"], origin=q["origin"],
            sources_json=json.dumps(sources, ensure_ascii=False),
            assets_json=json.dumps(_item_assets(q, sources, assets_by_name), ensure_ascii=False),
            status="pending", archived=False,
            stem_key=stem_key(q["stem"]), content_sha256=content_sha256(_content(q)),
            revision=1,
        )
        db.add(item)
        db.flush()
        ids.append(item.id)
    return ids


# ---------------------------------------------------------------------------
# 生成记录（tasks 3.6）
# ---------------------------------------------------------------------------


@router.get("/generations", summary="本人生成记录")
def list_generations(current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    rows = db.query(QuestionGeneration).filter_by(teacher_id=teacher.id).order_by(
        QuestionGeneration.created_at.desc()).all()
    return {"items": [
        dict(id=g.id, subject=g.subject, status=g.status, accepted_count=g.accepted_count,
             rejected_count=g.rejected_count, error=g.error, created_at=_iso(g.created_at))
        for g in rows
    ]}


@router.get("/generations/{gen_id}", summary="本人生成记录详情", responses={404: {"description": "不存在或非本人"}})
def get_generation(gen_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    g = owned_generation(db, gen_id, teacher)
    return dict(id=g.id, subject=g.subject, status=g.status, request=json.loads(g.request_json),
                accepted_count=g.accepted_count, rejected_count=g.rejected_count,
                gaps=json.loads(g.gaps_json), error=g.error, created_at=_iso(g.created_at))


# ---------------------------------------------------------------------------
# 题目列表与详情（tasks 4.1）
# ---------------------------------------------------------------------------


@router.get("/items", summary="题目列表（候选仅本人，approved 本学科）")
def list_items(status_: str | None = Query(None, alias="status"),
               type_: str | None = Query(None, alias="type"),
               difficulty: str | None = Query(None),
               knowledge_point: str | None = Query(None),
               q: str | None = Query(None),
               author_id: int | None = Query(None),
               archived: bool | None = Query(None),
               page: int = Query(1, ge=1),
               current: CurrentUser = Depends(get_current_teacher),
               db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    query = db.query(QuestionItem).filter(QuestionItem.subject == teacher.subject)
    if status_ == "approved":
        query = query.filter(QuestionItem.status == "approved")
    elif status_ in ("pending", "rejected"):
        query = query.filter(QuestionItem.status == status_, QuestionItem.author_id == teacher.id)
    else:
        # 未指定：本人的候选 + 本学科题库
        from sqlalchemy import or_
        query = query.filter(or_(QuestionItem.status == "approved", QuestionItem.author_id == teacher.id))
    if type_:
        query = query.filter(QuestionItem.type == type_)
    if difficulty:
        query = query.filter(QuestionItem.difficulty == difficulty)
    if knowledge_point:
        query = query.filter(QuestionItem.knowledge_points_json.contains(knowledge_point))
    if q:
        query = query.filter(QuestionItem.stem.contains(q))
    if author_id is not None:
        query = query.filter(QuestionItem.author_id == author_id)
    if archived is not None:
        query = query.filter(QuestionItem.archived.is_(archived))
    else:
        query = query.filter(QuestionItem.archived.is_(False))
    total = query.count()
    rows = query.order_by(QuestionItem.id.desc()).offset((page - 1) * 50).limit(50).all()
    return {"items": [serialize_item(i) for i in rows], "total": total, "page": page}


@router.get("/items/{item_id}", summary="题目详情（含出处快照、原稿状态、事件历史）",
            responses={404: {"description": "不存在或不可见"}})
def get_item(item_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = visible_item(db, item_id, teacher)
    data = serialize_item(item, with_sources=True)
    # 下架 / 恢复仅原作者可做（_set_archived 对他人返回 404），界面据此决定是否显示按钮
    data["can_archive"] = item.status == "approved" and item.author_id == teacher.id
    events = db.query(QuestionEvent).filter_by(target_type="item", target_id=item.id).order_by(
        QuestionEvent.created_at).all()
    data["events"] = [dict(action=e.action, detail=json.loads(e.detail_json or "{}"),
                           actor_id=e.actor_id, created_at=_iso(e.created_at)) for e in events]
    return data


# ---------------------------------------------------------------------------
# 复核（tasks 4.2 / 4.3 / 4.4）
# ---------------------------------------------------------------------------


class ItemEditRequest(BaseModel):
    revision: int = Field(ge=1)
    stem: str = Field(min_length=1)
    options: list = Field(default_factory=list)
    answer: object = None
    explanation: str = Field(min_length=1)
    knowledge_points: list[str] = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)


class RevisionRequest(BaseModel):
    revision: int = Field(ge=1)


class ApproveRequest(RevisionRequest):
    confirmed: bool = False


class RejectRequest(RevisionRequest):
    reason: str = Field(default="", max_length=500)


def _edit_context(teacher: User, item: QuestionItem, original_sources: list[dict]) -> dict:
    return {
        "knowledge_points": subject_knowledge_points(teacher.subject),
        "source_refs": {s["ref"] for s in original_sources},
        # 修改与通过时只允许生成时所选资料的原图
        "assets": [a["name"] for a in json.loads(item.assets_json or "[]")],
    }


@router.put("/items/{item_id}", summary="修改候选题", responses={400: {"description": "校验失败"}, 404: {"description": "不存在"}, 409: {"description": "非待复核或版本冲突"}})
def update_item(item_id: int, body: ItemEditRequest,
                current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = db.get(QuestionItem, item_id)
    if item is None or item.author_id != teacher.id or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="只有待复核题目可修改；入库题目请复制为新候选")
    original_sources = json.loads(item.sources_json or "[]")
    ctx = _edit_context(teacher, item, original_sources)
    raw_q = {
        "type": item.type, "difficulty": item.difficulty,
        "knowledge_points": body.knowledge_points, "stem": body.stem,
        "options": body.options, "answer": body.answer,
        "explanation": body.explanation, "origin": item.origin,
        "source_refs": body.source_refs,
    }
    normalized, reasons = validate_question(raw_q, ctx)
    if reasons:
        raise HTTPException(status_code=400, detail="；".join(reasons))
    if not normalized["source_refs"]:
        raise HTTPException(status_code=400, detail="至少保留一个出处")

    before = item.content_sha256
    after = content_sha256(_content(normalized))
    values = dict(
        stem=normalized["stem"], options_json=json.dumps(normalized["options"], ensure_ascii=False),
        answer_json=json.dumps(normalized["answer"], ensure_ascii=False),
        explanation=normalized["explanation"],
        knowledge_points_json=json.dumps(normalized["knowledge_points"], ensure_ascii=False),
        sources_json=json.dumps([s for s in original_sources if s["ref"] in normalized["source_refs"]], ensure_ascii=False),
        stem_key=stem_key(normalized["stem"]), content_sha256=after,
        modified_in_review=bool(item.modified_in_review) or before != after,
        revision=body.revision + 1, updated_at=datetime.now(timezone.utc),
    )
    count = db.query(QuestionItem).filter_by(id=item.id, revision=body.revision).update(values, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="题目已在其他窗口更新，请重新加载")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=item.id, action="modify",
                 detail={"before": before, "after": values["content_sha256"]})
    db.commit()
    return serialize_item(db.get(QuestionItem, item.id), with_sources=True)


@router.post("/items/{item_id}/approve", summary="通过复核", responses={400: {"description": "未确认或校验失败"}, 404: {"description": "不存在"}, 409: {"description": "重复题或状态冲突"}})
def approve_item(item_id: int, body: ApproveRequest,
                 current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = db.get(QuestionItem, item_id)
    if item is None or item.author_id != teacher.id or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status == "rejected":
        raise HTTPException(status_code=409, detail="已驳回的题目不能通过，只能删除")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="只有待复核题目可通过")
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="请确认已核对题干、答案、解析与出处后再通过")

    original_sources = json.loads(item.sources_json or "[]")
    ctx = _edit_context(teacher, item, original_sources)
    raw_q = {
        "type": item.type, "difficulty": item.difficulty,
        "knowledge_points": json.loads(item.knowledge_points_json or "[]"),
        "stem": item.stem, "options": json.loads(item.options_json or "[]"),
        "answer": json.loads(item.answer_json), "explanation": item.explanation,
        "origin": item.origin, "source_refs": [s["ref"] for s in original_sources],
    }
    normalized, reasons = validate_question(raw_q, ctx)
    if reasons:
        raise HTTPException(status_code=400, detail="；".join(reasons))

    # 查重：同学科 approved 且未下架
    key = stem_key(item.stem)
    dup = db.query(QuestionItem).filter(
        QuestionItem.subject == teacher.subject, QuestionItem.status == "approved",
        QuestionItem.archived.is_(False), QuestionItem.stem_key == key, QuestionItem.id != item.id,
    ).first()
    if dup is not None:
        raise HTTPException(status_code=409, detail=f"与本学科已有题目 #{dup.id} 题干重复")

    values = dict(status="approved", reviewed_by=teacher.id,
                  reviewed_at=datetime.now(timezone.utc), reject_reason=None,
                  revision=body.revision + 1, updated_at=datetime.now(timezone.utc))
    count = db.query(QuestionItem).filter_by(id=item.id, revision=body.revision, status="pending").update(
        values, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="题目已在其他窗口更新，请重新加载")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=item.id, action="approve",
                 detail={"modified_in_review": bool(item.modified_in_review)})
    db.commit()
    return serialize_item(db.get(QuestionItem, item.id), with_sources=True)


@router.post("/items/{item_id}/reject", summary="驳回候选题", responses={404: {"description": "不存在"}, 409: {"description": "非待复核"}})
def reject_item(item_id: int, body: RejectRequest,
                current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = db.get(QuestionItem, item_id)
    if item is None or item.author_id != teacher.id or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="只有待复核题目可驳回")
    values = dict(status="rejected", reject_reason=body.reason or None,
                  revision=body.revision + 1, updated_at=datetime.now(timezone.utc))
    count = db.query(QuestionItem).filter_by(id=item.id, revision=body.revision, status="pending").update(
        values, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="题目已在其他窗口更新，请重新加载")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=item.id, action="reject", detail={"reason": body.reason})
    db.commit()
    return serialize_item(db.get(QuestionItem, item.id), with_sources=True)


@router.post("/items/{item_id}/copy", summary="复制为新候选", responses={404: {"description": "不存在或不可见"}})
def copy_item(item_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = visible_item(db, item_id, teacher)
    if item.status != "approved":
        raise HTTPException(status_code=400, detail="只有入库题目可复制为新候选")
    new_item = QuestionItem(
        subject=teacher.subject, author_id=teacher.id, derived_from_id=item.id,
        type=item.type, difficulty=item.difficulty,
        knowledge_points_json=item.knowledge_points_json, stem=item.stem,
        options_json=item.options_json, answer_json=item.answer_json,
        explanation=item.explanation, origin=item.origin,
        sources_json=item.sources_json, assets_json=item.assets_json,
        status="pending", archived=False, stem_key=item.stem_key,
        content_sha256=item.content_sha256, revision=1,
    )
    db.add(new_item)
    db.flush()
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=new_item.id, action="copy", detail={"derived_from_id": item.id})
    db.commit()
    return serialize_item(new_item, with_sources=True)


@router.post("/items/{item_id}/archive", summary="下架题目", responses={404: {"description": "不存在"}, 409: {"description": "非入库题"}})
def archive_item(item_id: int, body: RevisionRequest,
                 current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return _set_archived(db, item_id, body, current, True)


@router.post("/items/{item_id}/restore", summary="恢复题目", responses={404: {"description": "不存在"}, 409: {"description": "非入库题"}})
def restore_item(item_id: int, body: RevisionRequest,
                 current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return _set_archived(db, item_id, body, current, False)


def _set_archived(db: Session, item_id: int, body: RevisionRequest, current: CurrentUser, archived: bool):
    teacher = current_teacher(db, current)
    item = db.get(QuestionItem, item_id)
    if item is None or item.author_id != teacher.id or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status != "approved":
        raise HTTPException(status_code=409, detail="只有入库题目可下架或恢复")
    values = dict(archived=archived, revision=body.revision + 1, updated_at=datetime.now(timezone.utc))
    count = db.query(QuestionItem).filter_by(id=item.id, revision=body.revision).update(values, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="题目已在其他窗口更新，请重新加载")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=item.id, action="archive" if archived else "restore", detail={})
    db.commit()
    return serialize_item(db.get(QuestionItem, item.id), with_sources=True)


@router.delete("/items/{item_id}", summary="删除候选题或已驳回题", responses={404: {"description": "不存在"}, 409: {"description": "入库题不可删除"}})
def delete_item(item_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    item = db.get(QuestionItem, item_id)
    if item is None or item.author_id != teacher.id or item.subject != teacher.subject:
        raise HTTPException(status_code=404, detail="题目不存在")
    if item.status == "approved":
        raise HTTPException(status_code=409, detail="入库题目不可删除，可下架")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="item",
                 target_id=item.id, action="delete", detail={"status": item.status})
    db.delete(item)
    db.commit()
    return {"message": "题目已删除", "id": item_id}


# ---------------------------------------------------------------------------
# 组卷（tasks 5.1 / 5.2 / 5.3）
# ---------------------------------------------------------------------------

PAPER_MAX_ITEMS = 50


class PaperGroup(BaseModel):
    type: str
    count: int = Field(ge=1, le=20)
    score: float = Field(ge=0.5, le=100)


class PaperCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    duration: int = Field(ge=10, le=180)
    knowledge_points: list[str] = Field(min_length=1, max_length=5)
    groups: list[PaperGroup] = Field(min_length=1, max_length=5)
    difficulty_pct: dict[str, int] = Field(default_factory=dict)


class PaperUpdateRequest(BaseModel):
    revision: int = Field(ge=1)
    items: list[dict] = Field(min_length=1)


def _validate_blueprint(body: PaperCreateRequest, subject: str) -> dict:
    vocab = set(subject_knowledge_points(subject))
    for kp in body.knowledge_points:
        if kp not in vocab:
            raise HTTPException(status_code=400, detail=f"知识点「{kp}」不在本学科词表中")
    if body.difficulty_pct:
        pct = {d: int(body.difficulty_pct.get(d, 0)) for d in DIFFICULTIES}
        for d, v in pct.items():
            if v < 0:
                raise HTTPException(status_code=400, detail="难度百分比不能为负")
        if sum(pct.values()) != 100:
            raise HTTPException(status_code=400, detail="易/中/难百分比合计必须为 100")
    else:
        pct = {"easy": 30, "medium": 50, "hard": 20}
    for g in body.groups:
        if g.type not in QUESTION_TYPES:
            raise HTTPException(status_code=400, detail=f"未知题型：{g.type}")
        # 分值步长 0.5
        if round(g.score * 2) != g.score * 2:
            raise HTTPException(status_code=400, detail="每题分值须以 0.5 为步长")
    total_items = sum(g.count for g in body.groups)
    if total_items > PAPER_MAX_ITEMS:
        raise HTTPException(status_code=400, detail=f"全卷题数不得超过 {PAPER_MAX_ITEMS}")
    return {"knowledge_points": body.knowledge_points, "groups": [g.model_dump() for g in body.groups],
            "difficulty_pct": pct}


def _used_counts(db: Session, subject: str) -> dict[int, int]:
    """统计每道题出现在 final 试卷中的次数（同一试卷只算一次）。"""
    rows = (
        db.query(QuestionPaperItem.question_item_id, QuestionPaperItem.paper_id)
        .join(QuestionPaper, QuestionPaper.id == QuestionPaperItem.paper_id)
        .filter(QuestionPaper.subject == subject, QuestionPaper.status == "final")
        .all()
    )
    seen: dict[int, set] = {}
    for qid, pid in rows:
        seen.setdefault(qid, set()).add(pid)
    return {qid: len(pids) for qid, pids in seen.items()}


def _select_items(db: Session, teacher: User, blueprint: dict) -> tuple[list[dict], list[dict]]:
    """按蓝图抽题。返回 (selected[{'question_item_id','score','snapshot'}], gaps[])。"""
    subject = teacher.subject
    kps = set(blueprint["knowledge_points"])
    pct = blueprint["difficulty_pct"]
    used = _used_counts(db, subject)
    chosen_ids: set[int] = set()
    selected: list[dict] = []
    gaps: list[dict] = []
    for group in blueprint["groups"]:
        qtype = group["type"]
        need = group["count"]
        alloc = allocate(need, pct)
        for d in DIFFICULTIES:
            n = alloc[d]
            if n <= 0:
                continue
            candidates = db.query(QuestionItem).filter(
                QuestionItem.subject == subject, QuestionItem.status == "approved",
                QuestionItem.archived.is_(False), QuestionItem.type == qtype, QuestionItem.difficulty == d,
            ).all()
            # 知识点交集过滤
            filtered = []
            for c in candidates:
                ckps = set(json.loads(c.knowledge_points_json or "[]"))
                if not (ckps & kps):
                    continue
                if c.id in chosen_ids:
                    continue
                filtered.append(c)
            filtered.sort(key=lambda c: (used.get(c.id, 0), c.id))
            picked = filtered[:n]
            if len(picked) < n:
                gaps.append({"type": qtype, "difficulty": d, "needed": n, "available": len(picked)})
            for c in picked:
                chosen_ids.add(c.id)
                selected.append(dict(question_item_id=c.id, score=group["score"], snapshot=serialize_item(c, with_sources=True)))
    return selected, gaps


@router.post("/papers", summary="按配比组卷", responses={400: {"description": "蓝图非法"}, 422: {"description": "题库不足，返回缺口"}})
def create_paper(body: PaperCreateRequest, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    blueprint = _validate_blueprint(body, teacher.subject)
    selected, gaps = _select_items(db, teacher, blueprint)
    if gaps:
        raise HTTPException(status_code=422, detail={"message": "题库不足，无法组卷", "gaps": gaps})
    paper = QuestionPaper(teacher_id=teacher.id, subject=teacher.subject, title=body.title.strip(),
                          duration=body.duration, blueprint_json=json.dumps(blueprint, ensure_ascii=False),
                          status="draft", revision=1)
    db.add(paper)
    db.flush()
    for pos, it in enumerate(selected, start=1):
        db.add(QuestionPaperItem(paper_id=paper.id, position=pos, question_item_id=it["question_item_id"],
                                 score=it["score"], snapshot_json=json.dumps(it["snapshot"], ensure_ascii=False)))
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                 target_id=paper.id, action="compose", detail={"item_count": len(selected)})
    db.commit()
    return serialize_paper(db, paper, detail=True)


@router.get("/papers", summary="本人试卷列表")
def list_papers(current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    rows = db.query(QuestionPaper).filter_by(teacher_id=teacher.id).order_by(QuestionPaper.created_at.desc()).all()
    return {"items": [serialize_paper(db, p) for p in rows]}


@router.get("/papers/{paper_id}", summary="试卷详情", responses={404: {"description": "不存在"}})
def get_paper(paper_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    return serialize_paper(db, owned_paper(db, paper_id, teacher), detail=True)


@router.put("/papers/{paper_id}", summary="修改草稿试卷", responses={400: {"description": "题目非法"}, 404: {"description": "不存在"}, 409: {"description": "非草稿或版本冲突"}})
def update_paper(paper_id: int, body: PaperUpdateRequest,
                 current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    if paper.status != "draft":
        raise HTTPException(status_code=409, detail="只能修改草稿试卷")
    if len(body.items) > PAPER_MAX_ITEMS:
        raise HTTPException(status_code=400, detail=f"题数不得超过 {PAPER_MAX_ITEMS}")
    seen_ids = set()
    prepared = []
    for it in body.items:
        qid = it.get("question_item_id")
        score = it.get("score")
        if not isinstance(qid, int) or qid in seen_ids:
            raise HTTPException(status_code=400, detail="题目编号非法或重复")
        if not isinstance(score, (int, float)) or score < 0.5 or score > 100 or round(score * 2) != score * 2:
            raise HTTPException(status_code=400, detail="分值须在 0.5–100 之间且以 0.5 为步长")
        q = db.get(QuestionItem, qid)
        if q is None or q.subject != teacher.subject or q.status != "approved":
            raise HTTPException(status_code=400, detail=f"题目 {qid} 不是本学科入库题目")
        if q.archived:
            raise HTTPException(status_code=400, detail=f"题目 {qid} 已下架，不能加入试卷")
        seen_ids.add(qid)
        prepared.append((qid, float(score), serialize_item(q, with_sources=True)))
    count = db.query(QuestionPaper).filter_by(id=paper.id, revision=body.revision, status="draft").update(
        {"revision": body.revision + 1, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="试卷已在其他窗口更新，请重新加载")
    db.query(QuestionPaperItem).filter_by(paper_id=paper.id).delete(synchronize_session=False)
    for pos, (qid, score, snap) in enumerate(prepared, start=1):
        db.add(QuestionPaperItem(paper_id=paper.id, position=pos, question_item_id=qid, score=score,
                                 snapshot_json=json.dumps(snap, ensure_ascii=False)))
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                 target_id=paper.id, action="edit_paper", detail={"item_count": len(prepared)})
    db.commit()
    return serialize_paper(db, db.get(QuestionPaper, paper.id), detail=True)


@router.post("/papers/{paper_id}/finalize", summary="定稿试卷", responses={404: {"description": "不存在"}, 409: {"description": "非草稿或版本冲突"}})
def finalize_paper(paper_id: int, body: RevisionRequest,
                   current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    if paper.status != "draft":
        raise HTTPException(status_code=409, detail="只有草稿试卷可定稿")
    count = db.query(QuestionPaper).filter_by(id=paper.id, revision=body.revision, status="draft").update(
        {"status": "final", "revision": body.revision + 1,
         "finalized_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)},
        synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="试卷已在其他窗口更新，请重新加载")
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                 target_id=paper.id, action="finalize", detail={})
    db.commit()
    return serialize_paper(db, db.get(QuestionPaper, paper.id), detail=True)


@router.post("/papers/{paper_id}/copy", summary="复制为新草稿", responses={404: {"description": "不存在"}})
def copy_paper(paper_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    items = db.query(QuestionPaperItem).filter_by(paper_id=paper.id).order_by(QuestionPaperItem.position).all()
    new_paper = QuestionPaper(teacher_id=teacher.id, subject=teacher.subject, title=paper.title,
                              duration=paper.duration, blueprint_json=paper.blueprint_json,
                              status="draft", revision=1, copied_from_id=paper.id)
    db.add(new_paper)
    db.flush()
    for pos, it in enumerate(items, start=1):
        db.add(QuestionPaperItem(paper_id=new_paper.id, position=pos, question_item_id=it.question_item_id,
                                 score=it.score, snapshot_json=it.snapshot_json))
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                 target_id=new_paper.id, action="copy_paper", detail={"from": paper.id})
    db.commit()
    return serialize_paper(db, new_paper, detail=True)


@router.delete("/papers/{paper_id}", summary="删除草稿试卷", responses={404: {"description": "不存在"}, 409: {"description": "非草稿"}})
def delete_paper(paper_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    if paper.status != "draft":
        raise HTTPException(status_code=409, detail="只能删除草稿试卷")
    db.query(QuestionPaperItem).filter_by(paper_id=paper.id).delete(synchronize_session=False)
    record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                 target_id=paper.id, action="delete_paper", detail={})
    db.delete(paper)
    db.commit()
    return {"message": "试卷已删除", "id": paper_id}


# ---------------------------------------------------------------------------
# 学生卷预览 / 发布 / 答案卷（tasks 5.4 / 5.5）
# ---------------------------------------------------------------------------


def _paper_items(db: Session, paper: QuestionPaper) -> list[dict]:
    rows = db.query(QuestionPaperItem).filter_by(paper_id=paper.id).order_by(QuestionPaperItem.position).all()
    return [dict(score=float(r.score), snapshot=json.loads(r.snapshot_json or "{}")) for r in rows]


@router.get("/papers/{paper_id}/preview", summary="学生卷预览（Markdown）", responses={404: {"description": "不存在"}})
def preview_paper(paper_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    markdown = render_student_paper({"title": paper.title, "duration": paper.duration}, _paper_items(db, paper))
    return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")


class PublishRequest(RevisionRequest):
    reviewed: bool = False
    class_ids: list[int] = Field(min_length=1, max_length=30)


@router.post("/papers/{paper_id}/publish", summary="分班发布试卷",
             responses={400: {"description": "未确认核对"}, 403: {"description": "非任教班级"}, 404: {"description": "不存在"},
                        409: {"description": "非定稿、指纹变化或版本冲突"}})
def publish_paper(paper_id: int, body: PublishRequest,
                  current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    if paper.status != "final":
        raise HTTPException(status_code=409, detail="请先定稿试卷再发布")
    if not body.reviewed:
        raise HTTPException(status_code=400, detail="请确认学生卷不含答案后再发布")
    allowed = set(json.loads(teacher.teaching_classes or "[]"))
    classes = list(dict.fromkeys(body.class_ids))
    if any(cid not in allowed for cid in classes):
        raise HTTPException(status_code=403, detail="只能发布到本人任教班级")

    paper_dict = {"title": paper.title, "duration": paper.duration}
    items = _paper_items(db, paper)
    markdown = render_student_paper(paper_dict, items)
    # 收集正文实际引用的配图
    from question_service import IMAGE, safe_name
    used_names = {safe_name(m.group(2).strip()) for m in IMAGE.finditer(markdown)}
    assets = _collect_assets(db, items, used_names)
    try:
        validate_student_paper(markdown, [a["name"] for a in assets])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = markdown.encode("utf-8")
    fingerprint = content_sha256(markdown)
    label = "试卷"
    filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", paper.title)[:140] + "（试卷）.md"
    kps = []
    for it in items:
        for kp in it["snapshot"].get("knowledge_points", []):
            if kp not in kps:
                kps.append(kp)
    tags = [SUBJECT_NAMES[teacher.subject], *kps[:3], label, "学生版"]

    before = paper.revision
    # 乐观锁 + 逐班创建
    count = db.query(QuestionPaper).filter_by(id=paper.id, revision=body.revision, status="final").update(
        {"revision": body.revision + 1, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="试卷已更新，请重新加载")

    paths, material_ids = [], []
    try:
        for cid in classes:
            previous = db.query(QuizPublication).filter_by(paper_id=paper.id, class_id=cid,
                                                          content_sha256=fingerprint).one_or_none()
            if previous is not None:
                material_ids.append(previous.material_id)
                continue
            directory = f"{cid}/quiz-{uuid.uuid4().hex}"
            paths.append(directory)
            path = f"{directory}/paper.md"
            write_physical_file(content, path)
            material = Material(class_id=cid, uploader_id=teacher.id, filename=filename, file_path=path,
                                file_type="text/markdown", file_size=len(content),
                                description=f"{SUBJECT_NAMES[teacher.subject]} · {label}",
                                tags=json.dumps(tags, ensure_ascii=False), is_indexed=False)
            db.add(material)
            db.flush()
            material_ids.append(material.id)
            for index, asset in enumerate(sorted(assets, key=lambda a: a["name"])):
                asset_path = f"{directory}/assets/{index}{asset['suffix']}"
                write_physical_file(asset["binary"], asset_path)
                db.add(MaterialAsset(material_id=material.id, name=asset["name"], file_path=asset_path,
                                     sha256=asset["sha256"], file_type=asset["mime"]))
            db.add(QuizPublication(paper_id=paper.id, class_id=cid, material_id=material.id,
                                   content_sha256=fingerprint))
        record_event(db, actor_id=teacher.id, subject=teacher.subject, target_type="paper",
                     target_id=paper.id, action="publish",
                     detail={"classes": classes, "material_ids": material_ids})
        db.commit()
    except Exception:
        db.rollback()
        from routers.research_materials import clean_created_directory
        for directory in paths:
            clean_created_directory(directory)
        raise HTTPException(status_code=500, detail="发布失败，已清理")
    return {"message": "试卷已发布", "material_ids": material_ids, "class_ids": classes}


def _collect_assets(db: Session, items: list[dict], used_names: set[str]) -> list[dict]:
    """从题目快照的 assets 清单里取出正文实际使用的原图，并核对指纹。"""
    from citation_service import file_sha256
    result = []
    seen = set()
    for it in items:
        for asset in it["snapshot"].get("assets", []):
            name = asset.get("name")
            if name not in used_names or name in seen:
                continue
            seen.add(name)
            stored, mime = asset.get("path"), asset.get("mime")
            if not stored:
                # 早期题目快照没有存储路径：回到原资料的配图清单查找
                source = db.get(ResearchMaterial, asset.get("source_id"))
                original = next((a for a in json.loads(source.assets_json or "[]")
                                 if a["name"] == asset.get("source_name")), None) if source else None
                if original is None:
                    raise HTTPException(status_code=409, detail=f"配图 {name} 缺失或已变化")
                stored, mime = original["path"], original.get("mime")
            path = resolve_abs_path(stored)
            if not path.is_file() or file_sha256(path) != asset["sha256"]:
                raise HTTPException(status_code=409, detail=f"配图 {name} 缺失或指纹不一致")
            suffix = Path(name).suffix.lower()
            result.append({"name": name, "binary": path.read_bytes(), "sha256": asset["sha256"],
                           "mime": mime or mimetypes.guess_type(name)[0] or "application/octet-stream",
                           "suffix": suffix})
    return result


@router.get("/papers/{paper_id}/answer-key", summary="下载答案卷", responses={404: {"description": "不存在"}})
def answer_key(paper_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    paper = owned_paper(db, paper_id, teacher)
    markdown = render_answer_key({"title": paper.title, "duration": paper.duration}, _paper_items(db, paper))
    filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", paper.title)[:140] + "（答案卷）.md"
    from urllib.parse import quote
    disposition = f"attachment; filename=answer-key.md; filename*=UTF-8''{quote(filename)}"
    return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": disposition})


# ---------------------------------------------------------------------------
# 命题审计（tasks 6.2）
# ---------------------------------------------------------------------------


@router.get("/events", summary="本人命题操作记录")
def list_events(limit: int = Query(100, ge=1, le=500),
                current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher = current_teacher(db, current)
    rows = db.query(QuestionEvent).filter_by(actor_id=teacher.id).order_by(
        QuestionEvent.created_at.desc()).limit(limit).all()
    return {"items": [
        dict(id=e.id, subject=e.subject, target_type=e.target_type, target_id=e.target_id,
             action=e.action, detail=json.loads(e.detail_json or "{}"), created_at=_iso(e.created_at))
        for e in rows
    ]}
