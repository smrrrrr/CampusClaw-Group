"""第10课交付工程检查：索引迁移幂等、观测采集口径、窗口失败率。

临时库 + 合成事件；不连接教学库、不启动容器、不调用模型。
对应任务 6.4（扩/迁/兼容）、8.2（采集去重与口径）、8.4（窗口报数）。
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
checks = []


def check(name, passed):
    assert passed, name
    checks.append(name)


with tempfile.TemporaryDirectory(prefix="lesson10-ops-", ignore_cleanup_errors=True) as directory:
    db_path = Path(directory) / "ops.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["UPLOAD_DIR"] = str(Path(directory) / "uploads")
    os.environ["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["LOG_FILE"] = ""
    sys.path.insert(0, str(ROOT / "backend"))

    from database import Base, engine, run_simple_migrations
    import models  # noqa: F401

    # 先造出旧索引结构，模拟已有教学库升级。
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP INDEX IF EXISTS ix_material_chunk_class_material_chunk")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_material_chunk_class_material ON material_chunks(class_id, material_id)")
        conn.exec_driver_sql("INSERT INTO classes (id, name, created_at) VALUES (101, '检查一班', '2026-11-14 07:00:00')")
        conn.exec_driver_sql(
            "INSERT INTO materials (id, class_id, uploader_id, filename, file_path, file_type, file_size, is_indexed, created_at) "
            "VALUES (1, 101, 1, 'm.md', '/tmp/m.md', 'text/markdown', 1, 1, '2026-11-14 07:00:00')"
        )
        conn.exec_driver_sql(
            "INSERT INTO material_chunks (material_id, class_id, chunk_index, content, embedding, created_at) "
            "VALUES (1, 101, 0, '分块', X'00', '2026-11-14 07:00:00')"
        )

    run_simple_migrations()
    run_simple_migrations()
    with engine.connect() as conn:
        names = {row[0] for row in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='material_chunks'"
        )}
        chunk_rows = conn.exec_driver_sql("SELECT COUNT(*) FROM material_chunks").scalar()
        plan = [row[-1] for row in conn.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT id, material_id, chunk_index FROM material_chunks "
            "WHERE class_id = 101 AND material_id = 1 ORDER BY material_id, chunk_index"
        )]
    check("M1 正常：重复迁移两次后新覆盖索引存在、旧索引移除", "ix_material_chunk_class_material_chunk" in names
          and "ix_material_chunk_class_material" not in names)
    check("M2 边界：纯索引迁移不改分块数据", chunk_rows == 1)
    check("M3 正常：检索计划使用覆盖索引", any("COVERING INDEX" in line and "class_material_chunk" in line for line in plan))

    # 合成技能事件：直接写库，验证采集口径而非业务写入路径。
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO users (id, role, identifier, password_hash, must_change_password, created_at, updated_at) "
                             "VALUES (1, 'teacher', 'T1', 'x', 0, '2026-11-14 07:00:00', '2026-11-14 07:00:00')")
        conn.exec_driver_sql("INSERT INTO users (id, role, identifier, password_hash, must_change_password, class_id, created_at, updated_at) "
                             "VALUES (2, 'student', 'S1', 'x', 0, 101, '2026-11-14 07:00:00', '2026-11-14 07:00:00')")
        for index in range(4):
            conn.exec_driver_sql(
                "INSERT INTO ai_question_logs (student_id, class_id, question, answer, created_at) VALUES (2, 101, ?, ?, ?)",
                ("问题" if index < 3 else "未完成", "回答" if index < 3 else None,
                 (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")),
            )
        states = ["succeeded", "succeeded", "dead", "pending", "running"]
        for index, status in enumerate(states):
            conn.exec_driver_sql(
                "INSERT INTO grade_tasks (submission_id, homework_id, class_id, subject, teacher_id, input_fingerprint, "
                "input_json, request_id, status, attempts, execution_count, max_attempts, next_attempt_at, created_at, updated_at) "
                "VALUES (?, 1, 101, 'math', 1, ?, '{}', ?, ?, 1, 1, 3, ?, ?, ?)",
                (index + 1, f"fp{index}", f"r{index}", status,
                 now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
            )
    engine.dispose()

    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}", "OBS_LOG_FILE": ""}
    output = subprocess.run([PY, str(ROOT / "scripts/observability/collect.py"), "--once", "--db", str(db_path)],
                            capture_output=True, text=True, env=env)
    check("C1 正常：采集器退出码 0 且输出 Prometheus 文本", output.returncode == 0 and "# TYPE skill_invocations_total counter" in output.stdout)
    check("C2 正常：引导技能计入已完成事件，未完成单列 unknown",
          'skill_invocations_total{skill="tutor_guidance",status="succeeded"} 3' in output.stdout
          and 'skill_invocations_total{skill="tutor_guidance",status="unknown"} 1' in output.stdout)
    check("C3 正常：批改按成功/失败/进行中分列",
          'skill_invocations_total{skill="homework_grading",status="succeeded"} 2' in output.stdout
          and 'skill_invocations_total{skill="homework_grading",status="failed"} 1' in output.stdout)
    check("C4 边界：无持久事件来源的技能标记未接入，不伪造 0 事件",
          'skill_events_available{skill="mistake_explanation"} 0' in output.stdout)

    start = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    window = subprocess.run([PY, str(ROOT / "scripts/observability/collect.py"), "--window", start, end,
                             "--db", str(db_path)], capture_output=True, text=True, env=env)
    report = json.loads(window.stdout)
    grading = report["skills"]["homework_grading"]
    check("W1 正常：窗口失败率按 failed/(succeeded+failed) 计算",
          grading["succeeded"] == 2 and grading["failed"] == 1 and grading["failure_rate"] == round(1 / 3, 4))
    check("W2 边界：无样本技能不给 0，明确无样本",
          report["skills"]["mistake_explanation"]["failure_rate"] is None)

    # 流水线静态核查：与本地门禁同命令、无静默放行、镜像构建依赖两道门禁。
    import yaml
    workflow_text = (ROOT / ".github/workflows/lesson10.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    jobs = workflow["jobs"]

    def run_text(job):
        return "\n".join(step.get("run", "") for step in jobs[job]["steps"])

    check("CI1 正常：check job 原样运行 make check", "make check" in run_text("check"))
    check("CI2 正常：security job 原样运行 make check-security", "make check-security" in run_text("security"))
    check("CI3 正常：镜像构建同时依赖两道门禁",
          set(jobs["images"]["needs"]) == {"check", "security"})
    check("CI4 边界：不允许 continue-on-error 静默放行", "continue-on-error" not in workflow_text)
    check("CI5 正常：镜像使用提交号标签并带 OCI revision",
          "GIT_SHA" in (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
          and "org.opencontainers.image.revision" in (ROOT / "backend/Dockerfile").read_text(encoding="utf-8"))

print(json.dumps({"passed": len(checks), "checks": checks, "scope": "temporary SQLite; no containers/models"},
                 ensure_ascii=False))
