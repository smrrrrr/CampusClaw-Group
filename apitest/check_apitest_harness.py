"""apitest 夹具自检：默认账号与开发种子一致，链路用例在模型未调用工具时跳过而非误报。

不连服务、不读演示库。需要 pytest 与 requests（与 run_all.py 相同的依赖）。

用法（项目根）：
    python apitest/check_apitest_harness.py
"""

import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- 默认账号：与 login-and-account-system 规约的种子表一致 ----
for key in ["APITEST_TEACHER_ID", "APITEST_TEACHER_PASSWORD", "APITEST_STUDENT_ID", "APITEST_STUDENT_PASSWORD"]:
    os.environ.pop(key, None)
sys.path.insert(0, str(ROOT / "apitest"))
conftest = load("conftest", ROOT / "apitest" / "conftest.py")
spec_md = (ROOT / "openspec/specs/login-and-account-system/spec.md").read_text(encoding="utf-8")
seed = {}  # 账号 → (种子初始密码, 任教或所属班级)
for row in re.finditer(r"^\| (?:教师|学生) \| [^|]+ \| (\S+) \| (\S+) \| ([^|]+) \|", spec_md, re.M):
    seed[row[1]] = (row[2], row[3].strip())
teacher, student = conftest.TEACHER, conftest.STUDENT
check("默认教师账号在种子表中且密码一致",
      teacher["identifier"] in seed and seed[teacher["identifier"]][0] == teacher["password"])
check("默认学生账号在种子表中且密码一致",
      student["identifier"] in seed and seed[student["identifier"]][0] == student["password"])
check("默认学生属于 102 班（链路与检索用例所在班）",
      student["identifier"] in seed and seed[student["identifier"]][1].startswith("102"))
os.environ["APITEST_STUDENT_ID"] = "override-id"
check("环境变量仍可覆盖默认学生账号", load("conftest_env", ROOT / "apitest" / "conftest.py").STUDENT["identifier"] == "override-id")
os.environ.pop("APITEST_STUDENT_ID")

# ---- 链路用例：模型未调用工具时跳过，已调用但未成功时失败 ----
chain_mod = load("chain_case", ROOT / "apitest/cases/api/mcp/CHAIN.py")
REF = "formula_hint@apitest-chain-x"


class FakeResp:
    status_code = 200
    text = ""

    def __init__(self, items):
        self._items = items

    def json(self):
        return {"items": self._items}


class FakeApi:
    def __init__(self, items):
        self.items = items

    def get(self, *a, **k):
        return FakeResp(self.items)


def outcome(events, audit=()):
    chain = {"skill_name": "s", "ref": REF, "cid": 7, "events": events}
    try:
        chain_mod.test_chain_tool_ok_audit(FakeApi(list(audit)), {}, chain)
        return "passed"
    except pytest.skip.Exception as exc:
        return "skipped:" + str(exc)
    except AssertionError:
        return "failed"


meta = lambda calls: {"type": "meta", "skill": {"name": "s"}, "tool_calls": calls}  # noqa: E731
r = outcome([meta([]), {"type": "delta", "content": "直接作答"}])
check("模型未提议调用工具：跳过并写明原因", r.startswith("skipped:") and "未提议调用" in r)
check("AI 不可用（error 帧）：跳过", outcome([meta([]), {"type": "error", "message": "x"}]).startswith("skipped:"))
check("已提议调用但状态为 error：失败", outcome([meta([{"ref": REF, "status": "error"}])]) == "failed")
check("调用 ok 但调用记录查不到：失败", outcome([meta([{"ref": REF, "status": "ok"}])], audit=[]) == "failed")
check("调用 ok 且调用记录可查：通过",
      outcome([meta([{"ref": REF, "status": "ok"}])],
              audit=[{"tool_ref": REF, "status": "ok", "conversation_id": 7}]) == "passed")

print(f"\n结果：{sum(1 for _, ok in checks if ok)}/{len(checks)} 通过")
failed = [n for n, ok in checks if not ok]
if failed:
    print("失败项：", failed)
    raise SystemExit(1)
