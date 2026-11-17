#!/usr/bin/env python3
"""第10课检索接口同口径压测：ASGI 进程内直调，轮换合成学生账号。

只用于独立合成库/副本；不写生产库。输出 rps、P95、P99、错误率。
用法：
    BENCH_DB=/path/to/bench.db backend/.venv/bin/python scripts/lesson10_api_bench.py \
        --concurrency 10 --duration 10 --rounds 2
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
os.environ["DATABASE_URL"] = f"sqlite:///{os.environ['BENCH_DB']}"
os.environ.setdefault("JWT_SECRET_KEY", "bench-only-secret-000000000000000000")
os.environ.setdefault("DEEPSEEK_API_KEY", "")
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402
import main as application  # noqa: E402
import services  # noqa: E402

# 压测只关心检索路径；限次检查仍执行，但不因 40 次/日提前拒绝。
services.AI_DAILY_LIMIT = 10**9

QUESTION = "夹角 余弦 向量 公式 坐标"
PASSWORD = "Lesson10!demo"


async def login_pool(client, accounts):
    tokens = []
    for identifier in accounts:
        response = await client.post("/api/auth/login", json={"identifier": identifier, "password": PASSWORD})
        if response.status_code == 200:
            tokens.append(response.json()["access_token"])
    return tokens


async def worker(client, index, tokens, deadline, latencies, errors):
    while time.perf_counter() < deadline:
        token = tokens[index % len(tokens)]
        index += 1
        headers = {"Authorization": f"Bearer {token}"}
        started = time.perf_counter()
        try:
            response = await client.post("/api/student/ai-question",
                                         json={"question": QUESTION, "subject": "math"}, headers=headers)
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code == 200:
                latencies.append(elapsed)
            else:
                errors.append(response.status_code)
        except Exception as exc:  # 连接错误等
            errors.append(type(exc).__name__)


async def one_round(accounts, concurrency, duration):
    transport = httpx.ASGITransport(app=application.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://bench", timeout=30) as client:
        tokens = await login_pool(client, accounts)
        if not tokens:
            raise SystemExit("没有可用账号令牌")
        latencies, errors = [], []
        deadline = time.perf_counter() + duration
        started = time.perf_counter()
        await asyncio.gather(*(worker(client, i, tokens, deadline, latencies, errors)
                               for i in range(concurrency)))
        wall = time.perf_counter() - started
    latencies.sort()
    p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else float("nan")
    p99 = latencies[int(0.99 * (len(latencies) - 1))] if latencies else float("nan")
    return {
        "concurrency": concurrency,
        "rps": round(len(latencies) / wall, 2) if wall else 0,
        "p50_ms": round(statistics.median(latencies), 2) if latencies else None,
        "p95_ms": round(p95, 2) if latencies else None,
        "p99_ms": round(p99, 2) if latencies else None,
        "mean_ms": round(statistics.fmean(latencies), 2) if latencies else None,
        "requests": len(latencies),
        "errors": len(errors),
        "error_rate": round(len(errors) / max(1, len(latencies) + len(errors)), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, nargs="+", default=[3, 10])
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--accounts", type=int, default=60)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    accounts = [f"S10P{i:02d}" for i in range(1, args.accounts + 1)]
    results = []
    for concurrency in args.concurrency:
        for round_no in range(1, args.rounds + 1):
            row = asyncio.run(one_round(accounts, concurrency, args.duration))
            row["round"] = round_no
            results.append(row)
            print(json.dumps(row, ensure_ascii=False))
    if args.json:
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
