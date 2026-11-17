#!/usr/bin/env python3
"""第10课运行链路走查：学生提交 → 教师触发初批 → 任务三态 → 本人结果 → 跨班 404。

只发真实 HTTP 请求；令牌只在本进程使用，输出不含令牌、正文或私有评分。
用法：
    python scripts/lesson10_smoke.py --base http://127.0.0.1:8086 --db data/campusclaw.db
"""

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "Lesson10!demo"


def call(base, method, path, token=None, body=None, csrf=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        status = exc.code
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    try:
        parsed = json.loads(payload or b"{}")
    except ValueError:
        parsed = {"raw_bytes": len(payload)}
    return status, parsed, elapsed


def login(base, identifier):
    status, payload, _ = call(base, "POST", "/api/auth/login",
                              body={"identifier": identifier, "password": PASSWORD})
    assert status == 200, f"登录失败 {identifier}: {status} {payload}"
    return payload["access_token"]


def material_ids(db, class_id):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return [row[0] for row in conn.execute("SELECT id FROM materials WHERE class_id=?", (class_id,))]
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8086")
    parser.add_argument("--db", type=Path, default=ROOT / "data/campusclaw.db")
    parser.add_argument("--poll-seconds", type=int, default=40)
    args = parser.parse_args()

    teacher = login(args.base, "T10A")
    student = login(args.base, "S10A")
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    homework_id = conn.execute("SELECT id FROM homeworks WHERE class_id=201 ORDER BY id DESC LIMIT 1").fetchone()[0]
    submission_id = conn.execute("SELECT id FROM homework_submissions WHERE homework_id=? ORDER BY id DESC LIMIT 1",
                                 (homework_id,)).fetchone()[0]
    conn.close()

    steps = []
    status, payload, ms = call(args.base, "POST", f"/api/student/homeworks/{homework_id}/submit", student,
                               body={"answer_text": "1+1=2"})
    steps.append({"step": "学生提交", "status": status, "expected": 200, "ms": ms,
                  "submission_id": payload.get("id")})
    assert status == 200, payload
    submission_id = payload.get("id") or submission_id

    status, payload, ms = call(args.base, "POST", f"/api/teacher/homeworks/{homework_id}/ai-grade", teacher)
    steps.append({"step": "教师触发初批", "status": status, "expected": 202, "ms": ms,
                  "task_ids": payload.get("task_ids")})
    assert status == 202, payload
    task_ids = payload.get("task_ids") or []
    assert task_ids, payload

    seen, deadline = [], time.time() + args.poll_seconds
    while time.time() < deadline:
        status, payload, ms = call(args.base, "GET", f"/api/teacher/grade-tasks/{task_ids[0]}", teacher)
        state = payload.get("status")
        if not seen or seen[-1] != state:
            seen.append(state)
        if state in ("succeeded", "dead", "skipped"):
            break
        time.sleep(1)
    steps.append({"step": "任务状态", "seen": seen, "final": payload.get("status"), "exit": payload.get("error")})

    status, payload, ms = call(args.base, "GET", f"/api/student/submissions/{submission_id}", student)
    steps.append({"step": "学生查本人结果", "status": status, "expected": 200, "ms": ms,
                  "teacher_score": payload.get("teacher_score")})

    other = material_ids(args.db, 202)
    own = material_ids(args.db, 201)
    cross = []
    for material_id in other:
        status, payload, ms = call(args.base, "GET", f"/api/materials/{material_id}/download", student)
        cross.append({"material_id": material_id, "status": status, "detail": payload.get("detail")})
    own_results = []
    for material_id in own:
        status, payload, ms = call(args.base, "GET", f"/api/materials/{material_id}/download", student)
        own_results.append({"material_id": material_id, "status": status})
    steps.append({"step": "跨班/本班资料", "cross": cross, "own": own_results})

    print(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "base": args.base, "steps": steps},
                     ensure_ascii=False, indent=2))
    ok = (steps[0]["status"] == 200 and steps[1]["status"] == 202 and steps[2]["final"] in ("succeeded", "dead", "skipped")
          and steps[3]["status"] == 200 and all(item["status"] == 404 for item in cross))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
