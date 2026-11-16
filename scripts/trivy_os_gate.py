#!/usr/bin/env python3
"""镜像 OS 层漏洞门禁：读 Trivy JSON 报告，按书面例外判定。

判定规则（不读 .trivyignore，报告里始终保留全部漏洞）：
  - 任何 CRITICAL → 失败，且 CRITICAL 不得登记例外；
  - HIGH 未登记例外 → 失败；
  - 例外已过 review_after → 失败（例外自动失效）；
  - 例外未命中任何报告 → 只告警，提示把已消失的条目删掉。

用法：
  python3 scripts/trivy_os_gate.py reports/lesson-10/ci/trivy-*.json
  python3 scripts/trivy_os_gate.py --exceptions <path> --today 2026-11-16 <reports...>

退出码：0 通过；1 有未覆盖或过期项；2 输入有误（报告缺失/无法解析）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

DEFAULT_EXCEPTIONS = "reports/security-evidence/os-vuln-exceptions.json"


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def collect_findings(report_path: Path) -> list[dict]:
    """把一份 Trivy JSON 报告摊平成漏洞列表。"""
    report = load_json(report_path)
    artifact = report.get("ArtifactName") or report_path.stem
    findings = []
    for result in report.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            findings.append(
                {
                    "image": artifact,
                    "report": report_path.name,
                    "cve": vuln.get("VulnerabilityID", ""),
                    "severity": (vuln.get("Severity") or "").upper(),
                    "package": vuln.get("PkgName", ""),
                    "installed": vuln.get("InstalledVersion", ""),
                    "fixed": vuln.get("FixedVersion", ""),
                    "target": result.get("Target", ""),
                }
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="镜像 OS 层漏洞门禁")
    parser.add_argument("reports", nargs="+", help="Trivy JSON 报告路径")
    parser.add_argument("--exceptions", default=DEFAULT_EXCEPTIONS, help="书面例外表")
    parser.add_argument(
        "--today", default=dt.date.today().isoformat(), help="用于判定例外是否过期的日期"
    )
    args = parser.parse_args(argv)

    today = parse_date(args.today)
    exceptions_path = Path(args.exceptions)
    if not exceptions_path.exists():
        print(f"例外表不存在：{exceptions_path}", file=sys.stderr)
        return 2

    exceptions = {}
    for entry in load_json(exceptions_path).get("entries") or []:
        cve = entry.get("cve", "")
        if not cve:
            continue
        exceptions[cve] = {
            "review_after": parse_date(entry["review_after"]),
            "reason": entry.get("reason", ""),
            "packages": entry.get("packages") or [],
        }

    findings = []
    for raw in args.reports:
        path = Path(raw)
        if not path.exists():
            print(f"报告不存在：{path}", file=sys.stderr)
            return 2
        try:
            findings.extend(collect_findings(path))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"报告无法解析：{path}（{exc}）", file=sys.stderr)
            return 2

    blocked: list[str] = []
    excepted_hits: dict[str, int] = {}
    summaries: dict[str, dict[str, int]] = {}

    for item in findings:
        image = item["image"]
        summary = summaries.setdefault(image, {"HIGH": 0, "CRITICAL": 0, "excepted": 0})
        summary[item["severity"] or "UNKNOWN"] = summary.get(item["severity"] or "UNKNOWN", 0) + 1

        if item["severity"] == "CRITICAL":
            blocked.append(
                f"CRITICAL {item['cve']} {item['package']} {item['installed']} "
                f"（{image}，CRITICAL 不接受例外）"
            )
            continue
        if item["severity"] != "HIGH":
            continue

        entry = exceptions.get(item["cve"])
        if entry is None:
            fixed = item["fixed"] or "（无修复版本）"
            blocked.append(
                f"HIGH {item['cve']} {item['package']} 装={item['installed']} 修={fixed}"
                f"（{image}，未登记例外）"
            )
            continue
        if entry["review_after"] < today:
            blocked.append(
                f"HIGH {item['cve']} {item['package']}（{image}，例外已于 "
                f"{entry['review_after'].isoformat()} 过期，需重新评估）"
            )
            continue
        summary["excepted"] += 1
        excepted_hits[item["cve"]] = excepted_hits.get(item["cve"], 0) + 1

    print("== 镜像 OS 层扫描汇总 ==")
    for image in sorted(summaries):
        s = summaries[image]
        print(
            f"  {image}: HIGH={s.get('HIGH', 0)} CRITICAL={s.get('CRITICAL', 0)} "
            f"其中例外放行={s.get('excepted', 0)}"
        )

    unused = sorted(set(exceptions) - set(excepted_hits))
    if unused:
        print("\n== 告警：例外未命中（漏洞已消失或已被修复）==")
        for cve in unused:
            print(f"  {cve}：可从例外表删除")

    if blocked:
        print("\n== 未通过的项 ==")
        for line in blocked:
            print("  ✗ " + line)
        print(f"\n结果：失败（{len(blocked)} 项）")
        return 1

    print("\n结果：通过（HIGH 均已有修复版本或登记了未过期的书面例外；无 CRITICAL）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
