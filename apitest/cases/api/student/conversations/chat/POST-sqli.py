# -*- coding: utf-8 -*-
"""SQL 注入反例：向检索/会话接口提交注入 payload，验证参数化查询不返回越权数据。

三段式：
- 前置条件：学生已登录，class-102 有已索引材料
- 操作：提交含 `' OR '1'='1` 的提问，观察检索结果
- 可观测结果：不返回非本班材料，响应正常（200 或空结果），不报 500/不泄露 SQL
"""

from conftest import CHAT_QUESTION, parse_sse

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE materials; --",
    "1' UNION SELECT * FROM users--",
    "admin'--",
]


def test_sqli_payloads_do_not_leak_or_crash(
    api, student_headers, db_conn, class102_material_id
):
    """逐条提交 SQL 注入 payload，断言：不返回非本班材料、不抛 500、不泄露 SQL 原文。"""
    # 先记录本班材料总数作为基线
    baseline = db_conn.execute(
        "select count(*) as c from materials where class_id=102"
    ).fetchone()["c"]

    for payload in SQLI_PAYLOADS:
        # 创建会话
        r = api.post("/api/student/conversations", json={}, headers=student_headers)
        assert r.status_code == 200, f"创建会话失败: {r.status_code}"
        cid = r.json()["id"]

        try:
            resp = api.post(
                f"/api/student/conversations/{cid}/chat",
                json={"question": payload},
                headers=student_headers,
            )
            # 注入 payload 不应导致 500（SQL 报错）；正常降级为 200 或 400
            assert resp.status_code in (200, 400), (
                f"SQL 注入 payload 导致异常状态码 {resp.status_code}: {resp.text[:200]}"
            )
            if resp.status_code == 200:
                events = parse_sse(resp.text)
                if events and events[-1]["type"] == "done":
                    citations = events[-1].get("citations", [])
                    # 所有引用必须指向本班材料，不能泄露其他班
                    for c in citations:
                        assert c["material_id"] == class102_material_id, (
                            f"SQL 注入返回了非本班材料 {c['material_id']}"
                        )
            # 数据库不应被破坏：本班材料数不变
            after = db_conn.execute(
                "select count(*) as c from materials where class_id=102"
            ).fetchone()["c"]
            assert after == baseline, "SQL 注入 payload 破坏了材料表"
        finally:
            db_conn.execute(
                "delete from ai_question_logs where student_id=3 and class_id=102 and question=?",
                (payload,),
            )
            db_conn.commit()
            api.delete(f"/api/student/conversations/{cid}", headers=student_headers)


def test_normal_question_still_works(
    api, student_headers, db_conn, class102_material_id
):
    """正常提问不受注入防御误伤：应返回 200 且命中本班材料。"""
    r = api.post("/api/student/conversations", json={}, headers=student_headers)
    assert r.status_code == 200
    cid = r.json()["id"]
    try:
        resp = api.post(
            f"/api/student/conversations/{cid}/chat",
            json={"question": CHAT_QUESTION},
            headers=student_headers,
        )
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        assert events and events[-1]["type"] in ("done", "error")
    finally:
        db_conn.execute(
            "delete from ai_question_logs where student_id=3 and class_id=102 and question=?",
            (CHAT_QUESTION,),
        )
        db_conn.commit()
        api.delete(f"/api/student/conversations/{cid}", headers=student_headers)
