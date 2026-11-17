# 单科切班错误修复记录（2026-11-04）

## 代码修改前的自检

根因已在隔离环境复现：教师进入一班单科学情页后，另一标签页登录学生，再切二班跳到 403。证据 `.review/class-switch-before.json`、`.review/class-switch-before.jpg`。该跳转来自共享辅助角色 Cookie 的前端判断，未到达对应业务接口。

已自检 proposal/design/specs 的一致性：当前有效会话继续合法切班；实际错误角色仍拒绝且不挂载业务内容；首次改密及刷新失败行为保留；不改后端权限、账号、数据库或令牌寿命。实施仅修复用户报告的错误。此为实施者自检，不冒充另一名组员的合并评审。

用户随后明确要求「你继续改这个问题吧」，据此继续本修复，并按实际证据更新本变更的任务状态；不执行 `/opsx-apply`、`/opsx-archive`，不修改其他变更的任务勾选。历史命题作业变更保持原状。

全门禁首轮发现旧待处理变更 `rework-account-permissions` 的同名 MODIFIED 规约未包含新主规约场景。已仅将该旧 delta 的「前端路由级权限拦截」一块与当前主规约同步，逐项断言原 Scenario 集合全部保留，避免未来归档覆盖本次修复；未执行该旧变更、未修改其任务状态，也未删减检查。记录 `.review/class-switch-compat-sync.json`；全量规约随后通过。

## 实现与检查结论

本次修改 `frontend/middleware.ts`、`frontend/components/auth-guard.tsx`，新增 `frontend/lib/route-access.ts`。页面启动不再依据共享辅助提示 Cookie 拒绝导航；当前页会话恢复完成后先校验角色，再挂载业务内容。角色变化时即使原先 ready=true 也立即隐藏业务子组件，随后跳转 403。首次改密、刷新恢复/失败及原后端 JWT、班级/学科权限均保留。

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 新前端回归 | **33/33 PASS**；直接执行真实 middleware、AuthGate 和路径判断，替身仅提供会话、路由和 React 调度 | `apitest/check_route_guard.cjs`、`.review/class-switch-regression.log` |
| 修复前失败 | 旧 middleware 对有效教师场景返回 redirect，首条检查出现 `redirect !== next` | `.review/class-switch-red.log` |
| 故意改坏验证 | 临时使教师路径接受学生，路径/角色断言按预期变红；恢复源码后 33 项通过 | `.review/class-switch-mutation.json`、`.review/class-switch-mutation.log` |
| 完整门禁 | **22/22 PASS**，含全部原业务回归、类型、密钥与分层检查 | `.review/class-switch-full-check.log` |
| 全量规约 | **28/28 PASS**；旧历史变更的 INFO 不构成失败 | `.review/class-switch-specs.log` |
| 前端构建 | Docker frontend 构建通过 | `.review/class-switch-build.log` |
| 实际服务 | 已仅更新 `campusclaw-groupv3` 的 frontend，并重启本套入口；8083 健康为 ok，数据库/MCP 正常、模型已配置 | `.review/class-switch-health.json`、`.review/class-switch-containers.json` |
| 实际页面 | 8083 从一班切二班后 URL 保留 `workspace=teaching&view=subject-analysis`，选择器为二班，标题仍为「学情分析（单科·数学）」且正常展示 | `.review/class-switch-after.jpg`、`.review/class-switch-browser.json:production` |

本次未修改提示词、依赖、模型、后端接口、数据库、上传文件或账号权限，不需要数据迁移。回归只使用临时数据或独立 `.review/qa` 测试库；实际 8083 只做页面读取及切班验证，未新增教学作业或提交。

## 浏览器与 Scenario 对应

测试环境为 `127.0.0.1:3009`（独立后端 8009），使用合成教师/学生账号。先复现错误，再在共享提示仍由学生标签页写入的条件下验证教师合法切班。以下 JSON 字段均来自 `.review/class-switch-browser.json`。

| Scenario | 本次检查 |
| --- | --- |
| 教师访问教师路由通过 | CJS「本角色页面正常渲染 teacher → /teacher」；实际 `production` |
| 学生访问学生路由通过 | CJS「本角色页面正常渲染 student → /student」；测试学生标签页正常登录 |
| 学生访问教师路由被拦截 | CJS 学生→教师时不挂载业务；浏览器 `studentForbidden` 为 /403 |
| 教师访问学生路由被拦截 | CJS 教师→学生时不挂载业务；浏览器 `teacherForbidden` 为 /403 |
| 未登录用户访问业务路由重定向登录 | CJS 缺令牌刷新失败→清理会话→/login；浏览器退出后再打开教师页 `anonymous` 为 /login |
| 双标签提示变化后的单科切班 | CJS 首条共享提示冲突检查；浏览器 `fixedSingleSubject` 从 101 切 102，保留原视图 |
| 辅助提示缺失但会话有效 | CJS 各业务路径提示为空仍可启动，当前教师/学生会话正常渲染 |
| 伪造角色提示不赋予页面权限 | CJS middleware 只允许启动，实际 AuthGate 拒绝错误角色且无业务闪现；浏览器两方向 /403 |
| 刷新恢复后的角色仍须匹配 | CJS 同一教师 URL 分别恢复 teacher/student，前者可用、后者 /403；浏览器 `refreshRestored` 保留助手配置二班 |
| 身份恢复前不显示业务内容 | CJS 缺令牌、缺角色、刷新中不挂载；首次改密优先进入 /change-password |
| 角色目录按完整路径边界判断 | CJS 覆盖 /teacher、/teacher/quiz、/student、子路径、/materials、相似前缀及无效角色 |
| 前端越权跳转 403 页面 | CJS 已就绪会话发生角色变化时立即隐藏内容并 /403；浏览器实际双向验证 |
| 后端越权返回 403 并记录审计日志 | 本次全门禁执行 `check_baseline.py:215` 的学生调教师接口与 403 访问日志检查；新功能集成也保留审计拒绝断言 |
| 教师跨班操作记录审计日志 | 全门禁 `check_lessons_2_5.py:96`、`check_quiz_homework.py` 的跨班拒绝及审计检查 |
| 审计日志异步写入不影响响应性能 | 保留原审计机制，现有回归核对 403 响应和日志可查；本修复没有修改后端审计写入或新增性能指标，不将本次页面修复宣称为后端性能改造 |

额外切班回归 `views`：单科资料切 101、学生名单切 102、作业与改分切 101、助手配置切 102，均保留对应 URL、工作区及标题。截图 `.review/class-switch-after-qa.jpg` 为隔离环境；`.review/class-switch-after.jpg` 为实际 8083。

## 文档、部署与回滚

README、OpenSpec 索引、RBAC 主规约、产品规范与安全规范已同步；主规约两项 Requirement 保留原有 Scenario 并补充共享提示冲突、刷新和路径边界。旧待处理 delta 仅兼容同步同名路由块，不修改其其他要求或任务。所有保护页面继续由 AuthGate 包裹，后端数据授权未放宽。

旧 frontend 镜像编号保存在 `.review/class-switch-old-images.json`。如需回滚，仅将其中 frontend 的旧镜像 ID 恢复为本项目前端标签，再执行 `docker compose up -d --no-build --no-deps frontend` 并重启本套 Nginx；无需恢复数据库。本次没有执行回滚，未修改其他端口部署。

本记录是实施者自检和本次可查的自动/浏览器证据，不冒充另一名组员的合并评审；未提交、合并或归档。共享刷新 Cookie 的既有语义保留：整页刷新后按服务器实际恢复的身份再次检查角色，不宣称浏览器多账号会话永久独立。
