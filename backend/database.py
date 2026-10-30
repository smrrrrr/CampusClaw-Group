"""数据库引擎与会话管理。

按存储环境选择 SQLite 日志模式：原生磁盘使用 WAL；
Windows Docker 共享目录使用 DELETE，避免跨文件系统共享内存异常。
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False, "timeout": 15} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_simple_migrations() -> None:
    """轻量列迁移（dev 用）：检测 materials 骨架表并重建为完整业务表。

    add-class-data-isolation 创建了 materials 骨架表（仅 id/class_id/created_at），
    add-material-upload 需扩展为完整业务表。SQLite 的 ALTER TABLE ADD COLUMN 无法
    添加带外键约束的列且无法添加联合索引，骨架表无业务数据，安全 drop 后由
    create_all 重建为最新结构。
    """
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(materials)"))
        col_names = {row[1] for row in result}
        # 骨架表缺少 filename 列 → drop 重建
        if col_names and "filename" not in col_names:
            conn.execute(text("DROP TABLE IF EXISTS materials"))
            conn.commit()
        elif col_names and "source_sha256" not in col_names:
            conn.execute(text("ALTER TABLE materials ADD COLUMN source_sha256 VARCHAR(64)"))
            conn.commit()

        # conversations 表若为旧结构（缺 context 列）则 ALTER 增列
        tinfo = conn.execute(text("PRAGMA table_info(conversations)")).fetchall()
        if tinfo:
            cols = {row[1] for row in tinfo}
            if "context" not in cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN context TEXT"))
                conn.commit()

        # users 表增列：subject（教师学科）、homeroom_class_id（班主任班级）
        uinfo = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if uinfo:
            ucols = {row[1] for row in uinfo}
            if "subject" not in ucols:
                conn.execute(text("ALTER TABLE users ADD COLUMN subject VARCHAR(32)"))
            if "homeroom_class_id" not in ucols:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN homeroom_class_id INTEGER")
                )
            if "subject" not in ucols or "homeroom_class_id" not in ucols:
                conn.commit()

        # audit_logs 表增列：subject、class_id（教研隔离审计上下文）
        ainfo = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
        if ainfo:
            acols = {row[1] for row in ainfo}
            if "subject" not in acols:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN subject VARCHAR(32)"))
            if "class_id" not in acols:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN class_id INTEGER"))
            if "subject" not in acols or "class_id" not in acols:
                conn.commit()

        # 保留旧配置，解除 class_id 单列唯一，改为每班/学科/教师独立。
        cfg_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(agent_configs)"))}
        if cfg_cols and "subject" not in cfg_cols:
            conn.execute(text("""CREATE TABLE IF NOT EXISTS agent_configs_scoped (
                id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id),
                subject VARCHAR(32) NOT NULL, teacher_id INTEGER NOT NULL REFERENCES users(id),
                system_prompt TEXT, tutor_enabled BOOLEAN NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_agent_class_subject_teacher UNIQUE(class_id, subject, teacher_id))"""))
            conn.execute(text("DELETE FROM agent_configs_scoped"))
            conn.execute(text("""INSERT INTO agent_configs_scoped
                (id,class_id,subject,teacher_id,system_prompt,tutor_enabled,updated_at)
                SELECT a.id,a.class_id,COALESCE(NULLIF(u.subject,''),'math'),a.teacher_id,
                       a.system_prompt,a.tutor_enabled,a.updated_at
                FROM agent_configs a LEFT JOIN users u ON u.id=a.teacher_id"""))
            conn.execute(text("DROP TABLE agent_configs"))
            conn.execute(text("ALTER TABLE agent_configs_scoped RENAME TO agent_configs"))
            conn.commit()
        convo_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(conversations)"))}
        if convo_cols:
            if "subject" not in convo_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN subject VARCHAR(32) NOT NULL DEFAULT 'math'"))
            if "teacher_id" not in convo_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN teacher_id INTEGER REFERENCES users(id)"))
            conn.commit()

        # homeworks 骨架表增列（add-homework-grading）
        hw_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(homeworks)"))}
        if hw_cols:
            if "subject" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN subject VARCHAR(32) NOT NULL DEFAULT 'math'"))
            if "teacher_id" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN teacher_id INTEGER REFERENCES users(id)"))
            if "title" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT ''"))
            if "content_json" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN content_json TEXT NOT NULL DEFAULT ''"))
            if "due_at" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN due_at DATETIME"))
            if "status" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'draft'"))
            if "updated_at" not in hw_cols:
                conn.execute(text("ALTER TABLE homeworks ADD COLUMN updated_at DATETIME"))
            conn.commit()

        # homework_submissions 骨架表增列
        hws_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(homework_submissions)"))}
        if hws_cols:
            if "homework_id" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN homework_id INTEGER REFERENCES homeworks(id)"))
            if "answer_text" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN answer_text TEXT NOT NULL DEFAULT ''"))
            if "submitted_at" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN submitted_at DATETIME"))
            if "ai_score" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN ai_score INTEGER"))
            if "ai_feedback" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN ai_feedback TEXT"))
            if "ai_graded_at" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN ai_graded_at DATETIME"))
            if "teacher_score" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN teacher_score INTEGER"))
            if "teacher_feedback" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN teacher_feedback TEXT"))
            if "teacher_graded_at" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN teacher_graded_at DATETIME"))
            if "status" not in hws_cols:
                conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"))
            conn.commit()

        # mistake_notes 骨架表增列
        mn_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(mistake_notes)"))}
        if mn_cols:
            if "subject" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN subject VARCHAR(32) NOT NULL DEFAULT 'math'"))
            if "homework_id" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN homework_id INTEGER REFERENCES homeworks(id)"))
            if "question_stem" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN question_stem TEXT NOT NULL DEFAULT ''"))
            if "student_answer" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN student_answer TEXT"))
            if "reason" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN reason TEXT"))
            if "mastered" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN mastered INTEGER NOT NULL DEFAULT 0"))
            if "mastered_at" not in mn_cols:
                conn.execute(text("ALTER TABLE mistake_notes ADD COLUMN mastered_at DATETIME"))
            conn.commit()


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """仅接受配置白名单中的日志模式；回滚日志采用 FULL 同步。"""
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"PRAGMA journal_mode={settings.sqlite_journal_mode};")
        cursor.execute("PRAGMA synchronous=" + ("NORMAL" if settings.sqlite_journal_mode == "WAL" else "FULL"))
        if settings.sqlite_journal_mode == "WAL":
            cursor.execute("PRAGMA wal_autocheckpoint=1000;")
    finally:
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
