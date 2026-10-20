## ADDED Requirements

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

### Requirement: 开发种子账号与班级名称

开发种子 MUST 采用下表中的姓名、账号和班级；班级名称 MUST 包含末尾“班”字。学生初始密码 MUST 使用学校缩写 `thu` 加学号最后六位，MUST NOT 将 `20260001` 的后六位误算为 `000001`。

| 角色 | 姓名 | 账号 | 种子初始密码 | 任教或所属班级 | 班主任班级 | must_change_password |
| --- | --- | --- | --- | --- | --- | --- |
| 教师 | 张老师 | TEA001 | Teach@2026 | 101、102（数学） | 101 | false |
| 教师 | 李老师 | TEA002 | Teach@2026 | 101、102（物理） | 102 | false |
| 学生 | 李明 | 20260001 | thu260001 | 101 | 不适用 | true |
| 学生 | 王芳 | 20260002 | thu260002 | 102 | 不适用 | true |

班级 101 显示为“高二（1）班”，班级 102 显示为“高二（2）班”。这些密码仅为开发环境的种子初始值；用户改密后 MUST 以数据库当前密码为准。已有教师重跑种子 MUST 保留原密码；学生重跑种子会恢复上表密码并要求改密。完整种子脚本还会清理清单外的学生，MUST NOT 用作生产数据迁移或为查密码而运行。

#### Scenario: 李明初始密码按学号末六位生成

- **WHEN** 开发种子创建或重置学号 `20260001`
- **THEN** 初始密码为 `thu260001`，首次登录进入改密页

#### Scenario: 王芳初始密码按学号末六位生成

- **WHEN** 开发种子创建或重置学号 `20260002`
- **THEN** 初始密码为 `thu260002`，所属班级为高二（2）班

#### Scenario: 教师种子维护身份而不覆盖已改密码

- **WHEN** 已存在 TEA001 且其已修改过密码后重跑开发种子
- **THEN** 更新姓名、学科和班主任字段，保留该教师当前密码

## MODIFIED Requirements

### Requirement: 初始密码规则

除下文明确列出的开发教师种子外，教师和学生的初始密码 MUST 为"学校三位缩写（全小写）+ 学号/工号后6位"（例如 thu123456）。教师重置密码时 MUST 重置为该规则生成的初始密码。

#### Scenario: 学生账号初始密码生成

- **WHEN** CSV 导入学号为 20260001 的学生，学校缩写为 thu
- **THEN** 该账号初始密码为 thu260001（学校缩写 + 学号后6位）

#### Scenario: 教师账号初始密码生成

- **WHEN** 管理员创建工号为 T2023001 的教师账号，学校缩写为 thu
- **THEN** 该账号初始密码为 thu023001（学校缩写 + 工号后6位）

### Requirement: JWT 会话管理

系统 MUST 使用 JWT 进行会话管理。Access Token 有效期 MUST 为 2 小时，Refresh Token 有效期 MUST 为 7 天且存放在 HttpOnly Cookie 中。正式 JWT Payload MUST 包含字段：user_id、role、class_id、must_change_password；教师账号 MUST 额外包含 subject（学科）、teaching_classes（任教班级列表）、homeroom_class_id（可空的班主任班级）字段。当 Access Token 过期时，前端 MUST 能使用 HttpOnly Cookie 中的 Refresh Token 自动刷新获取新的 Access Token。

#### Scenario: 登录成功签发双 Token

- **WHEN** 用户密码登录认证通过
- **THEN** 系统返回 Access Token（2小时有效）到响应体，同时通过 Set-Cookie 设置 Refresh Token（7天有效，HttpOnly）

#### Scenario: Access Token 过期自动刷新

- **WHEN** 前端请求携带过期的 Access Token，浏览器自动携带 HttpOnly Cookie 中的 Refresh Token
- **THEN** 系统验证 Refresh Token 有效后签发新的 Access Token，原请求重试成功

#### Scenario: Refresh Token 过期需重新登录

- **WHEN** Refresh Token 已过期（超过7天），用户发起请求
- **THEN** 系统返回认证失效响应，前端清除本地 Token 并重定向到登录页

#### Scenario: JWT Payload 包含必要字段

- **WHEN** 系统签发教师账号的正式 Access Token
- **THEN** Token 解码后包含 user_id、role、class_id、must_change_password、subject、teaching_classes、homeroom_class_id 字段（学生账号不赋予教师身份）

### Requirement: 密码登录失败锁定

系统 MUST 对密码登录连续失败 5 次的账号锁定 15 分钟。锁定基于 LoginAttempt 表（字段：identifier、attempt_count、lock_until）实现。锁定期间即使输入正确密码也 MUST 拒绝登录。锁定时间到期后 MUST 自动解除锁定。登录成功时 MUST 清零该账号的失败计数。

#### Scenario: 连续5次密码失败后锁定

- **WHEN** 某账号连续第 5 次输入错误密码
- **THEN** 系统将该账号的 lock_until 设为当前时间 +15 分钟，返回"账号或密码错误"

#### Scenario: 锁定期间正确密码也被拒

- **WHEN** 某账号处于锁定期间（lock_until 未过期），用户输入正确的账号和密码
- **THEN** 系统拒绝登录并提示"账号已锁定，请15分钟后重试"

#### Scenario: 锁定过期后可正常登录

- **WHEN** 某账号锁定时间已过（lock_until 已过期），用户输入正确的账号和密码
- **THEN** 系统验证通过，清零失败计数，签发 Token，登录成功

#### Scenario: 密码登录成功清零失败计数

- **WHEN** 某账号之前有 3 次密码失败记录，用户输入正确密码登录成功
- **THEN** 系统将该账号的 attempt_count 清零并清除 lock_until

### Requirement: 多端在线与登出

系统 MUST 允许同一账号多端同时在线（无状态 JWT，不引入黑名单）。登出时前端 MUST 清除内存中的 Access Token 和全局状态，后端 MUST 清除 HttpOnly Cookie 中的 Refresh Token。

#### Scenario: 同一账号多端登录都成功

- **WHEN** 同一学生账号在浏览器 A 和浏览器 B 同时登录
- **THEN** 两端均获得有效的 Access Token 和 Refresh Token，互不影响，不互踢

#### Scenario: 登出清除所有 Token 和状态

- **WHEN** 用户点击登出
- **THEN** 前端清除内存中的 Access Token 和全局状态，后端清除 HttpOnly Cookie，用户被重定向到登录页

### Requirement: 忘记密码与重置密码

系统 MUST NOT 提供短信验证码找回密码功能。忘记密码时 MUST 提示“请联系班主任重置”。只有目标学生所在班级的班主任 MUST 能通过本班学生页重置密码；任课教师页 MUST NOT 展示重置操作，后端 MUST 再次校验 `student.class_id == current.homeroom_class_id` 且班级非空。成功后 MUST 使用初始密码规则生成密码，并设置 `must_change_password=true`。

#### Scenario: 用户忘记密码看到班主任提示

- **WHEN** 用户点击登录页“忘记密码”
- **THEN** 展示“请联系班主任重置”，不提供自助短信重置

#### Scenario: 班主任重置本班学生密码

- **WHEN** 班主任在“本班学生”页确认重置自己带班学生的密码
- **THEN** 密码恢复为学校缩写加学号末六位，返回初始密码并要求学生下次登录改密

#### Scenario: 任课权限不能代替班主任权限

- **WHEN** 教师仅因任教关系调用 `POST /api/teacher/reset-password` 重置其他班主任班级的学生
- **THEN** 返回 403，不更新密码；不存在或非学生的目标返回 404

## REMOVED Requirements

### Requirement: 封闭注册与账号预置

**Reason**: 原需求包含"同一手机号可绑定多个学生账号"的多娃语义，家长端移除后不再成立；账号预置改为一人一号，并由新的「封闭注册与一人一号账号预置」需求取代。

**Migration**: CSV 导入仍可填写手机号（作为联系方式），但同一手机号不再支持多娃绑定；教师账号按学科 + 班主任身份预置。

### Requirement: 手机号验证码登录

**Reason**: 家长端功能整体移除。系统不再提供面向家长的手机号验证码便捷登录；学生仅以学号 + 密码登录。

**Migration**: 删除 send-code / verify-code 端点与验证码登录界面；学生改用密码登录。

### Requirement: 验证码防刷限制

**Reason**: 验证码登录随家长端移除，验证码防刷不再需要。

**Migration**: 保留 VerificationCode 表结构可选清理；登录流程不再使用验证码。

### Requirement: 多娃选择与 Temp Token

**Reason**: 多娃绑定与家长代登录已移除，Temp Token 选择流程不再需要。

**Migration**: 删除 select-student 端点与 Temp Token 签发逻辑。

### Requirement: 切换孩子

**Reason**: 一人一号后无需切换孩子。

**Migration**: 删除 switch-student 端点、前端"切换孩子"按钮及 store 中相关状态。

### Requirement: 强制首次改密

**Reason**: 原需求含"验证码登录方式不触发强制改密"的场景，验证码登录移除后该例外不再成立，由新的「强制首次改密（无验证码例外）」需求取代。

**Migration**: 所有账号统一密码登录，强制首次改密对密码登录生效，无验证码例外。
