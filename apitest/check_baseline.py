"""工程基线回归：健康检查、请求标识与 JSON 日志、必填配置、门禁脚本（2026-10-28-engineering-baseline）。

每条检查名前的 R 编号对应规约 runtime-reliability 增量中的场景：
  R1 健康检查  R2 请求标识与日志  R3 必填配置  R4 一键门禁  R5 规范常驻
按正常路径 / 失败路径 / 边界三类组织。临时数据库、假的 MCP 探测，不连外网、不调用模型。

用法（项目根）：make check，或
  JWT_SECRET_KEY=<至少 32 字符> PYTHONPATH=backend backend/.venv/bin/python apitest/check_baseline.py
"""

import importlib.util
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
HEX32 = re.compile(r"^[0-9a-f]{32}$")
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_probe(jwt_value):
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    if jwt_value is not None:
        env["JWT_SECRET_KEY"] = jwt_value
    # 工作目录 backend 下没有 .env，只看环境变量
    return subprocess.run([sys.executable, "-c", "import config"], cwd=BACKEND, env=env, capture_output=True, text=True)


with tempfile.TemporaryDirectory(prefix="baseline-test-") as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'baseline.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")

    import httpx
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    import main
    from config import settings
    from database import Base, SessionLocal, engine
    from logging_setup import JsonFormatter
    from models import Class, Role, User
    from security import create_access_token, hash_password
    from version import APP_VERSION

    Base.metadata.create_all(engine)
    db = SessionLocal()
    db.add(Class(id=102, name="二班"))
    student = User(role=Role.student, identifier="20260002", password_hash=hash_password("Student@2026"),
                   name="王芳", class_id=102, must_change_password=False)
    db.add(student)
    db.commit()
    student_token = create_access_token(user_id=student.id, role="student", class_id=102, must_change_password=False)
    db.close()

    log_buffer = io.StringIO()
    capture = logging.StreamHandler(log_buffer)
    capture.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(capture)

    def log_lines():
        return [line for line in log_buffer.getvalue().splitlines() if line.strip()]

    def access_entries():
        entries = []
        for line in log_lines():
            entry = json.loads(line)
            if entry.get("module") == "access":
                entries.append(entry)
        return entries

    class FakeResponse:
        def __init__(self, status):
            self.is_success = 200 <= status < 300

    probe_calls = []

    def fake_get(result):
        def _get(url, timeout):
            probe_calls.append((url, timeout))
            if isinstance(result, Exception):
                raise result
            return FakeResponse(result)
        return _get

    @main.app.get("/api/__baseline_probe_log")
    def _probe_log():
        logging.getLogger("lesson_service").info("基线探针日志")
        return {"ok": True}

    @main.app.get("/api/__baseline_probe_error")
    def _probe_error():
        raise RuntimeError("secret-internal-detail")

    MCP_URL = "http://mcp-tools.internal:8090/health"
    original_get = main.httpx.get
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            # ---------- R1 健康检查 ----------
            settings.mcp_tools_health_url = MCP_URL
            settings.deepseek_api_key = "test-key"
            main.httpx.get = fake_get(200)
            with engine.connect() as conn:
                users_before = conn.execute(text("SELECT count(*) FROM users")).scalar()
            response = client.get("/api/health")
            body = response.json()
            with engine.connect() as conn:
                users_after = conn.execute(text("SELECT count(*) FROM users")).scalar()
            check("R1 正常：未带令牌 200，status=ok", response.status_code == 200 and body.get("status") == "ok")
            check("R1 正常：version 等于 version.py", body.get("version") == APP_VERSION)
            check("R1 正常：time 为 UTC 且以 Z 结尾", re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", body.get("time", "")) is not None)
            check("R1 正常：三项依赖为 ok/ok/configured",
                  body.get("dependencies") == {"database": "ok", "mcp_tools": "ok", "model": "configured"})
            check("R1 正常：MCP 探测超时为 2 秒", probe_calls and probe_calls[-1] == (MCP_URL, 2.0))
            check("R1 正常：不写业务记录", users_before == users_after)
            check("R1 正常：响应不含探测地址", "mcp-tools.internal" not in response.text)

            for label, result in (("超时", httpx.ConnectTimeout("timeout")), ("返回 500", 500)):
                main.httpx.get = fake_get(result)
                response = client.get("/api/health")
                body = response.json()
                check(f"R1 失败：MCP {label} → 200 且 degraded/unreachable",
                      response.status_code == 200 and body["status"] == "degraded" and body["dependencies"]["mcp_tools"] == "unreachable")
                check(f"R1 失败：MCP {label} 时响应不含地址", "mcp-tools.internal" not in response.text and "8090" not in response.text)

            settings.mcp_tools_health_url = ""
            settings.deepseek_api_key = ""
            probe_calls.clear()
            response = client.get("/api/health")
            body = response.json()
            check("R1 边界：未配置 → mcp_tools/model 均为 not_configured 且 status=ok",
                  body["status"] == "ok" and body["dependencies"]["mcp_tools"] == "not_configured"
                  and body["dependencies"]["model"] == "not_configured")
            check("R1 边界：未配置时不发起出站探测", probe_calls == [])

            response = client.get("/api/health", headers={"Authorization": "Bearer forged-token"})
            body = response.json()
            check("R1 失败：伪造令牌仍 200，且不含用户信息",
                  response.status_code == 200 and set(body) == {"status", "version", "time", "dependencies"}
                  and not any(word in response.text for word in ("user", "role", "class")))

            original_engine = main.engine

            class BrokenEngine:
                def connect(self):
                    raise OperationalError("SELECT id FROM users /app/data/campusclaw.db", {}, Exception("private database error"))

            main.engine = BrokenEngine()
            try:
                response = client.get("/api/health")
            finally:
                main.engine = original_engine
            check("R1 失败：数据库异常 → 503 与通用提示",
                  response.status_code == 503 and response.json().get("detail") == "数据库暂不可用，请稍后重试")
            check("R1 失败：503 响应不含 SQL、路径与异常原文",
                  not any(word in response.text for word in ("SELECT", "/app/data", "private database error")))

            # ---------- R2 请求标识与日志 ----------
            log_buffer.seek(0)
            log_buffer.truncate()
            response = client.get("/api/health?probe=1")
            rid = response.headers.get("x-request-id", "")
            entries = [e for e in access_entries() if e.get("request_id") == rid]
            check("R2 正常：无请求头时生成 32 位十六进制标识", HEX32.match(rid) is not None)
            check("R2 正常：恰好一行访问日志且标识一致", len(entries) == 1)
            entry = entries[0] if entries else {}
            check("R2 正常：访问日志字段齐全",
                  {"ts", "level", "module", "request_id", "method", "path", "status", "duration_ms"} <= set(entry))
            check("R2 正常：path 不含查询串，status=200", entry.get("path") == "/api/health" and entry.get("status") == 200)
            check("R2 正常：日志全文不含查询参数", "probe=1" not in log_buffer.getvalue())
            check("R2 正常：每行日志都是合法 JSON", all(json.loads(line) is not None for line in log_lines()))

            response = client.get("/api/health", headers={"X-Request-ID": "lesson07-trace-0001"})
            check("R2 正常：采纳合法的调用方标识", response.headers.get("x-request-id") == "lesson07-trace-0001")
            check("R2 正常：访问日志使用调用方标识",
                  any(e.get("request_id") == "lesson07-trace-0001" for e in access_entries()))

            for label, raw in (("7 个字符含 +", "abc+def"), ("65 个字符", "a" * 65)):
                response = client.get("/api/health", headers={"X-Request-ID": raw})
                new_id = response.headers.get("x-request-id", "")
                check(f"R2 边界：非法标识（{label}）被替换为新生成值", HEX32.match(new_id) is not None and new_id != raw)
                check(f"R2 边界：非法标识（{label}）原值不进日志", raw not in log_buffer.getvalue())
            response = client.get("/api/health", headers={"X-Request-ID": "a" * 64})
            check("R2 边界：64 个字符的标识被采纳", response.headers.get("x-request-id") == "a" * 64)

            response = client.get("/api/teacher/classes")
            rid = response.headers.get("x-request-id", "")
            check("R2 失败：未登录 → 401 且带请求标识", response.status_code == 401 and HEX32.match(rid) is not None)
            check("R2 失败：401 访问日志 status=401",
                  any(e.get("request_id") == rid and e.get("status") == 401 for e in access_entries()))

            response = client.get("/api/teacher/classes", headers={"Authorization": f"Bearer {student_token}"})
            rid = response.headers.get("x-request-id", "")
            check("R2 失败：学生调用教师接口 → 403 且带请求标识", response.status_code == 403 and bool(rid))
            check("R2 失败：403 访问日志 status=403 且标识一致",
                  any(e.get("request_id") == rid and e.get("status") == 403 for e in access_entries()))
            check("R2 失败：日志不含令牌、Authorization 与 Cookie",
                  student_token not in log_buffer.getvalue() and "Bearer" not in log_buffer.getvalue()
                  and "Authorization" not in log_buffer.getvalue())

            response = client.get("/api/does-not-exist")
            rid = response.headers.get("x-request-id", "")
            check("R2 失败：不存在的接口 → 404 且带请求标识", response.status_code == 404 and bool(rid))
            check("R2 失败：404 访问日志 status=404",
                  any(e.get("request_id") == rid and e.get("status") == 404 for e in access_entries()))

            response = client.get("/api/__baseline_probe_error")
            rid = response.headers.get("x-request-id", "")
            check("R2 失败：未处理异常 → 500 且带请求标识", response.status_code == 500 and HEX32.match(rid) is not None)
            check("R2 失败：500 响应不含异常原文", "secret-internal-detail" not in response.text)
            check("R2 失败：500 访问日志 status=500",
                  any(e.get("request_id") == rid and e.get("status") == 500 for e in access_entries()))

            client.get("/api/__baseline_probe_log", headers={"X-Request-ID": "lesson07-trace-0002"})
            business = [json.loads(line) for line in log_lines() if '"基线探针日志"' in line]
            check("R2 正常：业务日志为 JSON 并带当前请求标识",
                  len(business) == 1 and business[0]["module"] == "lesson_service"
                  and business[0]["request_id"] == "lesson07-trace-0002" and business[0]["msg"] == "基线探针日志")
            outside = logging.LogRecord("lesson_service", logging.INFO, __file__, 0, "请求之外", None, None)
            check("R2 边界：请求之外的日志 request_id 为 null", json.loads(JsonFormatter().format(outside))["request_id"] is None)
    finally:
        main.httpx.get = original_get
        logging.getLogger().removeHandler(capture)
        engine.dispose()

# ---------- R3 必填配置 ----------
missing = config_probe(None)
check("R3 失败：缺少 JWT_SECRET_KEY → 非零退出并提示键名", missing.returncode != 0 and "JWT_SECRET_KEY" in missing.stderr)
short = config_probe("short-secret-12345")
check("R3 失败：18 个字符 → 非零退出并提示键名", short.returncode != 0 and "JWT_SECRET_KEY" in short.stderr)
check("R3 失败：错误信息不含配置值", "short-secret-12345" not in short.stdout + short.stderr)
edge = config_probe("x" * 31)
check("R3 边界：31 个字符被拒绝", edge.returncode != 0)
check("R3 边界：32 个字符可启动", config_probe("x" * 32).returncode == 0)
check("R3 正常：44 个字符（openssl rand -base64 32）可启动", config_probe("A" * 43 + "=").returncode == 0)
compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
check("R3 正常：Compose 缺 JWT_SECRET_KEY 时拒绝启动", "JWT_SECRET_KEY: ${JWT_SECRET_KEY:?" in compose)

# ---------- R1 部署配置 ----------
nginx = (ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
check("R1 正常：Nginx 把 /health 转发到后端 /api/health",
      re.search(r"location = /health \{\s*proxy_pass http://backend/api/health;", nginx) is not None)
check("R1 正常：Compose 后端探针调用 /api/health 并配置 MCP 探测地址",
      "127.0.0.1:8000/api/health" in compose and "MCP_TOOLS_HEALTH_URL: http://mcp-tools:8090/health" in compose)

# ---------- R4 一键门禁的两个检查脚本 ----------
layering = load("check_layering_under_test", ROOT / "scripts" / "check_layering.py")
with tempfile.TemporaryDirectory(prefix="layering-test-") as tmp:
    fake_root = Path(tmp)
    shutil.copytree(BACKEND, fake_root / "backend", ignore=shutil.ignore_patterns(".venv", "uploads", "__pycache__", "*.db"))
    layering.ROOT, layering.BACKEND = fake_root, fake_root / "backend"
    check("R4 正常：当前代码分层检查通过", layering.main() == 0)
    service = fake_root / "backend" / "citation_service.py"
    service.write_text(service.read_text(encoding="utf-8") + "\nfrom routers import quiz\n", encoding="utf-8")
    check("R4 失败：业务层 import 路由被拦下", layering.main() == 1)
    service.write_text(service.read_text(encoding="utf-8").replace("\nfrom routers import quiz\n", ""), encoding="utf-8")
    (fake_root / "backend" / "foo_service2.py").write_text("import config\n", encoding="utf-8")
    check("R4 失败：未登记层级的新模块被拦下", layering.main() == 1)

scanner = load("secret_scan_under_test", ROOT / "scripts" / "secret_scan.py")
with tempfile.TemporaryDirectory(prefix="secret-scan-test-") as tmp:
    repo = Path(tmp)
    fake_secret = "unit-test-secret-value-0123456789"
    git = lambda *args: subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    git("init", "-q")
    git("config", "user.email", "check@example.invalid")
    git("config", "user.name", "check")
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / ".env").write_text(f"JWT_SECRET_KEY={fake_secret}\n", encoding="utf-8")
    (repo / "README.md").write_text("clean\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "init")
    scanner.ROOT = repo
    check("R4 正常：干净仓库扫描通过", scanner.main() == 0)
    (repo / "notes.md").write_text(f"token {fake_secret}\n", encoding="utf-8")
    git("add", "notes.md")
    git("commit", "-q", "-m", "leak")
    out = io.StringIO()
    stdout, sys.stdout = sys.stdout, out
    try:
        leaked = scanner.main()
    finally:
        sys.stdout = stdout
    check("R4 失败：密钥进入提交被拦下", leaked == 1)
    check("R4 失败：扫描输出键名与文件名，不输出值",
          "JWT_SECRET_KEY" in out.getvalue() and "notes.md" in out.getvalue() and fake_secret not in out.getvalue())

# ---------- R5 工程规范常驻且可被读取 ----------
STANDARDS = ["01-产品设计规范.md", "02-后端开发规范.md", "03-安全开发规范.md", "04-测试规范.md",
             "05-部署运维规范.md", "06-AI应用规范.md", "07-数据规范.md", "08-评审与完成定义规范.md"]


def standards_problems(base: Path) -> list[str]:
    problems = []
    for name in STANDARDS:
        path = base / "docs" / "standards" / name
        if not path.exists():
            problems.append(f"缺少规范 {name}")
        elif "## 违反时" not in path.read_text(encoding="utf-8"):
            problems.append(f"{name} 缺少“违反时”一节")
    agents = (base / "AGENTS.md").read_text(encoding="utf-8")
    for heading in ("安全三条硬约束", "完成定义与门禁", "改代码前先读对应规范", "## 技能"):
        if heading not in agents:
            problems.append(f"AGENTS.md 缺少「{heading}」")
    for ref in sorted(set(re.findall(r"`(docs/standards/[^`]+\.md)`", agents))):
        if not (base / ref).exists():
            problems.append(f"AGENTS.md 引用的 {ref} 不存在")
    if not (base / "CLAUDE.md").read_text(encoding="utf-8").startswith("@AGENTS.md"):
        problems.append("CLAUDE.md 未引入 @AGENTS.md")
    trae = base / ".trae" / "rules" / "project_rules.md"
    if not trae.exists() or "AGENTS.md" not in trae.read_text(encoding="utf-8"):
        problems.append(".trae/rules/project_rules.md 未指向 AGENTS.md")
    skill_table = agents.split("## 技能", 1)[-1].split("\n## ", 1)[0]
    for skill in re.findall(r"^\| `([a-z0-9-]+)` \|", skill_table, flags=re.M):
        path = base / ".claude" / "skills" / skill / "SKILL.md"
        if not path.exists():
            problems.append(f"技能 {skill} 缺少 SKILL.md")
            continue
        head = path.read_text(encoding="utf-8").split("---")
        meta = head[1] if len(head) > 2 else ""
        name = re.search(r"^name:\s*(\S+)\s*$", meta, flags=re.M)
        desc = re.search(r"^description:\s*\S", meta, flags=re.M)
        if not name or name.group(1) != skill or not desc:
            problems.append(f"技能 {skill} 的 front matter 不合法")
    return problems


problems = standards_problems(ROOT)
for problem in problems:
    print("    · " + problem)
check("R5 正常：八份规范、AGENTS.md 索引、CLAUDE.md 引入、Trae 规则与七个技能齐全", problems == [])
with tempfile.TemporaryDirectory(prefix="standards-test-") as tmp:
    copy = Path(tmp)
    for item in ("AGENTS.md", "CLAUDE.md"):
        shutil.copy2(ROOT / item, copy / item)
    for item in ("docs/standards", ".trae/rules", ".claude/skills"):
        shutil.copytree(ROOT / item, copy / item)
    (copy / "docs" / "standards" / "07-数据规范.md").unlink()
    check("R5 失败：索引指向的规范被删除 → 指出缺失路径",
          any("07-数据规范.md" in p for p in standards_problems(copy)))
    shutil.copy2(ROOT / "docs" / "standards" / "07-数据规范.md", copy / "docs" / "standards" / "07-数据规范.md")
    skill = copy / ".claude" / "skills" / "release" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("name: release", "name: publish", 1), encoding="utf-8")
    check("R5 失败：技能名与目录不一致 → 指出该技能",
          standards_problems(copy) == ["技能 release 的 front matter 不合法"])

passed = sum(1 for _, ok in checks if ok)
print(f"\n结果：{passed}/{len(checks)} 通过")
sys.exit(0 if passed == len(checks) else 1)
