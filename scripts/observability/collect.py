"""第10课只读观测采集器。

把**已经记录**的审计、任务与访问日志转成 Prometheus 指标；不修改业务库，不读取正文、
令牌或会话内容。数据源缺失时输出“未接入”，不填 0 冒充已观测。

用法：
    python scripts/observability/collect.py --once              # 打印一次指标
    python scripts/observability/collect.py --serve --port 9101 # 供 Prometheus 抓取
    python scripts/observability/collect.py --window 2026-11-14T07:00:00Z 2026-11-14T08:00:00Z
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKILLS = ("tutor_guidance", "homework_grading", "mistake_explanation")
TRACKED_ENDPOINTS = {
    "/api/student/ai-question": "tutor_guidance",
    "/api/student/conversations/:id/chat": "tutor_guidance",
    "/api/student/mistakes/:id/explain": "mistake_explanation",
    "/api/teacher/homeworks/:id/ai-grade": "homework_grading",
    "/api/teacher/grade-tasks/:id": "homework_grading",
}
BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_ID_SEGMENT = re.compile(r"^(?:\d+|[0-9a-fA-F-]{8,})$")


def normalize_path(path: str) -> str:
    parts = [":id" if _ID_SEGMENT.match(part) else part for part in path.split("/")]
    return "/".join(parts)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def db_path_from_env() -> Path:
    raw = os.environ.get("DATABASE_URL", "")
    if raw.startswith("sqlite:///"):
        candidate = raw[len("sqlite:///"):]
        return Path(candidate) if candidate.startswith("/") else (Path.cwd() / candidate)
    return ROOT / "data/campusclaw.db"


def open_readonly(path: Path):
    if not path.exists():
        return None
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)


def table_exists(conn, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def max_value(conn, sql: str, params=()):
    return conn.execute(sql, params).fetchone()[0]


def collect_db(path: Path, start: datetime | None, end: datetime | None):
    """返回 {skill: {status: count}}、任务状态与执行次数。只读短事务。"""
    result = {skill: {} for skill in SKILLS}
    grading_states = {}
    executions = 0
    available = {skill: 0 for skill in SKILLS}
    conn = open_readonly(path)
    if conn is None:
        return result, grading_states, executions, available, "数据库不可读"

    def in_window(column: str) -> tuple[str, tuple]:
        clauses, params = [], ()
        if start:
            clauses.append(f"{column} >= ?")
            params += (start.replace(tzinfo=None).isoformat(sep=" "),)
        if end:
            clauses.append(f"{column} < ?")
            params += (end.replace(tzinfo=None).isoformat(sep=" "),)
        return (" AND " + " AND ".join(clauses) if clauses else ""), params

    try:
        if table_exists(conn, "ai_question_logs"):
            where, params = in_window("created_at")
            total = max_value(conn, f"SELECT COUNT(*) FROM ai_question_logs WHERE 1=1{where}", params)
            answered = max_value(conn, f"SELECT COUNT(*) FROM ai_question_logs WHERE answer IS NOT NULL{where}", params)
            result["tutor_guidance"] = {"succeeded": answered, "unknown": total - answered}
            available["tutor_guidance"] = 1

        if table_exists(conn, "grade_tasks"):
            where, params = in_window("created_at")
            rows = conn.execute(f"SELECT status, COUNT(*) FROM grade_tasks WHERE 1=1{where} GROUP BY status", params).fetchall()
            grading_states = {status: count for status, count in rows}
            executions = max_value(conn, f"SELECT COALESCE(SUM(execution_count),0) FROM grade_tasks WHERE 1=1{where}", params)
            result["homework_grading"] = {
                "succeeded": grading_states.get("succeeded", 0),
                "failed": grading_states.get("dead", 0),
                "skipped": grading_states.get("skipped", 0),
                "unknown": sum(grading_states.get(state, 0) for state in ("pending", "running", "retrying")),
            }
            available["homework_grading"] = 1

        if table_exists(conn, "audit_logs"):
            where, params = in_window("created_at")
            rows = conn.execute(
                f"SELECT request_path, status_code, COUNT(*) FROM audit_logs WHERE 1=1{where} GROUP BY request_path, status_code",
                params,
            ).fetchall()
            for raw_path, status, count in rows:
                if status != 403:
                    continue
                path_norm = normalize_path(raw_path)
                skill = TRACKED_ENDPOINTS.get(path_norm)
                if skill:
                    result[skill]["denied"] = result[skill].get("denied", 0) + count
        # mistake_explanation 目前没有成功/失败持久事件，只保留 denied（若审计有）。
        if result["mistake_explanation"].get("denied"):
            available["mistake_explanation"] = 1
    except sqlite3.Error as exc:
        return result, grading_states, executions, available, f"读取失败：{type(exc).__name__}"
    finally:
        conn.close()
    return result, grading_states, executions, available, ""


def parse_access_log(path: Path, start: datetime | None, end: datetime | None):
    counters, histograms = {}, {endpoint: {le: 0 for le in BUCKETS} for endpoint in TRACKED_ENDPOINTS}
    totals = {endpoint: 0 for endpoint in TRACKED_ENDPOINTS}
    sums = {endpoint: 0.0 for endpoint in TRACKED_ENDPOINTS}
    scanned = 0
    if not path or not path.exists():
        return counters, histograms, totals, sums, scanned, "日志不可读"
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            scanned += 1
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("module") != "access":
                continue
            timestamp = entry.get("ts")
            if start or end:
                try:
                    moment = parse_time(timestamp)
                except (TypeError, ValueError):
                    continue
                if start and moment < start:
                    continue
                if end and moment >= end:
                    continue
            path_norm = normalize_path(str(entry.get("path", "")))
            status = int(entry.get("status", 0) or 0)
            key = (path_norm, status)
            counters[key] = counters.get(key, 0) + 1
            if path_norm in TRACKED_ENDPOINTS:
                totals[path_norm] += 1
                duration = float(entry.get("duration_ms", 0) or 0) / 1000.0
                sums[path_norm] += duration
                for le in BUCKETS:
                    if duration <= le:
                        histograms[path_norm][le] += 1
    return counters, histograms, totals, sums, scanned, ""


def render_metrics(db_data, grading_states, executions, available, access, db_error, log_error, scanned):
    counters, histograms, totals, sums, _, _ = access
    lines = []

    def emit(name, help_text, kind, series):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {kind}")
        for labels, value in series:
            lines.append(f"{name}{labels} {value}")

    skill_series = []
    for skill in SKILLS:
        for status, count in sorted(db_data[skill].items()):
            labels = f'{{skill="{skill}",status="{status}"}}'
            skill_series.append((labels, count))
    emit("skill_invocations_total", "已实际记录的技能事件；缺失来源不在其中", "counter", skill_series)
    emit("skill_events_available", "1=有持久事件来源；0=未接入，不能按 0 解释", "gauge",
         [(f'{{skill="{skill}"}}', available[skill]) for skill in SKILLS])
    emit("grading_tasks", "GradeTask 当前状态分布", "gauge",
         [(f'{{status="{status}"}}', count) for status, count in sorted(grading_states.items())])
    emit("grading_executions_total", "GradeTask.execution_count 累计模型执行次数", "counter", [("", executions)])

    emit("http_requests_total", "按规范化路径与状态码的请求数；SSE 为响应开始即计数", "counter",
         [(f'{{path="{path}",status="{status}"}}', count) for (path, status), count in sorted(counters.items())])
    if histograms:
        lines.append("# HELP http_request_duration_seconds 访问日志记录的耗时；SSE 端点仅为首包耗时，不能当完整生成耗时")
        lines.append("# TYPE http_request_duration_seconds histogram")
    for endpoint, buckets in histograms.items():
        for le in BUCKETS:
            lines.append(f'http_request_duration_seconds_bucket{{path="{endpoint}",le="{le}"}} {buckets[le]}')
        lines.append(f'http_request_duration_seconds_bucket{{path="{endpoint}",le="+Inf"}} {totals[endpoint]}')
        lines.append(f'http_request_duration_seconds_sum{{path="{endpoint}"}} {round(sums[endpoint], 6)}')
        lines.append(f'http_request_duration_seconds_count{{path="{endpoint}"}} {totals[endpoint]}')
    emit("collector_last_scan_timestamp_seconds", "最近一次扫描时间", "gauge",
         [("", int(datetime.now(timezone.utc).timestamp()))])
    lines.append(f'# HELP collector_status 1=数据源可读；0=存在不可读来源')
    lines.append(f"# TYPE collector_status gauge")
    lines.append(f'collector_status{{source="database"}} {0 if db_error else 1}')
    lines.append(f'collector_status{{source="access_log"}} {0 if log_error else 1}')
    lines.append(f"collector_log_lines_scanned_total {scanned}")
    if db_error:
        lines.append(f'# database_blocked "{db_error}"')
    if log_error:
        lines.append(f'# access_log_blocked "{log_error}"')
    return "\n".join(lines) + "\n"


def window_report(db_data, start, end):
    report = {}
    for skill in SKILLS:
        counts = db_data[skill]
        succeeded, failed = counts.get("succeeded", 0), counts.get("failed", 0)
        rate = round(failed / (succeeded + failed), 4) if (succeeded + failed) else None
        report[skill] = {**counts, "failure_rate": rate,
                         "formula": "failed/(succeeded+failed)" if rate is not None else "无样本"}
    return {"window": {"start": start.isoformat(), "end": end.isoformat()},
            "utc_now": datetime.now(timezone.utc).isoformat(), "skills": report}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=db_path_from_env())
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=9101)
    parser.add_argument("--window", nargs=2, metavar=("START", "END"))
    args = parser.parse_args()
    log_path = args.log or (Path(os.environ["OBS_LOG_FILE"]) if os.environ.get("OBS_LOG_FILE") else None)

    if args.window:
        start, end = (parse_time(value) for value in args.window)
        db_data, _, _, _, error = collect_db(args.db, start, end)
        print(json.dumps({**window_report(db_data, start, end), "error": error}, ensure_ascii=False, indent=2))
        return 0

    def snapshot():
        db_data, states, executions, available, db_error = collect_db(args.db, None, None)
        access = parse_access_log(log_path, None, None)
        return render_metrics(db_data, states, executions, available, access, db_error, access[5], access[4])

    if args.serve:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in ("/metrics", "/"):
                    self.send_response(404)
                    self.end_headers()
                    return
                body = snapshot().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                return

        HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
        return 0

    print(snapshot(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
