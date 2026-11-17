# 项目报告 · CampusClaw

仓库：[smrrrrr/CampusClaw-Group](https://github.com/smrrrrr/CampusClaw-Group)；代码基线 `main@8964200`；核查日期 **2026-11-17**。贡献者按 Git 署名列示：**Jackler/hexzun1**（系统集成、依赖与运行验证）、**Grey_Wolf_King**（作业、学情、安全修复）、**smrrrrr**（异步批改、门禁修复、交叉评审与交付整理），提交依据见 [reports/contributions.md](reports/contributions.md)。本次 Harness 为 **Codex**，规则入口为 `AGENTS.md`。

## 1. 一句话介绍

CampusClaw 面向中学教师和学生，把讲义导入、备课、命题、作业初批与资料答疑连成流程，减少教师重复整理和批改工作，并让学生在本班、本学科资料范围内学习；教师保留发布与最终改分权。功能入口见 [README.md](README.md)。

## 2. AI 用在了哪里

AI 辅助实现及审核的可追溯样本包括 `backend/grading_service.py`、`scripts/trivy_os_gate.py`、`apitest/check_os_vuln_gate.py`，依据为 [reports/review-async-grading.md](reports/review-async-grading.md)、[reports/review-04.md](reports/review-04.md)。Codex 读取 `AGENTS.md`，按规约自审、执行脚本，再交人确认。七类完整问题、命令和判据集中在 [AGENTS.md](AGENTS.md) 的“七类代码核查责任”表：

| 类别 | 核查问题与手段 |
| --- | --- |
| 接口入口 | 参数、角色、状态码是否正确；脚本跑合法、未登录及越权请求。 |
| 业务逻辑 | 幂等与教师终评是否成立；AI 对照规约，脚本验状态和旧结果拒写。 |
| 数据库 | 失败是否回滚、迁移是否保留数据；脚本做故障注入和重复迁移。 |
| 公共函数 | 空值、边界、复用是否正确；单元断言、分层检查。 |
| 错误处理 | 超时、重投是否可恢复且无泄密；脚本注入模型、代理与数据库故障。 |
| 安全 | 跨班、工具授权、密钥与依赖是否受控；安全探针、双门禁、镜像扫描。 |
| 性能 | 请求是否等待模型、瓶颈在哪；20 并发断言与独立同参压测。 |

覆盖率百分比门槛、全局 P95 门禁尚未实现；现有性能数据的环境与限制见 [reports/bench.md](reports/bench.md)，不把测试数量当覆盖率。

## 3. 审核记录

以下三份记录均说明手段、对象、判据、结果及修复，发现来自 AI 自审或脚本，有历史原始证据和本次复跑：

| 记录 | 发现、判据与结果 |
| --- | --- |
| [reports/review-04.md](reports/review-04.md) | 合成扫描反例发现空报告及同 CVE 未登记包被放行；要求无效报告退出 2、未登记 HIGH 退出 1。修复 `cc5b0fc`，当时 19/25 转 25/25，本次扩展回归 31/31。 |
| [reports/review-05.md](reports/review-05.md) | AI 源码核查配合隔离探针发现写工具上下文缺失、权限分类丢失；学生必须被拒且不得写分。修复 `97ba0f5`；本次安全探针 41/41，0 红项。 |
| [reports/review-06.md](reports/review-06.md) | 远端镜像扫描拦下两份镜像的 ncurses-bin HIGH；保留原始告警，移除不用的 infocmp，并核验实际镜像。修复 `3da68c5` 后 CI 转绿，期限与版本受例外表约束。 |

人工交叉评审见 [reports/peer-review.md](reports/peer-review.md)：smrrrrr 在 PR #3 复核并正式批准，发现固化为 `apitest/check_os_vuln_gate.py` 反例，未由代理代签。

## 4. 高风险三查

本次在 Windows、临时 SQLite、假模型/MCP 环境复跑，命令均从仓库根执行，环境准备见 [reports/reproduce-checks.md](reports/reproduce-checks.md)。

| 检查与记录 | 手段、判据、实测 |
| --- | --- |
| 并发：[reports/risk-concurrency.md](reports/risk-concurrency.md) | `python apitest/check_async_grading.py`：同一提交 20 并发只建一条任务，重复消息不重复生效；C1 通过。 |
| 事务：[reports/risk-transaction.md](reports/risk-transaction.md) | 同一命令注入第二条任务写入失败：返回 503，整批任务和发件箱标记回滚，原提交仍为 pending；B3 通过。异步检查合计 57/57。 |
| 权限：[reports/risk-authz.md](reports/risk-authz.md) | `python apitest/probe_security_precheck.py --output .review/security-probe.json`：本班讲义下载 200、跨班 404 且无正文，学生写工具被拒；41/41。任务越权按合同为 403。 |

原始结果与源码摘要见 [reports/project-evidence/validation-runs.json](reports/project-evidence/validation-runs.json)。离线替身验证不代表外部部署、真实模型质量或生产容量。

## 5. 门禁与演示

准入流程为 **AI 初稿 → AI 自审 → 脚本检查 → 人工确认 → 交叉评审 → main**。`main` 要求一次正式批准和 `make check`、`make check-security`、`build-and-scan` 三项成功，管理员同样受限。PR #3 在批准后合入 `8964200`，主干 CI `44045260010` 三项通过；本次完整普通门禁 **43/43、退出 0**，见 [reports/project-validation.md](reports/project-validation.md)。Linux 执行 `make check`、`make check-security`；Windows 等价命令与准备步骤见 [reports/reproduce-checks.md](reports/reproduce-checks.md)。本次未重新执行联网依赖审计，安全结论引用注明版本的 CI；OS HIGH 仍有书面例外，不能表述为镜像零漏洞。

拦截证据为 [reports/gate-red-green.md](reports/gate-red-green.md) 和 [reports/project-gate.md](reports/project-gate.md)：PR #5 镜像检查失败的 run `44022376165`，经 `3da68c5` 修复后 run `44042306967` 成功；当前保护状态见 [reports/project-evidence/github-snapshot.json](reports/project-evidence/github-snapshot.json)。

**部署地址待教师提供，外部环境尚未验收。** 地址到位后按 [reports/live-demo.md](reports/live-demo.md) 当场操作：登录 → 教师触发 AI 初批返回 **202** 与任务编号 → 查询 `pending/running/succeeded` → 换班级账号下载同一讲义返回 **404**。先确认有权账号下载为 200。学生交作业本身返回 200；`dead/skipped` 不算成功演示。本机启动证据不替代此项。

## 6. 复盘

本次评审中返工链最长的一次是镜像门禁：先发现空报告与例外范围过宽，修好判定后，远端扫描又暴露两份镜像的 ncurses-bin 风险，继续做运行层缓解和实际镜像核验才转绿。过程见 [reports/review-04.md](reports/review-04.md)、[reports/review-06.md](reports/review-06.md)。下次先把“缺报告、错误结构、未登记软件包、例外过期”四类反例纳入门禁，再收集绿灯；已有反例常驻回归。外部环境到位后，合入报告前还须补部署地址、版本和四步真实结果。
