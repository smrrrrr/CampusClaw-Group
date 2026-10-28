## MODIFIED Requirements

### Requirement: 数据库可读性纳入健康检查

`GET /api/health` MUST 免认证访问，Nginx MUST 另把 `GET /health` 转发到同一处理。处理 MUST 实际连接数据库并查询 users 表。数据库可读时 MUST 返回 HTTP 200 与 JSON：`status`（`ok` 或 `degraded`）、`version`（后端 `version.py` 中的版本号）、`time`（UTC，ISO 8601，以 `Z` 结尾）、`dependencies`（`database`、`mcp_tools`、`model` 三个键）。`dependencies.database` 为 `ok`；`dependencies.mcp_tools` 在配置了 `MCP_TOOLS_HEALTH_URL` 且该地址 2 秒内返回 2xx 时为 `ok`，返回非 2xx 或超时为 `unreachable`，未配置时为 `not_configured`；`dependencies.model` 在 `DEEPSEEK_API_KEY` 非空时为 `configured`，否则为 `not_configured`，MUST NOT 为此发起模型调用。`mcp_tools` 为 `unreachable` 时 `status` MUST 为 `degraded`，否则为 `ok`。SQLAlchemy 数据库异常 MUST 返回 HTTP 503 与通用“数据库暂不可用，请稍后重试”提示。任何情况下响应 MUST NOT 包含 URL、主机名、配置键名、SQL、文件路径或异常原文，MUST NOT 写入业务记录。Compose 后端健康检查 MUST 调用该接口。

#### Scenario: 数据库读取正常

- **GIVEN** 数据库可读，`MCP_TOOLS_HEALTH_URL` 指向的服务返回 200，`DEEPSEEK_API_KEY` 非空
- **WHEN** 未携带任何令牌请求 `GET /api/health`
- **THEN** 返回 200，`status` 为 `ok`，`version` 等于 `version.py` 中的版本号，`time` 以 `Z` 结尾，`dependencies` 为 `{"database":"ok","mcp_tools":"ok","model":"configured"}`，业务表行数不变

#### Scenario: 经 Nginx 的 /health 别名

- **GIVEN** 按 Compose 启动全部服务
- **WHEN** 浏览器请求 `http://localhost:<CAMPUSCLAW_PORT>/health`
- **THEN** 返回与 `/api/health` 相同结构的 JSON，而不是前端页面

#### Scenario: 数据库存储异常

- **GIVEN** 健康检查的数据库读取抛出 SQLAlchemyError，异常文本含 SQL 与文件路径
- **WHEN** 请求 `GET /api/health`
- **THEN** 返回 503，`detail` 为“数据库暂不可用，请稍后重试”，响应体不含该 SQL 与路径，容器健康探针识别失败

#### Scenario: MCP 工具服务不可达

- **GIVEN** 数据库可读，`MCP_TOOLS_HEALTH_URL` 指向的地址 2 秒内无响应或返回 500
- **WHEN** 请求 `GET /api/health`
- **THEN** 返回 200，`status` 为 `degraded`，`dependencies.mcp_tools` 为 `unreachable`，响应体中不出现该地址

#### Scenario: 依赖未配置

- **GIVEN** 数据库可读，未设置 `MCP_TOOLS_HEALTH_URL`，`DEEPSEEK_API_KEY` 为空
- **WHEN** 请求 `GET /api/health`
- **THEN** 返回 200，`status` 为 `ok`，`dependencies.mcp_tools` 与 `dependencies.model` 均为 `not_configured`，不发起任何出站请求

#### Scenario: 携带无效令牌访问健康检查

- **GIVEN** 请求头带伪造的 `Authorization: Bearer forged-token`
- **WHEN** 请求 `GET /api/health`
- **THEN** 仍返回 200 与上述结构，响应中不含任何用户、角色或班级信息

## ADDED Requirements

### Requirement: 请求标识与单行 JSON 日志

后端 MUST 为每个 HTTP 请求确定一个 `request_id`：请求头 `X-Request-ID` 匹配 `^[A-Za-z0-9._-]{8,64}$` 时采纳，否则生成 32 位小写十六进制值。响应 MUST 带 `X-Request-ID` 头，值等于该 `request_id`，包括 401、403、404、422、500、503 等错误响应与 SSE 流式响应。每个请求 MUST 输出恰好一行 JSON 访问日志，字段为 `ts`（UTC ISO 8601）、`level`、`module`（值 `access`）、`request_id`、`method`、`path`（不含查询串）、`status`、`duration_ms`。后端业务模块日志与 uvicorn 启动日志 MUST 同为单行 JSON，至少含 `ts`、`level`、`module`、`request_id`（请求之外为 null）、`msg`。日志 MUST NOT 包含查询串、`Authorization` 头、Cookie、口令、令牌或任何 `.env` 中的密钥值。

#### Scenario: 正常请求的标识与访问日志

- **GIVEN** 后端已启动，日志输出到标准错误
- **WHEN** 不带 `X-Request-ID` 请求 `GET /api/health?probe=1`
- **THEN** 响应头 `X-Request-ID` 为 32 位十六进制；日志中恰有一行 `module` 为 `access` 的 JSON，其 `request_id` 与响应头相同，`path` 为 `/api/health`（不含 `probe=1`），`status` 为 200

#### Scenario: 采纳调用方传入的合法标识

- **GIVEN** 请求头 `X-Request-ID: lesson07-trace-0001`
- **WHEN** 请求 `GET /api/health`
- **THEN** 响应头 `X-Request-ID` 为 `lesson07-trace-0001`，访问日志的 `request_id` 相同

#### Scenario: 非法请求标识被替换

- **GIVEN** 请求头 `X-Request-ID` 为 7 个字符 `abc+def`，或为 65 个字符
- **WHEN** 请求 `GET /api/health`
- **THEN** 响应头 `X-Request-ID` 为服务端新生成的 32 位十六进制值，日志中不出现原值

#### Scenario: 未登录访问业务接口

- **GIVEN** 不携带令牌
- **WHEN** 请求 `GET /api/teacher/classes`
- **THEN** 返回 401，响应带 `X-Request-ID` 头；访问日志该行 `status` 为 401，日志中无 `Authorization` 与 Cookie 内容

#### Scenario: 学生调用教师接口被拒

- **GIVEN** 学生 20260002 已登录并改过密码
- **WHEN** 以其令牌请求 `GET /api/teacher/classes`
- **THEN** 返回 403，响应带 `X-Request-ID` 头；访问日志该行 `status` 为 403，`request_id` 与响应头一致；日志不含该令牌原文

#### Scenario: 请求不存在的接口

- **GIVEN** 后端已启动
- **WHEN** 请求 `GET /api/does-not-exist`
- **THEN** 返回 404，响应带 `X-Request-ID` 头，访问日志该行 `status` 为 404

#### Scenario: 业务日志带上请求标识

- **GIVEN** 某业务模块在处理请求时调用 `logging.getLogger(__name__).info(...)`
- **WHEN** 该请求带 `X-Request-ID: lesson07-trace-0002`
- **THEN** 该业务日志是一行 JSON，`module` 为该模块名，`request_id` 为 `lesson07-trace-0002`

### Requirement: 必填配置缺失即启动失败

`JWT_SECRET_KEY` MUST NOT 在代码中有默认值。该值缺失、为空或少于 32 个字符时，后端 MUST 在加载配置时失败并以非零状态退出，错误信息 MUST 只列出出错的配置键名，MUST NOT 包含配置值。Compose MUST 继续在根目录 `.env` 缺少 `JWT_SECRET_KEY` 时拒绝启动。

#### Scenario: 缺少 JWT 密钥

- **GIVEN** 环境变量与 `.env` 中都没有 `JWT_SECRET_KEY`
- **WHEN** 执行 `python -c "import config"`（工作目录 backend）
- **THEN** 进程以非零状态退出，标准错误含 `JWT_SECRET_KEY`

#### Scenario: JWT 密钥过短

- **GIVEN** `JWT_SECRET_KEY=short-secret-12345`（18 个字符）
- **WHEN** 加载后端配置
- **THEN** 进程以非零状态退出，标准错误含 `JWT_SECRET_KEY`，不含 `short-secret-12345`

#### Scenario: JWT 密钥合法

- **GIVEN** `JWT_SECRET_KEY` 为 `openssl rand -base64 32` 生成的 44 个字符
- **WHEN** 加载后端配置并启动
- **THEN** 正常启动，`GET /api/health` 返回 200

### Requirement: 一键门禁

仓库 MUST 提供一条命令 `make check`（等价于 `backend/.venv/bin/python scripts/check.py`）作为合并前门禁，依次执行：`openspec validate --all --strict --no-interactive`、分层检查 `scripts/check_layering.py`、密钥扫描 `scripts/secret_scan.py`、前端 `tsc --noEmit`、`apitest/` 下全部 `check_*.py` 与 `check_*.cjs` 离线回归脚本。任一子项非零退出 MUST 使整体以非零状态退出并打印未通过的子项名。回归子项 MUST 在子进程中以测试专用 `JWT_SECRET_KEY`、空 `DEEPSEEK_API_KEY` 与指向本机不可达端口的 `DEEPSEEK_BASE_URL` 运行，MUST NOT 读取真实模型 Key 或访问外网。分层检查 MUST 在出现自下而上的 import 或未登记层级的新后端模块时失败；密钥扫描 MUST 在本机 `.env` 的任一密钥值出现在任一提交或已跟踪文件中、或 `.env`/数据库/上传文件被 Git 跟踪时失败，且输出只含键名与文件名，不含值。

#### Scenario: 全部通过

- **GIVEN** 干净的工作区，依赖已安装（`backend/.venv`、`frontend/node_modules`）
- **WHEN** 在项目根执行 `make check`
- **THEN** 每个子项打印 PASS，最终以 0 退出，过程中无外网连接

#### Scenario: 业务层反向依赖接口层

- **GIVEN** 在某个 `*_service.py` 中加入 `from routers import quiz`
- **WHEN** 执行 `make check`
- **THEN** 分层检查子项失败并指出该文件与被引用模块，整体以非零状态退出

#### Scenario: 新模块未登记层级

- **GIVEN** 新增 `backend/foo_service2.py` 但未在分层表中登记
- **WHEN** 执行分层检查
- **THEN** 检查失败并提示该模块未登记层级

#### Scenario: 密钥进入已跟踪文件

- **GIVEN** 把本机 `.env` 中 `JWT_SECRET_KEY` 的值写进某个已跟踪文件
- **WHEN** 执行密钥扫描
- **THEN** 扫描失败，输出该键名与文件名，不输出密钥值

#### Scenario: 回归脚本不访问外网

- **GIVEN** 本机 `.env` 中填有真实 `DEEPSEEK_API_KEY`
- **WHEN** 执行 `make check`
- **THEN** 回归子项不向任何外部主机发起连接，结果与 `.env` 中不填 Key 时一致

### Requirement: 工程规范常驻且可被读取

仓库 MUST 在 `docs/standards/` 提供八份规范文件：`01-产品设计规范.md`、`02-后端开发规范.md`、`03-安全开发规范.md`、`04-测试规范.md`、`05-部署运维规范.md`、`06-AI应用规范.md`、`07-数据规范.md`、`08-评审与完成定义规范.md`，每份 MUST 含“违反时”一节。根目录 `AGENTS.md` MUST 含安全三条硬约束、完成定义与门禁、规范索引表与技能表；索引表引用的每个规范路径 MUST 存在。`CLAUDE.md` MUST 以 `@AGENTS.md` 引入同一内容，`.trae/rules/project_rules.md` MUST 指向 `AGENTS.md`。技能表列出的每个技能 MUST 存在 `.claude/skills/<名称>/SKILL.md`，其 front matter 的 `name` 等于目录名且 `description` 非空。

#### Scenario: 规范与规则齐全

- **GIVEN** 当前仓库
- **WHEN** 执行 `make check`
- **THEN** 基线检查确认八份规范存在且各含“违反时”，`AGENTS.md` 索引中的路径全部存在，`CLAUDE.md` 引入 `AGENTS.md`，七个技能的 front matter 合法

#### Scenario: 索引指向不存在的规范

- **GIVEN** `AGENTS.md` 规范索引中某一行引用的文件被删除或改名
- **WHEN** 执行 `make check`
- **THEN** 基线检查失败并指出缺失的路径

#### Scenario: 技能名与目录不一致

- **GIVEN** 某个 `SKILL.md` 的 `name` 与所在目录名不同，或缺少 `description`
- **WHEN** 执行 `make check`
- **THEN** 基线检查失败并指出该技能
