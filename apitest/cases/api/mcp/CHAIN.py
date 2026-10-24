# -*- coding: utf-8 -*-
"""MCP 链路（tasks 9.2，真实 dev 服务 + 真实 mcp-tools）。

连接服务器 → 保存引用 formula_hint 的技能 → 学生提问命中技能 → meta 帧 → ok 审计可在调用记录中查到。

运行前需要：
- APITEST_MCP_TOKEN：与服务端 MCP_AUTH_TOKEN 一致（不写进仓库，只从环境变量传入）；
- 后端在 compose 网络内，能访问 http://mcp-tools:8090。

连接失败按失败处理，不跳过。只有「模型提议调用 → ok 审计」一段依赖真实 AI：
AI 不可用（未配置或 Key 无效），或模型本次自行决定不调用工具（合法行为）时，该用例跳过并写明原因；
已提议的调用必须为 ok，否则失败。技能命中与 meta 帧仍须通过。
用例在班级 102（TEA001 任教数学、测试学生所在班）登记临时服务器与技能，结束时删除。
"""

import os
import uuid

import pytest

from conftest import parse_sse

CLASS_ID = 102
BASE_NAME = "apitest-chain"
TRIGGER = "apitest链路夹角"


def _cleanup(api, headers):
    r = api.get("/api/teacher/skills", params={"class_id": CLASS_ID}, headers=headers)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            if item["name"].startswith(BASE_NAME):
                api.delete(f"/api/teacher/skills/{item['id']}", headers=headers)
    r = api.get("/api/mcp/servers", params={"class_id": CLASS_ID}, headers=headers)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            if item["name"].startswith(BASE_NAME):
                api.delete(f"/api/mcp/servers/{item['id']}", headers=headers)


@pytest.fixture(scope="module")
def chain(api, teacher_headers, student_headers):
    token = os.environ.get("APITEST_MCP_TOKEN")
    if not token:
        pytest.skip("未提供 APITEST_MCP_TOKEN（须与服务端 MCP_AUTH_TOKEN 一致），无法连接真实 mcp-tools")
    _cleanup(api, teacher_headers)
    suffix = uuid.uuid4().hex[:6]
    server_name = f"{BASE_NAME}-{suffix}"
    skill_name = f"{BASE_NAME}-{suffix}"
    try:
        r = api.post(
            "/api/mcp/servers",
            json={"class_id": CLASS_ID, "name": server_name, "base_url": "http://mcp-tools:8090", "auth_token": token},
            headers=teacher_headers,
        )
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        rc = api.post(f"/api/mcp/servers/{sid}/connect", headers=teacher_headers)
        assert rc.status_code == 200, f"连接真实 mcp-tools 失败：{rc.status_code} {rc.text}"

        source = (
            f"名称：{skill_name}\n适用条件：{TRIGGER}\n工具：formula_hint@{server_name}\n启用：是\n\n"
            "求夹角时先调用公式提示工具，只给公式与步骤提示，不直接给答案。"
        )
        rs = api.post("/api/teacher/skills", json={"class_id": CLASS_ID, "source": source}, headers=teacher_headers)
        assert rs.status_code == 201, rs.text

        rv = api.post("/api/student/conversations", json={"title": "apitest 链路", "subject": "math"},
                      headers=student_headers)
        assert rv.status_code == 200, rv.text
        cid = rv.json()["id"]

        rq = api.post(
            f"/api/student/conversations/{cid}/chat",
            # 明确要求先查公式提示，尽量让模型提议调用；是否调用仍由模型决定
            json={"question": f"{TRIGGER}：请先用公式提示工具查一下，两个空间向量的夹角怎么求？"},
            headers=student_headers,
        )
        assert rq.status_code == 200, rq.text
        yield {"skill_name": skill_name, "ref": f"formula_hint@{server_name}", "cid": cid,
               "events": parse_sse(rq.text)}
    finally:
        _cleanup(api, teacher_headers)


def test_chain_skill_hit_meta(chain):
    """命中技能：meta 帧带技能名，且先于任何 delta。"""
    types = [e.get("type") for e in chain["events"]]
    assert "meta" in types, types
    meta = chain["events"][types.index("meta")]
    assert meta["skill"]["name"] == chain["skill_name"]
    if "delta" in types:
        assert types.index("meta") < types.index("delta")


def test_chain_tool_ok_audit(api, teacher_headers, chain):
    """模型提议调用 formula_hint → 真实 mcp-tools 返回 → meta.tool_calls 为 ok，调用记录可查。"""
    events = chain["events"]
    meta = next(e for e in events if e.get("type") == "meta")
    if any(e.get("type") == "error" for e in events):
        pytest.skip("AI 生成服务不可用（DeepSeek Key 未配置或无效），无法验证模型提议调用 → ok 审计")
    calls = [c for c in meta.get("tool_calls") or [] if c["ref"] == chain["ref"]]
    if not calls:
        pytest.skip("模型本次未提议调用 formula_hint（是否调用由模型决定，属合法行为），无法验证 ok 审计")
    assert all(c["status"] == "ok" for c in calls), calls

    r = api.get("/api/mcp/tool-calls", params={"class_id": CLASS_ID}, headers=teacher_headers)
    assert r.status_code == 200, r.text
    assert any(
        i["tool_ref"] == chain["ref"] and i["status"] == "ok" and i["conversation_id"] == chain["cid"]
        for i in r.json()["items"]
    )
