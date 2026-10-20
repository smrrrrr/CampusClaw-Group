## Context

CampusClaw 现有账号体系来自 `add-login-and-account-system` 与 `add-rbac-role-permissions` 两个已完成变更：双角色（teacher/student）、密码登录 + 手机号验证码登录、多娃绑定与 Temp Token 选择、切换孩子、JWT 双 Token + 班级数据隔离。现实情境（选题第二张图）要求：两名教师（张老师=数学+1班班主任、李老师=英语+2班班主任）、两名学生一人一号；教研资料（备课、命题、教研问答、课例）严格按学科隔离；班主任可跨学科查看本班学情；班级管理仅限任教班级。本设计为 `rework-account-permissions` 规约提供实现方案，聚焦：移除家长端、教师学科 + 班主任双重身份、教研学科隔离、班主任学情特权。

## Goals / Non-Goals

**Goals:**

- 移除手机号验证码登录、多娃绑定、Temp Token 选择与切换孩子（后端端点 + 前端组件 + 规约）
- 教师账号新增学科（subject）与班主任班级（homeroom_class_id）字段，JWT 携带 subject
- 教研资料按学科隔离（班主任身份权重为 0），学情诊断班主任可跨学科看本班，班级管理限任教班级
- 重设种子账号：2 教师（张老师/李老师）+ 2 学生

**Non-Goals:**

- 不新增家长角色（角色仍仅 teacher/student）
- 不实现"学科组管理员""教研组成员"独立角色（教研问答/课例分析模块后续变更再引入学科组共享维度）
- 不改变班级数据隔离与 AI 每日限次
- 不引入 ABAC 框架，权限判定用现有 FastAPI Depends + JWT claims 组合实现

## Decisions

### 1. 数据模型：User 新增学科与班主任字段

`users` 表新增两列（`database.run_simple_migrations` 增列）：

- `subject`（String，可空，如 "math"/"english"）—— 仅教师使用，学生为 NULL
- `homeroom_class_id`（Integer FK classes.id，可空）—— 仅教师使用，NULL 表示非班主任

**选择按字段而非新表**：身份是账号固有属性，单账号多身份直接体现在 User 行上，符合"一人一号、身份叠加"的现实模型；`teaching_classes`（JSON 数组，任教班级）保留不变。`subject` 也写入 JWT Payload，后端教研接口从 Token 取学科，不信任请求参数。

**替代方案**：新增 `teacher_identity` 关联表。**未选原因**：单学科单班主任场景下冗余，字段方案查询/鉴权更简单。

### 2. 家长端移除清单

- `auth.py`：删除 `send-code`、`verify-code`、`select-student`、`switch-student` 四个端点及 `create_temp_token`、`TOKEN_TYPE_TEMP` 相关逻辑；`login` 仅保留密码登录。
- `services.py`：验证码相关（`check_send_allowed`、`create_verification_code`、`register_code_failure`、`get_latest_pending_code`）与 `VerificationCode` 表保留但不再被调用，或一并删除（删除更干净，本项目由 OpenSpec apply 时按任务定）。
- 前端：删除 `switch-child.tsx`、`student-picker.tsx`、登录页验证码 Tab；`store` 移除 `canSwitchStudent` 等字段；`student/page.tsx` 移除"切换孩子"按钮。
- `apitest/cases/api/auth/`：移除验证码/多娃用例。
- 规约：`login-and-account-system` REMOVED 手机号验证码登录/验证码防刷/多娃选择与 Temp Token/切换孩子；`rbac-role-permissions` REMOVED 多娃切换与家长相关场景。

### 3. 权限判定：教研按学科、学情按班主任、班级按任教

新增 `deps` 依赖与 `services` 辅助函数，组合 JWT claims（role、class_id、teaching_classes、subject、homeroom_class_id）：

| 功能域 | 判定依据 | 规则 |
|---|---|---|
| 教研资料（备课/命题/教研问答/课例） | subject | 仅本学科，班主任不覆盖；跨学科 404/403 + 审计 |
| 学情诊断 | subject + homeroom_class_id + class_id | 班主任：可看本班全科；任课：仅任教班级本学科 |
| 班级管理（名单/事务） | teaching_classes / homeroom_class_id | 班主任：本班全名单；任课：任教班级名单 |

新增依赖：`get_current_teacher` 后追加 `require_subject(teacher)`（教研端点用）与 `require_homeroom(db, class_id)`（班主任特权端点用）。审计沿用 `write_audit_log` 异步写入，AuditLog 扩展字段可选（subject、class_id 可后续加列，或本变更直接加）。

### 4. 种子账号重设（dev_seed.py）

```
教师：
- 张老师 TEA001  math      任教 [101,102]  homeroom_class_id=101  （1班班主任，教1/2班数学）
- 李老师 TEA002  english   任教 [101,102]  homeroom_class_id=102  （2班班主任，教1/2班英语）
学生：
- 李明 20260001 class_id=101
- 王芳 20260002 class_id=102
```

班级使用 101（高二（1）班）、102（高二（2）班），班级显示名称 MUST 保留末尾的“班”字。删除多娃手机号绑定逻辑（学生一人一号）。密码沿用初始规则（thu + 后6位），开发种子中新建教师使用固定密码 `Teach@2026`，`must_change_password=false`；已有教师重跑种子不覆盖密码。学生 `20260001`、`20260002` 的初始密码分别为 `thu260001`、`thu260002`，`must_change_password=true`。种子脚本重跑会重置这两名学生的密码并清理不在清单内的学生，仅用于开发环境。

### 5. 前端适配

- 登录页只保留学号/工号 + 密码表单。
- 教师端共用 `teacher-navigation.tsx`：班主任菜单按 `homeroom_class_id != null` 常驻，任课菜单按任教班级选择；切换当前工作区不会移除另一身份的菜单。完整导航契约见 `teacher-workspace`。
- 学生端：移除切换孩子按钮与验证码登录；`app/login/page.tsx`、`app/student/page.tsx`、`app-layout.tsx` 清理相关引用。

## Risks / Trade-offs

- **[移除验证码登录影响已有习惯]** → 本选题明确一人一号 + 密码登录，家长端整体移除是既定方向；验证码相关后端代码若保留则无人调用，建议删除保持干净。
- **[JWT 增加 subject 后旧 Token 兼容]** → Access Token 2h 过期，自然滚动；旧 Token 无 subject 时教研接口按"无学科"拒绝（教师需重新登录，影响最小）。
- **[班主任特权与学科隔离并存易误实现]** → 用上表三域分离，教研接口必须走 `require_subject`，学情接口走 homeroom 判定，避免班主任身份"泄漏"到教研域。
- **[AuditLog 增加字段]** → 采用新增可空列（subject、class_id）写入，避免破坏现有审计查询。

## Migration Plan

- `users` 加列 `subject`、`homeroom_class_id`（`run_simple_migrations`，幂等）。
- 移除验证码相关端点与前端组件；`VerificationCode`/`LoginAttempt` 相关表保留或删除按任务取舍。
- 重跑 `dev_seed.py` 重置种子账号（幂等 upsert）。
- 既有测试更新：`apitest` 移除验证码/多娃，新增学科隔离与班主任特权用例。

## Open Questions

- 2026-10-16 已实现学生名单与班主任重置本班学生密码；日常事务、全科学情、作业总览等目前为导航/占位界面，业务接口仍待实现。
- 学情诊断模块尚未建立（属 5 大功能之一），班主任跨学科学情特权的数据来源待学情诊断变更落地；本变更先固化权限判定规则与接口依赖。
