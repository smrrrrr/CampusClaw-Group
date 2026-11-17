## MODIFIED Requirements

### Requirement: 越权处理与审计日志

当用户尝试访问无权限的页面或接口时，前端 MUST 跳转到 403 无权限提示页。后端 MUST 返回 403 Forbidden 并记录审计日志。未登录访问受保护接口 MUST 返回 401 并记录审计日志。按资源 ID 跨班取数 MUST 返回 404 并记录审计日志（见 class-data-isolation 规约）。审计日志 MUST 包含七列字段：actor（操作人 user_id）、created_at（操作时间）、action（操作类型，如 grade.write、skill.invoke、config.update）、object（操作对象的数据行 id）、status（结果状态或 HTTP 状态码）、skill_id（技能标识，非技能操作置空）、usage（用量与耗时，含 tokens 与 duration_ms，非模型调用置空）；同时保留 role、request_path、method、ip_address 辅助字段。被拒绝的请求（401/403/404）MUST 同样落一条审计记录。日志内容 MUST 经转义与截断（字段长度上限、只记 id 不记原文），MUST NOT 记录令牌、口令或用户提交的正文。审计日志 MUST NOT 影响主请求的响应性能（异步写入）。日志查询接口 MUST 仅教师可访问，学生 MUST NOT 查看审计日志。

**字段长度上限与清洗（本次补充，MUST）**：审计文本字段在入库前 MUST 由 `write_audit_log` 统一清洗，调用方不得依赖各自的截断逻辑保证合规。上限与模型列宽一致：`action` 64、`object_id` 128、`skill_id` 64、`request_path` 256、`ip_address` 64、`role` 20、`subject` 32 字符。超长值 MUST 截断到上限，不追加省略标记（避免污染可精确匹配的 id 值）。控制字符（U+0000–U+001F 与 U+007F）MUST 替换为空格。`None` MUST 保持 `None`，MUST NOT 转成字符串。截断与清洗 MUST NOT 改变正常长度字段的值。

#### Scenario: 前端越权跳转 403 页面

- **WHEN** role=student 的用户尝试访问 /teacher/* 路由，当前页会话角色校验拒绝
- **THEN** 前端重定向到 /403 无权限提示页，页面展示"您无权访问该页面"

#### Scenario: 后端越权返回 403 并记录审计日志

- **WHEN** role=student 的用户调用教师专用接口，get_current_teacher 依赖校验失败
- **THEN** 后端返回 403 Forbidden 响应，同时异步写入一条 AuditLog 记录（含 actor、created_at、action、object、status=403、skill_id 为空、usage 为空、role、request_path、method、ip_address）

#### Scenario: 未登录访问受保护接口返回 401 并记日志

- **WHEN** 未携带令牌的请求访问受保护业务接口
- **THEN** 后端返回 401 Unauthorized，异步写入一条审计记录（status=401，actor 为匿名）

#### Scenario: 跨班按 ID 取数返回 404 并记日志

- **WHEN** 学生请求不属于本班的资源 ID
- **THEN** 后端返回 404 Not Found，异步写入一条审计记录（status=404）

#### Scenario: 教师跨班操作记录审计日志

- **WHEN** 教师尝试操作非任教班级的数据，后端校验 class_id 不在 teaching_classes 中
- **THEN** 后端返回 403 Forbidden，同时异步写入一条 AuditLog 记录

#### Scenario: 超长字段入库前截断到列宽

- **WHEN** 调用 `write_audit_log` 时 `object_id` 为 500 个字符，其余字段正常
- **THEN** 落库的 `object_id` 长度为 128，值为原字符串前 128 个字符，不含截断标记；同一条记录的其他字段不受影响

#### Scenario: 控制字符被替换，日志保持单行

- **WHEN** 调用 `write_audit_log` 时 `object_id` 含换行符 `\n`、制表符 `\t` 与空字符 `\x00`
- **THEN** 落库值中这些字符均被替换为空格，不含任何 U+0000–U+001F 控制字符

#### Scenario: 正常字段与 None 不被改变

- **WHEN** 调用 `write_audit_log` 时 `object_id="42"`、`skill_id=None`
- **THEN** 落库 `object_id` 仍为 `"42"`，`skill_id` 仍为 `None`（不是字符串 `"None"` 或空串）

#### Scenario: 审计日志异步写入不影响响应性能

- **WHEN** 越权请求触发审计日志写入
- **THEN** 审计日志写入为异步操作，不阻塞 403 响应的返回，用户无感知延迟

#### Scenario: 未登录请求留匿名审计

- **WHEN** 无令牌或无效令牌请求受保护接口
- **THEN** 返回 401，落匿名 401 记录且 action 可识别；班主任查询不会获得其他范围的匿名日志

#### Scenario: 技能审计字段查询与范围

- **WHEN** 学生完成或被拒一次技能工具调用，本班班主任查询审计
- **THEN** 返回 action/object_id/skill_id/duration_ms/tokens，值匹配调用；学生查询 403、他班班主任不能看到该行