# 第二次安全评审记录（修复后交叉评审）

**状态：修复已完成，四项核心门禁本机全绿；本文件供组内另一人独立复现后填写。未填写完毕不可据此合并。**

日期：2026-11-11（修复完成日）。修复实施者：当前会话。本文件的人工评审部分必须由**另一名组员**独立填写，不得由修复者代填。

## 一、修复后门禁结果（机器自审，不可改）

以下四项由脚本输出，作为 AI 自审证据，人工评审只需核对退出码与通过数是否一致：

| 门禁 | 命令 | 预期结果 | 本机实测 |
| --- | --- | --- | --- |
| 全量回归 | `scripts/check.py` | 28/28 PASS，退出码 0 | 28/28 PASS（含 check_injection） |
| 安全探针 | `apitest/probe_security_precheck.py` | 26 通过，0 红项，退出码 0 | 26 通过，0 红项 |
| 提示注入实验 | `reports/security-evidence/prompt-injection/run_experiments.py` | 4/4 通过 | 4/4 通过 |
| 密钥与依赖 | `scripts/security_precheck.py --reuse-dependency-evidence` | PASS，退出码 0 | PASS（密钥0泄漏、依赖全部登记） |

证据文件：`reports/security-evidence/api-probe.json`、`reports/security-evidence/prompt-injection/results.json`、`reports/security-evidence/run.json`、`reports/security-evidence/secret-baseline.json`。

## 二、修复前后对照表（摘要）

完整对照表见 [security-fix-log.md](security-fix-log.md)。关键变化：

| SEC 项 | 修复前 | 修复后 |
| --- | --- | --- |
| SEC-02 跨班隔离 | fetch-then-check 返回 403 | 统一返回 404 |
| SEC-05 密钥扫描 | 运行日志/前端产物未扫（项目名硬编码） | 范围完整，0 命中 |
| SEC-06 依赖处置 | 9 个漏洞包未登记 | 全部登记例外条目，门禁通过 |
| SEC-07 审计字段 | 缺 skill_id/duration_ms/tokens | 七列齐全 |
| SEC-08 工具授权 | 写入工具不区分角色 | writable 字段，学生被拒 |
| 注入三件套 | 无反例用例 | 三条反例接入 make check，9/9 通过 |

## 三、请组员独立复现（留空，不能由修复者代填）

仓库根目录，按 [交接说明](../Lesson9-安全修复-交接说明.md) 第四节完成环境搭建。**任选至少 2 条**修复独立复现，不只读本文件结论。每条按"四件事"填写：

### 复现项 1（推荐：SEC-02 跨班 404）

- **用什么手段查**：（例：用 20260001/101班 token 请求 102 班讲义下载接口 `GET /api/materials/{id}/download`）
- **查了什么**：（例：HTTP 状态码、响应体是否含 102 班正文、审计日志是否有记录）
- **判据**：（例：状态码 404、响应体不含正文、审计日志有该请求记录）
- **结果**：（待填写）

### 复现项 2（推荐：SEC-08 学生写入工具拒绝）

- **用什么手段查**：（例：用学生 token 调用写入类 MCP 工具）
- **查了什么**：（例：工具调用返回状态、审计日志是否有 denied 记录、数据库是否有残留）
- **判据**：（例：返回 403 或 denied、审计日志有记录、数据库无写入）
- **结果**：（待填写）

### 复现项 3（可选：注入防御）

- **用什么手段查**：（例：运行 `apitest/check_injection.py`，或手动对检索接口提交 SQL 注入 payload）
- **查了什么**：（例：状态码是否非 500、材料表数据是否完整、XSS 标签是否转义）
- **判据**：（例：无 500、数据无破坏、`<script>` 被转义为 `&lt;script&gt;`）
- **结果**：（待填写）

### 复现项 4（可选：CSRF 令牌）

- **用什么手段查**：（例：登录后用 Cookie 会话不带 `X-CSRF-Token` 头发 POST 写请求）
- **查了什么**：（例：状态码、响应体是否含 CSRF 拒绝信息）
- **判据**：（例：状态码 403；带正确令牌后不被 CSRF 拒绝；Bearer 头豁免）
- **结果**：（待填写）

## 四、门禁复现确认（组员运行后填写）

组员在本机独立运行以下命令，记录实际结果：

| 门禁 | 命令 | 实际结果 | 退出码 |
| --- | --- | --- | --- |
| 全量回归 | `backend\.venv\Scripts\python.exe scripts\check.py` | 待填写 | 待填写 |
| 安全探针 | `backend\.venv\Scripts\python.exe apitest\probe_security_precheck.py` | 待填写 | 待填写 |
| 注入实验 | `backend\.venv\Scripts\python.exe reports\security-evidence\prompt-injection\run_experiments.py` | 待填写 | 待填写 |
| 密钥依赖 | `backend\.venv\Scripts\python.exe scripts\security_precheck.py --reuse-dependency-evidence` | 待填写 | 待填写 |

## 五、评审结论

| 执行人 | 本人机器/系统 | 日期 | 独立复现项数 | 与修复者结论是否一致 | 本人签名 |
| --- | --- | --- | --- | --- | --- |
| 待填写 | 待填写 | 待填写 | 至少 2 项 | 待判断 | 待本人签名 |

**注意**：
- 无需为了交材料伪造签名或绿色结果。
- 任一复现项与修复者结论不一致，先在本文件记录差异，再通知修复者排查。
- 人工评审只做机器判不了的项（如 XSS 看源码、CSRF 跨站伪造、SEC-08 实验现象），并为其补一条用例或一条规则。
