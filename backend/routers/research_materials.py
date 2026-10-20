"""教研组教师资料库：先入组内，再预览学生版、选择任教班级发布。"""
import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_service import SUBJECT_NAMES
from chunk_service import chunk_text
from database import get_db
from deps import CurrentUser, get_current_teacher, get_current_user
from embedding_service import embed_text
from knowledge_tags import knowledge_tags
from material_service import resolve_abs_path, get_upload_root, run_indexing, write_physical_file, MAX_FILE_SIZE
from models import Class, Material, MaterialAsset, MaterialPublication, ResearchChunk, ResearchMaterial, LessonGroupPublication, User
from rag_search_service import serialize_vector
from research_service import IMAGE, digest, safe_name, student_draft, unpack_markdown, validate_student_text
from routers.materials import _check_material_access

router = APIRouter(tags=['research-materials'])


def clean_created_directory(relative):
    root = get_upload_root().resolve()
    target = resolve_abs_path(relative).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError('拒绝清理上传目录外的路径')
    shutil.rmtree(target, ignore_errors=True)


def group_subject(current):
    if current.subject not in SUBJECT_NAMES:
        raise HTTPException(403, '请先分配任教学科')
    return current.subject


def source_record(db, material_id, current):
    subject = group_subject(current)
    material = db.get(ResearchMaterial, material_id)
    if material is None:
        raise HTTPException(404, '组内资料不存在')
    if material.subject != subject:
        raise HTTPException(403, '无权访问其他学科组资料')
    if not resolve_abs_path(material.file_path).is_file() or digest(resolve_abs_path(material.file_path).read_bytes()) != material.source_sha256:
        raise HTTPException(409, '教师原文件已变化或丢失，请重新导入资料')
    return material


def item(material, db, detail=False):
    author = db.get(User, material.uploader_id)
    publication = db.query(LessonGroupPublication).filter_by(research_material_id=material.id).one_or_none()
    result = dict(id=material.id, filename=material.filename, subject=material.subject,
                  uploader_name=author.name if author else '', created_at=material.created_at,
                  asset_count=len(json.loads(material.assets_json)),
                  chunk_count=db.query(ResearchChunk).filter_by(research_material_id=material.id).count())
    result.update(kind='lesson-plan' if publication else 'source',
                  lesson_version=publication.version if publication else None)
    if detail:
        result['content'] = material.content
        result['publications'] = [dict(material_id=p.material_id, class_id=p.class_id,
                                      class_name=db.get(Class, p.class_id).name, created_at=p.created_at)
                                  for p in db.query(MaterialPublication).filter_by(research_material_id=material.id).all()]
        result['lesson_sources'] = json.loads(publication.resources_json)['references'] if publication else []
    return result


@router.get('/api/teacher/research-materials')
def list_sources(current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    subject = group_subject(current)
    materials = db.query(ResearchMaterial).filter_by(subject=subject).order_by(ResearchMaterial.id.desc()).all()
    return {'items': [item(m, db) for m in materials]}


@router.post('/api/teacher/research-materials')
async def import_source(file: UploadFile = File(...), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    subject = group_subject(current)
    data = await file.read(MAX_FILE_SIZE + 1)
    try:
        filename, raw, content, assets = unpack_markdown(data, file.filename or '')
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    source_hash = digest(raw)
    existing = db.query(ResearchMaterial).filter_by(subject=subject, source_sha256=source_hash).all()
    expected_assets = {name: digest(binary) for name, (binary, _) in assets.items()}
    for previous in existing:
        if {a['name']: a['sha256'] for a in json.loads(previous.assets_json)} == expected_assets:
            return {**item(previous, db, True), 'message': '同一版本已在组内资料库中'}
    directory = f'research/{subject}/{uuid.uuid4().hex}'
    source_path = f'{directory}/source.md'
    written_assets = []
    try:
        write_physical_file(raw, source_path)
        for index, (name, (binary, mime)) in enumerate(assets.items()):
            path = f'{directory}/assets/{index}{Path(name).suffix.lower()}'
            write_physical_file(binary, path)
            written_assets.append(dict(name=name, path=path, sha256=digest(binary), mime=mime))
        material = ResearchMaterial(subject=subject, uploader_id=current.user_id, filename=filename,
                                    file_path=source_path, source_sha256=source_hash, content=content,
                                    assets_json=json.dumps(written_assets, ensure_ascii=False))
        db.add(material)
        db.flush()
        for index, chunk in enumerate(chunk_text(content), 1):
            db.add(ResearchChunk(research_material_id=material.id, subject=subject, chunk_index=index,
                                 content=chunk, embedding=serialize_vector(embed_text(chunk))))
        db.commit()
    except Exception:
        db.rollback()
        # 唯一创建的组内目录，绝不触及别的资料。
        clean_created_directory(directory)
        raise
    return {**item(material, db, True), 'message': '教师版已导入组内，尚未向班级发布'}


@router.get('/api/teacher/research-materials/{material_id}')
def read_source(material_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    return item(source_record(db, material_id, current), db, True)


def asset_response(path, sha, mime):
    absolute = resolve_abs_path(path)
    if not absolute.is_file():
        raise HTTPException(404, '配图不存在')
    if digest(absolute.read_bytes()) != sha:
        raise HTTPException(409, '配图版本已变化')
    return FileResponse(absolute, media_type=mime, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.get('/api/teacher/research-materials/{material_id}/assets')
def source_asset(material_id: int, name: str = Query(...), current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    source = source_record(db, material_id, current)
    asset = next((a for a in json.loads(source.assets_json) if a['name'] == name), None)
    if asset is None:
        raise HTTPException(404, '配图不存在')
    return asset_response(asset['path'], asset['sha256'], asset['mime'])


@router.get('/api/teacher/research-materials/{material_id}/bundle')
def source_bundle(material_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    source = source_record(db, material_id, current)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        original = resolve_abs_path(source.file_path).read_bytes()
        if digest(original) != source.source_sha256:
            raise HTTPException(409, '教师文件版本已变化')
        z.writestr(source.filename, original)
        for asset in json.loads(source.assets_json):
            path = resolve_abs_path(asset['path'])
            if not path.is_file():
                raise HTTPException(409, '配图缺失或版本已变化')
            binary = path.read_bytes()
            if digest(binary) != asset['sha256']:
                raise HTTPException(409, '配图缺失或版本已变化')
            z.writestr(asset['name'], binary)
    out.seek(0)
    return StreamingResponse(out, media_type='application/zip', headers={'Cache-Control': 'private, no-store'})


@router.post('/api/teacher/research-materials/{material_id}/student-preview')
def preview_student(material_id: int, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    source = source_record(db, material_id, current)
    if db.query(LessonGroupPublication).filter_by(research_material_id=source.id).first():
        raise HTTPException(422, '这是共享教师教案，请在智能备课中选用它，定稿后生成配套学生稿')
    try:
        content = student_draft(source.content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {'content': content, 'message': '已提取知识点与题干，发布前请人工核对答案和图片内容'}


class PublishRequest(BaseModel):
    class_ids: list[int] = Field(min_length=1, max_length=30)
    content: str = Field(min_length=1, max_length=2 * 1024 * 1024)
    reviewed: bool = False


@router.post('/api/teacher/research-materials/{material_id}/publish')
def publish_student(material_id: int, body: PublishRequest, current: CurrentUser = Depends(get_current_teacher), db: Session = Depends(get_db)):
    source = source_record(db, material_id, current)
    if db.query(LessonGroupPublication).filter_by(research_material_id=source.id).first():
        raise HTTPException(400, '共享教师教案不能直接发布给学生，请在智能备课中生成并核对学生稿')
    teacher = db.get(User, current.user_id)
    allowed = json.loads(teacher.teaching_classes or '[]')
    class_ids = list(dict.fromkeys(body.class_ids))
    if any(cid not in allowed for cid in class_ids):
        raise HTTPException(403, '只能发布到本人任教班级')
    if not body.reviewed:
        raise HTTPException(400, '请先核对学生版不含答案解析并确认发布')
    if any(db.get(Class, cid) is None for cid in class_ids):
        raise HTTPException(400, '目标班级不存在')
    try:
        validate_student_text(body.content)
        used = {safe_name(target.strip()) for _, target in IMAGE.findall(body.content)}
        assets = {a['name']: a for a in json.loads(source.assets_json)}
        if not used.issubset(assets):
            raise ValueError('学生版引用了未导入的配图')
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    for name in used:
        a = assets[name]
        if not resolve_abs_path(a['path']).is_file() or digest(resolve_abs_path(a['path']).read_bytes()) != a['sha256']:
            raise HTTPException(409, '配图缺失或版本已变化，请重新导入')
    content = body.content.encode('utf-8')
    filename = Path(source.filename).stem[:235] + '（学生版）.md'
    tags = [SUBJECT_NAMES[source.subject], *knowledge_tags(filename, body.content, source.subject), '学生版']
    paths, material_ids = [], []
    try:
        for cid in class_ids:
            directory = f'{cid}/published-{uuid.uuid4().hex}'
            path = f'{directory}/student.md'
            paths.append(directory)
            write_physical_file(content, path)
            material = Material(class_id=cid, uploader_id=current.user_id, filename=filename,
                                file_path=path, file_type='text/markdown', file_size=len(content),
                                description=f'{SUBJECT_NAMES[source.subject]} · 学生版讲义', tags=json.dumps(tags, ensure_ascii=False))
            db.add(material)
            db.flush()
            material_ids.append(material.id)
            for index, name in enumerate(sorted(used)):
                a = assets[name]
                asset_path = f'{directory}/assets/{index}{Path(name).suffix.lower()}'
                write_physical_file(resolve_abs_path(a['path']).read_bytes(), asset_path)
                db.add(MaterialAsset(material_id=material.id, name=name, file_path=asset_path, sha256=a['sha256'], file_type=a['mime']))
            db.add(MaterialPublication(research_material_id=source.id, material_id=material.id, teacher_id=current.user_id, class_id=cid))
        db.commit()
    except Exception:
        db.rollback()
        for directory in paths:
            clean_created_directory(directory)
        raise
    # 索引仅针对学生正文；教师版本始终留在独立组内表。
    for mid in material_ids:
        run_indexing(db, mid)
    return {'material_ids': material_ids, 'class_ids': class_ids,
            'indexed': [bool(db.get(Material, mid).is_indexed) for mid in material_ids],
            'message': '学生版已发布，教师版保留在教研组资料库'}


@router.get('/api/materials/{material_id}/assets')
def published_asset(material_id: int, name: str = Query(...), current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_material_access(db.get(Material, material_id), current)
    asset = db.query(MaterialAsset).filter_by(material_id=material_id, name=name).one_or_none()
    if asset is None:
        raise HTTPException(404, '配图不存在')
    return asset_response(asset.file_path, asset.sha256, asset.file_type)


@router.get('/api/materials/{material_id}/bundle')
def published_bundle(material_id: int, current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    _check_material_access(material, current)
    if material.file_type != 'text/markdown':
        raise HTTPException(400, '该资料不是 Markdown 图文讲义')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(material.filename, resolve_abs_path(material.file_path).read_bytes())
        for asset in db.query(MaterialAsset).filter_by(material_id=material_id).all():
            absolute = resolve_abs_path(asset.file_path)
            if not absolute.is_file() or digest(absolute.read_bytes()) != asset.sha256:
                raise HTTPException(409, '配图缺失或版本不一致')
            z.writestr(asset.name, absolute.read_bytes())
    out.seek(0)
    return StreamingResponse(out, media_type='application/zip', headers={'Cache-Control': 'private, no-store'})
