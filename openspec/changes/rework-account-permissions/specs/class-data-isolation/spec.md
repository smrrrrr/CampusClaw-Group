## ADDED Requirements

### Requirement: 一人一号班级上下文

学生业务上下文 MUST 绑定当前登录学生本人及其班级，MUST NOT 提供家长代登录、选择孩子或切换孩子流程。退出登录 MUST 清空内存中的用户和班级身份；重新登录 MUST 从新会话设置当前学生、教师任教班级、学科与班主任班级，避免复用另一账号的页面上下文。

#### Scenario: 学生登录建立本人班级上下文

- **WHEN** 李明以学号 `20260001` 登录成功
- **THEN** 当前学生为李明、class_id=101，不提供同手机号学生选择或孩子切换入口

#### Scenario: 登出后重新登录使用新的班级范围

- **WHEN** 当前账号登出后另一个账号登录
- **THEN** 会话状态以新登录返回的身份和班级字段初始化，不沿用前一账号的身份

## MODIFIED Requirements

### Requirement: 前端班级数据渲染控制

前端 MUST 根据会话中的班级权限显示数据。学生 MUST NOT 获得任意班级选择器；请求可以携带本人 `class_id` 用于一致性校验，后端 MUST 仍以 JWT 的班级为准。教师 MUST 能在 `teaching_classes` 中选择任教班级；班主任入口 MUST 固定到 `homeroom_class_id`，任教班级切换 MUST NOT 改变带班班级或隐藏班主任导航。URL 和请求中的 class_id MUST NOT 作为授权依据。

#### Scenario: 学生资料请求使用本人班级

- **WHEN** class_id=101 的学生访问 `/materials`
- **THEN** 前端请求本班资料，后端校验目标为 101，前端不提供跨班切换

#### Scenario: 任课切班不改变带班上下文

- **WHEN** 高二（1）班班主任切换任课班级到高二（2）班
- **THEN** 任课内容针对 102，班主任入口仍指向 101

#### Scenario: 篡改 class_id 不能扩权

- **WHEN** 用户在 URL 或请求参数里传入非授权班级
- **THEN** 后端按 JWT 范围拒绝，前端参数不授予额外权限

### Requirement: 学生班级数据范围控制

学生MUST 只能查看和操作自己所在班级（class_id）的数据。学生 MUST NOT 查看其他班级的任何信息。class_id 来源于 JWT Payload，后端 MUST NOT 信任请求参数中的 class_id。

#### Scenario: 学生查看本班资料成功

- **WHEN** 学生 class_id=101，请求查看资料列表
- **THEN** 系统返回 class_id=101 的资料，不返回其他班级的资料

#### Scenario: 学生尝试查看其他班级资料被拒

- **WHEN** 学生 class_id=101，尝试在请求参数中传入 class_id=102 查看资料
- **THEN** 系统以 JWT 中的 class_id=101 为准，返回 403 Forbidden

#### Scenario: 学生提交作业关联到本班

- **WHEN** 学生 class_id=101 提交一份作业
- **THEN** 系统将作业提交记录关联到 class_id=101，不允许篡改为其他班级

## REMOVED Requirements

### Requirement: 多娃切换班级上下文重载

**Reason**: 已移除家长代登录、多娃绑定与切换孩子功能。

**Migration**: 学生使用本人学号密码登录；上下文遵循“一人一号班级上下文”。
