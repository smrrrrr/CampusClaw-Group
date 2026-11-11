## Why

第8课安全自查（`reports/security-precheck.md`）发现 2 条红项与 1 项待验：SEC-02 跨班访问返回 403 与课程口径 404 不一致；SEC-06 依赖存在高危未处置；SEC-07 技能调用持久日志缺 skill 标识、耗时与用量三列；SEC-05 运行产物/日志未完成密钥扫描。同时 SQL 注入、XSS、CSRF 三处为盲区，无反例用例。第9课要求把红项逐条修到绿，用同一条三段式复测，并把防护补进应用层与数据层。

## What Changes

- **SEC-02 授权口径统一**：跨班取资料由 fetch-then-check 改为一律返回 404（不区分"不存在"与"不是你的"，避免存在性泄露）；检索侧班级过滤在向量库与 SQL 两侧同时生效；删除"先查全表再内存过滤"的旧路径。
- **SEC-07 审计日志七列**：技能/工具调用日志补齐操作人、操作时间、操作类型、操作对象、结果状态、技能标识、用量与耗时；被拒绝的请求（401/403/404）同样落一条；日志内容经转义与截断；日志查询接口教师可查、学生不可见。
- **SEC-08 工具执行层鉴权**：模型决策调用写入工具不等于授权；宿主在执行工具前按发起者身份与资源归属逐次校验，不通过则拒绝并留审计日志。提示词中不放密钥或敏感配置。
- **注入防护三件套**：检索查询全部参数化（排序列名白名单枚举）；用户提交的讲义标题等文本进入 HTML 前转义；写接口校验一次性 CSRF 令牌，会话 Cookie 标记 SameSite。三条各写一条反例用例进 `apitest/cases/` 常驻回归。
- **SEC-05 密钥处置**：补扫运行日志与前端产物；命中先轮换再清提交历史；必须落库的凭证字段（如 MCP 令牌）确认密文存储、解密口令外置。
- **SEC-06 依赖处置**：升级高危依赖至修复版本；无补丁的写成可检查登记条目；密钥扫描与依赖审计接入 `make check-security`，有命中时退出码非 0。
- **回归与归档**：`make check` 全量 + 异步判据 + 注入三件套回归全绿；证据归档至 `reports/`（修复前后对照表、SEC-08 实验记录、基线报告、门禁先红后绿证据）。

## Capabilities

### New Capabilities

无。注入防护与日志要求并入既有能力规约，不新建近重复命名的能力。

### Modified Capabilities

- `class-data-isolation`：跨班资源访问返回 404（fetch-then-check），检索在向量库与 SQL 双侧加班级过滤。
- `rbac-role-permissions`：审计日志扩展为七列（含技能标识、耗时、用量）；状态变更接口要求 CSRF 一次性令牌，会话 Cookie 标记 SameSite。
- `mcp-tool-integration`：工具调用日志补 skill_id、duration_ms、token_usage；工具执行前按发起者身份与资源归属逐次鉴权，模型决策不豁免。
- `material-upload`：用户提交的文本型字段（标题、描述等）进入页面 HTML 前 MUST 转义，防止 XSS。
- `rag-search`：检索查询全部参数化，排序列名白名单枚举，禁止字符串拼接构造 SQL。

## Impact

- 后端 `routers/`、`*_service.py`、`models.py`：授权判定位置调整（应用层角色 + 数据层归属），日志表结构扩展。
- 前端 `app/`、`components/`：输出转义、CSRF 令牌携带、SameSite Cookie 配置。
- `apitest/cases/`：新增 SQL/XSS/CSRF 三条反例用例。
- `scripts/`、`Makefile`：`make check-security` 接入 gitleaks 与依赖审计。
- `reports/`：修复前后对照表、SEC-08 实验记录、密钥与依赖基线、门禁先红后绿证据。
- 数据库：审计日志表新增列（skill_id、duration_ms、tokens），需迁移脚本。
