# CampusClaw 小组项目规约索引

更新时间：2026-10-20。本文是最近已实现功能的交接入口；具体行为以 `specs/` 主规约为准，`changes/` 保存变更动机、设计、任务和验收依据。现有未完成变更不在本次同步中自动归档。

## 最近功能与规约

| 功能 | 已实现范围 | 主规约 | 设计、任务及验收 |
| --- | --- | --- | --- |
| 学生学科助手 | 按班级/科目/任课教师选配置，多轮会话、SSE、历史管理、每日限次 | [agent-assistant](specs/agent-assistant/spec.md) | [助手变更](changes/add-agent-assistant/proposal.md)、[学科教师变更](changes/subject-teacher-assistants/proposal.md) |
| 解题引导 | 开启后使用固定框架并保留但忽略教师自定义提示词；分步提示、概念解释、短追问接续、完成总结 | [agent-assistant](specs/agent-assistant/spec.md) | [设计](changes/add-agent-assistant/design.md)、[任务](changes/add-agent-assistant/tasks.md)、[验收](changes/add-agent-assistant/validation.md) |
| 资料检索与引用 | 本班本科目过滤、文件指纹、真实摘录、本轮有效编号、夹角等公式召回改进 | [rag-search](specs/rag-search/spec.md) | [检索验收](changes/add-rag-search/validation.md)、[引用验收](changes/harden-citation-provenance/validation.md) |
| 教研组资料 | 教师版 MD/图文 ZIP、同科共享、去答案学生版预览、编辑核对、多班发布、知识点标签 | [research-materials](specs/research-materials/spec.md) | [设计](changes/add-research-materials/design.md)、[任务](changes/add-research-materials/tasks.md)、[验收](changes/add-research-materials/validation.md) |
| 智能备课 | 组内素材生成教师教案、编辑/章节重写、审阅定稿、版本、新修订、两种学生稿、分班发布 | [smart-lesson-prep](specs/smart-lesson-prep/spec.md) | [提案](changes/add-smart-lesson-prep/proposal.md)、[设计](changes/add-smart-lesson-prep/design.md)、[任务](changes/add-smart-lesson-prep/tasks.md)、[验收](changes/add-smart-lesson-prep/validation.md) |
| 教案共享 | 教师定稿默认私有，主动发布独立副本到同科教研组，可查阅/复用，学生不可见 | [smart-lesson-prep](specs/smart-lesson-prep/spec.md)、[research-materials](specs/research-materials/spec.md) | 同上备课及资料变更 |
| 配图与导出 | 中文空格图片路径、鉴权原图、图文包、统一“预览与下载”、浏览器打印/另存 PDF | [material-upload](specs/material-upload/spec.md)、[research-materials](specs/research-materials/spec.md)、[smart-lesson-prep](specs/smart-lesson-prep/spec.md) | 对应资料及备课验收 |
| 学生搜索/提问历史 | 每账号/班级/科目/功能最近 10 条，浏览器保存，搜索历史可重搜，提问历史仅回填 | [student-workspace](specs/student-workspace/spec.md) | [工作空间任务](changes/align-teacher-student-workspaces/tasks.md)、[验收](changes/align-teacher-student-workspaces/validation.md) |
| 页面与导航 | 班主任模块按身份常驻、单科资料入口、助手配置独立菜单、学生资料切科布局稳定 | [teacher-workspace](specs/teacher-workspace/spec.md)、[student-workspace](specs/student-workspace/spec.md) | [工作空间变更](changes/align-teacher-student-workspaces/proposal.md)、[单科资料变更](changes/add-subject-materials-navigation/proposal.md) |
| 运行可靠性 | Windows Docker SQLite 日志模式、数据库读健康检查、异常 503、业务数据保留 | [runtime-reliability](specs/runtime-reliability/spec.md) | [提案](changes/harden-runtime-reliability/proposal.md)、[设计](changes/harden-runtime-reliability/design.md)、[任务](changes/harden-runtime-reliability/tasks.md)、[验收](changes/harden-runtime-reliability/validation.md) |

认证、初始密码限制、刷新恢复、学生导入和班主任权限另见 [登录规约](specs/login-and-account-system/spec.md)、[身份权限](specs/teacher-identity-and-permissions/spec.md)、[角色权限](specs/rbac-role-permissions/spec.md)、[班级隔离](specs/class-data-isolation/spec.md)。

## 业务链路与数据边界

1. 教师在 `/teacher/library` 导入本科目教师版 MD 或图文 ZIP。教师原稿及答案只在同科教研组使用。
2. 在 `/teacher/lesson-prep` 选组内素材、任教班级、课题与课时，生成教师教案，编辑/审阅后定稿。完整教案默认本人私有，可主动共享当前定稿到教研组。
3. 从定稿生成学生可见教案和配套学生讲义，分别编辑、人工核对无答案/教师提示，再选择任教班级发布。发布的是独立学生稿，不是完整教师稿。
4. 学生在 `/materials` 查看本班已发布资料；助手在 `/student?view=assistant&subject=math` 等学科视图中，检索本班本科目的已索引学生资料。教研组原稿、私人完整教案不进入学生问答。
5. 资料页列表搜索仅匹配描述/标签，学科筛选是返回数据的元数据过滤；助手正文检索另走 RAG。两者不能混称同一个完整语义搜索功能。

## 已实现功能的边界

- 解题引导开启时覆盖教师自定义提示词，不会删除已保存内容；关闭后恢复自定义或默认提示词。
- `[n]` 是学生问答本轮来源编号，`[S1]` 等是教师备课来源快照。编号/指纹核对不等于自动证明每个结论的语义与计算正确。
- 快捷搜索/提问历史仅在当前浏览器保存，与后端真实会话独立，不跨设备同步。助手历史点击不自动调用 AI。
- 教研组直接导入目前支持 MD/图文 ZIP。班级直传支持更多文件格式，不代表教师版 Word/PDF 已能自动生成备课资料或可靠去除答案。
- 配图使用已导入原图，当前没有自动绘制新几何图；浏览器另存 PDF 不等于后端 PDF 转换服务。
- 作业批改、错题收录/讲解、真实学情诊断、技能注册、MCP 连接仍是演示或待接入；不作为已完成业务交付。
- AI 生成受模型遵循程度影响。学生稿正文、配图答案、公式和引用仍须教师核对。

## 检查与交接

在项目根目录执行：

```powershell
openspec validate --all --strict --no-interactive
```

文档校验只检查规约结构，不能替代功能测试。对应回归入口位于 `apitest/`：

| 检查入口 | 覆盖范围 |
| --- | --- |
| `check_lessons_2_5.py` | 认证权限、分科助手、会话、引导与引用 |
| `check_formula_retrieval.py` | 公式召回、原始摘录和来源过滤 |
| `check_research_materials.py` | 组内导入、学生版与发布隔离 |
| `check_lesson_prep.py` | 教案状态、并发版本、学生稿发布和可选共享 |
| `check_sqlite_storage.py` | 日志模式、事务和数据库健康检查 |
| `check_markdown_images.cjs` | 中文空格配图真实 Markdown 解析 |
| `check_recent_history.cjs` | 快捷历史持久化、隔离、清空及异常存储 |

真实 AI 试跑使用 `probe_tutor_guidance.py --real-llm`，会访问模型服务并产生费用；已有验收使用虚构题目/片段，不能将其表述为对真实学生数据的全面验证。本次规约同步不重新调用 AI、不修改业务数据、不提交 Git。

部署、数据目录及备份说明见项目根目录 [DEPLOYMENT.md](../DEPLOYMENT.md)。交接时将源码、`openspec/` 和验证脚本一起纳入团队版本管理；密钥、真实数据库、上传资料及 `.review/` 本地证据不随源码公开。
