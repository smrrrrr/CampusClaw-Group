# 第10课交付总览（测试、交付与运行验证）

- 变更：`openspec/changes/2026-11-12-lesson10-test-delivery-and-runtime-verification`
- 交付提交：`fe227a1`（工作区含本课未提交改动，镜像与证据均标注 dirty）
- 批次：`reports/lesson-10/20261114T072100Z-apply/`
- 更新：2026-11-14（UTC）
- 性质：工程实施与运行验证记录；**不是**组员本人签名，也不代表课程验收完成

## 一、结论

| 维度 | 结论 | 依据 |
| --- | --- | --- |
| 全量门禁 `make check` | **PASS**，32/32 子项 | `gates/check-final.txt`、`gates/check-meta-final.json` |
| 安全门禁 `make check-security` | **RED** | 7 个 npm 漏洞未登记（含 1 critical）；pip 审计本次未取得可解析响应；密钥扫描范围不完整 |
| 七服务启动 | **PASS**，全部 Up，关键服务 healthy | `boot/compose-build.txt`、`boot/compose-ps.txt` |
| 异步链路（学生 200 → 教师 202 → 三态） | **PASS**（未配模型，终态 `dead` 符合预期） | `boot/smoke.json` |
| 跨班资料隔离 | **PASS**（本班 200、跨班 404） | `boot/smoke.json` |
| 观测采集与面板 | **PASS**：采集器、面板 4 图、真实告警 Firing→送达 15 秒 | `observe-alert.md` |
| 三接口压测 | 查询接口 4 档曲线；接收/检索未压测 | `bench.md` |
| 索引改进 | **PASS（SQL 级）**：覆盖索引，P95 降 22.62% | `migration/index-bench.json` |
| 3 名真实用户 | **BLOCKED**（无真人） | `feedback.md` |

## 二、课程条目对照

| 课程条目 | 状态 | 证据/说明 |
| --- | --- | --- |
| 总要求：同一版本可追溯 | 部分 | 门禁、镜像、报告均记录同一提交；CI 未在远端运行 |
| 判定-可重复 | 部分 | 同一命令本机重复执行一致；**换人双跑未完成** |
| 判定-环境完整 | 部分 | 本目录可启动；**换目录/换机未完成** |
| 判定-版本追溯 | 部分 | 镜像带 OCI revision 与提交标签；**无线上实例**，反查链缺最后一环 |
| 判定-状态可见 | 部分 | 采集器/面板/窗口查询完成；真实告警待演练 |
| 1.1 命令盘点 | PASS | `reports/command-inventory.md`（46 行，逐命令时间来源） |
| 1.2 场景矩阵 | 部分 | `reports/scenario-matrix.md`：505 个 Scenario，70 断言名候选、97 文件级候选、338 空项 |
| 1.3 四项技能 | 部分 | 引导/终评/错题/跨班有资产；新增反例见 `check_lesson10_ops.py` 与场景矩阵 |
| 1.4 分工 | BLOCKED | 需真实姓名与交叉验收人 |
| 2.1 用例落库 | PASS（本课新增检查已入 `make check`） | `apitest/check_lesson10_ops.py` 9/9 |
| 2.2 聚合门禁 | PASS（本机 32/32） | CI 未运行 |
| 2.3 先红后绿 | 部分：`make check` 红绿齐全；`make check-security` 安全反例未重做 | 故障 `10af3b0` → 修复 `f7cddcb`，见 `gate-red-green.md` |
| 2.4 主干保护 | BLOCKED | 无远端配置权限 |
| 3.1 多阶段镜像 | 部分 | 后端/MCP 已分构建/运行层；Python 必要运行源码仍在，字面“无源码”未获确认 |
| 3.2 Compose 等价 | PASS（等价说明） | 七服务 + SQLite 读就绪；未迁 MySQL/Qdrant |
| 3.3 换目录/机器 | 未执行 | 需人从新目录复现 |
| 3.4 镜像编号 | 部分 | 镜像标签与 OCI revision 已接入 Compose；远端 digest 未产生 |
| 4.1 自动构建 | 部分 | `.github/workflows/lesson10.yml` 完成，未在远端运行 |
| 4.2 推送反查 | BLOCKED | 未推送、无 CI 编号与 digest |
| 4.3 扩迁缩 | PASS（N/A 说明） | 仅索引变更，无行数据迁移；见 `migration/README.md` |
| 4.4 就绪探针 | 部分 | DB 不可读 503 有既有检查；运行期摘流量未实现 |
| 5.1 指标口径 | PASS（按已记录事件） | 引导/批改有来源；错题讲解明确“未接入” |
| 5.2 三张图 | PASS（配置） | Grafana 4 panel（调用量/失败率/P95/队列） |
| 5.3 告警规则 | PASS（配置） | `deploy/observability/alerts.yml` |
| 5.4 真触发 | PASS（测试接收器） | Pending 07:43:39Z → Firing 07:48:39Z → 送达 07:48:54Z → Resolved 07:53:24Z；真实负责人未落实 |
| 6.1 H5 四步 | 部分 | 同 API 角色分步已验；**手机浏览器未验** |
| 6.2 三名用户 | BLOCKED | 无真人反馈 |
| 6.3 压测 | 部分 | 脚本完成；满档曲线未跑 |
| 6.4 改进复测 | 部分 | 索引改进有计划证据；**同参前后复测未完成** |
| 7.1 门禁核查 | 部分 | 本机全绿；安全门禁 RED 未消除 |
| 7.2 可复现核查 | 部分 | 本目录启动成功；源码字面冲突未确认 |
| 7.3 流水线核查 | BLOCKED | 无远端运行 |
| 7.4 观测核查 | 部分 | 面板/窗口可用；真实通知未送达 |
| 7.5 验证核查 | 部分 | 见 6.3/6.4/6.2 |
| 7.6 Harness 规则 | PASS | `AGENTS.md` 七类责任表 + `.cursor/rules` 入口 |
| 7.7 交付交评 | 部分 | 三份历史评审保留；本课独立评审待补 |

## 三、必交报告索引

| 报告 | 状态 |
| --- | --- |
| `reports/gate-red-green.md` | 追加第10课章节 |
| `reports/boot-reproduce.md` | 本批次启动与链路证据 |
| `reports/pipeline.md` | CI 设计、未运行说明、反查缺口 |
| `reports/observe-alert.md` | 指标口径、面板、告警配置与演练 |
| `reports/bench.md` | 脚本与历史基线；本课两轮待补 |
| `reports/feedback.md` | 阻塞说明 |
| 根 `report.md` | 结论索引 |

## 四、未完成与阻塞

1. 安全门禁：npm 7 个未登记漏洞（`next` critical 等），pip 审计本次网络失败，密钥扫描因无容器日志范围不完整。未放宽判据。
2. 真人环节：3 名真实用户、换人双跑、另一人新目录启动、组员签名。
3. 远端环节：CI 运行、镜像仓库 digest、main 保护、线上实例反查。
4. 运行期摘流量与真实模型语义：本轮未实现/未验证。
5. 场景矩阵 338 个空项：已列出，未逐条补例。
