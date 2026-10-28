# 变更：2026-10-28-engineering-baseline

## Why

**给谁用**：组内开发成员（含后续接手的人）、负责验收的教师，以及部署这套服务的运维者。

**解决什么问题**：CampusClaw 已有 v1.1 业务功能，但工程基线不完整：

- `/api/health` 只报数据库，不报版本、时间和 MCP 工具服务状态，部署后无法一眼判断"跑的是哪一版、哪个依赖掉了"；
- 后端日志是 uvicorn 默认文本格式，没有请求标识，一次请求跨模块的日志串不起来；
- `JWT_SECRET_KEY` 在代码里有默认值 `campusclaw-dev-secret`，不经 Compose 直接启动时会带着公开的默认密钥运行；
- 没有一条命令的门禁：九个回归脚本要逐个手跑，分层与密钥泄露只靠人工记忆，回归脚本还会读到本机 `.env` 里的真实模型 Key 去连外网；
- 工程规范只有 `AGENTS.md` 里 5 条，另起一次会话生成的代码没有统一约束。

**比现有做法好在哪**：部署与验收都从一个端点开始；日志可按 `request_id` 串联；配置缺失直接启动失败而不是静默用默认值；`make check` 一条命令给出通过/不通过，换人换机器结论一致。

## What Changes

本次交付能力（编号清单，每条可单独演示）：

1. **C1 健康检查**：`GET /api/health`（Nginx 另提供 `/health` 别名）免认证，返回 `status`、`version`、`time` 与 `dependencies`（`database`、`mcp_tools`、`model` 三项状态）；数据库不可读返回 503，MCP 工具服务不可达返回 200 且 `status=degraded`；响应不含任何地址、配置键名或异常原文。
2. **C2 请求标识与结构化日志**：每个请求有一个 `request_id`（采纳合法的 `X-Request-ID` 请求头，否则服务端生成），回写到响应头；后端每个请求输出一行 JSON 访问日志，业务模块日志同为单行 JSON 并带当前 `request_id`；日志不记录查询串、令牌、Cookie 与密钥。
3. **C3 配置缺失即启动失败**：`JWT_SECRET_KEY` 取消代码默认值，缺失、为空或少于 32 个字符时进程启动失败，错误信息只给键名不给值。
4. **C4 一键门禁**：`make check`（无 make 时 `python scripts/check.py`）依次运行规约严格校验、分层检查、密钥扫描、前端类型检查和全部离线回归脚本，任一子项非零退出即不通过；回归在隔离环境运行，不读真实模型 Key、不访问外网。
5. **C5 工程规范落地**：八份规范文件（产品设计、后端开发、安全开发、测试、部署运维五类必修，AI 应用、数据、评审与完成定义三类补充）入库到 `docs/standards/`，常驻约束写进 `AGENTS.md` / `CLAUDE.md`，按场景执行的流程写成 `.claude/skills/` 下的技能。

## 本次不做

- 不把全部接口改成统一的 `{code, message, data, request_id}` 响应结构，也不加 `/api/v1` 版本前缀——现有前端与 21 份主规约都依赖当前形态，改动面超出一组任务；作为书面例外记入后端开发规范。
- 不把跨班访问从 403 改为 404——现行主规约 `class-data-isolation` 要求 403 并写审计；作为书面例外记入安全开发规范。
- 不改 `mcp-server/` 与前端的日志格式，不接入指标与告警。
- 不新增任何业务功能，不改数据库表结构，不调用真实模型。
- 不在本变更内做回滚演练与他人机器上的从零启动（交叉评审），二者记入 `docs/lesson-07/` 的待办。

## 被放弃的候选

- **健康检查实际调用一次模型**：能证明模型可用，但每 10 秒一次的容器探针会持续消耗每日 10 万 token 额度，且模型延迟会拖垮探针；改为只报告"是否已配置"。
- **用第三方 JSON 日志库（如 structlog）**：功能更全，但新增依赖；标准库 `logging` + 一个格式化器足以满足字段要求。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `runtime-reliability`：健康检查扩展为版本、时间与三项依赖状态；新增请求标识与结构化日志、配置缺失即启动失败、一键门禁三项要求。

## Impact

- 后端：新增 `version.py`、`logging_setup.py`；改 `main.py`（中间件、健康检查）、`config.py`（必填项校验）。
- 部署：`docker-compose.yml` 给后端传 `MCP_TOOLS_HEALTH_URL`；`deploy/nginx.conf` 增加 `/health` 别名。
- 工具：新增 `Makefile`、`scripts/check.py`、`scripts/check_layering.py`、`scripts/secret_scan.py`、`apitest/check_baseline.py`。
- 文档：`docs/standards/` 八份规范、`AGENTS.md` / `CLAUDE.md`、`.claude/skills/`、README 协作约定、`docs/lesson-07/` 验证记录。
- 既有约定：登录、权限、班级隔离、全部业务接口的请求与响应不变。
