# 第 2—5 课功能验收记录

> 本文保留最初的验收发现。后续用户已确认“引导开启覆盖自定义提示词”，并要求按实现调整其他规约；导入权限、后端首次改密、页面刷新和审计已修复并重新部署。修复后 71 项回归通过。最新记录见 `openspec/changes/harden-foundation-and-align-specs/validation.md`；下文旧的失败数量不代表当前状态。

日期：2026-10-18。对象：`CampusClaw _Group` 小组项目，Docker Compose 项目名 `campusclaw-group`，入口 http://localhost:8081/login。

## 结论

基础链路可以演示，但不能把第 2—5 课标记为全部验收完成。完成了 60 项隔离后端检查及 1 项真实 DeepSeek 流式调用检查：共 61 项，52 项通过、9 项未通过。未通过的断言中，提示词问题有两项断言，CSV 越权包含创建和更新两个场景；数量不等于独立缺陷数。

另外执行了浏览器登录、菜单导航和刷新检查，以及当前部署的 HTTP/CSS、原文件存在性检查。没有改动业务代码、运行现有种子初始化、重置真实账号密码或上传测试资料到现有数据库。

## 课程对照

| 课程 | 已验证能力 | 验收缺口 |
| --- | --- | --- |
| 第 2 课：SDD 与 OpenSpec | 已有登录、权限、班级隔离、资料上传、检索和助手规约及变更文档 | `openspec/specs/` 的业务规约及 `add-agent-assistant` 等目录仍未被 Git 跟踪；规约与当前代码存在下述偏差。未执行官方 OpenSpec CLI 校验 |
| 第 3 课：认证授权与知识库入库 | 教师/学生登录；HttpOnly 刷新 Cookie；刷新、改密、弱密码拒绝、五次失败锁定；教师与学生角色拦截；学生列表/资料的基本班级隔离；班主任重置权限；Docker 服务健康 | 首次改密可以绕过后端；CSV 导入越权；审计查询 500；页面刷新后无法保持会话；现有原讲义缺失 |
| 第 4 课：可追溯检索 | MD/TXT/DOCX/PPTX/文字型 PDF 样本上传与解析；分块和 512 维向量持久化；keyword/vector/hybrid 检索；班级隔离；无关问题无命中；回答引用包含材料名、ID、块序号、摘要；预览/下载、重建索引和删除清理 | 向量为字符 n-gram 哈希，尚不能据此认定同义改写语义检索质量合格；“讲义与检索”页面搜索调用资料元数据过滤接口，没有接正文片段检索与命中定位 |
| 第 5 课：提示词、技能与流式会话 | 班级配置保存/读取及权限限制；多轮历史传递；SSE 增量与正常结束事件；引用和消息持久化；他人会话隔离；模型失败时返回段落；真实 DeepSeek 流式调用成功 | 引导开启时自定义提示词不生效；无配置时引导默认状态不一致；异常结束缺少引用/剩余额度；每日上限与规约不一致 |

## 需要修复的问题

### 优先修复：学生 CSV 导入绕过班级权限

位置：`backend/routers/teacher.py` 的 `import_students`。

- 仅任教 102 的教师导入已属于 101 的学生，返回 200，修改成功。
- 任教 101/102 的教师导入目标为 103 的新学生，也返回 200。
- 应同时验证已有学生归属和导入目标班级，禁止借导入操作跨班修改、转班或创建账号。
- 验收断言：`auth.csv_other_class_update_denied`、`auth.csv_other_class_create_denied`。

### 优先修复：首次改密只在前端拦截

位置：`backend/deps.py` 和业务接口依赖。

`require_password_changed` 已定义但业务接口没有使用。持有 `must_change_password=true` 的有效登录令牌直接请求 `/api/materials` 返回 200，应拒绝业务访问并引导改密。应覆盖资料、助手及教师业务入口，不能只补一个接口。

验收断言：`auth.first_password_blocks_business`。

### 审计查询不可用

位置：`backend/routers/teacher.py` 的 `query_audit_logs`。

接口返回 500。代码引用 `AuditLog`，但该文件没有导入模型。即使补齐导入，当前查询也没有班主任本班范围过滤；应按现有角色和规约限定查询范围。浏览器菜单进入“审计与统计”仍显示“该模块尚未接入”。

验收断言：`auth.audit_logs_query`。审计按班范围仅做代码检查，尚未动态验收。

### 开启解题引导后自定义提示词被忽略

位置：`backend/llm_service.py` 的 `resolve_system_prompt`。

教师可以保存并回读自定义提示词，但 `tutor_enabled=true` 时会用固定引导框架替换自定义内容。已用请求捕获确认，传给模型的系统消息中没有教师设置的标记。规约要求将技能规则并入系统提示词。

验收断言：`agent.tutor_preserves_custom_prompt`、`agent.actual_messages_use_custom_prompt`。

### 未配置班级的引导状态前后不一致

配置读取接口在没有配置行时返回 `tutor_enabled=true`；实际聊天的 `cfg=None` 会使用普通提示词，且 `tutor_on=false`。学生界面静态技能徽标也不能作为实际状态证据。

验收断言：`agent.default_tutor_matches_config_api`。

### AI 异常降级缺少结束元数据

位置：`backend/routers/student.py` 的 `chat.event_stream`。

失败时会返回检索段落并保存消息，但只发送 `error`，没有携带 `citations`、`remaining` 的结束事件。首次显示时前端拿不到结构化引用和剩余次数；重新读取历史时才能回读保存的来源。

验收断言：`agent.failure_end_event_has_sources`。

### 每日提问额度与规约不一致

`backend/services.py` 的 `AI_DAILY_LIMIT=40`，OpenSpec 要求 20。隔离数据库中已有当日 20 条记录后继续提问，实际返回 200，预期为 429。需要统一产品决定、规约、实现与界面，不应只修改说明来掩盖验收差异。

验收断言：`agent.spec_20_question_limit`。

### 浏览器刷新后返回登录页

实际操作：教师登录成功，进入助手配置/审计页面，然后刷新，地址变回 `/login`。`AuthGate` 在内存没有 Access Token 时直接跳转，没有先用现有 Refresh Cookie 恢复用户会话。

这是浏览器复现，未计入上面的 61 项后端检查。

## 当前数据及交接问题

- 当前三个 Docker 服务运行正常，前后端健康；`/api/health`、`/login` 及两份 CSS 资源返回 200。
- 当前数据库只有一条 `lesson.pdf` 资料记录，`is_indexed=true`，但对应物理原文件不存在。因此已有索引不代表预览/下载可用，需要重新上传正确原讲义。验收生成的新样本均放在临时目录，与现有资料分开。
- 旧 `apitest/conftest.py` 默认指向个人项目 `CampusClaw/data/campusclaw.db`，端口 8001，学生账号仍为 `20230002`。未执行这套旧测试，避免误操作个人项目；交接前需要改为显式目标和独立测试数据。
- 当前小组目录远程仍指向 `smrrrrr/CampusClaw.git`；未提交或推送本次检查内容。

## 复现方式与验证范围

新增脚本：`apitest/check_lessons_2_5.py`。在项目根目录运行：

```powershell
Get-Content -Raw -Encoding utf8 apitest/check_lessons_2_5.py | docker compose exec -T backend /app/.venv/bin/python -
```

这会在后端容器的独立子进程内创建临时数据库和上传目录，以 HTTP ASGI 接口运行 60 项检查。存在失败时退出码为 1。测试结束自动清理临时目录，不修改服务进程的环境变量或数据库。

如需真实模型连通性检查，最后增加 `--real-llm`；会使用服务端已有 Key 发起一次短请求。此次已真实调用成功，收到 16 个文本增量，内容为：“判别式Δ如何由系数a、b、c计算？[1]”。未记录或输出真实密钥。

助手接口、历史、引用与失败分支测试使用可控模型替身；真实模型调用单独验证。因此不把 ASGI 分块检查当作“浏览器经 Nginx 的完整 AI 流式端到端验收”。已检查 Nginx 关闭缓冲配置，但未在浏览器发起真实学生提问。未验证扫描 PDF/OCR、图片入库、复杂公式保真、大文件边界、并发额度竞争或完整学生页面操作；五类文档仅使用生成的基础样本。

建议修复顺序：导入权限与强制改密 → 会话恢复与审计 → 提示词和引导默认值 → 异常事件与额度 → 正文检索界面 → 使用真实示例讲义完成教师上传至学生引用的浏览器验收 → 更新规约并提交小组仓库。
