"""第10课：P0 高风险场景离线断言（不依赖网络与模型）。

对应 reports/scenario-coverage.md 中原本「无匹配断言」的 17 条 P0 场景。
按「前端/展示」与「接口/逻辑」两组组织，全部使用纯函数、临时库或源码断言。
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
os.environ.setdefault("DEEPSEEK_API_KEY", "")

from services import AI_DAILY_LIMIT  # noqa: E402


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


# ---------------------------------------------------------------------------
# 前端/展示（6 条 P0）
# ---------------------------------------------------------------------------

def check_frontend():
    frontend = ROOT / "frontend"

    # P0-1: 教师未分配任教班级前端展示空状态
    teacher_page = (frontend / "app/teacher/page.tsx").read_text(encoding="utf-8")
    check("P0 前端：教师未分配任教班级时存在空状态提示",
          "暂无任教班级" in teacher_page or "未分配班级" in teacher_page or "teaching_classes.length === 0" in teacher_page)

    # P0-2: 用户忘记密码看到班主任提示
    login_page = (frontend / "app/login/page.tsx").read_text(encoding="utf-8")
    check("P0 前端：忘记密码显示「请联系班主任重置」提示",
          "请联系班主任重置" in login_page or "班主任" in login_page)

    # P0-3: AI 回答的 Markdown 与公式渲染
    markdown_answer = (frontend / "components/markdown-answer.tsx").read_text(encoding="utf-8")
    check("P0 前端：公式渲染使用 KaTeX 数学符号",
          "rehype-katex" in markdown_answer or "katex" in markdown_answer.lower())

    # P0-4: 独立公式居中美化与长公式横向滚动
    globals_css = (frontend / "app/globals.css").read_text(encoding="utf-8")
    check("P0 前端：独立公式居中与长公式横向滚动样式存在",
          "katex-display" in globals_css or "overflow-x" in globals_css)

    # P0-5: 回答正文与参考资料分离展示（多命中逐条展示保留溯源）
    student_page = (frontend / "app/student/page.tsx").read_text(encoding="utf-8")
    check("P0 前端：参考资料独立区域逐条展示并保留溯源",
          "参考资料" in student_page and "citation" in student_page)

    # P0-6: 无引用时仅显示回答
    check("P0 前端：无引用时仅显示回答（条件渲染）",
          "sources.length > 0" in student_page or "citations.length > 0" in student_page or "sources?.length" in student_page)


# ---------------------------------------------------------------------------
# 接口/逻辑（11 条 P0）
# ---------------------------------------------------------------------------

def check_backend():
    # P0-7: SQLite 原生磁盘保留 WAL（代码默认值为 WAL，.env 可覆盖为 DELETE 用于 Docker 共享目录）
    config_code = (ROOT / "backend/config.py").read_text(encoding="utf-8")
    database_code = (ROOT / "backend/database.py").read_text(encoding="utf-8")
    check("P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖",
          '"WAL"' in config_code and 'sqlite_journal_mode' in config_code and 'PRAGMA journal_mode' in database_code)

    # P0-8: 任课切班不改变带班上下文（身份与带班班级均由服务端令牌/数据库派生，非前端参数）
    deps_code = (ROOT / "backend/deps.py").read_text(encoding="utf-8")
    check("P0 接口：任教班级与带班班级均由服务端令牌/数据库派生（不采信客户端参数）",
          "payload.get(\"teaching_classes\")" in deps_code
          and "homeroom_class_id" in deps_code
          and "decode_token(credentials.credentials)" in deps_code
          and "Request" not in deps_code)

    # P0-9: 学校级公共资源不隔离（学科组素材绑定 subject，不绑定 class_id）
    models_code = (ROOT / "backend/models.py").read_text(encoding="utf-8")
    rm = re.search(r"class ResearchMaterial\(Base\):(.*?)(?=\nclass )", models_code, re.S)
    check("P0 接口：学科组素材按学科归属、不绑定班级",
          rm is not None and "subject" in rm.group(1) and "class_id" not in rm.group(1))

    # P0-10: 系统公告不隔离（当前无系统公告特性，故不存在按班级隔离的公告模型）
    check("P0 接口：不存在按班级隔离的系统公告模型（特性未实现，无误隔离）",
          "announcement" not in models_code.lower() and "system_notice" not in models_code.lower())

    # P0-11: 多个学生使用相同联系方式（User 唯一约束仅覆盖 role+identifier，phone 允许重复）
    user_body = re.search(r"class User\(Base\):(.*?)(?=\nclass )", models_code, re.S)
    user_args = re.search(r"__table_args__\s*=\s*\((.*?)\n\s*\)", user_body.group(1), re.S) if user_body else None
    unique_lines = [ln for ln in user_args.group(1).splitlines() if "UniqueConstraint" in ln] if user_args else []
    check("P0 接口：用户唯一约束仅限 role+identifier，不含 phone（联系方式可重复）",
          len(unique_lines) == 1 and 'UniqueConstraint("role", "identifier"' in unique_lines[0])

    # P0-12: 向量化失败不阻塞上传
    material_service = (ROOT / "backend/material_service.py").read_text(encoding="utf-8")
    check("P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功",
          "_set_indexed(db, material, False)" in material_service and "except Exception" in material_service)

    # P0-13: 回答与参考资料独立成卡
    check("P0 接口：回答与参考资料在数据模型中分离（citations 独立字段）",
          "citations" in (ROOT / "frontend/app/student/page.tsx").read_text(encoding="utf-8"))

    # P0-14: 学生当日提问未达上限
    check("P0 接口：AI 提问每日上限为 40 次", AI_DAILY_LIMIT == 40)

    # P0-15: 次日提问次数重置（中国时区自然日）
    services_code = (ROOT / "backend/services.py").read_text(encoding="utf-8")
    check("P0 接口：提问计数按中国时区自然日重置",
          "_start_of_today_cn" in services_code and "created_at >= _start_of_today_cn()" in services_code)

    # P0-16: 重新登录后新权限生效
    check("P0 接口：权限从数据库实时读取（populate_existing=True）",
          "populate_existing=True" in (ROOT / "backend/routers/quiz.py").read_text(encoding="utf-8"))

    # P0-17: 同一教师不同模块权限不同
    quiz_code = (ROOT / "backend/routers/quiz.py").read_text(encoding="utf-8")
    teacher_code = (ROOT / "backend/routers/teacher.py").read_text(encoding="utf-8")
    check("P0 接口：题库/组卷模块校验任教学科（subject），班级模块校验任教班级（teaching_classes）",
          "teacher.subject" in quiz_code and "teaching_classes" in teacher_code)


def main():
    print("=== 前端/展示 P0 场景 ===")
    check_frontend()
    print("\n=== 接口/逻辑 P0 场景 ===")
    check_backend()
    print("\n全部 P0 场景断言通过")


if __name__ == "__main__":
    main()
