## MODIFIED Requirements

### Requirement: 越权处理与审计日志

当用户尝试访问无权限的页面或接口时，前端 MUST 跳转到 403 无权限提示页。后端 MUST 返回 403 Forbidden 并记录审计日志。未登录访问受保护接口 MUST 返回 401 并记录审计日志。按资源 ID 跨班取数 MUST 返回 404 并记录审计日志（见 class-data-isolation 规约）。审计日志 MUST 包含七列字段：actor（操作人 user_id）、created_at（操作时间）、action（操作类型，如 grade.write、skill.invoke、config.update）、object（操作对象的数据行 id）、status（结果状态或 HTTP 状态码）、skill_id（技能标识，非技能操作置空）、usage（用量与耗时，含 tokens 与 duration_ms，非模型调用置空）；同时保留 role、request_path、method、ip_address 辅助字段。被拒绝的请求（401/403/404）MUST 同样落一条审计记录。日志内容 MUST 经转义与截断（字段长度上限、只记 id 不记原文），MUST NOT 记录令牌、口令或用户提交的正文。审计日志 MUST NOT 影响主请求的响应性能（异步写入）。日志查询接口 MUST 仅教师可访问，学生 MUST NOT 查看审计日志。

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

#### Scenario: 技能调用审计日志七列齐全

- **WHEN** 学生命中技能并完成一次工具调用
- **THEN** 审计日志记录包含 actor、created_at、action=skill.invoke、object（会话/提交 id）、status、skill_id、usage（tokens 与 duration_ms）

#### Scenario: 审计日志内容转义与截断

- **WHEN** 操作对象字段包含换行符、引号或超长文本
- **THEN** 日志行仍为一条完整 JSON，换行与引号被转义，超长字段被截断，不破坏结构

#### Scenario: 审计日志异步写入不影响响应性能

- **WHEN** 越权请求触发审计日志写入
- **THEN** 审计日志写入为异步操作，不阻塞响应的返回，用户无感知延迟

#### Scenario: 学生不可查看审计日志

- **WHEN** 学生令牌请求审计日志查询接口
- **THEN** 后端返回 403 Forbidden，不返回任何日志数据

受保护请求返回 401/403/404 MUST 留审计；401 未解析有效身份时 actor/class_id 为 null，不凭客户端伪造身份归班。身份只使用服务端已验证的当前用户；匿名日志不暴露给班主任本班查询。action/object_id MUST 使用路由模板与实际资源编号，不记录正文或任意路径文本。技能路径写入 skill.invoke、会话 id、skill_id、duration_ms；tokens 保存决策轮返回用量，未返回时为 null。查询 MUST 返回已有 action/object_id/skill_id/duration_ms/tokens 五列，继续限制为本班班主任；学生和他班教师不得读取。

#### Scenario: 未登录请求留匿名审计
- **WHEN** 无令牌或无效令牌请求受保护接口
- **THEN** 返回 401，落匿名 401 记录且 action 可识别；班主任查询不会获得其他范围的匿名日志

#### Scenario: 技能审计字段查询与范围
- **WHEN** 学生完成或被拒一次技能工具调用，本班班主任查询审计
- **THEN** 返回 action/object_id/skill_id/duration_ms/tokens，值匹配调用；学生查询 403、他班班主任不能看到该行
## ADDED Requirements

### Requirement: 状态变更接口 CSRF 防护

所有状态变更接口（POST/PUT/DELETE）MUST 校验一次性 CSRF 令牌，令牌缺失或不匹配 MUST 返回 403 Forbidden。会话 Cookie（如 Refresh Token）MUST 标记 SameSite=Lax 或更严格，MUST NOT 使用 SameSite=None 且无 Secure。CSRF 令牌 MUST 与会话绑定，每次会话生成，服务端校验后不重用。

#### Scenario: 缺少 CSRF 令牌的写请求被拒

- **WHEN** 已登录用户通过跨站表单伪造提交配置修改请求，未携带 CSRF 令牌
- **THEN** 后端校验令牌缺失，返回 403 Forbidden，数据无变化

#### Scenario: CSRF 令牌不匹配被拒

- **WHEN** 已登录用户提交写请求，携带的 CSRF 令牌与会话不匹配
- **THEN** 后端返回 403 Forbidden，数据无变化

#### Scenario: 合法 CSRF 令牌写请求通过

- **WHEN** 已登录用户从本站页面提交写请求，携带与会话匹配的 CSRF 令牌
- **THEN** 后端校验通过，正常处理请求

#### Scenario: 会话 Cookie 标记 SameSite

- **WHEN** 后端设置 Refresh Token Cookie
- **THEN** Cookie 携带 SameSite=Lax（或 Strict）属性，本地开发未启用 HTTPS 时 MUST NOT 使用 SameSite=None
