# 2026-10-16 规约同步检查

## Scope

本次同步覆盖教师/学生工作空间、账号与权限、种子数据、助手配置界面、班级上下文以及材料上传主规约。只更新 OpenSpec 文档；已有变更不归档，尚未实现的业务接口和视觉验收保留待办。

## Results

| 检查项 | 结果 |
| --- | --- |
| Markdown 规约结构与 Requirement 唯一性 | 通过，检查 23 份 spec.md、206 条需求 |
| Scenario 标题及 WHEN / THEN | 通过，检查 589 个场景 |
| 新增/修改/移除增量与主规约一致性 | 通过，检查 10 份增量 |
| 主规约已移除家长验证码/多娃切换等旧需求 | 通过 |
| 种子姓名、2026 学号、带“班”字的班级及密码示例 | 通过，学生密码为 thu260001 / thu260002 |
| 教师/学生已实现与演示/待实现状态区分 | 已记录于主规约、设计与 tasks |
| Git 文档差异空白检查 | 通过，按仓库 Windows CRLF 换行规则检查 |

一致性检查对象：
- rework-account-permissions 下的 login-and-account-system、rbac-role-permissions、class-data-isolation、teacher-identity-and-permissions。
- align-teacher-student-workspaces 下的 teacher-workspace、student-workspace、agent-assistant。
- add-agent-assistant、add-material-upload、add-rag-search 的现有增量。

## Validation Limits

当前执行环境未找到 OpenSpec CLI，本次使用本地 Python 检查需求/场景格式、主规约与增量逐条一致性、移除项及种子示例；未将此结果称为官方 CLI 校验。

本次仅同步文档，没有重新执行登录、改密、密码重置、资料增删、学生完整视觉验收或 Docker 测试。设计文档引用的 TypeScript、生产构建、CSS 200 和数据库密码哈希匹配来自本次会话此前已执行的记录。

## Follow-up

仍待完成的业务和验证详见 tasks.md 第 5 节及 add-smart-lesson-prep/tasks.md。已有未完成变更不因本次规约同步被标记为完成或归档。

## 2026-10-20 搜索与提问历史增量验收

- `node apitest/check_recent_history.cjs` 通过：刷新持久化、学生/班级/科目/功能隔离、空白忽略、去重置顶、10 条上限、清空、损坏数据、拒绝/配额存储回退、文本安全渲染与按钮禁用。
- Docker 前端生产构建与类型检查通过，已更新 8081 前端并重载代理，前后端健康。
- 实际 `materials/page.tsx`、`student/page.tsx`、AppShell、RecentHistory 组件及 Hook 被编译到独立临时验证页，认证/API 使用明确标识的模拟账号和接口。浏览器确认搜索记录刷新保留、历史词再次搜索、物理/数学切换隔离、不同模拟账号隔离、助手点击仅回填且发送计数不增加、清空提问历史仍保留模拟会话。
- 截图 `.review/recent-history/materials.png`、`assistant.png`。验证页初版会话 mock 返回对象与实际数组契约不符，已纠正 mock 后重测；非产品故障。未修改真实登录状态、资料或会话，没有 AI 调用。未宣称已完成真实学生登录后的完整端到端验收。


## 2026-10-20 统一规约整理

本变更的主规约、设计及任务状态已对照当前实现整理，统一入口为 openspec/README.md。当前已可使用 OpenSpec CLI 1.13.0；本次严格校验和链接检查结果见 openspec/validation-2026-10-20.md。此前“未找到 CLI”的记录属于当时验收限制，本次文档检查不等于重跑功能测试。
