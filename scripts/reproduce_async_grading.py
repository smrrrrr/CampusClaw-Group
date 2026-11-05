"""一键真实RabbitMQ复现：独立Compose项目、临时库、合成账号、假模型，无教学数据/真实额度。

根目录执行：backend/.venv/Scripts/python.exe scripts/reproduce_async_grading.py
已有本次代码镜像可加 --image campusclaw-async-backend:local --skip-build。
退出时只清理本脚本随机命名的Compose项目，不操作现有部署。
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BROKER_IMAGE = "rabbitmq:4.2-management@sha256:4e1c1636957aa13c2dbeb8c92606891ac0c396999bb4d7c3a7e3ba38430df7fa"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="campusclaw-async-backend:local")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--output-prefix", default="", help="归档文件名前缀，仅小写英文、数字和短横线")
    args = parser.parse_args()
    assert re.fullmatch(r"[a-z0-9-]*", args.output_prefix)
    project = "cc-async-check-" + uuid.uuid4().hex[:10]
    assert re.fullmatch(r"cc-async-check-[a-f0-9]{10}", project)
    work = ROOT / ".review" / project
    work.mkdir(parents=True)
    data = work / "data"; data.mkdir()
    evidence = ROOT / "reports" / "async-grading"; evidence.mkdir(parents=True, exist_ok=True)
    results = {"started_at": datetime.now(timezone.utc).isoformat(), "project": project,
               "image": args.image, "model": "local synthetic HTTP model; no real provider calls",
               "database": "new empty temporary SQLite", "commands": [], "checks": [], "metrics": {}}
    password = secrets.token_urlsafe(32)
    env = {"DATABASE_URL": "sqlite:////data/test.db", "UPLOAD_DIR": "/data/uploads", "PYTHONPATH": "/app",
           "SQLITE_JOURNAL_MODE": "DELETE", "JWT_SECRET_KEY": secrets.token_urlsafe(48),
           "DEEPSEEK_API_KEY": "synthetic-model-key", "DEEPSEEK_BASE_URL": "http://model:9000/v1",
           "DEEPSEEK_MODEL": "synthetic-model", "DEEPSEEK_TIMEOUT": "3", "MCP_TOOLS_HEALTH_URL": "",
           "GRADING_BROKER_HOST": "broker", "GRADING_BROKER_USER": "synthetic", "GRADING_BROKER_PASSWORD": password,
           "GRADING_LEASE_SECONDS": "9", "GRADING_RETRY_BASE_SECONDS": "0.2",
           "GRADING_POLL_SECONDS": "0.1"}
    common = {"image": args.image, "environment": env, "volumes": [f"{data.as_posix()}:/data",
              f"{(ROOT / 'apitest').as_posix()}:/fixtures:ro"], "stop_grace_period": "10s"}
    config = {"services": {
        "broker": {"image": BROKER_IMAGE, "hostname": "grading-broker", "environment": {
            "RABBITMQ_DEFAULT_USER": "synthetic", "RABBITMQ_DEFAULT_PASS": password},
            "volumes": ["broker-data:/var/lib/rabbitmq"]},
        "model": {"image": args.image, "volumes": [f"{(ROOT / 'apitest').as_posix()}:/fixtures:ro"],
                  "ports": ["127.0.0.1::9000"], "command": ["/app/.venv/bin/python", "/fixtures/async_fake_model.py"]},
        "api": {**common, "ports": ["127.0.0.1::8000"],
                "command": ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]},
        "dispatcher": {**common, "command": ["/app/.venv/bin/python", "grading_worker.py", "--mode", "dispatch"]},
        "worker": {**common, "command": ["/app/.venv/bin/python", "grading_worker.py", "--mode", "consume"]},
    }, "volumes": {"broker-data": {}}}
    compose_file = work / "compose.json"
    compose_file.write_text(json.dumps(config), encoding="utf-8")
    prefix = ["docker", "compose", "-p", project, "-f", str(compose_file)]

    def command(tail, *, compose=True):
        cmd = (prefix if compose else []) + tail
        # 命令不含密码/令牌；生成的私有配置文件不归档。
        results["commands"].append(("docker compose -p " + project + " -f <private-generated-compose> " + " ".join(tail))
                                   if compose else " ".join(tail))
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode:
            raise RuntimeError(f"Command failed ({proc.returncode}): {tail[:3]}: {proc.stderr[-1600:]}")
        return proc.stdout.strip()

    def wait_until(predicate, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value: return value
            except (httpx.HTTPError, ValueError, KeyError, RuntimeError):
                pass
            time.sleep(.2)
        raise AssertionError("等待隔离环境条件超时")

    def check(name, condition, observed):
        results["checks"].append({"name": name, "passed": bool(condition), "observed": observed})
        assert condition, name
        print("PASS " + name, flush=True)

    try:
        if not args.skip_build:
            command(["docker", "build", "-t", args.image, "./backend"], compose=False)
        critical = ["grading_service.py", "grading_worker.py", "grading_queue.py", "homework_service.py", "models.py", "config.py", "routers/homework.py"]
        expected = {n: hashlib.sha256((ROOT / "backend" / n).read_bytes()).hexdigest() for n in critical}
        probe = "import hashlib,json;from pathlib import Path;print(json.dumps({n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in " + repr(critical) + "}))"
        actual = json.loads(command(["docker", "run", "--rm", args.image, "/app/.venv/bin/python", "-c", probe], compose=False))
        assert actual == expected, "测试镜像与当前代码不同，请去掉--skip-build重新构建"
        results["verified_image_source_sha256"] = actual
        results["image_id"] = command(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"], compose=False)
        command(["up", "-d", "broker", "model"])
        results["broker_digest"] = command(["docker", "image", "inspect", BROKER_IMAGE, "--format", "{{json .RepoDigests}}"], compose=False)
        wait_until(lambda: command(["exec", "--user", "rabbitmq", "-T", "broker", "rabbitmq-diagnostics", "-q", "ping"]), timeout=120)
        seeded = command(["run", "--rm", "--no-deps", "api", "/app/.venv/bin/python", "/fixtures/async_fixture.py"])
        fixtures = json.loads(seeded.splitlines()[-1])
        command(["up", "-d", "api", "dispatcher"])
        api_address = "http://" + command(["port", "api", "8000"]).splitlines()[0]
        model_address = "http://" + command(["port", "model", "9000"]).splitlines()[0]
        client = httpx.Client(base_url=api_address, timeout=20, trust_env=False)
        wait_until(lambda: client.get("/api/health").status_code == 200)
        login = client.post("/api/auth/login", json={"identifier": "async-teacher", "password": "Check-only-password123!"})
        assert login.status_code == 200, f"合成账号登录失败HTTP {login.status_code}"
        client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        model = httpx.Client(base_url=model_address, timeout=10, trust_env=False)
        started = time.perf_counter()
        assert model.post("/v1/chat/completions", json={"messages": []}).status_code == 200
        model_duration = time.perf_counter() - started

        def enqueue(name):
            response = client.post(f"/api/teacher/homeworks/{fixtures[name]['homework_id']}/ai-grade")
            assert response.status_code == 202
            body = response.json(); assert "score" not in body and "graded_count" not in body
            return body
        def task(tid):
            response = client.get(f"/api/teacher/grade-tasks/{tid}"); assert response.status_code == 200
            return response.json()
        def state(tid, wanted):
            info = task(tid)
            return info if info["status"] == wanted else None
        def subs(name):
            response = client.get(f"/api/teacher/homeworks/{fixtures[name]['homework_id']}/submissions")
            assert response.status_code == 200
            return response.json()
        def queue_counts():
            output = command(["exec", "-T", "api", "/app/.venv/bin/python", "-c",
                              "import json;from grading_queue import GradingQueue;q=GradingQueue();print(json.dumps(q.counts()));q.close()"])
            return json.loads(output.splitlines()[-1])

        times, batches = [], []
        for _ in range(20):
            started = time.perf_counter(); batches.append(enqueue("bulk")); times.append(time.perf_counter() - started)
        p95 = sorted(times)[18]
        results["metrics"]["submission_seconds"] = times
        results["metrics"]["p95_seconds"] = p95
        results["metrics"]["synthetic_execution_seconds"] = model_duration
        bulk_ids = batches[0]["task_ids"]
        check("A1 请求不等待执行", p95 < model_duration and len(bulk_ids) == 20
              and all(b["task_ids"] == bulk_ids for b in batches), {"requests": 20, "p95": p95, "fake_model": model_duration})
        wait_until(lambda: queue_counts()["ready"] >= 20)
        results["metrics"]["queue_before_consumer"] = queue_counts()
        check("B1 消费者停止期间任务保留", all(task(t)["status"] == "pending" for t in bulk_ids)
              and all(s["ai_score"] is None for s in subs("bulk")), {"pending": len(bulk_ids)})
        before_pause = queue_counts()
        time.sleep(32)
        after_pause = queue_counts()
        check("Q1 停止32秒队列长度不增长", before_pause["ready"] == after_pause["ready"] == 20,
              {"paused_seconds": 32, "before": before_pause, "after": after_pause})
        command(["up", "-d", "--force-recreate", "broker"])
        wait_until(lambda: queue_counts()["ready"] >= 20, timeout=120)
        check("B1 代理容器重建后持久消息仍在", all(task(t)["status"] == "pending" for t in bulk_ids), queue_counts())
        command(["up", "-d", "worker"])
        wait_until(lambda: all(state(t, "succeeded") for t in bulk_ids))
        check("B1 启动消费者无需重交自动完成", all(s["ai_score"] == 70 for s in subs("bulk")), {"succeeded": len(bulk_ids)})

        command(["stop", "worker"])
        with ThreadPoolExecutor(max_workers=20) as pool:
            duplicate_batches = list(pool.map(lambda _: enqueue("duplicate"), range(20)))
        duplicate_id = duplicate_batches[0]["task_ids"][0]
        check("C1 同一提交20并发只创建一个任务", all(b["task_ids"] == [duplicate_id] for b in duplicate_batches)
              and sum(b["created_count"] for b in duplicate_batches) == 1, {"requests": 20, "task_id": duplicate_id})
        command(["start", "worker"])
        completed = wait_until(lambda: state(duplicate_id, "succeeded"))
        previous = subs("duplicate")[0]
        command(["exec", "-T", "api", "/app/.venv/bin/python", "-c",
                 f"from grading_queue import GradingQueue;q=GradingQueue();q.publish({duplicate_id});q.close()"])
        wait_until(lambda: task(duplicate_id)["attempts"] > completed["attempts"])
        after = subs("duplicate")[0]
        check("C1 重复投递不重复生效", previous["ai_score"] == after["ai_score"] == 70
              and previous == after, {"attempts_before": completed["attempts"], "attempts_after": task(duplicate_id)["attempts"], "score": after["ai_score"]})

        crash_id = enqueue("crash")["task_ids"][0]
        wait_until(lambda: state(crash_id, "running"))
        command(["kill", "-s", "SIGKILL", "worker"])
        check("B4 杀进程后任务仍在", task(crash_id)["status"] == "running"
              and subs("crash")[0]["ai_score"] is None, {"task_id": crash_id})
        command(["start", "worker"])
        recovered = wait_until(lambda: state(crash_id, "succeeded"))
        check("B4 租约到期后自动重投恢复", recovered["attempts"] >= 2 and subs("crash")[0]["ai_score"] == 70,
              {"attempts": recovered["attempts"], "execution_count": recovered["execution_count"]})

        command(["stop", "broker"])
        outage_id = enqueue("outage")["task_ids"][0]
        check("B2 代理停止仍持久接收", task(outage_id)["status"] == "pending", {"task_id": outage_id})
        command(["start", "broker"])
        wait_until(lambda: state(outage_id, "succeeded"), timeout=120)
        check("B2 代理恢复后自动补投", subs("outage")[0]["ai_score"] == 70, {"status": "succeeded"})

        failed_id = enqueue("failure")["task_ids"][0]
        failed = wait_until(lambda: state(failed_id, "dead"))
        wait_until(lambda: queue_counts()["dead"] >= 1)
        results["metrics"]["queue_with_dead_letter"] = queue_counts()
        check("D1 三次失败进入持久死信", failed["execution_count"] == 3 and failed["error"]
              and subs("failure")[0]["ai_score"] is None, {"attempts": failed["attempts"], "execution_count": failed["execution_count"], "error": failed["error"]})
        model.post("/control", json={"fail_enabled": False}).raise_for_status()
        assert client.post(f"/api/teacher/grade-tasks/{failed_id}/retry").status_code == 202
        retried = wait_until(lambda: state(failed_id, "succeeded"))
        check("D2 人工重新排队后恢复", retried["attempts"] > failed["attempts"] and subs("failure")[0]["ai_score"] == 70,
              {"attempts": retried["attempts"], "execution_count": retried["execution_count"]})
        infos = [task(t) for t in bulk_ids] + [task(t) for t in (duplicate_id, crash_id, outage_id, failed_id)]
        results["metrics"]["tasks"] = infos
        results["metrics"]["consumption_seconds"] = [
            (datetime.fromisoformat(t["finished_at"]) - datetime.fromisoformat(t["started_at"])).total_seconds()
            for t in infos if t["finished_at"] and t["started_at"]]
        results["metrics"]["queue_final"] = queue_counts()
        results["metrics"]["synthetic_model_calls"] = model.get("/").json()["calls"]
        output = command(["logs", "--no-color", "--no-log-prefix", "worker"])
        assert password not in output and env["JWT_SECRET_KEY"] not in output and "SLOW_ME" not in output and "FAIL_ME" not in output
        events = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        task_events = [event for event in events if "task_id" in event]
        check("F1 任务日志为JSON且关联原请求", bool(task_events) and all(event.get("request_id") for event in task_events),
              {"task_events": len(task_events), "secret_or_answer_leak": False})
        (evidence / (args.output_prefix + "worker-events.json")).write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
        client.close(); model.close()
        results["status"] = "PASS"
    except Exception as exc:
        results["status"], results["failure"] = "FAIL", str(exc)
        raise
    finally:
        results["finished_at"] = datetime.now(timezone.utc).isoformat()
        results["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / "backend" / n for n in ("grading_service.py", "grading_worker.py", "grading_queue.py", "homework_service.py", "models.py", "config.py", "routers/homework.py")]
            + [Path(__file__), ROOT / "apitest" / "async_fixture.py", ROOT / "apitest" / "async_fake_model.py"]}
        try:
            command(["down", "--volumes", "--remove-orphans"])
            results["cleanup"] = "only generated isolated project removed"
        finally:
            result_path = evidence / (args.output_prefix + "real-broker-result.json")
            result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Evidence: " + str(result_path.relative_to(ROOT)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
