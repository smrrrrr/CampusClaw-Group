## MODIFIED Requirements

### Requirement: 前端路由级权限拦截

业务页面 MUST 在当前标签页的登录会话恢复完成后再判定页面角色并挂载业务内容。`/teacher` 及其子路径 MUST 仅允许 teacher，`/student` 及其子路径 MUST 仅允许 student，错误角色 MUST 进入 403 且不展示业务内容；会话恢复失败 MUST 回到登录页。共享且可改写的辅助角色提示 Cookie MUST NOT 作为页面放行或拒绝依据，即使其值来自其他标签页或已缺失。身份恢复期间及首次改密完成前 MUST 保留加载或改密流程；实际数据访问 MUST 继续由后端 JWT 与逐资源权限校验。

#### Scenario: 教师访问教师路由通过

- **WHEN** role=teacher 的用户访问 /teacher?workspace=teaching&view=students 页面
- **THEN** 当前页会话角色校验通过，正常渲染教师班级管理页面

#### Scenario: 学生访问学生路由通过

- **WHEN** role=student 的用户访问 /student?view=assistant 页面
- **THEN** 当前页会话角色校验通过，正常渲染学生资料页面

#### Scenario: 学生访问教师路由被拦截

- **WHEN** role=student 的用户尝试访问 /teacher?workspace=teaching&view=students 页面
- **THEN** 当前页会话角色校验拒绝，重定向到 403 无权限提示页

#### Scenario: 教师访问学生路由被拦截

- **WHEN** role=teacher 的用户尝试访问 /student?view=assistant 页面
- **THEN** 当前页会话角色校验拒绝，重定向到 403 无权限提示页

#### Scenario: 未登录用户访问业务路由重定向登录

- **WHEN** Access Token 缺失且会话恢复失败的用户访问 /teacher?workspace=teaching&view=students 或 /student?view=assistant
- **THEN** 当前页会话角色校验拒绝，重定向到登录页

#### Scenario: 双标签提示变化后的单科切班

- **WHEN** 持有有效教师会话的页面停留一班单科学情，另一标签页登录学生后，教师选择任教的二班
- **THEN** 仍保留 teaching 工作区及原单科视图，班级更新为二班并读取其本科目数据，不被共享角色提示误导到 403

#### Scenario: 辅助提示缺失但会话有效

- **WHEN** 当前页教师或学生会话有效，但浏览器辅助角色或登录提示缺失
- **THEN** 合法的本角色页面正常打开，不被提示缺失误导到登录页

#### Scenario: 伪造角色提示不赋予页面权限

- **WHEN** 当前实际会话为学生却带教师辅助提示，或实际会话为教师却带学生辅助提示，尝试打开对方的角色页面
- **THEN** 仍按实际会话跳转 403，业务子组件和数据均不向错误角色展示

#### Scenario: 刷新恢复后的角色仍须匹配

- **WHEN** 页面没有内存会话，通过有效刷新 Cookie 恢复得到学生身份但当前 URL 属于教师页面
- **THEN** 恢复期间只显示加载，身份恢复后进入 403，不先挂载教师业务内容；对应角色与 URL 匹配时正常加载

#### Scenario: 身份恢复前不显示业务内容

- **WHEN** 当前页缺少令牌或角色，正在恢复会话，或用户仍需首次改密
- **THEN** 不挂载业务子组件，恢复失败进入登录页，需要改密时优先进入改密页

#### Scenario: 角色目录按完整路径边界判断

- **WHEN** 校验 `/teacher`、`/teacher/quiz`、`/student` 与 `/student/…`，以及 `/materials` 和相似前缀的普通路径
- **THEN** 角色目录与其子路径按角色拦截，共用资料页允许两种有效角色；相似普通前缀不被误认作角色目录

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
