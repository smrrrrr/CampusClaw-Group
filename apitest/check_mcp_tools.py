"""MCP 工具集成隔离检查（add-mcp-tool-integration，对应 tasks 9.1）。

全部使用临时数据库 + 虚构模型桩 + 虚构 MCP 客户端，不访问真实 MCP 服务、不调用真实 AI、
不触碰演示数据。覆盖：管理接口权限、令牌不回传、连接失败/重复连接、引用保存期校验、
候选集与候选集外拒绝、调用上限（每问/轮次/会话累计）、ok/denied/error 三种记录与归属隔离、
令牌加解密与密钥轮换、地址白名单校验。

用法（在 backend 目录）：
    .venv/bin/python ../apitest/check_mcp_tools.py
"""

import asyncio
import json
import os
import tempfile

import httpx


async def main():
    with tempfile.TemporaryDirectory(prefix="mcp-test-", ignore_cleanup_errors=True) as temp:
        os.environ["DATABASE_URL"] = f"sqlite:///{temp}/test.db"
        os.environ["MCP_TOKEN_KEY"] = "3rSG9u0lJ_zU2C8pQc2F0bYQ0iZc1m1b2c3d4e5f6g8="
        os.environ["MCP_ALLOWED_HOSTS"] = "mcp-tools:8090"
        os.environ["MCP_AUTH_TOKEN"] = "server-token"

        # 必须在导入 config 前设置环境变量
        from database import Base, SessionLocal, engine
        from main import app
        from models import (
            AssistantSkill,
            Class,
            McpServer,
            McpTool,
            McpToolCall,
            Role,
            User,
        )
        from security import hash_password
        import mcp_crypto
        from mcp_client import DiscoveredTool, McpClientError
        import mcp_orchestrator
        from llm_service import DecisionResult, ToolCall, LLMGenerationError
        from config import settings
        from cryptography.fernet import Fernet

        Base.metadata.create_all(engine)

        with SessionLocal() as db:
            db.add_all([Class(id=101, name="Class A"), Class(id=102, name="Class B")])
            for ident, role, subject, classes, cid in [
                ("TM", Role.teacher, "math", "[101,102]", None),
                ("TP", Role.teacher, "physics", "[101,102]", None),
                ("TO", Role.teacher, "math", "[102]", None),
                ("S1", Role.student, None, None, 101),
                ("S2", Role.student, None, None, 102),
            ]:
                db.add(User(identifier=ident, role=role, subject=subject, teaching_classes=classes,
                            class_id=cid, name=ident, password_hash=hash_password("Test@2026"),
                            must_change_password=False))
            db.commit()

        checks = []

        def check(name, passed):
            checks.append((name, bool(passed)))
            if not passed:
                print(f"  ✗ {name}")
            else:
                print(f"  ✓ {name}")

        # ---- 虚构 MCP 客户端 ----
        class FakeClient:
            fail_connect = False
            tools = [
                DiscoveredTool("formula_hint", "数学公式与步骤提示", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}),
                DiscoveredTool("unit_convert", "物理单位换算提示", {"type": "object", "properties": {"from_unit": {"type": "string"}, "to_unit": {"type": "string"}}, "required": ["from_unit", "to_unit"]}),
            ]
            last_calls = []

            def __init__(self, base_url, token, timeout=10.0):
                self.base_url = base_url

            def connect_and_discover(self):
                if FakeClient.fail_connect:
                    raise McpClientError("连接超时")
                return FakeClient.tools, []

            def call_tool(self, name, arguments):
                FakeClient.last_calls.append((name, arguments))
                if name == "formula_hint":
                    return "余弦公式提示（只给公式，不给最终数值答案）", False
                return "换算关系提示", False

        mcp_orchestrator.McpClient = FakeClient
        import routers.mcp as mcp_router
        mcp_router.McpClient = FakeClient

        # ---- 虚构模型决策 ----
        decisions = []

        def fake_decide(messages, tools, timeout=None):
            if decisions:
                return decisions.pop(0)
            return DecisionResult(content="ok", tool_calls=[])

        mcp_orchestrator.decide_with_tools = fake_decide

        def frames(resp):
            assert resp.status_code == 200, (resp.status_code, resp.text)
            return [json.loads(line[5:]) for line in resp.text.splitlines() if line.startswith("data:")]

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {}
            for who in ["TM", "TP", "TO", "S1", "S2"]:
                r = await client.post("/api/auth/login", json={"identifier": who, "password": "Test@2026"})
                headers[who] = {"Authorization": "Bearer " + r.json()["access_token"]}

            async def req(method, path, who="TM", **kw):
                return await client.request(method, path, headers=headers[who], **kw)

            # === 管理接口权限 ===
            for path in ("/api/mcp/servers?class_id=101", "/api/teacher/skills?class_id=101", "/api/mcp/tool-calls?class_id=101"):
                r = await client.get(path)
                check(f"未登录访问 {path.split('?')[0]} 401", r.status_code == 401)
            r = await req("GET", "/api/mcp/servers?class_id=101", "S1")
            check("学生访问管理接口 403", r.status_code == 403)
            r = await req("GET", "/api/mcp/servers?class_id=999", "TM")
            check("非任教班级 403", r.status_code == 403)

            # === SSRF ===
            for bad in ("http://127.0.0.1:8000", "http://169.254.169.254", "http://backend:8000"):
                r = await req("POST", "/api/mcp/servers", json={"class_id": 101, "name": "bad", "base_url": bad, "auth_token": "x"})
                check(f"拒绝地址 {bad}", r.status_code == 400)

            # === 登记 ===
            r = await req("POST", "/api/mcp/servers", json={"class_id": 101, "name": "campus-tools", "base_url": "http://mcp-tools:8090", "auth_token": "secret-token"})
            check("登记服务器 201", r.status_code == 201)
            srv = r.json()
            check("响应不含令牌", "secret-token" not in json.dumps(srv, ensure_ascii=False))
            check("has_auth=true", srv["has_auth"] is True and srv["connected"] is False)
            sid = srv["id"]

            r = await req("POST", "/api/mcp/servers", json={"class_id": 101, "name": "campus-tools", "base_url": "http://mcp-tools:8090", "auth_token": "x"})
            check("同名再登记 400", r.status_code == 400)

            # === 连接失败 502 且置未连接 ===
            FakeClient.fail_connect = True
            r = await req("POST", f"/api/mcp/servers/{sid}/connect")
            check("连接失败 502", r.status_code == 502)
            r = await req("GET", "/api/mcp/servers?class_id=101")
            check("失败后 connected=false", r.json()["items"][0]["connected"] is False)
            FakeClient.fail_connect = False

            # === 连接成功 + 重复连接不翻倍 ===
            r = await req("POST", f"/api/mcp/servers/{sid}/connect")
            check("连接成功 200", r.status_code == 200 and r.json()["server"]["connected"] is True)
            await req("POST", f"/api/mcp/servers/{sid}/connect")
            r = await req("GET", f"/api/mcp/servers/{sid}/tools")
            check("重复连接工具不翻倍", len(r.json()["items"]) == 2)

            # === 归属隔离 ===
            r = await req("GET", f"/api/mcp/servers/{sid}/tools", "TP")
            check("同伴读取他人服务器 404", r.status_code == 404)
            r = await req("GET", "/api/mcp/servers?class_id=101", "TP")
            check("同伴列表不含他人服务器", r.json()["items"] == [])
            r = await req("GET", "/api/mcp/servers/999999/tools", "TM")
            check("不存在编号 404", r.status_code == 404)
            r = await req("POST", f"/api/mcp/servers/{sid}/connect", "S1")
            check("学生连接服务器 403", r.status_code == 403)

            # === 技能保存期校验 ===
            ok_src = "名称：公式提示\n适用条件：夹角,公式\n工具：formula_hint@campus-tools\n启用：是\n\n求夹角时给公式与步骤提示，不直接给答案。"
            r = await req("POST", "/api/teacher/skills", json={"class_id": 101, "source": ok_src})
            check("技能保存成功 201", r.status_code == 201)
            skill_id = r.json()["id"]

            bad_cases = {
                "启用写开启": "名称：x\n适用条件：y\n工具：formula_hint@campus-tools\n启用：开启\n\n说明",
                "工具引用非法": "名称：x\n适用条件：y\n工具：formula-hint@campus-tools\n启用：是\n\n说明",
                "缺空行": "名称：x\n适用条件：y\n工具：formula_hint@campus-tools\n启用：是",
                "未知字段": "名称：x\n未知：z\n适用条件：y\n工具：formula_hint@campus-tools\n启用：是\n\n说明",
                "引用不存在服务器": "名称：x\n适用条件：y\n工具：formula_hint@nope\n启用：是\n\n说明",
            }
            for label, src in bad_cases.items():
                r = await req("POST", "/api/teacher/skills", json={"class_id": 101, "source": src})
                check(f"技能校验：{label} 400", r.status_code == 400)

            r = await req("POST", "/api/teacher/skills", json={"class_id": 101, "source": ok_src})
            check("技能重名 400", r.status_code == 400)
            r = await req("GET", "/api/teacher/skills?class_id=101", "S1")
            check("学生访问技能接口 403", r.status_code == 403)
            r = await req("DELETE", f"/api/teacher/skills/{skill_id}", "TP")
            check("同伴删他人技能 404", r.status_code == 404)

            # === 调用编排：命中技能 → 模型提议调用 → ok ===
            r = await req("POST", "/api/student/conversations", "S1", json={"title": "t", "subject": "math"})
            check("学生建会话", r.status_code == 200)
            cid = r.json()["id"]

            decisions.clear()
            decisions.append(DecisionResult(content="", tool_calls=[ToolCall(id="c1", name="formula_hint", arguments={"query": "两向量夹角"})]))
            FakeClient.last_calls.clear()
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "S1", json={"question": "两向量夹角怎么求"})
            fr = frames(r)
            types = [f.get("type") for f in fr]
            meta = next((f for f in fr if f.get("type") == "meta"), None)
            check("meta 事件先于 delta", meta is not None and types.index("meta") < (types.index("delta") if "delta" in types else len(types)))
            check("meta 含技能名", meta and meta.get("skill", {}).get("name") == "公式提示")
            tcs = (meta or {}).get("tool_calls") or []
            check("meta.tool_calls 记录 ok", len(tcs) == 1 and tcs[0]["status"] == "ok" and tcs[0]["ref"] == "formula_hint@campus-tools")
            check("确实带令牌调用了工具", len(FakeClient.last_calls) == 1)

            with SessionLocal() as db:
                calls = db.query(McpToolCall).filter(McpToolCall.conversation_id == cid).all()
                check("写入 ok 审计记录", len(calls) == 1 and calls[0].status == "ok" and calls[0].tool_ref == "formula_hint@campus-tools")

            # === 断开后同一技能 → denied ===
            await req("POST", f"/api/mcp/servers/{sid}/disconnect")
            # 重新建技能（断开后保存期校验会拒绝，故直接改数据库模拟已存在技能）
            with SessionLocal() as db:
                sk = db.query(AssistantSkill).filter(AssistantSkill.id == skill_id).one()
                sk.enabled = True
                db.commit()
            decisions.clear()
            decisions.append(DecisionResult(content="", tool_calls=[]))
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "S1", json={"question": "夹角怎么算"})
            fr = frames(r)
            meta = next((f for f in fr if f.get("type") == "meta"), None)
            tcs = (meta or {}).get("tool_calls") or []
            check("断开后引用记 denied", any(t["ref"] == "formula_hint@campus-tools" and t["status"] == "denied" for t in tcs))
            with SessionLocal() as db:
                denied = db.query(McpToolCall).filter(McpToolCall.conversation_id == cid, McpToolCall.status == "denied").all()
                check("写入 denied 审计记录", len(denied) >= 1)

            # === 参数不合结构 → error ===
            await req("POST", f"/api/mcp/servers/{sid}/connect")
            decisions.clear()
            decisions.append(DecisionResult(content="", tool_calls=[ToolCall(id="c2", name="formula_hint", arguments={"wrong": 1})]))
            FakeClient.last_calls.clear()
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "S1", json={"question": "夹角再次"})
            fr = frames(r)
            meta = next((f for f in fr if f.get("type") == "meta"), None)
            tcs = (meta or {}).get("tool_calls") or []
            check("参数不符记 error 且未执行", any(t["status"] == "error" for t in tcs) and len(FakeClient.last_calls) == 0)
            with SessionLocal() as db:
                errs = db.query(McpToolCall).filter(McpToolCall.conversation_id == cid, McpToolCall.status == "error").all()
                check("写入 error 审计记录", len(errs) >= 1)

            # === 多轮调用：循环结束后只推送一次 meta ===
            decisions.clear()
            decisions.extend(
                DecisionResult(content="", tool_calls=[ToolCall(id=f"m{i}", name="formula_hint", arguments={"query": f"夹角{i}"})])
                for i in (1, 2)
            )
            FakeClient.last_calls.clear()
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "S1", json={"question": "夹角多轮"})
            fr = frames(r)
            types = [f.get("type") for f in fr]
            metas = [f for f in fr if f.get("type") == "meta"]
            tcs = (metas[0] if metas else {}).get("tool_calls") or []
            # 测试环境未配 Key 时正文走 error 降级帧，故断言 meta 为首帧（先于任何 delta/done/error）
            check("两轮调用只推送一次 meta 且为首帧", len(metas) == 1 and types[0] == "meta")
            check("meta.tool_calls 按序含两轮 ok 记录",
                  [t["status"] for t in tcs] == ["ok", "ok"] and len(FakeClient.last_calls) == 2)

            # === 调用记录归属隔离 ===
            r = await req("GET", "/api/mcp/tool-calls?class_id=101", "TM")
            check("教师可见本人记录", len(r.json()["items"]) >= 3)
            r = await req("GET", "/api/mcp/tool-calls?class_id=101", "TP")
            check("同伴看不到我的记录", r.json()["items"] == [])
            r = await req("GET", "/api/mcp/tool-calls?class_id=101", "S1")
            check("学生访问调用记录 403", r.status_code == 403)

            # === 未命中技能：无 meta，行为不变 ===
            decisions.clear()
            with SessionLocal() as db:
                db.query(AssistantSkill).update({"enabled": False})
                db.commit()
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "S1", json={"question": "今天天气"})
            fr = frames(r)
            check("未命中技能不发 meta", all(f.get("type") != "meta" for f in fr))

        # === 令牌加解密与密钥轮换（tasks 2.2） ===
        enc = mcp_crypto.encrypt_token("secret-token")
        check("令牌密文不含原文且可解回",
              "secret-token" not in enc and mcp_crypto.decrypt_token(enc) == "secret-token")
        old_key = settings.mcp_token_key
        settings.mcp_token_key = Fernet.generate_key().decode()
        try:
            mcp_crypto.decrypt_token(enc)
            check("换密钥后解密失败并提示重新填写令牌", False)
        except mcp_crypto.TokenDecryptError as exc:
            check("换密钥后解密失败并提示重新填写令牌", "请重新填写令牌" in str(exc))
        settings.mcp_token_key = ""
        try:
            mcp_crypto.encrypt_token("x")
            check("未配置 MCP_TOKEN_KEY 拒绝保存令牌", False)
        except mcp_crypto.TokenKeyNotConfigured:
            check("未配置 MCP_TOKEN_KEY 拒绝保存令牌", True)
        settings.mcp_token_key = old_key

        # === 地址白名单校验（不发请求） ===
        for bad in ("http://localhost:8090", "http://10.0.0.5:8090", "ftp://mcp-tools:8090",
                    "http://user:pw@mcp-tools:8090", "http://metadata.google.internal", "http://evil.com:8090"):
            try:
                mcp_crypto.validate_base_url(bad)
                check(f"地址校验拒绝 {bad}", False)
            except ValueError:
                check(f"地址校验拒绝 {bad}", True)
        check("白名单地址通过并去掉末尾斜杠",
              mcp_crypto.validate_base_url("http://mcp-tools:8090/") == "http://mcp-tools:8090")

        # === 调用上限与候选集外（直接驱动 run_tool_loop） ===
        candidates = [{
            "ref": "formula_hint@campus-tools", "tool_name": "formula_hint", "server_id": sid,
            "server_name": "campus-tools", "base_url": "http://mcp-tools:8090", "description": "公式提示",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }]

        def proposal(n, name="formula_hint"):
            return [ToolCall(id=f"p{i}", name=name, arguments={"query": "夹角"}) for i in range(n)]

        def run_loop(proposals, conversation_id):
            decisions.clear()
            decisions.extend(DecisionResult(content="", tool_calls=p) for p in proposals)
            FakeClient.last_calls.clear()
            with SessionLocal() as db:
                events = mcp_orchestrator.run_tool_loop(
                    db, skill=None, candidates=candidates, denied=[], messages=[],
                    class_id=101, subject="math", user_id=1, conversation_id=conversation_id,
                )[0]
            return events

        per_q = settings.mcp_max_calls_per_question
        events = run_loop([proposal(per_q + 2)], 9001)
        check(f"每问上限 {per_q}：只执行 {per_q} 次，其余 denied",
              len(FakeClient.last_calls) == per_q and [e["status"] for e in events].count("denied") == 2)
        with SessionLocal() as db:
            check("超出每问上限的调用写 denied 审计",
                  db.query(McpToolCall).filter_by(conversation_id=9001, status="denied").count() == 2)

        rounds = settings.mcp_max_rounds
        run_loop([proposal(1) for _ in range(rounds + 2)], 9002)
        check(f"决策轮次上限 {rounds}：只执行 {rounds} 次", len(FakeClient.last_calls) == rounds)

        per_conv = settings.mcp_max_calls_per_conversation
        with SessionLocal() as db:
            for _ in range(per_conv - 1):
                db.add(McpToolCall(class_id=101, subject="math", server_id=sid, server_name="campus-tools",
                                   tool_name="formula_hint", tool_ref="formula_hint@campus-tools", status="ok",
                                   user_id=1, conversation_id=9003, round=1))
            db.commit()
        run_loop([proposal(3)], 9003)
        check(f"会话累计上限 {per_conv}：已有 {per_conv - 1} 次时只再执行 1 次", len(FakeClient.last_calls) == 1)

        with SessionLocal() as db:
            before = db.query(McpToolCall).count()
        events = run_loop([proposal(1, "rm_rf")], 9004)
        with SessionLocal() as db:
            after = db.query(McpToolCall).count()
        check("候选集外工具 denied、不执行、不写审计",
              not FakeClient.last_calls and events and events[0]["status"] == "denied" and after == before)

        # ---- OpenAPI：403 由路由器级统一声明，路由级不再覆盖成别的文案 ----
        ops = [(path, method, op) for path, item in app.openapi()["paths"].items()
               if path.startswith(("/api/mcp", "/api/teacher/skills")) for method, op in item.items()]
        bad_403 = [f"{m.upper()} {p}" for p, m, op in ops
                   if op.get("responses", {}).get("403", {}).get("description") != "非教师或非任教班级"]
        check(f"OpenAPI：MCP/技能 {len(ops)} 个接口的 403 说明统一为路由器级口径", ops and not bad_403)
        create_op = app.openapi()["paths"]["/api/mcp/servers"]["post"]["responses"]
        check("OpenAPI：登记服务器仍保留特有的 400 说明", "400" in create_op and "401" in create_op)

        print(f"\n结果：{sum(1 for _, ok in checks if ok)}/{len(checks)} 通过")
        failed = [n for n, ok in checks if not ok]
        if failed:
            print("失败项：", failed)
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
