"""审计日志字段转义与截断（change 2026-11-16-harden-audit-field-bounds）。

覆盖三类：
  正常：正常值不变、数值字段不受影响
  失败：None 不被误转成字符串
  边界：超长截断到列宽、控制字符替换为空格、常量与模型列宽一致

只写临时 SQLite，不连真实库、不写真实审计数据。
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


with tempfile.TemporaryDirectory(prefix="audit-bounds-", ignore_cleanup_errors=True) as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'audit.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
    sys.path.insert(0, str(BACKEND))

    from database import Base, SessionLocal, engine  # noqa: E402
    from models import AuditLog  # noqa: E402
    from services import _AUDIT_TEXT_LIMITS, write_audit_log  # noqa: E402

    Base.metadata.create_all(engine)

    def write_and_read(**kwargs):
        base = dict(
            user_id=7, role="student", request_path="/api/materials/1",
            method="GET", status_code=403, ip_address="127.0.0.1",
        )
        base.update(kwargs)
        with SessionLocal() as db:
            write_audit_log(db, **base)
            row = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
            # 取出后转成普通值，避免 session 关闭后属性过期
            return {c: getattr(row, c) for c in (
                "user_id", "role", "subject", "class_id", "request_path", "method",
                "status_code", "ip_address", "action", "object_id", "skill_id",
                "duration_ms", "tokens",
            )}

    # 边界：超长 object_id 截断到 128
    long_id = "a" * 500
    row = write_and_read(object_id=long_id)
    check("超长 object_id 截断到 128", len(row["object_id"]) == 128)
    check("截断后为原串前 128 字符", row["object_id"] == long_id[:128])
    check("截断不追加省略标记", "…" not in row["object_id"] and "trunc" not in row["object_id"].lower())

    # 边界：控制字符替换为空格
    row = write_and_read(object_id="a\nb\tc\x00d")
    check("控制字符被替换为空格", row["object_id"] == "a b c d")
    check("落库值不含控制字符",
          all(ord(ch) >= 32 and ord(ch) != 127 for ch in row["object_id"]))

    # 边界：其他文本字段同样受限
    row = write_and_read(action="x" * 200, skill_id="y" * 200, request_path="z" * 900,
                         ip_address="1" * 200, subject="s" * 200)
    check("action 截断到 64", len(row["action"]) == 64)
    check("skill_id 截断到 64", len(row["skill_id"]) == 64)
    check("request_path 截断到 256", len(row["request_path"]) == 256)
    check("ip_address 截断到 64", len(row["ip_address"]) == 64)
    check("subject 截断到 32", len(row["subject"]) == 32)

    # 正常：正常值不变
    row = write_and_read(object_id="42", action="skill.invoke", ip_address="10.0.0.1")
    check("正常 object_id 不变", row["object_id"] == "42")
    check("正常 action 不变", row["action"] == "skill.invoke")
    check("正常 ip_address 不变", row["ip_address"] == "10.0.0.1")

    # 正常：中文与常见标点不被改动
    row = write_and_read(object_id="会话/12:abc-def_3")
    check("中文与标点不被改动", row["object_id"] == "会话/12:abc-def_3")

    # 失败路径：None 保持 None
    row = write_and_read(object_id=None, skill_id=None, subject=None, ip_address=None)
    check("None 的 object_id 仍为 None", row["object_id"] is None)
    check("None 的 skill_id 仍为 None", row["skill_id"] is None)
    check("None 不被转成字符串 None", row["skill_id"] != "None")
    check("None 的 ip_address 仍为 None", row["ip_address"] is None)

    # 正常：数值字段不受影响
    row = write_and_read(user_id=7, status_code=403, class_id=101, duration_ms=12, tokens=99)
    check("user_id 保持整数", row["user_id"] == 7)
    check("status_code 保持整数", row["status_code"] == 403)
    check("class_id 保持整数", row["class_id"] == 101)
    check("duration_ms 保持整数", row["duration_ms"] == 12)
    check("tokens 保持整数", row["tokens"] == 99)

    # 边界：常量与模型列宽同源，防止漂移
    columns = AuditLog.__table__.columns
    mismatched = []
    for field, limit in _AUDIT_TEXT_LIMITS.items():
        col = columns.get(field)
        actual = getattr(col.type, "length", None) if col is not None else None
        if actual != limit:
            mismatched.append(f"{field}: 常量={limit} 模型={actual}")
    check("_AUDIT_TEXT_LIMITS 与模型列宽一致", not mismatched)
    if mismatched:
        for item in mismatched:
            print("      差异:", item)

passed = sum(1 for _, p in checks if p)
total = len(checks)
print(f"\n结果：{passed}/{total} 通过")
sys.exit(0 if passed == total else 1)