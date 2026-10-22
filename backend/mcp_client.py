"""宿主侧 MCP 客户端（add-mcp-tool-integration，design.md 决策 6）。

只实现本项目需要的子集：POST /mcp 发送 JSON-RPC 2.0，处理 JSON 与 SSE 两种响应，
完成 ``initialize`` → ``notifications/initialized`` → ``tools/list`` 握手与发现，
以及单次 ``tools/call``。不实现 stdio、resources/prompts、服务端主动通知与会话持久化。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "campusclaw-backend", "version": "0.1.0"}
MAX_TOOLS = 50

# 工具名规则：小写字母开头，仅小写字母、数字、下划线
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# 服务名规则（与登记规则一致）：1–32 位小写字母、数字或连字符，字母或数字开头
SERVER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
# MCP 工具引用：工具名@服务器名
TOOL_REF_RE = re.compile(r"^([a-z][a-z0-9_]*)@([a-z0-9][a-z0-9-]{0,31})$")

# 已知提示词注入/指令式句式（软防线，仅拦截已知写法）
INJECTION_PATTERNS = [
    re.compile(r"(忽略|无视|忘记|抛弃)(以上|上面|之前|先前)(所有|全部)?(的)?(指令|要求|规则|提示|设定)", re.I),
    re.compile(r"ignore\s+(all\s+)?(the\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", re.I),
    re.compile(r"(你现在是|从现在开始你(是|将)|扮演|你的新角色)", re.I),
    re.compile(r"(system\s*prompt|系统提示词|系统提示|初始指令)", re.I),
    re.compile(r"(输出|泄露|打印|告诉我?)(你的)?(提示词|密钥|api\s*key|token)", re.I),
    re.compile(r"(reveal|print|output|show)\s+(your\s+)?(system\s+prompt|api\s*key|secret|token)", re.I),
]


class McpClientError(Exception):
    """MCP 交互失败（不可达、超时、HTTP 错误、协议/结构错误）。"""


@dataclass
class DiscoveredTool:
    name: str
    description: str
    input_schema: dict


def looks_like_injection(text: str) -> bool:
    """检测已知的指令式句式；仅拦截已知写法，不宣称完整防注入。"""
    if not text:
        return False
    return any(p.search(text) for p in INJECTION_PATTERNS)


def _parse_sse(raw_text: str, expected_id: int) -> dict | None:
    """从 text/event-stream 响应里取第一条 data: 的 JSON-RPC 消息。"""
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("id") == expected_id:
            return obj
    return None


class McpClient:
    """同步客户端：一次连接生命周期内复用同一个 httpx.Client。"""

    def __init__(self, base_url: str, token: str, timeout: float = 10.0):
        self.mcp_url = f"{base_url.rstrip('/')}/mcp"
        self.token = token
        self.timeout = timeout
        self._next_id = 0
        self._session_id: str | None = None

    # -- 低层 --------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _post(self, payload: dict) -> dict:
        """发送一条 JSON-RPC 请求并返回响应对象（含 error 时抛 McpClientError）。"""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                resp = client.post(self.mcp_url, json=payload, headers=self._headers())
                if resp.status_code == 401:
                    raise McpClientError("MCP 服务拒绝了令牌（401），请检查令牌是否一致")
                if resp.status_code >= 400:
                    raise McpClientError(f"MCP 服务返回 HTTP {resp.status_code}")
                session = resp.headers.get("Mcp-Session-Id")
                if session:
                    self._session_id = session
                ctype = resp.headers.get("content-type", "")
                if "text/event-stream" in ctype:
                    body = _parse_sse(resp.text, payload["id"])
                    if body is None:
                        raise McpClientError("MCP 流式响应缺少对应的 JSON-RPC 消息")
                    return body
                return resp.json()
        except McpClientError:
            raise
        except httpx.TimeoutException as exc:
            raise McpClientError("连接 MCP 服务器超时") from exc
        except httpx.HTTPError as exc:
            raise McpClientError(f"无法连接 MCP 服务器：{type(exc).__name__}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise McpClientError("MCP 响应不是合法的 JSON") from exc

    def _request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload: dict = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params
        body = self._post(payload)
        if "error" in body and body["error"]:
            message = body["error"].get("message", "未知错误")
            raise McpClientError(f"MCP 方法 {method} 失败：{message}")
        result = body.get("result")
        if not isinstance(result, dict):
            raise McpClientError(f"MCP 方法 {method} 返回结构不合法")
        return result

    def _notify(self, method: str, params: dict | None = None) -> None:
        """发送通知（无 id，不等待正文）。"""
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                client.post(self.mcp_url, json=payload, headers=self._headers())
        except httpx.HTTPError:
            # 通知失败不影响主流程；后续 tools/list 会暴露真正的问题
            pass

    # -- 高层 --------------------------------------------------------------

    def initialize(self) -> None:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO},
        )
        capabilities = result.get("capabilities")
        if not isinstance(capabilities, dict) or "tools" not in capabilities:
            raise McpClientError("MCP 服务器未声明 tools 能力")
        self._notify("notifications/initialized")

    def list_tools(self) -> tuple[list[DiscoveredTool], list[str]]:
        """分页拉取工具清单；返回 (合法工具列表, 被排除的工具名)。"""
        tools: list[DiscoveredTool] = []
        excluded: list[str] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while len(tools) < MAX_TOOLS:
            params = {"cursor": cursor} if cursor else None
            result = self._request("tools/list", params)
            page = result.get("tools")
            if not isinstance(page, list):
                raise McpClientError("tools/list 返回的 tools 不是数组")
            for item in page:
                if not isinstance(item, dict):
                    excluded.append("(非对象条目)")
                    continue
                name = item.get("name")
                description = item.get("description") or ""
                schema = item.get("inputSchema")
                if not isinstance(name, str) or not TOOL_NAME_RE.match(name):
                    excluded.append(str(name))
                    continue
                if not isinstance(description, str) or len(description) > 1000:
                    excluded.append(name)
                    continue
                if not isinstance(schema, dict) or schema.get("type") != "object":
                    excluded.append(name)
                    continue
                # 工具说明也按不可信数据检查句式
                if looks_like_injection(description):
                    excluded.append(name)
                    continue
                tools.append(DiscoveredTool(name=name, description=description, input_schema=schema))
                if len(tools) >= MAX_TOOLS:
                    break
            cursor = result.get("nextCursor")
            if not cursor or cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
        return tools, excluded

    def connect_and_discover(self) -> tuple[list[DiscoveredTool], list[str]]:
        """完成握手并发现工具。失败抛 McpClientError。"""
        self.initialize()
        return self.list_tools()

    def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        """执行一次 tools/call；返回 (文本, is_error)。失败抛 McpClientError。"""
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        is_error = bool(result.get("isError"))
        texts: list[str] = []
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(str(part.get("text") or ""))
        if not texts:
            raise McpClientError("工具返回内容为空")
        return "\n".join(texts), is_error
