# -*- coding: utf-8 -*-
"""注入三件套反例回归（SQL 注入 / XSS / CSRF）。

对应老师任务清单第三节：三条反例随 make check 常驻回归。
临时数据库 + 虚构模型，不连外网、不触碰演示数据。

用法（项目根）：make check，或
  JWT_SECRET_KEY=<至少 32 字符> PYTHONPATH=backend backend/.venv/Scripts/python.exe apitest/check_injection.py
"""

import asyncio
import io
import os
import tempfile

import httpx


async def main():
    with tempfile.TemporaryDirectory(prefix="injection-test-", ignore_cleanup_errors=True) as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/inj.db"
        os.environ["UPLOAD_DIR"] = os.path.join(tmp, "uploads")
        os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
        os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)

        from database import Base, SessionLocal, engine
        from main import app
        from models import Class, Material, Role, User
        from security import hash_password

        Base.metadata.create_all(engine)

        with SessionLocal() as db:
            db.add_all([Class(id=101, name="一班"), Class(id=102, name="二班")])
            db.add(User(identifier="T1", role=Role.teacher, subject="math",
                        teaching_classes="[101,102]", name="T1",
                        password_hash=hash_password("Test@2026"), must_change_password=False))
            db.add(User(identifier="S1", role=Role.student, class_id=102, name="S1",
                        password_hash=hash_password("Test@2026"), must_change_password=False))
            db.add(Material(class_id=102, uploader_id=1, filename="base.txt",
                            file_path="102/base.txt", file_type="text/plain",
                            file_size=10, description="基础材料", is_indexed=False))
            db.commit()

        checks = []

        def check(name, passed):
            checks.append((name, bool(passed)))
            print(("  ✓ " if passed else "  ✗ ") + name)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 登录
            tr = await client.post("/api/auth/login", json={"identifier": "T1", "password": "Test@2026"})
            teacher_token = tr.json()["access_token"]
            teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

            sr = await client.post("/api/auth/login", json={"identifier": "S1", "password": "Test@2026"})
            student_token = sr.json()["access_token"]
            student_headers = {"Authorization": f"Bearer {student_token}"}

            # ============ SQL 注入 ============
            print("\n[SQL 注入]")
            sqli_payloads = [
                "' OR '1'='1",
                "'; DROP TABLE materials; --",
                "1' UNION SELECT * FROM users--",
                "admin'--",
            ]
            # 基线：材料数
            with SessionLocal() as db:
                baseline = db.query(Material).count()

            all_sqli_ok = True
            for payload in sqli_payloads:
                # 创建会话
                c = await client.post("/api/student/conversations", json={}, headers=student_headers)
                cid = c.json()["id"]
                r = await client.post(f"/api/student/conversations/{cid}/chat",
                                      json={"question": payload}, headers=student_headers)
                # 不应返回 500（SQL 报错）
                ok = r.status_code in (200, 400)
                if not ok:
                    all_sqli_ok = False
                # 材料表不应被破坏
                with SessionLocal() as db:
                    after = db.query(Material).count()
                if after != baseline:
                    all_sqli_ok = False
                await client.delete(f"/api/student/conversations/{cid}", headers=student_headers)

            check("SQL 注入 payload 不导致 500 或破坏数据", all_sqli_ok)

            # ============ XSS ============
            print("\n[XSS]")
            xss_payload = "<script>alert(1)</script>"
            files = {"file": ("xss-test.txt", io.BytesIO(b"xss test"), "text/plain")}
            data = {"class_id": "101", "description": xss_payload, "tags": ""}
            r = await client.post("/api/teacher/upload-material", files=files, data=data, headers=teacher_headers)
            check("上传含 <script> 描述的材料成功", r.status_code == 200)

            r = await client.get("/api/materials", headers=teacher_headers)
            body = r.text
            check("列表响应不含原始 <script> 标签", "<script>" not in body)
            check("列表响应含转义后的 script 标记", "&lt;script&gt;" in body or "&#x3C;script" in body)

            # img onerror 变体
            files2 = {"file": ("xss-test2.txt", io.BytesIO(b"xss test2"), "text/plain")}
            data2 = {"class_id": "101", "description": "<img src=x onerror=alert(1)>", "tags": ""}
            await client.post("/api/teacher/upload-material", files=files2, data=data2, headers=teacher_headers)
            r = await client.get("/api/materials", headers=teacher_headers)
            # html.escape 转义 < > & " ，不删除属性名；<img 应变为 &lt;img，浏览器不解析为标签
            check("img 标签被转义（&lt;img）", "&lt;img" in r.text or "&#x3C;img" in r.text)

            # ============ CSRF ============
            print("\n[CSRF]")
            # 用独立 client 拿 Cookie（Bearer 头请求豁免 CSRF，所以用 Cookie 会话测）
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as csrf_client:
                lr = await csrf_client.post("/api/auth/login", json={"identifier": "T1", "password": "Test@2026"})
                csrf_cookie = lr.cookies.get("csrf_token")
                check("登录响应下发 csrf_token Cookie", csrf_cookie is not None and csrf_cookie != "")

                # 有 Cookie 无 X-CSRF-Token 头 → 403
                r = await csrf_client.post("/api/teacher/skills",
                                           json={"name": "csrf-test", "description": "t", "enabled": True})
                check("Cookie 会话无 X-CSRF-Token 头写请求被拒 (403)", r.status_code == 403)

                # 有 Cookie + 正确 X-CSRF-Token 头 → 通过 CSRF（业务鉴权另说，但不是 CSRF 403）
                r = await csrf_client.post("/api/teacher/skills",
                                           json={"name": "csrf-test2", "description": "t", "enabled": True},
                                           headers={"X-CSRF-Token": csrf_cookie})
                check("Cookie 会话带正确 X-CSRF-Token 头不被 CSRF 拒绝", r.status_code != 403)

            # Bearer 头豁免 CSRF
            r = await client.post("/api/teacher/skills",
                                  json={"name": "bearer-test", "description": "t", "enabled": True},
                                  headers=teacher_headers)
            check("Bearer 令牌请求豁免 CSRF 校验", r.status_code != 403 or "CSRF" not in r.text)

        # 汇总
        print("\n" + "=" * 50)
        passed = sum(1 for _, p in checks if p)
        total = len(checks)
        print(f"注入三件套回归：{passed}/{total} 通过")
        if passed != total:
            print("存在失败项，请检查上方 ✗ 标记")
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
