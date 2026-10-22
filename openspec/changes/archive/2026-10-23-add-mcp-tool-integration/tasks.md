## 1. 准备

- [x] 1.1 用 SQLite backup API 备份 `data/current/campusclaw.db` 为 `before-mcp-tool-integration-<时间>.db`，`PRAGMA integrity_check` 返回 ok
- [x] 1.2 根 `.env.example` 增加 `MCP_AUTH_TOKEN=`、`MCP_TOKEN_KEY=`、`MCP_ALLOWED_HOSTS=mcp-tools:8090`、`ENABLE_DOCS=false` 及中文说明；本机 `.env` 填入随机值，`git status` 确认 `.env` 未被跟踪

## 2. 自建 MCP 工具服务（mcp-server/）

- [x] 2.1 新建 `mcp-server/`（FastAPI、`pyproject.toml`+`uv.lock`、Dockerfile、`.dockerignore`），实现 `GET /health` 与 `POST /mcp` JSON-RPC 分发；本地 `curl /health` 返回 200
- [x] 2.2 实现 Bearer 校验（取 `MCP_AUTH_TOKEN`，未配置时拒绝全部 `/mcp`），无令牌/错误令牌返回 401；用 curl 验证三种情况
- [x] 2.3 实现 `initialize`、`tools/list`、`tools/call` 与 JSON-RPC 错误（解析错误、未知方法、未知工具、参数不合结构），验证各返回可读 `error`
- [x] 2.4 实现 `formula_hint`、`unit_convert` 两个只给提示的工具（说明写清适用场景与不给最终答案、JSON Schema 输入结构），`tools/call` 返回文本且不含最终数值答案
- [x] 2.5 `docker-compose.yml` 新增 `mcp-tools` 服务（仅 `expose: 8090`、healthcheck、注入 `MCP_AUTH_TOKEN`），`docker compose config --quiet` 通过；`docker compose exec backend` 内可访问 `http://mcp-tools:8090/health`，宿主机不可直连

## 3. 宿主侧数据与服务器管理

- [x] 3.1 `models.py` 新增 `McpServer`、`McpTool`、`AssistantSkill`、`McpToolCall` 及唯一键/索引；在数据库副本上启动后四张表被创建，旧表结构与行数不变
- [x] 3.2 `config.py` 增加 `mcp_token_key`、`mcp_allowed_hosts`、四项上限/超时配置；`pyproject.toml` 显式声明 `cryptography` 并同步 `uv.lock`，`uv sync --locked` 通过
- [x] 3.3 实现令牌加解密与 `has_auth`：未配置 `MCP_TOKEN_KEY` 时拒绝保存令牌；单元检查密文与原文不同、换密钥后解密失败给出「请重新填写令牌」
- [x] 3.4 实现 Base URL 校验（http/https、主机在允许清单、禁止重定向）；`127.0.0.1`、`backend:8000`、元数据地址均返回 400 且不发请求
- [x] 3.5 实现 `GET/POST /api/mcp/servers`、`PUT/DELETE /api/mcp/servers/{id}`：任教班级 403、他人/他班编号 404（与不存在一致）、学生 403、名称规则与同名 400、改地址或令牌即断开；响应全文不含令牌

## 4. 连接、发现与断开

- [x] 4.1 新增 `mcp_client.py`（JSON 与 SSE 响应解析、Bearer 头、超时）及 `initialize` → `notifications/initialized` → `tools/list`（分页、最多 50）流程
- [x] 4.2 实现 `POST /connect`：校验工具名/说明长度/inputSchema/句式检查，事务内整体替换缓存并置已连接；失败回滚、清空、置未连接并返回 502 可读原因；连续连接两次条数不翻倍
- [x] 4.3 实现 `POST /disconnect` 与 `GET /tools`（含完整说明与 inputSchema）；断开后清单为空
- [x] 4.4 验证远端停机时学生普通提问、检索与流式对话不受影响

## 5. 技能文件

- [x] 5.1 实现技能文件解析器（字段、长度、启用值、资料与学科一致、工具拆分、引用正则），对课件中合法/非法引用示例逐条断言
- [x] 5.2 实现保存期引用校验（服务器属于同教师同班、已连接、工具在缓存），错误指明具体引用
- [x] 5.3 实现 `GET/POST /api/teacher/skills`、`PUT/DELETE /api/teacher/skills/{id}`：重名 400、他人技能 404、学生 403，失败不部分保存

## 6. 调用编排与 SSE

- [x] 6.1 在 `chat` 中实现技能路由（绑定教师、本班本科目、已启用、关键词命中取最小 id），技能说明与固定边界声明进入系统提示；未命中时请求与响应与改动前一致（对比现有回归）
- [x] 6.2 `llm_service` 新增带 `tools` 的非流式决策调用，解析 `tool_calls`；用虚构模型桩验证解析多个调用
- [x] 6.3 实现候选集解析与 denied 判定（断开、不在缓存、服务器不存在、候选集外名称），可归属的 denied 写记录、不可归属的只进 `tool_calls`
- [x] 6.4 实现参数结构校验、带令牌 `tools/call`、结果截断与句式检查、工具消息回传，以及轮次/单次/会话累计上限与超限优雅降级
- [x] 6.5 每轮推送累计 `meta` 事件（`skill`、`tool_calls`，无调用时省略 `tool_calls`），最终作答把工具结果以来源标注拼入用户消息数据段后走原 `stream_chat`；未配置 Key 不进入循环
- [x] 6.6 每次可归属调用写 `mcp_tool_calls`（独立会话、失败不影响回答），实现 `GET /api/mcp/tool-calls?class_id=` 最近 50 条且只含本人服务器本班记录

## 7. 前端

- [x] 7.1 `lib/api.ts` 增加 MCP 服务器、工具、调用记录、技能接口及 SSE `onMeta` 回调，`tsc --noEmit` 通过
- [x] 7.2 教师助手配置页：MCP 面板（登记表单密码框提交即清空、列表只显示是否已配令牌、连接/断开/删除、工具完整说明与参数、最近调用记录）替换原预览按钮
- [x] 7.3 教师助手配置页：技能面板（列表、技能文件新建/改写/删除、显示服务端校验原因）；作业批改与错题讲解开关仍为预览并提示未接入
- [x] 7.4 学生助手页在回答正文前展示本次工具及状态（ok/denied/error 区分），未知事件忽略；`next build` 通过

## 8. 部署与文档

- [x] 8.1 后端注入 `MCP_TOKEN_KEY`、`MCP_ALLOWED_HOSTS`、`ENABLE_DOCS: ${ENABLE_DOCS:-false}`；Nginx 增加 `location = /docs`、`location = /openapi.json`；`ENABLE_DOCS=true` 时 `http://localhost:8081/docs` 可打开，缺省时不可访问
- [x] 8.2 为 `/api/mcp/*` 与技能接口补充 summary、响应模型与 400/401/403/404/502 说明，在 Swagger 中试调连接、工具列表、技能保存
- [x] 8.3 更新 `DEPLOYMENT.md`（新变量、令牌一致性、`MCP_TOKEN_KEY` 保管、交接包清空令牌列与调用记录）与 `openspec/README.md` 功能表

## 9. 测试与验收

- [x] 9.1 新增隔离检查 `apitest/check_mcp_tools.py`（TestClient + 数据库副本 + 虚构模型桩 + 以 TestClient 承载的 `mcp-server`），覆盖管理接口权限、令牌不回传、连接失败/重复连接、引用校验、候选集、上限、三种状态记录与隔离，全部通过
- [x] 9.2 在 `apitest/cases/api/mcp/` 按 URL 增加登记、连接、列出工具、断开及学生 403 用例，以及「连接 → 注册含 `formula_hint@…` 的技能 → 会话提问 → 审计出现 ok」链路用例；`run_all.py` 生成 HTML 报告且报告不入库
- [x] 9.3 运行既有 `check_*.py` 与 `.cjs` 回归，确认未命中技能的提问、检索、引用与额度行为不变
- [x] 9.4 Docker 端到端：`mcp-server` 单独验证（health、带令牌 tools/list、tools/call 文本），主机侧连接 → 发现 → 技能绑定 → 学生提问触发 → 审计含服务器与工具；断开后同一技能提问为 denied
- [x] 9.5 令牌边界检查：前端构建产物、Git 跟踪文件、镜像历史（`docker history`）、后端日志与接口响应中均搜不到 `MCP_AUTH_TOKEN` 值
- [x] 9.6 同伴交叉验证四项（服务器隔离、令牌不回传、断开即失效、记录只看本人范围）并留存请求/响应证据到验收记录
- [x] 9.7 `openspec validate --all --strict --no-interactive` 通过，并新建 `validation.md` 记录实际执行结果与未覆盖项
