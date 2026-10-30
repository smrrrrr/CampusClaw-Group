"""CampusClaw FastAPI 应用入口。

启动方式（uv 管理环境）：
    uv run uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import models  # noqa: F401  # 确保模型注册到 Base.metadata
from config import settings
from database import Base, SessionLocal, engine, run_simple_migrations
from logging_setup import RequestContextMiddleware, configure_logging
from routers import auth, materials, student, teacher, research_materials, lesson_plans, mcp, skills, quiz, homework, mistake, analytics
from security import JWTError, TOKEN_TYPE_ACCESS, decode_token
from services import write_audit_log
from version import APP_VERSION

# 根 logger 与 uvicorn 日志统一为单行 JSON 并带 request_id（engineering-baseline）。
# uvicorn 先配置日志再导入本模块，所以在导入时覆盖即可生效。
configure_logging()

MCP_HEALTH_TIMEOUT = 2.0  # 秒，见 runtime-reliability「数据库可读性纳入健康检查」


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 简单迁移：骨架表升级（materials 扩展为业务表等）
    run_simple_migrations()
    # 启动时自动建表（SQLite 文件随之生成）
    Base.metadata.create_all(bind=engine)
    yield


# ENABLE_DOCS=false 时关闭交互式文档（生产部署不暴露接口自描述）
_docs_enabled = settings.enable_docs

app = FastAPI(
    title="CampusClaw API",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# CORS：前端与后端不同端口，必须允许 credentials（HttpOnly Cookie 刷新）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(materials.router)
app.include_router(research_materials.router)
app.include_router(lesson_plans.router)
app.include_router(mcp.router)
app.include_router(skills.router)
app.include_router(quiz.router)
app.include_router(homework.router)
app.include_router(mistake.router)
app.include_router(analytics.router)


# ---------------------------------------------------------------------------
# 403 审计日志中间件：拦截 403 响应，异步写入 AuditLog
# ---------------------------------------------------------------------------


@app.middleware("http")
async def audit_403_middleware(request: Request, call_next):
    response = await call_next(request)

    if response.status_code == 403:
        # 从 Authorization 头解析用户信息（可选，无 Token 则 user_id/role 为 None）
        user_id = None
        role = None
        class_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                if payload.get("type") == TOKEN_TYPE_ACCESS:
                    user_id = payload.get("user_id")
                    role = payload.get("role")
                    if role == "student":
                        class_id = payload.get("class_id")
            except JWTError:
                pass

        ip = request.client.host if request.client else None
        # 异步写入：用独立 DB session，catch-and-log 不影响主请求
        try:
            audit_db = SessionLocal()
            write_audit_log(
                audit_db,
                user_id=user_id,
                role=role,
                class_id=class_id,
                request_path=request.url.path,
                method=request.method,
                status_code=403,
                ip_address=ip,
            )
        finally:
            audit_db.close()

    return response


# 最后注册即位于最外层：403 审计、CORS 与路由内的日志都能取到同一个 request_id
app.add_middleware(RequestContextMiddleware)


def _mcp_tools_status() -> str:
    url = settings.mcp_tools_health_url.strip()
    if not url:
        return "not_configured"
    try:
        response = httpx.get(url, timeout=MCP_HEALTH_TIMEOUT)
    except httpx.HTTPError:
        return "unreachable"
    return "ok" if response.is_success else "unreachable"


@app.get("/api/health", tags=["health"])
def health_check():
    """免认证；只返回状态枚举，不返回地址、键名或异常原文。"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT id FROM users LIMIT 1")).first()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="数据库暂不可用，请稍后重试") from exc
    mcp_tools = _mcp_tools_status()
    return {
        "status": "degraded" if mcp_tools == "unreachable" else "ok",
        "version": APP_VERSION,
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dependencies": {
            "database": "ok",
            "mcp_tools": mcp_tools,
            "model": "configured" if settings.deepseek_api_key.strip() else "not_configured",
        },
    }
