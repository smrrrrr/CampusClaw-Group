# CampusClaw 课程交付总报告

本文件只写结论与索引，不复制日志与原始输出；全部证据在 `reports/`。

- 当前交付提交：分支 `deps/upgrade-a-b` 最新提交（含第10课收口与场景逐条复核改动；具体 SHA 以 `git log -1` 为准）
- 最近更新：2026-11-16（UTC）

## 一、总体结论

| 课程 | 结论 | 详细记录 |
| --- | --- | --- |
| 第9课 安全修复 | 交叉评审完成；评审发现已修复并归档 | [评审](reports/review-03.md)、[安全证据](reports/security-evidence/) |
| 第10课 测试交付与运行验证 | 既有验证见历史记录；Next 15 升级本地双门禁绿、远端 `check`/`security`/`images` 三 job 全绿（OS 层 HIGH 走书面例外，CRITICAL 零）；真人、required checks 与线上环节未完成 | [总览](reports/lesson10-delivery.md)、[演示清单](reports/demo-checklist.md) |

第10课 Next 15 升级验证（2026-11-16 UTC，`next@15.5.28`，分支 `deps/upgrade-a-b`，PR #3）：本地 `make check` **41/41 PASS，exit 0**；`make check-security` 在将本地库只读副本放到 `data/current/` 后 **PASS，exit 0**（npm `critical=0/high=0/low=4` 已登记、`unregistered_vulns=[]`、backend/mcp 各 0 漏洞包），未改门禁判据或注入账号。远端 run `43877256576`：`check` pass、`security` pass（workflow 内写入临时库四个演示身份后转绿）、`images` 已修好流程并处置系统层漏洞（`trivy-action` 上游连续删 tag，最终按 commit 固定到 `v0.36.0`；补构建前一次性 `.env`；backend 与 mcp-server 运行层加 `apt-get upgrade` 修掉有补丁的 zlib1g 两条 CVE；无修复版本的 11 个 CVE 登记书面例外，复查日期 2026-12-15）。run `43885117587`（HEAD `3074cae`）三 job 全绿：backend 47、mcp-tools 47、frontend 0 条 HIGH，CRITICAL 0，门禁由 `scripts/trivy_os_gate.py` 判定（CRITICAL 一票否决，HIGH 未登记或例外过期即失败）。旧 Next 14.2.15 的 critical 适用性论证已由升级替代，见 [next-risk-applicability.md](reports/next-risk-applicability.md)。本轮隔离安装/构建与前端镜像 `.py=0` 通过；HTTP 冒烟 26/29；headless Chrome 在独立栈完成登录、首次改密、刷新恢复、切班与登出 6/6 页面检查，Markdown/KaTeX 预览、学生篡改 `class_id` 返回 403 均通过。**变更清单 14/14 已按本轮实测勾选**；学生按 ID 读取他班材料为防枚举 404（`materials.py` 注释明示，规约未规定 by-ID 状态码）。实际证据见 [升级批次](reports/lesson-10/20261116T124118Z-next15/README.md) 与 [浏览器/门禁批次](reports/lesson-10/20261116T215000Z-browser/README.md)；交接数据包 `handover-packs/2026-11-16-next15.zip`（含库、`.env`、上传材料，**仓库外私下传递**）与 [交接说明](docs/handover-2026-11-16-next15.md)、[数据说明](docs/handover-2026-11-16-next15-data.md) 同步。

以下为升级前既有第10课记录，历史远端结果未在本轮刷新：backend、mcp-tools、frontend 三镜像均已达成 0 源码（`.py = 0`，OCI revision 可反查提交），并以当前提交重建七服务栈复验；当前提交经空目录独立项目/端口启动成功，本机 registry push/pull digest 与临时库备份/上一 tag 回滚演练通过（均不代表远端或换机）；远端 Draft PR #3 的 run `43826707775` 已实跑：`check` 通过、`security` RED、`images` 跳过，不构成受控绿版本；隔离环境真实 RabbitMQ 异步复现 15 项 PASS；在线用例在 compose 网络内 **24 passed / 1 skipped / 0 failed**（唯一跳过为无模型 Key 时的工具审计）；检索热点优化后瓶颈档（并发 10）P95 **−23.8%**（并发 3 P95 +7.6%）。场景矩阵 505 条已逐条判定：人工复核确认 185、部分覆盖 22、断言名候选 77、人工语义别名 106、关键词别名 89、N/A 23（附理由）、已知缺口 3；待补断言 0、弱候选 0、仅文件级 0。在此状态下不宣称交付完成。

## 二、第10课证据索引

| 判据 | 报告 |
| --- | --- |
| 第10课交付总览 | [lesson10-delivery.md](reports/lesson10-delivery.md) |
| 独立演示清单 | [demo-checklist.md](reports/demo-checklist.md) |
| 测试收口与先红后绿 | [gate-red-green.md](reports/gate-red-green.md) |
| 从零启动与 H5 等价链路 | [boot-reproduce.md](reports/boot-reproduce.md) |
| 换目录、registry 与备份回滚演练 | [release-rollback.md](reports/release-rollback.md) |
| 流水线与镜像追溯 | [pipeline.md](reports/pipeline.md) |
| 观测、面板与告警 | [observe-alert.md](reports/observe-alert.md) |
| 压测与改进 | [bench.md](reports/bench.md) |
| 真实用户反馈 | [feedback.md](reports/feedback.md) |
| 命令盘点 | [command-inventory.md](reports/command-inventory.md) |
| 交接说明（Next 15 升级） | [handover-2026-11-16-next15.md](docs/handover-2026-11-16-next15.md) |
| 交接数据包（私有，不入库） | [数据说明](docs/handover-2026-11-16-next15-data.md)（实体为 `handover-packs/2026-11-16-next15.zip`） |
| 场景矩阵与逐条映射 | [scenario-matrix.md](reports/scenario-matrix.md)、[scenario-coverage.md](reports/scenario-coverage.md) |
| 镜像 0 源码方案与验证 | [no-source-plan.md](reports/no-source-plan.md) |
| 在线用例执行记录 | [online-cases.md](reports/online-cases.md) |
| 安全适用性与技术栈等价 | [next-risk-applicability.md](reports/next-risk-applicability.md)、[stack-equivalence.md](reports/stack-equivalence.md)、[course-decisions-2026-11-14.md](reports/course-decisions-2026-11-14.md) |
| 索引迁移 | [migration/README.md](reports/lesson-10/20261114T072100Z-apply/migration/README.md) |
| Next 15 升级批次 | [验证与阻塞记录](reports/lesson-10/20261116T124118Z-next15/README.md) |
| 原始证据 | `reports/lesson-10/20261114T072100Z-apply/` |

## 三、未完成项

1. 本次 `make check-security` exit 2 / BLOCKED：只读核查库缺四个演示身份；不向真实库补写账号。Next 的 npm critical/high 已按本轮审计归零，4 个 low 已登记。后端镜像 OS 层 Trivy HIGH=51 仍是独立维护项。Next 15 运行时验收未完：跨班资料实际 404 与 tasks 要求 403 不符；直接 rewrite 在 gzip 下合并短 SSE（14/15 对照一致，identity 下均正常）；浏览器服务不可用，页面守卫与实际公式渲染待验。
2. 3 名真实用户、换人双跑、另一人新目录启动、组员本人签名与真实负责人告警接收。
3. CI 已在 GitHub Actions 实跑但为红（run `43826707775`：`check` 绿、`security` RED、`images` 跳过）；独立分支故障重放已完成（run `43828237591`：`make check` 失败、`images` 跳过）。受控绿版本、远端镜像仓库 digest、main 保护（required check 未配置）、线上实例反查仍缺（本机 registry digest 与回滚演练已完成，不解除该项）。
4. 手机浏览器实机验证与真实模型语义抽查。
5. 场景矩阵 505 条已逐条判定：待补断言 **0**、P0 缺口 0、弱候选 **0**、仅文件级 **0**；人工复核确认 185 条、部分覆盖 22 条（备注写明未断言部分）、N/A 23 条（附理由）、已知缺口 3 条（工具说明注入句式；教师端按班级查看 AI 提问历史；AI 解答加入错题本）。部分覆盖与已知缺口不得计入「场景全覆盖」。在线用例已在 compose 网络内复跑至 24 passed / 1 skipped / 0 failed，唯一跳过为未配置模型 Key 时的工具审计。
