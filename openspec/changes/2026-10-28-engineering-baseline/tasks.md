# 任务清单：2026-10-28-engineering-baseline

## 1. 骨架（先做完，再谈其他）

- [x] 1.1 新增 `backend/version.py`（`APP_VERSION = "1.2.0"`），`main.py` 的 FastAPI `version` 改为引用它
- [x] 1.2 `config.py`：`jwt_secret_key` 去掉默认值，`Field(min_length=32)`；`get_settings()` 捕获 `ValidationError`，以 `SystemExit` 退出且只列键名；新增可选 `mcp_tools_health_url: str = ""`
- [x] 1.3 新增 `backend/logging_setup.py`：`JsonFormatter`、`request_id` 的 `ContextVar`、纯 ASGI `RequestContextMiddleware`（标识采纳/生成、响应头、单行访问日志）、`configure_logging()`（根 logger 与 uvicorn 日志改 JSON，关闭 `uvicorn.access`，httpx/httpcore/openai 提到 WARNING）
- [x] 1.4 `main.py`：用 `configure_logging()` 取代 `_configure_app_logging()`；最后一个注册 `RequestContextMiddleware`，使其位于最外层
- [x] 1.5 `main.py`：`/api/health` 返回 `status/version/time/dependencies`；MCP 用 `httpx` 2 秒超时探测；503 文案不变
- [x] 1.6 `docker-compose.yml` 后端增加 `MCP_TOOLS_HEALTH_URL: http://mcp-tools:8090/health`；`deploy/nginx.conf` 增加 `location = /health` 转发到后端 `/api/health`；`.env.example` 注明 `JWT_SECRET_KEY` 至少 32 字符与生成命令

## 2. 门禁

- [x] 2.1 `scripts/check_layering.py`：按 design.md 分层表检查 `backend/` 每个模块的 import，反向依赖或未登记模块即失败；两处已知例外登记在脚本内
- [x] 2.2 `scripts/secret_scan.py`：读取本机 `.env` 中名含 KEY/SECRET/TOKEN/PASSWORD 且长度 ≥ 8 的值，在全部提交与已跟踪文件中检索；检查 `.env`、`*.db`、`uploads/` 未被跟踪；只输出键名与文件名
- [x] 2.3 `scripts/check.py` 与 `Makefile`（`make check`）：顺序执行 openspec 严格校验、分层、密钥扫描、前端 `tsc --noEmit`、全部 `apitest/check_*.py` 与 `check_*.cjs`；回归子进程注入测试专用 `JWT_SECRET_KEY`、空 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL=http://127.0.0.1:9/v1`
- [x] 2.4 `apitest/check_baseline.py`：覆盖 spec 中健康检查、请求标识与日志、配置缺失、一键门禁、规范常驻五项要求的全部场景（正常 / 失败 / 边界三类，R1–R5，59 条）

## 3. 规范落地

- [x] 3.1 `docs/standards/` 八份规范：01 产品设计、02 后端开发、03 安全开发、04 测试、05 部署运维、06 AI 应用、07 数据、08 评审与完成定义；每条带判据，例外写明理由与失效条件
- [x] 3.2 `AGENTS.md` 与 `CLAUDE.md`：常驻安全三条硬约束、完成定义与门禁、规范索引（改哪些路径读哪份规范）、技能清单；`.trae/rules/project_rules.md` 指向同一内容
- [x] 3.3 `.claude/skills/` 技能：按规范补测试、按规范加一个接口、按规范发一次版本、改一次提示词并跑评测、按规范做一次数据变更、按规范评审一次变更、从零启动一次
- [x] 3.4 README：协作约定（主干保护、变更命名、提交信息三字段、每人克隆跑通）、许可证选择、`make check` 与 `/health` 验证步骤、密钥泄露处置步骤与执行人

## 4. 验证与归档

- [x] 4.1 `make check` 全部通过，记录输出
- [ ] 4.2 Docker 重建后端与 Nginx：`/health` 与 `/api/health` 返回新结构；`docker compose logs backend` 为单行 JSON 且带 `request_id`
  - 2026-10-28：本机 Docker Desktop 未运行，容器部分未做；已用真实 uvicorn 进程验证 `/api/health`、`X-Request-ID` 与 JSON 日志，见 `docs/lesson-07/verification.md` §3
- [ ] 4.3 规范生效验证：另起一次不带历史的 Harness 会话，只给仓库路径与"按规范新增一个只读接口"的任务，检查分层、命名与测试是否符合规范；再做一次违规验证（业务层 import 路由），确认被门禁拦下
  - 2026-10-28：违规验证已做 3 次，均被拦下（verification.md §4）；另起会话的生效验证未做，列入 verification.md §6
- [x] 4.4 验证记录与能力—场景对照表写入 `docs/lesson-07/`
- [ ] 4.5 `openspec validate 2026-10-28-engineering-baseline --strict` 通过后归档本变更，打标签 `v1.2.0-baseline`
  - 待组长同意后执行（AGENTS.md 规约优先第 4 条）
