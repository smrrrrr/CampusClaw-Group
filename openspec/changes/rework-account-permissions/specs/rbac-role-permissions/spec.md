## ADDED Requirements

### Requirement: 双角色定义与教师学科身份

系统 MUST 仅包含教师（teacher）和学生（student）两种底层角色，MUST NOT 创建独立的家长角色，MUST NOT 存在家长代登录或多娃绑定。学生 MUST 一人一号，仅以学号 + 密码登录。教师账号 MUST 携带学科（subject）与班主任班级（homeroom_class_id，可空）双重身份；教师工作空间展示其学科教研组身份；有带班班级时默认进入本班首页，否则进入本学科教研入口。

#### Scenario: 教师学科身份登录后进入教研组

- **WHEN** 学科为 math 的教师登录获得 JWT
- **THEN** 该 JWT 的 role 为 teacher，payload 携带 subject=math，系统默认展示数学教研组功能

#### Scenario: 系统不创建独立家长角色

- **WHEN** 任何用户尝试在系统中注册或创建"家长"角色账号
- **THEN** 系统拒绝该操作，系统仅支持 teacher 和 student 两种角色

#### Scenario: 学生仅以学号密码登录

- **WHEN** 学生使用学号 + 密码登录
- **THEN** 系统签发 role=student 的 JWT，不存在手机号验证码或家长代登录入口

### Requirement: 学生功能权限矩阵

学生 MUST 拥有以下功能权限：学习功能（查看本班资料、提交作业、查看个人错题本、修改个人密码）；AI 解题（发起 AI 提问、查看自己的提问历史、将 AI 解答加入错题本）。学生 MUST NOT 查看其他学生的任何数据。

#### Scenario: 学生查看本班资料并提交作业

- **WHEN** 学生登录后访问资料页面和作业页面
- **THEN** 系统展示该学生所在班级的资料和作业，学生可查看资料并提交作业

#### Scenario: 学生查看个人错题本

- **WHEN** 学生访问错题本页面
- **THEN** 系统仅展示该学生个人的错题记录，不包含其他学生的数据

#### Scenario: 学生修改个人密码

- **WHEN** 学生在设置页面修改自己的密码
- **THEN** 系统校验旧密码和新密码策略后更新密码，重新签发 Token

#### Scenario: 学生发起 AI 提问并查看历史

- **WHEN** 学生在 AI 解题页面发起一次提问
- **THEN** 系统接受提问，AI 返回解答，该提问记录在学生的提问历史中

#### Scenario: 学生将 AI 解答加入错题本

- **WHEN** 学生在 AI 解答页面点击"加入错题本"
- **THEN** 系统将该 AI 问答记录添加到该学生的个人错题本中

#### Scenario: 学生不能越权查看其他学生数据

- **WHEN** 学生尝试查看同班其他学生的错题本、作业、AI 提问历史
- **THEN** 系统拒绝该操作并返回 403 Forbidden，仅返回该学生本人的数据

### Requirement: AI 提问每日次数限制（按学生独立计数）

学生每日 MUST 最多发起 40 次 AI 提问。限制 MUST 绑定在 student_id 上，而非设备或班级。次日 MUST 自动重置计数。达到上限时系统 MUST 拒绝新的提问请求并返回提示。

#### Scenario: 学生当日提问未达上限

- **WHEN** 学生当日已发起 15 次 AI 提问，尝试再次提问
- **THEN** 系统接受该提问，当日提问计数更新为 16

#### Scenario: 学生当日提问达到上限被拒

- **WHEN** 学生当日已发起 40 次 AI 提问，尝试第 41 次提问
- **THEN** 系统拒绝该提问并返回提示"今日提问次数已达上限（40次），请明日再试"

#### Scenario: 次日提问次数重置

- **WHEN** 跨自然日后学生尝试发起 AI 提问
- **THEN** 系统清零该学生的当日提问计数，允许重新提问

#### Scenario: 不同学生账号次数独立计算

- **WHEN** 学生 A 与学生 B 分别发起 AI 提问
- **THEN** 系统按各自 student_id 独立计算当日提问次数，互不影响

### Requirement: 学生数据权限 - 个人数据隔离（一人一号）

学生 MUST 只能操作自己的数据。后端所有涉及学生个人数据的查询 MUST 带 WHERE student_id = :current_user_id 条件。学生 MUST NOT 越权查看其他学生的任何数据。current_user_id 来源于 JWT Payload 中的 user_id。由于学生一人一号、无家长代登录，不存在"家长查看兄弟姐妹数据"的场景。

#### Scenario: 学生查询自己数据成功

- **WHEN** 学生请求查看自己的错题本或 AI 提问历史
- **THEN** 系统返回该学生个人的数据，查询 SQL 带 WHERE student_id = :current_user_id

#### Scenario: 学生尝试查询他人数据被拒

- **WHEN** 学生尝试在请求参数中传入其他学生的 student_id 查看其错题本
- **THEN** 系统以 JWT 中的 user_id 为准，仅返回当前学生本人的数据，忽略请求参数中的 student_id

## MODIFIED Requirements

### Requirement: 教师功能权限矩阵

教师 MUST 拥有以下功能权限：班级管理（创建和管理自己任教的班级，拥有 teaching_classes 列表）；资料与作业（上传资料、布置作业、批改作业、查看本班所有学生的数据）；AI 解题（查看本班学生的 AI 提问历史用于了解薄弱知识点，但 MUST NOT 代替学生发起 AI 提问）；账号管理（查看任教班级学生信息；仅该班班主任可重置本班学生密码）。教师 MUST NOT 操作非任教班级的任何数据。教研类功能（备课、命题、教研问答、课例）MUST 额外受学科身份约束：教师 MUST 仅能访问本学科教研资料，班主任身份 MUST NOT 突破学科壁垒。班主任 MUST 可跨学科查看本班学情。

#### Scenario: 教师管理自己任教的班级

- **WHEN** 教师登录后访问班级管理页面
- **THEN** 系统展示该教师 teaching_classes 列表中的所有班级，教师可对这些班级进行管理操作

#### Scenario: 教师上传资料并布置作业

- **WHEN** 教师选择自己任教的某班级，上传一份资料并布置一份作业
- **THEN** 系统接受操作，资料和作业关联到该班级，该班级学生可见

#### Scenario: 教师批改作业并查看本班学生数据

- **WHEN** 教师选择自己任教的某班级，查看学生提交的作业并批改
- **THEN** 系统展示该班级所有学生的作业数据，教师可进行批改操作

#### Scenario: 教师查看本班学生 AI 提问历史

- **WHEN** 教师选择自己任教的某班级，查看 AI 提问历史页面
- **THEN** 系统展示该班级所有学生的 AI 提问历史记录，教师可查看但不可代替学生发起提问

#### Scenario: 教师不能代替学生发起 AI 提问

- **WHEN** 教师尝试在 AI 解题页面发起一次 AI 提问
- **THEN** 系统拒绝该操作并返回提示"AI 提问仅限学生发起"，教师无发起提问的权限

#### Scenario: 教师重置本班学生密码

- **WHEN** 该班班主任在“本班学生”页面对自己带班班级的学生确认“重置密码”
- **THEN** 系统校验学生班级等于教师 homeroom_class_id 后重置为初始密码，must_change_password 设为 true

#### Scenario: 教师不能查看非任教班级的学生数据

- **WHEN** 教师尝试查看或操作不在 teaching_classes 范围内的班级的学生数据
- **THEN** 系统拒绝该操作并返回 403 Forbidden

#### Scenario: 教师仅能访问本学科教研资料

- **WHEN** 学科为 math 的教师访问英语备课或教研资料
- **THEN** 系统返回 404/403 并记录审计日志，班主任身份不覆盖学科隔离

#### Scenario: 班主任跨学科查看本班学情

- **WHEN** 学科为 math 但担任一班班主任的教师查看一班的总体学情
- **THEN** 系统返回一班所有学科的学情数据（成绩、掌握度、薄弱点）

#### Scenario: 任课教师不能重置学生密码

- **WHEN** 教师在任课学生名单页浏览，或以任课身份直接调用重置接口
- **THEN** 页面不显示重置按钮；若目标班级不等于 homeroom_class_id，接口返回 403

### Requirement: 前端路由级权限拦截

前端 Next.js MUST 使用 middleware.ts 做路由拦截。/teacher/* 路由 MUST 仅允许 role=teacher 的用户访问，/student/* 路由 MUST 仅允许 role=student 的用户访问。越权访问 MUST 跳转到 403 无权限提示页。未登录用户访问任何业务路由 MUST 重定向到登录页。

#### Scenario: 教师访问教师路由通过

- **WHEN** role=teacher 的用户访问 /teacher?workspace=teaching&view=students 页面
- **THEN** middleware 校验通过，正常渲染教师班级管理页面

#### Scenario: 学生访问学生路由通过

- **WHEN** role=student 的用户访问 /student?view=assistant 页面
- **THEN** middleware 校验通过，正常渲染学生资料页面

#### Scenario: 学生访问教师路由被拦截

- **WHEN** role=student 的用户尝试访问 /teacher?workspace=teaching&view=students 页面
- **THEN** middleware 拦截请求，重定向到 403 无权限提示页

#### Scenario: 教师访问学生路由被拦截

- **WHEN** role=teacher 的用户尝试访问 /student?view=assistant 页面
- **THEN** middleware 拦截请求，重定向到 403 无权限提示页

#### Scenario: 未登录用户访问业务路由重定向登录

- **WHEN** 未携带有效 Access Token 的用户访问 /teacher?workspace=teaching&view=students 或 /student?view=assistant
- **THEN** middleware 拦截请求，重定向到登录页

### Requirement: 后端接口级权限拦截

后端 FastAPI MUST 使用 Depends 依赖注入做接口拦截。Depends(get_current_teacher) MUST 拦截所有教师专用接口，仅允许 role=teacher 的请求通过。Depends(get_current_student) MUST 拦截所有学生专用接口，仅允许 role=student 的请求通过。越权请求 MUST 返回 403 Forbidden 并记录审计日志。

#### Scenario: 教师调用教师接口通过

- **WHEN** role=teacher 的用户携带有效 Token 调用 POST /api/teacher/upload-material 接口
- **THEN** get_current_teacher 依赖校验通过，接口正常处理

#### Scenario: 学生调用学生接口通过

- **WHEN** role=student 的用户携带有效 Token 调用 POST /api/student/conversations 接口
- **THEN** get_current_student 依赖校验通过，接口正常处理

#### Scenario: 学生调用教师接口返回 403

- **WHEN** role=student 的用户携带有效 Token 调用 POST /api/teacher/upload-material 接口
- **THEN** get_current_teacher 依赖校验失败，返回 403 Forbidden，记录审计日志

#### Scenario: 教师调用学生接口返回 403

- **WHEN** role=teacher 的用户携带有效 Token 调用 POST /api/student/conversations 接口
- **THEN** get_current_student 依赖校验失败，返回 403 Forbidden，记录审计日志

## REMOVED Requirements

### Requirement: 双角色定义与家长身份透明

**Reason**: 家长端功能整体移除，不再存在家长验证码代登录、家长身份透明化需求；由新的「双角色定义与教师学科身份」取代。

**Migration**: 教师账号按学科 + 班主任身份建立；学生一人一号密码登录。

### Requirement: 学生功能权限矩阵（含家长代登录）

**Reason**: 家长代登录已移除，原需求中"含家长代登录"语义不再成立，由新的「学生功能权限矩阵」取代。

**Migration**: 学生权限按「学生功能权限矩阵」执行；删除"家长代登录享有同等权限"场景。

### Requirement: AI 提问每日次数限制

**Reason**: 原需求含"多娃切换后次数独立计算"场景，多娃绑定已移除；由新的「AI 提问每日次数限制（按学生独立计数）」取代。

**Migration**: 次数限制仍按 student_id 独立计数；删除多娃切换场景。

### Requirement: 学生数据权限 - 个人数据隔离

**Reason**: 原需求含"家长不能查看兄弟姐妹的数据"场景，家长代登录已移除；由新的「学生数据权限 - 个人数据隔离（一人一号）」取代。

**Migration**: 学生数据隔离仅按 student_id = current_user_id 执行，删除家长视角场景。

### Requirement: 多娃切换权限与状态重载

**Reason**: 多娃绑定与家长代登录已移除，切换孩子流程不再存在。

**Migration**: 删除 switch-student 端点与前端"切换孩子"按钮；JWT 签发不再涉及 Temp Token 与多娃选择。
