## Why

现有账号体系包含面向家长的手机号验证码登录、多娃绑定、Temp Token 选择与「切换孩子」功能（`login-and-account-system`、`rbac-role-permissions` 已固化），与选题「班级教学」的现实情境不符：真实学校里是"一名教师一个账号、一名学生一个账号"。教师账号也缺少**学科**与**班主任**双重身份，无法支撑第二张图片规定的三条权限铁律（教研资料按学科隔离、班主任跨学科查看本班学情、班级管理仅限任教班级）。本变更重构账号与权限模型，为智能备课等教研功能建立正确的人员与权限边界。

## What Changes

- **BREAKING** 移除家长端：删除手机号验证码登录、多娃绑定、Temp Token 选择与「切换孩子」相关接口、前端组件、表结构字段与规约需求。学生仅以学号 + 密码登录。
- 教师账号新增**学科（subject）**与**班主任班级（homeroom_class_id，可空）**身份字段；JWT 携带学科身份。
- 重设种子账号为 2 教师 + 2 学生（贴合图片 2 情境）：张老师（数学，教 1 班 + 2 班数学，1 班班主任）、李老师（英语，教 1 班 + 2 班英语，2 班班主任）、两名学生各属一个班。
- 新增教研权限维度：教研资料（备课、命题、教研问答、课例）按**学科隔离**，班主任身份不得突破学科壁垒（跨学科访问返回 404/403）。
- 学情诊断按班级 + 学科双重控制：班主任可**跨学科**查看本班学情；任课老师仅限任教班级的本学科成绩与掌握度。
- 班级管理边界：班主任可见本班全部学生名单与日常事务，任课老师仅限任教班级名单；重置学生密码仅授予该学生所在班级的班主任，任课身份不授予此权限。

## Capabilities

### New Capabilities

- `teacher-identity-and-permissions`: 教师学科 + 班主任双重身份模型，以及教研资料学科隔离、班主任跨学科本班学情特权、班级管理边界三条权限铁律的行为契约。

### Modified Capabilities

- `login-and-account-system`: 移除手机号验证码登录、多娃绑定、Temp Token 选择与切换孩子需求；封闭注册与账号预置改为支持教师学科/班主任字段的种子账号。
- `rbac-role-permissions`: 教师功能权限矩阵更新为「学科身份 + 班主任身份」混合判定（教研按学科、学情诊断班主任可跨学科看本班、班级管理限任教班级）；移除家长代登录相关需求。

- `class-data-isolation`: 移除多娃切换上下文契约，明确教师班级选择与学生本人班级过滤的差异。

## Impact

- **后端 (FastAPI)**：`auth.py` 移除 `send-code` / `verify-code` / `select-student` / `switch-student` 端点；`models.User` 新增 `subject`、`homeroom_class_id`；`security.create_access_token` 的 JWT Payload 增加 `subject`；`deps` 增加教师学科校验依赖；`dev_seed.py` 重设种子账号。
- **数据库 (SQLite)**：`users` 表新增 `subject`、`homeroom_class_id` 两列（`database.run_simple_migrations` 增列）；`verification_codes` 相关逻辑保留但不再被调用或随移除删除。
- **前端 (Next.js)**：移除验证码登录表单、`switch-child.tsx`、`student-picker.tsx` 及相关 store 字段；登录页仅保留学号/工号 + 密码。
- **测试 (apitest)**：移除验证码/多娃用例；新增学科隔离、班主任本班跨学科学情、非班主任任课老师权限用例。
- **约束**：学生数据隔离（本人数据）与教师任教班级隔离保持不变；AI 每日 40 次限制不变。
