"""密钥扫描（docs/standards/03-安全开发规范.md 硬约束 3）。

1. 本机 .env 中名含 KEY / SECRET / TOKEN / PASSWORD、长度 ≥ 8 的值，不得出现在任何提交或工作区文件（已跟踪及未被忽略的新文件）里；
2. 通用密钥形态（sk- 开头的长串、私钥块）不得出现在工作区文件里；
3. .env、数据库文件、上传目录不得被 Git 跟踪。

输出只含键名与文件名，从不打印密钥值。没有 .env 时跳过第 1 项（新克隆的仓库）。

用法（项目根）：python scripts/secret_scan.py
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_NAME = re.compile(r"KEY|SECRET|TOKEN|PASSWORD")
GENERIC_PATTERNS = {
    "sk- 开头的 API Key": r"sk-[A-Za-z0-9]{20,}",
    "私钥块": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
}
FORBIDDEN_TRACKED = [
    (re.compile(r"(^|/)\.env$"), ".env"),
    (re.compile(r"\.(db|sqlite3?)$"), "数据库文件"),
    (re.compile(r"(^|/)uploads/"), "上传目录"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def env_secrets() -> dict[str, str]:
    path = ROOT / ".env"
    if not path.exists():
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if SECRET_NAME.search(key) and len(value) >= 8:
            found[key.strip()] = value
    return found


def main() -> int:
    problems = []
    revisions = git("rev-list", "--all").split()

    secrets = env_secrets()
    for key, value in secrets.items():
        hits = set()
        if revisions:
            for line in git("grep", "-l", "-F", "-e", value, *revisions).splitlines():
                hits.add(line.split(":", 1)[1] if ":" in line else line)
        hits.update(git("grep", "--untracked", "-l", "-F", "-e", value).splitlines())
        for path in sorted(hits):
            problems.append(f"{key} 的值出现在 {path}（处理方式：立即轮换该密钥，见 README「密钥泄露处置」）")

    for label, pattern in GENERIC_PATTERNS.items():
        for path in git("grep", "--untracked", "-l", "-E", "-e", pattern).splitlines():
            problems.append(f"已跟踪文件 {path} 含疑似{label}")

    for path in git("ls-files").splitlines():
        for pattern, label in FORBIDDEN_TRACKED:
            if pattern.search(path) and not path.endswith(".env.example"):
                problems.append(f"{label}被 Git 跟踪：{path}")

    for problem in problems:
        print("  ✗ " + problem)
    checked = "、".join(secrets) if secrets else "无 .env，跳过"
    print(f"密钥扫描：{len(revisions)} 个提交；本机密钥 {checked}；{len(problems)} 处问题")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
