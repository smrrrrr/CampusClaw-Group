# -*- coding: utf-8 -*-
"""GET /api/mcp/servers/{id}/tools 与 POST connect/disconnect —— 连接与工具（真实 dev 服务）。

连接自建 mcp-tools 需要服务端 .env 的 MCP_AUTH_TOKEN 与 mcp-tools 的令牌一致，
且 MCP_ALLOWED_HOSTS 含 mcp-tools:8090。若环境未提供这些，用例会跳过而不是误报。
"""

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
    """连接 → 发现工具 → 断开；失败(502)时跳过（环境未部署 mcp-tools）。"""
    _cleanup(api, teacher_headers)
    name = f"{BASE_NAME}-{uuid.uuid4().hex[:6]}"
    try:
        r = api.post(
            "/api/mcp/servers",
            json={"class_id": 101, "name": name, "base_url": "http://mcp-tools:8090", "auth_token": "change-me"},
            headers=teacher_headers,
        )
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        rc = api.post(f"/api/mcp/servers/{sid}/connect", headers=teacher_headers)
        if rc.status_code == 502:
            pytest.skip("环境未部署 mcp-tools 或令牌不一致，跳过连接用例")
        assert rc.status_code == 200, rc.text
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
