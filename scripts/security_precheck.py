"""可重放安全自查。只写脱敏证据，已知红项也必须非零退出；不升级依赖、不改教学库。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports/security-evidence"
PRIVATE = ROOT / ".review/security-precheck"
PY = ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
sys.path.insert(0, str(ROOT / "scripts"))
from secret_scan import env_secrets, GENERIC_PATTERNS


def command(args, cwd=ROOT, timeout=180):
    started = time.monotonic()
    try:
        p = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        return p.returncode, p.stdout, p.stderr, round(time.monotonic() - started, 3)
    except (OSError, subprocess.TimeoutExpired) as exc:
        # 不把外部异常原文或捕获到的私有内容写入报告。
        return 2, b"", type(exc).__name__.encode(), round(time.monotonic() - started, 3)


def save(name, data):
    (EVIDENCE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint():
    paths = [p for folder in ("backend", "frontend/app", "frontend/components", "frontend/lib")
             for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".css"}
             and not {".venv", "node_modules", "__pycache__"}.intersection(p.parts)]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def secret_baseline():
    rc, out, err, seconds = command([PY, "scripts/secret_scan.py"])
    (EVIDENCE / "secret-scan.txt").write_bytes(out + err)
    secrets = list(env_secrets().values())
    def inspect(data):
        return {"bytes": len(data), "current_secret_hits": sum(v.encode() in data for v in secrets),
                "generic_hits": {label: len(re.findall(pattern.encode(), data)) for label, pattern in GENERIC_PATTERNS.items()}}
    history_rc, history, _, _ = command(["git", "log", "--all", "-p", "--format="], timeout=120)
    result = {"worktree_and_current_secret_history_exit": rc, "local_git_history": inspect(history),
              "history_command_exit": history_rc, "current_secret_count": len(secrets), "runtime": [],
              "limits": ["只包含本地Git引用，不包含未获取远端引用或无法识别的已轮换旧密钥", "运行日志只包含当前可取得容器；被删除或轮换日志不在范围内"]}
    docker = shutil.which("docker")
    if docker:
        compose_project = os.environ.get("COMPOSE_PROJECT_NAME")
        if not compose_project:
            env_path = ROOT / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("COMPOSE_PROJECT_NAME="):
                        compose_project = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not compose_project:
            compose_project = "campusclaw-groupv3"
        drc, names, _, _ = command([docker, "ps", "--filter", f"label=com.docker.compose.project={compose_project}", "--format", "{{.Names}}"], timeout=20)
        if drc == 0 and names.strip():
            for name in names.decode().splitlines():
                lrc, logs, stderr, _ = command([docker, "logs", name], timeout=30)
                result["runtime"].append({"container": name, "kind": "available_logs", "exit": lrc, **inspect(logs + stderr)})
                if "frontend" in name:
                    trc, tar, _, _ = command([docker, "exec", name, "tar", "-cf", "-", ".next/static"], timeout=60)
                    result["runtime"].append({"container": name, "kind": "frontend_static_tar", "exit": trc, **inspect(tar)})
        else:
            result["runtime_blocked"] = "Docker引擎不可达或本项目容器未运行"
    else:
        result["runtime_blocked"] = "Docker命令不存在"
    scopes = [result["local_git_history"], *result["runtime"]]
    result["leak_detected"] = any(s["current_secret_hits"] or any(s["generic_hits"].values()) for s in scopes) or rc == 1
    result["complete"] = (rc == history_rc == 0 and not result.get("runtime_blocked")
        and all(s["exit"] == 0 for s in result["runtime"]) and any(s["kind"] == "frontend_static_tar" for s in result["runtime"]))
    save("secret-baseline.json", result)
    return result


def dependency_audit():
    manifest = {"source": "npm registry security audit API; pip-audit default PyPI vulnerability service",
                "time": datetime.now(timezone.utc).isoformat(), "commands": [], "locks": {}, "versions": {}}
    # 防止断网失败后把上一次JSON误当成本次成功结果。
    for label in ("npm", "backend", "mcp"):
        (EVIDENCE / f"{label}-audit.json").unlink(missing_ok=True)
    for rel in ("frontend/package-lock.json", "backend/uv.lock", "mcp-server/uv.lock"):
        manifest["locks"][rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or "npm"
    uv = shutil.which("uv") or "uv"
    uvx = shutil.which("uvx") or "uvx"
    for name, args in [("npm", [npm, "--version"]), ("uv", [uv, "--version"]), ("pip-audit", [uvx, "--from", "pip-audit", "pip-audit", "--version"])]:
        rc, out, _, _ = command(args)
        manifest["versions"][name] = {"exit": rc, "version": out.decode(errors="replace").strip()}
    args = [npm, "audit", "--omit=dev", "--json", "--registry=https://registry.npmjs.org"]
    rc, out, err, seconds = command(args, cwd=ROOT / "frontend")
    (EVIDENCE / "npm-audit.json").write_bytes(out)
    (PRIVATE / "npm-audit-error.txt").write_bytes(err)
    manifest["commands"].append({"name": "npm", "command": args, "exit": rc, "seconds": seconds})
    for project, label in [("backend", "backend"), ("mcp-server", "mcp")]:
        req = PRIVATE / f"{label}-requirements.txt"
        args = [uv, "export", "--locked", "--no-dev", "--no-hashes", "--no-emit-project", "--project", project, "--output-file", req]
        erc, _, err, seconds = command(args)
        manifest["commands"].append({"name": label + "-export", "exit": erc, "seconds": seconds})
        (PRIVATE / f"{label}-export.txt").write_bytes(err)
        if erc:
            continue
        # 只复制锁定依赖清单，项目中不存在私有索引或凭证。
        (EVIDENCE / f"{label}-requirements.txt").write_bytes(req.read_bytes())
        args = [uvx, "--from", "pip-audit", "pip-audit", "--requirement", req, "--no-deps", "--disable-pip", "--format", "json", "--output", EVIDENCE / f"{label}-audit.json"]
        rc, out, err, seconds = command(args)
        (PRIVATE / f"{label}-audit-out.txt").write_bytes(out + err)
        manifest["commands"].append({"name": label, "exit": rc, "seconds": seconds})
    save("dependency-run.json", manifest)
    return manifest


def dependency_summary():
    result = {}
    for label in ("npm", "backend", "mcp"):
        try:
            data = json.loads((EVIDENCE / f"{label}-audit.json").read_text(encoding="utf-8-sig"))
            if label == "npm":
                result[label] = data["metadata"]["vulnerabilities"]
            else:
                vulnerable = [d for d in data["dependencies"] if d.get("vulns")]
                result[label] = {"vulnerable_packages": len(vulnerable), "advisories": sum(len(d["vulns"]) for d in vulnerable),
                    "unique_ids": len({v["id"] for d in vulnerable for v in d["vulns"]}),
                    "severity": "pip-audit响应不提供严重度，未判级，不能填high/critical=0",
                    "packages": [{"name": d["name"], "version": d["version"], "advisories": len(d["vulns"])} for d in vulnerable]}
        except (OSError, ValueError, KeyError, TypeError):
            result[label] = {"blocked": "没有可解析的本次漏洞数据库响应"}
    save("dependency-summary.json", result)
    return result


def load_exceptions():
    """加载依赖漏洞例外登记表。"""
    path = EVIDENCE / "dependency-exceptions.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("exceptions", [])
    except (OSError, ValueError):
        return []


def check_dependency_exceptions(deps):
    """校验所有有漏洞的包都在例外登记表中有未过期的对应条目。

    返回 (unregistered_packages, expired_exceptions)：
    - unregistered_packages: 有漏洞但登记表中找不到对应条目的包列表
    - expired_exceptions: 登记表中 review_after 已过期的条目
    """
    exceptions = load_exceptions()
    today = datetime.now(timezone.utc).date()
    unregistered = []
    expired = []

    # 构建已登记包名集合（按 ecosystem 分组）
    registered = {}
    for exc in exceptions:
        eco = exc.get("ecosystem", "")
        pkg = exc.get("package", "")
        registered.setdefault(eco, set()).add(pkg)
        # 检查过期
        review_after = exc.get("review_after", "")
        if review_after:
            try:
                if datetime.fromisoformat(review_after).date() < today:
                    expired.append(f"{pkg}（review_after={review_after}）")
            except ValueError:
                pass

    # npm：vulnerabilities 对象的 key 是包名
    npm_deps = deps.get("npm", {})
    if isinstance(npm_deps, dict) and "vulnerabilities" in npm_deps:
        for pkg in npm_deps["vulnerabilities"]:
            if pkg not in registered.get("npm", set()):
                unregistered.append(f"npm:{pkg}")

    # pip（backend/mcp）：packages 列表
    for label in ("backend", "mcp"):
        d = deps.get(label, {})
        for p in d.get("packages", []):
            pkg = p.get("name", "")
            if pkg not in registered.get("pip", set()):
                unregistered.append(f"{label}:{pkg}")

    return unregistered, expired


def readonly_accounts():
    # 优先使用 .env 中的 DATABASE_URL，否则依次尝试常见路径
    dbpath = None
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().upper().startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if url.startswith("sqlite"):
                    rel = url.split("sqlite:///", 1)[-1] if "sqlite:///" in url else url.split("sqlite://", 1)[-1]
                    candidate = ROOT / rel.lstrip("./")
                    if candidate.exists():
                        dbpath = candidate
                        break
    if dbpath is None:
        for rel in ("data/current/campusclaw.db", "data/review/campusclaw.db", "campusclaw.db"):
            candidate = ROOT / rel
            if candidate.exists():
                dbpath = candidate
                break
    result = {"mode": "SQLite mode=ro; no passwords or hashes queried", "identities": [], "db_path": str(dbpath) if dbpath else None}
    if dbpath and dbpath.exists():
        with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
            result["identities"] = [dict(zip(["identifier", "role", "class_id", "subject", "teaching_classes", "must_change_password"], row))
                for row in db.execute("SELECT identifier,role,class_id,subject,teaching_classes,must_change_password FROM users WHERE identifier IN ('TEA001','TEA002','20260001','20260002') ORDER BY identifier")]
    else:
        result["blocked"] = "本地教学库不存在"
    if len(result["identities"]) != 4:
        result["blocked"] = "四个演示身份未全部在本地库中找到"
    save("accounts-readonly.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-dependency-evidence", action="store_true", help="仅复查已有依赖证据，不冒充本次联网重扫")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    before = fingerprint()
    save("source-before.json", before)
    run = {"started": datetime.now(timezone.utc).isoformat(), "dependency_evidence_reused": args.reuse_dependency_evidence,
           "business_changes": False, "git_head": command(["git", "rev-parse", "HEAD"])[1].decode().strip(),
           "tools": {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in
                     ("scripts/security_precheck.py", "scripts/secret_scan.py", "apitest/probe_security_precheck.py")}}
    accounts = readonly_accounts()
    rc, out, err, seconds = command([PY, "apitest/probe_security_precheck.py"], timeout=120)
    (PRIVATE / "api-probe-out.txt").write_bytes(out + err)
    run["probe_exit"] = rc
    print(f"接口探针退出码={rc}（1表示观察到红项，2表示执行未完成）", flush=True)
    secrets = secret_baseline()
    print(f"密钥扫描：疑似泄漏={secrets['leak_detected']}，范围完整={secrets['complete']}", flush=True)
    if not args.reuse_dependency_evidence:
        dependency_audit()
    deps = dependency_summary()
    unregistered, expired = check_dependency_exceptions(deps)
    if unregistered:
        print(f"未登记的漏洞包：{unregistered}", flush=True)
    if expired:
        print(f"已过期的依赖例外登记：{expired}", flush=True)
    print(json.dumps(deps, ensure_ascii=False), flush=True)
    after = fingerprint()
    run.update(finished=datetime.now(timezone.utc).isoformat(), source_unchanged=before == after,
               secret_leak_detected=secrets["leak_detected"], secret_scope_complete=secrets["complete"],
               unregistered_vulns=unregistered, expired_exceptions=expired)
    save("source-after.json", after)
    blocked = "blocked" in accounts or rc == 2 or not secrets["complete"] or any("blocked" in d for d in deps.values())
    # 红项：探针红、密钥泄漏、有漏洞包未在例外登记表中、例外登记已过期
    red = rc == 1 or secrets["leak_detected"] or bool(unregistered) or bool(expired)
    run["exit"] = 1 if red or before != after else 2 if blocked else 0
    run["status"] = "RED" if red else "BLOCKED" if blocked else "PASS"
    run["has_blocked_scope"] = blocked
    save("run.json", run)
    print(f"安全自查={run['status']}，有待验范围={blocked}；reports/security-evidence/run.json", flush=True)
    return run["exit"]


if __name__ == "__main__":
    sys.exit(main())
