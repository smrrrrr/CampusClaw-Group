# -*- coding: utf-8 -*-
"""POST/GET /api/mcp/servers —— MCP 服务器登记与列出（真实 dev 服务）。

这些用例按 URL 组织，运行前需要：
- dev 服务已启动（BASE_URL，默认 http://localhost:8001）
- 数据库已执行到含 mcp_servers 表的新代码（启动时 create_all 自动建表）
- 服务端 .env 配置了 MCP_TOKEN_KEY 与 MCP_ALLOWED_HOSTS（含 mcp-tools:8090）

约定：用例自行登记一条临时服务器，并在结束时删除，避免污染。
"""

import uuid

BASE_NAME = "apitest-tools"


def _cleanup(api, headers, class_id=101):
    r = api.get("/api/mcp/servers", params={"class_id": class_id}, headers=headers)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            if item["name"].startswith(BASE_NAME):
                api.delete(f"/api/mcp/servers/{item['id']}", headers=headers)


def test_register_and_list_server(api, teacher_headers):
    """登记合法服务器 → 201，响应不含令牌，列表可见，完成后删除。"""
    _cleanup(api, teacher_headers)
    name = f"{BASE_NAME}-{uuid.uuid4().hex[:6]}"
    token = "apitest-secret-token"
    try:
        r = api.post(
            "/api/mcp/servers",
            json={"class_id": 101, "name": name, "base_url": "http://mcp-tools:8090", "auth_token": token},
            headers=teacher_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == name
        assert body["has_auth"] is True
        assert body["connected"] is False
        assert body["tool_count"] == 0
        # 任何响应都不得出现令牌原文
        assert token not in r.text

        r2 = api.get("/api/mcp/servers", params={"class_id": 101}, headers=teacher_headers)
        assert r2.status_code == 200, r2.text
        assert any(item["name"] == name for item in r2.json()["items"])
        assert token not in r2.text
    finally:
        _cleanup(api, teacher_headers)


def test_register_rejects_disallowed_host(api, teacher_headers):
    """不在允许清单/回环地址 → 400。"""
    for bad in ("http://127.0.0.1:8000", "http://169.254.169.254", "http://backend:8000"):
        r = api.post(
            "/api/mcp/servers",
            json={"class_id": 101, "name": BASE_NAME, "base_url": bad, "auth_token": "x"},
            headers=teacher_headers,
        )
        assert r.status_code == 400, (bad, r.text)


def test_mcp_requires_auth(api):
    """未带 Bearer → 401。"""
    r = api.get("/api/mcp/servers", params={"class_id": 101})
    assert r.status_code == 401, r.text


def test_student_forbidden(api, student_headers):
    """学生访问管理接口 → 403。"""
    r = api.get("/api/mcp/servers", params={"class_id": 101}, headers=student_headers)
    assert r.status_code == 403, r.text
