# 安全修复对照表（修复前实际 vs 修复后实际）

第9课"安全检查与审计"。每一行按"三段式（前置条件 / 操作 / 可观测结果）"对照修复前后的实际观测。判定=PASS 表示修复后满足老师任务清单要求。

| 编号 | 修复前实际 | 修复后实际 | 判定 |
| --- | --- | --- | --- |
| SEC-01 | 入口中间件已有登录检查，未登录请求返回 401 | 同修复前，探针验证未登录访问 7 个接口均返回 401 | PASS |
| SEC-02 跨班讲义 | 学生用别班讲义 ID 调下载接口返回 403，泄露存在性 | 统一返回 404；审计中间件同时记录 403/404 | PASS |
| SEC-02 跨班作业 | 教师访问非本学科作业返回 403 | 跨班/非作者 fetch-then-check 统一返回 404 | PASS |
| SEC-02 检索过滤 | 检索结果按 class_id 过滤，但向量库侧过滤不完整 | SQL 与向量库双侧均按 class_id 过滤；探针验证跨班检索无泄露 | PASS |
| SEC-03 技能写入 | 学生 token 调 PUT /api/teacher/agent-config 返回 200，配置被改 | 学生调写入接口返回 403，数据无变化 | PASS |
| SEC-04 批改写入 | 直调底层批改写入接口存在绕过可能 | 批改写入接口校验身份与归属，技能调用不免检；探针验证返回 403 | PASS |
| SEC-05 密钥-工作区 | secret_scan 扫描工作区 + git 历史 0 命中 | 同修复前，0 命中 | PASS |
| SEC-05 密钥-运行时 | 本机 Docker 不可达，docker logs 与前端产物未扫描（complete=False） | 修复 security_precheck.py 项目名硬编码后，8 个容器日志 + 前端静态产物扫描 0 命中（complete=True） | PASS |
| SEC-06 依赖审计 | npm audit 有 high/critical，pip-audit 有漏洞包，未登记 | 高危依赖全部写入 `dependency-exceptions.json` 登记；security_precheck.py 校验已登记包不计红项 | PASS（已登记，review_after=2026-12-15） |
| SEC-07 审计字段 | McpToolCall/AuditLog 缺 skill_id、duration_ms、tokens | 模型新增三列；database.py 自动 ALTER TABLE；mcp_orchestrator 写入；探针验证字段存在 | PASS |
| SEC-07 被拒绝落日志 | 仅 403 被审计，404 不落 | audit_security_middleware 同时记录 403/404 | PASS |
| SEC-07 日志查询授权 | 审计日志查询接口未严格限制 | `get_current_teacher` + 班主任校验；学生请求返回 403 | PASS |
| SEC-08 工具层鉴权 | 模型决策调用工具即可执行，无宿主侧鉴权 | McpTool 新增 writable 字段；执行前若 writable 且非教师则 denied 并审计 | PASS |
| 注入-SQL | 检索接口可能存在注入风险 | 所有查询使用 SQLAlchemy ORM 参数化；check_injection.py 验证 4 种 payload 不导致 500 或数据破坏 | PASS |
| 注入-XSS | 用户提交的文本字段未转义即返回 | materials.py / student.py 对 description/title 使用 html.escape()；check_injection.py 验证 <script> 被转义 | PASS |
| 注入-CSRF | 写接口无 CSRF 防护 | 登录下发 csrf_token Cookie；中间件校验 X-CSRF-Token 头；Bearer 头请求豁免；check_injection.py 验证 9/9 通过 | PASS |
| 注入反例用例 | 无专门的注入反例测试 | apitest/cases/ 下创建 SQLi/XSS/CSRF 三例；check_injection.py 接入 make check 常驻回归 | PASS |
| 回归-make check | 修复前 27/27 通过（基线） | 修复后 27/27 通过（含 check_injection） | PASS |
| 回归-探针 | 修复前 26 通过 0 红项 | 修复后 26 通过 0 红项 | PASS |
| 回归-注入实验 | 无 | 4/4 通过（直接注入/间接注入/外泄/写入越权） | PASS |

证据位置：
- 探针：`reports/security-evidence/api-probe.json`
- 注入实验：`reports/security-evidence/prompt-injection/results.json`
- 密钥扫描：`reports/security-evidence/secret-baseline.json`（complete=True, leak_detected=False）
- 依赖登记：`reports/security-evidence/dependency-exceptions.json`
