"""学情诊断回归：学生学情概览/掌握度/画像、教师班级学情、越权与失败路径（add-learning-diagnostics）。

每条检查名前的 S 编号对应 learning-diagnostics 规约中的场景。
临时数据库、假模型返回固定画像 JSON，不连外网。

用法（项目根）：make check，或
  JWT_SECRET_KEY=<至少 32 字符> PYTHONPATH=backend backend/.venv/bin/python apitest/check_analytics.py
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


with tempfile.TemporaryDirectory(prefix="analytics-test-", ignore_cleanup_errors=True) as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'analytics.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")

    from fastapi.testclient import TestClient

    import main
    from database import Base, SessionLocal, engine
    from models import (
        Class, Conversation, Homework, HomeworkSubmission, Message,
        MistakeNote, Role, User,
    )
    from security import create_access_token, hash_password

    Base.metadata.create_all(engine)
    db = SessionLocal()
    db.add(Class(id=101, name="一班"))
    db.add(Class(id=102, name="二班"))

    # 教师：数学，任教 101+102，101 班主任
    teacher = User(
        role=Role.teacher, identifier="TEA001", password_hash=hash_password("Teach@2026"),
        name="张老师", class_id=None, subject="math", must_change_password=False,
        homeroom_class_id=101,
    )
    db.add(teacher)
    db.flush()
    teacher.teaching_classes = "[101, 102]"

    # 学生：王芳 102，李明 101
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

    # 数学作业（102 班）
    hw_math = Homework(
        class_id=102, teacher_id=teacher.id, subject="math",
        title="数学练习", content_json='{"stem":"1+1"}',
        status="published", due_at=datetime.now(timezone.utc),
    )
    db.add(hw_math)
    # 物理作业（102 班）
    hw_physics = Homework(
        class_id=102, teacher_id=teacher.id, subject="physics",
        title="物理练习", content_json='{"stem":"F=ma"}',
        status="published", due_at=datetime.now(timezone.utc),
    )
    db.add(hw_physics)
    db.flush()

    # 王芳提交数学 80 分、物理 40 分
    sub_math = HomeworkSubmission(
        class_id=102, student_id=student.id, homework_id=hw_math.id,
        answer_text="2", submitted_at=datetime.now(timezone.utc),
        teacher_score=80, teacher_feedback="不错", teacher_graded_at=datetime.now(timezone.utc),
        status="teacher_graded",
    )
    sub_physics = HomeworkSubmission(
        class_id=102, student_id=student.id, homework_id=hw_physics.id,
        answer_text="F=mv", submitted_at=datetime.now(timezone.utc),
        teacher_score=40, teacher_feedback="公式错误", teacher_graded_at=datetime.now(timezone.utc),
        status="teacher_graded",
    )
    db.add(sub_math)
    db.add(sub_physics)

    # 王芳的错题：数学 1 条未掌握，物理 1 条已掌握
    note_math = MistakeNote(
        class_id=102, student_id=student.id, subject="math", homework_id=hw_math.id,
        question_stem="1+1", student_answer="3", reason="粗心", mastered=False,
    )
    note_physics = MistakeNote(
        class_id=102, student_id=student.id, subject="physics", homework_id=hw_physics.id,
        question_stem="F=ma", student_answer="F=mv", reason="公式记错", mastered=True,
        mastered_at=datetime.now(timezone.utc),
    )
    db.add(note_math)
    db.add(note_physics)

    # 李明的错题（101 班）
    note_other = MistakeNote(
        class_id=101, student_id=other_student.id, subject="math", homework_id=None,
        question_stem="他人错题", student_answer="ans", reason="错因", mastered=False,
    )
    db.add(note_other)

    # 王芳的助手对话与提问
    conv = Conversation(student_id=student.id, class_id=102, subject="math")
    db.add(conv)
    db.flush()
    msg = Message(conversation_id=conv.id, role="user", content="什么是导数？")
    db.add(msg)

    db.commit()

    teacher_token = create_access_token(
        user_id=teacher.id, role="teacher", class_id=None,
        teaching_classes=[101, 102], subject="math", homeroom_class_id=101,
        must_change_password=False,
    )
    student_token = create_access_token(
        user_id=student.id, role="student", class_id=102, must_change_password=False,
    )
    other_student_token = create_access_token(
        user_id=other_student.id, role="student", class_id=101, must_change_password=False,
    )
    db.close()

    # 假模型：返回固定画像 JSON
    import analytics_service

    original_generate = analytics_service.generate_answer

    def fake_generate(question, context_block, *, system_prompt=None, tutor_enabled=False):
        return '{"style":"逻辑推理型","strengths":["数学"],"weaknesses":["物理"],"suggestion":"多做物理基础题"}'

    analytics_service.generate_answer = fake_generate

    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            sh = {"Authorization": f"Bearer {student_token}"}
            oh = {"Authorization": f"Bearer {other_student_token}"}
            th = {"Authorization": f"Bearer {teacher_token}"}

            # ---------- 学生：学情概览 ----------
            r = client.get("/api/student/analytics/overview", headers=sh)
            body = r.json()
            check("S1 正常：本人学情概览正确", r.status_code == 200 and body["questions"] == 1 and body["submissions"] == 2 and body["mistakes"] == 2)
            check("S1 正常：作业正确率为平均分", body["accuracy"] == 60)  # (80+40)/2

            r = client.get("/api/student/analytics/overview", headers=oh)
            body = r.json()
            check("S4 正常：李明概览不含王芳数据", r.status_code == 200 and body["questions"] == 0 and body["submissions"] == 0 and body["mistakes"] == 1)

            # ---------- 学生：学科掌握度 ----------
            r = client.get("/api/student/analytics/mastery", headers=sh)
            body = r.json()
            subjects = {s["subject"]: s for s in body["subjects"]}
            check("S1 正常：数学掌握度含成绩与错题", "math" in subjects and subjects["math"]["mastery"] is not None)
            check("S1 正常：综合掌握度非空", body["overall"] is not None)
            check("S1 正常：近期趋势含 2 条", len(body["trend"]) == 2)

            # ---------- 学生：AI 画像 ----------
            r = client.post("/api/student/analytics/portrait", headers=sh)
            body = r.json()
            check("S1 正常：AI 画像返回且可用", r.status_code == 200 and body["available"] is True and body["portrait"]["style"] == "逻辑推理型")

            # ---------- 失败：AI 未配置 ----------
            analytics_service.generate_answer = lambda *a, **k: None
            r = client.post("/api/student/analytics/portrait", headers=sh)
            body = r.json()
            check("S2 失败：AI 未配置时画像降级", r.status_code == 200 and body["available"] is False and body["portrait"] is None)
            analytics_service.generate_answer = fake_generate

            # ---------- 教师：班级学情（班主任全科 101） ----------
            r = client.get("/api/teacher/analytics/class?class_id=101", headers=th)
            body = r.json()
            check("S1 正常：班主任查看本班全科 101 学情", r.status_code == 200 and body["class_id"] == 101 and body["total_students"] == 1)

            # ---------- 教师：班级学情（任课单科 102 数学） ----------
            r = client.get("/api/teacher/analytics/class?class_id=102&subject=math", headers=th)
            body = r.json()
            check("S1 正常：任课查看 102 数学学情", r.status_code == 200 and body["subject"] == "math" and body["class_average"] == 80)

            # ---------- 教师：班级学情（102 全科，含各学科平均分） ----------
            r = client.get("/api/teacher/analytics/class?class_id=102", headers=th)
            body = r.json()
            check("S1 正常：102 全科学情含各学科平均分", r.status_code == 200 and "math" in body["subject_averages"] and "physics" in body["subject_averages"])
            check("S1 正常：102 数学平均分=80", body["subject_averages"]["math"] == 80)
            check("S1 正常：102 物理平均分=40", body["subject_averages"]["physics"] == 40)

            # ---------- 越权：学生访问班级学情 ----------
            r = client.get("/api/teacher/analytics/class?class_id=102", headers=sh)
            check("S3 失败：学生访问班级学情 → 403", r.status_code == 403)

            # ---------- 越权：教师跨班（非任教班级） ----------
            r = client.get("/api/teacher/analytics/class?class_id=999", headers=th)
            check("S3 失败：教师跨班访问 → 403", r.status_code == 403)

            # ---------- 越权：教师跨学科 ----------
            r = client.get("/api/teacher/analytics/class?class_id=102&subject=english", headers=th)
            check("S3 失败：教师跨学科访问 → 403", r.status_code == 403)

            # ---------- 数据隔离：班级学情不含作答/评语原文 ----------
            r = client.get("/api/teacher/analytics/class?class_id=102&subject=math", headers=th)
            body = r.json()
            ranking_text = str(body["student_ranking"])
            check("S4 正常：班级学情不含作答原文", "F=mv" not in ranking_text and "2" not in ranking_text)
            check("S4 正常：班级学情不含评语原文", "公式错误" not in ranking_text and "不错" not in ranking_text)

            # ---------- 数据隔离：李明看不到王芳学情 ----------
            r = client.get("/api/student/analytics/overview", headers=oh)
            body = r.json()
            check("S4 正常：李明看不到王芳作业数据", body["submissions"] == 0 and body["accuracy"] is None)

            # ---------- 请求参数 class_id 被忽略（班主任只能看本班） ----------
            # 教师是 101 班主任且任教 101+102，请求 102 应正常（在任教范围）；
            # 这里验证非任教班级被拒而非参数生效
            r = client.get("/api/teacher/analytics/class?class_id=102", headers=th)
            check("S4 正常：任教范围内班级可查", r.status_code == 200)

    finally:
        analytics_service.generate_answer = original_generate

passed = sum(1 for _, p in checks if p)
total = len(checks)
print(f"\n结果：{passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
