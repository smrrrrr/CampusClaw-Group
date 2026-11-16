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

# 系统层安全更新：基础镜像 python:3.12-slim（debian 13.7）发布后，stable-security 仍有可用补丁
# （如 zlib1g 的 CVE-2026-76844）。构建时拉一次安全更新，把「有修复版本」的系统包修掉；
# 无修复版本的包另行登记书面例外（reports/security-evidence/os-vuln-exceptions.json）。
# 代价：构建期依赖 apt 源可达（与 builder 层"不装编译工具"的取舍不同），失效条件见规范书面例外。
RUN apt-get update \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY . .

# 第10课 6.1：最终镜像不带开发材料。先移除种子脚本、构建描述与开发期配置文件，
# 随后在下一步全量编译为 .pyc 并删除所有 .py；.dockerignore 已排除 .venv/缓存/数据库/.env。
RUN rm -f /app/dev_seed.py /app/Dockerfile /app/.dockerignore /app/.gitignore \
    /app/.env.example /app/.python-version

# 删除源码前留下构建期源码哈希清单：镜像仍为 0 源码，但可核对「镜像是否由当前源码构建」。
RUN /app/.venv/bin/python -c "import hashlib,json;from pathlib import Path;root=Path('/app');files=sorted(p for p in root.rglob('*.py') if '.venv' not in p.parts);root.joinpath('.source-sha256.json').write_text(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},sort_keys=True),encoding='utf-8')"

# 第10课 6.1：课程要求镜像 0 源码。递归编译应用、.venv 与系统标准库为 legacy .pyc 后删除所有 .py。
# 必须递归整个 /app：只编译顶层会让 routers/ 等包子目录被删后无法导入。
# 系统 Python 标准库 /usr/local/lib/python3.12 同样处理，否则 find / -name "*.py" 仍有残留。
# 基础镜像里 GCC 的 gdb 调试辅助 .py 与业务无关，一并删除。
# 末尾断言 .py 计数为 0：构建期强制保证，避免“注释声称无源码”但实际有残留。
# .pyc 仍可反编译，不等于代码加密。
RUN /app/.venv/bin/python -m compileall -b -q /app /usr/local/lib/python3.12 >/dev/null 2>&1 \
    && find /app /usr/local/lib/python3.12 -name "*.py" -delete \
    && { find /usr/share/gdb /usr/share/gcc -name "*.py" -delete 2>/dev/null || true; } \
    && test "$(find / -name '*.py' -not -path '/proc/*' 2>/dev/null | wc -l)" -eq 0

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
