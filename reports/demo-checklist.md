# 第10课独立演示清单（任务 10.5 备料）

- 版本：2026-11-14，分支 `deps/upgrade-a-b`
- 用途：交给**另一名组员**按本清单独立演示并记录；AI 与实施者不得代跑代签
- 状态：**备料完成，演示未执行**。任何一项未由本人完成，不得把对应课程任务标为完成

## 一、四项判定（须换人执行）

| 判定 | 演示人要做的事 | 通过信号 | 证据写回 |
| --- | --- | --- | --- |
| J1 换人双跑一致 | 同一提交、同一锁文件、同一夹具与参数，运行 `make check` 与 `make check-security` 各两次 | 断言数、退出码、关键状态一致；时间与随机 ID 不同需说明 | 本文件表下追加，或 `reports/boot-reproduce.md` |
| J2 README 新目录启动 | 新建空目录克隆，按 README 准备 `.env`、构建、`docker compose up -d` | 七服务就绪，`/health` 200，页面 200；不得复用已有数据目录 | `reports/boot-reproduce.md`「换机/换目录」节 |
| J3 线上提交反查 | 从线上 URL 找到实例 → 镜像 digest → OCI `revision` 标签 → CI run → 提交 | 五步可追溯且互相一致 | `reports/pipeline.md` |
| J4 60 秒窗口报数 | 指定任意 UTC 60 秒窗口，调用采集器窗口模式 | 60 秒内返回三技能调用量与失败率；空分母显示「无样本」 | `reports/observe-alert.md` |

## 二、五个当场动作

| 动作 | 命令/操作 | 预期 | 当前本机状态 |
| --- | --- | --- | --- |
| D1 改坏被拦 | 临时改坏一个断言或权限判断，跑门禁，再恢复 | 先红后绿，两次输出都保留 | 已完成（`reports/gate-red-green.md`） |
| D2 一键启动 | 新目录 `docker compose up -d` | 七服务 Up，核心 healthy | 本机通过；**缺新机** |
| D3 面板指三技能 | 打开 Grafana 三面板，核对技能标签与失败率 | 三技能分线；空分母显示无样本 | 本机可用；**第三图等价待课程确认** |
| D4 异步链路 | 学生提交 → 202/task_ids → 轮询三态 → 他人不可见 | 真实代理消费，跨班 404 | 真实代理 14 项 PASS；**缺手机** |
| D5 压测前后对比 | 跑 `scripts/lesson10_api_bench.py` 并对旧版同参 | 瓶颈档 P95 降 ≥10%，吞吐不降、错误率不增 | 已完成：并发 10 P95 −23.8%（`reports/bench.md`） |

补充现场核验项（课程答复新增）：
- **镜像 0 源码断言（任务 6.1）**：在运行中的 `backend` 与 `mcp-tools` 容器内执行 `find / -name '*.py' -not -path '/proc/*' | wc -l`，预期均为 `0`（证据见 `reports/no-source-plan.md`）。
- **在线 cases 复跑（任务 3.3）**：本机同宿主直连（临时库、后端与 pytest 同文件系统）第 5 轮为 `22 passed / 3 skipped / 0 failed`；3 项 MCP 用例因硬编码 `http://mcp-tools:8090`（仅 compose 网络可解析）跳过，明细与复现步骤见 `reports/online-cases.md`。

## 三、六份必交报告核对

| 报告 | 路径 | 当前状态 |
| --- | --- | --- |
| 交付与对照 | `reports/lesson10-delivery.md` | 已更新最新状态 |
| 从零启动 | `reports/boot-reproduce.md` | 本机完成；换机待做 |
| 流水线 | `reports/pipeline.md` | 文件齐全；远端 run 待做 |
| 观测与告警 | `reports/observe-alert.md` | 四阶段齐全；接收授权待确认 |
| 压测 | `reports/bench.md` | 已完成两轮对比 |
| 用户反馈 | `reports/feedback.md` | **BLOCKED**，无真实用户 |

另有根 `report.md`、`reports/scenario-coverage.md`（505 条场景逐条映射）、`reports/no-source-plan.md`（镜像 0 源码方案与实测）、`reports/online-cases.md`（在线用例环境与非通过明细）及 `reports/next-risk-applicability.md`。

## 四、3 份审核 / 3 人反馈 / 高风险三查

| 项 | 文件 | 状态 |
| --- | --- | --- |
| 审核 1 | `reports/review-01.md` | 已追加第10课复核；人工签名待填 |
| 审核 2 | `reports/review-02.md` | 同上 |
| 审核 3 | `reports/review-03.md` | 同上，评审人 phj 本人签名待填 |
| 反馈 1–3 | `reports/feedback.md` | **BLOCKED**，不得用合成账号替代 |
| 高风险：越权 | `reports/risk-authz.md` | 已有检查 |
| 高风险：事务 | `reports/risk-transaction.md` | 已有检查 |
| 高风险：并发 | `reports/risk-concurrency.md` | 已有检查与压测 |

## 五、展示前必须处理

1. **安全门禁 RED**：Next 4 条 critical 已有不适用论证（`reports/next-risk-applicability.md`），但课程是否接受尚未答复；未答复前不得说「高危 0 条」。
2. **等价未认可**：第三图 P95 是否等价于完整接口耗时、MySQL/Qdrant/Golang 是否强制，均未获课程确认。
3. **返回码差异**：演示中若出现与本文预期不同的状态码，先记入本节「待修」，不得现场改口径。
4. **签名**：三份审核与反馈表必须由本人填写；AI 生成的追加内容不能替代签名。

## 五之二、现场核验边界（避免预期偏差）

以下为本机已确认的边界，演示时须按实际行为记录，不得按理想口径改写：

1. **告警规则与送达**：规则见 `deploy/observability/alerts.yml`（错误率>1% 且样本≥20 持续 5 分钟）；本机测试接收器已验证 Pending→Firing→15 秒送达→Resolved，但**真实负责人接收授权未落实**，演示若用测试接收器须注明「非真实负责人送达」。
2. **数据库迁移与索引**：本课仅扩/迁索引，无行数据迁移（`reports/lesson-10/*/migration/README.md`）；可抽查迁移脚本执行两次幂等与 `EXPLAIN QUERY PLAN` 命中覆盖索引，但**不宣称已迁 MySQL/Qdrant**（等价待课程确认，见 `stack-equivalence.md`）。
3. **就绪探针摘流量边界**：启动期 DB 不可读返回 503 已覆盖；**运行中 `chmod` 后因连接池复用健康检查仍可能返回 200**，运行期自动摘流量未实现，演示不得把它说成「已自动摘流量」。
4. **镜像与扫描遗留**：后端与 MCP 镜像 `.py=0` 已实测；但**后端基础镜像 OS 层 Trivy 仍报 HIGH=51**，**前端构建产物及 node_modules 残留 59 个 `.py` 与 9 个测试文件**，**密钥扫描范围不完整（BLOCKED）**，演示须如实说明，不得笼统称「镜像无源码、无高危」。
5. **场景覆盖**：505 条 Scenario 中 17 条 P0 已由 `check_lesson10_p0_scenarios.py` 补离线断言（P0 缺口为 0），仍有 **149 条非 P0 无匹配断言**，不得宣称「场景全覆盖」。

## 六、演示当天记录模板

```text
演示人：           角色：           环境（系统/架构/Docker 版本）：
提交：             镜像 digest：
执行时间（UTC）：  至

| 项 | 命令 | 退出码/返回码 | 与预期是否一致 | 证据路径 |
| --- | --- | --- | --- | --- |
| J1 | make check | | | |
| J2 | docker compose up -d | | | |
| J3 | 线上反查五步 | | | |
| J4 | collect.py --window | | | |
| D1 | 改坏→恢复 | | | |
| D2 | 新目录启动 | | | |
| D3 | 三面板 | | | |
| D4 | 提交→202→三态 | | | |
| D5 | api_bench 两版 | | | |

本人签名：            日期：
```

## 七、边界

- 本清单只备料，不代表任何一项已由第二人完成。
- 不得代签、不得把「本机通过」写成「独立演示通过」、不得在等价未认可时宣称课程验收完成。
