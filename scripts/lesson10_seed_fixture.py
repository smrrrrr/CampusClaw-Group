#!/usr/bin/env python3
"""第10课独立演示夹具：在**空库**中写入合成班级、账号、作业、提交与资料。

不重置已有账号，不运行 dev_seed；发现目标库已有非本夹具数据时拒绝执行。
仅用于独立演示实例，账号密码为固定合成值，不得用于教学部署。

用法（宿主，库文件由 Compose 挂载）：
    DATABASE_URL=sqlite:///./data/campusclaw.db backend/.venv/bin/python scripts/lesson10_seed_fixture.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("JWT_SECRET_KEY", "lesson10-fixture-only-secret-000000000000")

from database import Base, SessionLocal, engine  # noqa: E402
from models import Class, Homework, HomeworkSubmission, Material, User  # noqa: E402
from security import hash_password  # noqa: E402

PASSWORD = "Lesson10!demo"


def main() -> int:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = db.query(User).filter(User.identifier.in_(["T10A", "S10A"])).count()
        if existing:
            print("夹具已存在，跳过（不覆盖任何数据）")
            return 0
        other = db.query(User).count()
        if other:
            print(f"目标库已有 {other} 个账号，不是空库；拒绝写入合成夹具")
            return 2

        db.add_all([Class(id=201, name="演示一班"), Class(id=202, name="演示二班")])
        db.flush()
        teacher = User(role="teacher", identifier="T10A", password_hash=hash_password(PASSWORD),
                       name="演示教师", subject="math", teaching_classes="[201]",
                       must_change_password=False)
        other_teacher = User(role="teacher", identifier="T10B", password_hash=hash_password(PASSWORD),
                             name="二班教师", subject="math", teaching_classes="[202]",
                             must_change_password=False)
        student = User(role="student", identifier="S10A", password_hash=hash_password(PASSWORD),
                       name="演示学生", class_id=201, must_change_password=False)
        db.add_all([teacher, other_teacher, student])
        db.flush()

        homework = Homework(class_id=201, subject="math", teacher_id=teacher.id, title="演示作业",
                            content_json=json.dumps({"title": "演示作业", "questions": [{"stem": "1+1=?"}]},
                                                    ensure_ascii=False),
                            due_at=datetime(2026, 12, 31, 23, 59, 59), status="published")
        db.add(homework)
        db.flush()
        db.add(HomeworkSubmission(class_id=201, student_id=student.id, homework_id=homework.id,
                                  answer_text="1+1=2", submitted_at=datetime(2026, 11, 14, 8, 0, 0),
                                  status="submitted"))
        db.add_all([
            Material(class_id=201, uploader_id=teacher.id, filename="一班讲义.md",
                     file_path="201/lesson.md", file_type="text/markdown", file_size=10, is_indexed=False),
            Material(class_id=202, uploader_id=other_teacher.id, filename="二班讲义.md",
                     file_path="202/lesson.md", file_type="text/markdown", file_size=10, is_indexed=False),
        ])
        db.commit()
        print(json.dumps({"classes": [201, 202], "homework_id": homework.id,
                          "users": ["T10A", "T10B", "S10A"]}, ensure_ascii=False))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
