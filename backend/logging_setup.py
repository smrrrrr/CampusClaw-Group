"""请求标识与单行 JSON 日志（engineering-baseline design「日志字段」）。

- 每个请求一个 request_id：采纳合法的 X-Request-ID 请求头，否则生成 uuid4().hex，回写到响应头
- 访问日志 logger 名为 access，每个请求一行；业务模块照常 logging.getLogger(__name__)，自动带上当前 request_id
- 日志只记路径，不记查询串、请求头、请求体、令牌与 Cookie
"""

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
access_logger = logging.getLogger("access")

# LogRecord 自带属性，不作为 extra 字段输出；color_message 是 uvicorn 带 ANSI 颜色码的重复文案
_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "taskName", "color_message"}
# 第三方库的 INFO 日志会带请求 URL 等细节，只保留警告以上
_QUIET_LOGGERS = ("httpx", "httpcore", "openai", "multipart", "python_multipart")


def _utc_iso(timestamp: float) -> str:
    moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": _utc_iso(record.created),
            "level": record.levelname.lower(),
            "module": record.name,
            "request_id": request_id_var.get(),
        }
        if record.name != "access":
            entry["msg"] = record.getMessage()
        for key, value in vars(record).items():
            if key not in _RESERVED and key not in entry:
                entry[key] = value
        if record.exc_info:
            # 堆栈只进日志、不进响应；换行由 json.dumps 转义，仍是一行
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """根 logger 与 uvicorn 日志统一为单行 JSON；uvicorn.access 由 RequestContextMiddleware 取代。"""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False
    uvicorn_access.disabled = True

    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def resolve_request_id(raw: str | None) -> str:
    if raw and _VALID_REQUEST_ID.match(raw):
        return raw
    return uuid.uuid4().hex


class RequestContextMiddleware:
    """纯 ASGI 中间件：不缓冲响应体，SSE 流式接口同样适用。

    访问日志在响应开始时写出；流式接口的 duration_ms 是首包耗时。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                raw = value.decode("latin-1")
                break
        request_id = resolve_request_id(raw)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        logged = False

        def log_access(status: int) -> None:
            nonlocal logged
            if logged:
                return
            logged = True
            access_logger.info(
                "",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )

        response_started = False

        async def send_with_request_id(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
                log_access(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            # 外层 ServerErrorMiddleware 发出的 500 不经过本中间件，带不上请求标识；
            # 这里先发出同样的通用 500，再把异常交给外层记录（外层见响应已开始只会继续抛出）
            if not response_started:
                body = json.dumps({"detail": "服务器内部错误"}, ensure_ascii=False).encode("utf-8")
                await send_with_request_id({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
            log_access(500)
            raise
        finally:
            request_id_var.reset(token)
