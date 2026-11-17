"""旧评分业务回归的显式消费者驱动，不伪装同步HTTP响应。只用于隔离临时库。"""
from datetime import datetime

from database import SessionLocal
from grading_service import process_task
from models import GradeTask


def complete_tasks(client, response, headers):
    assert response.status_code == 202, response.text
    body = response.json()
    assert not {"graded_count", "failed_count", "score"} & body.keys()
    counts = {"graded_count": 0, "failed_count": 0, "skipped_count": body["skipped_count"]}
    for task_id in body["task_ids"]:
        with SessionLocal() as db:
            task = db.get(GradeTask, task_id)
            state = task.status
            if state == "retrying":
                task.next_attempt_at = datetime(2000, 1, 1)
                db.commit()
        if state == "dead":
            assert client.post(f"/api/teacher/grade-tasks/{task_id}/retry", headers=headers).status_code == 202
        state = process_task(task_id)
        key = "graded_count" if state == "succeeded" else "skipped_count" if state == "skipped" else "failed_count"
        counts[key] += 1
    return counts
