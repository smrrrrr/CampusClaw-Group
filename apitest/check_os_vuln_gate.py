"""OS 层漏洞门禁脚本检查（trivy_os_gate）。

覆盖三类：
  正常：HIGH 命中未过期例外、无 CRITICAL → 通过；例外未命中只告警
  失败：CRITICAL、HIGH 未登记、例外过期 → 非零
  边界：无效或重复报告 → exit 2；合法空报告和当前书面例外仍可通过

只读本地文件，不联网。Docker 核验使用测试替身。
"""

import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "trivy_os_gate.py"
REAL_EXCEPTIONS = ROOT / "reports" / "security-evidence" / "os-vuln-exceptions.json"

checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(("  ✓ " if passed else "  ✗ ") + name)


def vuln(cve, severity, pkg="util-linux", installed="2.41.5-0+deb13u1", fixed=""):
    return {
        "VulnerabilityID": cve,
        "Severity": severity,
        "PkgName": pkg,
        "InstalledVersion": installed,
        "FixedVersion": fixed,
    }


def write_report(path: Path, image: str, vulns: list | None, image_id: str | None = None) -> None:
    report = {"SchemaVersion": 2, "ArtifactType": "container_image", "ArtifactName": image}
    if image_id is not None:
        report["Metadata"] = {"ImageID": image_id}
    if vulns is not None:
        report["Results"] = [{"Target": f"{image} (debian 13.7)", "Vulnerabilities": vulns}]
    path.write_text(json.dumps(report), encoding="utf-8")


def write_exceptions(path: Path, entries: list) -> None:
    path.write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")


def run(args):
    return subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", str(GATE), *args],
        capture_output=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )


with tempfile.TemporaryDirectory(prefix="os-gate-") as tmp:
    tmp = Path(tmp)

    # 正常：HIGH 命中未过期例外
    report = tmp / "trivy-backend.json"
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-76642", "HIGH")])
    exceptions = tmp / "exceptions.json"
    write_exceptions(
        exceptions,
        [{"cve": "CVE-2026-76642", "packages": ["util-linux"], "review_after": "2099-01-01",
          "reason": "fixture"}],
    )
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("HIGH 命中未过期例外 → exit 0", result.returncode == 0)
    check("汇总行包含镜像与计数", "campusclaw-backend:t" in result.stdout and "HIGH=1" in result.stdout)

    write_report(report, "campusclaw-backend:t", [
        vuln("CVE-2026-76642", "HIGH", pkg="unlisted-package", fixed="3.0.0"),
    ])
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("同 CVE 的未登记软件包 → exit 1",
          result.returncode == 1 and "unlisted-package" in result.stdout)

    report.write_text("{}", encoding="utf-8")
    result = run(["--exceptions", str(exceptions), str(report)])
    check("缺少 Trivy 元数据的空对象 → exit 2", result.returncode == 2)

    write_report(report, "campusclaw-backend:t", None)
    result = run(["--exceptions", str(exceptions), str(report)])
    check("合法 Trivy 报告省略空 Results → exit 0", result.returncode == 0)
    write_report(report, "campusclaw-backend:t", [])
    result = run(["--exceptions", str(exceptions), str(report)])
    check("合法 Trivy 报告有空的漏洞数组 → exit 0", result.returncode == 0)
    duplicate = tmp / "trivy-duplicate.json"
    write_report(duplicate, "campusclaw-backend:t", None)
    result = run(["--exceptions", str(exceptions), str(report), str(duplicate)])
    check("两份报告来自同一镜像 → exit 2", result.returncode == 2)

    invalid = json.loads(report.read_text(encoding="utf-8"))
    invalid["Results"] = {}
    report.write_text(json.dumps(invalid), encoding="utf-8")
    result = run(["--exceptions", str(exceptions), str(report)])
    check("Results 结构错误 → exit 2", result.returncode == 2)

    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-76642", "", pkg="util-linux")])
    result = run(["--exceptions", str(exceptions), str(report)])
    check("漏洞严重度字段为空 → exit 2", result.returncode == 2)

    # 失败：CRITICAL 一律否决（即使登记了例外）
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-0001", "CRITICAL")])
    write_exceptions(
        exceptions,
        [{"cve": "CVE-2026-0001", "packages": ["x"], "review_after": "2099-01-01",
          "reason": "fixture"}],
    )
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("CRITICAL → exit 1", result.returncode == 1)
    check("CRITICAL 不接受例外", "不接受例外" in result.stdout)

    # 失败：HIGH 未登记
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-0002", "HIGH")])
    write_exceptions(exceptions, [])
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("HIGH 未登记 → exit 1", result.returncode == 1)
    check("未登记项列出包名", "util-linux" in result.stdout)

    # 失败：例外过期
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-76642", "HIGH")])
    write_exceptions(
        exceptions,
        [{"cve": "CVE-2026-76642", "packages": ["util-linux"], "review_after": "2026-01-01",
          "reason": "fixture"}],
    )
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("例外过期 → exit 1", result.returncode == 1)
    check("过期提示含日期", "2026-01-01" in result.stdout)

    # 正常：例外未命中只告警
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-0003", "MEDIUM")])
    write_exceptions(
        exceptions,
        [{"cve": "CVE-2026-76642", "packages": ["util-linux"], "review_after": "2099-01-01",
          "reason": "fixture"}],
    )
    result = run(["--exceptions", str(exceptions), "--today", "2026-11-16", str(report)])
    check("MEDIUM 不影响判定，未命中例外只告警 → exit 0",
          result.returncode == 0 and "可从例外表删除" in result.stdout)

    # 边界：报告缺失
    result = run(["--exceptions", str(exceptions), str(tmp / "nope.json")])
    check("报告缺失 → exit 2", result.returncode == 2)

    # 边界：真实例外表可解析，且覆盖当前 11 个 CVE
    data = json.loads(REAL_EXCEPTIONS.read_text(encoding="utf-8"))
    cves = {e["cve"] for e in data["entries"]}
    check("真实例外表含 11 条", len(data["entries"]) == 11)
    check("真实例外表均带 reason 与 review_after",
          all(e.get("reason") and e.get("review_after") for e in data["entries"]))
    check("可修复的 CVE-2026-76844 未登记为例外", "CVE-2026-76844" not in cves)

    # 边界：用真实例外表跑一遍当前 11 个 CVE 的报告 → 通过
    current = [
        vuln("CVE-2026-76642", "HIGH"),
        vuln("CVE-2026-78408", "HIGH"),
        vuln("CVE-2026-78409", "HIGH"),
        vuln("CVE-2026-78410", "HIGH"),
        vuln("CVE-2025-69720", "HIGH", pkg="libtinfo6", installed="6.5+20250216-2"),
        vuln("CVE-2026-119373", "HIGH", pkg="libsqlite3-0", installed="3.46.1-7+deb13u2"),
        vuln("CVE-2026-119374", "HIGH", pkg="libsqlite3-0", installed="3.46.1-7+deb13u2"),
        vuln("CVE-2026-119379", "HIGH", pkg="libsqlite3-0", installed="3.46.1-7+deb13u2"),
        vuln("CVE-2026-16742", "HIGH", pkg="libsystemd0", installed="257.13-1~deb13u1"),
        vuln("CVE-2026-54369", "HIGH", pkg="libacl1", installed="2.3.2-2+b1"),
        vuln("CVE-2026-9538", "HIGH", pkg="perl-base", installed="5.40.1-6+deb13u1"),
    ]
    write_report(report, "campusclaw-backend:t", current)
    result = run(["--exceptions", str(REAL_EXCEPTIONS), "--today", "2026-11-16", str(report)])
    check("真实例外表覆盖当前 11 个 CVE → exit 0", result.returncode == 0)

    # 边界：已修复的包不再算失败来源
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-76844", "HIGH", pkg="zlib1g",
                                                        fixed="1:1.3.dfsg+really1.3.1-1+deb13u1")])
    result = run(["--exceptions", str(REAL_EXCEPTIONS), "--today", "2026-11-16", str(report)])
    check("有修复版本但未升级的包仍判失败（不因 FixedVersion 非空而放行）", result.returncode == 1)

    sys.path.insert(0, str(GATE.parent))
    import trivy_os_gate as gate

    image = "campusclaw-backend:" + "a" * 40
    image_id = "sha256:" + "b" * 64
    ncurses = vuln("CVE-2025-69720", "HIGH", pkg="ncurses-bin", installed="6.5+20250216-2")
    write_report(report, image, [ncurses], image_id)
    args = ["--exceptions", str(REAL_EXCEPTIONS), "--today", "2026-11-17", str(report)]
    check("未启用运行镜像核验时 ncurses-bin 仍失败", run(args).returncode == 1)

    args += ["--verify-infocmp-in", image]
    same_image = subprocess.CompletedProcess([], 0, stdout=image_id + "\n")
    with patch.object(gate.subprocess, "run", side_effect=[same_image, subprocess.CompletedProcess([], 0)]) as docker:
        with redirect_stdout(StringIO()) as output:
            rc = gate.main(args)
        command = docker.call_args.args[0]
    check("相同扫描镜像且 infocmp 已移除才放行",
          rc == 0 and "已核验缓解" in output.getvalue() and image_id in command and "--pull=never" in command)

    with patch.object(gate.subprocess, "run", side_effect=[same_image, subprocess.CompletedProcess([], 1)]):
        with redirect_stdout(StringIO()):
            rc = gate.main(args)
    check("infocmp 仍存在时拒绝放行", rc == 1)

    other_image = subprocess.CompletedProcess([], 0, stdout="sha256:" + "c" * 64)
    with patch.object(gate.subprocess, "run", return_value=other_image) as docker:
        with redirect_stdout(StringIO()):
            rc = gate.main(args)
    check("扫描镜像 ID 不匹配时拒绝放行", rc == 1 and docker.call_count == 1)

    write_report(report, image, [dict(ncurses, FixedVersion="6.6+deb13u1")], image_id)
    with patch.object(gate.subprocess, "run") as docker:
        with redirect_stdout(StringIO()):
            rc = gate.main(args)
    check("存在可升级的修复版本时拒绝放行", rc == 1 and docker.call_count == 0)

    # 回归：CI 里门禁步骤必须带 pipefail，否则退出码取自 tee，判失败也会显示通过
    # （run 43884238012 实际踩过：脚本 exit 1，job 仍 success）
    workflow = (ROOT / ".github" / "workflows" / "lesson10.yml").read_text(encoding="utf-8")
    check("workflow 门禁步骤启用 pipefail", "set -o pipefail" in workflow)
    check("workflow 门禁步骤调用 trivy_os_gate.py", "scripts/trivy_os_gate.py" in workflow)
    gate_args = workflow.partition("python3 scripts/trivy_os_gate.py")[2].partition("| tee")[0]
    check("workflow 门禁显式要求三份报告",
          all(f"reports/lesson-10/ci/trivy-{image}.json" in gate_args
              for image in ("backend", "frontend", "mcp-tools")))
    check("workflow 门禁核验两个含 ncurses-bin 的运行镜像",
          all(f'--verify-infocmp-in "campusclaw-{service}:${{{{ steps.rev.outputs.sha }}}}"' in gate_args
              for service in ("backend", "mcp-tools")))

passed = sum(1 for _, p in checks if p)
total = len(checks)
print(f"\n结果：{passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
