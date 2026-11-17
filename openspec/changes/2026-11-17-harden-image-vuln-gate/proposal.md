## Why

PR #3 的镜像门禁会把空 JSON 当成零漏洞，也会用同一 CVE 的书面例外放行未登记的软件包。两种输入都已在原提交上复现通过。

## What Changes

- 要求镜像门禁验证报告格式，CI 明确传入三个镜像的报告。
- HIGH 只在 CVE、软件包及例外复查日期均满足时放行。保留 CRITICAL 拒绝规则。
- 扩展现有门禁回归并记录先红后绿。统一回归子进程的 UTF-8 编码。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `runtime-reliability`：补充构建镜像进入交付流程前的扫描判据。

## Impact

涉及 Trivy 门禁脚本、镜像构建工作流、对应回归和验收报告。
