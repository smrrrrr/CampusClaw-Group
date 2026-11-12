## MODIFIED Requirements

### Requirement: 越权处理与审计日志

当用户尝试访问无权限的页面或接口时，前端 MUST 跳转到 403 无权限提示页。后端 MUST 返回 403 Forbidden 并记录审计日志。审计日志 MUST 包含字段：user_id、role、request_path、method、status_code、ip_address、created_at。审计日志 MUST NOT 影响主请求的响应性能（异步写入）。

#### Scenario: 前端越权跳转 403 页面

- **WHEN** role=student 的用户尝试访问 /teacher/* 路由，当前页会话角色校验拒绝
- **THEN** 前端重定向到 /403 无权限提示页，页面展示"您无权访问该页面"

#### Scenario: 后端越权返回 403 并记录审计日志

- **WHEN** role=student 的用户调用教师专用接口，get_current_teacher 依赖校验失败
- **THEN** 后端返回 403 Forbidden 响应，同时异步写入一条 AuditLog 记录（含 user_id、role、request_path、method、status_code=403、ip_address、created_at）

#### Scenario: 教师跨班操作记录审计日志

- **WHEN** 教师尝试操作非任教班级的数据，后端校验 class_id 不在 teaching_classes 中
- **THEN** 后端返回 403 Forbidden，同时异步写入一条 AuditLog 记录

#### Scenario: 审计日志异步写入不影响响应性能

- **WHEN** 越权请求触发审计日志写入
- **THEN** 审计日志写入为异步操作，不阻塞 403 响应的返回，用户无感知延迟

受保护请求返回 401/403/404 MUST 留审计；401 未解析有效身份时 actor/class_id 为 null，不凭客户端伪造身份归班。身份只使用服务端已验证的当前用户；匿名日志不暴露给班主任本班查询。action/object_id MUST 使用路由模板与实际资源编号，不记录正文或任意路径文本。技能路径写入 skill.invoke、会话 id、skill_id、duration_ms；tokens 保存决策轮返回用量，未返回时为 null。查询 MUST 返回已有 action/object_id/skill_id/duration_ms/tokens 五列，继续限制为本班班主任；学生和他班教师不得读取。

#### Scenario: 未登录请求留匿名审计
- **WHEN** 无令牌或无效令牌请求受保护接口
- **THEN** 返回 401，落匿名 401 记录且 action 可识别；班主任查询不会获得其他范围的匿名日志

#### Scenario: 技能审计字段查询与范围
- **WHEN** 学生完成或被拒一次技能工具调用，本班班主任查询审计
- **THEN** 返回 action/object_id/skill_id/duration_ms/tokens，值匹配调用；学生查询 403、他班班主任不能看到该行
