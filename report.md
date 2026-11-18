# 项目报告 · CampusClaw

仓库 [smrrrrr/CampusClaw-Group](https://github.com/smrrrrr/CampusClaw-Group)，业务基线 `main@8964200`，核查日期 2026-11-17。

**演示视频下载地址**：待录制并上传百度网盘或北大网盘后填写。

**成员与分工**。Jackler / hexzun1 上线智能命题与 MCP，建立健康检查和 CI，复核安全修复，完成检索压测优化、依赖和镜像升级（`13c1cd2`、`4b005e1`、PR #3）。
Grey_Wolf_King 新增批改、学情与错题，修复跨班访问和 XSS，加入七列审计、工具授权与 CSRF 防御，补安全反例和交接（`e10c81b`、`4cfaa15`、`efbfb67`）。
**smrrrrr**：同步第 2–5 课个人仓库内容，上线智能备课、讲义发布和作业异步初批，完成安全预检、Windows 部署复验及镜像门禁修复，最后人工进行项目业务语义修正并完成本地验收。[reports/contributions.md](reports/contributions.md)

## 1. 一句话介绍

CampusClaw 面向中学教师和学生，把讲义导入、备课、命题、作业初批与答疑连成流程，减少教师重复整理和批改工作，让学生能用本班本学科资料学习，教师保留发布和最终改分权。[README.md](README.md)

## 2. AI 写了什么

代码与规约由 AI 起草，开发与自审使用 Codex，并经脚本和组员复核。其他 AI 产出如下。

- **规则、用例**：`AGENTS.md` 写明规则入口和七类核查。`apitest/check_async_grading.py` 覆盖幂等和回滚，`apitest/probe_security_precheck.py` 覆盖跨班拒绝。
- **评审与三查**：`reports/review-04.md`、`reports/review-05.md`、`reports/review-06.md` 归档发现、判据和修复。并发、事务、权限各有一份复跑记录，见第 4 节。
- **压测与验证编排**：`scripts/lesson10_api_bench.py` 编排同参复测，`reports/bench.md` 记录 P95 和吞吐。`Makefile` 编排普通与安全检查，`.github/workflows/lesson10.yml` 接入 CI。
- **交付文档**：`README.md` 说明启动和教师验收入口，`reports/demo-recording.md` 编排录屏步骤。完整产出索引见 [reports/contributions.md](reports/contributions.md)。

七类核查问题、步骤和判据详见 [AGENTS.md](AGENTS.md) 的“七类代码核查责任”。

| 类别 | 核查问题与手段 |
| --- | --- |
| 接口入口 | 参数、角色、状态码是否正确；脚本跑合法、未登录及越权请求。 |
| 业务逻辑 | 幂等与教师终评是否成立；AI 对照规约，脚本验状态和旧结果拒写。 |
| 数据库 | 失败是否回滚、迁移是否保留数据；脚本做故障注入和重复迁移。 |
| 公共函数 | 空值、边界、复用是否正确；单元断言、分层检查。 |
| 错误处理 | 超时、重投是否可恢复且无泄密；脚本注入模型、代理与数据库故障。 |
| 安全 | 跨班、工具授权、密钥与依赖是否受控；安全探针、双门禁、镜像扫描。 |
| 性能 | 请求是否等待模型、瓶颈在哪；20 并发断言与独立同参压测。 |

## 3. 审核记录

| 记录 | 发现、判据与结果 |
| --- | --- |
| [reports/review-04.md](reports/review-04.md) | 合成扫描反例发现空报告及同 CVE 未登记包被放行；要求无效报告退出 2、未登记 HIGH 退出 1。修复 `cc5b0fc`，当时 19/25 转 25/25，本次扩展回归 31/31。 |
| [reports/review-05.md](reports/review-05.md) | AI 源码核查配合隔离探针发现写工具上下文缺失、权限分类丢失；学生必须被拒且不得写分。修复 `97ba0f5`；本次安全探针 41/41，0 红项。 |
| [reports/review-06.md](reports/review-06.md) | 远端镜像扫描拦下两份镜像的 ncurses-bin HIGH；保留原始告警，移除不用的 infocmp，并核验实际镜像。修复 `3da68c5` 后 CI 转绿，期限与版本受例外表约束。 |

在 PR #3 复核并正式批准，发现固化为 `apitest/check_os_vuln_gate.py` 中的空报告、同 CVE 不同软件包和缺报告反例。[reports/peer-review.md](reports/peer-review.md)

## 4. 高风险三查

本次在 Windows、临时 SQLite、假模型/MCP 环境复跑，命令均从仓库根执行，环境准备见 [reports/reproduce-checks.md](reports/reproduce-checks.md)。

| 检查与记录 | 手段、判据、实测 |
| --- | --- |
| 并发：[reports/risk-concurrency.md](reports/risk-concurrency.md) | `python apitest/check_async_grading.py`：同一提交 20 并发只建一条任务，重复消息不重复生效；C1 通过。 |
| 事务：[reports/risk-transaction.md](reports/risk-transaction.md) | 同一命令注入第二条任务写入失败：返回 503，整批任务和发件箱标记回滚，原提交仍为 pending；B3 通过。异步检查合计 57/57。 |
| 权限：[reports/risk-authz.md](reports/risk-authz.md) | `python apitest/probe_security_precheck.py --output .review/security-probe.json`：本班讲义下载 200、跨班 404 且无正文，学生写工具被拒；41/41。任务越权按合同为 403。 |

本次使用离线替身和合成数据，实测范围、时间和源码摘要见 [reports/project-evidence/validation-runs.json](reports/project-evidence/validation-runs.json)。

## 5. 门禁与演示

准入流程为 **AI 初稿 → AI 自审 → 脚本检查 → 人工确认 → 交叉评审 → main**。`main` 要求一次正式批准和普通、安全、镜像三项 CI 通过。PR #3 正式批准后合入 `8964200`，主干 CI `44045260010` 三项通过。完整普通门禁实测 **43/43、退出 0**。安全及镜像结果以该 CI 为准，OS HIGH 按登记例外判断。[reports/project-validation.md](reports/project-validation.md)

先红后绿证据为 PR #5 镜像检查失败的 run `44022376165`，经 `3da68c5` 修复后 run `44042306967` 成功。[reports/gate-red-green.md](reports/gate-red-green.md) · [reports/project-gate.md](reports/project-gate.md)

**录屏待录制**。介绍项目后，从仓库根依次运行第 4 节两条命令并展示结果，再跑 `make check`（Windows 为 `python scripts/check.py`）。随后登录演示学生提交、教师触发 AI 初批并查看结果。录屏总长 3 分钟以内，上传后把下载地址填到报告开头，命令准备及演示细节见 [reports/demo-recording.md](reports/demo-recording.md)。

## 6. 复盘

代价最大的一次返工是镜像门禁。旧判定把空报告当零漏洞、按 CVE 放宽例外。修好后，CI 又发现两份运行镜像含受影响的程序，因而需要修改两份 Dockerfile、重建并扫描三份镜像，再按镜像 ID 核验缓解。下次在首轮 CI 前就加上缺报告、错误结构、未登记包和例外过期四类反例。[reports/review-04.md](reports/review-04.md) · [reports/review-06.md](reports/review-06.md)
