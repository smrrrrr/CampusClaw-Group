# MCP 工具集成 · 实施与验收记录（2026-10-22）

本文件记录 `add-mcp-tool-integration` 本次实际执行内容、验证结果与未覆盖项。
历史文档不能替代功能测试，本文按“实际跑过”口径填写。

## 实际执行

| 环节 | 命令/方式 | 结果 |
| --- | --- | --- |
| 数据库备份 | SQLite backup API → `data/current/before-mcp-tool-integration-20261022-225120.db` | `integrity_check = ok`，23 张表，4 用户/7 资料/1 教案 |
| MCP 服务功能 | 本地 uvicorn + 真实 HTTP | health 200；无令牌/错令牌/非 Bearer 均 401；空 `MCP_AUTH_TOKEN` 拒绝全部；initialize/tools/list/tools/call 正常；解析错误 -32700、未知方法 -32601、未知工具/缺参/超参/类型错/超长均 -32602；无关问题返回兜底说明 |
| 宿主管理接口 | 本地 uvicorn（临时库）+ 真实 HTTP | 学生 403、非任教班级 403、SSRF 三类地址 400、登记 201 且响应无令牌、同名 400、名称规则 400、他人/他班/不存在统一 404、删除后 404 |
| 连接/断开 | 同上 | 失败 502 且 `connected=false`；成功 200；连续连接工具条数不翻倍；断开后清单清空 |
| 技能文件 | 同上 | 合法保存 201；启用写“开启”、工具引用非法、缺空行、未知字段、重名、资料≠学科均 400；未连接服务器引用 400；学生 403；同伴删他人技能 404 |
| 隔离集成检查 | `apitest/check_mcp_tools.py`（临时库 + 虚构模型 + 虚构 MCP 客户端） | **39/39 通过**：权限、令牌不回传、连接失败/重复、引用校验、候选集、参数校验、调用上限分支、ok/denied/error 三类审计、记录归属隔离、未命中技能不发 meta |
| 既有回归 | `check_formula_retrieval` / `check_research_materials` / `check_lesson_prep` / `check_sqlite_storage` / `check_lessons_2_5` | 11/11、54/54、112/112、16/16、122/122 全部通过——未命中技能的提问、检索、引用与额度行为未变 |
| 前端 | `tsc --noEmit`、`next build` | 均通过；`/teacher`、`/student` 正常产出 |
| Docker 端到端 | 构建 `mcp-server` 与 `backend` 镜像，同 Compose 网络运行 | mcp 容器：health 200、401/401/200、tools/list 含两工具、tools/call 返回提示；宿主机 8090 不可直达。后端容器：启动建四张新表；登记→连接（发现 2 工具）→技能绑定→学生提问发出 `meta`（技能命中；无 Key 走降级 error，符合预期）→断开后 `meta.tool_calls` 为 denied 且写入审计 |
| 令牌边界 | 全仓 grep + 响应模型核对 | 源码/构建产物/跟踪文件均无令牌；`.env.example` 为空值；接口仅返回 `has_auth`；日志不打印令牌 |
| 规约校验 | `openspec validate --all --strict --no-interactive` | 28/28 通过（含 1 条 login 规约超长 INFO，非本次引入） |

## 未覆盖 / 未完成项

1. **任务 1.2 的“本机 `.env` 填入随机值”由使用者手动完成**：本次执行环境的文件安全策略禁止代理读写 `.env`（`secret.basename.env`）。`.env.example` 的新键已由本次补齐；使用者在项目根 `.env` 追加 `MCP_AUTH_TOKEN`、`MCP_TOKEN_KEY`、`MCP_ALLOWED_HOSTS=mcp-tools:8090`、`ENABLE_DOCS=false` 后，经 `docker compose config` 复核：四项均非空，`MCP_AUTH_TOKEN` 在 backend 与 mcp-tools 两侧一致，`MCP_TOKEN_KEY` 为 44 字符、解码 32 字节、`Fernet` 初始化与加解密往返成功。`.env` 本就被 `.gitignore` 忽略。
2. **任务 9.6 同伴交叉验证**：由使用者本人作为复核人，对照真实栈（`docker compose up` 后经 8081 入口）逐项复核以下四项并确认通过：
   - **服务器隔离**：同伴教师列表不含他人服务器；按编号访问他人/他班服务器返回 404，与不存在一致。
   - **令牌不回传**：登记/列表/工具接口响应中均搜不到令牌原文，只返回布尔 `has_auth`。
   - **断开即失效**：断开后同一技能绑定的引用在学生提问时状态为 `denied`，并写入审计记录。
   - **记录只看本人范围**：调用记录接口仅返回本人服务器在本班的记录，同伴教师查询为空、学生访问 403。

   复核结论据使用者口述记录，具体请求/响应证据由复核人自行留存；本文档不代其生成证据。
3. **真实模型的 ok 调用链路**：本地无 `DEEPSEEK_API_KEY`，端到端只走到“命中技能→发 meta→无 Key 降级”和“断开→denied”。`formula_hint` 被真实调用并写入 ok 记录的分支，已在隔离检查中用虚构模型桩覆盖，但未对真实 DeepSeek 复测。
4. **真实学生浏览器端到端**：未在浏览器里逐项点按；前端只做了类型检查与构建。
5. **句式检查的局限**：仅拦截已知中英文写法，不宣称完整防御提示词注入；硬防线是候选集、参数校验、次数上限与令牌不出服务端。

## 结论

除上述明确标注的未覆盖项外，规约中的管理接口、连接发现、技能保存校验、调用编排、`meta` 事件、审计与隔离均已在隔离检查或端到端测试中通过验证。任务 9.6 的四项复核由使用者本人确认通过并据实记录；真实模型 ok 链路与浏览器端到端仍待后续补测。

## 归档记录（2026-10-23）

- 39/39 任务完成；`openspec validate add-mcp-tool-integration --strict` 通过。
- 已把 delta 合入主规约：新建 `specs/mcp-tool-integration/spec.md`（10 条 Requirement）；`specs/agent-assistant/spec.md` 由 14 条变为 16 条（新增“教师技能文件”“学生提问的技能路由”“助手技能与 MCP 配置界面”，删除“高级助手控件的预览边界”，SSE 流式回答替换为新版）。
- 归档到 `changes/archive/2026-10-23-add-mcp-tool-integration/`。
- **已知遗留问题**：`harden-citation-provenance` 与 `harden-foundation-and-align-specs` 两个历史变更早已完成但从未归档，它们的 `agent-assistant` delta 基于旧主规约（引用已删除的“高级助手控件的预览边界”和旧版 SSE 场景）。主规约更新后，`openspec validate --all` 会对这两个**未归档**变更报 delta 不一致。这是既有归档债务，非本变更引入；已按使用者决定暂不处理，后续应由负责组员按时间顺序归档这两个旧变更并解决其 delta 差异。
  - 已解决（2026-10-23）：两个旧变更中过时的「SSE 流式回答」MODIFIED 块已删除。这两块内容与 MCP 之前的主规约一致，按原样归档会冲掉 MCP 新增的 `meta` / `tool_calls` 要求；两个变更的其余增量未改动。SSE 中「`meta` 推送时机」的规约与实现差异，另由变更 `align-sse-meta-single-push` 改为「工具调用循环结束后只发送一次」，并已正常归档写入主规约。`harden-citation-provenance` 的其余增量已全部同步到主规约，按 `--skip-specs` 归档，主规约未改动。「高级助手控件的预览边界」不在这两个变更里，仍由 `subject-teacher-assistants`、`align-teacher-student-workspaces` 引用，校验只给出 INFO，不影响通过，留待这两个变更归档时处理。处理后 `openspec validate --all --strict --no-interactive` 结果为 22 passed、0 failed。

## 归档后核查与补测（2026-10-23）

归档后对照 tasks.md 逐项核查。本节只记录实际跑过的内容；没有改动规约、tasks.md 勾选和接口行为。

### 核查时实测

| 项 | 方式 | 结果 |
| --- | --- | --- |
| 隔离检查与回归 | `check_mcp_tools`、`check_formula_retrieval`、两个 `.cjs` | 39/39、11/11、两个 `.cjs` 均通过 |
| 真实工具服务 | 在 backend 容器内用真实 `McpClient` 连接 `mcp-tools:8090` | 发现 2 个工具；`formula_hint` 只返回提示，不给数值答案；无令牌 401；错令牌、参数不合、未知工具均被拒绝 |
| 文档入口 | 经 8081 | `/docs`、`/openapi.json` 均 404（`ENABLE_DOCS=false`） |
| 令牌泄露 | 前端构建产物、镜像历史、容器日志、git 跟踪文件中搜索令牌 | 均为 0 处；backend 与 mcp-tools 两侧令牌一致（只比较，不输出） |

### 发现的缺口

| 任务 | 缺口 |
| --- | --- |
| 8.3 | `openspec/README.md` 的 MCP 链接仍指向归档前的路径，均为断链 |
| 8.2 | OpenAPI 只给部分接口写了 401/403，多数接口缺少这两项说明 |
| 9.1 | 调用上限（每问 4 次、决策 3 轮、会话累计 20 次）、候选集外工具、令牌加解密与密钥轮换、地址白名单没有对应用例；原「调用上限分支」只覆盖到参数校验 |
| 9.2 | HTTP 用例没有「连接 → 技能 → 学生提问 → meta → 审计」链路；连接用例在 502 时跳过，连接失败会被当成通过 |
| 9.3 | `.cjs` 回归在上文没有运行记录 |
| 9.6 | 四项交叉复核只有口述记录，没有请求与响应证据 |
| 9.7 | `openspec validate --all` 为 27 通过、2 失败，失败项是上文已记录的两个未归档旧变更 |

另有两处小问题：编排在令牌解不开时以空令牌发起调用，审计记为「无法连接」，而不是「令牌需重新填写」；`routers/mcp.py` 中 `_token_for` 的注释写「置未连接」，代码实际只返回 400。

### 本轮补测与修正

| # | 内容 | 验证 |
| --- | --- | --- |
| 1 | README 的 MCP 提案、设计、任务链接改为归档路径，并新增验收记录链接 | 链接扫描：MCP 相关链接均可达。剩余 1 处断链是 `specs/smart-question-generation/spec.md`，该变更尚未归档，属预期 |
| 2 | `routers/mcp.py`、`routers/skills.py` 在路由器级补 401（未登录或令牌无效）与 403（非教师或非任教班级），路由级已有的 403 说明保留；`_token_for` 注释改为与代码一致 | `app.openapi()`：12 个 `/api/mcp/*`、`/api/teacher/skills*` 操作全部含 401 与 403 |
| 3 | `check_mcp_tools.py` 新增 19 条：未登录 401 三条、学生连接服务器 403、令牌加解密三条（密文不含原文且可解回、换密钥后提示重新填写令牌、未配置密钥拒绝保存）、地址校验七条（拒绝 localhost、内网、非 http、带用户名密码、元数据域名、白名单外主机；白名单地址通过）、上限与候选集五条（每问超出 2 次记 denied 并写审计、轮次上限 3、会话已有 19 次时只再执行 1 次、候选集外工具 denied 且不执行不写审计） | **58/58 通过** |
| 4 | 新增 `apitest/cases/api/mcp/CHAIN.py`：班级 102 登记服务器 → 连接真实 `mcp-tools` → 保存引用 `formula_hint` 的技能 → 学生提问 → 断言 `meta` 帧带技能名且先于 `delta` → AI 可用时断言 `meta.tool_calls` 为 ok 且调用记录可查。`GET.py` 的连接用例改为：令牌从 `APITEST_MCP_TOKEN` 传入，未提供时跳过并写明原因，连接失败按失败处理。`conftest.py` 的测试账号允许用环境变量覆盖 | 见下 |

链路用例的运行方式：在 scratch 目录新建空测试库，只含自建的两个测试班和两个测试账号，不复制演示数据；用本轮镜像 `docker compose run --no-deps -p 127.0.0.1:8001:8000` 起临时后端，接入 compose 网络以访问 `mcp-tools:8090`。演示库没有参与。

| 运行 | 结果 |
| --- | --- |
| `pytest cases/api/mcp`（令牌正确） | 7 通过、1 跳过。跳过的是 ok 审计一条：容器内 `DEEPSEEK_API_KEY` 为空，聊天返回「AI 生成服务未配置 API Key」 |
| 同上（令牌故意写错） | 连接用例与链路用例均失败，报 502「MCP 服务拒绝了令牌（401）」，不再被跳过 |
| 用例结束后 | 临时库中服务器、技能均为 0（用例自行清理） |

其余运行：

| 命令 | 结果 |
| --- | --- |
| `check_formula_retrieval`、`check_question_bank`、`check_lesson_prep`、`check_research_materials`、`check_sqlite_storage`、`check_lessons_2_5` | 11/11、68/68、112/112、54/54、16/16、122/122 |
| `node apitest/check_markdown_images.cjs`、`node apitest/check_recent_history.cjs` | 均通过 |
| `openspec validate --all` | 27 通过、2 失败（仍是 `harden-citation-provenance`、`harden-foundation-and-align-specs` 的 `SSE 流式回答` delta 缺两条新场景），与归档记录一致 |
| `docker compose up -d --build backend` | healthy；容器内为本轮代码 |
| 8081 冒烟 | `/api/health` 200；三个 MCP 与技能列表接口未登录均 401；`/docs`、`/openapi.json` 404 |

### 仍未覆盖

1. **真实模型提议调用 → ok 审计**：本机 `.env` 的 `DEEPSEEK_API_KEY` 只有 1 个字符，容器内为空。链路用例已写好，配置有效 Key 后重跑 `CHAIN.py` 即可验证这一段；在此之前只有隔离检查中的虚构模型覆盖。
2. **任务 9.6**：仍只有使用者口述，没有请求与响应证据。四项中的服务器隔离、令牌不回传、断开即 denied、记录只看本人范围，在 `check_mcp_tools.py` 中都有对应断言；但「同伴交叉复核」的本意是由另一位组员在真实栈上复核，建议补一次并留存证据。
3. ~~**任务 9.7**：两个旧变更的 delta 冲突仍待负责组员处理。~~ 已解决，处理方式见上文「归档记录」中「已知遗留问题」下的后续说明。`openspec validate --all --strict --no-interactive`：22 passed、0 failed。
4. **令牌解不开时的审计口径**：编排仍以空令牌调用并记为「无法连接」。若要改为提示「令牌需重新填写」，属于行为变更，需先改规约。
5. **apitest 默认账号**：`conftest.py` 默认学生账号 `20230002` 与当前演示库（`20260002`）不一致。本轮只增加了环境变量覆盖，没有改默认值。
   - 后续（2026-10-23，智能命题第四轮）：默认值已改为种子表的 `20260002`。`CHAIN.py` 在模型未提议调用工具时改为跳过并写明原因。MCP 与技能接口路由级重复的 403 已删除。详见 `add-smart-question-generation/validation.md` 第四轮。
