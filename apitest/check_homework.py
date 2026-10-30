"""作业批改回归：布置、提交、AI 初批、教师改分、错题收录、越权与失败路径（add-homework-grading）。

每条检查名前的 S 编号对应 homework 规约中的场景。
临时数据库、假模型返回固定 JSON，不连外网。

用法（项目根）：make check，或
  JWT_SECRET_KEY=<至少 32 字符> PYTHONPATH=backend backend/.venv/bin/python apitest/check_homework.py
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


with tempfile.TemporaryDirectory(prefix="homework-test-") as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'homework.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")

    from fastapi.testclient import TestClient

    import main
    from database import Base, SessionLocal, engine
    from models import Class, Homework, Role, User
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
    teacher.teaching_classes = json.dumps([102])
    student = User(
        role=Role.student, identifier="20260002", password_hash=hash_password("thu260002"),
        name="王芳", class_id=102, must_change_password=False,
    )
    other_student = User(
        role=Role.student, identifier="20260003", password_hash=hash_password("thu260003"),
        name="李明", class_id=101, must_change_password=False,
    )
    db.add(student)
    db.add(other_student)
    db.commit()
    teacher_token = create_access_token(
        user_id=teacher.id, role="teacher", class_id=None,
        teaching_classes=[102], subject="math", must_change_password=False,
    )
    student_token = create_access_token(
        user_id=student.id, role="student", class_id=102, must_change_password=False,
    )
    other_student_token = create_access_token(
        user_id=other_student.id, role="student", class_id=101, must_change_password=False,
    )
    db.close()

    # 假模型：返回固定评分 JSON
    import homework_service

    original_generate = homework_service.generate_answer

    def fake_generate(question, context_block, *, system_prompt=None, tutor_enabled=False):
        return json.dumps({"score": 70, "feedback": "作答基本正确", "is_wrong": False})

    homework_service.generate_answer = fake_generate

    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            th = {"Authorization": f"Bearer {teacher_token}"}
            sh = {"Authorization": f"Bearer {student_token}"}
            oh = {"Authorization": f"Bearer {other_student_token}"}

            # ---------- S1 教师布置作业 ----------
            due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            r = client.post("/api/teacher/homeworks", headers=th, json={
                "class_id": 102, "title": "一元二次方程练习",
                "content": json.dumps({"stem": "解方程 x²-5x+6=0"}), "due_at": due,
            })
            check("S1 正常：教师创建草稿作业 200", r.status_code == 200 and r.json()["status"] == "draft")
            hw_id = r.json()["id"]

            r = client.post("/api/teacher/homeworks", headers=th, json={
                "class_id": 101, "title": "越权作业",
                "content": json.dumps({"stem": "x"}), "due_at": due,
            })
            check("S1 失败：非任教班级布置 → 403", r.status_code == 403)

            # ---------- S2 草稿学生不可见 ----------
            r = client.get("/api/student/homeworks", headers=sh)
            check("S1 正常：草稿作业学生不可见", r.status_code == 200 and r.json() == [])

            # ---------- S3 发布作业 ----------
            r = client.put(f"/api/teacher/homeworks/{hw_id}/publish", headers=th)
            check("S1 正常：发布作业 200", r.status_code == 200 and r.json()["status"] == "published")

            r = client.put(f"/api/teacher/homeworks/{hw_id}/publish", headers=oh)
            check("S1 失败：非作者发布 → 403", r.status_code == 403)

            # ---------- S4 学生查看作业 ----------
            r = client.get("/api/student/homeworks", headers=sh)
            check("S2 正常：学生看到已发布作业", r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["title"] == "一元二次方程练习")
            check("S2 正常：作业携带学科字段 subject=math", r.status_code == 200 and r.json()[0].get("subject") == "math")

            r = client.get("/api/student/homeworks", headers=oh)
            check("S2 正常：其他班学生看不到", r.status_code == 200 and r.json() == [])

            # ---------- S5 学生提交 ----------
            r = client.post(f"/api/student/homeworks/{hw_id}/submit", headers=sh, json={"answer_text": "x=2 或 x=3"})
            check("S3 正常：学生提交成功", r.status_code == 200 and r.json()["status"] == "pending")

            sub_id = r.json()["id"]
            r = client.post(f"/api/student/homeworks/{hw_id}/submit", headers=sh, json={"answer_text": "x=2 或 x=3（修正）"})
            check("S3 正常：重复提交覆盖", r.status_code == 200 and r.json()["id"] == sub_id)

            r = client.post(f"/api/student/homeworks/{hw_id}/submit", headers=oh, json={"answer_text": "越权"})
            check("S3 失败：跨班提交 → 403", r.status_code == 403)

            # ---------- S6 AI 初批 ----------
            r = client.post(f"/api/teacher/homeworks/{hw_id}/ai-grade", headers=th)
            check("S4 正常：AI 初批返回批改数", r.status_code == 200 and r.json()["graded_count"] == 1)

            r = client.get(f"/api/teacher/homeworks/{hw_id}/submissions", headers=th)
            subs = r.json()
            check("S4 正常：AI 分数写入提交", subs[0]["ai_score"] == 70 and subs[0]["status"] == "ai_graded")

            # ---------- S7 教师改分（判对） ----------
            r = client.put(f"/api/teacher/submissions/{sub_id}/grade", headers=th, json={"score": 85, "feedback": "过程完整"})
            check("S5 正常：教师改分 200", r.status_code == 200 and r.json()["teacher_score"] == 85 and r.json()["status"] == "teacher_graded")

            from models import MistakeNote
            db = SessionLocal()
            note_count = db.query(MistakeNote).count()
            db.close()
            check("S7 正常：判对（85分）不写错题本", note_count == 0)

            # ---------- S8 教师改分（判错 → 错题收录） ----------
            r = client.put(f"/api/teacher/submissions/{sub_id}/grade", headers=th, json={"score": 50, "feedback": "计算错误"})
            check("S5 正常：教师改判错 200", r.status_code == 200 and r.json()["teacher_score"] == 50)

            db = SessionLocal()
            notes = db.query(MistakeNote).all()
            db.close()
            check("S7 正常：判错（50分）写入错题本", len(notes) == 1 and notes[0].student_id == student.id and notes[0].subject == "math")

            # ---------- 学情概览与作业/错题数据一致性 ----------
            r = client.get("/api/student/analytics/overview", headers=sh)
            ov = r.json()
            check("U1 一致：学情概览作业提交数=已批改提交数", r.status_code == 200 and ov["submissions"] == 1)
            check("U1 一致：学情概览正确率=教师评分均值(50)", ov["accuracy"] == 50)
            check("U1 一致：学情概览错题累计=错题本记录数", ov["mistakes"] == 1)

            # ---------- S9 学生查看批改结果 ----------
            r = client.get(f"/api/student/submissions/{sub_id}", headers=sh)
            check("S6 正常：学生看到最终分（教师分优先）", r.status_code == 200 and r.json()["final_score"] == 50 and r.json()["feedback"] == "计算错误")

            r = client.get(f"/api/student/submissions/{sub_id}", headers=oh)
            check("S6 失败：学生查看他人提交 → 403", r.status_code == 403)

            # ---------- S10 教师越权批改 ----------
            r = client.put(f"/api/teacher/submissions/{sub_id}/grade", headers=oh, json={"score": 90, "feedback": "越权"})
            check("S8 失败：非任教教师改分 → 403", r.status_code == 403)

            # ---------- S11 关闭作业 ----------
            r = client.put(f"/api/teacher/homeworks/{hw_id}/close", headers=th)
            check("S9 正常：教师关闭作业", r.status_code == 200 and r.json()["status"] == "closed")

            r = client.post(f"/api/student/homeworks/{hw_id}/submit", headers=sh, json={"answer_text": "已关闭不能提交"})
            check("S3 失败：关闭后提交 → 400", r.status_code == 400)

            # ---------- S12 截止后提交 ----------
            past_due = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            r = client.post("/api/teacher/homeworks", headers=th, json={
                "class_id": 102, "title": "已截止作业",
                "content": json.dumps({"stem": "x"}), "due_at": past_due,
            })
            past_hw_id = r.json()["id"]
            client.put(f"/api/teacher/homeworks/{past_hw_id}/publish", headers=th)
            r = client.post(f"/api/student/homeworks/{past_hw_id}/submit", headers=sh, json={"answer_text": "截止"})
            check("S3 失败：截止后提交 → 400", r.status_code == 400)

            # ---------- S13 AI 失败不写入 ----------
            def failing_generate(question, context_block, *, system_prompt=None, tutor_enabled=False):
                return "not valid json {"

            homework_service.generate_answer = failing_generate
            r = client.post("/api/teacher/homeworks", headers=th, json={
                "class_id": 102, "title": "AI失败测试",
                "content": json.dumps({"stem": "x"}), "due_at": due,
            })
            fail_hw_id = r.json()["id"]
            client.put(f"/api/teacher/homeworks/{fail_hw_id}/publish", headers=th)
            client.post(f"/api/student/homeworks/{fail_hw_id}/submit", headers=sh, json={"answer_text": "ans"})
            r = client.post(f"/api/teacher/homeworks/{fail_hw_id}/ai-grade", headers=th)
            subs = client.get(f"/api/teacher/homeworks/{fail_hw_id}/submissions", headers=th).json()
            check("S4 失败：AI 返回无效 JSON 不写入分数", subs[0]["ai_score"] is None and subs[0]["status"] == "pending")

            homework_service.generate_answer = original_generate

            # ---------- 多学科作业可见性（支撑前端学科筛选） ----------
            # 教师只能创建本学科作业，其他学科作业由对应学科教师创建。
            # 直接往 DB 插入物理、语文作业，验证学生能看到全部学科且 subject 正确。
            db = SessionLocal()
            due_dt = datetime.now(timezone.utc) + timedelta(days=1)
            db.add(Homework(
                class_id=102, teacher_id=teacher.id, subject="physics",
                title="物理作业", content_json=json.dumps({"stem": "F=ma"}),
                status="published", due_at=due_dt,
            ))
            db.add(Homework(
                class_id=102, teacher_id=teacher.id, subject="chinese",
                title="语文作业", content_json=json.dumps({"stem": "默写"}),
                status="published", due_at=due_dt,
            ))
            db.commit()
            db.close()

            r = client.get("/api/student/homeworks", headers=sh)
            hw_list = r.json()
            subjects = {h["subject"] for h in hw_list}
            check("U2 正常：学生可见多学科作业", "math" in subjects and "physics" in subjects and "chinese" in subjects)
            check("U2 正常：每条作业均携带 subject 字段", all("subject" in h for h in hw_list))
            math_hws = [h for h in hw_list if h["subject"] == "math"]
            check("U2 正常：数学作业 subject=math", len(math_hws) >= 1 and all(h["subject"] == "math" for h in math_hws))
    finally:
        homework_service.generate_answer = original_generate
        engine.dispose()

passed = sum(1 for _, ok in checks if ok)
print(f"\n结果：{passed}/{len(checks)} 通过")
sys.exit(0 if passed == len(checks) else 1)
