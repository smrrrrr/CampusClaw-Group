#!/usr/bin/env python3
"""第10课索引 A/B 基准：同一 SQL、同一合成数据，只切换索引。

测量的是 SQLite 查询耗时，不是 API P95，也不包含应用层相似度计算。
用法：backend/.venv/bin/python scripts/lesson10_index_bench.py --chunks 50000 --rounds 200 --json PATH
"""

import argparse
import json
import os
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

QUERY = """
SELECT id, material_id, chunk_index
FROM material_chunks
WHERE class_id = ? AND material_id IN (?, ?, ?)
ORDER BY material_id, chunk_index
"""

OLD = "CREATE INDEX ix_old ON material_chunks(class_id, material_id)"
NEW = "CREATE INDEX ix_new ON material_chunks(class_id, material_id, chunk_index)"


def build(path: Path, chunks: int):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("CREATE TABLE material_chunks (id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL, "
                 "material_id INTEGER NOT NULL, chunk_index INTEGER NOT NULL, content TEXT)")
    rows = []
    per_material = 100
    for index in range(chunks):
        rows.append((101 + (index // 20000), 1 + (index // per_material), index % per_material, "x"))
    conn.executemany("INSERT INTO material_chunks (class_id, material_id, chunk_index, content) VALUES (?,?,?,?)", rows)
    conn.commit()
    return conn


def measure(conn, rounds: int):
    timings = []
    for _ in range(rounds):
        started = time.perf_counter()
        conn.execute(QUERY, (101, 1, 2, 3)).fetchall()
        timings.append((time.perf_counter() - started) * 1000)
    return {"median_ms": round(statistics.median(timings), 3),
            "p95_ms": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 3),
            "mean_ms": round(statistics.fmean(timings), 3)}


def plan(conn):
    return [row[-1] for row in conn.execute("EXPLAIN QUERY PLAN " + QUERY, (101, 1, 2, 3))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", type=int, default=50000)
    parser.add_argument("--rounds", type=int, default=200)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="lesson10-bench-") as directory:
        conn = build(Path(directory) / "bench.db", args.chunks)
        conn.execute(OLD)
        conn.execute("ANALYZE")
        before = measure(conn, args.rounds)
        before_plan = plan(conn)
        conn.execute("DROP INDEX ix_old")
        conn.execute(NEW)
        conn.execute("ANALYZE")
        after = measure(conn, args.rounds)
        after_plan = plan(conn)
        conn.close()
    result = {"chunks": args.chunks, "rounds": args.rounds,
              "before": before, "before_plan": before_plan,
              "after": after, "after_plan": after_plan,
              "delta_p95_percent": round((after["p95_ms"] - before["p95_ms"]) / before["p95_ms"] * 100, 2),
              "scope": "SQL only; excludes application similarity scoring and HTTP"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
