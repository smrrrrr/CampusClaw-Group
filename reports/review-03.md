# 第三次安全评审记录（第9课修复后的独立交叉评审）

- 评审对象：`fix/security-lesson09-DuLaolaoDu`，提交 `70f0048b2a24d50512bd27b183c4e92a28704f9e`
- 数据包：`CampusClaw-Review-Data-20261105`（2026-11-12 重打包版，`code_commit=70f0048`）
- 环境：macOS 15.x（Darwin 24.6.0）；Python 3.12.15；uv 0.13.5；Node.js v25.9.0；npm 11.12.1；Docker 29.8.0 / Compose v5.5.1
- 方式：全新 clone → 恢复数据包 → 安装依赖 → `docker compose up -d --build` → 按交接说明第七节完整验证
- 时间：2026-11-12（北京时间）
- 性质：AI 代理独立交叉评审，**不是组员本人签名**

**结论：`needs-attention`，不应合并。** 机器门禁全绿，但 SEC-08 有两条独立失效路径，npm 安全门禁存在漏报，历史消息转义破坏数学内容。

---

## 一、环境与数据恢复

| 步骤 | 结果 |
| --- | --- |
| 全新 clone `fix/security-lesson09-DuLaolaoDu` | 成功 |
| `git checkout 70f0048` | 成功（detached HEAD，符合交接说明） |
| `restore.py --verify-only` | **PASS** |
| `restore.py --project ... --port 8084` | **PASS**（项目名 `campusclaw-review-8c3d1f`） |
| `uv sync --project backend --locked` | 成功（Python 3.12.15） |
| `npm --prefix frontend ci` | 成功 |
| `docker compose config --quiet` | 通过 |
| `docker compose up -d --build` | 成功 |
| 七服务状态 | nginx / backend / frontend / mcp-tools / rabbitmq / grading-dispatcher / grading-worker 全部 Up，关键服务 healthy |
| `GET /health` | **200**，`database=ok`、`mcp_tools=ok`、`model=not_configured` |
| `GET /login` | **200** |

### 1.1 数据包与修复提交的兼容性（已修复）

原数据包 `manifest.json` 绑定的是修复前基线 `55d18d3`：

- 98 个代码指纹中，16 个与 `70f0048` 不匹配（`models.py`、`main.py`、`database.py`、`mcp_orchestrator.py`、多个 `routers/*.py` 等安全修复核心文件）；
- `restore.py` 同时校验文件指纹与 `git rev-parse HEAD`，因此在 `70f0048` 上直接恢复会失败：

```text
恢复未完成：配套代码不匹配，请检出交接说明指定的提交：backend/database.py
退出码=2
```

2026-11-12 已按"重打包"方案修复：`code_commit` 与 `branch` 指向 `70f0048` / `fix/security-lesson09-DuLaolaoDu`，16 个指纹更新，交接说明同步；`data/campusclaw.db`、`uploads/` 与脱敏内容未改动。复验结果：

```text
restore.py --verify-only                          → PASS
全新 clone + checkout 70f0048 + restore           → PASS
同一数据包在 55d18d3 上恢复                        → 拒绝（符合预期）
启动应用后 audit_logs / mcp_tool_calls 自动补列     → 成功
```

**P0-1 已关闭。** 本次评审直接用重打包后的数据包在 `70f0048` 上恢复，不再需要两步变通。

---

## 二、机器门禁

| 门禁 | 命令 | 结果 | 证据 |
| --- | --- | --- | --- |
| 全量回归 | `backend/.venv/bin/python scripts/check.py` | **28/28 PASS**，退出码 0 | `reports/security-evidence/review03-check.txt` |
| 安全探针 | `apitest/probe_security_precheck.py` | **26 通过，0 红项**，退出码 0 | `reports/security-evidence/review03-peer-api.json` |
| 注入三件套 | `apitest/check_injection.py` | **9/9 通过**，退出码 0 | `reports/security-evidence/review03-check-injection.txt` |
| 密钥与依赖 | `scripts/security_precheck.py`（完整模式） | **PASS**，退出码 0 | `reports/security-evidence/review03-run.json` |

`security_precheck.py` 明细：

```text
status=PASS, exit=0, has_blocked_scope=False
secret_leak_detected=False, secret_scope_complete=True
probe_exit=0, unregistered_vulns=[], expired_exceptions=[]
source_unchanged=True
npm: critical=1, high=2, moderate=1
backend: 5 vulnerable packages（certifi/ecdsa/pillow/pyasn1/python-jose）
```

注意：`npm` 有 1 个 critical 和 2 个 high，脚本仍判 PASS；这不是已登记豁免生效，而是 npm 校验分支有缺陷（见 P1-3）。

探针的 26 条用例覆盖 `PRE` 登录 ×4、`SEC-01` ×7、`SEC-02` ×7、`SEC-03` ×4、`SEC-04` ×2、`SEC-07` ×2，**没有 SEC-08**。

---

## 三、7.4 四步演示走查

| 步骤 | 操作 | 实际结果 |
| --- | --- | --- |
| ① 登录取令牌 | `POST /api/auth/login`（TEA001） | **200**，取得 Bearer token |
| ② 提交任务返回 202 | `POST /api/teacher/homeworks/7/ai-grade` | **202**，`{"task_ids":[1],"created_count":1}` |
| ③ 轮询状态 | `GET /api/teacher/grade-tasks/1` | `retrying → dead`；`attempts=3`、`execution_count=3`；错误“模型调用失败或评分格式无效，请检查模型配置后重试” |
| ④ 换班取讲义 | 20260001（101班）请求 102 班材料 id=1、id=8 | **404**（本班 id=4 为 200） |

步骤③的 `dead` 是未配置模型 Key 的预期结果，未伪造成功评分；`homework_submissions` 的 `teacher_score` 保持为空。步骤④未泄露 102 班正文。

---

## 四、安全专项手动复现（四件事）

### SEC-02 跨班访问统一 404

- **用什么手段查**：20260001 登录后请求 `GET /api/materials/{id}/download`，分别访问本班 id=4、102 班 id=1 和 id=8；另做无 token 请求。
- **查了什么**：HTTP 状态码、响应体是否含 102 班正文、`audit_logs` 是否记录。
- **判据**：本班 200；跨班 404 且无正文；未认证 401；审计有 404 记录。
- **结果**：本班 200；跨班 404 `材料不存在`；未认证 401；`audit_logs` 有两条 404。**PASS**

补充：TEA002（物理教师）改 101 班数学提交 → 404；查询 101 班作业 → 404，符合跨学科/跨班 404 口径。

### SEC-03 / SEC-04 写入接口角色与归属校验

- **用什么手段查**：20260001（学生）token 请求四个写接口：`PUT /api/teacher/agent-config?class_id=101`、`POST /api/teacher/skills?class_id=101`、`PUT /api/teacher/submissions/1/grade`、`POST /api/teacher/homeworks/1/ai-grade`。
- **查了什么**：HTTP 状态码；请求前后 `agent_configs`、`assistant_skills`、`homework_submissions` 三张表的完整行快照。
- **判据**：四个请求均 403，且三张表数据逐行不变。
- **结果**：四个请求均 **403** `仅教师可执行该操作`；三张表前后快照完全一致。**PASS**

### CSRF 三条路径

- **用什么手段查**：登录后读取 `csrf_token` Cookie；分别发送无 `X-CSRF-Token`、带正确 Token、带 Bearer 的写请求。
- **查了什么**：状态码、响应体、Cookie 属性。
- **判据**：无 Token → 403；带 Token → 不被 CSRF 拒绝；Bearer → 豁免。
- **结果**：`csrf_token` 非 HttpOnly；无 Token → **403 `CSRF 令牌校验失败`**；带 Token → **401**（通过 CSRF，但无 Bearer 身份）；Bearer → **200**。**PASS**

### 审计查询授权

- **用什么手段查**：学生、TEA001（班主任 101）、TEA002（查 101 班）分别请求 `/api/teacher/audit-logs`。
- **判据**：学生 403；本班班主任 200；非本班班主任 403。
- **结果**：403 / 200 / 403。**PASS**

### SEC-07 审计字段与 401 落库

- **用什么手段查**：读取 `/api/teacher/audit-logs` 响应字段；直接只读查询 `audit_logs` 状态分布；制造一次未认证请求后再查。
- **判据**：七列可查；401/403/404 都落一条。
- **结果**：响应只有 `id/user_id/role/request_path/method/status_code/ip_address/created_at` 八个字段，**没有** `action/object_id/skill_id/duration_ms/tokens`；5 行审计中这五列非空数均为 **0**；状态分布为 403 ×3、404 ×2，**401 ×0**。**FAIL（P1-1、P1-2）**

### SEC-08 工具执行鉴权

官方实验脚本缺失（P0-2），改用仓库外只读脚本驱动真实 `run_tool_loop`，四组对照：

| 组 | 条件 | 工具执行 | 审计 | 异常 |
| --- | --- | --- | --- | --- |
| A | `read_hint`（只读），不注入 ctx | 1 次 | `ok` | 无 |
| B | `write_score`（可写），**生产路径** | 0 次 | **0 条** | **`NameError: name 'ctx' is not defined`** |
| C | 诊断：注入 `ctx.role=student` | 0 次 | `denied` | 无 |
| D | 诊断：注入 `ctx.role=teacher` | 1 次 | `ok` | 无 |

生产路径不是“拒绝并审计”，而是崩溃；`backend/routers/student.py` 只捕获 `LLMGenerationError`，该异常会中断 SSE 流。**FAIL（P0-4）**

### 注入三件套

- **用什么手段查**：`backend/.venv/bin/python apitest/check_injection.py`。
- **查了什么**：SQL 注入 payload 是否 500/破坏数据、XSS 标签是否转义、CSRF 三种路径。
- **判据**：无 500、数据完整、`<script>`/`<img>` 被转义、无令牌写请求 403、正确令牌通过、Bearer 豁免。
- **结果**：**9/9 通过**。**PASS**

---

## 五、问题汇总

| 编号 | 严重度 | 问题 | 证据 |
| --- | --- | --- | --- |
| P0-1 | 高 | 数据包原绑定 `55d18d3`，与 `70f0048` 不兼容 | 16/98 指纹不匹配；直接恢复报错。**已于 2026-11-12 重打包修复** |
| P0-2 | 高 | SEC-08 实验脚本与结果文件未提交 | `reports/security-evidence/prompt-injection/` 不存在；Git 历史无记录 |
| P0-3 | 高 | 探针没有 SEC-08 用例 | 26 条用例仅 SEC-01/02/03/04/07 |
| P0-4 | 高 | `run_tool_loop` 引用未定义 `ctx`，生产路径 `NameError` | 只读脚本 B 组；`mcp_orchestrator.py:348` |
| P0-5 | 高 | 工具发现不保存 `writable`，正常路径全部按只读执行 | `mcp_client.py:194`、`routers/mcp.py:362-370`、模型默认 `False`；重连清空缓存 |
| P1-1 | 中 | 401 未写入审计 | 实测 401 行数 0；`main.py:108` 只判断 403/404 |
| P1-2 | 中 | `AuditLog` 新增五列未赋值、查询接口不返回 | 5 行审计五列非空数均为 0；`AuditLogItem` 只有 8 字段 |
| P1-3 | 高 | npm 例外校验分支永不执行，未登记 npm 漏洞被放行 | `security_precheck.py:182-187`；critical/high 仍 PASS |
| P1-4 | 中 | 历史消息整体 `html.escape` 破坏公式与代码块 | `student.py:425-429`；KaTeX 实测 `katex-error` |
| P2-1 | 低 | 文档残留：材料下载 docstring 仍写 403；分支指针 `a15d4f0` 与 `70f0048` 不一致 | 代码与交接说明 |

补充证据：

```text
mcp_client.py:194  DiscoveredTool(name=..., description=..., input_schema=schema)  # 无 writable
connect_server      McpTool(server_id=..., name=..., description=..., input_schema=...)  # 无 writable
dependency-summary  npm = {"info":0,"low":0,"moderate":1,"high":2,"critical":1,"total":4}
                    "vulnerabilities" in npm == False
清空例外后         unregistered = ['backend:certifi','backend:ecdsa','backend:pillow','backend:pyasn1','backend:python-jose']
                    npm 的 critical/high 不在结果中
KaTeX 渲染          raw_has_katex=true；escaped_has_katex_error=true
```

---

## 六、结论与修复优先级

**代码质量：门禁全绿（28/28、26/26、9/9），SEC-02/03/04 一致；但 SEC-08 有两条独立失败路径，npm 门禁被代码缺陷跳过，历史消息转义破坏 Markdown。**

**不可合并原因：**

1. SEC-08 生产路径引用未定义的 `ctx`，调用即 `NameError`（P0-4）；实验脚本/结果缺失（P0-2），探针未覆盖（P0-3）；
2. 工具发现不保存 `writable`，正常发现路径上所有工具都按只读执行（P0-5），SEC-08 授权被整体绕过；
3. npm 例外校验分支永远跳过（P1-3），`make check-security` 会放行未登记的 npm 漏洞；
4. 历史消息整体 `html.escape()` 破坏 Markdown 公式与代码块（P1-4）；
5. SEC-07 的 401 审计与七列查询未达标（P1-1、P1-2）。

| 优先级 | 动作 |
| --- | --- |
| P0 | 建立可信的工具权限分类并在发现/落库时保存；未知权限默认拒绝学生；重连不得丢失授权 |
| P0 | 给 `run_tool_loop` 传入 `role`/`ctx`，由 `student.py` 提供 `current.role`；补端到端拒绝测试 |
| P0 | 提交 `prompt-injection/run_experiments.py` 与 `results.json`，或删除该实验并改用可执行用例 |
| P0 | 在探针中加入 `writable=True` 的学生/教师对照用例，并断言 SSE 不中断 |
| P1 | 修复 npm 例外校验：保留原始 `vulnerabilities` 明细，按包名+版本+advisory 匹配 |
| P1 | 审计中间件覆盖 401；`AuditLogItem` 暴露新增五列并在技能路径写入 |
| P1 | 历史消息返回原始 Markdown，在渲染边界做安全处理；补公式/代码块一致性用例 |
| P2 | 清理 403 残留 docstring；统一分支与提交引用 |

---

## 七、证据清单

| 文件 | 内容 |
| --- | --- |
| `reports/security-evidence/review03-check.txt` | 28/28 全量门禁输出 |
| `reports/security-evidence/review03-check-injection.txt` | 注入三件套 9/9 明细 |
| `reports/security-evidence/review03-peer-api.json` | 26 条安全探针原始结果 |
| `reports/security-evidence/review03-security-precheck.txt` | 完整密钥/依赖自查输出 |
| `reports/security-evidence/review03-sec08.json` | SEC-08 四组只读对照 |
| `reports/security-evidence/review03-run.json` | 安全自查汇总（PASS） |
| `reports/security-evidence/review03-dependency-summary.json` | npm/pip 漏洞计数明细 |
| `reports/security-evidence/review03-secret-baseline.json` | 容器日志/前端产物扫描（0 泄漏） |

---

## 八、评审人

| 执行人 | 环境 | 日期 | 覆盖范围 |
| --- | --- | --- | --- |
| phj | 隔离 clone + Docker 七服务 + 恢复数据包 | 2026-11-12 | 环境恢复、28 项门禁、26 条探针、7.4 四步、CSRF、审计授权、SEC-08、全部问题复现 |

> 本记录不能替代组员本人签名。按交接说明第八节，仍需一名组员在本机独立复现至少 2 条并签名；签名前不得宣称课程安全任务全部完成。
