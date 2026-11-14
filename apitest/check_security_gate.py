"""P1-3：离线漏洞门禁反例，P0-5：真实发现分类，审计存储故障告警。"""
import io
import asyncio
import logging
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
import security_precheck as gate


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


def main():
    advisory = "GHSA-abcd-1234-efgh"
    raw = {"metadata": {"vulnerabilities": {"critical": 1, "high": 0, "total": 2}}, "vulnerabilities": {
        "direct": {"via": [{"url": "https://github.com/advisories/" + advisory}], "nodes": ["node_modules/direct"]},
        "parent": {"via": ["direct"], "nodes": ["node_modules/parent"]}}}
    lock = {"packages": {"node_modules/direct": {"version": "1.2.3"}, "node_modules/parent": {"version": "2.0.0"}}}
    summary = gate.summarize_npm_audit(raw, lock)
    deps = {"npm": summary}
    exc = [{"ecosystem": "npm", "package": n, "version": v["version"], "advisories": [advisory], "review_after": "2099-12-31"}
           for n, v in [("direct", lock["packages"]["node_modules/direct"]), ("parent", lock["packages"]["node_modules/parent"])]]
    with patch.object(gate, "load_exceptions", return_value=[]):
        missing, _ = gate.check_dependency_exceptions(deps)
        check("P1-3 失败：npm critical/high未登记必须红", missing == ["npm:direct", "npm:parent"])
    with patch.object(gate, "load_exceptions", return_value=exc):
        check("P1-3 正常：精确版本通告含传递引用可匹配", gate.check_dependency_exceptions(deps) == ([], []))
    for field, value in [("version", "9.9.9"), ("advisories", ["GHSA-aaaa-bbbb-cccc"]), ("review_after", "2000-01-01"), ("review_after", "invalid"), ("review_after", "")]:
        changed = [dict(e) for e in exc]
        changed[0][field] = value
        with patch.object(gate, "load_exceptions", return_value=changed):
            missing, expired = gate.check_dependency_exceptions(deps)
            check(f"P1-3 边界：{field}={value}不放行", "npm:direct" in missing)
    with patch.object(gate, "load_exceptions", return_value=exc):
        check("P1-3 失败：旧计数summary不得静默跳过", bool(gate.check_dependency_exceptions({"npm": {"critical": 1}})[0]))
        incomplete = gate.summarize_npm_audit(raw, {"packages": {}})
        check("P1-3 失败：锁文件无版本阻断", bool(gate.check_dependency_exceptions({"npm": incomplete})[0]))
        circular = {"metadata": raw["metadata"], "vulnerabilities": {"direct": {"via": ["direct"], "nodes": ["node_modules/direct"]}}}
        check("P1-3 边界：循环via不放行", bool(gate.check_dependency_exceptions({"npm": gate.summarize_npm_audit(circular, lock)})[0]))

    from mcp_client import McpClient, DiscoveredTool
    client = McpClient("http://mcp-tools:8090", "synthetic")
    tools = [{"name": name, "description": "合成工具", "inputSchema": {"type": "object"}, **other} for name, other in [
        ("formula_hint", {}), ("unit_convert", {"writable": True}),
        ("unknown", {"annotations": {"readOnlyHint": True}}), ("write_score", {})]]
    with patch.object(client, "_request", return_value={"tools": tools}):
        found, excluded = client.list_tools()
    check("P0-5 正常/边界：真实发现分类保守且不信远端只读声明", [t.writable for t in found] == [False, True, True, True] and not excluded)
    client = McpClient("http://other:8090", "synthetic")
    with patch.object(client, "_request", return_value={"tools": tools}):
        found, _ = client.list_tools()
    check("P0-5 失败：同名外部工具不能伪装内置只读", all(t.writable for t in found))
    check("P0-5 边界：未知DiscoveredTool默认可写", DiscoveredTool("unknown", "", {}).writable)

    with tempfile.TemporaryDirectory(prefix="audit-fault-") as tmp:
        os.environ.update(DATABASE_URL=f"sqlite:///{tmp}/fault.db", UPLOAD_DIR=f"{tmp}/uploads",
                          JWT_SECRET_KEY="check-only-jwt-secret-not-for-real-use-000000", DEEPSEEK_API_KEY="")
        import mcp_orchestrator as orchestrator
        import services
        import llm_service
        from database import Base, SessionLocal, engine
        Base.metadata.create_all(engine)
        class DecisionResponse:
            def __init__(self, usage): self.usage = usage
            def raise_for_status(self): pass
            def json(self): return {"choices": [{"message": {"content": "", "tool_calls": []}}], "usage": self.usage}
        for supplied, expected in [({"total_tokens": 37}, 37), (None, None), ({"total_tokens": True}, None),
                                   ({"total_tokens": -1}, None), ({"total_tokens": "37"}, None), ({"total_tokens": 0}, 0)]:
            with patch.object(llm_service.settings, "deepseek_api_key", "synthetic-test-key"), patch.object(llm_service.httpx, "post", return_value=DecisionResponse(supplied)):
                check("P1-2 决策轮用量：" + repr(supplied), llm_service.decide_with_tools([], []).tokens == expected)

        import httpx
        import main as application

        async def background_order():
            order = []
            async def observed(scope, receive, send):
                async def record_send(message):
                    if message["type"] == "http.response.body" and not message.get("more_body", False):
                        order.append("body-sent")
                    await send(message)
                await application.app(scope, receive, record_send)
            with patch.object(application, "_record_security_denial", side_effect=lambda *a: order.append("audit-write")):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=observed), base_url="http://test") as client:
                    response = await client.get("/api/materials")
            check("R2 审计异步：401响应正文发出后再写入", response.status_code == 401 and order == ["body-sent", "audit-write"])
        asyncio.run(background_order())

        output = io.StringIO()
        handler = logging.StreamHandler(output)
        class FailingSession:
            def __init__(self): self.rolled_back = False
            def add(self, row): pass
            def get(self, *args): return None
            def commit(self): raise RuntimeError("sensitive-exception-contents")
            def rollback(self): self.rolled_back = True
            def close(self): pass
        for module in (orchestrator, services):
            module.logger.addHandler(handler)
            module.logger.setLevel(logging.ERROR)
        try:
            session = FailingSession()
            with patch.object(orchestrator, "SessionLocal", return_value=session):
                orchestrator.record_call(class_id=101, subject="math", server_id=1, server_name="campus-tools", tool_name="formula_hint",
                    tool_ref="formula_hint@campus-tools", status="ok", user_id=None, conversation_id=None, round_no=1, detail="safe")
            check("审计故障：工具存储回滚且不中断", session.rolled_back)
            session = FailingSession()
            services.write_audit_log(session, user_id=None, role=None, request_path="/test", method="GET", status_code=401)
            check("审计故障：请求存储回滚且不中断", session.rolled_back)
            check("审计故障：告警可见且不泄露异常原文", output.getvalue().count("audit_write_failed") == 2 and "sensitive" not in output.getvalue())
        finally:
            for module in (orchestrator, services): module.logger.removeHandler(handler)
            engine.dispose()

    # 第10课：课程“高危 0 条”独立于例外登记；pip 未判级不能折算为 0。
    npm_high = {"npm": {"high": 1, "critical": 1, "vulnerabilities": {}}}
    check("第10课：npm high/critical 计数直接进入课程判据", gate.course_high_critical(npm_high) == (2, []))
    check("第10课：npm 明细缺失视为未判级",
          gate.course_high_critical({"npm": {"blocked": "x"}}) == (None, []))
    pip_vuln = {"npm": {"high": 0, "critical": 0, "vulnerabilities": {}},
                "backend": {"vulnerable_packages": 3}, "mcp": {"vulnerable_packages": 0}}
    check("第10课：pip 有漏洞但无严重度时阻塞而不是 0", gate.course_high_critical(pip_vuln) == (0, ["backend"]))
    check("第10课：全部为 0 才给出高危 0",
          gate.course_high_critical({"npm": {"high": 0, "critical": 0, "vulnerabilities": {}},
                                     "backend": {"vulnerable_packages": 0},
                                     "mcp": {"vulnerable_packages": 0}}) == (0, []))


if __name__ == "__main__":
    main()
