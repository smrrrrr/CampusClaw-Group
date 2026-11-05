"""作业历史与终评错题同步：临时库、合成账号，无真实模型调用。"""
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["MCP_TOOLS_HEALTH_URL"] = ""
checks = []


def check(name, passed):
    assert passed, name
    checks.append(name)


with tempfile.TemporaryDirectory(prefix="assignment-history-", ignore_cleanup_errors=True) as folder:
    db_path = Path(folder) / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["UPLOAD_DIR"] = str(Path(folder) / "uploads")
    from fastapi.testclient import TestClient
    from sqlalchemy import event
    from sqlalchemy.exc import SQLAlchemyError
    from database import Base, SessionLocal, engine
    from main import app
    from models import AuditLog, Class, Homework, HomeworkAsset, HomeworkSubmission, MistakeNote, Role, User
    from security import create_access_token
    from material_service import write_physical_file, resolve_abs_path

    Base.metadata.create_all(engine)
    headers = {}
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="合成一班"), Class(id=102, name="合成二班")]); db.flush()
        for uid, role, cid, subject, tc in [(1, Role.teacher, None, "math", [101]), (2, Role.student, 101, None, None),
                                           (3, Role.student, 101, None, None), (4, Role.student, 102, None, None),
                                           (5, Role.teacher, None, "physics", [101]), (6, Role.teacher, None, "math", [102])]:
            db.add(User(id=uid, identifier=f"history-{uid}", role=role, name="合成用户", class_id=cid,
                        subject=subject, teaching_classes=json.dumps(tc) if tc else None,
                        password_hash="unused", must_change_password=False))
            headers[uid] = {"Authorization": "Bearer " + create_access_token(user_id=uid, role=role.value,
                class_id=cid, subject=subject, teaching_classes=tc, must_change_password=False)}
        db.commit()
    with TestClient(app) as client:
        def req(method, path, who=1, **kwargs):
            return client.request(method, path, headers=headers.get(who, {}), **kwargs)
        def make_hw(title, state="published", cid=101, subject="math"):
            with SessionLocal() as db:
                hw = Homework(class_id=cid, teacher_id=1, subject=subject, title=title,
                    content_json='{"stem":"公开题面"}', grading_snapshot_json='{"private":"PRIVATE_HISTORY_RUBRIC"}',
                    source_type="quiz", status=state, due_at=datetime.now(timezone.utc)+timedelta(days=1))
                db.add(hw); db.flush(); ident = hw.id; db.commit(); return ident
        def submit(hw, who=2):
            response = req("POST", f"/api/student/homeworks/{hw}/submit", who, json={"answer_text": "本人合成答案"})
            assert response.status_code == 200, response.text
            return response.json()["id"]
        def grade(sub, score, who=1):
            return req("PUT", f"/api/teacher/submissions/{sub}/grade", who, json={"score": score, "feedback": "教师终评反馈"})
        def note_count(hw, student=2):
            with SessionLocal() as db:return db.query(MistakeNote).filter_by(homework_id=hw, student_id=student).count()

        hw = make_hw("历史样例")
        sub = submit(hw)
        first = req("GET", "/api/student/homeworks", 2)
        item = next(row for row in first.json() if row["id"] == hw)
        check("H1 正常：提交后历史输入与时间持久返回", item["submission_id"] == sub and item["answer_text"] == "本人合成答案"
              and item["submitted_at"] and not item["graded"] and "PRIVATE_HISTORY_RUBRIC" not in first.text)
        check("H1 正常：重复读取记录不消失", req("GET", "/api/student/homeworks", 2).json() == first.json())
        check("M1 正常：首次100分不入错题", grade(sub, 100).status_code == 200 and note_count(hw) == 0)
        for score, expected in [(59, 1), (60, 0), (59, 1), (99, 0), (59, 1), (100, 0), (59, 1)]:
            check(f"M2 边界：改为{score}分后错题{expected}条", grade(sub, score).status_code == 200 and note_count(hw) == expected)

        def fail_delete(conn, cursor, statement, parameters, context, many):
            if statement.startswith("DELETE FROM mistake_notes"):
                raise SQLAlchemyError("PRIVATE_SQL_AND_PATH")
        event.listen(engine, "before_cursor_execute", fail_delete)
        try:
            failed = grade(sub, 100)
            check("M4 失败：派生清理失败返回503且无内部信息", failed.status_code == 503 and "PRIVATE_SQL_AND_PATH" not in failed.text)
        finally:
            event.remove(engine, "before_cursor_execute", fail_delete)
        with SessionLocal() as db:
            check("M4 失败：教师分和错题整批回滚", db.get(HomeworkSubmission, sub).teacher_score == 59 and note_count(hw) == 1)
        for who, status in [(None, 401), (5, 403), (6, 403), (3, 403)]:
            check(f"M4 失败：{who}不能越权改分", grade(sub, 100, who).status_code == status and note_count(hw) == 1)
        grade(sub, 100)

        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jV3sAAAAASUVORK5CYII=")
        write_physical_file(png, "history/fig.png")
        with SessionLocal() as db:
            db.add(HomeworkAsset(homework_id=hw, class_id=101, teacher_id=1, name="fig.png", file_path="history/fig.png",
                                 sha256=hashlib.sha256(png).hexdigest(), file_type="image/png")); db.commit()
        check("H2 正常：教师关闭作业", req("PUT", f"/api/teacher/homeworks/{hw}/close").status_code == 200)
        closed = next(row for row in req("GET", "/api/student/homeworks", 2).json() if row["id"] == hw)
        check("H2 正常：关闭后保留100分作答与评语", closed["homework_status"] == "closed" and closed["graded"]
              and closed["final_score"] == 100 and closed["answer_text"] == "本人合成答案" and closed["feedback"] == "教师终评反馈")
        check("H2 正常：关闭后本人可读配图和提交", req("GET", f"/api/student/homeworks/{hw}/assets?name=fig.png", 2).content == png
              and req("GET", f"/api/student/submissions/{sub}", 2).json()["final_score"] == 100)
        check("H2 失败：关闭后不可重交", req("POST", f"/api/student/homeworks/{hw}/submit", 2, json={"answer_text": "新内容"}).status_code == 400)
        draft = make_hw("不应见草稿", "draft"); other = make_hw("他班", cid=102)
        for who in (2, 3):
            rows = req("GET", "/api/student/homeworks", who).json()
            check(f"H3 失败：{who}列表不泄露草稿他班或他人关闭历史", all(r["id"] not in (draft, other) for r in rows)
                  and (any(r["id"] == hw for r in rows) if who == 2 else all(r["id"] != hw for r in rows)))
        for who, status in [(None, 401), (3, 403), (4, 403)]:
            response = req("GET", f"/api/student/homeworks/{hw}/assets?name=fig.png", who)
            check(f"H3 失败：{who}不能读取他人关闭配图", response.status_code == status and response.content != png)
        check("H3 失败：他人提交不可读", req("GET", f"/api/student/submissions/{sub}", 3).status_code == 403)
        for name, status in [("../bad.png", 400), ("unknown.png", 404)]:
            check(f"H3 失败：关闭配图名{name}", req("GET", f"/api/student/homeworks/{hw}/assets", 2, params={"name": name}).status_code == status)
        path = resolve_abs_path("history/fig.png"); path.write_bytes(b"bad")
        check("H3 失败：关闭配图损坏409", req("GET", f"/api/student/homeworks/{hw}/assets?name=fig.png", 2).status_code == 409)
        path.write_bytes(png)
        def fail_history(conn, cursor, statement, parameters, context, many):
            if "FROM homeworks LEFT OUTER JOIN homework_submissions" in statement:
                raise SQLAlchemyError("PRIVATE_DB_FAILURE")
        event.listen(engine, "before_cursor_execute", fail_history)
        try:
            response = req("GET", "/api/student/homeworks", 2)
            check("H3 失败：历史依赖故障503", response.status_code == 503 and "PRIVATE_DB_FAILURE" not in response.text)
        finally: event.remove(engine, "before_cursor_execute", fail_history)

        # 合成旧残留：只有完全匹配的及格终评允许修复。
        low_hw = make_hw("仍低分"); low_sub = submit(low_hw); grade(low_sub, 59)
        pending_hw = make_hw("尚未终评"); submit(pending_hw)
        with SessionLocal() as db:
            for homework_id, cid, subject in [(hw, 101, "math"), (hw, 102, "math"), (pending_hw, 101, "math"), (None, 101, "math")]:
                db.add(MistakeNote(class_id=cid, student_id=2, subject=subject, homework_id=homework_id,
                                   question_stem="合成旧错题", student_answer="合成作答", reason="旧记录"))
            db.commit()
        def fingerprint():
            with sqlite3.connect(db_path) as conn:
                return {table: conn.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
                        for table in ("users", "homeworks", "homework_submissions", "homework_assets")}
        before = fingerprint()
        def repair(apply=False):
            command = [sys.executable, str(ROOT / "scripts/repair_resolved_mistakes.py"), "--database", str(db_path)]
            if apply: command.append("--apply")
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout.strip())
        preview = repair()
        check("M3 正常：dry-run只匹配1条且不删除", preview["matched_count"] == 1 and preview["removed_count"] == 0 and note_count(hw) == 2)
        applied = repair(True); again = repair(True)
        check("M3 正常：备份后修复且重复执行0条", applied["removed_count"] == 1 and again["removed_count"] == 0
              and (db_path.parent / applied["backup"]).exists() and fingerprint() == before and path.read_bytes() == png)
        check("M3 边界：低分未终评无来源不匹配记录保留", note_count(low_hw) == 1 and note_count(pending_hw) == 1 and note_count(hw) == 1)
    engine.dispose()
print(json.dumps({"passed": len(checks), "checks": checks}, ensure_ascii=False))
