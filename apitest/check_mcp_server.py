"""mcp-tools 服务：非法请求可读与令牌边界（离线 TestClient，不联网）。

覆盖 mcp-tool-integration「非法请求可读」「令牌缺失或错误」等场景：
非 JSON 正文、非法 JSON-RPC 结构、未知方法、未知工具、缺少必填参数
都必须返回对应 JSON-RPC 错误码与中文说明，且服务不崩溃。
"""

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["MCP_AUTH_TOKEN"] = "check-only-mcp-token-000000"

checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("PASS " if passed else "FAIL ") + name)


def load_server():
    spec = importlib.util.spec_from_file_location("campusclaw_mcp_server", ROOT / "mcp-server/main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    server = load_server()
    from fastapi.testclient import TestClient

    auth = {"Authorization": "Bearer check-only-mcp-token-000000"}
    with TestClient(server.app) as client:
        check("MCP 服务健康检查不需要令牌", client.get("/health").status_code == 200)
        check("MCP 交互式文档未暴露", client.get("/docs").status_code == 404)
        check("令牌缺失返回 401", client.post("/mcp", content=b"{}").status_code == 401)
        check("令牌错误返回 401",
              client.post("/mcp", content=b"{}", headers={"Authorization": "Bearer wrong"}).status_code == 401)

        cases = [
            ("非 JSON 正文", b"not-json", -32700, "合法 JSON"),
            ("非对象正文", b"[1, 2]", -32600, "JSON-RPC 对象"),
            ("缺少 jsonrpc 版本", b'{"id": 1, "method": "tools/list"}', -32600, "2.0"),
            ("缺少 method", b'{"jsonrpc": "2.0", "id": 1}', -32600, "method"),
            ("未知方法", b'{"jsonrpc": "2.0", "id": 2, "method": "tools/unknown"}', -32601, "未知方法"),
            ("未知工具", b'{"jsonrpc": "2.0", "id": 3, "method": "tools/call", '
                        b'"params": {"name": "nope", "arguments": {}}}', -32602, "未知工具"),
            ("缺少必填参数", b'{"jsonrpc": "2.0", "id": 4, "method": "tools/call", '
                          b'"params": {"name": "formula_hint", "arguments": {}}}', -32602, "缺少必填参数"),
            ("参数类型不符", b'{"jsonrpc": "2.0", "id": 5, "method": "tools/call", '
                          b'"params": {"name": "formula_hint", "arguments": {"query": 42}}}', -32602, "必须是字符串"),
        ]
        for label, body, code, hint in cases:
            response = client.post("/mcp", content=body, headers=auth)
            error = response.json().get("error") or {}
            check(f"非法请求可读：{label} 返回 {code} 中文说明",
                  error.get("code") == code and hint in (error.get("message") or ""))

        listing = client.post("/mcp", headers=auth,
                              json={"jsonrpc": "2.0", "id": 6, "method": "tools/list"}).json()
        names = [tool["name"] for tool in listing["result"]["tools"]]
        check("非法请求可读：连续错误后工具列表仍正常返回", names == ["formula_hint", "unit_convert"])

        hint = client.post("/mcp", headers=auth, json={
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "formula_hint", "arguments": {"query": "两向量夹角"}}}).json()
        check("正常调用返回提示文本且不代算最终答案",
              hint["result"]["isError"] is False
              and "夹角" in hint["result"]["content"][0]["text"]
              and "具体数值请自行" in hint["result"]["content"][0]["text"])

    print(f"\n结果：{sum(1 for _, ok in checks if ok)}/{len(checks)} 通过")
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("失败项：", failed)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
