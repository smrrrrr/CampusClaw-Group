"""智能命题隔离验收（add-smart-question-generation，tasks 8.2）。

使用临时数据库 + 虚构 stream_chat，覆盖规约各 Scenario、越权 404/403、
组卷算法示例、学生卷去答案。不依赖真实 DeepSeek Key。

用法（项目根）：
    PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py
"""

import asyncio
import json
import os
import re
import tempfile
import threading
import time


async def main():
    with tempfile.TemporaryDirectory(prefix="quiz-test-", ignore_cleanup_errors=True) as temp:
        os.environ["DATABASE_URL"] = f"sqlite:///{temp}/test.db"
        os.environ["UPLOAD_DIR"] = f"{temp}/uploads"
        os.environ["DEEPSEEK_API_KEY"] = "test-key"  # 让 503 检查仅在显式清空时触发

        from database import Base, SessionLocal, engine
        from main import app
        from models import (
            Class, QuestionItem, QuestionGeneration, QuestionPaper, QuestionEvent,
            QuizPublication, ResearchMaterial, ResearchChunk, Role, User, Material,
        )
        from security import hash_password
        from research_service import digest
        from material_service import write_physical_file
        import routers.quiz as quiz_router

        Base.metadata.create_all(engine)

        # ---- 准备数据：两个学科教师、两个班、两份数学资料 ----
        math_content = "# 立体几何\n\n## 一、向量夹角\n\n两向量夹角用数量积公式计算。\n\n### 例题\n\n**题干**：求两向量夹角。\n\n**答案**：用公式。\n"
        with SessionLocal() as db:
            db.add_all([Class(id=101, name="Class A"), Class(id=102, name="Class B"), Class(id=201, name="Class C")])
            for ident, role, subject, classes, cid in [
                ("TM", Role.teacher, "math", "[101,102]", None),
                ("TM2", Role.teacher, "math", "[101,102]", None),
                ("TP", Role.teacher, "physics", "[101]", None),
                ("S1", Role.student, None, None, 101),
            ]:
                db.add(User(identifier=ident, role=role, subject=subject, teaching_classes=classes,
                            class_id=cid, name=ident, password_hash=hash_password("Test@2026"),
                            must_change_password=False))
            db.commit()
            # 数学资料
            path = "research/math/test/source.md"
            write_physical_file(math_content.encode(), path)
            rm = ResearchMaterial(subject="math", uploader_id=1, filename="立体几何.md", file_path=path,
                                  source_sha256=digest(math_content.encode()), content=math_content, assets_json="[]")
            db.add(rm)
            db.flush()
            for i, chunk in enumerate(["立体几何 向量夹角 数量积", "两向量夹角公式 cos"], 1):
                db.add(ResearchChunk(research_material_id=rm.id, subject="math", chunk_index=i, content=chunk, embedding=b"\x00"))
            db.commit()
            math_rm_id = rm.id

        checks = []

        def check(name, passed):
            checks.append((name, bool(passed)))
            print(("  ✓ " if passed else "  ✗ ") + name)

        # ---- 虚构 stream_chat ----
        fake_output = {"value": ""}

        async def fake_stream(messages, **kw):
            for i in range(0, len(fake_output["value"]), 20):
                hook = fake_output.pop("hook", None)  # 模拟生成期间发生的外部变化
                if hook:
                    hook()
                yield fake_output["value"][i:i + 20]

        quiz_router.stream_chat = fake_stream
        import llm_service
        quiz_router.LLMGenerationError = llm_service.LLMGenerationError

        def frames(resp):
            assert resp.status_code == 200, (resp.status_code, resp.text)
            return [json.loads(l[5:]) for l in resp.text.splitlines() if l.startswith("data:")]

        def q(**kw):
            base = {"type": "single_choice", "difficulty": "medium", "knowledge_points": ["立体几何"],
                    "stem": "求两向量夹角", "options": [{"label": l, "text": f"选项{l}"} for l in "ABCD"],
                    "answer": "A", "explanation": "解析：用数量积。", "origin": "original", "source_refs": ["S1"]}
            base.update(kw)
            return base

        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {}
            for who in ["TM", "TM2", "TP", "S1"]:
                r = await client.post("/api/auth/login", json={"identifier": who, "password": "Test@2026"})
                headers[who] = {"Authorization": "Bearer " + r.json()["access_token"]}

            async def req(method, path, who="TM", **kw):
                return await client.request(method, "/api/teacher/quiz" + path, headers=headers[who], **kw)

            # === 知识点词表（1.2）===
            r = await req("GET", "/knowledge-points", "TM")
            check("数学词表返回", r.status_code == 200 and "立体几何" in r.json()["knowledge_points"])
            r = await req("GET", "/knowledge-points", "S1")
            check("学生访问词表 403", r.status_code == 403)

            # === 生成：配额校验（SC 配比不一致）===
            bad = {"research_material_ids": [math_rm_id], "knowledge_points": ["立体几何"],
                   "type_counts": {"single_choice": 4, "fill_blank": 2, "short_answer": 2},
                   "difficulty_counts": {"easy": 3, "medium": 3, "hard": 1}}
            r = await req("POST", "/generations", json=bad)
            check("题型/难度合计不等 400", r.status_code == 400)

            # === 生成：词表外知识点 400 ===
            bad2 = {"research_material_ids": [math_rm_id], "knowledge_points": ["不存在的知识点"],
                    "type_counts": {"single_choice": 3}, "difficulty_counts": {"medium": 3}}
            r = await req("POST", "/generations", json=bad2)
            check("词表外知识点 400", r.status_code == 400)

            # === 生成：他科资料 404 ===
            with SessionLocal() as db:
                phy = "research/physics/x/source.md"
                phy_bytes = "# 物理\n\n## 一、运动学\n\n内容".encode("utf-8")
                write_physical_file(phy_bytes, phy)
                from research_service import digest as dg
                prm = ResearchMaterial(subject="physics", uploader_id=3, filename="物理.md", file_path=phy,
                                       source_sha256=dg(phy_bytes), content=phy_bytes.decode("utf-8"), assets_json="[]")
                db.add(prm); db.commit(); phy_id = prm.id
            r = await req("POST", "/generations", json={"research_material_ids": [phy_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 3},
                    "difficulty_counts": {"medium": 3}})
            check("选用他科资料 404", r.status_code == 404)

            # === 生成：模型照抄资料细分知识点 → 归一后通过 ===
            sub = {"questions": [q(knowledge_points=["空间向量基本定理"])], "gaps": []}
            fake_output["value"] = json.dumps(sub, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["空间向量"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            events = frames(r)
            done = [e for e in events if e.get("type") == "done"]
            check("细分知识点：归一到所选知识点后通过",
                  bool(done) and done[0]["accepted_ids"] and not done[0]["rejected"])
            if done and done[0]["accepted_ids"]:
                with SessionLocal() as db:
                    from models import QuestionItem
                    item = db.get(QuestionItem, done[0]["accepted_ids"][0])
                    check("细分知识点：落库知识点为所选标签",
                          json.loads(item.knowledge_points_json) == ["空间向量"])
            # === 生成：不构成字面包含的细分术语 → 判越界（不做同义词推断）===
            sub3 = {"questions": [q(knowledge_points=["共面向量定理"])], "gaps": []}
            fake_output["value"] = json.dumps(sub3, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["空间向量"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            events = frames(r)
            done = [e for e in events if e.get("type") == "done"]
            check("非字面包含的细分术语：判超出范围",
                  bool(done) and not done[0]["accepted_ids"]
                  and "知识点超出本次所选范围" in done[0]["rejected"][0]["reasons"])

            # === 提示词：要求逐字复制标签 ===
            from question_service import QUESTION_PROMPT as _QP, build_user_message as _bum
            check("提示词含逐字复制约束", "逐字" in _QP and "原样复制" in _QP)
            _msg = _bum({"types": {"single_choice": 1}, "difficulties": {"medium": 1}},
                        ["空间向量"], "", "<ctx>")
            check("用户消息以 JSON 数组重申标签", '["空间向量"]' in _msg)

            # === 生成：与所选知识点无关的表述仍判越界 ===
            sub2 = {"questions": [q(knowledge_points=["数列求和"])], "gaps": []}
            fake_output["value"] = json.dumps(sub2, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["空间向量"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            events = frames(r)
            done = [e for e in events if e.get("type") == "done"]
            check("无关细分知识点：仍判超出范围",
                  bool(done) and not done[0]["accepted_ids"]
                  and "知识点超出本次所选范围" in done[0]["rejected"][0]["reasons"])

            # === 生成：全部通过（8 题）===
            ok8 = {"questions": [q(stem=f"求两向量夹角 第{i}题") for i in range(8)], "gaps": []}
            fake_output["value"] = "```json\n" + json.dumps(ok8, ensure_ascii=False) + "\n```"
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 8},
                    "difficulty_counts": {"medium": 8}})
            fr = frames(r)
            done = next((f for f in fr if f["type"] == "done"), None)
            check("全部通过 8 题落库", done is not None and len(done["accepted_ids"]) == 8 and not done["rejected"])
            pending_ids = done["accepted_ids"] if done else []

            # === 生成：部分不合格（6 通过 2 未通过）===
            partial = {"questions": [q(stem=f"另一题 {i}") for i in range(6)] + [q(answer="E"), q(source_refs=["S9"])], "gaps": []}
            fake_output["value"] = json.dumps(partial, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 8},
                    "difficulty_counts": {"medium": 8}})
            fr = frames(r)
            done = next((f for f in fr if f["type"] == "done"), None)
            check("部分不合格：6 通过 2 未通过", done is not None and len(done["accepted_ids"]) == 6 and len(done["rejected"]) == 2)

            # === 生成：非 JSON → error，不落题 ===
            before_count = 0
            with SessionLocal() as db:
                before_count = db.query(QuestionItem).count()
            fake_output["value"] = "这不是 JSON，只是一段正文。"
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 3},
                    "difficulty_counts": {"medium": 3}})
            fr = frames(r)
            check("非 JSON 返回 error", any(f["type"] == "error" for f in fr))
            with SessionLocal() as db:
                check("非 JSON 不保存题目", db.query(QuestionItem).count() == before_count)
                check("非 JSON 写失败记录", db.query(QuestionGeneration).filter_by(status="failed").count() >= 1)

            # === 单反斜杠 LaTeX：修补后正常生成并计数（harden-model-json-escapes 4.2）===
            # 样本由 2026-10-23 真实失败输出提炼为最小片段：同一字符串混用 \\ 与 \ 两种写法。
            # 手写 JSON 原文，与模型真实输出同形态（json.dumps 会替我们正确转义，测不到修补）。
            BS, DBS = "\\", "\\\\"
            expect_stem = ("如图，在正方体中 $\\overrightarrow{AB}=(1,0,1)$，"
                           "$\\overrightarrow{AF}=(0,1,1)$，求 $\\vec{a}\\cdot\\vec{b}$ 的夹角，"
                           "已知 $\\sqrt{2}\\neq 0$，$\\begin{cases}x=1\\y=2\\end{cases}$，"
                           "答案为 $\\frac{1}{2}$。\n第二步验证。")
            expect_option = "选项A $\\cos\\theta$"
            expect_explanation = "由 $\\frac{1}{2}$ 与 $\\times$ 可知。"
            stem_raw = (DBS + "overrightarrow{AB}=(1,0,1)$，$" + BS + "overrightarrow{AF}=(0,1,1)$，求 $"
                        + BS + "vec{a}" + BS + "cdot" + BS + "vec{b}$ 的夹角，已知 $"
                        + BS + "sqrt{2}" + BS + "neq 0$，$" + BS + "begin{cases}x=1" + DBS + "y=2"
                        + BS + "end{cases}$，答案为 $" + BS + "frac{1}{2}$。" + BS + "n第二步验证。")
            raw_mixed = ('{"questions": [{"type": "single_choice", "difficulty": "medium",'
                         ' "knowledge_points": ["立体几何"], "stem": "如图，在正方体中 $' + stem_raw + '",'
                         ' "options": [{"label": "A", "text": "' + expect_option + '"},'
                         ' {"label": "B", "text": "选项B"}, {"label": "C", "text": "选项C"},'
                         ' {"label": "D", "text": "选项D"}], "answer": "A",'
                         ' "explanation": "' + expect_explanation + '", "origin": "new",'
                         ' "source_refs": ["S1"]}], "gaps": []}')
            fake_output["value"] = raw_mixed
            with SessionLocal() as db:
                before_gen = db.query(QuestionGeneration).count()
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            fr = frames(r)
            done = next((f for f in fr if f["type"] == "done"), None)
            check("单反斜杠 LaTeX：生成成功且题目保存",
                  done is not None and len(done["accepted_ids"]) == 1
                  and not any(f["type"] == "error" for f in fr))
            saved = (await req("GET", f"/items/{done['accepted_ids'][0]}")).json() if done and done["accepted_ids"] else {}
            check("单反斜杠 LaTeX：题干还原为 LaTeX 命令", saved.get("stem") == expect_stem)
            check("单反斜杠 LaTeX：选项与解析同样还原",
                  [o["text"] for o in saved.get("options", [])] == [expect_option, "选项B", "选项C", "选项D"]
                  and saved.get("explanation") == expect_explanation)
            check("单反斜杠 LaTeX：字段中不含换页、退格",
                  "\f" not in saved.get("stem", "") and "\b" not in saved.get("stem", "")
                  and "\f" not in saved.get("explanation", ""))
            with SessionLocal() as db:
                ev = (db.query(QuestionEvent).filter_by(target_type="generation", action="generate")
                      .order_by(QuestionEvent.id.desc()).first())
                detail = json.loads(ev.detail_json) if ev else {}
                last_gen = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
            # 单反斜杠命令：\overrightarrow \vec \cdot \vec \vec \sqrt \neq \begin \end \frac
            # 加选项 \cos、解析 \frac \times，共 13 处
            check("单反斜杠 LaTeX：generate 事件记录 escape_repairs=13",
                  isinstance(detail.get("escape_repairs"), int) and detail["escape_repairs"] == 13)
            check("单反斜杠 LaTeX：本次生成成功、未写失败记录",
                  last_gen.status == "succeeded" and db.query(QuestionGeneration).count() == before_gen + 1)

            # === 漏网控制字符：U+000C 的题判未通过，其余照常保存 ===
            with SessionLocal() as db:
                before_count = db.query(QuestionItem).count()
            fake_output["value"] = json.dumps({"questions": [
                q(stem="正常的题", explanation="解析正常。"),
                q(stem="含换页的题干\f残留公式"),
            ], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 2},
                    "difficulty_counts": {"medium": 2}})
            fr = frames(r)
            done = next((f for f in fr if f["type"] == "done"), None)
            rejected = done["rejected"] if done else []
            with SessionLocal() as db:
                after_count = db.query(QuestionItem).count()
            check("U+000C 题干：该题未通过、正常题照常保存",
                  done is not None and len(done["accepted_ids"]) == 1 and len(rejected) == 1
                  and after_count == before_count + 1)
            check("U+000C 题干：原因为含不可见控制字符",
                  bool(rejected) and any("含不可见控制字符，疑似公式转义错误" in reason for reason in rejected[0]["reasons"]))

            # === 截断输出：失败原因含行列且不含原文 ===
            fake_output["value"] = '{"questions": [\n' + "\n" * 10 + '{"stem": "半截'
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            fr = frames(r)
            with SessionLocal() as db:
                last = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
            check("截断输出：返回 error 且不落题",
                  any(f["type"] == "error" for f in fr) and not any(f["type"] == "done" for f in fr))
            check("截断输出：失败原因含第 12 行与列号",
                  "第 12 行" in (last.error or "") and "列" in (last.error or ""))
            check("截断输出：失败原因不含模型原文", "半截" not in (last.error or ""))

            # === 无 Key → 503 ===
            import config
            old_key = quiz_router.settings.deepseek_api_key
            quiz_router.settings.deepseek_api_key = ""
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 3},
                    "difficulty_counts": {"medium": 3}})
            check("无 Key 返回 503", r.status_code == 503)
            quiz_router.settings.deepseek_api_key = old_key

            # === 候选题隔离：他人读取 404，学生 403 ===
            pid = pending_ids[0]
            r = await req("GET", f"/items/{pid}", "TM2")
            check("同科同事读取他人候选题 404", r.status_code == 404)
            r = await req("GET", f"/items/{pid}", "S1")
            check("学生读取题目 403", r.status_code == 403)
            r = await req("GET", f"/items/{pid}", "TP")
            check("跨学科读取题目 404", r.status_code == 404)

            # === 未确认即通过 400 ===
            item = (await req("GET", f"/items/{pid}")).json()
            r = await req("POST", f"/items/{pid}/approve", json={"revision": item["revision"], "confirmed": False})
            check("未确认即通过 400", r.status_code == 400)

            # === 通过 → 入库 ===
            r = await req("POST", f"/items/{pid}/approve", json={"revision": item["revision"], "confirmed": True})
            check("确认通过 200 且 approved", r.status_code == 200 and r.json()["status"] == "approved")
            approved_item = r.json()

            # === 重复题干通过 → 409 ===
            dup_pid = pending_ids[1]
            # 把另一道候选题题干改成与已通过题相同
            dup_item = (await req("GET", f"/items/{dup_pid}")).json()
            r = await req("PUT", f"/items/{dup_pid}", json={"revision": dup_item["revision"],
                    "stem": approved_item["stem"], "options": approved_item["options"],
                    "answer": approved_item["answer"], "explanation": approved_item["explanation"],
                    "knowledge_points": approved_item["knowledge_points"],
                    "source_refs": [s["ref"] for s in approved_item["sources"]]})
            check("修改候选题成功", r.status_code == 200)
            r2 = await req("POST", f"/items/{dup_pid}/approve", json={"revision": r.json()["revision"], "confirmed": True})
            check("重复题干通过 409", r2.status_code == 409)

            # === 驳回后尝试通过 409 ===
            rej_pid = pending_ids[2]
            ri = (await req("GET", f"/items/{rej_pid}")).json()
            r = await req("POST", f"/items/{rej_pid}/reject", json={"revision": ri["revision"], "reason": "不合适"})
            check("驳回成功", r.status_code == 200)
            rr = await req("POST", f"/items/{rej_pid}/approve", json={"revision": r.json()["revision"], "confirmed": True})
            check("驳回后通过 409", rr.status_code == 409)

            # === 入库题目不可原地修改 409 ===
            r = await req("PUT", f"/items/{pid}", json={"revision": approved_item["revision"], "stem": "改",
                    "options": approved_item["options"], "answer": "A", "explanation": "x",
                    "knowledge_points": ["立体几何"], "source_refs": []})
            check("入库题目修改 409", r.status_code == 409)

            # === 复制为新候选 ===
            r = await req("POST", f"/items/{pid}/copy")
            check("复制为新候选 200 pending", r.status_code == 200 and r.json()["status"] == "pending")

            # === 题库：同科同事可见 approved ===
            r = await req("GET", "/items?status=approved", "TM2")
            check("同科同事可见题库", r.status_code == 200 and r.json()["total"] >= 1)

            # === 补足题库用于组卷：批量通过 13 道单选/解答 ===
            # 直接构造 approved 题目（绕过模型，模拟题库）
            with SessionLocal() as db:
                tm = db.query(User).filter_by(identifier="TM").one()
                from question_service import stem_key, content_sha256
                def add_approved(qtype, diff, idx):
                    payload = {"type": qtype, "difficulty": diff, "knowledge_points": ["立体几何"],
                               "stem": f"{qtype}-{diff}-{idx}", "options": (
                                   [{"label": l, "text": f"o{l}"} for l in "ABCD"] if qtype in ("single_choice", "multiple_choice") else []),
                               "answer": ("A" if qtype == "single_choice" else ("解答要点" if qtype == "short_answer" else "A")),
                               "explanation": "解析", "origin": "new", "source_refs": ["S1"]}
                    db.add(QuestionItem(subject="math", author_id=tm.id, type=qtype, difficulty=diff,
                        knowledge_points_json='["立体几何"]', stem=payload["stem"],
                        options_json=json.dumps(payload["options"]), answer_json=json.dumps(payload["answer"]),
                        explanation="解析", origin="new", sources_json="[]", assets_json="[]",
                        status="approved", archived=False, stem_key=stem_key(payload["stem"]) + f"{idx}",
                        content_sha256=content_sha256(payload), revision=1))
                for i in range(20):
                    add_approved("single_choice", ["easy","medium","hard"][i%3], f"sc{i}")
                for i in range(8):
                    add_approved("short_answer", ["easy","medium","hard"][i%3], f"sa{i}")
                db.commit()

            # === 组卷 3:5:2 → 13 题 80 分 ===
            blueprint = {"title": "验收试卷", "duration": 90, "knowledge_points": ["立体几何"],
                         "groups": [{"type": "single_choice", "count": 10, "score": 5},
                                    {"type": "short_answer", "count": 3, "score": 10}],
                         "difficulty_pct": {"easy": 30, "medium": 50, "hard": 20}}
            r = await req("POST", "/papers", json=blueprint)
            check("组卷成功 201", r.status_code == 200)
            paper = r.json()
            check("组卷 13 题", paper["item_count"] == 13)
            check("组卷总分 80", abs(paper["total_score"] - 80) < 1e-6)

            # === 题库不足 422 ===
            with SessionLocal() as db:
                db.query(QuestionItem).filter_by(type="multiple_choice").delete()
                db.commit()
            bad_bp = {"title": "缺口卷", "duration": 60, "knowledge_points": ["立体几何"],
                      "groups": [{"type": "multiple_choice", "count": 2, "score": 5}],
                      "difficulty_pct": {"easy": 0, "medium": 0, "hard": 100}}
            r = await req("POST", "/papers", json=bad_bp)
            check("题库不足 422 并列出缺口", r.status_code == 422 and "gaps" in json.dumps(r.json(), ensure_ascii=False))

            # === 学生卷预览：不含答案/解析/S编号 ===
            r = await req("GET", f"/papers/{paper['id']}/preview")
            md = r.text
            check("预览 200 markdown", r.status_code == 200)
            check("学生卷不含答案/解析/S编号",
                  "答案" not in md and "[S1]" not in md and "解析" not in md)
            option_lines = re.findall(r"^ {3,4}([A-D])\. .*$", md, re.MULTILINE)
            tenth = re.search(r"^10\. .*\n\n((?: {4}.*\n?)+)", md, re.MULTILINE)
            check("学生卷选择题：A–D 每项一行且行尾硬换行",
                  option_lines[:40] == list("ABCD") * 10
                  and len(re.findall(r"^ {3,4}[A-D]\. .*\\$", md, re.MULTILINE)) == 30)
            check("学生卷第 10 题：选项缩进 4 格",
                  tenth is not None and all(line.startswith("    ") for line in tenth.group(1).splitlines()))

            # === 定稿 ===
            p = (await req("GET", f"/papers/{paper['id']}")).json()
            r = await req("POST", f"/papers/{paper['id']}/finalize", json={"revision": p["revision"]})
            check("定稿成功", r.status_code == 200 and r.json()["status"] == "final")

            # === 草稿发布 409：先建草稿 ===
            r = await req("POST", "/papers", json=blueprint)
            draft = r.json()
            rr = await req("POST", f"/papers/{draft['id']}/publish", json={"revision": draft["revision"],
                    "reviewed": True, "class_ids": [101]})
            check("草稿发布 409", rr.status_code == 409)

            # === 越权班级 403 ===
            p = (await req("GET", f"/papers/{paper['id']}")).json()
            rr = await req("POST", f"/papers/{paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": True, "class_ids": [101, 201]})
            check("批次混入非任教班级 403", rr.status_code == 403)

            # === 未确认核对 400 ===
            p = (await req("GET", f"/papers/{paper['id']}")).json()
            rr = await req("POST", f"/papers/{paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": False, "class_ids": [101]})
            check("未确认核对 400", rr.status_code == 400)

            # === 发布到两个班 ===
            p = (await req("GET", f"/papers/{paper['id']}")).json()
            rr = await req("POST", f"/papers/{paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": True, "class_ids": [101, 102]})
            check("发布到两个班 200", rr.status_code == 200 and len(rr.json()["material_ids"]) == 2)
            mids = rr.json()["material_ids"]
            with SessionLocal() as db:
                mats = db.query(Material).filter(Material.id.in_(mids)).all()
                check("发布资料 is_indexed=False", all(m.is_indexed is False for m in mats))
                check("发布资料标签含试卷", all("试卷" in m.tags for m in mats))
                check("发布写入 quiz_publications", db.query(QuizPublication).count() == 2)

            # === 重复发布复用 ===
            p = (await req("GET", f"/papers/{paper['id']}")).json()
            rr2 = await req("POST", f"/papers/{paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": True, "class_ids": [101]})
            check("重复发布复用资料", rr2.status_code == 200 and set(rr2.json()["material_ids"]).issubset(set(mids)))

            # === 答案卷 ===
            r = await req("GET", f"/papers/{paper['id']}/answer-key")
            check("答案卷含答案与解析", r.status_code == 200 and "答案" in r.text and "解析" in r.text)

            # === 带配图资料：生成、复核、发布复制原图 ===
            png = b"\x89PNG\r\n\x1a\n" + b"fig-bytes" * 8
            img_content = "# 立体几何配图\n\n## 一、例题\n\n![正方体](fig%201.png)\n\n求异面直线夹角。\n"
            with SessionLocal() as db:
                write_physical_file(img_content.encode(), "research/math/img/source.md")
                write_physical_file(png, "research/math/img/fig 1.png")
                irm = ResearchMaterial(subject="math", uploader_id=1, filename="立体几何配图.md",
                                       file_path="research/math/img/source.md",
                                       source_sha256=digest(img_content.encode()), content=img_content,
                                       assets_json=json.dumps([{"name": "fig 1.png", "path": "research/math/img/fig 1.png",
                                                                "sha256": digest(png), "mime": "image/png"}]))
                db.add(irm); db.commit(); img_rm_id = irm.id
            img_ref = f"sources/{img_rm_id}/fig%201.png"

            async def generate_one(questions, type_counts, diff_counts):
                fake_output["value"] = json.dumps({"questions": questions, "gaps": []}, ensure_ascii=False)
                r = await req("POST", "/generations", json={"research_material_ids": [img_rm_id],
                        "knowledge_points": ["立体几何"], "type_counts": type_counts, "difficulty_counts": diff_counts})
                return next((f for f in frames(r) if f["type"] == "done"), None)

            # === 公式结构校验（fix-quiz-latex-and-option-layout 1.1–1.3）===
            from question_service import check_formula_structure
            formula_cases = [
                (r"$\vec{a}$", []),
                ("$$\\begin{cases}x\\\\y\\end{cases}$$", []),
                (r"$\{x\mid x>0\}$", []),
                (r"$\left\{ a \right.$", []),
                (r"价格 \$5，$x$", []),
                ("解析中 $$x$$ 与 $y$ 混用", []),
                ("集合{1,2}", []),
                (r"$a}{b$", ["公式花括号不配对"]),
                (r"$\frac{1}{2}", ["公式定界符 $ 不成对"]),
            ]
            check("公式结构：转义、cases 与定界符正反用例",
                  all(check_formula_structure(text) == expected for text, expected in formula_cases))
            check("提示词要求公式花括号成对并写完整命令",
                  "公式中的花括号必须成对" in _QP and r"\frac{1}{2}" in _QP)

            bad_option = r"$-\frac{1}{2}\vec{a}+\frac{2}{3}\vec{b}+\frac{1}{2}\vec{c$"
            fake_output["value"] = json.dumps({"questions": [
                q(stem="#15 原样选项校验", options=[{"label": l, "text": bad_option} for l in "ABCD"])
            ], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            done = next((f for f in frames(r) if f["type"] == "done"), None)
            check("#15 原样选项：生成时未通过且原因含字段名",
                  done is not None and not done["accepted_ids"] and done["rejected"]
                  and any("选项 D 公式花括号不配对" in reason
                          for reason in done["rejected"][0]["reasons"]))

            fake_output["value"] = json.dumps({"questions": [q(stem="公式修改与复核测试")], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1},
                    "difficulty_counts": {"medium": 1}})
            done = next((f for f in frames(r) if f["type"] == "done"), None)
            formula_id = done["accepted_ids"][0] if done and done["accepted_ids"] else 0
            fi = (await req("GET", f"/items/{formula_id}")).json()
            formula_body = {"stem": fi["stem"], "options": fi["options"], "answer": fi["answer"],
                            "explanation": fi["explanation"], "knowledge_points": fi["knowledge_points"],
                            "source_refs": [s["ref"] for s in fi["sources"]]}
            broken_options = [dict(o) for o in fi["options"]]
            broken_options[0]["text"] = r"$\vec{a$"
            r = await req("PUT", f"/items/{formula_id}",
                          json={**formula_body, "revision": fi["revision"], "options": broken_options})
            unchanged = (await req("GET", f"/items/{formula_id}")).json()
            check("修改引入不配对括号：400 且题目与 revision 不变",
                  r.status_code == 400 and "选项 A 公式花括号不配对" in r.json()["detail"]
                  and unchanged["revision"] == fi["revision"] and unchanged["options"] == fi["options"])
            fixed_options = [dict(o) for o in fi["options"]]
            fixed_options[0]["text"] = r"$\vec{a}$"
            r = await req("PUT", f"/items/{formula_id}",
                          json={**formula_body, "revision": fi["revision"], "options": fixed_options})
            saved_revision = r.json().get("revision") if r.status_code == 200 else fi["revision"]
            rr = await req("POST", f"/items/{formula_id}/approve",
                           json={"revision": saved_revision, "confirmed": True})
            check("补齐括号后保存并通过：进入题库且标记已修改",
                  r.status_code == 200 and rr.status_code == 200
                  and rr.json()["status"] == "approved" and rr.json()["modified_in_review"] is True)

            done = await generate_one([q(stem="配图资料的纯文字题")], {"single_choice": 1}, {"medium": 1})
            check("配图资料、题目不含图片：生成成功", done is not None and len(done["accepted_ids"]) == 1)
            done = await generate_one([q(stem=f"如图 ![正方体]({img_ref}) 求异面直线夹角")], {"single_choice": 1}, {"medium": 1})
            check("配图资料、题干引用原图：生成成功", done is not None and len(done["accepted_ids"]) == 1)
            img_item_id = done["accepted_ids"][0] if done and done["accepted_ids"] else 0
            done = await generate_one([q(stem=f"如图 ![伪图](sources/{img_rm_id}/nope.png) 求夹角")], {"single_choice": 1}, {"medium": 1})
            check("引用资料中不存在的配图：判为未通过", done is not None and not done["accepted_ids"] and len(done["rejected"]) == 1)

            ii = (await req("GET", f"/items/{img_item_id}")).json()
            check("含图题快照带原图路径与指纹", any(a["sha256"] == digest(png) and a.get("path") for a in ii.get("assets", [])))
            r = await req("POST", f"/items/{img_item_id}/approve", json={"revision": ii["revision"], "confirmed": True})
            check("含图题通过复核 200", r.status_code == 200 and r.json()["status"] == "approved")

            # === 判断题 / 填空题按类型修改答案 ===
            done = await generate_one([
                q(type="true_false", stem="正方体的体对角线互相平分", options=[], answer=True),
                q(type="fill_blank", stem="棱长为 1 的正方体体对角线长为 ____", options=[], answer=["√3"]),
            ], {"true_false": 1, "fill_blank": 1}, {"medium": 2})
            check("判断题与填空题生成成功", done is not None and len(done["accepted_ids"]) == 2)
            tf_id, fb_id = (done["accepted_ids"] + [0, 0])[:2] if done else (0, 0)
            for qid, new_answer, label in [(tf_id, False, "判断题答案改为布尔 false"), (fb_id, ["根号3"], "填空题答案按数组修改")]:
                it = (await req("GET", f"/items/{qid}")).json()
                r = await req("PUT", f"/items/{qid}", json={"revision": it["revision"], "stem": it["stem"],
                        "options": [], "answer": new_answer, "explanation": it["explanation"],
                        "knowledge_points": it["knowledge_points"], "source_refs": [x["ref"] for x in it["sources"]]})
                check(label, r.status_code == 200 and r.json()["answer"] == new_answer)

            # === 题型顺序打乱：学生卷与答案卷题号一致 ===
            def numbered(md, prefix):
                rows = []
                for line in md.splitlines():
                    m = re.match(prefix + r"(\d+)\. (.*)$", line)
                    if m:
                        rows.append((int(m.group(1)), re.sub(r"（[\d.]+ 分）$", "", m.group(2))))
                return rows

            async def same_numbering(paper_id):
                stu = (await req("GET", f"/papers/{paper_id}/preview")).text
                key = (await req("GET", f"/papers/{paper_id}/answer-key")).text
                a, b = numbered(stu, ""), numbered(key, "### ")
                return bool(a) and a == b

            shuffled_bp = {"title": "题型倒序卷", "duration": 40, "knowledge_points": ["立体几何"],
                           "groups": [{"type": "short_answer", "count": 2, "score": 10},
                                      {"type": "single_choice", "count": 2, "score": 5}],
                           "difficulty_pct": {"easy": 0, "medium": 100, "hard": 0}}
            r = await req("POST", "/papers", json=shuffled_bp)
            check("蓝图解答题在前、单选在后：组卷成功", r.status_code == 200)
            check("蓝图题型倒序：学生卷与答案卷题号一致", await same_numbering(r.json()["id"]))

            # 草稿编辑：把含图单选题放到解答题之后，并改分值
            sa_id = next(it["question_item_id"] for it in (await req("GET", f"/papers/{r.json()['id']}")).json()["items"]
                         if it["snapshot"]["type"] == "short_answer")
            r = await req("POST", "/papers", json=blueprint)
            img_paper = r.json()
            r = await req("PUT", f"/papers/{img_paper['id']}", json={"revision": img_paper["revision"],
                    "items": [{"question_item_id": sa_id, "score": 12.5}, {"question_item_id": img_item_id, "score": 7.5}]})
            check("草稿改为解答题在前的两题并改分值", r.status_code == 200 and r.json()["item_count"] == 2
                  and abs(r.json()["total_score"] - 20) < 1e-6)
            check("草稿手工倒序：学生卷与答案卷题号一致", await same_numbering(img_paper["id"]))
            stu = (await req("GET", f"/papers/{img_paper['id']}/preview")).text
            check("学生卷单选题排在解答题之前并保留配图", stu.index("求异面直线夹角") < stu.index("short_answer") and img_ref in stu)
            # 答案卷出处：快照 sources 中的 S 编号、资料名与原文摘录
            key = (await req("GET", f"/papers/{img_paper['id']}/answer-key")).text
            check("答案卷列出出处 S 编号与资料名", "**出处**：S1" in key and "> [S1] 立体几何配图.md 原文行" in key)
            src = (await req("GET", f"/items/{img_item_id}")).json()["sources"][0]
            check("答案卷出处带原文行号与摘录（与题目快照一致）",
                  f"> [S1] 立体几何配图.md 原文行 {src['start_line']}-{src['end_line']}：{src['excerpt'][:200]}" in key
                  and src["excerpt"].strip() != "")

            # 定稿并发布：原图复制为班级资料附件
            p = (await req("GET", f"/papers/{img_paper['id']}")).json()
            await req("POST", f"/papers/{img_paper['id']}/finalize", json={"revision": p["revision"]})
            p = (await req("GET", f"/papers/{img_paper['id']}")).json()
            rr = await req("POST", f"/papers/{img_paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": True, "class_ids": [101]})
            check("含图试卷发布 200", rr.status_code == 200)
            if rr.status_code == 200:
                from models import MaterialAsset
                with SessionLocal() as db:
                    assets = db.query(MaterialAsset).filter_by(material_id=rr.json()["material_ids"][0]).all()
                    check("发布复制原图且指纹一致", len(assets) == 1 and assets[0].sha256 == digest(png)
                          and assets[0].name == f"sources/{img_rm_id}/fig 1.png")

            # 原图被替换后发布：指纹不一致 409
            r = await req("POST", f"/papers/{img_paper['id']}/copy")
            copy_paper = r.json()
            await req("POST", f"/papers/{copy_paper['id']}/finalize", json={"revision": copy_paper["revision"]})
            write_physical_file(b"\x89PNG\r\n\x1a\nchanged", "research/math/img/fig 1.png")
            p = (await req("GET", f"/papers/{copy_paper['id']}")).json()
            rr = await req("POST", f"/papers/{copy_paper['id']}/publish", json={"revision": p["revision"],
                    "reviewed": True, "class_ids": [102]})
            check("原图被替换后发布 409（指纹不一致）", p["status"] == "final" and rr.status_code == 409 and "配图" in rr.json()["detail"])
            write_physical_file(png, "research/math/img/fig 1.png")

            # === 修改事件的前后指纹：与入库指纹同一口径 ===
            done = await generate_one([q(stem="指纹口径测试题")], {"single_choice": 1}, {"medium": 1})
            fp_id = done["accepted_ids"][0]
            it = (await req("GET", f"/items/{fp_id}")).json()
            body = {"stem": it["stem"], "options": it["options"], "answer": it["answer"],
                    "explanation": it["explanation"], "knowledge_points": it["knowledge_points"],
                    "source_refs": [x["ref"] for x in it["sources"]]}
            r = await req("PUT", f"/items/{fp_id}", json={**body, "revision": it["revision"]})
            r2 = await req("PUT", f"/items/{fp_id}", json={**body, "revision": r.json()["revision"], "explanation": "改写后的解析。"})
            with SessionLocal() as db:
                mods = [json.loads(e.detail_json) for e in db.query(QuestionEvent).filter_by(
                    target_type="item", target_id=fp_id, action="modify").order_by(QuestionEvent.id)]
            check("原样保存：修改前后指纹相同、不计为复核中修改",
                  r.status_code == 200 and mods[0]["before"] == mods[0]["after"] and r.json()["modified_in_review"] is False)
            check("改写解析：前指纹接上一条后指纹、后指纹变化、计为修改",
                  r2.status_code == 200 and mods[1]["before"] == mods[0]["after"] != mods[1]["after"]
                  and r2.json()["modified_in_review"] is True)
            with SessionLocal() as db:
                check("修改事件后指纹等于题目当前指纹", db.get(QuestionItem, fp_id).content_sha256 == mods[1]["after"])

            # === 生成后核对资料指纹：生成期间资料变化则整批作废 ===
            def counts():
                with SessionLocal() as db:
                    return (db.query(QuestionItem).count(),
                            db.query(QuestionGeneration).filter_by(status="failed").count())

            def mutate(rid, **values):
                def hook():
                    with SessionLocal() as db:
                        db.query(ResearchMaterial).filter_by(id=rid).update(values)
                        db.commit()
                return hook

            async def generate_during(rid, hook, stem):
                fake_output["value"] = json.dumps({"questions": [q(stem=stem)], "gaps": []}, ensure_ascii=False)
                fake_output["hook"] = hook
                r = await req("POST", "/generations", json={"research_material_ids": [rid],
                        "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1}, "difficulty_counts": {"medium": 1}})
                return frames(r)

            with SessionLocal() as db:
                img_rm = db.get(ResearchMaterial, img_rm_id)
                orig_sha, orig_assets = img_rm.source_sha256, img_rm.assets_json
            changed_assets = json.dumps([dict(a, sha256="0" * 64) for a in json.loads(orig_assets)])
            with SessionLocal() as db:
                tmp_bytes = "# 临时资料\n\n## 一、例题\n\n求夹角。\n".encode()
                write_physical_file(tmp_bytes, "research/math/tmp/source.md")
                tmp = ResearchMaterial(subject="math", uploader_id=1, filename="临时资料.md", file_path="research/math/tmp/source.md",
                                       source_sha256=digest(tmp_bytes), content=tmp_bytes.decode(), assets_json="[]")
                db.add(tmp); db.commit(); tmp_id = tmp.id

            def delete_tmp():
                with SessionLocal() as db:
                    db.delete(db.get(ResearchMaterial, tmp_id)); db.commit()

            for label, rid, hook, restore in [
                ("资料正文被替换", img_rm_id, mutate(img_rm_id, source_sha256="f" * 64), mutate(img_rm_id, source_sha256=orig_sha)),
                ("资料原图被替换", img_rm_id, mutate(img_rm_id, assets_json=changed_assets), mutate(img_rm_id, assets_json=orig_assets)),
                ("资料被删除", tmp_id, delete_tmp, None),
            ]:
                before = counts()
                fr = await generate_during(rid, hook, f"生成期间{label}的题")
                after = counts()
                with SessionLocal() as db:
                    last = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
                check(f"生成期间{label}：返回 error、不落题、写失败记录",
                      any(f["type"] == "error" for f in fr) and not any(f["type"] == "done" for f in fr)
                      and after[0] == before[0] and after[1] == before[1] + 1
                      and last.status == "failed" and "生成期间已变化" in (last.error or ""))
                if restore:
                    restore()
            done = await generate_one([q(stem="资料恢复后正常生成")], {"single_choice": 1}, {"medium": 1})
            check("资料恢复后生成正常、任务锁已释放", done is not None and len(done["accepted_ids"]) == 1)

            # === 生成中客户端断开：写失败记录与审计事件、不落题、释放任务锁 ===
            from starlette.requests import Request as StarletteRequest
            original_is_disconnected = StarletteRequest.is_disconnected

            async def always_disconnected(self):
                return True

            before = counts()
            StarletteRequest.is_disconnected = always_disconnected
            try:
                fake_output["value"] = json.dumps({"questions": [q(stem="断开连接时的题")], "gaps": []}, ensure_ascii=False)
                r = await req("POST", "/generations", json={"research_material_ids": [img_rm_id],
                        "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1}, "difficulty_counts": {"medium": 1}})
                fr = frames(r)
            finally:
                StarletteRequest.is_disconnected = original_is_disconnected
            after = counts()
            with SessionLocal() as db:
                last = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
                ev = db.query(QuestionEvent).filter_by(target_type="generation", target_id=last.id).one_or_none()
            check("检测到断开：无 done、不落题", not any(f["type"] == "done" for f in fr) and after[0] == before[0])
            check("检测到断开：写失败记录与 generate_failed 事件",
                  after[1] == before[1] + 1 and "断开" in (last.error or "")
                  and ev is not None and ev.action == "generate_failed")

            # 服务端关闭流（GeneratorExit）：直接驱动生成流，读到首帧后关闭
            from deps import CurrentUser
            before = counts()
            with SessionLocal() as db:
                tm = db.query(User).filter_by(identifier="TM").one()
                cu = CurrentUser(user_id=tm.id, role="teacher", class_id=None, must_change_password=False,
                                 teaching_classes=[101, 102], subject="math")

                class StillConnected:
                    async def is_disconnected(self):
                        return False

                fake_output["value"] = json.dumps({"questions": [q(stem="流被关闭时的题")], "gaps": []}, ensure_ascii=False)
                resp = quiz_router.create_generation(quiz_router.GenerationRequest(
                    research_material_ids=[img_rm_id], knowledge_points=["立体几何"],
                    type_counts={"single_choice": 1}, difficulty_counts={"medium": 1}), StillConnected(), cu, db)
                stream = resp.body_iterator
                await stream.__anext__()
                await stream.aclose()
                tm_id = tm.id
            after = counts()
            with SessionLocal() as db:
                last = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
            check("流被关闭：不落题、写断开失败记录",
                  after[0] == before[0] and after[1] == before[1] + 1 and "断开" in (last.error or ""))
            check("流被关闭：任务锁已释放", tm_id not in quiz_router.active_quiz_generations)

            # === 模型返回字段类型错误：逐题判为未通过，不影响合格题 ===
            before = counts()
            bad_shapes = [
                q(stem="类型正常的题"),
                q(stem="选项文本为数字", options=[{"label": l, "text": i} for i, l in enumerate("ABCD")]),
                q(stem=123),
                q(stem="题型为数组", type=["single_choice"]),
                q(stem="难度为数组", difficulty=["medium"]),
                q(stem="解析为对象", explanation={"text": "解析"}),
                q(stem="选项为字符串", options="ABCD"),
            ]
            fake_output["value"] = json.dumps({"questions": bad_shapes, "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 7}, "difficulty_counts": {"medium": 7}})
            fr = frames(r)
            done = next((f for f in fr if f["type"] == "done"), None)
            check("字段类型错误：生成正常结束、无 error 帧",
                  done is not None and not any(f["type"] == "error" for f in fr))
            check("字段类型错误：合格题入库 1 道、其余 6 道逐题未通过",
                  done is not None and len(done["accepted_ids"]) == 1 and len(done["rejected"]) == 6
                  and all(x.get("reasons") for x in done["rejected"]) and counts()[0] == before[0] + 1)

            from question_service import validate_batch as real_validate_batch
            ctx_probe = {"source_refs": {"S1"}, "assets": [], "knowledge_points": ["立体几何"]}
            try:
                acc, rej = real_validate_batch([q(stem={"x": 1}), "不是对象", None], ctx_probe,
                                               {"types": {"single_choice": 3}, "difficulties": {"medium": 3}})
                check("validate_batch 遇到任意结构不抛异常、逐题拒绝", not acc and len(rej) == 3)
            except Exception as exc:  # noqa: BLE001
                check(f"validate_batch 遇到任意结构不抛异常、逐题拒绝（抛出 {type(exc).__name__}）", False)

            # === 生成流内意外异常：发 error 帧、不落题、写失败记录与事件、释放任务锁 ===
            def exploding_validate(*a, **k):
                raise RuntimeError("boom")

            before = counts()
            quiz_router.validate_batch = exploding_validate
            try:
                fake_output["value"] = json.dumps({"questions": [q(stem="校验时出错的题")], "gaps": []}, ensure_ascii=False)
                r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                        "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1}, "difficulty_counts": {"medium": 1}})
                fr = frames(r)
            finally:
                quiz_router.validate_batch = real_validate_batch
            after = counts()
            with SessionLocal() as db:
                last = db.query(QuestionGeneration).order_by(QuestionGeneration.id.desc()).first()
                ev = db.query(QuestionEvent).filter_by(target_type="generation", target_id=last.id).one_or_none()
            check("意外异常：发 error 帧、无 done、不落题",
                  any(f["type"] == "error" for f in fr) and not any(f["type"] == "done" for f in fr) and after[0] == before[0])
            check("意外异常：写失败记录与 generate_failed 事件",
                  after[1] == before[1] + 1 and "生成过程出错" in (last.error or "")
                  and ev is not None and ev.action == "generate_failed")
            check("意外异常：任务锁已释放", tm_id not in quiz_router.active_quiz_generations)

            # === 任务锁：响应体未开始迭代即被丢弃，登记残留到 TTL 后可重新生成 ===
            gen_body = {"research_material_ids": [math_rm_id], "knowledge_points": ["立体几何"],
                        "type_counts": {"single_choice": 1}, "difficulty_counts": {"medium": 1}}
            with SessionLocal() as db:
                fake_output["value"] = json.dumps({"questions": [q(stem="从未开始的流")], "gaps": []}, ensure_ascii=False)
                resp = quiz_router.create_generation(quiz_router.GenerationRequest(**gen_body), StillConnected(), cu, db)
                del resp  # 模拟连接在响应开始前断开：生成器从未运行，finally 不会执行
            check("未开始的流：任务锁仍在登记中", tm_id in quiz_router.active_quiz_generations)
            r = await req("POST", "/generations", json=gen_body)
            check("登记未过期：再次生成 409", r.status_code == 409)
            tok, _ = quiz_router.active_quiz_generations[tm_id]
            quiz_router.active_quiz_generations[tm_id] = (tok, time.monotonic() - quiz_router.GENERATION_LOCK_TTL - 1)
            fake_output["value"] = json.dumps({"questions": [q(stem="残留登记过期后的题")], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json=gen_body)
            done = next((f for f in frames(r) if f["type"] == "done"), None)
            check("登记超过 TTL：可重新生成，结束后释放",
                  done is not None and len(done["accepted_ids"]) == 1 and tm_id not in quiz_router.active_quiz_generations)

            old = quiz_router.acquire_generation(tm_id)
            quiz_router.active_quiz_generations[tm_id] = (old, time.monotonic() - quiz_router.GENERATION_LOCK_TTL - 1)
            new = quiz_router.acquire_generation(tm_id)
            quiz_router.release_generation(tm_id, old)
            check("过期任务释放时不误删新任务的登记",
                  new is not None and new != old and quiz_router.active_quiz_generations.get(tm_id, ("",))[0] == new)
            quiz_router.release_generation(tm_id, new)
            check("新任务自己释放后登记清空", tm_id not in quiz_router.active_quiz_generations)

            # === 并发登记：同一教师 20 个线程同时抢锁，只有一个成功 ===
            barrier = threading.Barrier(20)
            tokens = []

            def contend():
                barrier.wait()
                tokens.append(quiz_router.acquire_generation(999))

            threads = [threading.Thread(target=contend) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            winners = [t for t in tokens if t]
            check("并发登记：20 个线程中恰好 1 个拿到任务锁", len(tokens) == 20 and len(winners) == 1)
            quiz_router.release_generation(999, winners[0] if winners else "")
            check("并发登记：释放后可再次登记", quiz_router.acquire_generation(999) is not None)
            quiz_router.active_quiz_generations.pop(999, None)

            # === 下架 / 恢复：仅原作者，详情返回 can_archive 供界面决定是否显示按钮 ===
            mine = (await req("GET", f"/items/{img_item_id}")).json()
            others = (await req("GET", f"/items/{img_item_id}", "TM2")).json()
            check("作者查看入库题：can_archive 为真", mine.get("can_archive") is True)
            check("同科非作者查看入库题：can_archive 为假", others.get("can_archive") is False)
            r = await req("POST", f"/items/{img_item_id}/archive", "TM2", json={"revision": others["revision"]})
            check("同科非作者下架：服务端仍返回 404", r.status_code == 404)
            fake_output["value"] = json.dumps({"questions": [q(stem="待复核题的下架标记")], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 1}, "difficulty_counts": {"medium": 1}})
            done = next((f for f in frames(r) if f["type"] == "done"), None)
            pend = (await req("GET", f"/items/{done['accepted_ids'][0]}")).json() if done and done["accepted_ids"] else {}
            check("待复核题：can_archive 为假（只有入库题可下架）", pend.get("can_archive") is False)

            # === 每题配图清单：出处资料的配图 + 题面引用的配图，不整批照抄 ===
            def asset(src, name):
                return {"name": f"sources/{src}/{name}", "source_id": src, "source_name": name,
                        "sha256": "0" * 64, "path": f"research/{src}/{name}", "mime": "image/png"}
            batch = {a["name"]: a for a in [asset(1, "a.png"), asset(1, "b.png"), asset(2, "c.png"), asset(2, "d.png")]}
            src1 = [{"ref": "S1", "research_material_id": 1}]
            plain = quiz_router._item_assets(q(stem="不含图"), src1, batch)
            check("每题配图：只列出处所在资料的配图", sorted(a["name"] for a in plain) == ["sources/1/a.png", "sources/1/b.png"])
            used = quiz_router._item_assets(q(stem="如图", explanation="见 ![图](sources/2/c.png)"), src1, batch)
            check("每题配图：另加题面实际引用的他资料配图，不带其余配图",
                  sorted(a["name"] for a in used) == ["sources/1/a.png", "sources/1/b.png", "sources/2/c.png"])
            none = quiz_router._item_assets(q(stem="不含图"), [{"ref": "S1", "research_material_id": 9}], batch)
            check("每题配图：出处资料无配图且题面不引用时为空", none == [])

            # 经接口：同时选纯文字资料与配图资料，每道题的清单都只来自出处资料或题面引用
            fake_output["value"] = json.dumps({"questions": [
                q(stem="两份资料下的纯文字题"), q(stem=f"两份资料下的含图题 ![正方体]({img_ref})")], "gaps": []}, ensure_ascii=False)
            r = await req("POST", "/generations", json={"research_material_ids": [math_rm_id, img_rm_id],
                    "knowledge_points": ["立体几何"], "type_counts": {"single_choice": 2}, "difficulty_counts": {"medium": 2}})
            done = next((f for f in frames(r) if f["type"] == "done"), None)
            stored_ok = done is not None and len(done["accepted_ids"]) == 2
            for qid in (done["accepted_ids"] if done else []):
                it = (await req("GET", f"/items/{qid}")).json()
                cited = {s["research_material_id"] for s in it["sources"]}
                text = it["stem"] + it["explanation"]
                stored_ok &= all(a["source_id"] in cited or a["name"] in text.replace("%20", " ") for a in it["assets"])
                if "含图题" in it["stem"]:
                    stored_ok &= any(a["sha256"] == digest(png) for a in it["assets"])
            check("两份资料生成：每题配图只来自出处资料或题面引用，含图题保留原图", stored_ok)

            # === 学生访问命题接口 403 ===
            r = await req("GET", "/items", "S1")
            check("学生访问题库 403", r.status_code == 403)

            # === 事件 ===
            r = await req("GET", "/events")
            check("本人事件记录非空", r.status_code == 200 and len(r.json()["items"]) > 0)

        print(f"\n结果：{sum(1 for _, ok in checks if ok)}/{len(checks)} 通过")
        failed = [n for n, ok in checks if not ok]
        if failed:
            print("失败项：", failed)
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
