"""应用配置：从环境变量 / .env 文件读取。"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库
    database_url: str = "sqlite:///./campusclaw.db"
    # Windows Docker 共享目录使用 DELETE；原生本地磁盘可使用 WAL。
    sqlite_journal_mode: Literal["WAL", "DELETE"] = "WAL"

    # JWT
    jwt_secret_key: str = "campusclaw-dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # 2 小时
    refresh_token_expire_days: int = 7

    # 生产环境关闭交互式 API 文档（/docs、/redoc、/openapi.json）
    enable_docs: bool = True

    # 学校缩写（初始密码规则：三位小写缩写 + 学号/工号后 6 位）
    school_abbr: str = "thu"

    # CORS
    frontend_origins: str = "http://localhost:3000"

    # Cookie
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # 材料上传
    # 本地开发：uploads（相对 backend 工作目录）；Docker：/app/uploads
    upload_dir: str = "uploads"
    max_file_size_mb: int = 50
    # 允许的文件格式（MIME → 扩展名映射，用于前端 accept 与后端校验）
    allowed_extensions: str = "pdf,pptx,docx,jpg,png,md,txt"

    # RAG 检索（add-rag-search）
    chunk_size: int = 300          # 文本分块长度（字符）
    chunk_overlap: int = 60        # 相邻分块重叠长度（字符）
    chunk_top_k: int = 3           # 相似度检索返回的分块数（资料 2-3 条即可）
    # 相关度下限比例：低于最优命中分数 × 该比例的块视为低相关剔除，避免硬凑条数
    chunk_min_relevance: float = 0.35
    # 绝对词元门槛：问题与所有候选块精确字符二元组重叠的最大次数低于该值，
    # 视为「本班未找到相关资料」，不返回任何引用（避免无关问题被虚假余弦召回并误标出处）
    chunk_min_keyword_hits: int = 3
    embed_dim: int = 512           # 字符 n-gram 哈希向量维度
    # 检索模式：vector（仅向量） / keyword（仅关键字） / hybrid（关键字+向量 RRF 融合）
    retrieval_mode: str = "hybrid"

    # AI 解题助手：DeepSeek 生成（openai 兼容接口）
    deepseek_api_key: str = ""               # 为空则 AI 生成降级为提示
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: float = 60             # 单次请求超时（秒）
    deepseek_temperature: float = 0.3        # 偏低以贴合资料、减少编造

    # MCP 工具集成（add-mcp-tool-integration）
    # 与 mcp-tools 服务共享的访问令牌；仅用于宿主侧调用远端时携带
    mcp_auth_token: str = ""
    # 加密教师登记令牌用的 Fernet 密钥；为空则拒绝保存令牌
    mcp_token_key: str = ""
    # 允许服务端连接的 MCP 主机清单（host[:port]，逗号分隔），防 SSRF
    mcp_allowed_hosts: str = "mcp-tools:8090"
    # 调用循环上限与超时
    mcp_max_rounds: int = 3                   # 每次提问最多决策轮次
    mcp_max_calls_per_question: int = 4       # 每次提问最多工具调用
    mcp_max_calls_per_conversation: int = 20  # 单会话累计调用上限
    mcp_call_timeout: float = 10              # 单次 tools/call 超时（秒）

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def mcp_allowed_host_set(self) -> set[str]:
        """归一化为小写 host[:port] 集合，供 Base URL 校验。"""
        return {h.strip().lower() for h in self.mcp_allowed_hosts.split(",") if h.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
