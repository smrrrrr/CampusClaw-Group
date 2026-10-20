## MODIFIED Requirements

### Requirement: 教师共用工作空间导航

教师端 MUST 在 `/teacher`、`/materials`、`/teacher/upload`、`/teacher/library` 和 `/teacher/lesson-prep` 共用同一导航结构和身份范围。侧栏 MUST 按班主任工作台、任课教学、教研中心、系统与统计排列；当前页面及父级 MUST 正确高亮。页面 MUST 保留班级或学科身份提示以及退出登录入口。

#### Scenario: 教师打开资料页仍可访问其他模块

- **WHEN** 教师从任课管理进入资料页或上传页
- **THEN** 侧栏保留同样的教师导航，可进入学生名单、教研入口和助手配置

### Requirement: 班主任模块按身份常驻

班主任身份 MUST 由 `homeroom_class_id != null` 判定，MUST NOT 仅由当前 `workspace` 判定。有班主任身份时，班主任模块 MUST 在任课教学、资料页和助手配置页继续可见。无此身份的教师 MUST NOT 获得该模块。侧栏 MUST NOT 再提供“我的带班 / 任课教学”二选一切换控件。

班主任模块 MUST 包含“本班首页”及下列入口：本班学生、本班资料（全科）、本班学情（全科）、本班作业（总览）、班级通知/公告。

#### Scenario: 任课教学保留班主任入口

- **WHEN** 张老师在 `workspace=teaching` 查看班级 102 的任课内容
- **THEN** 班主任工作台仍显示，点击“本班学生”进入 `workspace=homeroom&view=class-students&class_id=101`

#### Scenario: 非班主任只显示任课与教研功能

- **WHEN** 教师 `homeroom_class_id=null`
- **THEN** 侧栏不显示班主任工作台及班主任审计入口，保留任课、教研和助手配置入口

### Requirement: 任课与带班上下文独立

任课管理 MUST 提供 `teaching_classes` 范围内的班级选择器，并包含班级学生、本班资料（单科）、学情分析（单科）、作业与改分、单科资料发布。任课链接 MUST 使用 `workspace=teaching`；班主任链接 MUST 使用 `workspace=homeroom`，并固定为本人 `homeroom_class_id`。任课切班 MUST NOT 改变班主任班级。无效任课 URL 班级值 MUST 回退到有效任教班级；前端路由参数 MUST NOT 赋予后端权限。

#### Scenario: 切换任课班级不切换带班班级

- **WHEN** 任教 101、102 且带班 101 的教师将任课下拉切到 102
- **THEN** 任课请求使用 102，班主任入口仍使用 101，后端继续校验各操作所需权限

### Requirement: 两种学生名单的操作差异

“本班学生”页 MUST 显示带班学生名单，允许班主任确认后重置本班学生密码，MUST NOT 显示“单科资料发布”按钮。“班级学生”页 MUST 显示当前任教班级名单，MUST NOT 显示重置密码按钮或重置操作列；该页面可保留单科资料发布入口。

后端 `POST /api/teacher/reset-password` MUST 按 `teacher-identity-and-permissions` 独立校验班主任班级，不能仅依据按钮是否可见或 `workspace` 参数授权。

#### Scenario: 班主任学生页展示重置操作

- **WHEN** 高二（1）班班主任进入本班学生页
- **THEN** 页面展示操作列与“重置密码”，不展示单科资料发布；成功后提示初始密码并要求学生改密

#### Scenario: 同一教师在任课页不展示重置操作

- **WHEN** 该教师进入任课管理的班级学生页
- **THEN** 只展示名单字段，不展示重置密码按钮或操作列，即使该教师同时具备班主任身份

### Requirement: 全科总览与单科教学入口区分

班主任资料、学情、作业入口 MUST 标明全科或总览；全科资料和作业总览 MUST 为只读，不赋予跨学科修改资料或批改作业权限。任课教学入口 MUST 标明单科范围，科目 MUST 来源于登录教师的 `subject`。教研中心 MUST 包含教研组资料、智能备课、智能命题、教研问答和课例分析，目标权限只限本学科组。教研组资料 MUST 提供教师版导入、学生版预览及分班发布；智能备课 MUST 进入 /teacher/lesson-prep，提供教师教案生成、编辑审阅定稿与两种学生稿发布，详情见 smart-lesson-prep。智能命题、教研问答及课例分析等尚未接入模块 MUST 使用占位状态，不得伪装为已有生成结果。

#### Scenario: 班主任进入全科资料总览

- **WHEN** 班主任打开本班资料（全科）
- **THEN** 页面不提供该总览中的资料上传或删除操作；任课发布入口仍属于任课上下文

#### Scenario: 打开未接入的学情或教研模块

- **WHEN** 教师访问尚无业务实现的学情、作业或教研入口
- **THEN** 展示对应名称、范围说明和未接入提示，不伪装为已有统计或生成结果

#### Scenario: 在教研组内选择教师版发布学生稿

- **WHEN** 教师进入教研组资料，选择本学科教师版并生成学生预览
- **THEN** 可编辑学生稿并选择任教班级发布，教师原稿保持组内可见；该操作不生成 AI 教案

### Requirement: 助手配置独立入口及菜单顺序

“助手配置” MUST 为独立主菜单项，位于系统与统计分组中，并在“审计与统计”上方。所有教师 MUST 可进入助手配置；当前班主任审计入口 MUST 仅面向本人带班范围。助手配置页 MUST 自带“配置班级”选择器，并从任教班级范围内读取/保存本人任教学科的提示词与解题引导开关，各教师互不覆盖。

#### Scenario: 在助手配置页切换班级

- **WHEN** 教师在配置页从 101 切换到 102
- **THEN** 保留助手配置视图，读取 102 的配置，后续保存以 102 为目标；班主任菜单仍保留

#### Scenario: 检查系统菜单顺序

- **WHEN** 有班主任身份的教师查看侧栏
- **THEN** “助手配置”紧邻且位于“审计与统计”之前

### Requirement: 教师页移除快捷切换账号

教师工作空间顶栏 MUST NOT 显示“切换账号”按钮，MUST 保留当前用户身份和退出登录。更换账号 MUST 通过退出当前会话后重新登录完成，不引入多用户快捷切换。

#### Scenario: 教师检查顶栏

- **WHEN** 教师打开名单或助手配置页
- **THEN** 顶栏显示身份与退出，不显示“切换账号”

### Requirement: 本地预览包含静态资源

本地构建部署 MUST 同时交付页面、JavaScript 和 CSS，使登录页、教师端及学生端使用一致的构建资源。使用 Next.js standalone 时 MUST 在启动前将 `.next/static` 复制到 `.next/standalone/.next/static`，若存在 `public` 则同时复制。Windows 本地重建 MUST 先停止占用构建目录的本项目服务，再构建、补齐资源并启动。

#### Scenario: standalone 服务交付登录样式

- **WHEN** 访问本地 3000 端口的登录页及页面引用的 CSS
- **THEN** 页面和 CSS 均正常返回，CSS 使用样式内容类型，不出现 HTML 正常而样式 404 的裸页面
