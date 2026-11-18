"""命题作业集成回归：正常/失败/边界；临时库、假模型，不读取真实教学数据。"""
import base64
import copy
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("JWT_SECRET_KEY", "check-only-jwt-secret-not-for-real-use-000000")
os.environ["DEEPSEEK_API_KEY"] = ""
checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    assert passed, name


with tempfile.TemporaryDirectory(prefix="quiz-homework-test-", ignore_cleanup_errors=True) as directory:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory) / 'test.db'}"
    os.environ["UPLOAD_DIR"] = str(Path(directory) / "uploads")
    from fastapi.testclient import TestClient
    import database
    import homework_service as hs
    import quiz_homework_service as publication
    from database import Base, SessionLocal, engine
    from main import app
    from material_service import write_physical_file, resolve_abs_path
    from models import (AuditLog, Class, Homework, HomeworkAsset, HomeworkSubmission, Material, MaterialAsset,
                        MaterialChunk, MistakeNote, QuestionEvent, QuestionPaper, QuestionPaperItem,
                        QuizPublication, Role, User)
    from security import create_access_token

    Base.metadata.create_all(engine)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jV3sAAAAASUVORK5CYII=")
    image_path = "research/math/test/fig 1.png"
    image_name = "sources/1/fig 1.png"
    write_physical_file(png, image_path)
    fixture_asset = {"name": image_name, "path": image_path, "sha256": hashlib.sha256(png).hexdigest(), "mime": "image/png"}
    q1 = {"type": "single_choice", "stem": "计算 $2+2$。 ![图](sources/1/fig%201.png)",
          "options": [{"label": label, "text": str(number)} for label, number in zip("ABCD", [4, 5, 6, 7])],
          "answer": "A", "explanation": "PRIVATE_RUBRIC_TOKEN", "knowledge_points": ["集合"], "sources": [], "assets": [fixture_asset]}
    q2 = {"type": "fill_blank", "stem": "填入指定词和数值：____，____。", "options": [],
          "answer": ["PRIVATE_ANSWER_TOKEN", "6"], "explanation": "PRIVATE_RUBRIC_TOKEN", "knowledge_points": ["集合"], "sources": [], "assets": []}
    with SessionLocal() as db:
        db.add_all([Class(id=i, name=f"班级{i}") for i in (101, 102, 201)])
        people = [("teacher", Role.teacher, "math", "[101,102]", None),
                  ("colleague", Role.teacher, "math", "[101]", None),
                  ("outsider", Role.teacher, "math", "[201]", None),
                  ("physics", Role.teacher, "physics", "[101,102]", None),
                  ("s1", Role.student, None, None, 101), ("s2", Role.student, None, None, 102),
                  ("s3", Role.student, None, None, 101)]
        ids, headers = {}, {}
        for identifier, role, subject, teaching, cid in people:
            user = User(identifier=identifier, role=role, name=identifier, password_hash="unused",
                        subject=subject, teaching_classes=teaching, class_id=cid, must_change_password=False)
            db.add(user)
            db.flush()
            ids[identifier] = user.id
            token = create_access_token(user_id=user.id, role=role.value, class_id=cid,
                                        teaching_classes=json.loads(teaching) if teaching else None,
                                        subject=subject, must_change_password=False)
            headers[identifier] = {"Authorization": "Bearer " + token}
        db.commit()
    def make_paper(title="命题作业测试", count=2, state="final"):
        with SessionLocal() as db:
            paper = QuestionPaper(teacher_id=ids["teacher"], subject="math", title=title,
                                  duration=45, blueprint_json="{}", status=state, revision=1)
            db.add(paper)
            db.flush()
            for index in range(count):
                snapshot = copy.deepcopy([q1, q2][index]) if count == 2 else copy.deepcopy(q1)
                if count != 2:
                    snapshot["stem"] = str(index + 1) + "：" + snapshot["stem"]
                db.add(QuestionPaperItem(paper_id=paper.id, position=index + 1, question_item_id=index + 1,
                                        score=40 if count == 2 else 5, snapshot_json=json.dumps(snapshot, ensure_ascii=False)))
            paper_id = paper.id
            db.commit()
            return paper_id
    paper_id = make_paper()
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {"revision": 1, "reviewed": True, "class_ids": [101, 102], "due_at": due}
    def counts():
        with SessionLocal() as db:
            return tuple(db.query(model).count() for model in (Homework, Material, MaterialAsset, QuizPublication, MaterialChunk))
    with TestClient(app) as client:
        def request(method, path, who="teacher", **kwargs):
            return client.request(method, path, headers=headers[who] if who else {}, **kwargs)
        def publish(pid=paper_id, body=None, who="teacher"):
            return request("POST", f"/api/teacher/quiz/papers/{pid}/publish", who, json=body or payload)
        def teacher_revision(pid):
            return request("GET", f"/api/teacher/quiz/papers/{pid}").json()["revision"]
        def submit(hw_id, answer="按题号作答", who="s1"):
            return request("POST", f"/api/student/homeworks/{hw_id}/submit", who, json={"answer_text": answer})
        from grading_driver import complete_tasks
        def run_grade(hw_id):
            return complete_tasks(client, request("POST", f"/api/teacher/homeworks/{hw_id}/ai-grade"), headers["teacher"])

        def grade(submission_id, score):
            return request("PUT", f"/api/teacher/submissions/{submission_id}/grade", json={"score": score, "feedback": "测试教师评语"})

        # 正常：两个入口、多班发布、公开/私有分离。
        manual = request("POST", "/api/teacher/homeworks", json={"class_id": 101, "title": "手工作业",
                          "content": json.dumps({"stem": "手工题目"}), "due_at": due}).json()["id"]
        check("H/保留手工布置：草稿不可见", request("GET", "/api/student/homeworks", "s1").json() == [])
        request("PUT", f"/api/teacher/homeworks/{manual}/publish")
        before = counts()
        result = publish()
        check("Q/发布到两个任教班级", result.status_code == 200 and len(result.json().get("homework_ids", [])) == 2)
        assignments = {item["class_id"]: item["homework_id"] for item in result.json()["assignments"]}
        h1, h2 = assignments[101], assignments[102]
        check("Q/发布只增加作业而不增加资料切片", counts() == (before[0] + 2, *before[1:]))
        visible = request("GET", "/api/student/homeworks", "s1")
        check("H/两种作业同时展示", {item["source_type"] for item in visible.json()} == {"manual", "quiz"})
        check("H/学生响应不泄露评分依据", all(marker not in visible.text for marker in
              ("PRIVATE_ANSWER_TOKEN", "PRIVATE_RUBRIC_TOKEN", "grading_snapshot", "source_paper_id", image_path)))
        detail = request("GET", f"/api/teacher/homeworks/{h1}").json()
        check("H/教师可读取固定评分依据", detail["grading"]["total_score"] == 80 and
              detail["grading"]["questions"][1]["answer"][0] == "PRIVATE_ANSWER_TOKEN")
        with SessionLocal() as db:
            check("Q/作业发布审计", any(str(h1) in row.detail_json for row in db.query(QuestionEvent).filter_by(action="publish")))
        check("H/学科与班级筛选", {item["id"] for item in request("GET", "/api/student/homeworks", "s2").json()} == {h2}
              and {item["id"] for item in request("GET", "/api/teacher/homeworks?class_id=101").json()} == {manual, h1})

        # 失败：每个新读接口成对检查身份与资源归属。
        for path in (f"/api/teacher/homeworks/{h1}", f"/api/teacher/homeworks/{h1}/assets?name={image_name}",
                     f"/api/student/homeworks/{h1}/assets?name={image_name}"):
            check("H/未登录读取作业或配图：" + path, request("GET", path, None).status_code == 401)
        for who in ("physics", "outsider"):
            for suffix in ("", "/submissions", "/assets?name=" + image_name):
                check("H/教师班级或学科不符：" + who + suffix,
                      request("GET", f"/api/teacher/homeworks/{h1}" + suffix, who).status_code == 404)
        check("H/同科同班教师可评分但源卷保持私有", request("GET", f"/api/teacher/homeworks/{h1}", "colleague").status_code == 200
              and request("GET", f"/api/teacher/quiz/papers/{paper_id}", "colleague").status_code == 404)
        check("H/学生跨班读取或提交", request("GET", f"/api/student/homeworks/{h1}/assets", "s2", params={"name": image_name}).status_code == 404
              and submit(h1, who="s2").status_code == 404)
        check("H/访问他人的提交或教师接口：教师接口", request("GET", f"/api/teacher/homeworks/{h1}", "s1").status_code == 403)
        for who, expected in ((None, 401), ("s1", 403), ("colleague", 404), ("physics", 404)):
            check("Q/发布身份边界：" + str(who), publish(who=who).status_code == expected)
        with SessionLocal() as db:
            check("H/拒绝访问已审计", db.query(AuditLog).filter(AuditLog.status_code.in_((403, 404))).count() >= 7)
        check("H/配图异常：非法名", request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": "../private"}).status_code == 400)
        check("H/配图异常：点路径", request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": "."}).status_code == 400)
        check("H/配图异常：未知名", request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": "missing.png"}).status_code == 404)

        # 边界与发布幂等。
        stable = counts()
        for changes, expected in (({"class_ids": []}, 422), ({"class_ids": list(range(31))}, 422),
                ({"due_at": "2027-01-01T10:00:00"}, 422), ({"due_at": "not-a-time"}, 422),
                ({"due_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}, 400),
                ({"class_ids": [101, 201]}, 403), ({"reviewed": False}, 400)):
            check("Q/发布参数边界或批次混入非任教班级：" + str(changes),
                  publish(body={**payload, **changes}).status_code == expected and counts() == stable)
        without_due = {key: value for key, value in payload.items() if key != "due_at"}
        check("Q/发布参数边界：缺少截止时间", publish(body=without_due).status_code == 422)
        check("Q/草稿试卷发布", publish(make_paper(state="draft")).status_code == 409)
        repeat = publish()
        check("Q/重复发布：原请求旧版本仍复用", repeat.status_code == 200 and repeat.json()["homework_ids"] == [h1, h2]
              and counts() == stable)
        check("Q/重复目标去重", publish(body={**payload, "class_ids": [101, 101]}).json()["homework_ids"] == [h1])
        changed_due = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        check("Q/重复发布更换截止时间或遇到已关闭作业：截止时间冲突",
              publish(body={**payload, "due_at": changed_due}).status_code == 409 and counts() == stable)
        new_paper = make_paper("混合班级测试")
        first = publish(new_paper, {**payload, "class_ids": [101]})
        mixed = publish(new_paper, {**payload, "revision": teacher_revision(new_paper)})
        check("Q/混合已有和新目标班级", mixed.status_code == 200
              and mixed.json()["homework_ids"][0] == first.json()["homework_ids"][0])
        request("PUT", f"/api/teacher/homeworks/{mixed.json()['homework_ids'][0]}/close")
        check("Q/重复发布更换截止时间或遇到已关闭作业：已关闭", publish(new_paper).status_code == 409)
        stale_paper = make_paper("版本冲突")
        with SessionLocal() as db:
            db.get(QuestionPaper, stale_paper).revision = 2
            db.commit()
        check("Q/未确认核对或版本冲突", publish(stale_paper).status_code == 409)
        concurrent_paper = make_paper("并发测试")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(publish, concurrent_paper) for _ in range(2)]
            responses = [future.result() for future in futures]
        check("Q/重复发布：并发唯一", all(response.status_code == 200 for response in responses)
              and responses[0].json()["homework_ids"] == responses[1].json()["homework_ids"])
        thirty = list(range(300, 330))
        with SessionLocal() as db:
            db.add_all([Class(id=cid, name=f"边界班级{cid}") for cid in thirty])
            db.get(User, ids["teacher"]).teaching_classes = json.dumps([101, 102, *thirty])
            db.commit()
        maximum = publish(make_paper("30班边界"), {**payload, "class_ids": thirty, "subject": "physics", "role": "student"})
        check("Q/发布参数边界：30班成功且不信客户端身份", maximum.status_code == 200 and len(maximum.json()["homework_ids"]) == 30)
        with SessionLocal() as db:
            check("Q/服务端学科归属", all(row.subject == "math" for row in db.query(Homework).filter(Homework.id.in_(maximum.json()["homework_ids"]))))
            db.get(User, ids["teacher"]).teaching_classes = "[]"
            db.commit()
        check("Q/撤销任教权限后旧令牌失效", publish().status_code == 403)
        with SessionLocal() as db:
            db.get(User, ids["teacher"]).teaching_classes = "[101,102]"
            db.commit()

        # 批改链路、失败保持、分值折算和并发结果保护。
        submission = submit(h1, "初稿").json()["id"]
        check("H/提交命题作业", request("GET", f"/api/teacher/homeworks/{h1}/submissions").json()[0]["answer_text"] == "初稿")
        repeated_submission = submit(h1, "修改稿").json()["id"]
        check("H/截止前重新提交", repeated_submission == submission
              and len(request("GET", f"/api/teacher/homeworks/{h1}/submissions").json()) == 1)
        check("H/访问他人的提交或教师接口：他人提交", request("GET", f"/api/student/submissions/{submission}", "s3").status_code == 404)
        for who in ("physics", "outsider"):
            check("H/教师班级或学科不符：改分" + who, request("PUT", f"/api/teacher/submissions/{submission}/grade", who,
                  json={"score": 99}).status_code == 404)
            check("H/教师班级或学科不符：初批" + who, request("POST", f"/api/teacher/homeworks/{h1}/ai-grade", who).status_code == 404)
        check("H/教师班级或学科不符：改分学生越权", request("PUT", f"/api/teacher/submissions/{submission}/grade", "s1",
              json={"score": 99}).status_code == 403)
        check("H/教师班级或学科不符：初批学生越权", request("POST", f"/api/teacher/homeworks/{h1}/ai-grade", "s1").status_code == 403)
        for invalid in (-1, 101, True, 0.5):
            check("H/教师评分整数边界：" + str(invalid), request("PUT", f"/api/teacher/submissions/{submission}/grade",
                  json={"score": invalid}).status_code == 422)
        captured = []
        def fake_grade(question, context, **kwargs):
            captured.append(question)
            return json.dumps({"items": [
                {"number": 1, "earned_score": 24, "feedback": "部分正确"},
                {"number": 2, "earned_score": 40, "feedback": "正确"},
            ], "feedback": "作答基本正确"})
        hs.generate_answer = fake_grade
        response = run_grade(h1)
        check("H/AI 使用发布时的评分依据", response["graded_count"] == 1
              and "PRIVATE_ANSWER_TOKEN" in captured[0] and "PRIVATE_RUBRIC_TOKEN" in captured[0])
        check("H/非百分制原卷折算", request("GET", f"/api/teacher/homeworks/{h1}/submissions").json()[0]["ai_score"] == 80)
        ai_record = next(row for row in request("GET", f"/api/teacher/homeworks/{h1}/submissions").json() if row["id"] == submission)
        not_final = request("GET", f"/api/student/submissions/{submission}", "s1").json()
        check("逐题 AI 建议持久化，未确认时学生看不到逐题终评",
              [row["earned_score"] for row in ai_record["ai_item_results"]] == [24, 40]
              and not_final["item_results"] is None)
        for raw, expected in ((0, 0), (0.4, 1), (80, 100)):
            check("H/分数折算边界：" + str(raw), hs.quiz_percentage_score(raw, 80) == expected)
        for invalid in (-1, 81, True, "64", float("nan"), float("inf")):
            try:
                hs.quiz_percentage_score(invalid, 80)
                rejected = False
            except ValueError:
                rejected = True
            check("H/分数折算边界：拒绝" + str(invalid), rejected)
        grade(submission, 85)
        repeated_grade = run_grade(h1)
        check("H/教师覆盖 AI 分且后续初批跳过", repeated_grade["graded_count"] == 0
              and request("GET", f"/api/student/submissions/{submission}", "s1").json()["final_score"] == 85)
        other_sub = submit(h1, "错误答案", "s3").json()["id"]
        for invalid in (None, "invalid-json", '{"earned_score":999}', '{"earned_score":true}'):
            hs.generate_answer = lambda *a, _value=invalid, **kw: _value
            fail = run_grade(h1)
            with SessionLocal() as db:
                actual = db.get(HomeworkSubmission, other_sub)
                check("H/初批失败仍可人工改分：" + str(invalid), fail["failed_count"] == 1
                      and actual.status == "pending" and actual.ai_score is None)
        grade(other_sub, 55)
        with SessionLocal() as db:
            note = db.query(MistakeNote).filter_by(student_id=ids["s3"], homework_id=h1).one()
            check("H/教师直接评分并联动错题学情", note.student_answer == "错误答案"
                  and request("GET", "/api/student/analytics/overview", "s3").json()["accuracy"] == 55)
        check("H/手工作业仍可人工评分", grade(submit(manual).json()["id"], 90).status_code == 200)
        three = make_paper("三题逐题批改", count=3)
        three_hw = publish(three).json()["homework_ids"][0]
        graded_id = submit(three_hw, "1.B 2.B 3.1/2").json()["id"]
        version = request("GET", f"/api/teacher/homeworks/{three_hw}/submissions").json()[0]["submission_version"]
        grade_path = f"/api/teacher/submissions/{graded_id}/grade"
        items = [
            {"number": 1, "earned_score": 0, "feedback": "核对垂直条件"},
            {"number": 2, "earned_score": 5, "feedback": ""},
            {"number": 3, "earned_score": 5, "feedback": ""},
        ]
        item_payload = {"item_results": items, "submission_version": version, "feedback": "请复习第一题"}
        for label, invalid_items in (
            ("缺题", items[:-1]),
            ("重号", [items[0], items[0], items[2]]),
            ("未知题号", [{**items[0], "number": 4}, *items[1:]]),
            ("越界", [{**items[0], "earned_score": 6}, *items[1:]]),
        ):
            rejected = request("PUT", grade_path, json={**item_payload, "item_results": invalid_items})
            check("逐题终评拒绝" + label, rejected.status_code == 400)
        check("逐题终评沿用班级与学科授权",
              all(request("PUT", grade_path, who, json=item_payload).status_code == 404 for who in ("outsider", "physics")))
        check("拒绝后不保存任何成绩",
              request("GET", f"/api/student/submissions/{graded_id}", "s1").json()["final_score"] is None)
        from sqlalchemy import event
        from sqlalchemy.exc import SQLAlchemyError

        def fail_mistake_insert(conn, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO mistake_notes"):
                raise SQLAlchemyError("合成错题写入失败")

        event.listen(engine, "before_cursor_execute", fail_mistake_insert)
        try:
            failed_save = request("PUT", grade_path, json=item_payload)
        finally:
            event.remove(engine, "before_cursor_execute", fail_mistake_insert)
        check("错题写入失败时逐题终评和总分同事务回滚",
              failed_save.status_code == 503
              and request("GET", f"/api/student/submissions/{graded_id}", "s1").json()["final_score"] is None)
        confirmed = request("PUT", grade_path, json=item_payload)
        repeated = request("PUT", grade_path, json=item_payload)
        detail_after = request("GET", f"/api/student/submissions/{graded_id}", "s1").json()
        own_work = next(row for row in request("GET", "/api/student/homeworks", "s1").json() if row["id"] == three_hw)
        check("教师确认0、5、5折算67且学生列表和详情逐题一致",
              confirmed.status_code == 200 and repeated.status_code == 200
              and detail_after["final_score"] == 67 and detail_after["item_results"] == own_work["item_results"]
              and [item["earned_score"] for item in own_work["item_results"]] == [0, 5, 5])
        check("其他学生无法读取逐题成绩，学生响应不含私有答案",
              request("GET", f"/api/student/submissions/{graded_id}", "s2").status_code == 404
              and "PRIVATE_ANSWER_TOKEN" not in json.dumps(own_work))

        def three_mistakes():
            notes = request("GET", "/api/student/mistakes", "s1").json()
            return [note for note in notes if note["homework_id"] == three_hw]

        notes = three_mistakes()
        check("及格试卷只收录第一题，重复确认不重复，旧整份清理忽略逐题记录",
              len(notes) == 1 and notes[0]["question_number"] == 1 and notes[0]["reason"] == "核对垂直条件"
              and "PRIVATE_ANSWER_TOKEN" not in notes[0]["question_stem"])
        with SessionLocal() as db:
            db.get(MistakeNote, notes[0]["id"]).student_answer = "1.B 2.B 3.1/2"
            db.commit()
        check("旧错题的整份文本只取对应题号，历史仍保留原文",
              three_mistakes()[0]["student_answer"] == "B" and detail_after["answer_text"] == "1.B 2.B 3.1/2"
              and [item["answer_text"] for item in own_work["item_answers"]] == ["B", "B", "1/2"])
        with SessionLocal() as db:
            check("旧整份错题清理不会误删及格试卷的逐题错题",
                  all(note.homework_id != three_hw for note in hs.resolved_homework_mistakes(db)))
        full = [{**items[0], "earned_score": 5}, *items[1:]]
        check("第1题改成满分后移除错题",
              request("PUT", grade_path, json={**item_payload, "item_results": full}).json()["teacher_score"] == 100
              and three_mistakes() == [])
        check("学生重交后旧页面逐题终评被拒",
              submit(three_hw, "订正后的答案").status_code == 200
              and request("PUT", grade_path, json=item_payload).status_code == 409
              and request("GET", f"/api/student/submissions/{graded_id}", "s1").json()["item_results"] is None)
        check("旧作答题号不明确时保留原文，不猜测对应题",
              request("GET", f"/api/student/submissions/{graded_id}", "s1").json()["item_answers"] is None
              and request("GET", f"/api/student/submissions/{graded_id}", "s1").json()["answer_text"] == "订正后的答案")

        submit_path = f"/api/student/homeworks/{three_hw}/submit"
        read_path = f"/api/student/submissions/{graded_id}"
        teacher_path = f"/api/teacher/homeworks/{three_hw}/submissions"
        answers = [{"number": 1, "answer_text": "第一题答案\n第二行"},
                   {"number": 2, "answer_text": ""}, {"number": 3, "answer_text": "C"}]
        receipt = request("POST", submit_path, "s1", json={"item_answers": answers[::-1]})
        check("提交并读取逐题作答", receipt.status_code == 200 and receipt.json()["id"] == graded_id
              and request("GET", read_path, "s1").json()["item_answers"] == answers
              and request("GET", teacher_path).json()[0]["item_answers"] == answers)
        student_homework = next(row for row in request("GET", "/api/student/homeworks", "s1").json() if row["id"] == three_hw)
        with SessionLocal() as db:
            check("学生历史显示冻结题号与数据库保存的答案",
                  student_homework["question_numbers"] == [1, 2, 3] and student_homework["item_answers"] == answers
                  and json.loads(db.get(HomeworkSubmission, graded_id).item_answers_json) == answers)
        for label, malformed in (
            ("漏题", answers[:2]), ("重号", [answers[0], answers[0], answers[2]]),
            ("错误题号", [*answers[:2], {"number": 5, "answer_text": "D"}]),
            ("全部空白", [{"number": i, "answer_text": " "} for i in range(1, 4)]),
        ):
            check("拒绝逐题提交：" + label,
                  request("POST", submit_path, "s1", json={"item_answers": malformed}).status_code == 400)
        check("逐题作答沿用认证、班级和本人隔离",
              request("POST", submit_path, None, json={"item_answers": answers}).status_code == 401
              and request("POST", submit_path, "s2", json={"item_answers": answers}).status_code == 404
              and request("GET", read_path, "s3").status_code == 404
              and request("GET", read_path, "s1").json()["item_answers"] == answers)

        model_answers = []
        def model_for_items(question, *args, **kwargs):
            model_answers.append(json.loads(question)["student_answer"])
            return json.dumps({"items": [{**item, "earned_score": 0} if item["number"] == 2 else item
                                         for item in items]})
        hs.generate_answer = model_for_items
        check("初批冻结逐题作答，保留未答题", run_grade(three_hw)["graded_count"] == 1 and model_answers == [answers])
        version = request("GET", teacher_path).json()[0]["submission_version"]
        two_wrong = [items[0], {**items[1], "earned_score": 0}, items[2]]
        result = request("PUT", grade_path, json={"submission_version": version, "item_results": two_wrong})
        saved_notes = {note["question_number"]: note for note in three_mistakes()}
        check("按题查看错题作答及未作答状态", result.status_code == 200 and set(saved_notes) == {1, 2}
              and saved_notes[1]["student_answer"] == answers[0]["answer_text"] and saved_notes[2]["student_answer"] == "")
        import mistake_service
        explanation_inputs = []
        saved_generate = mistake_service.generate_answer
        def explain_with_fixture(question, *_args, **_kwargs):
            explanation_inputs.append(question)
            return "合成讲解"
        mistake_service.generate_answer = explain_with_fixture
        try:
            explanation = request("POST", f"/api/student/mistakes/{saved_notes[1]['id']}/explain", "s1")
        finally:
            mistake_service.generate_answer = saved_generate
        check("错题讲解只输入当前题作答", explanation.status_code == 200 and len(explanation_inputs) == 1
              and explanation_inputs[0].split("学生作答：", 1)[1].split("\n教师评语", 1)[0] == answers[0]["answer_text"])
        twelve = make_paper("12题排版", count=12)
        twelve_hw = publish(twelve).json()["homework_ids"][0]
        twelve_text = request("GET", f"/api/teacher/homeworks/{twelve_hw}").json()["content"]["stem"]
        check("H/题面显示一致", "10." in twelve_text and "12." in twelve_text and "A. 4" in twelve_text and "____" in detail["content"]["stem"])
        moving = submit(twelve_hw).json()["id"]
        def resubmit_during_grade(*args, **kwargs):
            with SessionLocal() as db:
                sub = db.get(HomeworkSubmission, moving)
                sub.answer_text = "新答案"
                sub.submitted_at = datetime.now(timezone.utc)
                db.commit()
            return json.dumps({"items": [{"number": i, "earned_score": 2.5} for i in range(1, 13)], "feedback": "旧结果"})
        hs.generate_answer = resubmit_during_grade
        check("H/初批期间提交被更新或教师改分：重交", run_grade(twelve_hw)["skipped_count"] == 1)
        def teacher_during_grade(*args, **kwargs):
            with SessionLocal() as db:
                sub = db.get(HomeworkSubmission, moving)
                sub.status, sub.teacher_score = "teacher_graded", 91
                db.commit()
            return json.dumps({"items": [{"number": i, "earned_score": 2.5} for i in range(1, 13)], "feedback": "旧结果"})
        hs.generate_answer = teacher_during_grade
        check("H/初批期间提交被更新或教师改分：教师终评", run_grade(twelve_hw)["skipped_count"] == 1
              and request("GET", f"/api/student/submissions/{moving}", "s1").json()["final_score"] == 91)

        # 整批回滚：文件与数据库中途失败均不留下第一班作业。
        failing = make_paper("文件失败")
        original_write = publication.write_physical_file
        calls = []
        before_failure = counts()
        before_directories = set(Path(os.environ["UPLOAD_DIR"]).rglob("homework-*"))
        def fail_second_file(content, path):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("PRIVATE_PATH_SHOULD_NOT_LEAK")
            return original_write(content, path)
        publication.write_physical_file = fail_second_file
        try:
            failure = publish(failing)
        finally:
            publication.write_physical_file = original_write
        check("Q/原图校验或文件写入失败：文件整批回滚", failure.status_code == 500 and counts() == before_failure
              and "PRIVATE_PATH" not in failure.text and set(Path(os.environ["UPLOAD_DIR"]).rglob("homework-*")) == before_directories)
        from sqlalchemy import event
        from sqlalchemy.orm import Session
        failing_db = make_paper("数据库失败")
        def fail_second_row(session, *args):
            if any(isinstance(row, Homework) and row.source_paper_id == failing_db and row.class_id == 102 for row in session.new):
                raise RuntimeError("PRIVATE_SQL_SHOULD_NOT_LEAK")
        event.listen(Session, "before_flush", fail_second_row)
        try:
            failure = publish(failing_db)
        finally:
            event.remove(Session, "before_flush", fail_second_row)
        check("Q/原图校验或文件写入失败：数据库整批回滚", failure.status_code == 500 and counts() == before_failure
              and "PRIVATE_SQL" not in failure.text and set(Path(os.environ["UPLOAD_DIR"]).rglob("homework-*")) == before_directories)

        # 历史资料夹具，与新发布路径独立，明确保留旧内容/图片读取断言。
        legacy_bytes = "# 历史试卷\n\n填空____，____。\n\n![图](legacy.png)\n".encode()
        write_physical_file(legacy_bytes, "101/legacy/paper.md")
        write_physical_file(png, "101/legacy/legacy.png")
        with SessionLocal() as db:
            legacy = Material(class_id=101, uploader_id=ids["teacher"], filename="历史试卷.md",
                file_path="101/legacy/paper.md", file_type="text/markdown", file_size=len(legacy_bytes),
                tags=json.dumps(["数学", "试卷", "学生版"]), description="历史数学试卷", is_indexed=False)
            db.add(legacy)
            db.flush()
            legacy_id = legacy.id
            db.add(MaterialAsset(material_id=legacy_id, name="legacy.png", file_path="101/legacy/legacy.png",
                                 sha256=hashlib.sha256(png).hexdigest(), file_type="image/png"))
            db.add(QuizPublication(paper_id=paper_id, class_id=101, material_id=legacy_id,
                                   content_sha256=hashlib.sha256(legacy_bytes).hexdigest()))
            db.commit()
        check("H/更新后旧资料仍可访问", request("GET", f"/api/materials/{legacy_id}/download", "s1").content == legacy_bytes
              and request("GET", f"/api/materials/{legacy_id}/assets", "s1", params={"name": "legacy.png"}).content == png)
        with SessionLocal() as db:
            old_material = db.get(Material, legacy_id)
            check("H/历史资料标签索引及发布记录保留", not old_material.is_indexed and "试卷" in json.loads(old_material.tags)
                  and db.query(QuizPublication).filter_by(material_id=legacy_id).count() == 1)
        check("Q/已发布资料不被改写", request("GET", f"/api/materials/{legacy_id}/preview", "s1").content == legacy_bytes
              and b"PRIVATE_RUBRIC" not in legacy_bytes)
        legacy_source = make_paper("历史定稿卷再次布置")
        old_counts = counts()
        republished = publish(legacy_source)
        check("H/老试卷主动重新发布", republished.status_code == 200 and counts() == (old_counts[0] + 2, *old_counts[1:]))
        for suffix in ("/download", "/assets?name=legacy.png"):
            check("H/历史资料未登录与跨班隔离：" + suffix,
                  request("GET", f"/api/materials/{legacy_id}" + suffix, None).status_code == 401
                  and request("GET", f"/api/materials/{legacy_id}" + suffix, "s2").status_code == 404)
        with SessionLocal() as db:
            asset = db.query(HomeworkAsset).filter_by(homework_id=h1).one()
            copied_path = asset.file_path
        valid_image = request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": image_name})
        check("H/学生配图字节与原图一致", valid_image.status_code == 200 and valid_image.content == png)
        write_physical_file(b"tampered", copied_path)
        corrupt = request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": image_name})
        check("H/配图异常：指纹变化", corrupt.status_code == 409 and directory not in corrupt.text)
        write_physical_file(png, copied_path)
        broken_source = make_paper("原图变化")
        write_physical_file(b"changed-source", image_path)
        check("Q/原图校验或文件写入失败：指纹", publish(broken_source).status_code == 409)
        resolve_abs_path(image_path).unlink()
        check("Q/原图校验或文件写入失败：缺失", publish(broken_source).status_code == 409)
        frozen = request("GET", f"/api/teacher/homeworks/{h1}").json()
        check("H/原题和原资料后续变化", frozen["content"] == detail["content"] and frozen["grading"] == detail["grading"]
              and request("GET", f"/api/student/homeworks/{h1}/assets", "s1", params={"name": image_name}).content == png)
        with SessionLocal() as db:
            db.get(Homework, h1).due_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
        old_answer = request("GET", f"/api/student/submissions/{submission}", "s1").json()["answer_text"]
        check("H/逾期或关闭后提交：逾期", submit(h1, "不能覆盖").status_code == 400
              and request("GET", f"/api/student/submissions/{submission}", "s1").json()["answer_text"] == old_answer)
        request("PUT", f"/api/teacher/homeworks/{h2}/close")
        check("H/逾期或关闭后提交：关闭", submit(h2, who="s2").status_code == 400)
        check("H/不存在作业详情", request("GET", "/api/teacher/homeworks/999999").status_code == 404)

    # 旧格式临时数据库：保留用户、历史资料和真实形状的旧作业/成绩，连续迁移两次。
    from sqlalchemy import create_engine
    old_path = Path(directory) / "old-format.db"
    src = sqlite3.connect(Path(directory) / "test.db")
    old = sqlite3.connect(old_path)
    src.backup(old)
    src.close()
    legacy_columns = "id,class_id,subject,teacher_id,title,content_json,due_at,status,created_at,updated_at"
    legacy_rows = old.execute("SELECT " + legacy_columns + " FROM homeworks").fetchall()
    scores_before = old.execute("SELECT id,answer_text,teacher_score,ai_score FROM homework_submissions ORDER BY id").fetchall()
    accounts_before = old.execute("SELECT id,identifier,password_hash FROM users ORDER BY id").fetchall()
    material_before = old.execute("SELECT id,file_path,filename FROM materials ORDER BY id").fetchall()
    old.execute("DROP INDEX uq_mistake_note_homework_question")
    old.execute("ALTER TABLE mistake_notes DROP COLUMN question_number")
    old.execute("ALTER TABLE homework_submissions DROP COLUMN ai_item_results_json")
    old.execute("ALTER TABLE homework_submissions DROP COLUMN teacher_item_results_json")
    old.execute("ALTER TABLE homework_submissions DROP COLUMN item_answers_json")
    old.execute("DROP TABLE homework_assets")
    old.execute("DROP TABLE homeworks")
    old.execute("CREATE TABLE homeworks(id INTEGER PRIMARY KEY,class_id INTEGER NOT NULL,subject TEXT NOT NULL,"
                "teacher_id INTEGER NOT NULL,title TEXT NOT NULL,content_json TEXT NOT NULL,due_at DATETIME NOT NULL,"
                "status TEXT NOT NULL,created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL)")
    old.executemany("INSERT INTO homeworks VALUES(?,?,?,?,?,?,?,?,?,?)", legacy_rows)
    old.commit()
    old.close()
    original_engine = database.engine
    old_engine = create_engine("sqlite:///" + str(old_path))
    database.engine = old_engine
    try:
        database.run_simple_migrations()
        Base.metadata.create_all(old_engine)
        database.run_simple_migrations()
    finally:
        database.engine = original_engine
        old_engine.dispose()
    with sqlite3.connect(old_path) as migrated:
        check("H/迁移重复执行", migrated.execute("SELECT " + legacy_columns + " FROM homeworks ORDER BY id").fetchall() == sorted(legacy_rows)
              and migrated.execute("SELECT id,answer_text,teacher_score,ai_score FROM homework_submissions ORDER BY id").fetchall() == scores_before
              and migrated.execute("SELECT id,identifier,password_hash FROM users ORDER BY id").fetchall() == accounts_before
              and migrated.execute("SELECT id,file_path,filename FROM materials ORDER BY id").fetchall() == material_before
              and migrated.execute("SELECT COUNT(*) FROM homework_submissions WHERE ai_item_results_json IS NOT NULL OR teacher_item_results_json IS NOT NULL").fetchone()[0] == 0
              and migrated.execute("SELECT COUNT(*) FROM homework_submissions WHERE item_answers_json IS NOT NULL").fetchone()[0] == 0
              and migrated.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='uq_mistake_note_homework_question'").fetchone()[0] == 1
              and migrated.execute("SELECT COUNT(*) FROM homeworks WHERE source_type<>'manual'").fetchone()[0] == 0)
    engine.dispose()

print(json.dumps({"passed": len(checks), "failed": 0, "checks": [name for name, _ in checks]}, ensure_ascii=False))
