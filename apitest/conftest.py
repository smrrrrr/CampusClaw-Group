"""apitest 共享 fixtures：BASE_URL 客户端、数据库连接、教师/学生登录头、class-102 已索引材料 id。

- 测试学生账号：20230002 / Test@2023（学生，class_id=102，id=3）。
  class-102 已存在已索引材料（materials id=1），检索类用例直接对其命中即可，
  无需额外的种子/复制逻辑。
- 每个用例同时做「HTTP 响应内容」与「SQLite 数据库一致性」两层断言。
"""

import json
import os

import pytest
import requests

BASE_URL = os.environ.get("APITEST_BASE_URL", "http://localhost:8001")

TEACHER = {"identifier": "TEA001", "password": "Teach@2026"}
# 用户指定的学生测试账号：20230002 / Test@2023（class 102，id=3）
STUDENT = {"identifier": "20230002", "password": "Test@2023"}

# 检索用问题：必须与 class-102 材料词元高度重叠，确保命中（chunk_min_keyword_hits=3）
SEED_QUESTION = "如何用空间向量法求二面角的平面角？"
CHAT_QUESTION = "用空间向量法求二面角的平面角"


class API:
    """极简 requests 客户端，URL 先拼 base。"""

    def __init__(self, base: str):
        self.base = base

    def _url(self, path: str):
        return self.base + path

    def get(self, path, **kw):
        return requests.get(self._url(path), timeout=60, **kw)

    def post(self, path, **kw):
        return requests.post(self._url(path), timeout=120, **kw)

    def put(self, path, **kw):
        return requests.put(self._url(path), timeout=60, **kw)

    def delete(self, path, **kw):
        return requests.delete(self._url(path), timeout=60, **kw)


@pytest.fixture(scope="session")
def api() -> API:
    return API(BASE_URL)


DB_PATH = os.environ.get(
    "APITEST_DB_PATH",
    r"c:\Users\17424\Desktop\CampusClaw\data\campusclaw.db",
)


@pytest.fixture(scope="session")
def db_conn():
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    try:
        conn.close()
    except Exception:
        pass


def _login(api: API, identifier: str, password: str):
    r = api.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert r.status_code == 200, f"登录失败 {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("access_token"), "响应缺少 access_token"
    return {"Authorization": f"Bearer {body['access_token']}"}, body


@pytest.fixture(scope="session")
def teacher_headers(api):
    headers, body = _login(api, TEACHER["identifier"], TEACHER["password"])
    assert body.get("role") == "teacher", "教师登录角色不正确"
    assert 101 in (body["user"].get("teaching_classes") or []), "教师应任教 101（供 agent-config 用例）"
    return headers


@pytest.fixture(scope="session")
def student_headers(api):
    headers, body = _login(api, STUDENT["identifier"], STUDENT["password"])
    assert body.get("role") == "student", "学生登录角色不正确"
    assert body["user"]["id"] == 3, "学生账号应映射到 id=3"
    assert body["user"]["class_id"] == 102, "学生账号应属于 class 102"
    return headers


@pytest.fixture(scope="session")
def class102_material_id(db_conn):
    """class-102 已索引材料的 id（检索引用应指向它）。"""
    row = db_conn.execute(
        "select id from materials where class_id=102 and is_indexed=1 order by id limit 1"
    ).fetchone()
    assert row is not None, "class-102 缺少已索引材料"
    return row["id"]


def parse_sse(text: str) -> list[dict]:
    """解析 text/event-stream 响应中的 `data: {...}` 事件。"""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events