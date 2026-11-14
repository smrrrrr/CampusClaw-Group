# CampusClaw 课程交付总报告

本文件只写结论与索引，不复制日志与原始输出；全部证据在 `reports/`。

- 当前交付提交：`fe227a1`（第10课改动未提交，工作区 dirty）
- 最近更新：2026-11-14（UTC）

## 一、总体结论

| 课程 | 结论 | 详细记录 |
| --- | --- | --- |
| 第9课 安全修复 | 交叉评审完成；评审发现已修复并归档 | [评审](reports/review-03.md)、[安全证据](reports/security-evidence/) |
| 第10课 测试交付与运行验证 | 工程实施与运行验证进行中；真人、远端与线上环节未完成 | [总览](reports/lesson10-delivery.md) |

第10课当前门禁：`make check` **33/33 PASS**；`make check-security` **RED**（npm 未登记漏洞含 critical、pip 未取得可解析响应、密钥扫描范围不完整）。新目录从干净 clone 启动成功；真实 RabbitMQ 异步复现 14 项 PASS；检索接口压测已完成，但索引改进在 API 级 **未产生收益**（P95 +0.4%）。在此状态下不宣称交付完成。

## 二、第10课证据索引

| 判据 | 报告 |
| --- | --- |
| 测试收口与先红后绿 | [gate-red-green.md](reports/gate-red-green.md) |
| 从零启动与 H5 等价链路 | [boot-reproduce.md](reports/boot-reproduce.md) |
| 流水线与镜像追溯 | [pipeline.md](reports/pipeline.md) |
| 观测、面板与告警 | [observe-alert.md](reports/observe-alert.md) |
| 压测与改进 | [bench.md](reports/bench.md) |
| 真实用户反馈 | [feedback.md](reports/feedback.md) |
| 命令盘点 | [command-inventory.md](reports/command-inventory.md) |
| 场景矩阵 | [scenario-matrix.md](reports/scenario-matrix.md) |
| 索引迁移 | [migration/README.md](reports/lesson-10/20261114T072100Z-apply/migration/README.md) |
| 原始证据 | `reports/lesson-10/20261114T072100Z-apply/` |

## 三、未完成项

1. 安全门禁未清零（高危 1 critical + 2 high；pip 未判级）。
2. 3 名真实用户、换人双跑、另一人新目录启动、组员本人签名。
3. CI 远端运行、镜像 digest、main 保护、线上实例反查。
4. 手机浏览器实机验证与真实模型语义抽查。
5. 场景矩阵空项与压测满档基线。
