# -*- coding: utf-8 -*-
"""CSRF 反例：携带 csrf_token Cookie 但不带 X-CSRF-Token 头的写请求应被拒绝。

三段式：
- 前置条件：教师已登录（响应 Set-Cookie: csrf_token=...）
- 操作：用 Cookie 会话发起 POST /api/teacher/skills，不带 X-CSRF-Token 头
- 可观测结果：返回 403（CSRF 令牌校验失败）；带正确 X-CSRF-Token 头的同请求返回 200/201
"""

import requests


def test_csrf_cookie_without_header_rejected(api, teacher_headers):
    """有 csrf_token Cookie 但无 X-CSRF-Token 头 → 403。"""
    # 登录拿 Cookie（teacher_headers 已登录，但我们需要原始 cookie）
    from conftest import TEACHER
    login_resp = requests.post(
        api.base + "/api/auth/login",
        json={"identifier": TEACHER["identifier"], "password": TEACHER["password"]},
        timeout=30,
    )
    assert login_resp.status_code == 200
    csrf_cookie = login_resp.cookies.get("csrf_token")
    assert csrf_cookie, "登录响应应包含 csrf_token Cookie"

    # 用 Cookie 发起写请求，不带 X-CSRF-Token 头
    cookies = {"csrf_token": csrf_cookie}
    r = requests.post(
        api.base + "/api/teacher/skills",
        json={"name": "csrf-test-skill", "description": "test", "enabled": True},
        cookies=cookies,
        timeout=30,
    )
    assert r.status_code == 403, (
        f"缺少 X-CSRF-Token 头的写请求应被拒绝，实际 {r.status_code}"
    )
    assert "CSRF" in r.text or "csrf" in r.text.lower(), "响应应提示 CSRF 校验失败"


def test_csrf_cookie_with_correct_header_accepted(api, teacher_headers):
    """csrf_token Cookie + 正确 X-CSRF-Token 头 → 放行。"""
    from conftest import TEACHER
    login_resp = requests.post(
        api.base + "/api/auth/login",
        json={"identifier": TEACHER["identifier"], "password": TEACHER["password"]},
        timeout=30,
    )
    assert login_resp.status_code == 200
    csrf_cookie = login_resp.cookies.get("csrf_token")

    cookies = {"csrf_token": csrf_cookie}
    headers = {"X-CSRF-Token": csrf_cookie}
    r = requests.post(
        api.base + "/api/teacher/skills",
        json={"name": "csrf-test-skill-ok", "description": "test", "enabled": True},
        cookies=cookies,
        headers=headers,
        timeout=30,
    )
    # 带正确令牌应通过 CSRF 校验（业务鉴权可能仍返回 401 因为没带 Bearer token，但不应是 CSRF 403）
    assert r.status_code != 403 or "CSRF" not in r.text, (
        f"带正确 X-CSRF-Token 头不应被 CSRF 拒绝，实际 {r.status_code}: {r.text[:200]}"
    )


def test_bearer_token_exempt_from_csrf(api, teacher_headers):
    """带 Authorization: Bearer 头的请求豁免 CSRF 校验。"""
    r = api.post(
        "/api/teacher/skills",
        json={"name": "bearer-csrf-test", "description": "test", "enabled": True},
        headers=teacher_headers,  # teacher_headers 含 Authorization: Bearer
    )
    # Bearer 头请求不受 CSRF 校验；业务层返回 201 或其他业务码，不应是 CSRF 403
    assert r.status_code != 403 or "CSRF" not in r.text, (
        f"Bearer 令牌请求不应被 CSRF 拒绝，实际 {r.status_code}: {r.text[:200]}"
    )
