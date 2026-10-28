# 第 7 课任务清单对照（2026-10-28）

依据：[第 7 课任务清单](https://devops.hello1023.com/课程任务清单-第7课.html)与[第 7 课课件](https://devops.hello1023.com/课件/第7课-课件-小组项目启动/index.html)。对照对象是 `main` 分支的提交 `a86e19f`。

> 本文件是实施前（2026-10-28）的差距分析。实施后的逐条结果、证据与剩余待办见 [`docs/lesson-07/verification.md`](../../../docs/lesson-07/verification.md)。

“对应任务”一列指向本变更 `tasks.md` 中的编号。标“人工”的项由组长或组员自己完成，不在本变更里。

## 先做这三件事

1. **先对照 `tasks.md` 看自己做过哪些。** 本规约基于 `a86e19f`。如果你已经在本地改过 `/health`、日志或规则文件，先改规约（删掉或调整对应任务），再实现，避免两套写法并存。
2. **审“待决定”一节。** 你同意或修改后再执行；修改要写回 proposal / design / spec。
3. **按顺序执行。** 先跑 `openspec validate 2026-10-28-engineering-baseline --strict --no-interactive`，再用 `/opsx-apply` 从第 1 组（骨架）开始，一组验证通过再做下一组。

## 一、创建小组仓库

| 清单要求 | 现状 | 对应任务 |
| --- | --- | --- |
| 仓库名用课题短名，成员全部加入 | 仓库 `smrrrrr/CampusClaw-Group` 已存在 | 人工：确认成员和教师都有访问权限 |
| 写第一行代码前设好主干保护 | 未核实 | 人工：组长在 GitHub 上给 `main` 设置保护规则 |
| 首次提交含 README、.gitignore、可选 LICENSE | README、`.gitignore` 已有；没有 LICENSE，README 也没写许可证的选择 | 3.4 |
| `.gitignore` 先于代码入库；`.env.example` 只写键名 | 已满足：`.env`、数据库、上传目录都被忽略；`.env.example` 的密钥项为空 | — |
| 提交历史中没有密钥 | 已满足：用本机 `.env` 的 4 个密钥值检索全部 6 个提交，没有命中；通用密钥模式也没有命中 | 2.2 把这项做成自动检查 |
| 变更以 `YYYY-MM-DD-短横小写英文名` 命名，提交信息写清依据 | 已有的变更没有日期前缀；README 没写命名和提交信息约定 | 3.4；本变更已按新约定命名 |
| 每人 clone 后按 README 跑通一次 | README 有启动步骤，没有写“启动后怎么确认成功” | 3.4、4.2；人工：每位组员各跑一次 |

## 二、明确功能边界，完成规约制定

| 清单要求 | 现状 | 对应任务 |
| --- | --- | --- |
| `openspec init`，用 propose / validate / apply / archive | 已初始化；21 份主规约 `--strict` 全部通过 | — |
| 价值三问、编号能力清单、“这次不做”的事 | 本变更的 `proposal.md` 已写：价值三问、能力 C1–C5、5 条不做、2 个被放弃的候选 | — |
| proposal / design / specs / tasks 四份文件齐全，骨架任务排最前 | 本变更四份文件齐全，`tasks.md` 第 1 组就是骨架 | — |
| Scenario 三段式；参数非法、无权限、资源不存在、依赖不可达四类失败路径；数值写具体 | 24 个场景，用 GIVEN / WHEN / THEN 三段；四类失败路径都覆盖；超时 2 秒、密钥至少 32 字符、标识 8–64 位等都写成了数字 | — |
| `--strict` 通过；新会话能照做；能力与场景能列成两列表 | `--strict` 已通过；新会话验证和对照表还没做 | 4.3、4.4 |

## 三、制定工程规范

现状：只有 `AGENTS.md` / `CLAUDE.md` 里的 5 条项目规则，没有任何规范文件，也没有技能。

| 清单要求 | 对应任务 |
| --- | --- |
| 产品设计、后端开发、安全开发、测试、部署运维五类规范写成文件 | 3.1 |
| 补充三类：AI 应用（含 10–20 条评测集）、数据、评审与完成定义 | 3.1 |
| 常驻约束写进规则（`AGENTS.md` / `CLAUDE.md` / 规则目录） | 3.2 |
| 按场景执行的流程写成技能 | 3.3 |
| 改一次代码验证规范生效，另起一次会话结果一致 | 4.3 |

写规范时用得上的项目事实（已核实）：

- **分层**：`routers/` → `*_service.py` → `models.py` / `database.py`，没有反向依赖。例外两处：`services.py` 和 `agent_service.py` 在业务层抛出 `fastapi.HTTPException`。
- **跨班访问**：现行主规约 `class-data-isolation` 要求返回 403 并写审计，和课件样例的 404 不同。
- **错误响应**：用 FastAPI 默认的 `{"detail": ...}`，没有统一错误码，路径也没有 `/api/v1` 前缀。
- **提示词**：写在代码常量里（`llm_service.py`、`lesson_service.py`、`question_service.py`），没有版本号。
- **数据迁移**：`database.run_simple_migrations()` 里手写 `ALTER TABLE`，没有迁移文件。

## 四、创建项目框架（骨架）

| 清单要求 | 现状 | 对应任务 |
| --- | --- | --- |
| 结构符合分层 | 符合，但没有自动检查 | 2.1 |
| 配置全部外置，缺失即启动失败 | `JWT_SECRET_KEY` 在代码里有默认值 `campusclaw-dev-secret`；Compose 有 `:?` 保护，但直接用 uvicorn 启动时会带默认值运行 | 1.2 |
| 免认证的 `/health`，返回依赖连通状态 | `/api/health` 免认证，只报数据库；没有版本、时间、MCP 与模型状态；Nginx 下没有 `/health` 路径 | 1.1、1.5、1.6 |
| 日志一行一条 JSON，带请求标识 | 后端用 uvicorn 默认文本日志，没有 `request_id` | 1.3、1.4 |
| clone → 填 `.env` → 一条命令 → `/health` 成功 | `docker compose up -d --build` 能启动；README 没写检查 `/health` 这一步 | 3.4、4.2 |
| 归档变更并打标签（如 `v0.0.1-skeleton`） | 仓库没有任何标签 | 4.5 |

## 五、核查清单（提交前逐条打勾）

| 维度 | 状态 | 还差什么 |
| --- | --- | --- |
| 仓库 | 部分完成 | 教师访问权限；README 补协作约定与验证步骤 |
| 规约 | 部分完成 | 新会话照做验证；能力—场景对照表 |
| 规范 | 未完成 | 八份规范、规则、技能，以及生效验证 |
| 骨架 | 未完成 | 配置缺失即失败；`/health` 依赖状态；JSON 日志 + `request_id`；分层检查 |
| 交付 | 未完成 | 版本标签；`docs/lesson-07/` 验证记录；交叉评审（另一名组员在自己机器上从零启动成功） |

## 改动前的基线测试（2026-10-28）

- `openspec validate --all --strict --no-interactive`：21 项全部通过。
- `apitest/check_*.py` 离线回归：8 个通过（formula_retrieval、lesson_prep、lessons_2_5（122/122）、mcp_tools（62/62）、model_json（65/65）、question_bank（115/115）、research_materials、sqlite_storage）。`check_apitest_harness.py` 因 `backend/.venv` 缺少 pytest 没能运行。
- `apitest/check_*.cjs`：2 个通过。
- **发现的问题**：回归脚本以项目根目录为工作目录运行时，会读到根目录 `.env` 里的真实模型 Key 并连接课程网关，会消耗每日额度。tasks.md 2.3 在门禁里用环境变量覆盖来隔离。

## 待决定

| 事项 | 规约当前写法 | 理由 |
| --- | --- | --- |
| 跨班访问用 403 还是 404 | 保留 403，作为书面例外写进安全规范 | 现行主规约要求 403 加审计；改成 404 要另起一次变更 |
| 统一响应结构与 `/api/v1` 前缀 | 本次不改，作为书面例外写进后端规范 | 改动面涉及 9 个路由文件和前端，超出一组任务 |
| 健康检查是否实际调用模型 | 不调用，只报“已配置 / 未配置” | 探针每 10 秒一次，会耗光每日额度 |
| `JWT_SECRET_KEY` 最短长度 | 32 个字符 | 恢复脚本生成 44 个字符，已满足 |
| 版本号与标签 | `1.2.0`，标签 `v1.2.0-baseline` | 项目已有 v1.1，`v0.0.1-skeleton` 会造成误解 |
| 变更名带日期前缀 | `2026-10-28-engineering-baseline` | 课程要求带日期；归档时 openspec 会再加一次日期，目录名会变成 `2026-10-28-2026-10-28-…` |
