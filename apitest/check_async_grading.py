"""异步初批离线场景：临时库、假模型和队列替身；真实代理另见reproduce脚本。"""
import json
import os
import statistics
import sqlite3
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
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


class MemoryQueue:
    def __init__(self):
        self.messages, self.dead = [], []

    def publish(self, task_id, dead=False):
        (self.dead if dead else self.messages).append(task_id)


with tempfile.TemporaryDirectory(prefix="async-grading-", ignore_cleanup_errors=True) as directory:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory) / 'test.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(directory) / "uploads")
    from fastapi.testclient import TestClient
    from sqlalchemy import event, text
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SQLAlchemyError
    import database
    import grading_service as gs
    import homework_service as hs
    from config import settings
    from database import Base, SessionLocal, engine
    from main import app
    from models import AuditLog, Class, GradeTask, Homework, HomeworkSubmission, Role, User
    from security import create_access_token

    Base.metadata.create_all(engine)
    headers = {}
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="隔离一班"), Class(id=102, name="隔离二班")])
        db.flush()
        for index, (who, role, subject, classes, cid) in enumerate([
            ("teacher", Role.teacher, "math", [101], None),
            ("other", Role.teacher, "math", [102], None),
            ("physics", Role.teacher, "physics", [101], None),
            ("student", Role.student, None, None, 101),
        ], 1):
            db.add(User(id=index, identifier=who, role=role, name=who, subject=subject,
                        teaching_classes=json.dumps(classes) if classes else None, class_id=cid,
                        password_hash="unused", must_change_password=False))
            headers[who] = {"Authorization": "Bearer " + create_access_token(
                user_id=index, role=role.value, subject=subject, teaching_classes=classes,
                class_id=cid, must_change_password=False)}
        db.commit()

    def fixture(count=1):
        with SessionLocal() as db:
            hw = Homework(class_id=101, teacher_id=1, subject="math", title="隔离演示题",
                          content_json='{"stem":"2+2"}', status="published", due_at=datetime.now() + timedelta(days=1))
            db.add(hw); db.flush()
            ids = []
            for i in range(count):
                # 大批量用独立合成学生ID，绝不读教学库。
                student = User(identifier=f"student-{hw.id}-{i}", role=Role.student, name="合成学生",
                               class_id=101, password_hash="unused", must_change_password=False)
                db.add(student); db.flush()
                sub = HomeworkSubmission(class_id=101, student_id=student.id, homework_id=hw.id,
                                         answer_text="4", submitted_at=gs.now(), status="pending")
                db.add(sub); db.flush(); ids.append(sub.id)
            hw_id = hw.id
            db.commit()
            return hw_id, ids

    calls = []
    def model(*args, **kwargs):
        calls.append(1)
        return '{"score":70,"feedback":"合成评分"}'
    hs.generate_answer = model
    queue = MemoryQueue()
    with TestClient(app) as client:
        def req(method, path, who="teacher", **kw):
            return client.request(method, path, headers=headers.get(who, {}), **kw)
        def enqueue(hw):
            response = req("POST", f"/api/teacher/homeworks/{hw}/ai-grade")
            assert response.status_code == 202, response.text
            return response.json()
        def task(task_id):
            return req("GET", f"/api/teacher/grade-tasks/{task_id}").json()
        def due(task_id):
            with SessionLocal() as db:
                row = db.get(GradeTask, task_id)
                row.next_attempt_at = datetime(2000, 1, 1)
                row.last_published_at = None
                db.commit()

        hw, sub_ids = fixture(20)
        timings, bodies = [], []
        for _ in range(20):
            start = time.perf_counter(); bodies.append(enqueue(hw)); timings.append(time.perf_counter() - start)
        p95 = sorted(timings)[18]
        start = time.perf_counter(); time.sleep(.2); model_cost = time.perf_counter() - start
        check("A1 正常：20次202无评分且P95小于200ms假执行，无请求内模型调用",
              p95 < model_cost and not calls and len(bodies[0]["task_ids"]) == 20
              and all(b["task_ids"] == bodies[0]["task_ids"] and "score" not in b for b in bodies)
              and bodies[0]["created_count"] == 20 and bodies[-1]["existing_count"] == 20)
        first = bodies[0]["task_ids"][0]
        before = task(first)
        for _ in range(3):
            req("GET", f"/api/teacher/homeworks/{hw}/grade-tasks"); task(first)
        check("A2 正常：GET只读", before == task(first))
        empty, _ = fixture(0)
        check("A2 边界：无提交空批次", enqueue(empty)["task_ids"] == [])
        check("A3 失败：非法任务编号422", req("GET", "/api/teacher/grade-tasks/invalid").status_code == 422
              and req("GET", "/api/teacher/grade-tasks/0").status_code == 422)
        check("A3 失败：任务和作业不存在404", req("GET", "/api/teacher/grade-tasks/999999").status_code == 404
              and req("POST", "/api/teacher/homeworks/999999/ai-grade").status_code == 404)
        check("A3 失败：活跃任务重试409", req("POST", f"/api/teacher/grade-tasks/{first}/retry").status_code == 409)

        gs.dispatch(queue)
        check("B1 正常：队列有消息、消费者未运行时pending", first in queue.messages and task(first)["status"] == "pending")
        confirmed_messages = list(queue.messages)
        original_now = gs.now
        try:
            for minutes in (1, 5, 30):
                gs.now = lambda minutes=minutes: original_now() + timedelta(minutes=minutes)
                gs.dispatch(queue)
        finally:
            gs.now = original_now
        check("Q1 边界：确认后跨越30分钟不积攒副本", queue.messages == confirmed_messages)
        check("B1 正常：启动消费后成功", gs.process_task(first) == "succeeded" and task(first)["attempts"] == 1)
        failed_hw, failed_subs = fixture()
        failed_id = enqueue(failed_hw)["task_ids"][0]
        class BrokenQueue:
            def publish(self, *a, **kw):
                raise ConnectionError("不得回显的代理内部错误")
        try:
            gs.dispatch(BrokenQueue())
            raised = False
        except ConnectionError:
            raised = True
        with SessionLocal() as db:
            check("B2 失败：代理故障任务未丢且未标记投递", raised and db.get(GradeTask, failed_id).last_published_at is None)
        gs.dispatch(queue)
        check("B2 正常：恢复后补投并可消费", failed_id in queue.messages and gs.process_task(failed_id) == "succeeded")

        atomic_hw, atomic_subs = fixture(2)
        inserts = []
        def break_second(conn, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO grade_tasks"):
                inserts.append(1)
                if len(inserts) == 2:
                    raise SQLAlchemyError("合成第二条写入故障：禁止回显SQL与路径")
        event.listen(engine, "before_cursor_execute", break_second)
        try:
            fault = req("POST", f"/api/teacher/homeworks/{atomic_hw}/ai-grade")
            check("B3 失败：数据库错误503且不泄露内部信息", fault.status_code == 503
                  and "禁止回显" not in fault.text and "SQL" not in fault.text)
        finally:
            event.remove(engine, "before_cursor_execute", break_second)
        with SessionLocal() as db:
            check("B3 失败：第二项故障整批任务和发件箱回滚", db.query(GradeTask).filter_by(homework_id=atomic_hw).count() == 0
                  and all(db.get(HomeworkSubmission, i).status == "pending" for i in atomic_subs))

        parallel_hw, parallel_subs = fixture()
        with ThreadPoolExecutor(max_workers=20) as pool:
            batches = list(pool.map(lambda _: enqueue(parallel_hw), range(20)))
        parallel_id = batches[0]["task_ids"][0]
        with SessionLocal() as db:
            check("C1 边界：20并发数据库唯一幂等", all(b["task_ids"] == [parallel_id] for b in batches)
                  and db.query(GradeTask).filter_by(homework_id=parallel_hw).count() == 1)
        gs.process_task(parallel_id)
        with SessionLocal() as db:
            sub = db.get(HomeworkSubmission, parallel_subs[0]); score, graded_at = sub.ai_score, sub.ai_graded_at
        count = len(calls)
        gs.process_task(parallel_id)
        with SessionLocal() as db:
            sub = db.get(HomeworkSubmission, parallel_subs[0])
            check("C1 边界：重复消息attempts增加而评分和时间不变", task(parallel_id)["attempts"] == 2
                  and sub.ai_score == score and sub.ai_graded_at == graded_at and len(calls) == count)

        stale_hw, stale_subs = fixture()
        stale_id = enqueue(stale_hw)["task_ids"][0]
        with SessionLocal() as db:
            row = db.get(GradeTask, stale_id); snap = json.loads(row.input_json)
            row.status, row.claim_token, row.lease_until, row.execution_count = "running", "old", datetime(2000, 1, 1), 1
            db.commit()
        check("B4 边界：过期运行自动重领", gs.process_task(stale_id) == "succeeded")
        with SessionLocal() as db:
            check("B4 失败：旧租约不能覆盖", gs.finish(db, stale_id, "old", snap, result=(99, "旧结果")) == "lease_lost"
                  and db.get(HomeworkSubmission, stale_subs[0]).ai_score == 70)

        for changed in ("resubmit", "teacher"):
            changing_hw, changing_subs = fixture(); tid = enqueue(changing_hw)["task_ids"][0]
            def racing_model(*args, **kw):
                with SessionLocal() as db:
                    sub = db.get(HomeworkSubmission, changing_subs[0])
                    if changed == "resubmit":
                        sub.answer_text, sub.submitted_at = "新作答", gs.now()
                    else:
                        sub.status, sub.teacher_score = "teacher_graded", 91
                    db.commit()
                return '{"score":30,"feedback":"过期评分"}'
            hs.generate_answer = racing_model
            check("C2 边界：旧结果跳过" + changed, gs.process_task(tid) == "skipped")
            with SessionLocal() as db:
                sub = db.get(HomeworkSubmission, changing_subs[0])
                check("C2 正常：保留新作答或教师分" + changed, sub.ai_score is None and
                      (sub.answer_text == "新作答" if changed == "resubmit" else sub.teacher_score == 91))

        hs.generate_answer = lambda *a, **kw: '{"score":true}'
        dead_hw, dead_subs = fixture(); dead_id = enqueue(dead_hw)["task_ids"][0]
        for index, expected in enumerate(("retrying", "retrying", "dead"), 1):
            if index > 1: due(dead_id)
            start = gs.now(); state = gs.process_task(dead_id); info = task(dead_id)
            check(f"D1 失败：第{index}次失败状态{expected}", state == expected and info["execution_count"] == index
                  and info["attempts"] == index and info["error"] and "score" not in info)
            if index < 3:
                with SessionLocal() as db:
                    row = db.get(GradeTask, dead_id)
                    check(f"D1 边界：第{index}次退避时间", (row.next_attempt_at - start).total_seconds()
                          >= settings.grading_retry_base_seconds * 2 ** (index - 1))
                check(f"D1 边界：未到期不执行{index}", gs.process_task(dead_id) == "deferred")
        with SessionLocal() as db:
            check("D1 失败：不写部分分数", db.get(HomeworkSubmission, dead_subs[0]).ai_score is None)
        try: gs.dispatch(BrokenQueue())
        except ConnectionError: pass
        with SessionLocal() as db:
            check("D1 失败：死信投递失败不假确认", db.get(GradeTask, dead_id).dead_published_at is None)
        gs.dispatch(queue)
        check("D1 正常：死信恢复后补投", dead_id in queue.dead)
        hs.generate_answer = model
        check("D2 正常：授权手动重试202", req("POST", f"/api/teacher/grade-tasks/{dead_id}/retry").status_code == 202)
        check("D2 边界：活跃任务重复重试409", req("POST", f"/api/teacher/grade-tasks/{dead_id}/retry").status_code == 409)
        check("D2 正常：恢复后成功且累计attempts保留", gs.process_task(dead_id) == "succeeded"
              and task(dead_id)["attempts"] == 4 and task(dead_id)["execution_count"] == 1)

        for who, status in ((None, 401), ("student", 403), ("other", 403), ("physics", 403)):
            for method, path in [("POST", f"/api/teacher/homeworks/{hw}/ai-grade"),
                                 ("GET", f"/api/teacher/homeworks/{hw}/grade-tasks"),
                                 ("GET", f"/api/teacher/grade-tasks/{first}"),
                                 ("POST", f"/api/teacher/grade-tasks/{first}/retry")]:
                response = req(method, path, who)
                check(f"E1 失败：{who or '未登录'} {method} {path}", response.status_code == status
                      and "input_json" not in response.text and "answer_text" not in response.text)
        with SessionLocal() as db:
            check("E1 正常：403有审计", db.query(AuditLog).filter_by(status_code=403).count() >= 12)
            before_counts = {table: db.execute(text(f"SELECT count(*) FROM {table}")).scalar() for table in
                             ("users", "homeworks", "homework_submissions", "grade_tasks")}
        for _ in range(2):
            database.run_simple_migrations(); Base.metadata.create_all(engine)
        with SessionLocal() as db:
            check("F1 边界：重复迁移不改变旧数据", all(db.execute(text(f"SELECT count(*) FROM {t}")).scalar() == n
                  for t, n in before_counts.items()) and db.get(HomeworkSubmission, parallel_subs[0]).ai_score == 70)
        # 独立旧库没有任务表；两次升级必须新增表而不改变已有账号、提交与评分。
        old_path = Path(directory) / "old.db"
        with sqlite3.connect(Path(directory) / "test.db") as src, sqlite3.connect(old_path) as dest:
            src.backup(dest)
            dest.execute("DROP TABLE grade_tasks"); dest.commit()
            old_rows = {t: dest.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()
                        for t in ("users", "homeworks", "homework_submissions")}
        old_engine = create_engine(f"sqlite:///{old_path}")
        current_engine = database.engine
        try:
            database.engine = old_engine
            for _ in range(2):
                database.run_simple_migrations(); Base.metadata.create_all(old_engine)
        finally:
            database.engine = current_engine
            old_engine.dispose()
        with sqlite3.connect(old_path) as old:
            check("F1 边界：无任务表旧库升级两次保留账号作答评分", all(old.execute(f"SELECT * FROM {t} ORDER BY id").fetchall() == rows
                  for t, rows in old_rows.items()) and old.execute("SELECT count(*) FROM grade_tasks").fetchone()[0] == 0
                  and old.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
        recover_hw, _ = fixture()
        recover_id = enqueue(recover_hw)["task_ids"][0]
        with SessionLocal() as db:
            row = db.get(GradeTask, recover_id)
            row.status, row.lease_until = "running", datetime(2000, 1, 1)
            db.commit()
        gs.dispatch(queue); recovered_messages = list(queue.messages)
        for _ in range(5): gs.dispatch(queue)
        check("Q2 边界：同一过期租约只确认一条恢复消息", queue.messages == recovered_messages
              and queue.messages.count(recover_id) == 1)
        with SessionLocal() as db:
            row = db.get(GradeTask, recover_id)
            row.lease_until = datetime(2001, 1, 1)
            row.last_published_at = datetime(2000, 1, 1)
            db.commit()
        gs.dispatch(queue)
        check("Q2 边界：后续新租约再次中断仍可补投", queue.messages.count(recover_id) == 2)
        with SessionLocal() as db:
            expected = {t.id for t in db.query(GradeTask).filter(GradeTask.status.in_(["pending", "retrying"]), GradeTask.last_published_at.isnot(None))}
            done_before = gs.serialize(db.get(GradeTask, first))
            running_before = gs.serialize(db.get(GradeTask, recover_id))
            count = gs.recover_pending_deliveries(db)
        with SessionLocal() as db:
            check("Q3 正常：显式恢复只清待执行投递标记", count == len(expected) and count > 0
                  and all(db.get(GradeTask, tid).last_published_at is None for tid in expected)
                  and gs.serialize(db.get(GradeTask, first)) == done_before
                  and gs.serialize(db.get(GradeTask, recover_id)) == running_before)
            check("Q3 边界：重复恢复为0", gs.recover_pending_deliveries(db) == 0)
    engine.dispose()

print(json.dumps({"passed": len(checks), "checks": checks,
                  "timing": {"requests": 20, "p95_seconds": round(p95, 6), "fake_execution_seconds": round(model_cost, 6)},
                  "model": "offline fake; no provider calls", "queue": "memory adapter; real broker separately"}, ensure_ascii=False))
