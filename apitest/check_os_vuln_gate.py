"""OS 层漏洞门禁脚本检查（trivy_os_gate）。

覆盖三类：
  正常：HIGH 命中未过期例外、无 CRITICAL → 通过；例外未命中只告警
  失败：CRITICAL、HIGH 未登记、例外过期 → 非零
  边界：报告缺失 → 输入错（exit 2）；真实例外表与当前 12 个 CVE 一致

只读本地文件，不联网、不调用 trivy。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

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


def write_report(path: Path, image: str, vulns: list) -> None:
    path.write_text(
        json.dumps(
            {
                "ArtifactName": image,
                "Results": [{"Target": f"{image} (debian 13.7)", "Vulnerabilities": vulns}],
            }
        ),
        encoding="utf-8",
    )


def write_exceptions(path: Path, entries: list) -> None:
    path.write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")


def run(args):
    return subprocess.run(
        [sys.executable, "-I", "-B", str(GATE), *args],
        capture_output=True,
        text=True,
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

    # 边界：真实例外表可解析，且覆盖当前 12 个 CVE
    data = json.loads(REAL_EXCEPTIONS.read_text(encoding="utf-8"))
    cves = {e["cve"] for e in data["entries"]}
    check("真实例外表含 12 条", len(data["entries"]) == 12)
    check("真实例外表均带 reason 与 review_after",
          all(e.get("reason") and e.get("review_after") for e in data["entries"]))
    check("可修复的 CVE-2026-76844 未登记为例外", "CVE-2026-76844" not in cves)

    # 边界：用真实例外表跑一遍当前 12 个 CVE 的报告 → 通过
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
        vuln("CVE-2026-85091", "HIGH", pkg="zlib1g", installed="1:1.3.dfsg+really1.3.1-1+b1"),
    ]
    write_report(report, "campusclaw-backend:t", current)
    result = run(["--exceptions", str(REAL_EXCEPTIONS), "--today", "2026-11-16", str(report)])
    check("真实例外表覆盖当前 12 个 CVE → exit 0", result.returncode == 0)

    # 边界：已修复的包不再算失败来源
    write_report(report, "campusclaw-backend:t", [vuln("CVE-2026-76844", "HIGH", pkg="zlib1g",
                                                        fixed="1:1.3.dfsg+really1.3.1-1+deb13u1")])
    result = run(["--exceptions", str(REAL_EXCEPTIONS), "--today", "2026-11-16", str(report)])
    check("有修复版本但未升级的包仍判失败（不因 FixedVersion 非空而放行）", result.returncode == 1)

passed = sum(1 for _, p in checks if p)
total = len(checks)
print(f"\n结果：{passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
