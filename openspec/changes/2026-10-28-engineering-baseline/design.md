# 设计：2026-10-28-engineering-baseline

## 选型

- **日志**：Python 标准库 `logging`，自写 `JsonFormatter`，每条记录 `json.dumps(..., ensure_ascii=False)` 输出一行；请求标识用 `contextvars.ContextVar` 在同一请求内传递，业务模块照常 `logging.getLogger(__name__)` 即可带上。
- **请求标识中间件**：纯 ASGI 中间件（不用 `BaseHTTPMiddleware`），包住 `send` 取状态码并写 `X-Request-ID` 响应头，对 SSE 流式响应不缓冲。访问日志在响应开始（`http.response.start`）时写出，`duration_ms` 对流式接口表示首包耗时。
- **请求标识格式**：采纳请求头 `X-Request-ID`，仅当匹配 `^[A-Za-z0-9._-]{8,64}$`；否则生成 `uuid4().hex`（32 位十六进制）。
- **MCP 连通探测**：`httpx.get(MCP_TOOLS_HEALTH_URL, timeout=2.0)`，2xx 记 `ok`，其余与异常记 `unreachable`；未配置该地址记 `not_configured`。
- **配置校验**：pydantic-settings 字段 `jwt_secret_key: str = Field(min_length=32)`，无默认值；`get_settings()` 捕获 `ValidationError`，以 `SystemExit` 退出并只列出出错的键名（pydantic 原始报错会带 `input_value`，即密钥原文）。
- **门禁**：`scripts/check.py` 顺序执行各子项并汇总；`Makefile` 只是一层 `check:` 入口，方便 macOS/Linux，Windows 直接跑 Python 脚本。

## 分层

```
接口层   main.py · routers/* · deps.py · schemas.py · logging_setup.py
业务层   *_service.py · services.py · mcp_orchestrator.py · model_json.py · knowledge_tags.py · security.py
适配层   llm_service.py · embedding_service.py · mcp_client.py · mcp_crypto.py
数据层   models.py · database.py
配置     config.py · version.py
```

依赖只允许自上而下（接口 → 业务 → 适配/数据 → 配置）。`scripts/check_layering.py` 用 `ast` 读每个模块的 import，出现反向依赖或未登记的新模块即失败。已知例外两处（`services.py`、`agent_service.py` 从业务层抛 `fastapi.HTTPException`），登记在检查脚本与后端开发规范中，只许减少不许新增。

健康检查与中间件属于接口层；MCP 连通探测直接用 `httpx` 访问内部地址，不经 `mcp_client`（后者面向教师登记的服务器、带令牌与 JSON-RPC 握手，语义不同）。

## 健康检查响应

```json
{"status": "ok", "version": "1.2.0", "time": "2026-10-28T02:00:00Z",
 "dependencies": {"database": "ok", "mcp_tools": "ok", "model": "configured"}}
```

| 情况 | HTTP | status | 说明 |
| --- | --- | --- | --- |
| 数据库可读，MCP 正常或未配置 | 200 | ok | |
| 数据库可读，MCP 不可达 | 200 | degraded | 主应用可用，工具调用会失败 |
| 数据库不可读 | 503 | — | `detail` 保持"数据库暂不可用，请稍后重试"，与现行规约一致 |

`model` 只取 `configured` / `not_configured`，由 `DEEPSEEK_API_KEY` 是否非空决定，不发起模型调用。响应中不出现任何 URL、主机名、键名或异常文本。

## 日志字段

访问日志（logger 名 `access`）：

```json
{"ts":"2026-10-28T02:00:00.123Z","level":"info","module":"access","request_id":"4f…","method":"GET","path":"/api/health","status":200,"duration_ms":3.1}
```

业务日志：`ts`、`level`、`module`（logger 名）、`request_id`（请求外为 `null`）、`msg`，以及调用方通过 `extra=` 传入的字段。`path` 只记路径不记查询串；不记录请求头、请求体、令牌、Cookie。uvicorn 自身的启动日志改用同一格式化器，`uvicorn.access` 关闭（由本中间件取代）；`httpx`、`httpcore`、`openai` 日志级别提到 WARNING。

## 关键取舍

1. **只改健康检查与日志，不改统一响应结构**：统一结构能让错误码可登记、可遍历，但要同时改 9 个路由文件、前端 `lib/api.ts` 和多份主规约的场景，远超一组任务；代价是错误响应仍是 FastAPI 的 `{"detail": ...}`，`request_id` 只在响应头里。放弃的候选：本次一并迁移到 `{code, message, data, request_id}`。
2. **模型状态只报"已配置"**：放弃"探针实际调一次模型"，代价是模型 Key 失效时健康检查仍显示 `configured`，要靠业务接口的 503 发现。
3. **JWT 密钥最短 32 字符**：现有恢复脚本生成 44 字符的 base64 值，满足要求；代价是手写短密钥的旧 `.env` 会启动失败，需要按 `.env.example` 的命令重新生成（所有人重新登录）。
4. **门禁里的回归脚本强制隔离**：`scripts/check.py` 给子进程设置测试专用 `JWT_SECRET_KEY`，并把 `DEEPSEEK_API_KEY` 置空、`DEEPSEEK_BASE_URL` 指向不可达的本机端口，环境变量优先于 `.env`，从而保证不连外网、不耗额度。代价是需要真实模型的检查（如 `check_lessons_2_5.py` 中的实测分支）在门禁中只走跳过分支。

## 已知限制

- 流式接口的 `duration_ms` 是首包耗时，不是整段对话耗时。
- 中间件之外、uvicorn 接收连接阶段的错误不带 `request_id`。
- `mcp-server/` 仍输出文本日志；前端（Next.js）日志未纳入。
