## ADDED Requirements

### Requirement: 镜像漏洞门禁校验报告及例外范围

CI MUST 提交 backend、frontend 和 mcp-tools 的三份镜像扫描报告。门禁 MUST 拒绝缺失、格式错误或同一镜像重复的报告。CRITICAL MUST 失败。HIGH 仅当 CVE 与软件包均命中同一条未过期书面例外时 MAY 放行。

#### Scenario: 合法的零漏洞扫描报告

- **WHEN** 提交包含镜像标识的合法 Trivy 报告，结果为空或省略且没有未获准的漏洞
- **THEN** 门禁退出 0

#### Scenario: 特定镜像中验证 infocmp 已移除

- **WHEN** 后端或 MCP 的镜像报告仍标记 `ncurses-bin` 的 `CVE-2025-69720`，且命中登记版本和有效期内的例外
- **THEN** 门禁仅在受检镜像与扫描镜像 ID 一致、确认 `infocmp` 不在运行文件系统的已知路径或 PATH 时允许继续
- **WHEN** 镜像 ID 不一致、检查无法完成或程序仍存在
- **THEN** 门禁退出 1，Trivy 原始报告保留

#### Scenario: 报告缺失或无效

- **WHEN** 指定报告缺失、格式不符，或提交了同一镜像的重复报告
- **THEN** 门禁退出 2

#### Scenario: 软件包超出漏洞例外范围

- **WHEN** HIGH 漏洞的 CVE 已登记但扫描软件包不在同一条例外的包清单内
- **THEN** 门禁退出 1 并指出该软件包

#### Scenario: 按严重度及例外复查日期判定

- **WHEN** 发现 CRITICAL 或发现只匹配过期例外的 HIGH
- **THEN** 门禁退出 1
- **WHEN** 所有发现均符合判据且 HIGH 均命中有效例外
- **THEN** 门禁退出 0
