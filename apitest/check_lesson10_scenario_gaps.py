"""第10课：scenario-coverage.md 中「待补断言」场景的离线补例（不依赖网络与模型）。

覆盖 12 条此前无对应断言的场景：上传大小/存储目录/同名重命名/DB 回滚删文件/
解析失败保持未索引/删除会话清理消息/技能文件格式错误/文档默认关闭/MCP 地址允许清单/
下架后组卷/手工替换下架题/H4 空历史与时间边界。
全部使用临时库、合成账号、纯函数或故障注入；断言值而非形状。
"""

import asyncio
import io
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


def run(folder: Path):
    os.environ["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["MCP_TOOLS_HEALTH_URL"] = ""
    os.environ["ENABLE_DOCS"] = "false"
    os.environ["DATABASE_URL"] = f"sqlite:///{folder / 'gaps.db'}"
    os.environ["UPLOAD_DIR"] = str(folder / "uploads")
    sys.path.insert(0, str(ROOT / "backend"))

    from fastapi import BackgroundTasks, HTTPException, UploadFile
    from fastapi.testclient import TestClient

    import material_service
    import routers.materials as materials_router
    from config import Settings
    from database import Base, SessionLocal, engine
    from deps import CurrentUser
    from main import app
    from material_service import (
        MAX_FILE_SIZE,
        build_relative_path,
        delete_physical_file,
        resolve_abs_path,
        run_indexing,
        validate_upload_file,
        write_physical_file,
    )
    from mcp_crypto import validate_base_url
    from models import (
        Class,
        Conversation,
        Homework,
        HomeworkSubmission,
        Material,
        MaterialContent,
        Message,
        QuestionItem,
        QuestionPaper,
        QuestionPaperItem,
        Role,
        User,
    )
    from security import create_access_token
    from skill_service import SkillParseError, parse_skill_file

    Base.metadata.create_all(engine)
    headers = {}
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="补例一班"), Class(id=102, name="补例二班"), Class(id=103, name="补例三班")])
        db.flush()
        for uid, role, cid, subject, tc in [
            (1, Role.teacher, None, "math", [101]),
            (2, Role.student, 101, None, None),
            (3, Role.student, 102, None, None),
            (4, Role.student, 103, None, None),
        ]:
            db.add(User(id=uid, identifier=f"gaps-{uid}", role=role, name="合成用户", class_id=cid,
                        subject=subject, teaching_classes=json.dumps(tc) if tc else None,
                        password_hash="unused", must_change_password=False))
            headers[uid] = {"Authorization": "Bearer " + create_access_token(
                user_id=uid, role=role.value, class_id=cid, subject=subject,
                teaching_classes=tc, must_change_password=False)}
        db.commit()

    # ---- 上传大小上限 ------------------------------------------------------
    check("上传超大文件被拒：上限为 50MB", MAX_FILE_SIZE == 50 * 1024 * 1024 and Settings().max_file_size_mb == 50)
    try:
        validate_upload_file(b"\0" * (MAX_FILE_SIZE + 1), "huge.md")
        oversize_rejected = ""
    except ValueError as exc:
        oversize_rejected = str(exc)
    check("上传超大文件被拒：超限文件在写盘前被拒并给出中文原因", "超过上限" in oversize_rejected)

    # ---- 存储目录 ----------------------------------------------------------
    rel = build_relative_path(101, "note.md")
    written = write_physical_file(b"# synthetic material", rel)
    upload_root = Path(os.environ["UPLOAD_DIR"]).resolve()
    check("文件存储在挂载目录：按班级子目录写入 UPLOAD_DIR", written.exists()
          and written.parent == upload_root / "101" and written.read_bytes() == b"# synthetic material")
    delete_physical_file(rel)
    check("文件存储在挂载目录：删除物理文件后磁盘不再保留", not written.exists())

    # ---- 同名重命名 --------------------------------------------------------
    real_time = material_service.time
    material_service.time = types.SimpleNamespace(time=lambda: 1700000000)
    try:
        first = build_relative_path(101, "same.md")
        write_physical_file(b"first", first)
        second = build_relative_path(101, "same.md")
    finally:
        material_service.time = real_time
    check("同名文件自动重命名：同秒同名文件追加计数器不覆盖",
          first == "101/1700000000_same.md" and second == "101/1700000000_1_same.md"
          and resolve_abs_path(first).exists())
    delete_physical_file(first)

    # ---- DB 写入失败回滚删物理文件 ----------------------------------------
    class FailingDb:
        def __init__(self):
            self.rolled = False

        def add(self, obj):
            pass

        def commit(self):
            raise RuntimeError("synthetic commit failure")

        def rollback(self):
            self.rolled = True

        def refresh(self, obj):
            pass

    real_build = materials_router.build_relative_path
    materials_router.build_relative_path = lambda class_id, filename: "101/rollback.md"
    fake_db = FailingDb()
    teacher_ctx = CurrentUser(user_id=1, role=Role.teacher.value, class_id=None,
                              must_change_password=False, teaching_classes=[101], subject="math")
    upload_file = UploadFile(filename="rollback.md", file=io.BytesIO(b"rollback content"))
    try:
        asyncio.run(materials_router.upload_material(
            background=BackgroundTasks(), file=upload_file, class_id=101,
            description="", tags="", current=teacher_ctx, db=fake_db))
        rollback_error = None
    except HTTPException as exc:
        rollback_error = exc
    finally:
        materials_router.build_relative_path = real_build
    check("DB 写入失败时回滚删除物理文件：返回 500、数据库回滚且磁盘文件已清理",
          rollback_error is not None and rollback_error.status_code == 500
          and "已清理物理文件" in str(rollback_error.detail)
          and fake_db.rolled and not resolve_abs_path("101/rollback.md").exists())

    # ---- 解析失败保持未索引 ------------------------------------------------
    with SessionLocal() as db:
        material = Material(class_id=101, uploader_id=1, filename="missing.md",
                            file_path="101/missing.md", file_type="text/markdown",
                            file_size=10, is_indexed=False)
        db.add(material)
        db.commit()
        material_id = material.id
        run_indexing(db, material_id)
        db.expire_all()
        stored = db.get(Material, material_id)
        content = db.query(MaterialContent).filter_by(material_id=material_id).one()
        check("解析失败的材料保持未索引：is_indexed 为 False 且 parse_error 落库",
              stored.is_indexed is False and stored.source_sha256 is None
              and "无法读取" in (content.parse_error or ""))

    # ---- 删除会话并清理消息 ------------------------------------------------
    with SessionLocal() as db:
        convo = Conversation(student_id=2, class_id=101, title="待删除会话", subject="math")
        db.add(convo)
        db.flush()
        convo_id = convo.id
        db.add_all([Message(conversation_id=convo_id, role="user", content="合成问题"),
                    Message(conversation_id=convo_id, role="assistant", content="合成回答")])
        other = Conversation(student_id=3, class_id=102, title="他人会话", subject="math")
        db.add(other)
        db.flush()
        other_id = other.id
        db.commit()
    with TestClient(app) as client:
        response = client.delete(f"/api/student/conversations/{convo_id}", headers=headers[2])
        with SessionLocal() as db:
            messages_left = db.query(Message).filter_by(conversation_id=convo_id).count()
            convo_gone = db.get(Conversation, convo_id) is None
        check("删除会话并清理消息：会话与其全部消息一并删除",
              response.status_code == 200 and response.json() == {"ok": True}
              and convo_gone and messages_left == 0)
        foreign = client.delete(f"/api/student/conversations/{other_id}", headers=headers[2])
        with SessionLocal() as db:
            other_alive = db.get(Conversation, other_id) is not None
        check("删除会话并清理消息：他人或跨班会话按不存在处理且数据保留",
              foreign.status_code == 404 and other_alive)

        # ---- 技能文件格式错误 ---------------------------------------------
        bad_sources = {
            "缺少分隔空行": "名称：合成技能",
            "未知字段": "名称：合成技能\n未知字段：x\n适用条件：合成\n工具：\n启用：true\n\n说明",
            "缺少必填字段": "名称：合成技能\n适用条件：合成\n\n说明",
        }
        parser_errors = {}
        for label, source in bad_sources.items():
            try:
                parse_skill_file(source)
                parser_errors[label] = ""
            except SkillParseError as exc:
                parser_errors[label] = str(exc)
        endpoint = client.post("/api/teacher/skills", headers=headers[1],
                               json={"class_id": 101, "source": bad_sources["未知字段"]})
        check("技能文件格式错误：缺分隔空行、未知字段、缺必填均解析失败且接口返回 400",
              all(parser_errors.values()) and "空行" in parser_errors["缺少分隔空行"]
              and "未知字段" in parser_errors["未知字段"]
              and "缺少必填字段" in parser_errors["缺少必填字段"]
              and endpoint.status_code == 400 and "未知字段" in endpoint.json()["detail"])

    # ---- 文档默认关闭 ------------------------------------------------------
    main_source = (ROOT / "backend/main.py").read_text(encoding="utf-8")
    check("默认关闭文档：代码默认值为关闭，/docs 与 /openapi.json 随之不暴露",
          Settings.model_fields["enable_docs"].default is False
          and 'docs_url="/docs" if _docs_enabled else None' in main_source
          and 'openapi_url="/openapi.json" if _docs_enabled else None' in main_source)

    # ---- MCP 地址允许清单 --------------------------------------------------
    rejected = {}
    for url in ("http://evil.example.com:8090", "http://127.0.0.1:8090",
                "http://localhost:8090", "http://169.254.169.254"):
        try:
            validate_base_url(url)
            rejected[url] = ""
        except ValueError as exc:
            rejected[url] = str(exc)
    check("不在允许清单的地址：清单外主机、回环、本机与元数据地址均被拒",
          "允许清单" in rejected["http://evil.example.com:8090"]
          and "回环" in rejected["http://127.0.0.1:8090"]
          and "本机" in rejected["http://localhost:8090"]
          and "内网" in rejected["http://169.254.169.254"])
    check("不在允许清单的地址：清单内地址归一化后通过",
          validate_base_url("http://mcp-tools:8090/") == "http://mcp-tools:8090")

    # ---- 下架后组卷 --------------------------------------------------------
    with SessionLocal() as db:
        archived = QuestionItem(subject="math", author_id=1, type="single_choice", difficulty="easy",
                                knowledge_points_json=json.dumps(["空间向量"]),
                                stem="合成的下架选择题", options_json=json.dumps(["1", "2", "3", "4"]),
                                answer_json=json.dumps(["A"]), explanation="合成", status="approved",
                                archived=True, stem_key="a" * 64, content_sha256="b" * 64)
        db.add(archived)
        db.commit()
        archived_id = archived.id
    blueprint = {"title": "下架题组卷", "duration": 45, "knowledge_points": ["空间向量"],
                 "difficulty_pct": {"easy": 100, "medium": 0, "hard": 0},
                 "groups": [{"type": "single_choice", "count": 1, "score": 5}]}
    with TestClient(app) as client:
        compose = client.post("/api/teacher/quiz/papers", headers=headers[1], json=blueprint)
        with SessionLocal() as db:
            papers = db.query(QuestionPaper).count()
        gaps = (compose.json().get("detail") or {}).get("gaps") or []
        check("下架后组卷：下架题不进入新试卷且返回缺口、不创建试卷",
              compose.status_code == 422 and papers == 0
              and gaps == [{"type": "single_choice", "difficulty": "easy", "needed": 1, "available": 0}])

        # ---- 手工替换为下架题 ---------------------------------------------
        with SessionLocal() as db:
            paper = QuestionPaper(teacher_id=1, subject="math", title="草稿试卷", duration=45,
                                  blueprint_json="{}", status="draft", revision=1)
            db.add(paper)
            db.commit()
            paper_id = paper.id
        replace = client.put(f"/api/teacher/quiz/papers/{paper_id}", headers=headers[1],
                             json={"revision": 1, "items": [{"question_item_id": archived_id, "score": 5}]})
        with SessionLocal() as db:
            kept = db.get(QuestionPaper, paper_id)
            item_count = db.query(QuestionPaperItem).filter_by(paper_id=paper_id).count()
            state = (kept.revision, item_count)
        check("手工替换为下架题：返回 400 且草稿题数与版本不变",
              replace.status_code == 400 and "已下架" in replace.json()["detail"]
              and state == (1, 0))

        # ---- H4 空历史与时间边界 ------------------------------------------
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            overdue = Homework(class_id=101, teacher_id=1, subject="math", title="逾期未交",
                               content_json='{"stem":"合成题面"}', grading_snapshot_json="{}",
                               source_type="quiz", status="published", due_at=now - timedelta(hours=1))
            upcoming = Homework(class_id=101, teacher_id=1, subject="math", title="未截止",
                                content_json='{"stem":"合成题面"}', grading_snapshot_json="{}",
                                source_type="quiz", status="published", due_at=now + timedelta(days=1))
            closed = Homework(class_id=101, teacher_id=1, subject="math", title="关闭未提交",
                              content_json='{"stem":"合成题面"}', grading_snapshot_json="{}",
                              source_type="quiz", status="closed", due_at=now - timedelta(hours=2))
            submitted = Homework(class_id=101, teacher_id=1, subject="math", title="关闭已提交",
                                 content_json='{"stem":"合成题面"}', grading_snapshot_json="{}",
                                 source_type="quiz", status="closed", due_at=now - timedelta(hours=3))
            db.add_all([overdue, upcoming, closed, submitted])
            db.flush()
            db.add(HomeworkSubmission(class_id=101, student_id=2, homework_id=submitted.id,
                                      answer_text="合成作答", submitted_at=now - timedelta(hours=4),
                                      status="ai_graded"))
            db.commit()
        rows = client.get("/api/student/homeworks", headers=headers[2]).json()
        by_title = {row["title"]: row for row in rows}
        empty_room = client.get("/api/student/homeworks", headers=headers[4]).json()
        check("H4 空历史与时间边界：无历史学生返回空列表，逾期未交在历史且标记已截止",
              empty_room == [] and set(by_title) == {"逾期未交", "未截止", "关闭已提交"}
              and by_title["逾期未交"]["submission_id"] is None
              and by_title["逾期未交"]["homework_status"] == "published"
              and by_title["逾期未交"]["due_at"] < now.isoformat()
              and by_title["未截止"]["submission_id"] is None
              and by_title["关闭已提交"]["submission_id"] is not None)
    student_page = (ROOT / "frontend/app/student/page.tsx").read_text(encoding="utf-8")
    check("H4 空历史与时间边界：学生页历史分页有明确空状态",
          "暂无作业历史" in student_page and 'assignmentTab === "history"' in student_page)

    engine.dispose()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="scenario-gaps-", ignore_cleanup_errors=True) as folder:
        run(Path(folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
