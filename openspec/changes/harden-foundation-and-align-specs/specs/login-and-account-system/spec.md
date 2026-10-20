## ADDED Requirements

### Requirement: 刷新页面恢复完整会话

Access Token MUST 仍只存客户端内存。页面刷新后 AuthGate MUST 先调用 HttpOnly Cookie 的刷新接口，成功时恢复角色、学生本人信息、任教班级、学科、带班班级和改密状态，再加载业务界面；刷新失败时清除辅助角色 Cookie 并跳转登录页。刷新响应 MUST 包含完整 user 信息。

#### Scenario: 教师刷新后保留页面

- **WHEN** 已登录教师在助手配置或审计页刷新且 Refresh Cookie 有效
- **THEN** 恢复完整教师身份，保留当前 URL 和菜单，不要求再次登录

#### Scenario: 学生刷新后仍指向本人

- **WHEN** 已登录学生刷新且 Refresh Cookie 有效
- **THEN** 恢复本人 id、姓名、class_id；若仍需初始改密则进入改密页

#### Scenario: 刷新失败回登录

- **WHEN** Refresh Cookie 缺失或无效
- **THEN** 业务页面不展示，清理辅助 Cookie 并回到登录页

### Requirement: 学生 CSV 导入的双向班级权限

教师导入 MUST 同时校验已有学生的原班级与 CSV 指定的目标班级均在 teaching_classes 内。省略目标班级时，已有学生 MUST 仍通过原班级校验；新学生缺少班级 MUST 返回 400。未知班级、非任教班级、原班级为空或不在任教范围的学生 MUST 返回 403。文件中任一行失败 MUST 整批回滚，MUST NOT 部分更新。

#### Scenario: 修改非任教班级学生被拒绝

- **WHEN** 仅任教 102 的教师导入属于 101 的已有学号，包括省略班级或将目标写成 102
- **THEN** 返回 403，原账号资料和班级均保持不变

#### Scenario: 导入非任教目标班级被拒绝

- **WHEN** 任教 101、102 的教师向 103 或不存在的班级导入学生
- **THEN** 返回 403，不创建账号或班级

#### Scenario: 合法行之后出现越权行

- **WHEN** 一份 CSV 前面的行合法，后面的行越权
- **THEN** 整批回滚，之前的合法行也不提交

#### Scenario: 任教范围内创建或更新

- **WHEN** 新学生目标班级或已有学生的原班级与目标班级全部属于任教范围
- **THEN** 允许创建或更新；新账号使用初始密码且需要改密

## MODIFIED Requirements

### Requirement: 封闭注册与一人一号账号预置

系统 MUST 完全禁止自助注册。系统仅包含教师（teacher）和学生（student）两种角色，MUST NOT 提供任何公开注册入口。教师和学生账号由管理员或教师通过 CSV 批量导入预置。教师账号 MUST 携带学科（subject）与可选的班主任班级（homeroom_class_id）身份字段，用于教研隔离与班主任特权判定。学生账号 MUST 一人一号：CSV 导入时可填写手机号作为联系方式，手机号允许作为多个账号的普通联系方式，MUST NOT 用于家长代登录或账号切换。CSV 表头 MUST 包含学号，姓名和手机号为可选字段；新学生 MUST 填写一个教师已获授权的现有班级，MUST NOT 借导入新建班级。

#### Scenario: 未登录用户无法注册

- **WHEN** 未登录用户访问系统任意页面
- **THEN** 系统重定向到登录页，页面上不显示任何注册链接或按钮

#### Scenario: 教师通过 CSV 批量导入学生含手机号

- **WHEN** 教师上传 CSV 文件，某行包含学号 20260001、学生姓名李明、手机号 13800001111，以及教师任教范围内的班级
- **THEN** 系统创建学号为 20260001 的学生账号，初始密码按规则生成，并将手机号 13800001111 作为联系方式写入该账号的 phone 字段

#### Scenario: 预置教师账号携带学科与班主任身份

- **WHEN** 管理员预置教师账号，指定学科为 math、班主任班级为 101
- **THEN** 系统记录 subject=math、homeroom_class_id=101，该教师教研资料按 math 隔离、拥有一班班主任特权

#### Scenario: 多个学生使用相同联系方式

- **WHEN** CSV 中两行学生填写相同手机号
- **THEN** 在学号和班级权限均合规时允许保存相同手机号；各账号仍以自己的学号和密码独立登录

#### Scenario: CSV 缺少学号列被拒绝

- **WHEN** 教师上传的 CSV 文件缺少"学号"列
- **THEN** 系统拒绝导入并返回明确的错误提示，不创建任何账号

### Requirement: 强制首次改密（无验证码例外）

所有新建业务账号和被重置密码的账号 MUST 将 must_change_password 设为 true；显式视为已改密的开发教师种子可使用 false，此例外仅适用于开发种子。FastAPI 业务依赖 MUST 从数据库读取当前 must_change_password，并统一拦截所有资料、教师和学生业务请求；为 true 时 MUST 返回 403 及“请先修改初始密码”。登录、刷新、改密及登出属于认证自身流程，MUST 允许正常执行。班主任重置密码后，旧 Access Token 的业务访问 MUST 立即被拦截。用户成功修改密码后 MUST 将 must_change_password 设为 false。验证码登录方式已被移除，不存在"验证码登录不触发强制改密"的例外。

#### Scenario: 首次密码登录被拦截要求改密

- **WHEN** 用户使用初始密码登录成功，must_change_password 为 true
- **THEN** 系统跳转到修改密码页面，不允许访问其他业务页面

#### Scenario: 未改密时访问业务接口被拦截

- **WHEN** 用户 must_change_password 为 true，携带有效 Access Token 调用非改密的业务接口
- **THEN** 系统返回"请先修改初始密码"的提示，拒绝处理该业务请求

#### Scenario: 改密成功后恢复正常访问

- **WHEN** 用户在改密页输入符合策略的新密码并提交成功
- **THEN** 系统将 must_change_password 设为 false，重新签发不含改密标记的 Token，用户可正常访问业务接口
