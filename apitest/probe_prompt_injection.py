"""四组可重放宿主防线实验：强制假模型发起攻击，不宣称真实模型防注入率。"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from probe_security_precheck import ROOT, run


async def main(output):
    names = ["实验-直接注入", "实验-间接注入", "实验-外泄", "SEC-08 失败：学生写入拒绝且SSE完整"]
    with tempfile.TemporaryDirectory(prefix="injection-experiments-") as tmp:
        evidence = Path(tmp) / "probe.json"
        rc = await run(evidence)
        data = json.loads(evidence.read_text())
    groups = []
    for name in names:
        checks = [c for c in data["checks"] if c["case"].startswith(name)]
        groups.append({"group": name, "passed": bool(checks) and all(c["passed"] for c in checks), "checks": checks})
    result = {"time": datetime.now(timezone.utc).isoformat(), "scope": data["scope"],
              "limitation": "强制假模型决策的宿主防线实验；不是在线模型安全评测", "groups": groups,
              "passed": sum(g["passed"] for g in groups), "failed": sum(not g["passed"] for g in groups), "probe_exit": rc}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"提示注入实验：{result['passed']}/4；{output}")
    return int(rc != 0 or result["failed"] != 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/security-evidence/prompt-injection-results.json")
    raise SystemExit(asyncio.run(main(parser.parse_args().output)))
