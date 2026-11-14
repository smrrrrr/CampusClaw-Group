# ---- 依赖构建层：只在构建期出现 uv 与编译缓存 ----
FROM python:3.12-slim AS builder

WORKDIR /app

# 说明：所有第三方依赖（PyMuPDF、python-docx、python-pptx、cryptography、uvloop 等）
# 都有预编译 wheel，无需在镜像内安装 gcc 等编译工具，避免构建时依赖 apt 源可达性。
# 若将来新增了需要编译的依赖，再在此层按需安装构建工具。

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

# 先拷依赖清单以利用 Docker 层缓存；--no-dev 不带测试与开发依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# ---- 运行层：只保留锁定运行依赖与应用文件，不含 uv/构建工具/测试/仓库 ----
FROM python:3.12-slim AS runtime

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="campusclaw-backend" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source="campusclaw"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

# 第10课 6.1：最终镜像不带开发材料。运行所需的业务 .py 全部保留，
# 只移除种子脚本、构建描述与开发期配置文件；.dockerignore 已排除 .venv/缓存/数据库/.env。
RUN rm -f /app/dev_seed.py /app/Dockerfile /app/.dockerignore /app/.gitignore \
    /app/.env.example /app/.python-version

# 以非 root 运行；entrypoint 在容器启动时修正挂载目录属主后降权。
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}" \
    UPLOAD_DIR=/app/uploads \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
# 直接用 .venv 里的 uvicorn，避免 `uv run` 启动时联网解析依赖（国内网络易超时）
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
