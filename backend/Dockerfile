FROM python:3.12-slim

WORKDIR /app

# 说明：所有第三方依赖（PyMuPDF、python-docx、python-pptx、cryptography、uvloop 等）
# 都有预编译 wheel，无需在镜像内安装 gcc 等编译工具，避免构建时依赖 apt 源可达性。
# 若将来新增了需要编译的依赖，再在此处按需安装构建工具。

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 先拷依赖清单以利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# 拷业务代码
COPY . .

# 上传目录（与 docker-compose 卷挂载一致）
RUN mkdir -p /app/uploads
ENV UPLOAD_DIR=/app/uploads

EXPOSE 8000
# 直接用 .venv 里的 uvicorn，避免 `uv run` 每次启动联网解析依赖（国内网络易超时）
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
