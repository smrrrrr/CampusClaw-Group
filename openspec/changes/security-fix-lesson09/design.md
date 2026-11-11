## Context

第8课安全自查发现的红项与盲区需要修复。当前实现状态（见 proposal.md 动机）：

- `_check_material_access`（materials.py:107）等 fetch-then-check 函数对跨班资源返回 **403**，课程口径要求 **404**。
- `AuditLog` 表（models.py:91）字段：user_id、role、subject、class_id、request_path、method、status_code、ip_address、created_at。缺 operation type、object、skill_id、duration、tokens。
- `McpToolCall` 表（models.py:639）字段：class_id、server_id、server_name、tool_name、tool_ref、status、user_id、conversation_id、round、detail、created_at。缺 **skill_id、duration_ms、tokens**——这是 SEC-07 的红项。
- MCP 工具执行循环（mcp_orchestrator.py）目前校验工具在候选集内、参数合规，但**未在执行前校验发起者对写入操作的授权**（SEC-08）。
- 检索查询（services.py）需确认全部参数化；讲义标题等文本字段输出未做服务端转义（XSS 盲区）；写接口无 CSRF 令牌校验（CSRF 盲区）。
- `make check-security` 尚未接入 gitleaks 与依赖审计（SEC-05/06）。

## Goals / Non-Goals

**Goals:**
- 跨班按 ID 取数统一返回 404（fetch-then-check），参数篡改仍 403。
- 审计日志与 MCP 调用记录补齐七列字段，被拒绝请求也落日志。
- MCP 工具执行前逐次鉴权，模型决策不豁免。
- SQL/XSS/CSRF 三条注入反例用例进 `apitest/cases/` 并为绿。
- `make check-security` 接入密钥扫描与依赖审计。

**Non-Goals:**
- 不重构整体权限架构，只把判定补到正确的层。
- 不改动业务功能行为（除授权口径 403→404 外）。
- 不引入新的鉴权框架或外部安全服务。
- SEC-05/06 的依赖升级若涉及 breaking change 不在本次范围，登记处置。

## Decisions

### D1: 跨班取数 403→404 的判定位置

**决策**：fetch-then-check 模式的资源访问（按 ID 取单条资源，如材料、提交、会话）返回 **404**；参数篡改（URL/Payload 中 class_id 与 JWT 不符）仍返回 **403**。

**理由**：404 不区分"不存在"与"无权访问"，避免通过状态码差异泄露资源存在性。参数篡改是明确的越权尝试，403 语义更准确且已有审计。

**实现**：修改 `_check_material_access` 及其他按 ID 取数的鉴权函数，将归属不匹配的 `HTTP_403_FORBIDDEN` 改为 `HTTP_404_NOT_FOUND`；列表查询的 class_id 参数校验保持 403。同时确认检索侧向量库查询与 SQL 查询都带班级过滤（双侧过滤）。

**替代方案**：全部统一 404。否决——参数篡改场景 403 更能体现"你在越权"并触发审计告警，且现有规约明确参数篡改返回 403。

### D2: 审计日志与 MCP 调用记录的字段扩展

**决策**：
- `McpToolCall` 表新增 `skill_id`（String, nullable）、`duration_ms`（Integer, nullable）、`tokens`（Integer, nullable）三列。
- `AuditLog` 表新增 `action`（String, nullable）、`object_id`（String, nullable）、`skill_id`（String, nullable）、`duration_ms`（Integer, nullable）、`tokens`（Integer, nullable）五列。
- 提供迁移脚本（`scripts/migrate_audit_fields.py`）用 `ALTER TABLE ADD COLUMN`，SQLite 支持。
- `write_audit_log` 函数签名扩展，新字段可选；非技能操作传空。

**理由**：SEC-07 要求七列可回查。MCP 调用记录缺 skill/duration/tokens 是直接红项；通用审计日志需记录操作类型与对象以支持回查。新增列全部 nullable，不破坏已有写入。

**替代方案**：新建独立的 operation_log 表。否决——已有 AuditLog 表承担此职责，扩展列比新建表更简单且查询统一。

### D3: MCP 工具执行层鉴权

**决策**：在 `mcp_orchestrator.py` 的工具执行循环中，执行 `tools/call` 前增加一步授权检查：若工具属于写入类（如批改写入、配置修改），校验发起者（会话绑定学生）是否有对应权限。学生无权执行写入操作时拒绝执行，记为 denied 并写审计日志。

**理由**：SEC-08 要求"模型说可以不等于授权"。当前候选集校验只确认工具在技能绑定范围内，不确认用户有权执行该操作。写入类工具必须额外校验发起者身份与资源归属。

**实现**：为 MCP 工具定义 `write` 标记（在工具发现缓存中标记），执行前检查当前用户角色与资源归属。本期内置工具（formula_hint、unit_convert）均为只读，标记为 read；教师通过技能配置的自定义工具若涉及写入，需在登记时声明。

**替代方案**：在技能保存时校验工具类型。否决——保存期校验不能防止运行时权限变更，必须在执行时逐次校验。

### D4: 注入防护三件套

**SQL 注入**：审查 services.py 中所有检索查询，确认使用参数化绑定（SQLAlchemy `filter(Model.col == param)` 形式）。对排序列名使用白名单枚举（`{"created_at", "title", ...}`），命中白名单外返回 400。**不新增框架**，只在现有查询入口加校验。

**XSS**：在 FastAPI 响应序列化层，对用户提交的文本字段（Material.title、Material.description 等）使用 `html.escape()` 转义。不依赖前端转义。转义在服务端输出层统一处理。

**CSRF**：
- 会话 Cookie（Refresh Token）设置 `SameSite=Lax`。
- 状态变更接口（POST/PUT/DELETE）增加 CSRF 令牌校验：登录时生成令牌存入 HttpOnly Cookie + 返回给前端；写请求须在 Header 携带 `X-CSRF-Token`，服务端校验与会话 Cookie 中的令牌一致。
- 读接口（GET）不校验 CSRF。

**理由**：三处盲区各有标准防护方式，实现成本低且不影响现有业务。白名单枚举比正则黑名单更安全。

### D5: `make check-security` 门禁

**决策**：Makefile 新增 `check-security` 目标，串联：
1. `gitleaks detect --source . --no-banner`（密钥扫描，0 命中才通过）
2. `npm audit --audit-level=high`（前端依赖，无高危才通过）
3. `pip-audit`（后端依赖，无高危才通过或有登记豁免）
4. `scripts/security_precheck.py`（接口安全探针）

任一退出码非 0 则整体非 0。在 README.md 注明入口。留一次先红后绿证据归档 `reports/gate-red-green.md`。

**理由**：课程要求密钥扫描与依赖审计常驻门禁。gitleaks 是业界标准密钥扫描工具；npm audit / pip-audit 是官方依赖审计。

## Risks / Trade-offs

- **[404 口径变更可能影响前端]** → Mitigation：前端已按"失败"处理，不区分 403/404；审查前端对 404 的处理，确保不暴露资源存在性。
- **[审计日志表结构变更影响历史数据]** → Mitigation：新增列全部 nullable，历史记录新字段为空，查询时用 COALESCE 或前端兼容空值。
- **[CSRF 令牌影响现有前端写请求]** → Mitigation：登录响应已返回令牌，前端在写请求 Header 自动携带；GET 请求不受影响。提供兼容期。
- **[依赖升级可能引入 breaking change]** → Mitigation：优先升级 patch/minor 版本；major 版本升级或无补丁的漏洞写成登记条目，注明降险措施。
- **[授权收紧可能误伤正常异步任务]** → Mitigation：回归必须跑上一课三条异步判据；GradeTask 等后台任务使用服务端身份，不走用户鉴权路径。

## Migration Plan

1. 运行迁移脚本新增 AuditLog 和 McpToolCall 列（可回滚：删除列不支持 SQLite，需重建表——本次只加列不删列，无回滚风险）。
2. 修改 fetch-then-check 鉴权函数的状态码。
3. 扩展 write_audit_log 和 MCP 调用记录写入函数。
4. 增加 MCP 工具执行授权检查。
5. 增加 XSS 转义、CSRF 校验、SQL 白名单。
6. 新增 `make check-security` 目标。
7. 回归测试：`make check` + 异步判据 + 注入三件套。

**回滚策略**：每步单独提交，可逐 commit revert；表结构变更只加列，不影响已有数据。
