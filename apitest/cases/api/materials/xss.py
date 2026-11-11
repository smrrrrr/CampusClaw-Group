# -*- coding: utf-8 -*-
"""XSS 反例：讲义描述提交 <script> 标签，列表接口响应应已转义，无脚本执行。

三段式：
- 前置条件：教师已登录，任教 101 班
- 操作：上传一份材料，description 含 <script>alert(1)</script>
- 可观测结果：GET /api/materials 返回的 description 字段为转义后的文本（&lt;script&gt;），源码中无原始 <script>
"""

import io

XSS_PAYLOAD = "<script>alert(1)</script>"
XSS_PAYLOAD_IMG = "<img src=x onerror=alert(1)>"


def test_material_description_xss_escaped(api, teacher_headers, db_conn):
    """上传含 XSS payload 的描述，列表响应应转义。"""
    # 上传材料（小文本文件）
    file_content = b"xss test material content"
    files = {"file": ("xss-test.txt", io.BytesIO(file_content), "text/plain")}
    data = {
        "class_id": "101",
        "description": XSS_PAYLOAD,
        "tags": "",
    }
    r = api.post("/api/teacher/upload-material", files=files, data=data, headers=teacher_headers)
    assert r.status_code == 200, f"上传失败: {r.status_code} {r.text[:200]}"
    material_id = r.json()["id"]

    try:
        # 获取材料列表，检查描述是否转义
        resp = api.get("/api/materials", headers=teacher_headers)
        assert resp.status_code == 200
        body = resp.text
        # 响应正文不应包含原始 <script> 标签
        assert "<script>" not in body, "XSS payload 未被转义，响应中存在原始 <script>"
        # 应包含转义后的形式
        assert "&lt;script&gt;" in body or "&#x3C;script" in body, "XSS payload 应被 HTML 转义"

        # 再测 img onerror 变体
        files2 = {"file": ("xss-test2.txt", io.BytesIO(file_content), "text/plain")}
        data2 = {"class_id": "101", "description": XSS_PAYLOAD_IMG, "tags": ""}
        r2 = api.post("/api/teacher/upload-material", files=files2, data=data2, headers=teacher_headers)
        assert r2.status_code == 200
        material_id2 = r2.json()["id"]

        resp2 = api.get("/api/materials", headers=teacher_headers)
        # html.escape 转义 < > & " ，不删除属性名；<img 应变为 &lt;img，浏览器不解析为标签
        assert "&lt;img" in resp2.text or "&#x3C;img" in resp2.text, "img 标签应被 HTML 转义"

        # 清理
        db_conn.execute("delete from materials where id in (?, ?)", (material_id, material_id2))
        db_conn.commit()
    except Exception:
        # 确保清理
        db_conn.execute("delete from materials where description like '%<script>%' or description like '%onerror%'")
        db_conn.commit()
        raise
