"""第三轮评审全链路回归；make check 子进程隔离，证据仅用临时目录。"""
import asyncio
from pathlib import Path
import tempfile

from probe_security_precheck import run


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="review-check-") as tmp:
        raise SystemExit(asyncio.run(run(Path(tmp) / "checks.json")))
