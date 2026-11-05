"""课程安全基线探针：临时库、合成身份、假模型/MCP；红项返回1，不改业务实现。"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


async def run(output, mutate_access=False):
    import httpx
    from cryptography.fernet import Fernet

    rows = []
    def record(case, expected, actual, passed):
        rows.append(dict(case=case, expected=expected, actual=actual, passed=bool(passed)))

    with tempfile.TemporaryDirectory(prefix="security-precheck-", ignore_cleanup_errors=True) as tmp:
        os.environ.update(DATABASE_URL=f"sqlite:///{tmp}/audit.db", UPLOAD_DIR=f"{tmp}/uploads",
                          JWT_SECRET_KEY="check-only-jwt-secret-not-for-real-use-000000",
                          DEEPSEEK_API_KEY="", DEEPSEEK_BASE_URL="http://127.0.0.1:9/v1",
                          MCP_TOKEN_KEY=Fernet.generate_key().decode(), MCP_ALLOWED_HOSTS="mcp-tools:8090",
                          MCP_TOOLS_HEALTH_URL="", MCP_AUTH_TOKEN="synthetic-test-token")
        from database import Base, SessionLocal, engine
        from main import app
        from models import (Class, User, Role, Material, MaterialChunk, AuditLog, AgentConfig,
                            AssistantSkill, HomeworkSubmission, GradeTask, McpToolCall, McpServer, MistakeNote)
        from security import hash_password
        from embedding_service import embed_text
        from rag_search_service import serialize_vector
        from routers import student, mcp, materials
        from mcp_client import DiscoveredTool
        from llm_service import DecisionResult, ToolCall
        import mcp_orchestrator

        Base.metadata.create_all(engine)
        identities = [("TEA001", Role.teacher, None, "math", "[101,102]", 101),
                      ("TEA002", Role.teacher, None, "physics", "[101,102]", 102),
                      ("20260001", Role.student, 101, None, None, None),
                      ("20260002", Role.student, 102, None, None, None)]
        with SessionLocal() as db:
            db.add_all([Class(id=101, name="合成A班"), Class(id=102, name="合成B班")])
            db.flush()
            for ident, role, cid, subject, classes, head in identities:
                db.add(User(identifier=ident, name=ident, role=role, class_id=cid, subject=subject,
                            teaching_classes=classes, homeroom_class_id=head,
                            password_hash=hash_password("Test@2026"), must_change_password=False))
            db.commit()
            ids = {u.identifier: u.id for u in db.query(User)}
            for mid, cid, text in [(1, 101, "A班专属的两向量夹角公式合成资料。青松赤壁虹桥定理演示"),
                                   (2, 102, "B班专属的两向量夹角公式合成资料")]:
                data = text.encode()
                rel = f"{cid}/synthetic.txt"
                path = Path(tmp) / "uploads" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                db.add(Material(id=mid, class_id=cid, uploader_id=ids["TEA001"], filename="向量夹角公式.txt",
                                file_path=rel, file_type="text/plain", file_size=len(data),
                                source_sha256=hashlib.sha256(data).hexdigest(), is_indexed=True))
                db.flush()
                db.add(MaterialChunk(material_id=mid, class_id=cid, chunk_index=0, content=text,
                                     embedding=serialize_vector(embed_text(text))))
            db.commit()

        # 故意改坏仅限本进程临时应用，用于证明探针能发现越权，磁盘源码不变。
        if mutate_access:
            materials._check_material_access = lambda *args, **kwargs: None

        class FakeClient:
            calls = 0
            def __init__(self, base_url, token, timeout=10):
                pass
            def connect_and_discover(self):
                return [DiscoveredTool("formula_hint", "合成公式提示", {"type": "object", "properties": {
                    "query": {"type": "string"}}, "required": ["query"], "additionalProperties": False})], []
            def call_tool(self, name, arguments):
                FakeClient.calls += 1
                return "合成公式提示数据", False
        mcp_orchestrator.McpClient = mcp.McpClient = FakeClient
        decisions = []
        mcp_orchestrator.decide_with_tools = lambda *a, **k: decisions.pop(0) if decisions else DecisionResult(content="ok", tool_calls=[])
        async def fake_stream(messages):
            yield "合成回答，参考资料[1]。"
        student.stream_chat = fake_stream

        def snapshot():
            # 只比较业务状态，403审计新增是预期副作用；不输出原始行。
            with SessionLocal() as db:
                state = []
                for model in (AgentConfig, AssistantSkill, HomeworkSubmission, GradeTask, McpServer, MistakeNote):
                    state.append([(tuple(getattr(r, c.name) for c in model.__table__.columns))
                                  for r in db.query(model).order_by(model.id)])
                return hashlib.sha256(repr(state).encode()).hexdigest()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://audit.local") as client:
            headers = {}
            for ident, *_ in identities:
                r = await client.post("/api/auth/login", json={"identifier": ident, "password": "Test@2026"})
                record("PRE 登录 " + ident, 200, r.status_code, r.status_code == 200)
                if r.status_code != 200:
                    raise RuntimeError("合成身份无法登录；不能继续权限测试")
                headers[ident] = {"Authorization": "Bearer " + r.json()["access_token"]}
            async def req(method, path, who="TEA001", **kw):
                return await client.request(method, path, headers=headers[who], **kw)
            protected = ["/api/materials", "/api/student/homeworks", "/api/teacher/students?class_id=101",
                         "/api/teacher/agent-config?class_id=101", "/api/teacher/skills?class_id=101",
                         "/api/mcp/servers?class_id=101", "/api/mcp/tool-calls?class_id=101"]
            # 清除登录留下的refresh cookie；无Token请求完全不携带身份。
            client.cookies.clear()
            for path in protected:
                r = await client.get(path)
                record("SEC-01 GET " + path, 401, r.status_code, r.status_code == 401)
            r = await req("GET", "/api/materials/1/download", "20260001")
            record("SEC-02 本班资料正例", "200且含A班正文", {"http": r.status_code, "own_body": "A班专属" in r.text},
                   r.status_code == 200 and "A班专属" in r.text)
            with SessionLocal() as db:
                before_audit = db.query(AuditLog).count()
            r = await req("GET", "/api/materials/2/download", "20260001")
            with SessionLocal() as db:
                audited = db.query(AuditLog).count() > before_audit
            record("SEC-02 跨班资料项目合同", "403、无B班正文、有审计", {"http": r.status_code, "body_leaked": "B班专属" in r.text, "audited": audited},
                   r.status_code == 403 and "B班专属" not in r.text and audited)
            record("SEC-02 跨班资料课程口径", 404, r.status_code, r.status_code == 404)
            # 经真实聊天入口检索；先确认A班确实能命中，B班同问不能得到A班引用。
            for who, own, other in [("20260001", 1, 2), ("20260002", 2, 1)]:
                r = await req("POST", "/api/student/conversations", who, json={"title": "合成检索", "subject": "math"})
                cid = r.json()["id"]
                r = await req("POST", f"/api/student/conversations/{cid}/chat", who, json={"question": "两向量夹角公式"})
                events = [json.loads(s[5:]) for s in r.text.splitlines() if s.startswith("data:")]
                done = next((e for e in events if e.get("type") == "done"), {})
                found = [c["material_id"] for c in done.get("citations", [])]
                record("SEC-02 检索 " + who, f"本班{own}命中，他班{other}为空", {"http": r.status_code, "material_ids": found},
                       r.status_code == 200 and own in found and other not in found)

            for who in ("20260001", "20260002"):
                r = await req("POST", "/api/student/conversations", who, json={"title": "合成A班独有知识", "subject": "math"})
                cid = r.json()["id"]
                r = await req("POST", f"/api/student/conversations/{cid}/chat", who, json={"question": "青松赤壁虹桥定理"})
                events = [json.loads(s[5:]) for s in r.text.splitlines() if s.startswith("data:")]
                done = next((e for e in events if e.get("type") == "done"), None)
                found = [c["material_id"] for c in (done or {}).get("citations", [])]
                expected = [1] if who == "20260001" else []
                record("SEC-02 A班独有知识 " + who, expected, {"http": r.status_code, "material_ids": found},
                       r.status_code == 200 and done is not None and found == expected)

            r = await req("POST", "/api/mcp/servers", json={"class_id": 101, "name": "campus-tools", "base_url": "http://mcp-tools:8090", "auth_token": "synthetic-test-token"})
            assert r.status_code == 201, "合成服务器建立失败"
            sid = r.json()["id"]
            r = await req("POST", f"/api/mcp/servers/{sid}/connect")
            assert r.status_code == 200, "合成工具发现失败"
            source = "名称：合成公式提示\n适用条件：夹角,公式\n工具：formula_hint@campus-tools\n启用：是\n\n仅使用合成公式提示。"
            r = await req("POST", "/api/teacher/skills", json={"class_id": 101, "source": source})
            assert r.status_code == 201, "合成技能建立失败"
            skill_id = r.json()["id"]
            for method, path, body in [
                ("PUT", "/api/teacher/agent-config", {"class_id": 101, "system_prompt": "合成非法修改", "tutor_enabled": False}),
                ("POST", "/api/teacher/skills", {"class_id": 101, "source": source.replace("合成公式提示", "合成新技能")}),
                ("PUT", f"/api/teacher/skills/{skill_id}", {"source": source.replace("合成公式提示", "合成非法修改")}),
                ("POST", "/api/mcp/servers", {"class_id": 101, "name": "student-write", "base_url": "http://mcp-tools:8090"})]:
                before = snapshot()
                r = await req(method, path, "20260001", json=body)
                unchanged = before == snapshot()
                record("SEC-03 " + method + " " + path, "403且业务状态不变", {"http": r.status_code, "unchanged": unchanged}, r.status_code == 403 and unchanged)

            r = await req("POST", "/api/teacher/homeworks", json={"class_id": 101, "title": "合成安全验收",
                "content": json.dumps({"stem": "合成题目"}), "due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()})
            assert r.status_code == 200, "合成作业建立失败"
            hid = r.json()["id"]
            assert (await req("PUT", f"/api/teacher/homeworks/{hid}/publish")).status_code == 200
            r = await req("POST", f"/api/student/homeworks/{hid}/submit", "20260001", json={"answer_text": "合成答案"})
            assert r.status_code == 200, "合成提交失败"
            subid = r.json()["id"]
            for method, path, body in [("PUT", f"/api/teacher/submissions/{subid}/grade", {"score": 100, "feedback": "非法自评"}),
                                       ("POST", f"/api/teacher/homeworks/{hid}/ai-grade", None)]:
                before = snapshot()
                r = await req(method, path, "20260001", **({"json": body} if body else {}))
                unchanged = before == snapshot()
                record("SEC-04 " + method + " " + path, "403、分数和任务不变", {"http": r.status_code, "unchanged": unchanged}, r.status_code == 403 and unchanged)

            r = await req("POST", "/api/student/conversations", "20260001", json={"title": "合成Skill调用", "subject": "math"})
            cid = r.json()["id"]
            decisions.append(DecisionResult(content="", tool_calls=[ToolCall(id="synthetic-call", name="formula_hint", arguments={"query": "夹角"})]))
            r = await req("POST", f"/api/student/conversations/{cid}/chat", "20260001", json={"question": "两向量夹角公式"})
            events = [json.loads(s[5:]) for s in r.text.splitlines() if s.startswith("data:")]
            meta = next((e for e in events if e.get("type") == "meta"), {})
            invoked = FakeClient.calls == 1 and meta.get("skill", {}).get("name") == "合成公式提示"
            r = await req("GET", "/api/mcp/tool-calls?class_id=101")
            calls = [c for c in r.json()["items"] if c.get("conversation_id") == cid]
            record("SEC-07 实际合成技能执行", "执行一次且日志actor/status正确", {"calls": FakeClient.calls, "meta_skill": meta.get("skill"), "log_count": len(calls)},
                   invoked and len(calls) == 1 and calls[0].get("user_id") == ids["20260001"] and calls[0].get("status") == "ok")
            with SessionLocal() as db:
                persisted = db.query(McpToolCall).filter_by(conversation_id=cid).count()
            fields = set(calls[0]) if calls else set()
            missing = []
            for label, alternatives in {"skill_identifier": {"skill_id", "skill_name", "skill"}, "duration": {"duration_ms", "duration"},
                                        "usage": {"usage", "total_tokens", "token_usage"}}.items():
                if not fields.intersection(alternatives):
                    missing.append(label)
            record("SEC-07 持久日志字段", "actor、skill、status、duration、usage齐全", {"persisted_rows": persisted,
                "response_fields": sorted(fields), "model_fields": list(McpToolCall.__table__.columns.keys()), "missing": missing},
                persisted == 1 and invoked and not missing)
        engine.dispose()
    result = {"time": datetime.now(timezone.utc).isoformat(), "scope": "temporary SQLite + fake LLM/MCP; no production writes",
              "mutation": mutate_access, "checks": rows, "passed": sum(r["passed"] for r in rows), "failed": sum(not r["passed"] for r in rows)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"安全探针：{result['passed']}通过，{result['failed']}红项；证据 {output}")
    return int(result["failed"] > 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/security-evidence/api-probe.json")
    parser.add_argument("--mutate-access", action="store_true")
    args = parser.parse_args()
    try:
        code = asyncio.run(run(args.output, args.mutate_access))
    except Exception as exc:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"error": type(exc).__name__, "status": "BLOCKED",
            "time": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
        print("探针执行未完成，异常类型：" + type(exc).__name__)
        code = 2
    sys.exit(code)
