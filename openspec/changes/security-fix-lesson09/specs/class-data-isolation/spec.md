## MODIFIED Requirements

### Requirement: 跨班访问拦截与审计日志

当用户尝试篡改 URL 参数或 API Payload 中的 class_id 进行跨班访问时，后端 MUST 返回 403 Forbidden 并记录审计日志。当用户按资源 ID 取数（如讲义、作业提交、会话）且该资源不属于当前用户班级/任教范围时，后端 MUST 采用 fetch-then-check 模式，先按 ID 取行再校验归属，不属于则一律返回 404 Not Found（不区分"不存在"与"不是你的"，避免存在性泄露），并记录审计日志。审计日志 MUST 复用 RBAC 规约中的 AuditLog 表，包含 user_id、role、request_path、method、status_code、ip_address、created_at 字段。

#### Scenario: 篡改 URL 参数跨班访问被拦截

- **WHEN** 学生 class_id=101，尝试通过 URL 参数 ?class_id=102 访问其他班级资料列表
- **THEN** 后端校验 URL 参数中的 class_id=102 与 JWT 中的 class_id=101 不匹配，返回 403 Forbidden，记录审计日志

#### Scenario: 篡改 API Payload 中 class_id 被拦截

- **WHEN** 学生 class_id=101，尝试在 API 请求体中传入 class_id=102 提交作业
- **THEN** 后端校验请求体中的 class_id=102 与 JWT 中的 class_id=101 不匹配，返回 403 Forbidden，记录审计日志

#### Scenario: 按 ID 跨班取讲义返回 404

- **WHEN** 学生 class_id=101，请求 GET /api/materials/{id}，其中 id 属于班级 102 的讲义
- **THEN** 后端先按 id 取出行，校验该行 class_id=102 不在用户范围内，返回 404 Not Found，记录审计日志；响应不暴露该讲义是否存在

#### Scenario: 按 ID 跨班取作业提交返回 404

- **WHEN** 教师 teaching_classes=[101]，请求查看提交 id 属于班级 102 的作业
- **THEN** 后端 fetch-then-check 校验归属，不属于任教范围，返回 404 Not Found，记录审计日志

#### Scenario: 教师篡改 class_id 跨班访问被拦截

- **WHEN** 教师 teaching_classes=[101,102]，尝试在请求中传入 class_id=201 访问非任教班级数据
- **THEN** 后端校验 201 不在 teaching_classes 中，返回 403 Forbidden，记录审计日志

#### Scenario: 跨班访问审计日志记录完整

- **WHEN** 任何跨班访问被拦截时
- **THEN** 审计日志记录包含 user_id、role、request_path、method、status_code（403 或 404）、ip_address、created_at，异步写入不影响响应性能
