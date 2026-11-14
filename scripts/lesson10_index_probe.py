#!/usr/bin/env python3
"""第10课索引探针：在临时合成库上重放三个目标 SQL 的 EXPLAIN QUERY PLAN。

只读现有模型定义，不连接教学库、不写仓库数据。输出可作为“为什么加这个索引”的证据；
复跑同一命令即可对比加索引前后。

用法：backend/.venv/bin/python scripts/lesson10_index_probe.py [--rows 3000] [--json PATH]
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DISPATCH_SQL = """
SELECT id FROM grade_tasks
WHERE (status IN ('pending','retrying') AND next_attempt_at <= :now AND last_published_at IS NULL)
   OR (status = 'running' AND lease_until <= :now AND (last_published_at IS NULL OR last_published_at <= lease_until))
   OR (status = 'dead' AND dead_published_at IS NULL)
ORDER BY id LIMIT 100
"""

TASK_DETAIL_SQL = "SELECT * FROM grade_tasks WHERE id = :id"

RETRIEVAL_SQL = """
SELECT material_chunks.id, material_chunks.material_id, material_chunks.chunk_index
FROM material_chunks
JOIN materials ON materials.id = material_chunks.material_id
WHERE material_chunks.class_id IN (:c1, :c2)
  AND materials.is_indexed = 1
  AND material_chunks.material_id IN (:m1, :m2, :m3)
ORDER BY material_chunks.material_id, material_chunks.chunk_index
"""


def build(rows: int):
    os.environ["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
    os.environ["DEEPSEEK_API_KEY"] = ""
    directory = tempfile.TemporaryDirectory(prefix="lesson10-index-", ignore_cleanup_errors=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory.name) / 'probe.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(directory.name) / "uploads")

    from database import Base, SessionLocal, engine
    from models import Class, GradeTask, Material, MaterialChunk, User

    Base.metadata.create_all(engine)
    moment = datetime(2026, 11, 14, 7, 0, 0)
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="探针一班"), Class(id=102, name="探针二班")])
        db.flush()
        db.add(User(id=1, identifier="probe-teacher", password_hash="x", role="teacher",
                    name="探针教师", subject="math", class_id=None, teaching_classes="[101,102]"))
        db.add(User(id=2, identifier="probe-student", password_hash="x", role="student",
                    name="探针学生", subject=None, class_id=101))
        db.flush()
        materials = [Material(id=i, class_id=101 if i % 2 else 102, filename=f"m{i}.md",
                              uploader_id=1, is_indexed=True, file_path=f"/tmp/m{i}.md",
                              file_size=1, file_type="text/markdown")
                     for i in range(1, 101)]
        db.add_all(materials)
        db.flush()
        chunks = []
        for material in materials:
            for index in range(50):
                chunks.append(MaterialChunk(material_id=material.id, class_id=material.class_id,
                                            chunk_index=index, content=f"分块{material.id}-{index}",
                                            embedding=b"\x00" * 8))
        db.add_all(chunks)
        statuses = ["pending", "retrying", "running", "dead", "succeeded", "skipped"]
        for index in range(rows):
            status = statuses[index % len(statuses)]
            db.add(GradeTask(
                submission_id=index + 1, homework_id=index % 50 + 1, class_id=101,
                subject="math", teacher_id=1, input_fingerprint=f"f{index}", input_json="{}",
                request_id=f"r{index}", status=status, max_attempts=3,
                next_attempt_at=moment if status == "pending" else moment + timedelta(days=1),
                lease_until=moment - timedelta(seconds=1) if status == "running" else None,
                last_published_at=None, dead_published_at=None,
            ))
        db.commit()
    return directory, engine


def explain(engine, sql, params):
    from sqlalchemy import text
    with engine.connect() as conn:
        rows = conn.execute(text("EXPLAIN QUERY PLAN " + sql), params).fetchall()
        return [row[-1] for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--analyze", action="store_true", help="先执行 ANALYZE，再取执行计划")
    args = parser.parse_args()
    directory, engine = build(args.rows)
    if args.analyze:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ANALYZE"))
            conn.commit()
    moment = datetime(2026, 11, 14, 7, 0, 0)
    plans = {
        "dispatch": explain(engine, DISPATCH_SQL, {"now": moment}),
        "task_detail": explain(engine, TASK_DETAIL_SQL, {"id": 42}),
        "retrieval": explain(engine, RETRIEVAL_SQL,
                             {"c1": 101, "c2": 102, "m1": 1, "m2": 2, "m3": 3}),
    }
    with engine.connect() as conn:
        from sqlalchemy import text
        indexes = [row[1] for row in conn.execute(text(
            "SELECT type, name FROM sqlite_master WHERE type='index' AND tbl_name IN ('grade_tasks','material_chunks') ORDER BY tbl_name, name"
        )).fetchall()]
    for name, plan in plans.items():
        print(f"[{name}]")
        for line in plan:
            print("  " + line)
    print("[indexes] " + ", ".join(indexes))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"rows": args.rows, "plans": plans, "indexes": indexes},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    engine.dispose()
    directory.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
