"""错题本回归：列表、详情、掌握标记、AI 讲解、越权与失败路径（add-mistake-notebook）。

每条检查名前的 S 编号对应 mistake-notebook 规约中的场景。
临时数据库、假模型返回固定讲解文本，不连外网。

用法（项目根）：make check，或
  JWT_SECRET_KEY=<至少 32 字符> PYTHONPATH=backend backend/.venv/bin/python apitest/check_mistake.py
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


with tempfile.TemporaryDirectory(prefix="mistake-test-", ignore_cleanup_errors=True) as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'mistake.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")

    from fastapi.testclient import TestClient

    import main
    from database import Base, SessionLocal, engine
    from models import Class, Homework, MistakeNote, Role, User
    from security import create_access_token, hash_password

    Base.metadata.create_all(engine)
    db = SessionLocal()
    db.add(Class(id=101, name="一班"))
    db.add(Class(id=102, name="二班"))

    teacher = User(
        role=Role.teacher, identifier="TEA001", password_hash=hash_password("Teach@2026"),
        name="张老师", class_id=None, subject="math", must_change_password=False,
    )
    db.add(teacher)
    db.flush()
    teacher.teaching_classes = "[102]"

    student = User(
        role=Role.student, identifier="20260002", password_hash=hash_password("thu260002"),
        name="王芳", class_id=102, must_change_password=False,
    )
    other_student = User(
        role=Role.student, identifier="20260001", password_hash=hash_password("thu260001"),
        name="李明", class_id=101, must_change_password=False,
    )
    db.add(student)
    db.add(other_student)
    db.flush()

    # 一道作业，用于关联错题
    hw = Homework(
        class_id=102, teacher_id=teacher.id, subject="math",
        title="一元二次方程练习", content_json='{"stem": "解方程 x²-5x+6=0"}',
        status="published", due_at=datetime.now(timezone.utc),
    )
    db.add(hw)
    db.flush()

    # 直接插入两条错题（王芳的），一条数学一条物理；李明一条数学
    note1 = MistakeNote(
        class_id=102, student_id=student.id, subject="math", homework_id=hw.id,
        question_stem="解方程 x²-5x+6=0", student_answer="x=1", reason="计算错误",
    )
    note2 = MistakeNote(
        class_id=102, student_id=student.id, subject="physics", homework_id=None,
        question_stem="求匀加速位移", student_answer="s=vt", reason="漏了 1/2at²",
    )
    note_other = MistakeNote(
        class_id=101, student_id=other_student.id, subject="math", homework_id=None,
        question_stem="他人错题", student_answer="ans", reason="错因",
    )
    db.add(note1)
    db.add(note2)
    db.add(note_other)
    db.commit()

    note1_id = note1.id
    note2_id = note2.id
    note_other_id = note_other.id

    student_token = create_access_token(
        user_id=student.id, role="student", class_id=102, must_change_password=False,
    )
    other_student_token = create_access_token(
        user_id=other_student.id, role="student", class_id=101, must_change_password=False,
    )
    db.close()

    # 假模型：返回固定讲解文本
    import mistake_service

    original_generate = mistake_service.generate_answer

    def fake_generate(question, context_block, *, system_prompt=None, tutor_enabled=False):
        return "错因：因式分解错误。思路：先移项再用求根公式。知识点：一元二次方程。"

    mistake_service.generate_answer = fake_generate

    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            sh = {"Authorization": f"Bearer {student_token}"}
            oh = {"Authorization": f"Bearer {other_student_token}"}

            # ---------- 列表 ----------
            r = client.get("/api/student/mistakes", headers=sh)
            check("S1 正常：本人错题列表返回 2 条", r.status_code == 200 and len(r.json()) == 2)

            r = client.get("/api/student/mistakes?subject=math", headers=sh)
            check("S1 正常：学科过滤 math 返回 1 条", r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["subject"] == "math")

            r = client.get("/api/student/mistakes?subject=math&only_unmastered=true", headers=sh)
            check("S1 正常：仅未掌握 math 返回 1 条", r.status_code == 200 and len(r.json()) == 1)

            r = client.get("/api/student/mistakes", headers=oh)
            check("S1 正常：李明只看到自己 1 条", r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["question_stem"] == "他人错题")

            # ---------- 详情 ----------
            r = client.get(f"/api/student/mistakes/{note1_id}", headers=sh)
            body = r.json()
            check("S1 正常：本人错题详情正确", r.status_code == 200 and body["question_stem"] == "解方程 x²-5x+6=0" and body["homework_title"] == "一元二次方程练习")

            r = client.get(f"/api/student/mistakes/{note_other_id}", headers=sh)
            check("S1 失败：查看他人错题 → 403", r.status_code == 403)

            r = client.get("/api/student/mistakes/99999", headers=sh)
            check("S2 失败：错题不存在 → 404", r.status_code == 404)

            # ---------- 掌握标记 ----------
            r = client.put(f"/api/student/mistakes/{note1_id}/mastered", headers=sh, json={"mastered": True})
            body = r.json()
            check("S1 正常：标记已掌握 mastered=True", r.status_code == 200 and body["mastered"] is True and body["mastered_at"] is not None)

            r = client.get("/api/student/mistakes?only_unmastered=true", headers=sh)
            check("S1 正常：仅未掌握过滤后剩 1 条", r.status_code == 200 and len(r.json()) == 1)

            r = client.put(f"/api/student/mistakes/{note1_id}/mastered", headers=sh, json={"mastered": False})
            body = r.json()
            check("S1 正常：取消掌握 mastered=False", r.status_code == 200 and body["mastered"] is False and body["mastered_at"] is None)

            r = client.put(f"/api/student/mistakes/{note_other_id}/mastered", headers=sh, json={"mastered": True})
            check("S3 失败：标记他人错题 → 403", r.status_code == 403)

            # ---------- AI 讲解 ----------
            r = client.post(f"/api/student/mistakes/{note1_id}/explain", headers=sh)
            body = r.json()
            check("S1 正常：AI 讲解返回文本", r.status_code == 200 and body["available"] is True and "错因" in (body["explanation"] or ""))

            r = client.post(f"/api/student/mistakes/{note_other_id}/explain", headers=sh)
            check("S3 失败：讲解他人错题 → 403", r.status_code == 403)

            # AI 未配置降级
            mistake_service.generate_answer = lambda *a, **k: None
            r = client.post(f"/api/student/mistakes/{note1_id}/explain", headers=sh)
            body = r.json()
            check("S2 失败：AI 未配置返回 available=False", r.status_code == 200 and body["available"] is False and body["explanation"] is None)
            mistake_service.generate_answer = fake_generate

            # ---------- 数据隔离：请求参数 student_id 被忽略 ----------
            r = client.get("/api/student/mistakes?student_id=999", headers=sh)
            check("S4 正常：请求参数 student_id 被忽略，仍只返回本人错题", r.status_code == 200 and len(r.json()) == 2)

    finally:
        mistake_service.generate_answer = original_generate
        engine.dispose()

passed = sum(1 for _, ok in checks if ok)
print(f"\n结果：{passed}/{len(checks)} 通过")
sys.exit(0 if passed == len(checks) else 1)
