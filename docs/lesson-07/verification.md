# 第 7 课验证记录（2026-10-28）

变更：`openspec/changes/2026-10-28-engineering-baseline/`。基线提交：`main` 的 `a86e19f`。改动前的差距分析见该变更目录下的 `lesson07-checklist.md`。
验证环境：macOS，`backend/.venv`（Python 3.12），`frontend/node_modules`，openspec 1.13.1。

## 1. 核查清单

| 维度 | 要求 | 结果 | 证据 |
| --- | --- | --- | --- |
| 仓库 | 地址可访问、教师有权限 | **待人工** | 组长在 GitHub 确认教师账号与主干保护规则 |
| 仓库 | 按 README 能从零跑起来 | **待交叉评审** | README 已补 `/health` 验证与门禁步骤；需另一名组员按技能 `fresh-start` 执行 |
| 仓库 | 全部提交历史中检索不到密钥 | 通过 | `scripts/secret_scan.py`：6 个提交，本机 4 个密钥值，0 处命中 |
| 规约 | 四份文件齐，`--strict` 通过 | 通过 | `openspec validate 2026-10-28-engineering-baseline --strict` → valid |
| 规约 | 每条能力至少一组 Scenario，失败路径 ≥ 4 类 | 通过 | 见 §2 对照表：5 项能力、27 个场景；参数非法、无权限、资源不存在、依赖不可达均有 |
| 规范 | 五类必修 + 三类补充写成文件，放在 Harness 读得到的位置 | 通过 | `docs/standards/01–08`；`AGENTS.md` 常驻索引；`CLAUDE.md` = `@AGENTS.md`；`.trae/rules/project_rules.md`；`.claude/skills/` 七个技能 |
| 规范 | 改一次代码验证生效；违规能被发现 | 部分通过 | 违规验证 3 次全部被门禁拦下（§4）；“另起会话按规范新增接口”尚未执行（§6） |
| 骨架 | 分层无反向依赖 | 通过 | `scripts/check_layering.py`：37 个模块 0 违规 |
| 骨架 | 配置外置，缺失即启动失败 | 通过 | 缺 `JWT_SECRET_KEY` 或少于 32 字符 → 退出码 1，只输出键名（§3） |
| 骨架 | `/health` 免认证并返回依赖连通状态 | 通过（本机进程）；容器待验 | §3 真实 uvicorn 输出；Docker Desktop 未运行，Nginx `/health` 别名未在容器中实测 |
| 骨架 | 日志一行一条 JSON 且带请求标识 | 通过 | §3 日志原文 |
| 交付 | 骨架标签存在 | **待执行** | 归档与打标签 `v1.2.0-baseline` 需明确指示（AGENTS.md 规约优先第 4 条） |
| 交付 | 验证记录归档到 `docs/lesson-07/` | 通过 | 本文件 |
| 交付 | 组内另一人在自己机器上从零启动成功 | **待交叉评审** | 技能 `fresh-start` |

## 2. 能力—场景对照表

| 能力 | Scenario | 检查（`apitest/check_baseline.py` 中的检查名前缀） |
| --- | --- | --- |
| C1 健康检查 | 数据库读取正常 | R1 正常：未带令牌 200 / version / time / 三项依赖 / 2 秒超时 / 不写业务记录 / 不含地址 |
| C1 | 经 Nginx 的 /health 别名 | R1 正常：Nginx 把 /health 转发到后端 /api/health（配置检查；容器实测待做） |
| C1 | 数据库存储异常 | R1 失败：数据库异常 → 503；503 响应不含 SQL、路径与异常原文 |
| C1 | MCP 工具服务不可达 | R1 失败：MCP 超时 / 返回 500 → degraded；不含地址 |
| C1 | 依赖未配置 | R1 边界：未配置 → not_configured；不发起出站探测 |
| C1 | 携带无效令牌访问健康检查 | R1 失败：伪造令牌仍 200，且不含用户信息 |
| C2 请求标识与日志 | 正常请求的标识与访问日志 | R2 正常：生成 32 位标识 / 恰好一行访问日志 / 字段齐全 / path 不含查询串 / 每行合法 JSON |
| C2 | 采纳调用方传入的合法标识 | R2 正常：采纳合法标识；访问日志使用调用方标识；R2 边界：64 个字符被采纳 |
| C2 | 非法请求标识被替换 | R2 边界：7 个字符含 + / 65 个字符被替换，原值不进日志 |
| C2 | 未登录访问业务接口 | R2 失败：未登录 → 401 且带请求标识；访问日志 status=401 |
| C2 | 学生调用教师接口被拒 | R2 失败：→ 403 且带请求标识；status=403；日志不含令牌 |
| C2 | 请求不存在的接口 | R2 失败：→ 404 且带请求标识；status=404 |
| C2 | 业务日志带上请求标识 | R2 正常：业务日志为 JSON 并带当前请求标识；R2 边界：请求之外为 null；R2 失败：未处理异常 → 500 带标识 |
| C3 必填配置 | 缺少 JWT 密钥 | R3 失败：缺少 JWT_SECRET_KEY → 非零退出并提示键名 |
| C3 | JWT 密钥过短 | R3 失败：18 个字符；错误信息不含配置值；R3 边界：31 个字符被拒绝 |
| C3 | JWT 密钥合法 | R3 边界：32 个字符可启动；R3 正常：44 个字符可启动；Compose 缺值拒绝启动 |
| C4 一键门禁 | 全部通过 | `make check` 16 项 PASS（§3） |
| C4 | 业务层反向依赖接口层 | R4 失败：业务层 import 路由被拦下；另见 §4 真实仓库违规验证 |
| C4 | 新模块未登记层级 | R4 失败：未登记层级的新模块被拦下 |
| C4 | 密钥进入已跟踪文件 | R4 失败：密钥进入提交被拦下；输出键名与文件名，不输出值 |
| C4 | 回归脚本不访问外网 | `make check` 在网络沙箱中运行，无外连拦截记录；改动前同一批脚本曾尝试连接课程网关被拦（§5） |
| C5 规范落地 | 规范与规则齐全 | R5 正常：八份规范、索引、引入、Trae 规则与七个技能齐全 |
| C5 | 索引指向不存在的规范 | R5 失败：索引指向的规范被删除 → 指出缺失路径 |
| C5 | 技能名与目录不一致 | R5 失败：技能名与目录不一致 → 指出该技能 |

`check_baseline.py` 共 59 条检查，全部通过。

## 3. 运行证据

`make check`（2026-10-28）：

```
[PASS] openspec-validate  [PASS] layering  [PASS] secret-scan  [PASS] fe-typecheck
[PASS] check_apitest_harness  [PASS] check_baseline  [PASS] check_formula_retrieval
[PASS] check_lesson_prep  [PASS] check_lessons_2_5  [PASS] check_mcp_tools
[PASS] check_model_json  [PASS] check_question_bank  [PASS] check_research_materials
[PASS] check_sqlite_storage  [PASS] check_markdown_images  [PASS] check_recent_history
门禁全部通过
```

真实 uvicorn 进程（临时库，`MCP_TOOLS_HEALTH_URL` 指向不可达端口，未填模型 Key）：

```
$ curl -s -D - "http://127.0.0.1:8099/api/health?probe=1" -H "X-Request-ID: lesson07-live-0001"
HTTP/1.1 200 OK
x-request-id: lesson07-live-0001
{"status":"degraded","version":"1.2.0","time":"2026-10-28T02:25:18Z","dependencies":{"database":"ok","mcp_tools":"unreachable","model":"not_configured"}}

$ curl -s -i http://127.0.0.1:8099/api/teacher/classes -H "Authorization: Bearer forged"
HTTP/1.1 401 Unauthorized
x-request-id: 9b1fb783c8ed48d2960e9c44105c6159
```

同一进程的日志（每行一条 JSON，不含查询串与令牌）：

```
{"ts": "2026-10-28T02:25:17.834Z", "level": "info", "module": "uvicorn.error", "request_id": null, "msg": "Started server process [98062]"}
{"ts": "2026-10-28T02:25:18.422Z", "level": "info", "module": "access", "request_id": "lesson07-live-0001", "method": "GET", "path": "/api/health", "status": 200, "duration_ms": 9.7}
{"ts": "2026-10-28T02:25:18.429Z", "level": "info", "module": "access", "request_id": "9b1fb783c8ed48d2960e9c44105c6159", "method": "GET", "path": "/api/teacher/classes", "status": 401, "duration_ms": 1.0}
```

缺少 `JWT_SECRET_KEY` 时启动 uvicorn：输出 `配置缺失或不合法：JWT_SECRET_KEY（见 .env.example）`，退出码 1。

## 4. 违规验证（改坏后门禁必须变红）

在真实仓库临时改动、跑 `scripts/check.py`、再恢复原文件：

| 故意违规 | 门禁结果 | 结论 |
| --- | --- | --- |
| `citation_service.py` 末尾加 `from routers import quiz` | `layering` FAIL（并因循环导入使 8 个回归脚本失败） | 分层规则被执行 |
| 中间件不再回写 `X-Request-ID` 响应头 | `check_baseline` FAIL | 请求标识检查断言到了行为 |
| 删掉 `deps.get_current_teacher` 的角色检查 | 只有 `check_mcp_tools` FAIL | 能拦下，但**功能级越权的覆盖偏薄**：多数教师接口还有班级 / 学科判定兜底，其余脚本没有直接断言“学生调教师接口 → 403”。列为待办 |

恢复后 `make check` 全部通过，`git diff` 中这三个文件无残留改动。

## 5. 实现中的调整（已同步回规约）

- **断言修改**：`apitest/check_lesson_prep.py` 原断言要求 `lesson_service` logger 自己挂处理器（旧实现细节）。日志改由根 logger 统一输出 JSON 后，该断言失败。断言本意是“修补次数确实写进服务端日志”，改为判断“该 logger 或其上级有处理器会写出”，其余条件不变。
- **测试隔离问题**：改动前直接运行回归脚本时，脚本以项目根为工作目录，读到根 `.env` 的真实模型 Key，并尝试连接课程网关（被网络沙箱拦下，未消耗额度）。现由 `scripts/check.py` 用环境变量覆盖隔离。直接单独运行脚本时仍会读 `.env`，请通过 `make check` 运行。
- **规约补充**：C5 原本没有 Scenario，补了“工程规范常驻且可被读取”一条需求与 3 个场景，并在 `check_baseline.py` 中实现为 R5 检查。
- **示例配置**：`backend/.env.example` 原有占位值 `change-me-to-a-long-random-secret`（33 字符）会通过新校验，改为留空。
- **依赖**：`backend` dev 依赖加入 `pytest`、`requests`（`check_apitest_harness.py` 需要），`uv.lock` 只有新增，无既有版本变化。
- **日志细节**：去掉 uvicorn 附带的 `color_message` 字段（含 ANSI 颜色码）。

## 6. 待办（未在本次完成）

| 事项 | 谁 | 怎么做 |
| --- | --- | --- |
| 容器验证：`docker compose up -d --build` 后 `curl http://localhost:<端口>/health`，`docker compose logs backend` 为 JSON | 任一组员 | 本机 Docker Desktop 当时未运行 |
| 另起一次不带历史的 Harness 会话，只给仓库路径与任务“按 docs/standards 新增只读接口 `GET /api/student/materials/count`（返回本班已发布资料数），并按 add-tests 补检查”，核对分层、命名、403/401 检查是否符合规范；再换一次会话做同样任务，比较两次结果 | 任一组员 | 结果补进本文件 |
| 交叉评审：另一名组员按技能 `fresh-start` 从零启动 | 非本次实现者 | 结果补进本文件 |
| 主干保护规则、教师访问权限 | 组长 | GitHub 仓库设置 |
| 归档变更并打标签 `v1.2.0-baseline` | 经组长同意后执行 | `openspec archive 2026-10-28-engineering-baseline`；技能 `release` |
| 回滚演练（当前标签与上一标签各起一次，记录耗时） | 发版人 | 技能 `release` 回滚段落 |
| AI 评测集 `apitest/eval/cases.jsonl`（10 条必须答对 + 10 条必须拒答） | 负责助手的组员 | 06-AI应用规范 §7 |
| 补“学生调用每个教师接口 → 403”的成组检查 | 任一组员 | 见 §4 第三行 |
