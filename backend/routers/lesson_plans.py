"""智能备课：教师私有教案定稿，再审核发布两种学生文稿。"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from chunk_service import chunk_text
from config import settings
from database import get_db
from deps import CurrentUser, get_current_teacher
from embedding_service import embed_text
from knowledge_tags import knowledge_tags
from lesson_service import (TEACHER_PROMPT, STUDENT_PROMPT, build_resources, context_text,
                            parse_student_output, validate_student, validate_teacher, normalize_image_links)
from llm_service import LLMGenerationError, stream_chat
from material_service import resolve_abs_path, run_indexing, write_physical_file
from models import Class, LessonPlan, LessonPlanVersion, LessonPublication, LessonGroupPublication, Material, MaterialAsset, ResearchMaterial, ResearchChunk, Role, User
from rag_search_service import serialize_vector
from research_service import IMAGE, digest, safe_name
from routers.research_materials import asset_response, clean_created_directory, source_record
from services import write_audit_log

router = APIRouter(prefix='/api/teacher/lesson-plans', tags=['lesson-plans'])
active_generations: set[int] = set()


class GenerateRequest(BaseModel):
    class_id: int
    topic: str = Field(min_length=1, max_length=160)
    duration: int = Field(default=45, ge=10, le=180)
    scope: str = Field(default='', max_length=2000)
    curriculum_standards: str = Field(default='', max_length=3000)
    class_profile: str = Field(default='', max_length=2000)
    requirements: str = Field(default='', max_length=3000)
    research_material_ids: list[int] = Field(min_length=1, max_length=5)


class RevisionRequest(BaseModel):
    revision: int = Field(ge=1)


class EditRequest(RevisionRequest):
    content: str = Field(min_length=1, max_length=100000)


class ReviewRequest(RevisionRequest):
    reviewed: bool = False


class StudentEditRequest(RevisionRequest):
    student_lesson: str = Field(min_length=1, max_length=100000)
    student_handout: str = Field(min_length=1, max_length=100000)


class SectionRequest(RevisionRequest):
    heading: str = Field(min_length=1, max_length=300)
    instructions: str = Field(default='', max_length=2000)


class PublishRequest(ReviewRequest):
    kind: Literal['lesson', 'handout']
    class_ids: list[int] = Field(min_length=1, max_length=30)


def actor(db, current, class_ids=()):
    teacher = db.get(User, current.user_id, populate_existing=True)
    if not teacher or teacher.role != Role.teacher or teacher.subject not in SUBJECT_NAMES:
        raise HTTPException(403, '仅已分配学科的教师可备课')
    allowed = json.loads(teacher.teaching_classes or '[]')
    if any(cid not in allowed for cid in class_ids):
        raise HTTPException(403, '只能操作本人当前任教班级的教案')
    if any(db.get(Class, cid) is None for cid in class_ids):
        raise HTTPException(400, '班级不存在')
    return teacher, allowed


def owned(db, plan_id, current):
    plan = db.get(LessonPlan, plan_id, populate_existing=True)
    if not plan:
        raise HTTPException(404, '教案不存在')
    teacher, _ = actor(db, current, [plan.class_id])
    if plan.teacher_id != teacher.id or plan.subject != teacher.subject:
        raise HTTPException(403, '只能访问本人本学科的教案')
    return plan


def sources_current(db, resources, current):
    sources = []
    for sid in resources['source_ids']:
        source = source_record(db, sid, current)
        if source.source_sha256 != resources['source_hashes'][str(sid)]:
            raise HTTPException(409, '教师资料版本已变化，请重新备课')
        sources.append(source)
    return sources


def checked_assets(db, resources, content, current):
    sources = {s.id: s for s in sources_current(db, resources, current)}
    catalog = {a['name']: a for a in resources['assets']}
    result = {}
    for _, target in IMAGE.findall(content):
        name = safe_name(target.strip())
        if name not in catalog:
            raise HTTPException(400, '文稿含未选入资料的配图')
        entry = catalog[name]
        original = next((a for a in json.loads(sources[entry['source_id']].assets_json)
                         if a['name'] == entry['source_name']), None)
        if not original or original['sha256'] != entry['sha256']:
            raise HTTPException(409, '原图版本已变化，请重新备课')
        path = resolve_abs_path(original['path'])
        if not path.is_file():
            raise HTTPException(409, '原图缺失，请重新导入资料')
        binary = path.read_bytes()
        if digest(binary) != original['sha256']:
            raise HTTPException(409, '原图版本已变化，请重新导入资料')
        result[name] = (original, binary)
    return result


def serialize(plan, db, detail=True):
    def stamp(value):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    result = dict(id=plan.id, title=plan.title, class_id=plan.class_id,
                  class_name=db.get(Class, plan.class_id).name, subject=plan.subject,
                  duration=plan.duration, status=plan.status, current_version=plan.current_version,
                  revision=plan.revision, updated_at=stamp(plan.updated_at), created_at=stamp(plan.created_at))
    if detail:
        result.update(content=plan.content, requirements=json.loads(plan.requirements_json),
                      resources=json.loads(plan.resources_json), student_lesson=plan.student_lesson,
                      student_handout=plan.student_handout, student_from_version=plan.student_from_version)
        result['versions'] = [dict(version=v.version, content=v.content, resources=json.loads(v.resources_json),
                                   created_at=stamp(v.created_at)) for v in db.query(LessonPlanVersion).filter_by(
                                       lesson_plan_id=plan.id).order_by(LessonPlanVersion.version.desc()).all()]
        result['publications'] = [dict(id=p.id, version=p.version, kind=p.kind, class_id=p.class_id,
                                      class_name=db.get(Class, p.class_id).name, material_id=p.material_id,
                                      created_at=stamp(p.created_at)) for p in db.query(LessonPublication).filter_by(
                                          lesson_plan_id=plan.id).order_by(LessonPublication.id.desc()).all()]
        result['group_publications'] = [dict(version=p.version, research_material_id=p.research_material_id,
                                            created_at=stamp(p.created_at)) for p in db.query(LessonGroupPublication).filter_by(
                                                lesson_plan_id=plan.id).order_by(LessonGroupPublication.version.desc()).all()]
    return result


def change(db, plan, revision, **values):
    values.update(revision=revision + 1, updated_at=datetime.now(timezone.utc))
    count = db.query(LessonPlan).filter_by(id=plan.id, revision=revision).update(values, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(409, '教案已在其他窗口更新，请重新加载后操作')
    db.expire_all()
    return db.get(LessonPlan, plan.id)


def audit(db, current, plan, request):
    write_audit_log(db, user_id=current.user_id, role='teacher', subject=plan.subject,
                    class_id=plan.class_id, request_path=request.url.path, method=request.method,
                    status_code=200, ip_address=request.client.host if request.client else None)


def event(kind, **data):
    return 'data: ' + json.dumps({'type': kind, **data}, ensure_ascii=False, default=str) + '\n\n'


def start_generation(current):
    if not settings.deepseek_api_key:
        raise HTTPException(503, 'AI 服务尚未配置，请配置 DeepSeek 后重试；已填写内容会保留')
    if current.user_id in active_generations:
        raise HTTPException(409, '已有备课任务正在生成，请等待完成')
    active_generations.add(current.user_id)


async def collect(messages, request, deltas=True):
    content = ''
    async with asyncio.timeout(180):
        async for delta in stream_chat(messages, timeout=90, temperature=0.2):
            if await request.is_disconnected():
                raise asyncio.CancelledError()
            content += delta
            if len(content) > 100000:
                raise ValueError('生成内容过长，请缩小范围后重试')
            yield delta if deltas else ''


@router.get('')
def list_plans(class_id: int | None = Query(default=None), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher, allowed = actor(db, current, [] if class_id is None else [class_id])
    query = db.query(LessonPlan).filter(LessonPlan.teacher_id == teacher.id, LessonPlan.subject == teacher.subject,
                                       LessonPlan.class_id.in_(allowed))
    if class_id is not None:
        query = query.filter_by(class_id=class_id)
    return {'items': [serialize(p, db, False) for p in query.order_by(LessonPlan.updated_at.desc()).all()]}


@router.post('/generate')
def generate(body: GenerateRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    teacher, _ = actor(db, current, [body.class_id])
    if not body.topic.strip():
        raise HTTPException(400, '请填写课题')
    sources = [source_record(db, sid, current) for sid in dict.fromkeys(body.research_material_ids)]
    try:
        resources = build_resources(sources, body.topic, body.scope)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    requirements = body.model_dump()
    requirements['class_name'] = db.get(Class, body.class_id).name
    requirements['subject_name'] = SUBJECT_NAMES[teacher.subject]
    original_subject = teacher.subject
    messages = [{'role': 'system', 'content': TEACHER_PROMPT},
                {'role': 'user', 'content': json.dumps(requirements, ensure_ascii=False) + '\n\n教师资料片段：\n' + context_text(resources)}]
    start_generation(current)

    async def stream():
        try:
            yield event('context', resources=resources)
            content = ''
            async for delta in collect(messages, request):
                content += delta
                yield event('delta', text=delta)
            content = normalize_image_links(content)
            validate_teacher(content, resources)
            if len(content) < 200 or not all(term in content for term in ['教学目标', '重难点', '教学过程']):
                raise ValueError('AI 返回的教案不完整，请重试')
            db.expire_all()
            live_teacher, _ = actor(db, current, [body.class_id])
            if live_teacher.subject != original_subject:
                raise HTTPException(403, '生成期间学科身份已变化，请重新发起')
            sources_current(db, resources, current)
            plan = LessonPlan(teacher_id=current.user_id, subject=live_teacher.subject, class_id=body.class_id,
                              title=body.topic.strip(), duration=body.duration, requirements_json=json.dumps(requirements, ensure_ascii=False),
                              resources_json=json.dumps(resources, ensure_ascii=False), content=content,
                              status='draft', current_version=0, revision=1, student_lesson='', student_handout='')
            db.add(plan); db.commit(); db.refresh(plan)
            audit(db, current, plan, request)
            yield event('done', plan=serialize(plan, db))
        except (LLMGenerationError, TimeoutError):
            db.rollback()
            yield event('error', message='AI 生成失败或超时，请稍后重试；本次未保存教案，表单仍保留')
        except (ValueError, HTTPException) as exc:
            db.rollback()
            yield event('error', message=exc.detail if isinstance(exc, HTTPException) else str(exc))
        finally:
            active_generations.discard(current.user_id)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.get('/{plan_id}')
def read_plan(plan_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return serialize(owned(db, plan_id, current), db)


@router.put('/{plan_id}')
def edit_plan(plan_id: int, body: EditRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status == 'final':
        raise HTTPException(409, '请先开始新修订，再修改定稿')
    try:
        content = normalize_image_links(body.content)
        validate_teacher(content, json.loads(plan.resources_json))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    plan = change(db, plan, body.revision, content=content, status='draft', student_lesson='', student_handout='', student_from_version=None)
    db.commit(); audit(db, current, plan, request)
    return serialize(plan, db)


@router.post('/{plan_id}/review')
def review_plan(plan_id: int, body: ReviewRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status != 'draft' or not body.reviewed:
        raise HTTPException(400, '请先核对草稿的内容、公式、例题和引用并确认审阅')
    plan = change(db, plan, body.revision, status='reviewed')
    db.commit(); audit(db, current, plan, request)
    return serialize(plan, db)


@router.post('/{plan_id}/regenerate-section')
def regenerate_section(plan_id: int, body: SectionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status == 'final' or plan.revision != body.revision:
        raise HTTPException(409, '请先保存当前草稿，定稿须先开始新修订')
    matches = list(re.finditer(r'(?m)^##\s+[^\n]+', plan.content))
    selected = [(i, m) for i, m in enumerate(matches) if m[0].strip() == body.heading.strip()]
    if len(selected) != 1:
        raise HTTPException(400, '请选择草稿中唯一的二级章节标题')
    index, match = selected[0]
    end = matches[index + 1].start() if index + 1 < len(matches) else len(plan.content)
    before, after = plan.content[:match.start()], plan.content[end:]
    resources = json.loads(plan.resources_json)
    sources_current(db, resources, current)
    messages = [{'role': 'system', 'content': TEACHER_PROMPT + '\n本次只重写一个章节。只输出指定的原二级标题及该章节正文，不输出整篇教案或其他二级章节。'},
                {'role': 'user', 'content': '教学要求：' + plan.requirements_json + '\n完整现稿：\n' + plan.content +
                 '\n指定章节：' + body.heading + '\n重写要求：' + body.instructions + '\n教师资料：\n' + context_text(resources)}]
    start_generation(current)
    async def stream():
        try:
            replacement = ''
            yield event('progress', message='正在重写所选章节…')
            async for delta in collect(messages, request):
                replacement += delta
                yield event('progress', message='正在重写所选章节…')
            replacement = normalize_image_links(replacement.strip())
            headings = re.findall(r'(?m)^##\s+[^\n]+', replacement)
            if headings != [body.heading.strip()] or not replacement.startswith(body.heading.strip() + '\n'):
                raise ValueError('AI 返回的章节边界不正确，原草稿保留，请重试')
            content = before + replacement + '\n\n' + after
            validate_teacher(content, resources)
            db.expire_all()
            live = owned(db, plan_id, current)
            sources_current(db, resources, current)
            live = change(db, live, body.revision, content=content, status='draft', student_lesson='', student_handout='', student_from_version=None)
            db.commit(); audit(db, current, live, request)
            yield event('done', plan=serialize(live, db))
        except (LLMGenerationError, TimeoutError):
            db.rollback()
            yield event('error', message='章节重写失败或超时，原草稿保留，请重试')
        except (ValueError, HTTPException) as exc:
            db.rollback()
            yield event('error', message=exc.detail if isinstance(exc, HTTPException) else str(exc))
        finally:
            active_generations.discard(current.user_id)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.post('/{plan_id}/finalize')
def finalize_plan(plan_id: int, body: RevisionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status != 'reviewed':
        raise HTTPException(400, '请先审阅教案再定稿')
    version = plan.current_version + 1
    plan = change(db, plan, body.revision, status='final', current_version=version)
    db.add(LessonPlanVersion(lesson_plan_id=plan.id, version=version, content=plan.content, resources_json=plan.resources_json))
    db.commit(); audit(db, current, plan, request)
    return serialize(plan, db)


@router.post('/{plan_id}/revise')
def revise_plan(plan_id: int, body: RevisionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status != 'final':
        raise HTTPException(400, '当前已经是可编辑草稿')
    plan = change(db, plan, body.revision, status='draft', student_lesson='', student_handout='', student_from_version=None)
    db.commit(); audit(db, current, plan, request)
    return serialize(plan, db)


@router.get('/{plan_id}/assets')
def plan_asset(plan_id: int, name: str = Query(...), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    resources = json.loads(plan.resources_json)
    entry = next((a for a in resources['assets'] if a['name'] == name), None)
    if not entry:
        raise HTTPException(404, '配图不存在')
    source = next(s for s in sources_current(db, resources, current) if s.id == entry['source_id'])
    asset = next((a for a in json.loads(source.assets_json) if a['name'] == entry['source_name']), None)
    if not asset or asset['sha256'] != entry['sha256']:
        raise HTTPException(409, '原图版本已变化')
    return asset_response(asset['path'], asset['sha256'], asset['mime'])


@router.post('/{plan_id}/student-drafts')
def generate_students(plan_id: int, body: RevisionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status != 'final' or plan.revision != body.revision:
        raise HTTPException(409, '请先保存并定稿当前教案，再生成学生稿')
    resources = json.loads(plan.resources_json)
    sources_current(db, resources, current)
    messages = [{'role': 'system', 'content': STUDENT_PROMPT}, {'role': 'user', 'content':
                '教师最终定稿：\n' + plan.content + '\n\n原始资料（仅供核对题干和图）：\n' + context_text(resources)}]
    start_generation(current)
    async def stream():
        try:
            yield event('progress', message='正在从定稿生成学生可见教案与配套讲义…')
            raw = ''
            async for delta in collect(messages, request):
                raw += delta
                yield event('progress', message='正在整理两份学生稿并检查答案标记…')
            result = parse_student_output(raw, resources)
            db.expire_all()
            live = owned(db, plan_id, current)
            sources_current(db, resources, current)
            checked_assets(db, resources, '\n'.join(result.values()), current)
            live = change(db, live, body.revision, **result, student_from_version=live.current_version)
            db.commit(); audit(db, current, live, request)
            yield event('done', plan=serialize(live, db))
        except (LLMGenerationError, TimeoutError):
            db.rollback()
            yield event('error', message='学生稿生成失败或超时，已保存的教案及原有学生稿不受影响，请重试')
        except (ValueError, HTTPException) as exc:
            db.rollback()
            yield event('error', message=exc.detail if isinstance(exc, HTTPException) else str(exc))
        finally:
            active_generations.discard(current.user_id)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.put('/{plan_id}/student-drafts')
def edit_students(plan_id: int, body: StudentEditRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.status != 'final' or plan.student_from_version != plan.current_version:
        raise HTTPException(409, '请先从当前定稿生成学生稿')
    resources = json.loads(plan.resources_json)
    try:
        student_lesson = normalize_image_links(body.student_lesson)
        student_handout = normalize_image_links(body.student_handout)
        validate_student(student_lesson, resources); validate_student(student_handout, resources)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    checked_assets(db, resources, student_lesson + '\n' + student_handout, current)
    plan = change(db, plan, body.revision, student_lesson=student_lesson, student_handout=student_handout)
    db.commit(); audit(db, current, plan, request)
    return serialize(plan, db)


@router.post('/{plan_id}/publish')
def publish_plan(plan_id: int, body: PublishRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    classes = list(dict.fromkeys(body.class_ids))
    actor(db, current, classes)
    if plan.revision != body.revision or plan.status != 'final' or plan.student_from_version != plan.current_version:
        raise HTTPException(409, '教案或学生稿已更新，请重新加载并核对')
    if not body.reviewed:
        raise HTTPException(400, '请确认学生稿不含答案和教师提示后再发布')
    content = plan.student_lesson if body.kind == 'lesson' else plan.student_handout
    resources = json.loads(plan.resources_json)
    try:
        content = normalize_image_links(content)
        validate_student(content, resources)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    assets = checked_assets(db, resources, content, current)
    binary = content.encode('utf-8'); fingerprint = digest(binary)
    label = '学生可见教案' if body.kind == 'lesson' else '学生讲义'
    filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', plan.title)[:140] + f'（{label}·v{plan.current_version}）.md'
    tags = [SUBJECT_NAMES[plan.subject], *knowledge_tags(filename, content, plan.subject), label, '学生版']
    paths, ids = [], []
    try:
        # 先执行乐观锁，防止不同窗口发布期间修改学生稿；重复提交复用已有发布记录。
        plan = change(db, plan, body.revision)
        for cid in classes:
            previous = db.query(LessonPublication).filter_by(lesson_plan_id=plan.id, version=plan.current_version,
                kind=body.kind, class_id=cid, content_sha256=fingerprint).one_or_none()
            if previous:
                ids.append(previous.material_id)
                continue
            directory = f'{cid}/lesson-{uuid.uuid4().hex}'
            paths.append(directory)
            path = f'{directory}/student.md'; write_physical_file(binary, path)
            material = Material(class_id=cid, uploader_id=current.user_id, filename=filename, file_path=path,
                                file_type='text/markdown', file_size=len(binary), description=f'{SUBJECT_NAMES[plan.subject]} · {label}',
                                tags=json.dumps(tags, ensure_ascii=False))
            db.add(material); db.flush(); ids.append(material.id)
            for index, (name, (original, image)) in enumerate(sorted(assets.items())):
                asset_path = f'{directory}/assets/{index}{Path(original["path"]).suffix.lower()}'
                write_physical_file(image, asset_path)
                db.add(MaterialAsset(material_id=material.id, name=name, file_path=asset_path,
                                     sha256=original['sha256'], file_type=original['mime']))
            db.add(LessonPublication(lesson_plan_id=plan.id, version=plan.current_version, kind=body.kind,
                                    class_id=cid, material_id=material.id, content_sha256=fingerprint))
        db.commit()
    except Exception:
        db.rollback()
        for directory in paths:
            clean_created_directory(directory)
        raise
    for mid in ids:
        if not db.get(Material, mid).is_indexed:
            run_indexing(db, mid)
    audit(db, current, plan, request)
    return {'plan': serialize(plan, db), 'material_ids': ids,
            'indexed': [bool(db.get(Material, mid).is_indexed) for mid in ids],
            'message': f'{label}已发布到所选班级；相同版本内容不会重复创建'}


@router.post('/{plan_id}/share-to-group')
def share_to_group(plan_id: int, body: RevisionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.revision != body.revision or plan.status != 'final':
        raise HTTPException(409, '请先完成当前教案的审阅与定稿，再发布到教研组')
    existing = db.query(LessonGroupPublication).filter_by(lesson_plan_id=plan.id, version=plan.current_version).one_or_none()
    if existing:
        return {'plan': serialize(plan, db), 'research_material_id': existing.research_material_id,
                'message': '该定稿版本已发布到教研组，不会重复创建'}
    snapshot = db.query(LessonPlanVersion).filter_by(lesson_plan_id=plan.id, version=plan.current_version).one_or_none()
    if not snapshot or snapshot.content != plan.content:
        raise HTTPException(409, '定稿快照不一致，请重新加载教案')
    resources = json.loads(snapshot.resources_json)
    try:
        content = normalize_image_links(snapshot.content)
        validate_teacher(content, resources)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    assets = checked_assets(db, resources, content, current)
    directory = f'research/{plan.subject}/lesson-{uuid.uuid4().hex}'
    try:
        plan = change(db, plan, body.revision)
        binary = content.encode('utf-8')
        path = f'{directory}/source.md'
        write_physical_file(binary, path)
        written_assets = []
        for index, (name, (original, image)) in enumerate(sorted(assets.items())):
            asset_path = f'{directory}/assets/{index}{Path(original["path"]).suffix.lower()}'
            write_physical_file(image, asset_path)
            written_assets.append(dict(name=name, path=asset_path, sha256=original['sha256'], mime=original['mime']))
        filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', plan.title)[:140] + f'（教师教案·v{plan.current_version}）.md'
        shared = ResearchMaterial(subject=plan.subject, uploader_id=current.user_id, filename=filename,
                                  file_path=path, source_sha256=digest(binary), content=content,
                                  assets_json=json.dumps(written_assets, ensure_ascii=False))
        db.add(shared); db.flush()
        for index, chunk in enumerate(chunk_text(content), 1):
            db.add(ResearchChunk(research_material_id=shared.id, subject=plan.subject, chunk_index=index,
                                 content=chunk, embedding=serialize_vector(embed_text(chunk))))
        db.add(LessonGroupPublication(lesson_plan_id=plan.id, teacher_id=current.user_id, version=plan.current_version,
                                      research_material_id=shared.id, resources_json=snapshot.resources_json))
        db.commit()
    except Exception:
        db.rollback(); clean_created_directory(directory)
        raise
    audit(db, current, plan, request)
    return {'plan': serialize(plan, db), 'research_material_id': shared.id,
            'message': f'教师完整教案 v{plan.current_version} 已发布到{SUBJECT_NAMES[plan.subject]}教研组，仅同学科教师可见'}


@router.delete('/{plan_id}')
def delete_plan(plan_id: int, body: RevisionRequest, request: Request, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    plan = owned(db, plan_id, current)
    if plan.revision != body.revision:
        raise HTTPException(409, '教案已更新，请重新加载')
    # 已发布学生资料独立保留，删除私人教案不删除班级学习资料。
    plan = change(db, plan, body.revision)
    db.query(LessonPublication).filter_by(lesson_plan_id=plan.id).delete(synchronize_session=False)
    db.query(LessonGroupPublication).filter_by(lesson_plan_id=plan.id).update({'lesson_plan_id': None}, synchronize_session=False)
    db.query(LessonPlanVersion).filter_by(lesson_plan_id=plan.id).delete(synchronize_session=False)
    db.delete(plan); db.commit(); audit(db, current, plan, request)
    return {'message': '教案及定稿历史已删除，已发布班级资料和教研组共享稿保留'}
