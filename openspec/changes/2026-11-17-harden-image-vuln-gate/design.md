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
