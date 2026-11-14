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

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

# 仅 Compose 内网可达；不映射宿主机端口
EXPOSE 8090

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
