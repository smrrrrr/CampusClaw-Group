"""SEC-07 审计字段迁移脚本。

为 audit_logs 表新增 action、object_id、skill_id、duration_ms、tokens 列；
为 mcp_tool_calls 表新增 skill_id、duration_ms、tokens 列。
使用 SQLite ALTER TABLE ADD COLUMN，全部 nullable，不影响已有数据。
可重复执行：已存在的列跳过。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text  # noqa: E402

from database import engine  # noqa: E402


AUDIT_COLUMNS = [
    ("action", "VARCHAR(64)"),
    ("object_id", "VARCHAR(128)"),
    ("skill_id", "VARCHAR(64)"),
    ("duration_ms", "INTEGER"),
    ("tokens", "INTEGER"),
]

MCP_COLUMNS = [
    ("skill_id", "VARCHAR(64)"),
    ("duration_ms", "INTEGER"),
    ("tokens", "INTEGER"),
]


def add_columns(conn, table: str, columns: list[tuple[str, str]]) -> list[str]:
    info = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    if not info:
        return []  # 表不存在（全新库由 create_all 创建，无需迁移）
    existing = {row[1] for row in info}
    added = []
    for col, ddl in columns:
        if col not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
            added.append(col)
    if added:
        conn.commit()
    return added


def main() -> int:
    with engine.connect() as conn:
        audit_added = add_columns(conn, "audit_logs", AUDIT_COLUMNS)
        mcp_added = add_columns(conn, "mcp_tool_calls", MCP_COLUMNS)
    print(f"audit_logs 新增列: {audit_added or '(无)'}")
    print(f"mcp_tool_calls 新增列: {mcp_added or '(无)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
