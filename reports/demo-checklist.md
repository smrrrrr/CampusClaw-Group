# 第10课独立演示清单（任务 10.5 备料）

- 版本：2026-11-14，分支 `deps/upgrade-a-b`
- 用途：交给**另一名组员**按本清单独立演示并记录；AI 与实施者不得代跑代签
- 状态：**备料完成，演示未执行**。任何一项未由本人完成，不得把对应课程任务标为完成

## 一、四项判定（须换人执行）

| 判定 | 演示人要做的事 | 通过信号 | 证据写回 |
| --- | --- | --- | --- |
| J1 换人双跑一致 | 同一提交、同一锁文件、同一夹具与参数，运行 `make check` 与 `make check-security` 各两次 | 断言数、退出码、关键状态一致；时间与随机 ID 不同需说明 | 本文件表下追加，或 `reports/boot-reproduce.md` |
| J2 README 新目录启动 | 新建空目录克隆，按 README 准备 `.env`、构建、`docker compose up -d` | 七服务就绪，`/health` 200，页面 200；不得复用已有数据目录 | `reports/boot-reproduce.md` §八（本机已做当前提交空目录；仍需他人独立执行） |
| J3 线上提交反查 | 从线上 URL 找到实例 → 镜像 digest → OCI `revision` 标签 → CI run → 提交 | 五步可追溯且互相一致 | `reports/pipeline.md`；远端 CI run `43826707775` 已存在但 `images` 跳过、无在线实例，五步仍缺两环 |
| J4 60 秒窗口报数 | 指定任意 UTC 60 秒窗口，调用采集器窗口模式 | 60 秒内返回三技能调用量与失败率；空分母显示「无样本」 | `reports/observe-alert.md` |

## 二、五个当场动作

| 动作 | 命令/操作 | 预期 | 当前本机状态 |
| --- | --- | --- | --- |
| D1 改坏被拦 | 临时改坏一个断言或权限判断，跑门禁，再恢复 | 先红后绿，两次输出都保留 | 已完成（`reports/gate-red-green.md`） |
| D2 一键启动 | 新目录 `docker compose up -d` | 七服务 Up，核心 healthy | 本机空目录已通过（当前提交、独立项目/端口 8097）；**缺新机** |
| D3 面板指三技能 | 打开 Grafana 三面板，核对技能标签与失败率 | 三技能分线；空分母显示无样本 | 本机可用；**第三图等价待课程确认** |
| D4 异步链路 | 学生提交 → 202/task_ids → 轮询三态 → 他人不可见 | 真实代理消费，跨班 404 | 真实代理 15 项 PASS；**缺手机** |
| D5 压测前后对比 | 跑 `scripts/lesson10_api_bench.py` 并对旧版同参 | 瓶颈档 P95 降 ≥10%，吞吐不降、错误率不增 | 已完成：并发 10 P95 −23.8%（`reports/bench.md`） |

补充现场核验项（课程答复新增）：
- **镜像 0 源码断言（任务 6.1）**：在运行中的 `backend` 与 `mcp-tools` 容器内执行 `find / -name '*.py' -not -path '/proc/*' | wc -l`，预期均为 `0`（证据见 `reports/no-source-plan.md`）。
- **在线 cases 复跑（任务 3.3）**：本机同宿主直连（临时库、后端与 pytest 同文件系统）第 5 轮为 `22 passed / 3 skipped / 0 failed`；compose 网络内第 6 轮（2026-11-16）为 `24 passed / 1 skipped / 0 failed`，仅剩「无模型 Key 时的工具审计」跳过，明细与复现步骤见 `reports/online-cases.md` §2.2。
- **当前提交重建复验（2026-11-16，任务 6.1/7.1）**：七服务 + 四个观测容器全部启动，`/health`、`/api/health`、`/login` 200；backend/mcp-tools 镜像 `.py=0`、OCI revision 与提交一致；真实 RabbitMQ 异步复现 15 项 PASS。证据 `reports/lesson-10/20261116T161500Z-docker/`、`reports/async-grading/20261116tdockerreal-broker-result.json`。
- **换目录 / 本机 registry / 备份回滚（2026-11-16）**：当前提交导出到空目录后独立项目/端口 8097 启动成功（七服务 Up、`/health` 与 `/login` 200、`.py=0`）；本机 `registry:2` push/pull 三镜像并记录 digest；演示库临时副本备份恢复指纹一致，`37aecf9` 上一 tag 在独立项目/端口 8098 回滚通过。均不替代换机、远端仓库或正式发布。证据 `reports/lesson-10/20261116T024000Z-clone-registry-rollback/`、`reports/release-rollback.md`。
- **GitHub Actions 远端实跑（2026-11-16）**：Draft PR #3 触发两次。首次因 `@openspec/cli` npm 404 失败；修复 `fca85f7` 后 run `43826707775` 的 `make check` 在远端 Ubuntu **41/41 通过**，`make check-security` **RED**（Next critical + 5 个未登记 npm 包；容器账本 blocked），`images` 按 `needs` 跳过。故远端没有镜像、Trivy 或 digest，也不构成受控绿版本。证据 `reports/lesson-10/20261116T075000Z-remote-ci/`。这是“另一台机器”，不是“另一个人”。
- **独立分支故障重放（7.3，2026-11-16）**：在 `ci-fault-replay` 分支故意写错 M2 断言，Draft PR #4 的 run `43828237591` 中 `make check` **失败**、`images` **跳过**；本机退出码 1。验证后已关闭 PR、删除分支。required check 未配置，不能宣称“已阻止合入”。证据 `reports/lesson-10/20261116T080640Z-ci-fault-replay/`。

## 三、六份必交报告核对

| 报告 | 路径 | 当前状态 |
| --- | --- | --- |
| 交付与对照 | `reports/lesson10-delivery.md` | 已更新最新状态 |
| 从零启动 | `reports/boot-reproduce.md` | 本机完成（含当前提交空目录复验）；换机待做 |
| 流水线 | `reports/pipeline.md` | GitHub Actions 已实跑（run `43826707775`）：check 绿、security 红、images 跳过；受控绿版本与远端 digest 待做 |
| 观测与告警 | `reports/observe-alert.md` | 四阶段齐全；接收授权待确认 |
| 压测 | `reports/bench.md` | 已完成两轮对比 |
| 用户反馈 | `reports/feedback.md` | **BLOCKED**，无真实用户 |

另有根 `report.md`、`reports/scenario-coverage.md`（505 条场景逐条判定：待补 0 / 弱候选 0 / 仅文件级 0 / N/A 23 / 已知缺口 3）、`reports/no-source-plan.md`（镜像 0 源码方案与实测）、`reports/online-cases.md`（在线用例环境与非通过明细）及 `reports/next-risk-applicability.md`。

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

1. **安全门禁 RED**：Next 4 条 critical 已有不适用论证（`reports/next-risk-applicability.md`），但计数还包含 5 个未登记 npm 包；课程是否接受尚未答复，未答复前不得说「高危 0 条」。
2. **等价未认可**：第三图 P95 是否等价于完整接口耗时、MySQL/Qdrant/Golang 是否强制，均未获课程确认。
3. **返回码差异**：演示中若出现与本文预期不同的状态码，先记入本节「待修」，不得现场改口径。
4. **签名**：三份审核与反馈表必须由本人填写；AI 生成的追加内容不能替代签名。

## 五之二、现场核验边界（避免预期偏差）

以下为本机已确认的边界，演示时须按实际行为记录，不得按理想口径改写：

1. **告警规则与送达**：规则见 `deploy/observability/alerts.yml`（错误率>1% 且样本≥20 持续 5 分钟）；本机测试接收器已验证 Pending→Firing→15 秒送达→Resolved，但**真实负责人接收授权未落实**，演示若用测试接收器须注明「非真实负责人送达」。
2. **数据库迁移与索引**：本课仅扩/迁索引，无行数据迁移（`reports/lesson-10/*/migration/README.md`）；可抽查迁移脚本执行两次幂等与 `EXPLAIN QUERY PLAN` 命中覆盖索引，但**不宣称已迁 MySQL/Qdrant**（等价待课程确认，见 `stack-equivalence.md`）。
3. **就绪探针摘流量边界**：启动期 DB 不可读返回 503 已覆盖；**运行中 `chmod` 后因连接池复用健康检查仍可能返回 200**，运行期自动摘流量未实现，演示不得把它说成「已自动摘流量」。
4. **镜像与扫描遗留**：backend、mcp-tools 与 frontend 三镜像 `.py=0` 已实测；但**后端基础镜像 OS 层 Trivy 仍报 HIGH=51**，演示须如实说明，不得笼统称「镜像无源码、无高危」。密钥扫描已按当前工作目录识别 compose 项目并实扫容器日志与前端静态包，**范围完整**；容器账本仍 blocked 的原因是演示库没有四个种子身份，不是扫描范围缺失。
5. **场景覆盖**：505 条 Scenario 已逐条判定：待补断言 **0**、P0 缺口 0、弱候选 **0**、仅文件级 **0**；**人工复核确认 185 条**、**部分覆盖 22 条**（备注写明未断言部分）、**N/A 23 条**（前端交互/真实模型语义/需容器，逐条理由见 `reports/scenario-coverage.md`）、**已知缺口 3 条**（工具说明「先读取其他数据并放进参数」的注入句式；教师端按班级查看 AI 提问历史；学生把 AI 解答加入错题本）。部分覆盖与已知缺口不得计入「场景全覆盖」。

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

- 上方为演示准备与历史结果。换人执行的实测见第八、九节。
- 不得代签、不得把「本机通过」写成「独立演示通过」、不得在等价未认可时宣称课程验收完成。

## 八、J1 本人门禁双跑（2026-11-17）

执行人 **smrrrrr**，在 Windows 新克隆目录 `campusclaw-10-personal` 的 PowerShell 5.1 中运行。两对检查都使用 PR #3 的提交 `977bcde028b24892ac58466b5612e844bd5b2ecb`。以下时间为北京时间。

| 检查 | 第 1 轮 | 第 2 轮 | 对照 |
| --- | --- | --- | --- |
| 普通门禁 `scripts/check.py` | 15:01:59–15:03:38，42/43 通过，退出 1 | 15:04:12–15:05:32，42/43 通过，退出 1 | 两轮各子项及退出状态一致。唯一失败是 `check_os_vuln_gate` 在 Windows 上读取中文输出时发生编码错误。 |
| 安全门禁 `scripts/security_precheck.py`，恢复演示库以后 | PASS，退出 0 | 15:09:13–15:09:25，PASS，退出 0 | 两轮接口探针与密钥扫描均通过，npm 高危和严重漏洞为 0，待验范围为空。 |

首次安全双跑使用空库，两轮均为 BLOCKED、退出 2。补入交接包中的四个演示账号后，重启独立 Compose 项目 `campusclaw-lesson10-personal`，用同一演示库执行上表的两次安全扫描。普通门禁使用脚本自己的离线测试夹具，保留原结果。补丁 PR #5 含这项编码修复，被验收的 PR #3 提交仍是 `977bcde`。

证据见 [普通第 1 轮](lesson-10/20261117-personal-j1/check-1.json)、[普通第 2 轮](lesson-10/20261117-personal-j1/check-2.json)、[安全第 1 轮](lesson-10/20261117-personal-j1/security-demo-1.txt)、[安全第 2 轮](lesson-10/20261117-personal-j1/security-demo-2.txt) 和 [末次安全报告](lesson-10/20261117-personal-j1/security-demo-2.json)。

**J1 结论：** 两次普通结果一致，仍有一个失败。两次安全结果一致，均通过。[J2 本人启动记录](boot-reproduce.md#九102-本人启动复验2026-11-17)已另行归档。

## 九、smrrrrr 对 PR #3 的交叉验收汇总（2026-11-17）

评审基线为 PR #3 的 `977bcde028b24892ac58466b5612e844bd5b2ecb`。本人执行结果、Codex 技术复验和先前项目证据按实际来源填写。

| 项目 | 状态与证据 |
| --- | --- |
| J1 双跑 | **本人完成。** 两次普通门禁均 42/43、退出 1，两次安全专项均 PASS、退出 0。普通门禁失败是可复现的 Windows 编码问题。见本报告第八节。 |
| J2 新目录启动 | **本人完成。** 七服务就绪，健康页与登录入口均返回 200。见[本人启动记录](boot-reproduce.md#九102-本人启动复验2026-11-17)。 |
| J3 线上反查 | **待线上目标。** GitHub 仓库的部署列表为空，交接报告也未提供线上 URL，当前只能核对本地镜像标记和历史 CI。见[流水线与反查](pipeline.md)。 |
| J4 60 秒窗口 | **技术复验已执行。** Codex 在北京时间 15:09–15:10 的窗口读取本地演示库，三个技能均显示无样本，约 0.16 秒返回。再用同长度的临时合成库验证，作业批改两次成功、一次失败，失败率 33.33%，窗口结束时刻的测试记录未计入。无分母的错题讲解返回 null。见[窗口原始结果](lesson-10/20261117-peer-review/j4-window.json)。 |
| D1 先红后绿 | 已复核课程的[终评保护故障演练](gate-red-green.md)。本次门禁修复另有[真实缺陷回归](https://github.com/smrrrrr/CampusClaw-Group/blob/b068cb912f55bd14d9322cae99f5838b13680fab/reports/gate-red-green.md)，普通门禁从退出 1 恢复为退出 0。 |
| D2 一键启动 | **本人完成。** 同 J2。 |
| D3 面板 | 已核对[当前 Grafana 配置](lesson-10/20261117-peer-review/d3-dashboard-config.json)，覆盖技能调用量、失败率、对应接口 P95 和批改队列深度。P95 与队列深度分两个面板。现场页面操作待录；P95 的课程口径见[课程决定](course-decisions-2026-11-14.md)。 |
| D4 异步链路 | 复核已保存的[本地 HTTP 结果](lesson-10/20261117-peer-review/d4-assisted-http.json)。Codex 用合成账号和假模型观察到学生提交 200、教师初批 202、任务 pending → running → succeeded、本人结果 200、跨班 404。手机实机待验。 |
| D5 压测对比 | 已复核[历史两轮数据](bench.md)。并发 10 的 P95 从 677.25 ms 降为 516.37 ms，下降 23.8%。并发 3 的 P95 上升 7.6%，保留原记录。 |

**评审结论：** 本人启动通过，双跑结果一致，原版普通门禁仍有一个失败。已核对的现场证据、辅助复验与历史证据可供课堂复查。补丁 PR #5 的普通及安全门禁已通过，镜像检查拦下后端与 MCP 镜像中未登记的软件包 `ncurses-bin`。线上反查、现场待验项与镜像问题保持开放。见 [PR #3 复验评论](https://github.com/smrrrrr/CampusClaw-Group/pull/3#issuecomment-6939322783)和 [#5 镜像检查](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44022376165/job/133835370477)。
