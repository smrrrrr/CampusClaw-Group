# Next 15 升级后浏览器页面验收与安全门禁复跑

- 时间：2026-11-16 UTC；变更 `2026-11-16-upgrade-next-15-5-28`
- 基线：未提交工作区（`next@15.5.28`；HEAD `01f47cc`）
- 性质：补做任务 3.2 的页面级验收与 4.3 的安全门禁复跑；不修改业务代码、门禁判据或验收预期

## 一、隔离环境

| 项 | 值 |
| --- | --- |
| 项目名 | `ccnext15-browser` |
| 对外端口 | `55890`（仅本机回环） |
| 数据 | 临时目录中的合成 SQLite，由 `scripts/lesson10_seed_fixture.py` 生成（班级 201/202、`T10A/T10B/S10A`，密码为夹具固定值） |
| 额外合成数据 | 为验证切班与首次改密，另将 `T10A.teaching_classes` 设为 `[201,202]`，并新增 `N10A`（`must_change_password=true`）；均只写临时库 |
| 镜像 | `campusclaw-backend:984c4c8…`、`campusclaw-frontend:next15-20261116t124118z`、`campusclaw-mcp-tools:984c4c8…` |
| 浏览器 | 本机 Chrome 157，headless，`puppeteer-core 24.43.1` |
| 未使用 | 真实教学库、既有 8081 栈、`dev_seed.py`、真实模型 |

## 二、结果

### 2.1 页面级会话与守卫（任务 3.2）

| 检查 | 预期 | 实测 | 结果 |
| --- | --- | --- | --- |
| 登录页渲染 | 显示登录表单 | 显示 CampusClaw 与登录按钮 | PASS |
| 首次登录强制改密 | 跳转 `/change-password` | `/change-password` | PASS |
| 教师登录 | 进入 `/teacher` | `/teacher/lesson-prep` | PASS |
| 刷新恢复会话 | 不回落登录页 | 仍在教师页 | PASS |
| 教师切班 | `class_id=202` 生效 | `/teacher/…?class_id=202` | PASS |
| 登出 | 回 `/login`，刷新仍停留 | `/login`；Refresh Cookie 已清除 | PASS |

证据：[page-checks.json](page-checks.json)、[logout-checks.json](logout-checks.json)。

说明：第一轮脚本在资料页查找登出按钮未命中，属脚本选择器错误；改到教师页按钮后 4/4 通过，未修改应用代码。

### 2.2 页面渲染（任务 3.3 的一部分）

| 检查 | 预期 | 实测 | 结果 |
| --- | --- | --- | --- |
| Markdown 与 KaTeX | 预览中出现公式节点 | `.katex` 节点 2 个，正文含 `E=mc` | PASS |

### 2.3 跨班资料状态码（任务 3.3）

| 请求 | 预期 | 实测 | 结果 |
| --- | --- | --- | --- |
| 学生本班资料列表 | 200 | 200 | PASS |
| 学生篡改 `?class_id=202` 访问他班列表（规约场景） | 403，无正文 | 403，无他班正文 | PASS |
| 学生按 ID 读取他班材料 2 | 规约未规定；防枚举设计 | 404，无正文泄露 | 按设计 |

依据：`class-data-isolation` 要求学生篡改 `class_id` 参数时返回 403；按 ID 读取采用 fetch-then-check 一律 404（`backend/routers/materials.py` 注释明确“不泄露存在性”），与 `research-materials`、`agent-assistant` 的 404 防枚举写法一致。任务书原文“别班讲义 404/403”两种说法在此统一为：**参数篡改 403，按 ID 404**。证据：[cross-class-checks.json](cross-class-checks.json)。

### 2.4 安全门禁复跑（任务 4.3）

- 操作：将主仓库数据包中的本地库只读副本放到 `data/current/campusclaw.db`（含 `<demo-teacher-1>/<demo-teacher-2>/<demo-student-1>/<demo-student-2>`），未注入账号、未改 `scripts/security_precheck.py`。
- 结果：`make check-security` **PASS，exit 0**；`unregistered_vulns=[]`、`expired_exceptions=[]`、npm `critical=0/high=0/low=4`、backend/mcp 漏洞包 0。
- 证据：[security-run-after-db-restore.json](security-run-after-db-restore.json)、[accounts-readonly.json](accounts-readonly.json)。
- 与 `make check`（41/41，exit 0）合并后，两条门禁均为 0。

## 三、边界

- 浏览器为桌面 headless Chrome，不是手机实机；任务 3.2 中“实际手机浏览器”的要求仍以课程演示为准。
- 合成库仅覆盖演示班级与账号，不代表真实教学数据。
- 本批次证据中的演示账号标识已替换为角色占位符（`<demo-teacher-1>` 等），原始标识仅保存在本地数据包，不随仓库发布。
- 3.3 的 403 判据未满足，按真实结果保留未勾选。
