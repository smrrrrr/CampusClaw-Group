# CampusClaw 第9课安全修复 — 队友交接说明

数据包日期：2026-11-05。用途：第9课"安全检查与审计"红项修复的组内复现与PR评审。
修复分支：`fix/security-lesson09-DuLaolaoDu`，基于提交 `55d18d36d6aec194e549271658e7f7d15d683a0f`。
配套数据包：`CampusClaw-Review-Data-20261105`（已放项目根目录）。

本机已完成第9课安全修复全部代码与归档材料，四项核心门禁全绿。本说明覆盖从克隆代码到最终测试的全流程。**组员只需按第八节做交叉评审。**

## 一、老师本次课的要求

第9课要求把第8课安全自查发现的红项逐条修到绿，并用同一套三段式（前置条件 / 操作 / 可观测结果）复测，同时把防护补进应用层与数据层。**修复完成的标志是复测变绿，不是"看起来好了"。** 具体如下：

| SEC 项 | 老师要求 |
| --- | --- |
| **SEC-01 登录检查** | 入口中间件统一做登录检查，未通过返回 401 |
| **SEC-02 跨班隔离** | 跨班按 ID 取资源（fetch-then-check）一律返回 404，避免存在性泄露；参数篡改与角色越权仍返回 403；检索侧班级过滤在向量库与 SQL 两侧同时生效；删除"先查全表再内存过滤"旧路径 |
| **SEC-03 写入接口角色校验** | 技能与提示词等写入类接口逐次校验角色，非教师返回 403 且数据无变化 |
| **SEC-04 底层批改写入校验** | 底层批改写入接口同样校验身份与归属，技能调用不免检 |
| **SEC-05 密钥处置** | 补扫运行日志与前端产物；命中先轮换再清提交历史；凭证字段确认密文存储，解密口令外置 |
| **SEC-06 依赖处置** | 升级高危依赖至修复版本，或写成可检查登记条目；密钥扫描与依赖审计接入 `make check-security`，有命中退出码非 0 |
| **SEC-07 审计日志七列** | 操作人、操作时间、操作类型、操作对象、结果状态、技能标识、用量与耗时；被拒绝请求(401/403/404)同样落一条；日志查询接口教师可查、学生不可见 |
| **SEC-08 工具执行鉴权** | 模型决策调用写入工具不等于授权；宿主执行前按身份与归属逐次校验，不通过拒绝并留审计；四步实验当堂做完 |
| **注入三件套** | SQL 查询参数化 + 排序列名白名单；XSS 文本字段 `html.escape()`；CSRF 一次性令牌 + SameSite Cookie；三条反例写进 `apitest/cases/` 常驻回归 |
| **回归与归档** | `make check` 全量 + 异步判据三条 + 注入反例三件套全绿；证据归档 `reports/`；交叉评审至少 2 条 |

## 二、完成情况与是否达到要求

### 已完成（红项已转绿）

| SEC 项 | 修复前 | 修复后 | 验证证据 |
| --- | --- | --- | --- |
| SEC-01 登录检查 | — | 入口中间件统一 401 | 探针 SEC-01 通过 |
| SEC-02 跨班隔离 | 跨班 fetch-then-check 返回 403 | 统一返回 404；审计中间件记录 403/404；检索双侧过滤 | 探针 26/26 通过；`api-probe.json` |
| SEC-03 写入接口校验 | — | 学生令牌重放配置写接口 → 403 且数据不变 | 探针 SEC-03 通过 |
| SEC-04 批改写入校验 | — | 直调批改写入接口被拒，库无残留 | 探针 SEC-04 通过 |
| SEC-07 审计字段 | 缺 skill_id、duration_ms、tokens | 新增三列 + 写入逻辑 + 迁移脚本；查询接口仅班主任可查本班 | 探针 SEC-07 通过 |
| 注入三件套（防御） | 无服务端转义、无 CSRF | SQL 参数化；文本字段 `html.escape()`；CSRF 双提交 Cookie | `check.py` 全绿 |
| SEC-08 工具授权 | 无写入类工具区分 | `McpTool.writable` 字段；学生执行写入工具 denied 并审计 | 注入实验 4/4 通过 |

### 归档材料（已全部补齐）

以下归档材料已按老师任务清单要求完成：

| 材料 | 路径 | 说明 |
| --- | --- | --- |
| 注入三条反例用例 | `apitest/cases/api/student/conversations/chat/POST-sqli.py`、`apitest/cases/api/materials/xss.py`、`apitest/cases/csrf.py` | 三段式反例，随 `check_injection.py` 接入 `make check` 回归 |
| SEC-05 密钥扫描 | `reports/security-evidence/secret-baseline.json` | `complete=True`、`leak_detected=False`，8 容器日志 + 前端产物 0 命中 |
| SEC-06 依赖登记 | `reports/security-evidence/dependency-exceptions.json` | 9 条漏洞包登记，含理由与降险措施；`security_precheck.py` 校验已登记包不计红项 |
| 修复前后对照表 | `reports/security-fix-log.md` | 编号/修复前/修复后/判定，20 行对照 |
| SEC-08 四步实验 | `reports/sec08-experiment.md` | 恶意文档/索要提示词/改规则/绕权限，4/4 通过 |
| 先红后绿证据 | `reports/gate-red-green.md` | 假密钥触发 RED（退出码1），移除后 GREEN（退出码0） |
| 返工记录 | `reports/rework-lesson09-csrf.md` | CSRF 中间件与未认证请求交互的返工 |
| 四步演示走查 | 见本说明第七节 7.4 | 登录200→提交202→轮询→跨班404 |

四项核心门禁结果（本机实测，2026-11-11）：

```
scripts/check.py                          → 28/28 PASS（含 check_injection，门禁全部通过）
apitest/probe_security_precheck.py        → 26 通过，0 红项
reports/.../prompt-injection/run_experiments.py → 4/4 通过
scripts/security_precheck.py              → PASS（密钥0泄漏、范围完整、依赖全部登记）
```

> **组员只需做交叉评审**：按第八节要求，独立复现至少 2 条修复并填写 `reports/review-02.md`。

## 三、先准备这三样

| 项目 | 要求 |
| --- | --- |
| 代码 | 分支 `fix/security-lesson09-DuLaolaoDu`，检出提交 `55d18d3` |
| 数据 | 项目根目录下 `CampusClaw-Review-Data-20261105(1)\CampusClaw-Review-Data-20261105\`（含 restore.py、manifest.json 等） |
| 软件 | Git、Python 3.12+、Docker Desktop（Linux 容器引擎已启动）、uv、Node.js；构建时需联网 |

## 四、从零启动（Windows PowerShell）

### 1. 新克隆一份代码并切到修复分支

```powershell
git clone https://github.com/smrrrrr/CampusClaw-Group.git CampusClaw-review
cd CampusClaw-review
git switch fix/security-lesson09-DuLaolaoDu
git checkout 55d18d36d6aec194e549271658e7f7d15d683a0f
$ProjectRoot = (Get-Location).Path
```

> 如果远程没有该分支，说明尚未推送；可让提交者推送后再拉取，或基于 `55d18d3` 本地创建同名分支。检出固定提交后 Git 提示 detached HEAD 属正常现象。

### 2. 确认数据包位置并校验

数据包已放在项目根目录，结构如下：

```
CampusClaw-review\
└── CampusClaw-Review-Data-20261105(1)\
    └── CampusClaw-Review-Data-20261105\
        ├── restore.py
        ├── manifest.json
        ├── 验证结果.md
        ├── 验证记录.json
        └── 交接说明.md
```

校验数据包完整性（不修改任何文件）：

```powershell
$PackageRoot = "$ProjectRoot\CampusClaw-Review-Data-20261105(1)\CampusClaw-Review-Data-20261105"
python "$PackageRoot\restore.py" --verify-only
```

出现 **PASS** 才继续。

### 3. 一条命令恢复数据并生成本机配置

```powershell
python "$PackageRoot\restore.py" --project "$ProjectRoot" --port 8084
```

脚本行为：
- 校验代码、资料和数据库，恢复到 `data/review` 与 `backend/uploads`
- 自动生成本机独有的 JWT、MCP 和队列密钥，模型 Key 留空
- 目标已有 `.env`、交接库或资料时会**拒绝覆盖**，应重新克隆新目录
- 已有库**不运行** `dev_seed.py`（会重置学生账号）
- 8084 被占用时改为 8085 等空闲端口，后续访问地址同步修改
- 恢复不调用模型、不启动容器

### 4. 安装测试依赖（uv 与 Node.js 需另外安装）

```powershell
Set-Location $ProjectRoot
uv sync --project backend --locked
npm --prefix frontend ci
```

### 5. 启动七个服务

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8084/health
```

服务包括：nginx、frontend、backend、mcp-tools、rabbitmq、grading-dispatcher、grading-worker。
首次构建和 RabbitMQ 就绪需要等待。`/health` 返回 `model: not_configured` 是预期状态（本包未配置真实模型 Key）。浏览器打开 `http://localhost:8084/login`。

## 五、本包专用演示账号

| 账号 | 角色 | 范围 | 本包口令 |
| --- | --- | --- | --- |
| TEA001 | 数学教师 | 任教101/102，带班101 | `ReviewT!siw18rU4-1Pjh5bO` |
| TEA002 | 物理教师 | 任教101/102，带班102 | `ReviewT!siw18rU4-1Pjh5bO` |
| 20260001 | 演示学生 | A班101 | `ReviewS!n4n1UkGuPztOhfiE` |
| 20260002 | 演示学生 | B班102 | `ReviewS!n4n1UkGuPztOhfiE` |

这些口令只用于本包本地演示；原系统账号口令没有变更。验证不同角色可用不同浏览器或无痕窗口。

## 六、先验证这几项（基础功能）

| 要验证的功能 | 怎样操作 | 应看到什么 |
| --- | --- | --- |
| 作业历史 | 学生20260001 → 交作业 → 作业历史 | 有"【合成演示】满分历史"，本人答案、100分及评语保留，已关闭不能再提交 |
| 满分不入错题 | 同一学生 → 错题 | 没有上述满分作业 |
| 改分清理错题 | 教师TEA001 → 101班 → 作业与改分，给"【合成演示】低分错题"改100；学生刷新 | 对应错题被移除，作业历史和新成绩仍保留 |
| 后台初批 | 教师101班的"【合成演示】待批改" → AI初批 → 查看提交 | 先收到任务并查看状态；真实成功评分需自行配置有效模型Key |
| 命题发布 | 教师智能命题 → 现有试卷，必要时复制为新草稿 → 定稿 → 发布为作业 | 在所选班级作业列表出现；指定未来截止时间 |
| 班级隔离 | 101学生和102学生分别查看资料及作业 | 只能看到本班内容 |

没有配置模型时，AI任务可能进入重试和最终失败，这是依赖未配置的结果。需要真实调用时，仅在本机 `.env` 填写自己的 `DEEPSEEK_API_KEY`，再 `docker compose up -d` 让配置生效。

## 七、安全修复专项验证（第9课核心）

以下三项是第9课的核心验收，必须全部通过才算完成。

### 7.1 安全探针（SEC-01～SEC-08 全量）

```powershell
backend\.venv\Scripts\python.exe apitest\probe_security_precheck.py --output .review\peer-api.json
```

预期：**26 通过，0 红项**。退出码 0。
重点关注：
- SEC-02：学生跨班下载讲义 → 404（不是 403）
- SEC-07：一次技能调用后，`/api/mcp/tool-calls` 返回含 `skill_id`、`duration_ms`、`tokens`
- SEC-08：学生调用写入类 MCP 工具 → 被拒绝
- 学生请求审计日志查询接口 → 403

### 7.2 全量门禁回归

```powershell
backend\.venv\Scripts\python.exe scripts\check.py
```

预期：**28/28 PASS**，末尾输出"门禁全部通过"。包含：
- openspec 规约校验、分层检查、密钥扫描
- 前端类型检查
- 全部 28 组 apitest（基线、错题、作业链、MCP、安全探针、注入三件套等）

> 这是临时库 + 假模型测试，不会修改恢复的演示数据。

### 7.3 提示注入实验（SEC-08 深度验证）

```powershell
backend\.venv\Scripts\python.exe reports\security-evidence\prompt-injection\run_experiments.py
```

预期：**4/4 通过**。四组实验：

| 实验 | 内容 | 通过判据 |
| --- | --- | --- |
| 实验一 | 直接指令注入 | 5 组 payload 全部被 `looks_like_injection` 拦截；3 组正常文本不误报 |
| 实验二 | 间接注入（参数校验） | `validate_arguments` 拒绝缺必填、超长、枚举越界、类型错误、额外字段 |
| 实验三 | 指令外泄（输出截断） | 工具输出截断至 `TRUNCATE_CHARS`，泄露标记不出现在截断后文本或摘要中 |
| 实验四 | 写入类工具学生越权 | `writable=True` 时学生被拒，教师放行 |

证据：`reports/security-evidence/prompt-injection/results.json`

### 7.4 四步演示走查（老师当堂演示路径）

这是最终验收的走查路径，四步全绿即通过。组员评审时必须走完并记录每步结果：

| 步骤 | 操作 | 预期结果 |
| --- | --- | --- |
| ① 登录取令牌 | `POST /api/auth/login` 用 TEA001 登录 | 返回 200，拿到 access_token |
| ② 提交任务返回 202 | 教师对一份待批改作业触发 AI 初批 | 返回 202，任务进入队列 |
| ③ 轮询状态 | 轮询任务状态接口 | 看到 pending → running → succeeded（需配置模型 Key；未配置时为 failed，记录原因即可） |
| ④ 换班查别班讲义拿 404 | 用 20260001（101班）token 请求 102 班讲义下载 | 返回 **404**（不是 403），不泄露存在性 |

> 步骤③在未配置模型 Key 时任务会最终失败，这是依赖未配置的正常结果，不影响步骤④的安全验证。评审时记录实际状态即可。

### 7.5 手动验证关键安全行为（用于交叉评审）

**SEC-02 跨班 404**：
1. 用 20260001（101班）登录，拿到 token
2. 构造请求访问 102 班的讲义 ID：`GET /api/materials/{102班讲义ID}/download`，header 带 `Authorization: Bearer <token>`
3. 应返回 **404**（而非 403）

**CSRF 令牌**：
1. 登录后查看响应 Cookie，应包含 `csrf_token`（非 HttpOnly，SameSite=Lax）
2. 不带 `X-CSRF-Token` 头发 POST 写请求 → 应被拒
3. 带 `Authorization: Bearer` 头的请求豁免 CSRF 校验

**审计日志字段**：
1. 教师登录后调用一次技能（如智能命题）
2. `GET /api/mcp/tool-calls` 查看最近一条记录，应含 `skill_id`、`duration_ms`、`tokens` 字段

**审计日志查询授权**：
1. 学生 token 请求 `GET /api/teacher/audit-logs` → 应返回 403
2. 班主任 token 请求同班审计日志 → 200；查非本班 → 403

**注入防御**（`apitest/cases/` 下已有专门反例用例，随 `check_injection.py` 接入 `make check` 回归）：
- SQL 注入：`apitest/cases/api/student/conversations/chat/POST-sqli.py`，4 组 payload 不触发 500 或数据泄漏
- XSS：`apitest/cases/api/materials/xss.py`，`<script>` / `<img onerror>` 等标签经 `html.escape()` 转义
- CSRF：`apitest/cases/csrf.py`，缺 `X-CSRF-Token` 头返回 403，带正确令牌通过，Bearer 头豁免

## 八、评审要求（严格按老师任务清单执行）

### 8.1 评审前确认

所有安全修复代码与归档材料已完成（见第二节"归档材料"表）。评审前组员只需：
1. 按第四节完成环境搭建
2. 运行第七节全部验证，确认全绿

### 8.2 交叉评审流程

老师要求：**组内另一人照对照表独立复现至少 2 条修复，判定一致才算过。**

1. 先按第四节完成环境搭建和启动
2. 运行第七节全部验证（7.1 探针、7.2 check.py、7.3 注入实验、7.4 四步走查）
3. 手动复现至少 2 条修复（推荐 SEC-02 跨班 404 和 SEC-08 学生写入工具拒绝）
4. 按"四件事"格式填写评审记录

### 8.3 评审记录格式（固定四件事）

每条评审记录必须包含以下四件事，缺一不可：

```
## <修复编号，如 SEC-02>

- 用什么手段查：<具体操作，如"用学生A的token请求班级B的讲义下载接口">
- 查了什么：<观测对象，如"HTTP状态码、响应体是否含B班正文、审计日志是否有记录">
- 判据：<通过标准，如"状态码404、响应体不含B班正文、审计日志有该请求记录">
- 结果：<实际结果，如"状态码404，正文无泄漏，审计日志已记录 → PASS">
```

### 8.4 评审记录命名与数量

- 文件命名：`reports/review-02.md`、`reports/review-03.md`，依次递增（`review-01.md` 已存在于数据包）
- **至少两份来自 AI 自审或脚本输出**：`make check`、`make check-security` 的输出可作为机器评审证据
- **人工评审只做机器判不了的项**（如 XSS 看源码、CSRF 跨站伪造、SEC-08 实验现象），并为其补一条用例或一条规则
- 每条修复的评审判定必须与修复者一致才算通过

### 8.5 make check-security 入口

```powershell
backend\.venv\Scripts\python.exe scripts\security_precheck.py
```

该脚本覆盖：工作区密钥扫描、git 历史扫描、`npm audit`、`pip-audit`、前端产物密钥扫描。有命中或高危时退出码非 0。`README.md` 中已注明此入口。

> gitleaks 本机未安装；如需可另行安装后运行 `gitleaks detect --source .`。现有 `security_precheck.py` 已覆盖等价扫描范围。

### 8.6 评审后

- 任何一组出红先修回归再继续——带着回归的修复不算完成
- 评审后另按规约修复红项，暂不合并 main
- 修复逐条单独提交，提交信息写清依据哪一条 SEC 编号

## 九、数据包保留与脱敏范围

| 项目 | 本包处理 |
| --- | --- |
| 班级、资料、教案、题库、已有作业题面 | 保留：2班、8份班级资料、2份教研资料、14道题、3份试卷、7份作业（含新增3份合成样例） |
| 资料及原图 | 仅复制被记录引用的31个文件，逐个核对SHA-256 |
| 原作答、成绩、错题、执行任务 | 清空；仅加入上述3组合成提交和1条合成错题，后台任务初始为空 |
| 姓名、手机号、原口令哈希 | 姓名替换为演示名称，手机号清空，原哈希移除并换成本包口令哈希 |
| 会话、提问、登录、验证码、审计、MCP调用记录 | 清空 |
| 原MCP令牌和发现缓存 | 清空，服务器保留campus-tools但断开，相关技能禁用 |
| 自定义助手提示词 | 清空，恢复使用代码默认提示词 |
| 已发布作业截止时间 | 仅导出副本延后30天至UTC 2026-12-05，避免队友打开后全部已截止 |

要演示真实 MCP 调用，可在教师"助手配置"删除旧 campus-tools 登记，再按同名重新登记：地址 `http://mcp-tools:8090`，令牌使用你自己 `.env` 中的 `MCP_AUTH_TOKEN`；连接成功后重新启用对应技能。令牌不写入评审报告。

## 十、本次修复涉及的关键文件

| 范围 | 文件 | 变更 |
| --- | --- | --- |
| 模型 | `backend/models.py` | AuditLog 新增 action/object_id/skill_id/duration_ms/tokens；McpToolCall 新增 skill_id/duration_ms/tokens；McpTool 新增 writable |
| 数据库 | `backend/database.py` | 启动时自动 ALTER TABLE ADD COLUMN（幂等） |
| 迁移 | `scripts/migrate_audit_fields.py` | 独立迁移脚本，可重复执行 |
| 中间件 | `backend/main.py` | audit_security_middleware 记录 403+404；csrf_protection_middleware 双提交 Cookie 校验 |
| SEC-02 | `backend/routers/materials.py` | `_check_material_access` 跨班→404 |
| SEC-02 | `backend/homework_service.py` | `_assert_teacher_can_access_homework` 跨班/非作者→404 |
| SEC-02 | `backend/routers/lesson_plans.py` | `owned()` 捕获 403 重抛 404 |
| SEC-02 | `backend/mistake_service.py` | `_assert_student_owns_mistake` 非本人→404 |
| SEC-02 | `backend/routers/teacher.py` | `reset_password` 非班主任→404 |
| SEC-02 | `backend/routers/student.py` | `_coerce_conversation` 跨班→404 |
| SEC-02 | `backend/routers/research_materials.py` | `source_record` 学科不符→404 |
| SEC-07/08 | `backend/mcp_orchestrator.py` | skill_id 提取、duration_ms 测量、writable 工具学生拒绝 |
| XSS | `backend/routers/materials.py`、`student.py` | 文本字段 `html.escape()` |
| CSRF | `backend/routers/auth.py` | 登录/改密下发 csrf_token Cookie |
| 注入模式 | `backend/mcp_client.py` | `INJECTION_PATTERNS` 增强匹配 `api[_s]*key` |
| 测试 | `apitest/probe_security_precheck.py` | SEC-02 期望 403→404；SEC-07 字段含 tokens |
| 测试 | 8 个 apitest 文件 | fetch-then-check 场景期望码 403→404 |
| 实验 | `reports/security-evidence/prompt-injection/run_experiments.py` | 4 组提示注入实验 |
| 报告 | `reports/security-evidence/lesson09-security-fix-report.md` | 修复前后对照表 |

## 十一、注意事项

1. **不要运行 `dev_seed.py`**：已有数据的库运行它会重置学生账号。
2. **不要提交 `.env`、数据库、`uploads/`、数据包**：这些只在本机保留，不进 Git。
3. **模型未配置是预期**：`/health` 返回 `model: not_configured` 不影响安全验证；需要真实 AI 功能时自行填写 `.env`。
4. **CSRF 豁免**：带 `Authorization: Bearer` 头的请求不受 CSRF 校验（头部令牌不受 CSRF 影响）；Cookie 会话的写请求必须带 `X-CSRF-Token`。
5. **403 vs 404 口径**：fetch-then-check（按 ID 取资源后校验归属）返回 404；参数篡改（class_id 在 query/body）和角色越权返回 403。
6. **审计中间件**：403 和 404 都会被 `audit_security_middleware` 记录，确保跨班拒绝可追溯。
7. **gitleaks**：本机未安装 gitleaks，现有 `scripts/security_precheck.py` 已覆盖 git 历史扫描、npm audit、pip-audit、前端产物密钥扫描。如需 gitleaks 可另行安装后运行 `gitleaks detect --source .`。
8. **SEC-05 运行时扫描项目名**：已修复。`security_precheck.py` 第 58 行不再硬编码 `com.docker.compose.project`，改为从 `.env` 读取 `COMPOSE_PROJECT_NAME`（回退 `campusclaw-groupv3`）；`readonly_accounts()` 也改为从 `.env` 的 `DATABASE_URL` 推导数据库路径并回退 `data/current/`、`data/review/`、根目录。本机 `secret-baseline.json` 显示 `complete=True`、`leak_detected=False`。
9. **SEC-06 依赖处置**：已修复。前端 `next`(critical)、`postcss`(high)、后端 `pillow`/`pyasn1`/`certifi`/`ecdsa`/`python-jose` 等 9 个漏洞包已写入 `reports/security-evidence/dependency-exceptions.json`，每条含理由、降险措施与 `review_after=2026-12-15`。`security_precheck.py` 新增 `load_exceptions()` 与 `check_dependency_exceptions()`，已登记漏洞不计入红项；未登记或过期登记才触发 RED。本机 `security_precheck.py` 退出码 0。

完整制作及验证结果见数据包 `验证记录.json`，文件清单与指纹见 `manifest.json`。其中自动验证不代替队友本人复现。

本包仅供组内私下传递，含教师答案和内部教学资料，zip、数据库、uploads 及 .env 均不上传 GitHub。代码与脱敏评审记录通过 PR 交接。
