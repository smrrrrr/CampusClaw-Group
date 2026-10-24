# -*- coding: utf-8 -*-
"""GET /api/mcp/servers/{id}/tools 与 POST connect/disconnect —— 连接与工具（真实 dev 服务）。

连接自建 mcp-tools 需要通过环境变量 APITEST_MCP_TOKEN 传入与服务端 MCP_AUTH_TOKEN 一致的令牌，
且 MCP_ALLOWED_HOSTS 含 mcp-tools:8090。未提供令牌时跳过；提供了令牌仍连接失败按失败处理。
"""

import os
import uuid

import pytest

BASE_NAME = "apitest-conn"


def _cleanup(api, headers, class_id=101):
    r = api.get("/api/mcp/servers", params={"class_id": class_id}, headers=headers)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            if item["name"].startswith(BASE_NAME):
                api.delete(f"/api/mcp/servers/{item['id']}", headers=headers)


def test_connect_then_tools_then_disconnect(api, teacher_headers):
    """连接 → 发现工具 → 断开；连接失败按失败处理。"""
    token = os.environ.get("APITEST_MCP_TOKEN")
    if not token:
        pytest.skip("未提供 APITEST_MCP_TOKEN（须与服务端 MCP_AUTH_TOKEN 一致），无法连接真实 mcp-tools")
    _cleanup(api, teacher_headers)
    name = f"{BASE_NAME}-{uuid.uuid4().hex[:6]}"
    try:
        r = api.post(
            "/api/mcp/servers",
            json={"class_id": 101, "name": name, "base_url": "http://mcp-tools:8090", "auth_token": token},
            headers=teacher_headers,
        )
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        rc = api.post(f"/api/mcp/servers/{sid}/connect", headers=teacher_headers)
        assert rc.status_code == 200, f"连接真实 mcp-tools 失败：{rc.status_code} {rc.text}"
        assert rc.json()["server"]["connected"] is True

        rt = api.get(f"/api/mcp/servers/{sid}/tools", headers=teacher_headers)
        assert rt.status_code == 200, rt.text
        names = [t["name"] for t in rt.json()["items"]]
        assert "formula_hint" in names and "unit_convert" in names

        # 断开后工具清空
        rd = api.post(f"/api/mcp/servers/{sid}/disconnect", headers=teacher_headers)
        assert rd.status_code == 200, rd.text
        rt2 = api.get(f"/api/mcp/servers/{sid}/tools", headers=teacher_headers)
        assert rt2.json()["items"] == []
    finally:
        _cleanup(api, teacher_headers)


def test_unknown_server_404(api, teacher_headers):
    """不存在的服务器编号 → 404。"""
    r = api.get("/api/mcp/servers/999999/tools", headers=teacher_headers)
    assert r.status_code == 404, r.text
