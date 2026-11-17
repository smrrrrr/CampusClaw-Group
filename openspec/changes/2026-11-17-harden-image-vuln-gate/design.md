## Context

Trivy 扫描三份镜像并输出 JSON。门禁聚合报告，再用书面例外判定漏洞。现有流程用文件通配符，也会把不含任何报告元数据的 JSON 当成空结果。

## Goals / Non-Goals

校验扫描报告和软件包例外的适用范围。业务接口、数据、依赖版本与例外表沿用当前版本。

## Decisions

- CI 逐个传入 backend、frontend、mcp-tools 的报告路径，并保留 `pipefail`。门禁采用 Trivy v2 容器报告的版本、类型和镜像名识别报告，拒绝重复镜像名和错误结构。合法的 Trivy 镜像报告可以省略空 `Results`，目标也可以省略空 `Vulnerabilities`。
- 软件包使用 Trivy 记录的 `PkgName` 与书面例外的 `packages` 精确比较。原有 CRITICAL 拒绝规则和复查日期边界延续。
- 回归沿用现有自动收集入口。隔离子进程使用 `-X utf8`，捕获端也显式用 UTF-8。

## Risks / Trade-offs

Trivy 更新输出版本时需先核对格式并更新判据。测试使用临时合成报告验证正常与失败路径，历史扫描样例另供格式兼容复核。

## 运行镜像中的 infocmp

PR #5 首次远端镜像检查在 backend 和 mcp-tools 各拦下一个 `ncurses-bin` 的 HIGH。Debian trixie 当前包仍受 CVE-2025-69720 影响。受影响的入口是 `/usr/bin/infocmp`，项目运行不使用该工具。两个 Dockerfile 在系统层升级后移除该程序，保留 Debian 软件包和原始 Trivy 报告。

只对 `CVE-2025-69720`、`ncurses-bin`、登记版本和未过期例外增加缓解判定。CI 明确传入它刚构建的两个镜像。门禁将 Trivy 的镜像 ID 与本地镜像核对，再用该 ID 创建无网络、只读的临时容器，确认已知路径和 PATH 上均无 `infocmp`。无法检查、镜像 ID 不一致、版本变化或程序仍在时均阻断。Debian 发布修复后，移除该条件例外并重建。
