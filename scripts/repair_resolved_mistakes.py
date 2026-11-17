"""限定修复已终评及格却残留的作业错题，默认只预览；不改作答或成绩。"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True, help="明确指定要检查的现有SQLite文件")
    parser.add_argument("--apply", action="store_true", help="先备份再删除已确认的派生错题")
    args = parser.parse_args()
    target = args.database.resolve(strict=True)
    os.environ["DATABASE_URL"] = "sqlite:///" + target.as_posix()
    sys.path.insert(0, str(ROOT / "backend"))
    from database import SessionLocal, engine
    from homework_service import resolved_homework_mistakes
    from sqlalchemy import text
    backup = None
    if args.apply:
        backup = target.with_name(f"before-resolved-mistakes-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6]}.db")
        with sqlite3.connect(target) as source, sqlite3.connect(backup) as dest:
            source.backup(dest)
            assert dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with SessionLocal() as db:
        if args.apply:
            db.execute(text("BEGIN IMMEDIATE"))
        rows = resolved_homework_mistakes(db)
        ids = [note.id for note in rows]
        if args.apply:
            for note in rows:
                db.delete(note)
            db.commit()
    engine.dispose()
    print(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "mode": "apply" if args.apply else "dry-run",
                      "matched_ids": ids, "matched_count": len(ids), "removed_count": len(ids) if args.apply else 0,
                      "backup": backup.name if backup else None, "submission_and_scores_modified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
