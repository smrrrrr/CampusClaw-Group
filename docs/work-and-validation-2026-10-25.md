# 代码工作与验证记录（2026-10-22 至 10-25）

本文汇总接手后（基线提交 `642242e`）这一轮做过的代码工作、实际跑过的验证，以及仍未完成的检测，包括本轮之前的旧变更。各项的详细过程见对应变更目录下的 `validation.md`，本文只做索引和汇总。

所有结果都按“实际跑过”的口径记录：没跑过的写“未覆盖”，口述确认的也如实标明。

## 1. 代码工作

### 1.1 提交

| 提交 | 日期 | 内容 |
| --- | --- | --- |
| `99f476e` | 10-23 | MCP 工具集成（`add-mcp-tool-integration`） |
| `13c1cd2` | 10-25 | 智能命题、模型 JSON 反斜杠修补、题目渲染修复；一并提交 10-23 的旧变更归档 |
| `2ae00f6` | 10-25 | 同步 `align-teacher-student-workspaces` 中 teacher-workspace 的两个 MODIFIED 块 |
| `a6a7c56` | 10-25 | 命题公式结构校验、学生卷选项分行（`fix-quiz-latex-and-option-layout`）；归档 `add-material-upload`；交接文档整理（README、DEPLOYMENT.md、本文、`.env.example`、`.gitignore`） |

### 1.2 功能变更

| 变更（已归档） | 做了什么 | 主要代码 |
| --- | --- | --- |
| `add-mcp-tool-integration` | 自建 MCP 工具服务（`formula_hint`、`unit_convert`，只给提示不给答案）。教师登记、连接、发现、断开服务器，令牌 Fernet 加密存库。技能文件以 `工具名@服务器名` 引用工具。学生提问时服务端按候选集、参数校验和次数上限调用工具，发 `meta` 事件并写调用审计 | `mcp-server/`，`backend/mcp_client.py`、`mcp_crypto.py`、`mcp_orchestrator.py`、`skill_service.py`、`routers/mcp.py`、`routers/skills.py`；前端教师助手配置页的 MCP 面板、技能面板，学生回答的工具栏 |
| `align-sse-meta-single-push` | 只改规约：`meta` 在工具调用循环结束后只发一次，与实现一致 | 无代码改动；`check_mcp_tools.py` 补多轮断言 |
| `add-smart-question-generation` | 智能命题：按知识点 × 题型 × 难度生成结构化题目、逐题校验、人工复核（通过、修改、驳回）、学科题库、按配比组卷、定稿、去答案的学生卷分班发布、答案卷、审计。入口 `/teacher/quiz` | `backend/question_service.py`、`routers/quiz.py`、`models.py`（新增 6 张表），`frontend/app/teacher/quiz/page.tsx` |
| `harden-model-json-escapes` | 修补模型输出中 LaTeX 单反斜杠导致的 JSON 解析失败，兜底控制字符；命题和学生稿共用。修补次数写服务端日志 | `backend/model_json.py`；`main.py` 给 `lesson_service` 配置 INFO 日志 |
| `fix-quiz-markdown-rendering` | 填空多空位不再被当作加粗；选项、填空和解答的答案按 Markdown/KaTeX 渲染 | `frontend/lib/markdown-blanks.ts`、`components/markdown-answer.tsx`、`globals.css` |
| `fix-quiz-latex-and-option-layout` | 逐题校验增加公式结构检查：`$` 须成对、公式内花括号须配对，题干、选项、答案、解析都查；不通过的题拒绝入库，修改和通过时返回 400。提示词补充花括号规则。学生卷选项每项一行，缩进随题号宽度 | `backend/question_service.py`（`check_formula_structure`、`render_student_paper`），`apitest/check_question_bank.py` |

### 1.3 部署与配置

- **新增 `mcp-tools` 服务**：Compose 新增该服务，只在内网暴露。后端增加 `MCP_AUTH_TOKEN`、`MCP_TOKEN_KEY`、`MCP_ALLOWED_HOSTS`、`ENABLE_DOCS` 四个变量。
- **Nginx**：转发 `/docs` 和 `/openapi.json`。默认 `ENABLE_DOCS=false`，这两个路径返回 404。
- **模型接口可配置**：后端支持 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`，可以切到课程网关（`course-chat`）。
- **后端镜像**：Dockerfile 去掉了 gcc 安装，所有依赖都有现成的 wheel。

### 1.4 OpenSpec 整理

- **10-23 归档 7 个已完成的旧变更**：
  - add-class-data-isolation
  - add-login-and-account-system
  - add-rag-search
  - add-rbac-role-permissions
  - add-research-materials
  - add-subject-materials-navigation
  - harden-citation-provenance

  其中 harden-citation-provenance 的增量早已在主规约里，用 `--skip-specs` 归档。同一天还归档了本轮的 add-mcp-tool-integration 和 align-sse-meta-single-push。
- **删除两处过时的 SSE 块**：`harden-citation-provenance`、`harden-foundation-and-align-specs` 各有一块过时的「SSE 流式回答」MODIFIED。按原样归档会冲掉 MCP 的 `meta` 要求，所以删掉了。
- **10-25 归档本轮三个变更**：add-smart-question-generation、harden-model-json-escapes、fix-quiz-markdown-rendering，按依赖顺序归档。归档前，把后两个变更 MODIFIED 块里缺的前序规则补齐。
- **10-25 归档 `add-material-upload`**：47/47 任务完成，主规约本来就一致，用 `--skip-specs` 归档。
- **修正 `align-teacher-student-workspaces`**：它的两个 teacher-workspace MODIFIED 块改为主规约现行全文，否则归档时会冲掉 `/teacher/quiz` 入口。
- **10-25 归档 `fix-quiz-latex-and-option-layout`**：只有 ADDED，主规约 smart-question-generation 新增 2 条需求（公式结构校验、学生卷选项排版）。
- **校验结果**：`openspec validate --all --strict --no-interactive` 现为 21 passed、0 failed。

## 2. 验证

### 2.1 当前回归（2026-10-25 重跑）

在项目根目录用 `PYTHONPATH=backend backend/.venv/bin/python apitest/<脚本>` 运行。脚本都使用临时数据库和假模型，不访问演示库，也不花模型额度。

| 脚本 | 结果 |
| --- | --- |
| `check_model_json.py` | 65/65 |
| `check_question_bank.py` | 115/115 |
| `check_lesson_prep.py` | 119/119 |
| `check_mcp_tools.py` | 62/62 |
| `check_research_materials.py` | 54/54 |
| `check_sqlite_storage.py` | 16/16 |
| `check_lessons_2_5.py` | 122/122 |
| `check_formula_retrieval.py` | 11/11 |
| `node apitest/check_markdown_images.cjs`、`check_recent_history.cjs` | 通过 |
| `openspec validate --all --strict --no-interactive` | 21/21 |

`check_mcp_tools.py` 运行时会尝试连接模型网关（既有行为）。本次连接被沙箱拦截，结果不受影响；在网络不受限的环境里运行，可能消耗网关额度。

### 2.2 各变更的端到端验证

| 变更 | 实际做过的验证 |
| --- | --- |
| MCP 工具集成 | **Docker 端到端**（8081）：登记 → 连接（发现 2 个工具）→ 绑定技能 → 学生提问发出 `meta` → 断开后状态为 `denied`，并写入审计。<br>**真实工具服务**：后端容器内的 `McpClient` 能连上 `mcp-tools:8090`。<br>**令牌泄露排查**：前端构建产物、镜像历史、容器日志、Git 跟踪文件中搜索令牌，均为 0 处。<br>**链路用例**：`cases/api/mcp/CHAIN.py` 在临时库和临时后端上跑过；令牌写错时按失败处理 |
| 智能命题 | **Docker 端到端**：组卷 → 定稿 → 学生卷不含答案 → 发布两班 → 学生可见；越权访问返回 403/404。<br>**真实网关复测**（10-24，`course-chat`）：3 次生成全部解析成功，同参数下此前 4 次失败 3 次。<br>**浏览器复核**：通过、修改、驳回各做一次，KaTeX 0 个渲染错误 |
| JSON 反斜杠修补 | 离线回放 10-23 抓到的两份真实失败输出：旧代码解析失败，新代码各得 5 题。<br>真实生成一份学生稿，渲染正常，未发布 |
| 题目渲染 | 浏览器验收，用教师 TEA001 和学生 20260002 两个身份：9 个 Scenario 全部通过（8 个在浏览器里验证，1 个由离线用例验证）。<br>同一渲染器上的备课页面没有回归 |
| 公式校验与选项排版 | **真实网关实测**（10-25）：生成 9 得 3 题，其中一题选项公式花括号不配对（`\vec{c`），促成本变更。<br>**浏览器复核**：试卷 3 的学生卷每道选择题为 2 段、选项间 3 个换行，KaTeX 0 个渲染错误 |

每次改表结构前都用 SQLite backup API 备份过，`integrity_check` 均为 ok。

## 3. 本轮变更仍未覆盖的验证

| 变更 | 未覆盖项 |
| --- | --- |
| MCP 工具集成 | 1. **真实模型提议调用工具 → ok 审计**：没测到，当时 Key 无效。配好 Key 后重跑 `apitest/cases/api/mcp/CHAIN.py` 即可验证。<br>2. **任务 9.6 同伴交叉复核**：只有口述记录，没有请求与响应证据，建议由另一位组员在真实栈上复核。<br>3. **浏览器验证**：没有在浏览器里逐项点按。<br>4. **令牌解不开时的审计口径**：目前记为“无法连接”，不是“令牌需重新填写”。要改属于行为变更，需先改规约 |
| 智能命题 | 1. **任务 9.3 同伴签字**：未完成，归档时如实保留未勾选。<br>2. **浏览器验证**：草稿编辑、答案编辑、“仅原作者可下架”没有在浏览器里逐项点按。<br>3. **任务锁与并发**：锁残留和并发登记只在函数层验证过，没有用真实的并发 HTTP 请求复测。<br>4. **旧题配图清单**：已入库旧题的 `assets_json` 没有回填，仍是整批清单 |
| JSON 反斜杠修补 | 1. **修补路径没在线上触发过**：真实复测里模型都写成了双反斜杠，`escape_repairs` 均为 0；正确性只由离线回放证明。<br>2. **日志修复后没再生成过**：修复日志后，没有再做一次真实的学生稿生成。<br>3. **学生端展示**：学生稿没有发布，没有以学生身份看过渲染效果 |
| 题目渲染 | 1. **构建**：`npm run build` 只由实现会话跑过。<br>2. **打印**：打印和另存 PDF 没有实测。<br>3. **两种写法只有离线用例**：学生 AI 回答里的长下划线、“下标紧挨空位”的写法。<br>4. **块级公式选项**：没有这样的题，未验证 |
| 公式校验与选项排版 | 1. **已知误判**：公式里以 `\\` 结尾、紧跟 `$`（如 `$a\\$`）会被误判为 `$` 不成对，当前库中 0 处命中。原因、绕开办法和修法见[验收记录](../openspec/changes/archive/2026-10-25-fix-quiz-latex-and-option-layout/validation.md#已知限制)。<br>2. **校验上线后没有再真实生成**：拒绝入库路径只由离线用例验证 |

**`apitest/conftest.py` 的默认账号**：默认值是种子账号和种子初始密码。在交接数据副本上运行接口用例时，要用 `APITEST_STUDENT_*`、`APITEST_TEACHER_*` 环境变量覆盖。

## 4. 旧变更未完成的检测

下表是本轮之前的变更里仍未完成的检测和验收，均来自各变更的 `tasks.md` 与 `validation.md`。这些变更都还没有归档；本轮没有补做这些检测，也没有改它们的勾选状态。

| 变更 | 未完成的检测 | 依据 |
| --- | --- | --- |
| `rework-account-permissions` | **5.1 接口用例**：数学教师访问英语教研资料被拒；班主任看本班全科学情放行，看其他班被拒；学生调用备课和教师接口返回 403。<br>**5.2 端到端冒烟**：教师登录 → 本学科教研资料 → 跨学科拒绝 → 班主任看本班全科学情。<br>**6.6 接口回归**：名单模式和重置密码权限，用学生和两位教师账号做完整回归。不能用源码检查代替 | tasks.md 5.1、5.2、6.6；该变更没有 validation.md |
| `align-teacher-student-workspaces` | **5.1**：学生身份下六个页面的桌面、窄屏视觉与交互验收。<br>**规约同步检查**：只用本地脚本做过，没有重跑登录、改密、密码重置、资料增删和 Docker 测试 | tasks.md 5.1；validation.md「Validation Limits」 |
| `harden-foundation-and-align-specs` | **2.6**：完整学生页面、窄屏，以及真实讲义从浏览器上传到被引用的端到端验收 | tasks.md 2.6 |
| `subject-teacher-assistants` | 学生在真实浏览器中提问和流式显示的视觉验收；收费模型的作答效果；窄屏 | tasks.md 未勾选项；validation.md「限制」 |
| `add-agent-assistant` | **429 超限审计**：目前只有限额和 429 响应，没有写审计。<br>**解题引导真实模型试跑**：只用虚构样例跑过 6 次，不保证每次都遵循引导规则 | tasks.md；validation.md |
| `add-smart-lesson-prep` | **真实讲义联网试跑**：没做，因为没有把真实讲义发给模型的授权，只用虚构资料验证过。<br>**答案与引用检查的局限**：答案标记、图片指纹和来源编号检查都不是语义证明，正文仍需人工核对 | validation.md「Limits」 |
| `harden-runtime-reliability` | 多副本、高可用存储与自动故障恢复没有实现，也没有测试 | tasks.md |

已归档的旧变更在验收记录里写明的限制：

| 变更 | 限制 |
| --- | --- |
| `add-research-materials` | 发布到真实班级只用隔离测试覆盖过；分区提取答案对任意排版不可靠，需要教师核对 |
| `add-rag-search`、`harden-citation-provenance` | 编号和出处正确不等于结论被原文支持；夹角公式引用只用虚构样例做过真实模型试跑 |
| `add-material-upload` | `.txt` 预览只做了代码核对，没有在浏览器里验证 |
| `add-class-data-isolation`、`add-rbac-role-permissions`、`add-login-and-account-system`、`add-subject-materials-navigation` | 没有单独的 validation.md，相关回归在 `check_lessons_2_5.py` 中 |

### 4.1 尚未实现的功能任务（不属于检测，列出供参考）

- 作业提交与批改、错题收录与讲解、学情画像、首页统计接入真实接口（`align-teacher-student-workspaces` 5.3）。目前这些页面是演示数据，相关表为空。
- 学生助手学科切换与技能状态回读，错题讲解传入具体上下文（同上 5.4）。
- 作业批改和错题讲解技能（`add-agent-assistant` 10.4、`align-teacher-student-workspaces` 5.5）。
- 教师全科/单科学情、作业、公告、完整审计统计（同上 5.6）。
- 旧数据库班级名称迁移，本地 standalone 自动打包启动（同上 5.7）。
- Word/PDF 教师原稿解析、服务端 PDF/Word 导出（`add-smart-lesson-prep`）。

### 4.2 归档注意

- `subject-teacher-assistants`：它对 agent-assistant 规约的修改块与当前主规约对不上，现在直接归档会失败，要先对齐。
- `subject-teacher-assistants`、`align-teacher-student-workspaces`：都还引用已删除的「高级助手控件的预览边界」。校验只报 INFO，归档时需要一并处理。
