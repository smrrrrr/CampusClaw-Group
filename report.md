# CampusClaw 课程交付总报告

本文件只写结论与索引，不复制日志与原始输出；全部证据在 `reports/`。

- 当前交付提交：分支 `deps/upgrade-a-b` 最新提交（含第10课收口与场景逐条复核改动；具体 SHA 以 `git log -1` 为准）
- 最近更新：2026-11-16（UTC）

## 一、总体结论

| 课程 | 结论 | 详细记录 |
| --- | --- | --- |
| 第9课 安全修复 | 交叉评审完成；评审发现已修复并归档 | [评审](reports/review-03.md)、[安全证据](reports/security-evidence/) |
| 第10课 测试交付与运行验证 | 本机工程实施与运行验证已收口；真人、远端与线上环节未完成 | [总览](reports/lesson10-delivery.md)、[演示清单](reports/demo-checklist.md) |

第10课当前门禁：`make check` **41/41 PASS**（本机与 GitHub Actions 远端 Ubuntu 均通过）；`make check-security` **RED**（Next.js 14.2.15 critical + 5 个未登记 npm 包：katex、micromark-extension-math、next、rehype-katex、remark-math；容器账本仍 blocked，CI 临时库无四个种子身份；Next 4 条 critical 的适用性论证见 [next-risk-applicability.md](reports/next-risk-applicability.md)）。backend、mcp-tools、frontend 三镜像均已达成 0 源码（`.py = 0`，OCI revision 可反查提交），并以当前提交重建七服务栈复验；当前提交经空目录独立项目/端口启动成功，本机 registry push/pull digest 与临时库备份/上一 tag 回滚演练通过（均不代表远端或换机）；远端 Draft PR #3 的 run `43826707775` 已实跑：`check` 通过、`security` RED、`images` 跳过，不构成受控绿版本；隔离环境真实 RabbitMQ 异步复现 15 项 PASS；在线用例在 compose 网络内 **24 passed / 1 skipped / 0 failed**（唯一跳过为无模型 Key 时的工具审计）；检索热点优化后瓶颈档（并发 10）P95 **−23.8%**（并发 3 P95 +7.6%）。场景矩阵 505 条已逐条判定：人工复核确认 185、部分覆盖 22、断言名候选 77、人工语义别名 106、关键词别名 89、N/A 23（附理由）、已知缺口 3；待补断言 0、弱候选 0、仅文件级 0。在此状态下不宣称交付完成。

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
| 场景矩阵与逐条映射 | [scenario-matrix.md](reports/scenario-matrix.md)、[scenario-coverage.md](reports/scenario-coverage.md) |
| 镜像 0 源码方案与验证 | [no-source-plan.md](reports/no-source-plan.md) |
| 在线用例执行记录 | [online-cases.md](reports/online-cases.md) |
| 安全适用性与技术栈等价 | [next-risk-applicability.md](reports/next-risk-applicability.md)、[stack-equivalence.md](reports/stack-equivalence.md)、[course-decisions-2026-11-14.md](reports/course-decisions-2026-11-14.md) |
| 索引迁移 | [migration/README.md](reports/lesson-10/20261114T072100Z-apply/migration/README.md) |
| 原始证据 | `reports/lesson-10/20261114T072100Z-apply/` |

## 三、未完成项

1. 安全门禁 `make check-security` 仍为 RED（Next 4 条 critical 不适用论证待课程书面认可；后端镜像 OS 层 Trivy HIGH=51 另立维护任务）。
2. 3 名真实用户、换人双跑、另一人新目录启动、组员本人签名与真实负责人告警接收。
3. CI 已在 GitHub Actions 实跑但为红（run `43826707775`：`check` 绿、`security` RED、`images` 跳过）；受控绿版本、远端镜像仓库 digest、main 保护、线上实例反查仍缺（本机 registry digest 与回滚演练已完成，不解除该项）。
4. 手机浏览器实机验证与真实模型语义抽查。
5. 场景矩阵 505 条已逐条判定：待补断言 **0**、P0 缺口 0、弱候选 **0**、仅文件级 **0**；人工复核确认 185 条、部分覆盖 22 条（备注写明未断言部分）、N/A 23 条（附理由）、已知缺口 3 条（工具说明注入句式；教师端按班级查看 AI 提问历史；AI 解答加入错题本）。部分覆盖与已知缺口不得计入「场景全覆盖」。在线用例已在 compose 网络内复跑至 24 passed / 1 skipped / 0 failed，唯一跳过为未配置模型 Key 时的工具审计。
