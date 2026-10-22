"""MCP 令牌加解密与 Base URL 安全校验（add-mcp-tool-integration）。

设计见 design.md 决策 3、4：

- 教师登记的令牌经 Fernet 加密后落库；密钥只取服务端环境变量 ``MCP_TOKEN_KEY``，
  未配置时拒绝保存令牌，避免明文入库或随数据库/交接包外泄。
- 教师填写的 Base URL 会被服务端请求，必须命中 ``MCP_ALLOWED_HOSTS`` 允许清单，
  且禁用重定向，防止借服务端探测内网（SSRF）。
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken

from config import settings


class TokenKeyNotConfigured(Exception):
    """未配置 MCP_TOKEN_KEY，无法保存或读取令牌。"""


class TokenDecryptError(Exception):
    """令牌无法解密（密钥被轮换或丢失），需教师重新填写。"""


def _fernet() -> Fernet:
    key = (settings.mcp_token_key or "").strip()
    if not key:
        raise TokenKeyNotConfigured("未配置 MCP_TOKEN_KEY，无法保存或读取令牌")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise TokenKeyNotConfigured("MCP_TOKEN_KEY 格式不合法，应为 Fernet 密钥") from exc


def encrypt_token(plain: str) -> str:
    """明文令牌 → Fernet 密文（str）。"""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_token(cipher: str) -> str:
    """密文 → 明文；密钥不匹配时抛 TokenDecryptError。"""
    try:
        return _fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenDecryptError("令牌无法解密，请重新填写令牌") from exc


def normalize_host(base_url: str) -> str:
    """取 URL 的 host[:port]（小写），用于允许清单比对。"""
    parts = urlsplit(base_url)
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    return f"{host}:{port}"


def validate_base_url(base_url: str) -> str:
    """校验并归一化 Base URL；不合法抛 ValueError（中文原因）。

    规则：http/https；必须有主机；主机（含端口）必须在允许清单内；
    拒绝回环、链路本地与云元数据地址。
    """
    raw = (base_url or "").strip()
    if not raw:
        raise ValueError("Base URL 不能为空")
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https"):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
    if not parts.hostname:
        raise ValueError("Base URL 缺少主机名")
    if parts.username or parts.password:
        raise ValueError("Base URL 不能包含用户名或密码")

    hostname = parts.hostname.lower()
    # 直接拒绝明显危险的主机，即使被误加进允许清单
    if hostname in ("localhost", "metadata.google.internal"):
        raise ValueError("不允许访问本机或云元数据地址")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_reserved:
            raise ValueError("不允许访问回环、内网或保留地址")
    except ValueError as exc:
        # 不是 IP 字面量（域名）时正常通过；上面的自定义错误需原样抛出
        if "不允许访问" in str(exc):
            raise

    allowed = settings.mcp_allowed_host_set
    if normalize_host(raw) not in allowed:
        raise ValueError(
            "Base URL 的主机不在允许清单内（MCP_ALLOWED_HOSTS），无法登记"
        )
    # 归一化：去掉路径尾部多余斜杠，保留 scheme://host[:port][/path]
    return raw.rstrip("/")
