#!/usr/bin/env python3
"""第10课三接口压测的无依赖执行器（k6 不可用时的等价实现）。

只发真实 HTTP 请求，不连接模型供应商；假模型由服务端配置决定。
令牌与任务号只从环境变量读取，输出不含令牌、提问正文或响应正文。

用法：
    python apitest/load/lesson10.py --scenario query --concurrency 10 --duration 60
环境变量：BASE_URL、TEACHER_TOKEN、STUDENT_TOKEN、HOMEWORK_ID、GRADE_TASK_ID、QUESTION。
"""

import argparse
import itertools
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

_token_cycle = None
_token_lock = threading.Lock()


def next_token(fallback):
    """按 STUDENT_TOKENS_FILE 轮换学生令牌，避免单账号撞每日 40 次配额。"""
    global _token_cycle
    with _token_lock:
        if _token_cycle is None:
            raw = os.environ.get("STUDENT_TOKENS_FILE", "")
            tokens = [line.strip() for line in open(raw, encoding="utf-8") if line.strip()] if raw else []
            _token_cycle = itertools.cycle(tokens or [fallback])
        return next(_token_cycle)


def request_once(scenario, base, headers, payload, results, lock, deadline):
    while time.monotonic() < deadline:
        url, method, body, expected = endpoint(scenario, base, payload)
        request_headers = dict(headers)
        request_headers["Authorization"] = f"Bearer {next_token(headers['Authorization'].split(' ', 1)[1])}"
        started = time.perf_counter()
        status, error = 0, None
        try:
            req = urllib.request.Request(url, data=body, method=method, headers=request_headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                status = response.status
                response.read(1)
        except urllib.error.HTTPError as exc:
            status = exc.code
        except Exception as exc:  # 连接失败/超时按错误请求记录，不中断整轮
            error = type(exc).__name__
        elapsed = (time.perf_counter() - started) * 1000
        with lock:
            results.append({"status": status, "ms": elapsed, "error": error, "expected": expected})


def endpoint(scenario, base, payload):
    if scenario == "submit":
        return (f"{base}/api/teacher/homeworks/{payload['homework']}/ai-grade", "POST", b"{}", 202)
    if scenario == "retrieve":
        body = json.dumps({"question": payload["question"], "subject": "math"}).encode()
        return (f"{base}/api/student/ai-question", "POST", body, 200)
    return (f"{base}/api/teacher/grade-tasks/{payload['task']}", "GET", None, 200)


def percentile(values, ratio):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(ratio * (len(ordered) - 1)))))
    return round(ordered[index], 2)


def run(scenario, concurrency, duration, warmup, payload, base, headers):
    for phase, seconds in (("warmup", warmup), ("sample", duration)):
        results, lock = [], threading.Lock()
        deadline = time.monotonic() + seconds
        threads = [threading.Thread(target=request_once, args=(scenario, base, headers, payload, results, lock, deadline))
                   for _ in range(concurrency)]
        started = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.perf_counter() - started
        if phase == "warmup":
            continue
        accepted = [r for r in results if r["status"] == r["expected"]]
        rejected = [r for r in results if r["status"] == 429]
        failed = [r for r in results if r["status"] not in (r["expected"], 429)]
        durations = [r["ms"] for r in accepted]
        return {
            "scenario": scenario,
            "concurrency": concurrency,
            "duration_seconds": round(elapsed, 2),
            "requests": len(results),
            "accepted": len(accepted),
            "business_rejected_429": len(rejected),
            "failed": len(failed),
            "throughput_rps": round(len(accepted) / elapsed, 2) if elapsed else 0,
            "error_rate": round(len(failed) / len(results), 4) if results else None,
            "p95_ms": percentile(durations, 0.95),
            "mean_ms": round(statistics.fmean(durations), 2) if durations else None,
            "status_counts": {str(status): sum(1 for r in results if r["status"] == status)
                              for status in sorted({r["status"] for r in results})},
        }
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["submit", "query", "retrieve"], default="query")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--base", default=os.environ.get("BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    token = os.environ.get("STUDENT_TOKEN", "") if args.scenario == "retrieve" else os.environ.get("TEACHER_TOKEN", "")
    if not token:
        raise SystemExit("缺少令牌：请设置 TEACHER_TOKEN 或 STUDENT_TOKEN；脚本不会打印令牌")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "homework": os.environ.get("HOMEWORK_ID", "1"),
        "task": os.environ.get("GRADE_TASK_ID", "1"),
        "question": os.environ.get("QUESTION", "请提示这道题的思路"),
    }
    result = run(args.scenario, args.concurrency, args.duration, args.warmup, payload, args.base, headers)
    result["utc"] = datetime.now(timezone.utc).isoformat()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
