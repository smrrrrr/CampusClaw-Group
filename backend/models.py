"""SQLAlchemy ORM 模型。

- User：统一存储教师 / 学生两种角色（无独立家长角色）
- LoginAttempt：密码登录失败锁定
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    teacher = "teacher"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    # 学号 / 工号
    identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 手机号（非唯一：同一手机号可绑定多个学生）
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 学生必填，教师为空
    class_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=True
    )
    # 教师任教班级 ID 列表（JSON 数组，如 "[101, 102]"），仅教师使用
    teaching_classes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 教师学科（如 "math" / "english"），仅教师使用；学生为空
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 班主任班级（可空，NULL 表示非班主任），仅教师使用
    homeroom_class_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("role", "identifier", name="uq_user_role_identifier"),
        Index("ix_user_phone", "phone"),
    )


class Class(Base):
    """班级表（账号预置时引用）。"""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 学号 / 工号
    identifier: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lock_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    """越权行为审计日志。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 教研隔离相关上下文（可空，仅教研/学情域写入）
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    class_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_path: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_audit_log_created_at", "created_at"),)


class AIQuestionLog(Base):
    """AI 提问记录（用于每日次数限制计数 + 班级数据隔离）。"""

    __tablename__ = "ai_question_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    # 班级数据隔离：记录提问时所在班级，教师查看 AI 历史时按 class_id 过滤
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ai_question_student_created", "student_id", "created_at"),
        Index("ix_ai_question_class_id", "class_id"),
    )


class AgentConfig(Base):
    """AI 解题助手的班级级配置：可自定义系统提示词与「解题引导」技能开关。

    每班、每科、每位教师独立配置；学生按班级、科目及会话绑定教师读取；
    无配置行则使用 llm_service 内置默认提示词。
    """

    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="math")
    # 最近一次编辑配置的教师
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    # 可自定义的系统提示词；留空则使用默认提示词
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 「解题引导技能」开关：开启后 AI 只给思路引导、不直接给最终答案，引导学生自己算出
    tutor_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    __table_args__ = (UniqueConstraint("class_id", "subject", "teacher_id", name="uq_agent_class_subject_teacher"),)


class Conversation(Base):
    """AI 解题助手多轮会话（按学生、班级和学科隔离，并绑定任课教师）。

    学生可新建多个会话，同一会话内连续追问；会话连同其 Message 构成多轮上下文。
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    # 会话所在班级（隔离 + 读取对应班级的 AgentConfig）
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(128), default="新对话", nullable=False)
    subject: Mapped[str] = mapped_column(String(32), default="math", nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    # 首轮检索到的班级资料上下文（整段文本）；后续轮次复用，避免重复检索。
    # 注意：SQLite 建表时此列可能缺失，需 database.run_simple_migrations 增列。
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_conversation_student", "student_id", "updated_at"),
        Index("ix_conversation_class_id", "class_id"),
    )


class Message(Base):
    """会话内的单条消息（role: user / assistant）。

    content 存消息文本；assistant 消息可用 sources（JSON）记录溯源引用。
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 溯源引用 JSON 数组（assistant）；user 消息为空
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_message_conversation", "conversation_id", "id"),)


# ---------------------------------------------------------------------------
# 班级数据隔离骨架表（class_id 字段规范，业务字段由后续规约扩展）
# ---------------------------------------------------------------------------


class Material(Base):
    """班级资料表：教师上传的学习材料元数据（文件本体存储在挂载卷，不存 SQLite）。"""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    # 原文件名（展示用）
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # 存储相对路径（如 101/1620000000_lesson1.pdf）
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # MIME 类型（如 application/pdf）
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 标签 JSON 数组（如 ["数学", "代数"]）
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 是否已解析为纯文本并纳入 AI 检索
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_material_class_id", "class_id"),
        # 联合索引：加速"查询某班已索引材料"场景
        Index("ix_material_class_indexed", "class_id", "is_indexed"),
    )


class ResearchMaterial(Base):
    """学科组教师素材，不绑定班级，也不进入学生资料检索。"""
    __tablename__ = "research_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    source_sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    assets_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ResearchChunk(Base):
    __tablename__ = "research_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_material_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_materials.id"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(nullable=False)


class MaterialAsset(Base):
    __tablename__ = "material_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("materials.id"), index=True)
    name: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))
    file_type: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("material_id", "name"),)


class MaterialPublication(Base):
    __tablename__ = "material_publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_material_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_materials.id"), index=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("materials.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class LessonPlan(Base):
    __tablename__ = "lesson_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    duration: Mapped[int] = mapped_column(Integer)
    requirements_json: Mapped[str] = mapped_column(Text)
    resources_json: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    student_lesson: Mapped[str] = mapped_column(Text, default="")
    student_handout: Mapped[str] = mapped_column(Text, default="")
    student_from_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class LessonPlanVersion(Base):
    __tablename__ = "lesson_plan_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("lesson_plans.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    resources_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    __table_args__ = (UniqueConstraint("lesson_plan_id", "version"),)


class LessonGroupPublication(Base):
    """教师主动共享的定稿快照。私人教案删除不删除组内副本。"""
    __tablename__ = "lesson_group_publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lesson_plans.id"), nullable=True, index=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer)
    research_material_id: Mapped[int] = mapped_column(Integer, ForeignKey("research_materials.id"), unique=True)
    resources_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    __table_args__ = (UniqueConstraint("lesson_plan_id", "version"),)


class LessonPublication(Base):
    __tablename__ = "lesson_publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("lesson_plans.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"))
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("materials.id"), unique=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    __table_args__ = (UniqueConstraint("lesson_plan_id", "version", "kind", "class_id", "content_sha256"),)


class MaterialContent(Base):
    """材料解析后的纯文本内容（供 AI 解题助手检索作为上下文）。"""

    __tablename__ = "material_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_material_content_material_id", "material_id"),)


class MaterialChunk(Base):
    """材料分块与向量（RAG 检索单元）。

    上传材料解析为纯文本后，按 chunk_service 切分为固定长度 + 重叠的文本块，
    每块计算 embedding 向量（BLOB）持久化于此表，供 rag_search_service 按班级检索。
    """

    __tablename__ = "material_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False
    )
    # 冗余存储：支持按班隔离检索，避免跨表 join（design.md 决策 2）
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 稠密向量的字节序列（float32，dtype 转换后持久化）
    embedding: Mapped[bytes] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_material_chunk_material_id", "material_id"),
        # 加速"查询某班已索引材料分块"的检索过滤
        Index("ix_material_chunk_class_material", "class_id", "material_id"),
    )


class Homework(Base):
    """作业布置表。"""

    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_homework_class_id", "class_id"),
        Index("ix_homework_class_subject", "class_id", "subject"),
    )


class HomeworkSubmission(Base):
    """作业提交记录表。"""

    __tablename__ = "homework_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    homework_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("homeworks.id"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    teacher_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_homework_submission_class_id", "class_id"),
        Index("ix_homework_submission_homework_id", "homework_id"),
        UniqueConstraint("homework_id", "student_id", name="uq_homework_student"),
    )


class MistakeNote(Base):
    """错题本表。"""

    __tablename__ = "mistake_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    homework_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("homeworks.id"), nullable=True
    )
    question_stem: Mapped[str] = mapped_column(Text, nullable=False)
    student_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastered: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="0"
    )
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_mistake_note_class_id", "class_id"),)


# ---------------------------------------------------------------------------
# MCP 工具集成（add-mcp-tool-integration）
# 四张新表由启动时 create_all 创建，不改动旧表结构。
# ---------------------------------------------------------------------------


class McpServer(Base):
    """教师登记的 MCP 服务器。令牌只存密文，任何响应/日志不返回。"""

    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    # Fernet 密文；None 表示未配置令牌
    auth_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", "name", name="uq_mcp_server_teacher_class_name"),
        Index("ix_mcp_server_teacher_class", "teacher_id", "class_id"),
    )


class McpTool(Base):
    """连接时从远端发现的工具缓存；每次连接在同一事务内先删后插。"""

    __tablename__ = "mcp_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    input_schema: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("server_id", "name", name="uq_mcp_tool_server_name"),
        Index("ix_mcp_tool_server", "server_id"),
    )


class AssistantSkill(Base):
    """教师技能文件（按班级、学科、教师隔离）。"""

    __tablename__ = "assistant_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # JSON 数组，如 ["knowledge_search", "formula_hint@campus-tools"]
    tools: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("class_id", "subject", "teacher_id", "name", name="uq_skill_scope_name"),
        Index("ix_skill_teacher_class", "teacher_id", "class_id"),
    )


class McpToolCall(Base):
    """MCP 工具调用审计：每次可归属到服务器的调用一行。"""

    __tablename__ = "mcp_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 服务器删除后该列置空，仍保留 server_name 文本
    server_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server_name: Mapped[str] = mapped_column(String(32), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok / error / denied
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_mcp_call_server_created", "server_id", "created_at"),
        Index("ix_mcp_call_conversation", "conversation_id"),
    )


# ---------------------------------------------------------------------------
# 智能命题（add-smart-question-generation）
# 六张新表由启动时 create_all 创建，不改动旧表结构。
# ---------------------------------------------------------------------------


class QuestionGeneration(Base):
    """一次命题任务。流结束时写入一行；失败也留记录，便于审计。"""

    __tablename__ = "question_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    request_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    resources_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="succeeded", nullable=False)  # succeeded / failed
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gaps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_qgen_teacher_created", "teacher_id", "created_at"),)


class QuestionItem(Base):
    """候选题与题库题共用一张表，由 status 区分（pending/approved/rejected）。"""

    __tablename__ = "question_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    generation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("question_generations.id"), nullable=True)
    derived_from_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(12), nullable=False)
    knowledge_points_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    answer_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    assets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stem_key: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    modified_in_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_qitem_scope", "subject", "status", "archived", "type", "difficulty"),
        Index("ix_qitem_author", "author_id"),
        Index("ix_qitem_stemkey", "subject", "stem_key"),
    )


class QuestionPaper(Base):
    """试卷，仅作者可见。"""

    __tablename__ = "question_papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    blueprint_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="draft", nullable=False)  # draft / final
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    copied_from_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (Index("ix_qpaper_teacher", "teacher_id", "created_at"),)


class QuestionPaperItem(Base):
    """试卷中的一道题：保存加入试卷时的完整题目与出处快照。"""

    __tablename__ = "question_paper_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("question_items.id"), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    __table_args__ = (
        UniqueConstraint("paper_id", "question_item_id", name="uq_paper_item"),
        Index("ix_qpaper_item_paper", "paper_id", "position"),
    )


class QuizPublication(Base):
    """试卷分班发布记录。相同内容重复发布时复用。"""

    __tablename__ = "quiz_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("question_papers.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classes.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("materials.id"), unique=True, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("paper_id", "class_id", "content_sha256", name="uq_quiz_pub_content"),
        Index("ix_quiz_pub_paper", "paper_id"),
    )


class QuestionEvent(Base):
    """命题审计事件。删除题目/试卷后事件仍保留。"""

    __tablename__ = "question_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # generation / item / paper
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_qevent_target", "target_type", "target_id"),
        Index("ix_qevent_actor", "actor_id", "created_at"),
    )
