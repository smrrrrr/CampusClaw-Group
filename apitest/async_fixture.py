"""仅由隔离复现容器执行，创建合成账号和作业，不运行dev_seed。"""
import json
from datetime import datetime, timedelta

from database import Base, SessionLocal, engine, run_simple_migrations
from models import Class, Homework, HomeworkSubmission, Role, User
from security import hash_password

run_simple_migrations()
Base.metadata.create_all(engine)
with SessionLocal() as db:
    assert db.query(User).count() == 0, "只允许在空临时库建立合成数据"
    db.add(Class(id=101, name="Synthetic class")); db.flush()
    teacher = User(identifier="async-teacher", name="Synthetic teacher", role=Role.teacher,
                   password_hash=hash_password("Check-only-password123!"), subject="math",
                   teaching_classes="[101]", must_change_password=False)
    db.add(teacher); db.flush()
    result = {}
    for name, count, answer in [("bulk", 20, "4"), ("duplicate", 1, "4"), ("crash", 1, "SLOW_ME"),
                                 ("failure", 1, "FAIL_ME"), ("outage", 1, "4")]:
        hw = Homework(class_id=101, teacher_id=teacher.id, subject="math", title="Synthetic " + name,
                      content_json='{"stem":"2+2"}', status="published", due_at=datetime.utcnow() + timedelta(days=1))
        db.add(hw); db.flush()
        ids = []
        for i in range(count):
            student = User(identifier=f"synthetic-{name}-{i}", name="Synthetic student", role=Role.student,
                           class_id=101, password_hash="unused", must_change_password=False)
            db.add(student); db.flush()
            sub = HomeworkSubmission(homework_id=hw.id, class_id=101, student_id=student.id,
                                     answer_text=answer, submitted_at=datetime.utcnow(), status="pending")
            db.add(sub); db.flush(); ids.append(sub.id)
        result[name] = {"homework_id": hw.id, "submission_ids": ids}
    db.commit()
print(json.dumps(result))
