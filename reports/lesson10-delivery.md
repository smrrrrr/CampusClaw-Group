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
| 3.1 多阶段镜像 | 部分 | 运行层无 uv/gcc/测试，前端无 ts 源码；后端仍有 47 个 .py；trivy 发现后端依赖 12 critical |
| 3.2 Compose 等价 | PASS（等价说明） | 七服务 + SQLite 读就绪；未迁 MySQL/Qdrant |
| 3.3 换目录/机器 | 部分 | 干净 clone + 新项目名/端口 8087 启动成功；**换机未做** |
| 3.4 镜像编号 | 部分 | 本机 image ID + OCI revision 可反查；干净 clone 构建成功；无镜像仓库 digest |
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
| 6.3 压测 | PASS（三接口均有曲线） | submit 322 rps、query 573 rps、retrieve 38/24 rps；`bench.md` |
| 6.4 改进复测 | **FAIL（API 级）** | SQL 级 P95 降 22.62%；API 级同参 **123.2→123.7 ms（+0.4%）**，未达 ≥10% |
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

1. 安全门禁：npm `next` critical、`postcss`/`source-map-js` high；后端依赖 trivy 报 12 critical（`pillow` 需 13.0.0、`certifi` 需 2026.10.18、`python-jose` 无修复）；未登记例外、未大版本升级。
2. 真人环节：3 名真实用户、换人双跑、另一人新目录启动、组员签名。
3. 远端环节：CI 运行、镜像仓库 digest、main 保护、线上实例反查。
4. 运行期摘流量：仅自动检查覆盖 DB 503；运行中 chmod 后健康检查仍为 200（连接池），未证明自动摘流量。
5. 场景矩阵 338 条能力级待映射：已列出，未逐条补例。
6. 检索索引改进：SQL 级有效（-22.6%），API 级无收益（+0.4%），任务 9.4 失败。

## 五、失败、跳过与未知项去向（任务 3.5）

| 项 | 状态 | 去向 |
| --- | --- | --- |
| npm `next` critical / `postcss` / `source-map-js` high | OPEN | 需框架大版本升级（Next 15/16），超出“不大修”；保持 RED |
| pip `certifi`/`pillow`/`python-jose` 等 | OPEN | trivy 显示 12 critical（pillow 需 13.0.0、certifi 需 2026.10.18、python-jose 无修复）；记录后待定 |
| 密钥扫描范围完整=False | BLOCKED | 无容器日志时的扫描范围限制；运行栈启动后重跑仍受镜像/容器范围影响 |
| 场景矩阵 338 条能力级待映射 | OPEN | 已列出，需人工逐条确认/补例 |
| retrieve 并发 10 墙钟异常 | 已记录 | 样本窗数据有效，进程收尾耗时另记，不参与吞吐计算 |
| 3 名真实用户 | BLOCKED | 无真人，未用合成账号替代 |
| 新目录启动（首次） | FAIL→已修 | 非 root 后挂载目录属主问题；入口脚本修正后重验 |

## 六、同一版本核对（任务 4.1）

| 证据 | 版本/批次 | 是否同一版本 |
| --- | --- | --- |
| `gates/check-final.txt` | `a89ce70` 工作区（dirty） | 是 |
| `boot/smoke.json` | `fe227a1` 工作区 | 否（早期批次，已标注） |
| `async/reproduce2.txt` | `de035b8` 镜像 | 是（代码同） |
| `image-scan/trivy.txt` | `de035b8` 镜像 | 是 |
| `load-before/*` | `fe227a1`–`de035b8` 工作区 | 部分批次，已在 bench 标注 |
| `alert/received.jsonl` | `fe227a1` 工作区 | 早期批次，告警链路不受代码版本影响 |

结论：报告按批次标注版本；**不宣称全部证据来自同一提交**。

## 七、四项判定与五个当场动作（任务 10.5）

| 判定/动作 | 本机结果 | 缺失 |
| --- | --- | --- |
| 换人双跑一致 | 未执行 | 第二人 |
| README 新目录启动 | 重验中 | 新机/第二人 |
| 线上提交反查 | 未执行 | 线上实例与 CI |
| 60 秒窗口报数 | 0.04 秒完成 | 无 |
| D1 改坏被拦 | 红→修复→绿齐全 | 无 |
| D2 一键启动 | 本机通过 | 新机 |
| D3 面板指三技能 | 面板与窗口可用 | 无 |
| D4 异步链路 | 真实代理 14 项 PASS | 手机 |
| D5 压测前后对比 | SQL 级有效，API 级未做 | 同参 API 复测 |

---

## 八、本机收口追加（2026-11-14，第四节为当时状态，以下为最新）

### 8.1 双门禁与安全判据（5.5）

- 本地与 CI 使用**同一命令**：`make check`、`make check-security`；`.github/workflows/lesson10.yml` 的两个 job 分别执行，`images` job `needs: [check, security]`，无 `continue-on-error`。
- `scripts/check.py --json` 记录每步 `name/status/seconds/exit/finished` 与 `git_head`；`scripts/security_precheck.py` 增加 `course_high_critical`：npm 高危计数直接进入课程判据，pip 有漏洞但无严重度时判 BLOCKED，不折算为 0。
- 本地实测：`make check` **35/35 PASS**（含新增 `check_frontend_image_safety`、`check_lesson10_scenarios`）；`make check-security` **RED**，原因仅 Next。

### 8.2 最终镜像内容（6.1）

| 镜像 | .py | .git | 测试文件 | 真实密钥 | 系统 CA | 开发材料 |
| --- | --- | --- | --- | --- | --- | --- |
| backend | 2571（含 .venv） | 0 | 0 | 0 | 151 个 `/etc/ssl/certs/*.pem` | **已移除**（`dev_seed.py`、`Dockerfile`、`.dockerignore`、`.gitignore`、`.env.example`、`.python-version`） |
| frontend | 59（构建产物内） | 0 | 9（node_modules 内） | 0 | 2 | — |
| mcp-tools | 1561 | 0 | 0 | 0 | 150 | — |

- `.venv/bin` 无 `pip`/`uv`，只有 `python`/`uvicorn` 等运行入口。
- 后端 Dockerfile 在 `COPY . .` 后移除种子脚本与构建描述，`/app/*.py` 由 34 降为 33；新镜像重建后 health 200、启动日志正常。
- **未删除 Python 运行源码**：后端必须保留 `.py` 才能运行；是否接受仍待课程确认。
- 结论：不能声称“镜像绝对无源码”；密钥为零，开发材料仅 `dev_seed.py` 与构建文件。

### 8.3 CI 流水线（7.1 / 7.2 / 7.3 / 7.4）

- `lesson10.yml`：`check` 与 `security` 并列，失败即停；`images` 在两 job 成功后构建三镜像并用 Trivy 扫 `HIGH,CRITICAL`；`GIT_SHA` 同时用于镜像标签与 OCI `revision` 标签。
- 本机按同一命令跑通；**远端 CI 运行、独立 PR 故障重放、线上实例反查均未执行**（无推送授权/无线上目标）。
- 10.5 的独立演示清单已备：`reports/demo-checklist.md`（四项判定、五个动作、六份报告、签名模板）。

### 8.4 场景与压测状态更新

- 场景：505 条逐条映射已生成（`reports/scenario-coverage.md`），**335 条有候选**（断言名 55、别名 72、弱候选 174、文件级 34），**170 条无匹配断言**，其中 P0 高风险 17 条；较上一轮 280/225/P0 66 有明显收敛。新增 `check_lesson10_scenarios.py` 把 6 条纯函数场景变成自动断言。不再使用“338 条能力级待映射”这一旧口径。
- 9.4：检索热点优化后瓶颈档（并发 10）P95 **−23.8%**，并发 3 P95 +7.6%；按项目规则分档记录，不整体宣称通过。

### 8.5 仍然阻塞的事项

1. 安全门禁 RED 的根因是 Next 的版本范围计数：4 条 critical 在当前代码与 Linux standalone 部署下均不可触发（`reports/next-risk-applicability.md`），是否接受该论证取决于课程口径；若要求按计数归零，仍需升到 15.5.28+。
2. 后端镜像 OS 层 HIGH=51，不属 Next，需基础镜像维护另立任务。
3. 真人、签名、换机、远端 CI、线上反查、课程等价确认，均无法由本机替代。
