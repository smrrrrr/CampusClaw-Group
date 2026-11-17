"""第10课：场景映射中可直接断言、且不依赖网络与模型的场景。

对应 reports/scenario-coverage.md 中这些原本「无匹配断言」的条目：
- 学生/教师账号初始密码生成
- 系统不创建独立家长角色
- 短材料生成单个分块 / 解析材料生成多个分块

只调用纯函数，不建库、不启服务、不访问外部模型。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
os.environ.setdefault("DEEPSEEK_API_KEY", "")

import security  # noqa: E402
from chunk_service import chunk_text  # noqa: E402
from config import settings  # noqa: E402
from models import Role  # noqa: E402


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


def main():
    abbr = settings.school_abbr.lower()

    student_pwd = security.generate_initial_password("S2023001")
    check("学生账号初始密码：前缀为学校缩写且结尾为学号末六位",
          student_pwd == f"{abbr}023001" and student_pwd.endswith("023001"))

    teacher_pwd = security.generate_initial_password("T2023456")
    check("教师账号初始密码：前缀为学校缩写且结尾为工号末六位",
          teacher_pwd == f"{abbr}023456" and teacher_pwd.endswith("023456"))

    check("双角色定义：系统不创建独立家长角色",
          {role.value for role in Role} == {"teacher", "student"})

    short_text = "短材料只含一个自然段，没有换行。" * 3
    check("文本分块：短材料生成单个分块", len(chunk_text(short_text)) == 1)

    long_text = "。".join(f"第{i}段讲解内容，包含公式与说明" for i in range(400))
    check("文本分块：长材料生成多个分块", len(chunk_text(long_text)) > 1)

    check("文本分块：空材料不产生分块", chunk_text("") == [] and chunk_text(None) == [])


if __name__ == "__main__":
    main()
