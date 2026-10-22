FROM python:3.12-slim

WORKDIR /app

# 安装 uv（与后端镜像一致，锁定依赖版本）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY main.py ./

# 仅 Compose 内网可达；不映射宿主机端口
EXPOSE 8090

CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
