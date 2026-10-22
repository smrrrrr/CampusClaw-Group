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
