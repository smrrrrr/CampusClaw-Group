# ---- 依赖构建层 ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# ---- 运行层：只保留锁定运行依赖与入口，不含 uv/构建缓存 ----
FROM python:3.12-slim AS runtime

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="campusclaw-mcp-tools" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source="campusclaw"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY main.py ./

# 第10课 6.1：与后端一致，镜像 0 源码。递归编译应用、.venv 与系统标准库为 .pyc 后删除所有 .py，
# 并清理基础镜像 GCC 的 gdb 调试辅助脚本；末尾断言 .py 计数为 0。
# .pyc 可反编译，不等于代码加密。
RUN /app/.venv/bin/python -m compileall -b -q /app /usr/local/lib/python3.12 >/dev/null 2>&1 \
    && find /app /usr/local/lib/python3.12 -name "*.py" -delete \
    && { find /usr/share/gdb /usr/share/gcc -name "*.py" -delete 2>/dev/null || true; } \
    && test "$(find / -name '*.py' -not -path '/proc/*' 2>/dev/null | wc -l)" -eq 0

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

# 仅 Compose 内网可达；不映射宿主机端口
EXPOSE 8090

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
