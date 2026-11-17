"""定稿试卷 → 班级作业；快照、幂等发布与文件/数据库整批回滚。"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import mimetypes
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from homework_service import HomeworkServiceError, UserContext
from material_service import resolve_abs_path, write_physical_file
from models import Homework, HomeworkAsset, QuestionEvent, QuestionPaper, QuestionPaperItem, ResearchMaterial
from question_service import IMAGE, ordered_items, render_student_paper, safe_name, validate_student_paper

logger = logging.getLogger(__name__)
# 进程内串行化短发布事务；数据库唯一索引仍是跨进程的最终约束。
_publication_lock = threading.RLock()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _owned_paper(db: Session, ctx: UserContext, paper_id: int) -> QuestionPaper:
    paper = db.get(QuestionPaper, paper_id)
    if paper is None or paper.teacher_id != ctx.user_id or paper.subject != ctx.subject:
        raise HomeworkServiceError(404, "试卷不存在")
    return paper


def _snapshot(db: Session, paper: QuestionPaper) -> tuple[str, dict, list[dict], str]:
    rows = db.query(QuestionPaperItem).filter_by(paper_id=paper.id).order_by(
        QuestionPaperItem.position, QuestionPaperItem.id).all()
    items = ordered_items([{"score": float(row.score), "snapshot": json.loads(row.snapshot_json)} for row in rows])
    total = sum(item["score"] for item in items)
    if not items or not math.isfinite(total) or total <= 0:
        raise HomeworkServiceError(409, "试卷缺少有效题目或分值，请检查后重新定稿")
    markdown = render_student_paper({"title": paper.title, "duration": paper.duration}, items)
    used = {safe_name(match.group(2).strip()) for match in IMAGE.finditer(markdown)}
    assets: dict[str, dict] = {}
    questions = []
    for number, item in enumerate(items, 1):
        source = item["snapshot"]
        questions.append({"number": number, "score": item["score"], **{
            key: source.get(key) for key in ("type", "stem", "options", "answer", "explanation")}})
        for asset in source.get("assets", []):
            name = safe_name(asset["name"])
            if name not in used:
                continue
            previous = assets.get(name)
            if previous and previous["sha256"] != asset["sha256"]:
                raise HomeworkServiceError(409, "试卷配图存在冲突，请重新核对")
            assets[name] = dict(asset, name=name)
    if set(assets) != used:
        raise HomeworkServiceError(409, "试卷配图缺失，请重新核对")
    try:
        validate_student_paper(markdown, sorted(assets))
    except ValueError:
        raise HomeworkServiceError(400, "学生卷内容或链接不符合要求，请重新核对") from None
    grading = {"title": paper.title, "total_score": total, "questions": questions}
    fingerprint = hashlib.sha256(json.dumps({"student": markdown, "grading": grading,
        "assets": [{"name": name, "sha256": assets[name]["sha256"]} for name in sorted(assets)]},
        ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return markdown, grading, [assets[name] for name in sorted(assets)], fingerprint


def _read_source_asset(db: Session, asset: dict) -> tuple[bytes, str]:
    stored = asset.get("path")
    mime = asset.get("mime")
    if not stored:
        source = db.get(ResearchMaterial, asset.get("source_id"))
        original = next((entry for entry in json.loads(source.assets_json or "[]")
                         if entry["name"] == asset.get("source_name")), None) if source else None
        if original:
            stored, mime = original["path"], original.get("mime")
    if not stored:
        raise HomeworkServiceError(409, "试卷配图缺失或已变化")
    root = resolve_abs_path(".").resolve()
    path = resolve_abs_path(stored).resolve()
    if not path.is_relative_to(root):
        raise HomeworkServiceError(409, "试卷配图路径不合法")
    try:
        content = path.read_bytes()
    except OSError:
        raise HomeworkServiceError(409, "试卷配图缺失或已变化") from None
    if hashlib.sha256(content).hexdigest() != asset["sha256"]:
        raise HomeworkServiceError(409, "试卷配图指纹不一致，请重新核对")
    return content, mime or mimetypes.guess_type(asset["name"])[0] or "application/octet-stream"


def _existing(db: Session, paper_id: int, classes: list[int], fingerprint: str, due_at: datetime) -> dict[int, int]:
    rows = db.query(Homework).filter(Homework.source_paper_id == paper_id,
        Homework.class_id.in_(classes), Homework.source_fingerprint == fingerprint).all()
    for row in rows:
        if row.status == "closed" or _utc(row.due_at) != _utc(due_at):
            raise HomeworkServiceError(409, "该试卷已布置，请复制试卷开始新一轮作业")
    return {row.class_id: row.id for row in rows}


def _result(classes: list[int], assignments: dict[int, int]) -> dict:
    return {"message": "试卷已发布为作业", "class_ids": classes,
            "homework_ids": [assignments[cid] for cid in classes],
            "assignments": [{"class_id": cid, "homework_id": assignments[cid]} for cid in classes]}


def _cleanup(paths: list[Path]) -> None:
    root = resolve_abs_path(".").resolve()
    for path in paths:
        if path.resolve().is_relative_to(root) and path != root:
            try:
                shutil.rmtree(path)
            except FileNotFoundError:
                pass
            except OSError:
                logger.error("作业发布回滚文件清理失败")


def publish_quiz_homework(db: Session, ctx: UserContext, paper_id: int, revision: int,
                          reviewed: bool, class_ids: list[int], due_at: datetime) -> dict:
    with _publication_lock:
        paper = _owned_paper(db, ctx, paper_id)
        if paper.status != "final":
            raise HomeworkServiceError(409, "请先定稿试卷再发布")
        if not reviewed:
            raise HomeworkServiceError(400, "请确认学生卷不含答案后再发布")
        classes = list(dict.fromkeys(class_ids))
        if any(cid not in (ctx.teaching_classes or []) for cid in classes):
            raise HomeworkServiceError(403, "只能发布到本人任教班级")
        if _utc(due_at) <= datetime.now(timezone.utc):
            raise HomeworkServiceError(400, "截止时间必须晚于当前时间")
        markdown, grading, assets, fingerprint = _snapshot(db, paper)
        assignments = _existing(db, paper_id, classes, fingerprint, due_at)
        if len(assignments) == len(classes):
            return _result(classes, assignments)
        if paper.revision != revision:
            raise HomeworkServiceError(409, "试卷已更新，请刷新后重新发布")
        binaries = [_read_source_asset(db, asset) for asset in assets]
        paths: list[Path] = []
        source_revision = paper.revision
        try:
            changed = db.query(QuestionPaper).filter_by(id=paper_id, teacher_id=ctx.user_id,
                subject=ctx.subject, revision=revision, status="final").update(
                    {"revision": revision + 1, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
            if changed != 1:
                raise HomeworkServiceError(409, "试卷已更新，请刷新后重新发布")
            for cid in classes:
                if cid in assignments:
                    continue
                directory = f"{cid}/homework-{uuid.uuid4().hex}"
                root = resolve_abs_path(".").resolve()
                target = resolve_abs_path(directory).resolve()
                if not target.is_relative_to(root):
                    raise HomeworkServiceError(500, "作业文件保存失败")
                if assets:
                    target.mkdir(parents=True, exist_ok=False)
                    paths.append(target)
                hw = Homework(class_id=cid, subject=ctx.subject, teacher_id=ctx.user_id,
                    title=paper.title, content_json=json.dumps({"stem": markdown, "format": "markdown",
                        "original_total": grading["total_score"]}, ensure_ascii=False),
                    status="published", due_at=_utc(due_at), source_type="quiz", source_paper_id=paper_id,
                    source_paper_revision=source_revision, source_fingerprint=fingerprint,
                    grading_snapshot_json=json.dumps(grading, ensure_ascii=False))
                db.add(hw)
                db.flush()
                assignments[cid] = hw.id
                for index, (asset, (content, mime)) in enumerate(zip(assets, binaries)):
                    stored = f"{directory}/assets/{index}{Path(asset['name']).suffix.lower()}"
                    write_physical_file(content, stored)
                    db.add(HomeworkAsset(homework_id=hw.id, class_id=cid, teacher_id=ctx.user_id,
                        name=asset["name"], file_path=stored, sha256=asset["sha256"], file_type=mime))
            db.add(QuestionEvent(actor_id=ctx.user_id, subject=ctx.subject, target_type="paper",
                target_id=paper_id, action="publish", detail_json=json.dumps({"classes": classes,
                    "homework_ids": [assignments[cid] for cid in classes]})))
            result = _result(classes, assignments)
            db.commit()
            return result
        except (IntegrityError, OperationalError):
            db.rollback()
            _cleanup(paths)
            # 竞争者可能已提交相同批次；仍按唯一记录和截止时间核对。
            existing = _existing(db, paper_id, classes, fingerprint, due_at)
            if len(existing) == len(classes):
                return _result(classes, existing)
            raise HomeworkServiceError(409, "发布状态已变化，请刷新后重试") from None
        except Exception as exc:
            db.rollback()
            _cleanup(paths)
            if isinstance(exc, HomeworkServiceError):
                raise
            logger.error("命题作业发布失败，已回滚")
            raise HomeworkServiceError(500, "发布失败，本次作业未保存，请重试") from None
