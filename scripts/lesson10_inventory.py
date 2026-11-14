"""第10课命令盘点：从门禁入口、探针、异步与部署入口生成可核实的命令表。

只读：不执行任何命令，不修改证据。`--check-meta` 可传入 `scripts/check.py --json`
生成的记录，用其中的起止时间与退出码填充"上次可核实执行"；找不到时间的条目如实写"未知"，
不拿文件 mtime 代替。
"""

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/command-inventory.md"

# 已知证据文件里可核实的最近执行时间（字段名 → 文件）。只登记真实存在的记录。
EVIDENCE_TIME_SOURCES = [
    ("安全门禁", ROOT / "reports/security-evidence/run.json", ("started", "finished")),
    ("真实队列异步复现", ROOT / "reports/async-grading/history-real-broker-result.json", ("started", "finished")),
]


def load_check_steps():
    spec = importlib.util.spec_from_file_location("gate_check", ROOT / "scripts/check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.steps(), module.ISOLATED_ENV


def first_doc_line(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'^"""(.*?)$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def load_times():
    times = {}
    for label, path, keys in EVIDENCE_TIME_SOURCES:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        values = [data.get(key) for key in keys if isinstance(data.get(key), str)]
        if values:
            times[label] = values
    return times


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-meta", type=Path, help="scripts/check.py --json 生成的记录")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()

    steps, isolated = load_check_steps()
    meta = None
    if args.check_meta and args.check_meta.exists():
        meta = json.loads(args.check_meta.read_text(encoding="utf-8"))
    step_times = {}
    if meta:
        for item in meta.get("steps", []):
            step_times[item["name"]] = (item.get("finished"), item.get("seconds"), item.get("status"), item.get("exit"))

    rows = []
    for name, command, env in steps:
        script = next((part for part in command if part.startswith("apitest/")), None)
        purpose = first_doc_line(ROOT / script) if script else ""
        if name == "openspec-validate":
            purpose = "全部规约与变更严格校验"
        elif name == "layering":
            purpose = "后端分层依赖检查"
        elif name == "secret-scan":
            purpose = "密钥与敏感信息扫描"
        elif name == "fe-typecheck":
            purpose = "前端 TypeScript 类型检查"
        executed = step_times.get(name)
        rows.append({
            "入口": "make check",
            "命令": " ".join(command),
            "作用": purpose,
            "前置": "backend/.venv、frontend/node_modules、openspec CLI" if isolated else "同左",
            "写入范围": "只读；临时库/临时目录" if isolated else "只读",
            "预期退出码": "0",
            "上次可核实": f"{executed[0]}（{executed[1]}s，{executed[2]}，exit={executed[3]}）" if executed else "未知",
            "证据": "reports/lesson-10/<run-id>/gates/check-meta.json",
        })

    security_meta = None
    security_run = ROOT / "reports/security-evidence/run.json"
    if security_run.exists():
        security_meta = json.loads(security_run.read_text(encoding="utf-8"))
    rows.append({
        "入口": "make check-security",
        "命令": "backend/.venv/bin/python scripts/security_precheck.py",
        "作用": "密钥扫描、接口安全探针、npm/pip/mcp 依赖漏洞与例外校验",
        "前置": "网络可达 npm/PyPI 漏洞库；Docker 运行时用于容器日志扫描",
        "写入范围": "reports/security-evidence/（覆盖固定证据文件）",
        "预期退出码": "0；红项/阻断为 1",
        "上次可核实": f"{security_meta.get('started')} → {security_meta.get('finished')}（exit={security_meta.get('exit')}，{security_meta.get('status')}）" if security_meta else "未知",
        "证据": "reports/security-evidence/run.json",
    })

    for probe in sorted((ROOT / "apitest").glob("probe_*.py")):
        rows.append({
            "入口": "安全/模型探针",
            "命令": f"backend/.venv/bin/python {probe.relative_to(ROOT)}",
            "作用": first_doc_line(probe),
            "前置": "临时库或运行中实例；部分需真实模型 Key",
            "写入范围": "按脚本参数，通常写临时目录",
            "预期退出码": "0",
            "上次可核实": "未知",
            "证据": "reports/lesson-10/<run-id>/probes/",
        })

    rows.append({
        "入口": "异步三判据",
        "命令": "backend/.venv/bin/python scripts/reproduce_async_grading.py --image campusclaw-lesson10-<run-id>:local --output-prefix lesson10-<run-id>-",
        "作用": "真实 RabbitMQ + 假模型：A 提交不等待 / B 恢复 / C 幂等",
        "前置": "Docker；独立项目名与端口；镜像标签",
        "写入范围": "独立 Compose 项目与输出前缀",
        "预期退出码": "0",
        "上次可核实": "历史记录见 reports/async-grading/history-real-broker-result.json；本课需重跑",
        "证据": "reports/lesson-10/<run-id>/async/",
    })

    for name, command, purpose in [
        ("Compose 配置", "docker compose config --quiet", "合成配置校验，不启动服务"),
        ("七服务启动", "docker compose up -d", "按 README 前置启动 nginx/backend/frontend/mcp-tools/rabbitmq/dispatcher/worker"),
        ("服务状态", "docker compose ps", "实际容器与健康状态"),
        ("入口健康", "GET /api/health", "数据库可读、MCP 连通、模型配置状态"),
    ]:
        rows.append({
            "入口": "部署与就绪",
            "命令": command,
            "作用": purpose,
            "前置": "根目录 .env、独立数据目录与端口",
            "写入范围": "Compose 项目与挂载卷",
            "预期退出码": "0 / 200",
            "上次可核实": "2026-11-14T07:33Z 启动（见 reports/boot-reproduce.md）",
            "证据": "reports/boot-reproduce.md",
        })

    for name, command, purpose in [
        ("CI 双门禁", "GitHub Actions：make check 与 make check-security 并列", "远端同命令门禁"),
        ("三接口压测", "k6 run apitest/load/lesson10.js", "接收/查询/检索分档吞吐、P95、错误率"),
        ("观测采集", "python scripts/observability/collect.py --once", "把现有审计/任务数据转 Prometheus 指标"),
        ("告警演练", "连续失败注入并经 Alertmanager 送达", "真实 Firing 与收信"),
        ("索引迁移", "数据规范扩→迁→缩复验", "至少一项索引改进与兼容复验"),
    ]:
        rows.append({
            "入口": "本课新增",
            "命令": command,
            "作用": purpose,
            "前置": "见对应任务",
            "写入范围": "按任务说明",
            "预期退出码": "0",
            "上次可核实": "未实施" if not command.startswith("k6") else "未实施",
            "证据": "reports/lesson-10/<run-id>/",
        })

    lines = [
        "# 第10课命令盘点",
        "",
        f"- 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",
        f"- 提交：{meta.get('git_head', '未知') if meta else '未知'}",
        "- 说明：只列实际存在或本课明确新增的入口；“上次可核实”只采信证据文件中的时间字段，找不到写“未知”，不用 mtime 代替。",
        "",
        "| 入口 | 命令 | 作用 | 前置 | 写入范围 | 预期退出码 | 上次可核实执行（UTC） | 证据 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]).replace("|", "\\|") for key in
                                      ("入口", "命令", "作用", "前置", "写入范围", "预期退出码", "上次可核实", "证据")) + " |")
    lines.append("")
    lines.append("## 未纳入本次盘点的条目")
    lines.append("")
    lines.append("- 在线接口全量 `apitest/run_all.py`：需要运行中实例、固定身份与已索引材料，尚未在隔离环境重跑。")
    lines.append("- 真实模型质量与真实用户会话：不属于可重复门禁，单独在技能抽查与反馈报告中记录。")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写入 {args.out.relative_to(ROOT)}（{len(rows)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
