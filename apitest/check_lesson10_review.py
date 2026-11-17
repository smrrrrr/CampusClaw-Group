"""第10课弱候选逐条复核中补齐的接口/源码断言（离线、临时库、空 Key）。

覆盖此前只有 bigram 弱候选、没有明确断言的场景：
登录失败同文案、JWT 声明、刷新过期、封闭注册、CSV 手机号与缺列、
开发种子保留已改密码、教师不能代学生提问、匿名 401 审计、AI 次数独立与历史、
未刷新旧权限、多班接口、原稿指纹状态、Material 仅元数据、前端 accept、
Markdown 列表加粗解析、学生端班级来源与未分班空状态。
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


def seed(database: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database}"
    env["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, str(ROOT / "backend/dev_seed.py")],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def run(folder: Path):
    os.environ["JWT_SECRET_KEY"] = "check-only-jwt-secret-not-for-real-use-000000"
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["MCP_TOOLS_HEALTH_URL"] = ""
    os.environ["ENABLE_DOCS"] = "false"
    os.environ["DATABASE_URL"] = f"sqlite:///{folder / 'review.db'}"
    os.environ["UPLOAD_DIR"] = str(folder / "uploads")
    sys.path.insert(0, str(ROOT / "backend"))

    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from sqlalchemy import LargeBinary

    import routers.quiz as quiz_router
    from deps import CurrentUser
    from routers import skills as skills_router
    from routers.skills import SkillRequest
    import security
    from database import Base, SessionLocal, engine
    from main import app
    from material_service import parse_material_text, write_physical_file
    from models import AssistantSkill, AuditLog, Class, Material, Role, User
    from security import REFRESH_COOKIE_NAME, decode_token, hash_password
    from services import get_ai_daily_count

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="高二（1）班"), Class(id=102, name="高二（2）班"),
                    Class(id=103, name="高二（3）班")])
        db.flush()
        rows = [
            (1, "T1", Role.teacher, "数学教师", None, "math", [101, 102, 103], 101),
            (2, "T2", Role.teacher, "英语教师", None, "english", [101], None),
            (3, "T3", Role.teacher, "任课教师", None, "math", [101], None),
            (4, "S1", Role.student, "合成学生甲", 101, None, None, None),
            (5, "S2", Role.student, "合成学生乙", 102, None, None, None),
            (6, "S3", Role.student, "合成学生丙", 101, None, None, None),
            (7, "NOCLASS", Role.student, "未分班学生", None, None, None, None),
        ]
        for uid, ident, role, name, cid, subject, tc, homeroom in rows:
            db.add(User(id=uid, identifier=ident, role=role, name=name, class_id=cid,
                        subject=subject,
                        teaching_classes=json.dumps(tc) if tc else None,
                        homeroom_class_id=homeroom,
                        password_hash=hash_password("Test@2026"), must_change_password=False))
        db.commit()

    def login(who: str) -> str:
        response = client.post("/api/auth/login", json={"identifier": who, "password": "Test@2026"})
        assert response.status_code == 200, (who, response.status_code, response.text)
        return response.json()["access_token"]

    def headers(who: str) -> dict:
        return {"Authorization": "Bearer " + tokens[who]}

    def upload(who: str, class_id: int):
        return client.post("/api/teacher/upload-material", headers=headers(who),
                           data={"class_id": str(class_id), "description": "复核", "tags": "数学"},
                           files={"file": ("review.md", "# 合成资料\n\n内容".encode(), "text/markdown")})

    with TestClient(app) as client:
        tokens = {who: login(who) for who in ("T1", "T2", "T3", "S1", "S2", "S3")}

        # ---- 登录失败同文案 / JWT 声明 -------------------------------------
        wrong = client.post("/api/auth/login", json={"identifier": "T1", "password": "wrong-password"})
        missing = client.post("/api/auth/login", json={"identifier": "NO-SUCH-USER", "password": "wrong-password"})
        check("密码错误与账号不存在返回同一提示",
              wrong.status_code == missing.status_code == 401
              and wrong.json()["detail"] == missing.json()["detail"] == "账号或密码错误")

        payload = decode_token(tokens["T1"])
        check("JWT Payload 包含必要字段：教师令牌含七个声明",
              {"user_id", "role", "class_id", "must_change_password", "subject",
               "teaching_classes", "homeroom_class_id"} <= set(payload)
              and payload["role"] == "teacher" and payload["subject"] == "math"
              and payload["teaching_classes"] == [101, 102, 103]
              and payload["homeroom_class_id"] == 101
              and payload["must_change_password"] is False)
        student_payload = decode_token(tokens["S1"])
        check("JWT Payload 包含必要字段：学生令牌不带教师身份",
              student_payload["role"] == "student" and student_payload["class_id"] == 101
              and "teaching_classes" not in student_payload and "homeroom_class_id" not in student_payload)

        # ---- Refresh 过期 --------------------------------------------------
        expired = security._create_token(
            {"user_id": 1, "role": "teacher", "class_id": None, "must_change_password": False},
            timedelta(seconds=-1), "refresh")
        client.cookies.set(REFRESH_COOKIE_NAME, expired)
        expired_response = client.post("/api/auth/refresh")
        client.cookies.delete(REFRESH_COOKIE_NAME)
        check("Refresh Token 过期需重新登录：过期刷新令牌返回 401",
              expired_response.status_code == 401 and "重新登录" in expired_response.json()["detail"])

        api_source = (ROOT / "frontend/lib/api.ts").read_text(encoding="utf-8")
        check("Access Token 过期自动刷新：前端 401 后调用 refresh 并重试原请求",
              "if (res.status === 401 && !options.skipAuthRefresh)" in api_source
              and "const ok = await refreshAccessToken();" in api_source
              and "res = await doFetch();" in api_source)

        # ---- 封闭注册 ------------------------------------------------------
        register = client.post("/api/auth/register", json={"identifier": "x", "password": "Test@2026"})
        login_page = (ROOT / "frontend/app/login/page.tsx").read_text(encoding="utf-8")
        check("未登录用户无法注册：注册接口不存在且登录页无注册入口",
              register.status_code == 404 and "注册" not in login_page)

        # ---- CSV：缺学号列 / 手机号 ---------------------------------------
        before_users = 0
        with SessionLocal() as db:
            before_users = db.query(User).count()
        missing_column = client.post(
            "/api/teacher/import-students", headers=headers("T1"),
            files={"file": ("students.csv", "姓名,班级\n张三,高二（1）班\n".encode("utf-8"), "text/csv")})
        with SessionLocal() as db:
            after_missing = db.query(User).count()
        check("CSV 缺少学号列被拒绝：400 且不创建账号",
              missing_column.status_code == 400 and "学号" in missing_column.json()["detail"]
              and after_missing == before_users)

        with_phone = client.post(
            "/api/teacher/import-students", headers=headers("T1"),
            files={"file": ("students.csv",
                            "学号,学生姓名,班级,手机号\n20269991,李明,高二（1）班,13800001111\n".encode("utf-8"),
                            "text/csv")})
        with SessionLocal() as db:
            imported = db.query(User).filter_by(identifier="20269991").one_or_none()
        check("CSV 导入手机号：phone 字段落库",
              with_phone.status_code == 200 and with_phone.json()["created"] == 1
              and imported is not None and imported.phone == "13800001111"
              and imported.class_id == 101)

        # ---- 开发种子：预置身份 / 重跑保留已改密码 -------------------------
        seed_db = folder / "seed.db"
        first = seed(seed_db)
        connection = sqlite3.connect(seed_db)
        row = connection.execute(
            "SELECT password_hash, name, subject, homeroom_class_id, must_change_password "
            "FROM users WHERE identifier='TEA001'").fetchone()
        check("开发种子：教师学科与班主任身份写入",
              first.returncode == 0 and row is not None
              and row[1] == "张老师" and row[2] == "math" and row[3] == 101 and row[4] == 0)
        connection.execute("UPDATE users SET password_hash='CUSTOM-HASH', name='旧名', "
                           "subject='english', homeroom_class_id=NULL WHERE identifier='TEA001'")
        connection.commit()
        second = seed(seed_db)
        row2 = connection.execute(
            "SELECT password_hash, name, subject, homeroom_class_id, must_change_password "
            "FROM users WHERE identifier='TEA001'").fetchone()
        connection.close()
        check("教师种子维护身份而不覆盖已改密码：重跑保留自定义口令并更新学科",
              second.returncode == 0 and row2 == ("CUSTOM-HASH", "张老师", "math", 101, 0))

        # ---- 教师不能代替学生提问 ----------------------------------------
        teacher_ask = client.post("/api/student/ai-question", headers=headers("T1"),
                                  json={"question": "两向量夹角", "subject": "math"})
        check("教师不能代替学生发起 AI 提问：教师调用学生提问接口 403",
              teacher_ask.status_code == 403
              and "仅学生" in teacher_ask.json()["detail"])

        # ---- 匿名审计 ------------------------------------------------------
        anonymous = client.get("/api/materials")
        with SessionLocal() as db:
            audit = (db.query(AuditLog).filter_by(status_code=401)
                     .order_by(AuditLog.id.desc()).first())
        check("未登录请求留匿名审计：401 落库 user_id 为空且 action 可识别",
              anonymous.status_code == 401 and audit is not None
              and audit.user_id is None and audit.role is None
              and audit.action == "GET /api/materials" and audit.request_path == "/api/materials")

        # ---- 学生提问历史与按学生独立计数 ---------------------------------
        first_ask = client.post("/api/student/ai-question", headers=headers("S1"),
                                json={"question": "合成提问-甲", "subject": "math"})
        client.post("/api/student/ai-question", headers=headers("S3"),
                    json={"question": "合成提问-丙", "subject": "math"})
        with SessionLocal() as db:
            count_s1, count_s3, count_s2 = (get_ai_daily_count(db, 4),
                                            get_ai_daily_count(db, 6), get_ai_daily_count(db, 5))
        check("不同学生账号次数独立计算：两名学生各自计数互不影响",
              first_ask.status_code == 200 and (count_s1, count_s3, count_s2) == (1, 1, 0))
        history_s1 = client.get("/api/student/ai-history", headers=headers("S1")).json()
        history_s2 = client.get("/api/student/ai-history", headers=headers("S2")).json()
        check("学生发起 AI 提问并查看历史：提问落库且历史仅本人可见",
              first_ask.status_code == 200
              and any(item["question"] == "合成提问-甲" for item in history_s1)
              and all(item["question"] != "合成提问-甲" for item in history_s2))

        # ---- 多班级选择器接口 ---------------------------------------------
        classes = client.get("/api/teacher/classes", headers=headers("T1"))
        check("多班级选择器展示所有任教班级：接口返回全部任教班级",
              classes.status_code == 200
              and {item["id"] for item in classes.json()} == {101, 102, 103})

        # ---- 未刷新前旧权限仍有效 -----------------------------------------
        denied_before = upload("T3", 102)
        with SessionLocal() as db:
            teacher = db.get(User, 3)
            teacher.teaching_classes = json.dumps([101, 102])
            db.commit()
        denied_after_db_change = upload("T3", 102)
        tokens["T3"] = login("T3")
        allowed_after_relogin = upload("T3", 102)
        check("未刷新前旧权限仍有效：旧令牌按旧任教班级校验，重新登录后生效",
              denied_before.status_code == 403 and denied_after_db_change.status_code == 403
              and allowed_after_relogin.status_code == 200)

        material_id = allowed_after_relogin.json()["id"]
        student_delete = client.delete(f"/api/teacher/materials/{material_id}", headers=headers("S1"))
        check("学生尝试删除资料被拒：学生调用删除接口 403 且资料保留",
              student_delete.status_code == 403
              and client.get(f"/api/materials/{material_id}/preview", headers=headers("S2")).status_code == 200)

        # ---- 原稿在入库后被替换 -------------------------------------------
        relative = "research/math/review/source.md"
        original = b"# original source\n"
        write_physical_file(original, relative)
        import hashlib
        snapshot = types.SimpleNamespace(sources_json=json.dumps([{
            "research_material_id": 1,
            "file_sha256": hashlib.sha256(original).hexdigest(),
            "file_path": relative,
        }]))
        consistent = quiz_router.source_status(snapshot)
        write_physical_file(b"# replaced source\n", relative)
        changed = quiz_router.source_status(snapshot)
        (folder / "uploads" / relative).unlink()
        deleted = quiz_router.source_status(snapshot)
        check("原稿在入库后被替换：指纹变化标记 changed、缺失标记 deleted",
              (consistent, changed, deleted) == ("consistent", "changed", "deleted"))

        # ---- Material 仅元数据 / 前端 accept ------------------------------
        columns = {column.name: column.type for column in Material.__table__.columns}
        check("SQLite 仅存储元数据：Material 表无二进制列",
              not any(isinstance(column_type, LargeBinary) for column_type in columns.values())
              and {"file_path", "file_size", "filename"} <= set(columns))
        upload_page = (ROOT / "frontend/app/teacher/upload/page.tsx").read_text(encoding="utf-8")
        check("前端 accept 属性初步限制：ACCEPT 仅含允许格式且绑定文件输入",
              'const ACCEPT = ".pdf,.pptx,.docx,.jpg,.png,.md,.txt";' in upload_page
              and "accept={ACCEPT}" in upload_page)

        # ---- Markdown 列表与加粗 -----------------------------------------
        markdown = folder / "outline.md"
        markdown.write_text("- 第一项\n- 第二项\n\n**加粗结论**\n", encoding="utf-8")
        content, error = parse_material_text(markdown, "text/markdown")
        check("支持 Markdown 列表与加粗：解析保留列表与加粗原文",
              error is None and content is not None
              and "- 第一项" in content and "- 第二项" in content and "**加粗结论**" in content)

        # ---- 学生首页班级 / 未分班空状态 / 资料班级来源 -------------------
        student_page = (ROOT / "frontend/app/student/page.tsx").read_text(encoding="utf-8")
        check("学生首页展示本人班级：班级名取自本人会话且无班级选择器",
              "const className = currentStudent?.class_id === 101" in student_page
              and "className={className}" in student_page
              and "班级选择器" not in student_page)
        check("未分班学生访问：空状态且不请求班级资料",
              "const hasClass = currentStudent?.class_id != null;" in student_page
              and "if (!hasClass) return;" in student_page
              and "你还未被分配到班级" in student_page)
        materials_page = (ROOT / "frontend/app/materials/page.tsx").read_text(encoding="utf-8")
        check("学生资料请求使用本人班级：学生端固定取本人 class_id，不提供跨班切换",
              "const cid = isTeacher ? classFilter : currentStudent?.class_id ?? null;" in materials_page)

        logout_button = (ROOT / "frontend/components/logout-button.tsx").read_text(encoding="utf-8")
        check("登出清除所有 Token 和状态：前端清本地状态并跳转登录，后端清 Cookie",
              "await api.logout();" in logout_button and "reset();" in logout_button
              and 'router.replace("/login");' in logout_button)

        teacher_page = (ROOT / "frontend/app/teacher/page.tsx").read_text(encoding="utf-8")
        check("同一教师在任课页不展示重置操作：操作列与按钮均受班主任身份控制",
              "{isHomeroom && <th style={{ width: 140 }}>操作</th>}" in teacher_page
              and "{isHomeroom && <td>" in teacher_page
              and "重置密码" in teacher_page)

        # ---- 并发同名技能：唯一约束映射为 400 而非 500 ---------------------
        source = ("名称：并发同名技能\n适用条件：夹角\n工具：knowledge_search\n启用：是\n\n"
                  "只给公式提示，不直接给答案。")
        current = CurrentUser(user_id=1, role="teacher", class_id=None, must_change_password=False,
                              teaching_classes=[101, 102, 103], subject="math")
        with SessionLocal() as db:
            first = skills_router.create_skill(SkillRequest(class_id=101, source=source),
                                               current=current, db=db)
            # 模拟两个请求都已通过前置查重：跳过查重后第二次插入必然撞唯一约束
            with patch.object(skills_router, "_check_name_unique", lambda *a, **k: None):
                try:
                    skills_router.create_skill(SkillRequest(class_id=101, source=source),
                                               current=current, db=db)
                    outcome = (None, None)
                except HTTPException as exc:
                    outcome = (exc.status_code, exc.detail)
            total = db.query(AssistantSkill).count()
        check("技能文件格式错误：并发同名创建仍返回 400 且不新增",
              outcome == (400, "本班本科目下已存在同名技能")
              and total == 1 and first.name == "并发同名技能")

    engine.dispose()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lesson10-review-", ignore_cleanup_errors=True) as folder:
        run(Path(folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
