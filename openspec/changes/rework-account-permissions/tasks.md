## 1. 数据模型：教师学科与班主任字段

- [x] 1.1 models.py User 新增 subject（String，可空）、homeroom_class_id（Integer FK classes.id，可空）字段，验证 create_all / run_simple_migrations 增列后字段存在
- [x] 1.2 dev_seed.py 重设种子：张老师 TEA001 math 任教[101,102] homeroom_class_id=101；李老师 TEA002 english 任教[101,102] homeroom_class_id=102；两名学生一人一号（删除多娃绑定），验证种子脚本幂等可重复运行

## 2. 移除家长端（后端）

- [x] 2.1 auth.py 删除 send-code / verify-code / select-student / switch-student 端点与 Temp Token 签发逻辑（create_temp_token、TOKEN_TYPE_TEMP），验证登录仅剩密码登录且 apitest 无验证码用例
- [x] 2.2 清理 services.py 验证码相关函数与 schemas 中验证码/选择学生模型（或按设计决策删除 VerificationCode 相关），验证 import 与 /api/auth/login 正常
- [x] 2.3 _issue_tokens 移除 phone 相关 claim（如需），验证刷新/改密/登出端点正常

## 3. 权限判定：学科隔离 + 班主任特权

- [x] 3.1 deps.py 新增 require_subject(current, subject) 依赖（教研端点用）与 require_homeroom(db, class_id)（班主任特权端点用），验证跨学科/非班主任访问返回 403 并记审计
- [x] 3.2 security.create_access_token 在 JWT Payload 增加 subject、homeroom_class_id，验证解码后字段存在、旧 Token 无 subject 时按"无学科"拒绝
- [x] 3.3 audit_logs 表新增可空列 subject、class_id（AuditLog 模型 + 迁移），write_audit_log 支持写入，验证越权审计记录含新字段

## 4. 前端适配

- [x] 4.1 登录页移除验证码 Tab，仅保留学号/工号 + 密码表单，验证手动登录成功
- [x] 4.2 删除 switch-child.tsx、student-picker.tsx 及 store 中 canSwitchStudent 等字段，验证 npm run build 通过、教师/学生页面无残留引用
- [x] 4.3 api.ts 移除验证码/切换孩子接口定义，验证类型检查通过

## 5. 测试与集成验证

- [ ] 5.1 apitest 移除验证码/多娃用例，新增用例：数学教师访问英语教研资料 404/403；班主任看本班全科学情放行、看其他班被拒；学生调用备课/教师接口 403
- [ ] 5.2 完整端到端冒烟：教师登录 → 本学科教研资料 → 跨学科拒绝 → 班主任本班全科学情；当前学情/教研完整业务尚未接入，旧勾选不足以证明此流程完成
- [x] 5.3 npm run build + 后端 import/建表通过


## 6. 2026-10-16 工作空间与权限补充

- [x] 6.1 种子与文档统一为张老师/李老师、李明/王芳、20260001/20260002、高二（1）班/高二（2）班。
- [x] 6.2 明确学生初始密码为 thu260001/thu260002，并记录本次会话已完成的数据库哈希核对。
- [x] 6.3 重置密码接口仅允许目标学生班级等于教师 homeroom_class_id；任课列表隐藏操作，班主任列表保留。
- [x] 6.4 班主任菜单按账号身份常驻，任课切班只改变任课上下文；完整 UI 契约同步至 teacher-workspace。
- [x] 6.5 同步主规约并移除班级隔离中旧的多娃上下文与禁止所有 class_id 参数的表述。
- [ ] 6.6 对新增名单模式/重置权限进行学生与两位教师的完整接口回归；未以源码检查替代接口验收。

说明：既有任务勾选保留其原始记录，6 节与 align-teacher-student-workspaces 记录今日新增范围；此次规约同步未重新执行历史集成测试。未实现的教研和学情业务不因导航存在而完成。
