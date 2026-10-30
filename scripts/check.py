"""一键门禁：合并前必跑，任一子项非零退出即不通过（docs/standards/04-测试规范.md §7）。

子项顺序：openspec 严格校验 → 分层检查 → 密钥扫描 → 前端类型检查 → apitest 离线回归。
回归子进程强制隔离：测试专用 JWT_SECRET_KEY、空模型 Key、模型地址指向本机不可达端口，
环境变量优先于 .env，因此不会读到真实 Key，也不会连外网。

用法（项目根）：make check，或 python scripts/check.py
前提：backend 下执行过 uv sync（含 dev 依赖），frontend 下执行过 npm ci，已安装 openspec CLI。
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = os.name == "nt"
BACKEND_PYTHON = ROOT / "backend" / ".venv" / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
TSC = ROOT / "frontend" / "node_modules" / ".bin" / ("tsc.cmd" if IS_WINDOWS else "tsc")

ISOLATED_ENV = {
    "JWT_SECRET_KEY": "check-only-jwt-secret-not-for-real-use-000000",
    "DEEPSEEK_API_KEY": "",
    "DEEPSEEK_BASE_URL": "http://127.0.0.1:9/v1",
    "MCP_TOOLS_HEALTH_URL": "",
    "PYTHONPATH": str(ROOT / "backend"),
}


def steps() -> list[tuple[str, list[str], dict | None]]:
    py = str(BACKEND_PYTHON)
    openspec_cmd = shutil.which("openspec") or "openspec"
    items = [
        ("openspec-validate", [openspec_cmd, "validate", "--all", "--strict", "--no-interactive"], None),
        ("layering", [py, "scripts/check_layering.py"], None),
        ("secret-scan", [py, "scripts/secret_scan.py"], None),
        ("fe-typecheck", [str(TSC), "--noEmit", "-p", "frontend/tsconfig.json"], None),
    ]
    for script in sorted((ROOT / "apitest").glob("check_*.py")):
        items.append((script.stem, [py, str(script.relative_to(ROOT))], ISOLATED_ENV))
    for script in sorted((ROOT / "apitest").glob("check_*.cjs")):
        items.append((script.stem, ["node", str(script.relative_to(ROOT))], None))
    return items


def missing_prerequisites() -> list[str]:
    missing = []
    if not BACKEND_PYTHON.exists():
        missing.append("backend/.venv（在 backend 下执行 uv sync）")
    if not TSC.exists():
        missing.append("frontend/node_modules（在 frontend 下执行 npm ci）")
    for tool in ("openspec", "node", "git"):
        if shutil.which(tool) is None:
            missing.append(f"命令 {tool}")
    return missing


def main() -> int:
    missing = missing_prerequisites()
    if missing:
        print("门禁无法运行，缺少：" + "；".join(missing))
        return 2

    failed = []
    for name, command, extra_env in steps():
        env = {**os.environ, **extra_env} if extra_env else None
        started = time.time()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        elapsed = time.time() - started
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"[{status}] {name}  ({elapsed:.1f}s)")
        if result.returncode != 0:
            failed.append(name)
            tail = (result.stdout + result.stderr).strip().splitlines()[-15:]
            for line in tail:
                print("        " + line)

    if failed:
        print(f"\n门禁未通过：{', '.join(failed)}")
        return 1
    print("\n门禁全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
