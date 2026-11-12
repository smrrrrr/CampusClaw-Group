## Why

第三轮安全评审发现机器门禁遗漏真实工具授权失败、审计缺项和 npm 漏报，并发现历史消息转义破坏公式。一次性修复本工作树已记录的评审问题，保留历史证据，避免以旧的绿色结果代替本次验证。

## What Changes

- SEC-08：使用服务端数据库身份，修复未定义 ctx；发现并保存保守的工具权限分类，重连不得降权为只读；补学生/教师对照、未知工具和 SSE 检查。
- SEC-07：记录 401；技能调用及拒绝日志填充 action/object_id/skill_id/duration_ms，tokens 记录决策轮返回用量，未返回时为 null；查询返回已有五列；审计写失败输出脱敏告警。
- npm 安全门禁保存包明细，按锁定版本及全部通告精确核对有效例外；未知、过期或格式错误不得放行。不升级任何依赖或编造风险豁免。
- 历史消息返回原始 Markdown，在既有 ReactMarkdown 渲染边界验证脚本不执行；修正下载注释和交接基线。
- 将缺失的提示注入实验改为仓库内可执行探针与实际 JSON 证据；全部问题清单见 design.md。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `mcp-tool-integration`：执行身份、工具分类和可观测审计失败。
- `rbac-role-permissions`：401 与技能审计字段、查询边界。
- `agent-assistant`：历史 Markdown 保真与安全渲染。

## Impact

仅修改 MCP 客户端/编排/相关路由、审计写入/查询、历史消息、安全门禁及直接相关检查与文档。不重构其他业务，不改提示词、模型参数、依赖版本、数据库表结构或教学数据。

用户本次明确授权代码修复及规约编写；不调用 OpenSpec apply/archive、不勾选 tasks、不同步主规约，不实现本范围以外的后续功能。所有修改保留在一个工作树，不推送。用户已在本机创建并切换 `fix/review-lesson09-all`；共享 Git 元数据超出代理可写边界，提交实际状态与验证记录在 validation.md。
