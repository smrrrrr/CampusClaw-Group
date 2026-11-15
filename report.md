# CampusClaw 课程交付总报告

本文件只写结论与索引，不复制日志与原始输出；全部证据在 `reports/`。

- 当前交付提交：`61184b8`（含第10课收口口径同步改动）
- 最近更新：2026-11-15（UTC）

## 一、总体结论

| 课程 | 结论 | 详细记录 |
| --- | --- | --- |
| 第9课 安全修复 | 交叉评审完成；评审发现已修复并归档 | [评审](reports/review-03.md)、[安全证据](reports/security-evidence/) |
| 第10课 测试交付与运行验证 | 本机工程实施与运行验证已收口；真人、远端与线上环节未完成 | [总览](reports/lesson10-delivery.md)、[演示清单](reports/demo-checklist.md) |

第10课当前门禁：`make check` **35/35 PASS**；`make check-security` **RED**（仅 Next.js 14.2.15 版本范围计数，4 条 critical 在当前代码与 Linux standalone 部署下均不可触发，论证见 [next-risk-applicability.md](reports/next-risk-applicability.md)）。后端与 MCP 镜像均已达成 0 源码（`.py = 0`，全量 `.pyc`）；新目录从干净 clone 启动成功；真实 RabbitMQ 异步复现 14 项 PASS；检索热点优化后瓶颈档（并发 10）P95 **−23.8%**（并发 3 P95 +7.6%）。在此状态下不宣称交付完成。

## 二、第10课证据索引

| 判据 | 报告 |
| --- | --- |
| 第10课交付总览 | [lesson10-delivery.md](reports/lesson10-delivery.md) |
| 独立演示清单 | [demo-checklist.md](reports/demo-checklist.md) |
| 测试收口与先红后绿 | [gate-red-green.md](reports/gate-red-green.md) |
| 从零启动与 H5 等价链路 | [boot-reproduce.md](reports/boot-reproduce.md) |
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
3. CI 远端运行、镜像 digest、main 保护、线上实例反查。
4. 手机浏览器实机验证与真实模型语义抽查。
5. 场景矩阵 170 条无匹配断言（含 17 条 P0）及在线用例跨进程 SQLite 并发冲突收口。
