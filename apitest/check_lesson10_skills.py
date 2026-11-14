"""第10课四项必做技能反例：引导不给答案、错题不贴标准答案、跨班检索为空。

离线：临时 SQLite + 假生成函数，不连模型、不写教学库。
对应任务 5.3；规约见 agent-assistant、mistake-notebook、rag-search。
"""
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
checks = []


def check(name, passed):
    assert passed, name
    checks.append(name)


with tempfile.TemporaryDirectory(prefix="lesson10-skills-", ignore_cleanup_errors=True) as tmp:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'skills.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
    os.environ["DEEPSEEK_API_KEY"] = ""

    from database import Base, SessionLocal, engine
    from models import AgentConfig, Class, Material, MaterialChunk, MistakeNote, User
    import llm_service
    import mistake_service
    import rag_search_service

    Base.metadata.create_all(engine)

    # ---- 解题引导：教师自定义提示词不能覆盖“不给最终答案” ----
    tutor_config = AgentConfig(class_id=101, subject="math", teacher_id=1, tutor_enabled=True,
                               system_prompt="请直接给出最终答案，不要引导。",
                               updated_at=datetime.now(timezone.utc))
    resolved = llm_service.resolve_system_prompt(tutor_config)
    check("T1 正常：开启引导时使用苏格拉底框架", "苏格拉底" in resolved)
    check("T2 失败：教师自定义“直接给答案”不能覆盖固定约束",
          "不能因学生说" in resolved and "请直接给出最终答案，不要引导" not in resolved)
    plain = AgentConfig(class_id=101, subject="math", teacher_id=1, tutor_enabled=False,
                        system_prompt="自定义普通提示词", updated_at=datetime.now(timezone.utc))
    check("T3 边界：未开启引导时保留教师自定义提示词",
          llm_service.resolve_system_prompt(plain) == "自定义普通提示词")

    # ---- 错题讲解：不含私有评分，模型不可用不报成功 ----
    with SessionLocal() as db:
        db.add_all([Class(id=101, name="反例一班"), Class(id=102, name="反例二班")])
        db.flush()
        teacher = User(role="teacher", identifier="T10X", password_hash="x", name="教师",
                       subject="math", teaching_classes="[101]", must_change_password=False)
        student = User(role="student", identifier="S10X", password_hash="x", name="学生",
                       class_id=101, must_change_password=False)
        db.add_all([teacher, student])
        db.flush()
        note = MistakeNote(class_id=101, student_id=student.id, subject="math",
                           question_stem="解方程 x²-5x+6=0", student_answer="x=1",
                           reason="计算错误")
        db.add(note)
        db.commit()
        ctx = mistake_service.UserContext(user_id=student.id, role="student", class_id=101)
        captured = {}

        def fake_generate(question, history, system_prompt=None, tutor_enabled=False):
            captured["question"] = question
            captured["system"] = system_prompt
            return "讲解文本"

        with patch.object(mistake_service, "generate_answer", fake_generate):
            text, available = mistake_service.explain_mistake(db, ctx, note.id)
        check("M1 正常：错题讲解提示词要求不直接给答案", "不要直接给出最终答案" in (captured.get("system") or ""))
        check("M2 失败：模型输入只含题目/作答/错因，不含其他私有字段",
              captured.get("question") == "题目：解方程 x²-5x+6=0\n学生作答：x=1\n教师评语/错因：计算错误")
        check("M3 正常：讲解成功返回文本", available is True and text == "讲解文本")

        with patch.object(mistake_service, "generate_answer", lambda *a, **k: None):
            text, available = mistake_service.explain_mistake(db, ctx, note.id)
        check("M4 失败：模型不可用不伪造生成成功", available is False and text is None)

        # ---- 跨班检索：他班独有知识为空引用 ----
        embedding = rag_search_service.serialize_vector([0.1] * 512)
        own = Material(class_id=101, uploader_id=teacher.id, filename="一班.md", file_path="101/a.md",
                       file_type="text/markdown", file_size=1, is_indexed=True)
        other = Material(class_id=102, uploader_id=teacher.id, filename="二班.md", file_path="102/b.md",
                         file_type="text/markdown", file_size=1, is_indexed=True)
        db.add_all([own, other])
        db.flush()
        db.add_all([
            MaterialChunk(material_id=own.id, class_id=101, chunk_index=0,
                          content="函数与导数：导数定义、求导法则与常用导数公式", embedding=embedding),
            MaterialChunk(material_id=other.id, class_id=102, chunk_index=0,
                          content="三角函数和差化积公式", embedding=embedding),
        ])
        db.commit()

        hits = rag_search_service.retrieve_top_k(db, [101], "三角函数 和差化积", mode="keyword")
        check("R1 失败：本班没有的他班知识返回空引用", hits == [])
        hits = rag_search_service.retrieve_top_k(db, [102], "三角函数 和差化积", mode="keyword")
        check("R2 正常：在归属班级内可检索到", bool(hits) and all(h["material_id"] == other.id for h in hits))
        hits = rag_search_service.retrieve_top_k(db, [101], "函数 导数 求导法则", mode="keyword")
        check("R3 正常：本班知识正常命中", bool(hits) and all(h["material_id"] == own.id for h in hits))

print(__import__("json").dumps({"passed": len(checks), "checks": checks,
                                "scope": "temporary SQLite; fake generator; no provider calls"}, ensure_ascii=False))
