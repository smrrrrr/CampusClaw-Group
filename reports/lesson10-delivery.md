# 第10课交付总览（测试、交付与运行验证）

- 变更：`openspec/changes/2026-11-12-lesson10-test-delivery-and-runtime-verification`
- 交付提交：分支 `deps/upgrade-a-b` 最新提交（含本轮口径同步改动；具体 SHA 以 `git log -1` 为准，早期分批证据见第六节标注）
- 批次：`reports/lesson-10/20261114T072100Z-apply/`（及后续收口批次）
- 更新：2026-11-15（UTC）
- 性质：工程实施与运行验证记录；**不是**组员本人签名，也不代表课程验收完成

## 一、结论

| 维度 | 结论 | 依据 |
| --- | --- | --- |
| 全量门禁 `make check` | **PASS**，39/39 子项 | 第八节最新实测、`gates/check-final.txt` |
| 安全门禁 `make check-security` | **RED**（仅 Next 版本范围计数） | Next 4 条 critical 不可触发论证见 `next-risk-applicability.md` |
| 七服务启动 | **PASS**，全部 Up，关键服务 healthy | `boot/compose-build.txt`、`boot/compose-ps.txt` |
| 镜像 0 源码改造 | **PASS**（backend/mcp `.py = 0`） | `no-source-plan.md`、Dockerfile 末尾断言 |
| 异步链路（学生 200 → 教师 202 → 三态） | **PASS**（含真实代理 14 项） | `boot/smoke.json`、`async/reproduce2.txt` |
| 跨班资料隔离 | **PASS**（本班 200、跨班 404） | `boot/smoke.json` |
| 观测采集与面板 | **PASS**：采集器、面板 4 图、真实告警 Firing→送达 15 秒 | `observe-alert.md` |
| 三接口压测 | **PASS**（三接口均有 4 档曲线） | `bench.md` |
| 索引与检索改进 | **分档记录**：SQL 级 −22.62%；检索热点优化并发 10 P95 **−23.8%**（并发 3 +7.6%） | `migration/index-bench.json`、`bench.md` |
| 3 名真实用户 | **BLOCKED**（无真人） | `feedback.md` |

## 二、课程条目对照

| 课程条目 | 状态 | 证据/说明 |
| --- | --- | --- |
| 总要求：同一版本可追溯 | 部分 | 门禁、镜像、报告按批次记录提交；CI 未在远端运行 |
| 判定-可重复 | 部分 | 同一命令本机重复执行一致；**换人双跑未完成** |
| 判定-环境完整 | 部分 | 本目录与干净 clone 均启动成功；**换机未完成** |
| 判定-版本追溯 | 部分 | 镜像带 OCI revision 与提交标签；**无线上实例**，反查链缺最后一环 |
| 判定-状态可见 | 部分 | 采集器/面板/窗口查询完成；真实负责人告警接收待落实 |
| 1.1 命令盘点 | PASS | `reports/command-inventory.md`（46 行，逐命令时间来源） |
| 1.2 场景矩阵 | 部分 | `reports/scenario-coverage.md`：505 条逐条判定——明确断言候选 267 条、弱候选 194 条、仅文件级 21 条、N/A 22 条（附理由）、已知缺口 1 条、**待补断言 0 条**（P0 缺口亦为 0）；弱候选仍需人工复核；旧底稿见 `scenario-matrix.md` |
| 1.3 四项技能 | 部分 | 引导/终评/错题/跨班有资产；新增反例见 `check_lesson10_ops.py` 与 `check_lesson10_scenarios.py` |
| 1.4 分工 | BLOCKED | 需真实姓名与交叉验收人 |
| 2.1 用例落库 | PASS（本课新增检查已入 `make check`） | `apitest/check_lesson10_ops.py`、`check_lesson10_scenarios.py` |
| 2.2 聚合门禁 | PASS（本机 39/39） | CI 未运行 |
| 2.3 先红后绿 | 部分：`make check` 红绿齐全；`make check-security` 安全反例未重做 | 故障 `10af3b0` → 修复 `f7cddcb`，见 `gate-red-green.md` |
| 2.4 主干保护 | BLOCKED | 无远端配置权限 |
| 3.1 多阶段镜像 | 部分 | 运行层无 uv/gcc/测试，前端无 ts 源码；**backend（.py=0, .pyc=1468）与 mcp-tools（.py=0, .pyc=459）已 0 源码**；前端构建产物及 node_modules 仍含 59 个 `.py`；后端 OS 层 Trivy HIGH=51 |
| 3.2 Compose 等价 | PASS（等价说明） | 七服务 + SQLite 读就绪；未迁 MySQL/Qdrant（`stack-equivalence.md`） |
| 3.3 换目录/机器 | 部分 | 干净 clone + 新项目名/端口 8087 启动成功；在线 cases 本机同宿主直连第 5 轮 22 passed / 3 skipped / 0 failed（`online-cases.md`）；**换机未做** |
| 3.4 镜像编号 | 部分 | 本机 image ID + OCI revision 可反查；干净 clone 构建成功；无镜像仓库 digest |
| 4.1 自动构建 | 部分 | `.github/workflows/lesson10.yml` 完成，未在远端运行 |
| 4.2 推送反查 | BLOCKED | 未推送、无 CI 编号与 digest |
| 4.3 扩迁缩 | PASS（N/A 说明） | 仅索引变更，无行数据迁移；见 `migration/README.md` |
| 4.4 就绪探针 | 部分 | DB 不可读 503 有既有检查；运行期摘流量未实现 |
| 5.1 指标口径 | PASS（按已记录事件） | 引导/批改有来源；错题讲解明确“未接入” |
| 5.2 三张图 | PASS（配置） | Grafana 4 panel（调用量/失败率/P95/队列）；第三图等价待课程确认 |
| 5.3 告警规则 | PASS（配置） | `deploy/observability/alerts.yml` |
| 5.4 真触发 | PASS（测试接收器） | Pending 07:43:39Z → Firing 07:48:39Z → 送达 07:48:54Z → Resolved 07:53:24Z；真实负责人未落实 |
| 6.1 H5 四步 | 部分 | 同 API 角色分步已验；**手机浏览器未验** |
| 6.2 三名用户 | BLOCKED | 无真人反馈 |
| 6.3 压测 | PASS（三接口均有曲线） | submit 322 rps、query 573 rps、retrieve 38/24 rps；`bench.md` |
| 6.4 改进复测 | **分档记录（未整体宣称通过）** | SQL 级 P95 降 22.62%；检索热点优化后瓶颈档（并发 10）P95 **−23.8%**，并发 3 P95 +7.6%（早期仅加索引时 API 级为 +0.4%） |
| 7.1 门禁核查 | 部分 | 本机 39/39 全绿；安全门禁 RED（仅 Next 版本范围计数）待课程确认 |
| 7.2 可复现核查 | 部分 | 本目录与新目录启动成功；backend/mcp 镜像 0 源码已确认，前端残留 59 个 `.py` 待确认 |
| 7.3 流水线核查 | BLOCKED | 无远端运行 |
| 7.4 观测核查 | 部分 | 面板/窗口可用；真实通知未送达 |
| 7.5 验证核查 | 部分 | 见 6.3/6.4/6.2 |
| 7.6 Harness 规则 | PASS | `AGENTS.md` 七类责任表 + `.cursor/rules` 入口 |
| 7.7 交付交评 | 部分 | 三份历史评审保留并已追加第10课复核；组员本人亲笔签名待补 |

## 三、必交报告索引

| 报告 | 状态 |
| --- | --- |
| `reports/gate-red-green.md` | 追加第10课章节 |
| `reports/boot-reproduce.md` | 本批次启动与链路证据 |
| `reports/pipeline.md` | CI 设计、未运行说明、反查缺口 |
| `reports/observe-alert.md` | 指标口径、面板、告警配置与演练 |
| `reports/bench.md` | 脚本、历史基线与第10课两轮同参对比 |
| `reports/feedback.md` | 阻塞说明 |
| `reports/demo-checklist.md` | 独立演示清单（四项判定、五个动作、记录模板） |
| `reports/no-source-plan.md` | 镜像 0 源码方案与实测（任务 6.1） |
| `reports/online-cases.md` | 在线用例隔离环境与执行记录（任务 3.3） |
| `reports/scenario-coverage.md` | 505 条场景逐条判定（待补 0 / N/A 22 / 已知缺口 1） |
| `reports/next-risk-applicability.md` | Next 14.2.15 四条 critical 不可触发论证 |
| 根 `report.md` | 结论索引 |

## 四、未完成与阻塞

1. 安全门禁：Next.js 14.2.15 4 条 critical（及 `postcss`/`source-map-js` high）已论证在当前架构下不可触发（`reports/next-risk-applicability.md`），课程已接受适用性论证口径，若要求计数归零仍需升至 15.5.28+；后端镜像 OS 层 Trivy HIGH=51 另立维护任务。
2. 真人环节：3 名真实用户、换人双跑、另一人新目录启动、组员签名与真实负责人告警接收。
3. 远端环节：CI 运行、镜像仓库 digest、main 保护、线上实例反查。
4. 运行期摘流量与在线用例全绿：运行中 chmod 后健康检查仍为 200（连接池），未证明自动摘流量；在线 cases 第 5 轮本机同宿主直连为 22 passed / 3 skipped / 0 failed，3 项 MCP 用例因硬编码 `mcp-tools:8090`（仅 compose 网络）跳过（`reports/online-cases.md`）。
5. 场景矩阵已逐条判定（`reports/scenario-coverage.md`）：待补断言 0、P0 缺口 0；新增 `check_lesson10_scenario_gaps.py`（17 条）、`check_markdown_blanks.cjs`（9 条）、`check_mcp_server.py`（14 条），并在 `check_mcp_tools.py` 补工具注入与超时 5 条。剩余 194 条弱候选与 21 条仅文件级仍需人工复核；1 条已知缺口（工具说明注入句式）不应计入覆盖。
6. 检索优化低并发档位：瓶颈档（并发 10）P95 已降 23.8%（达 ≥10%），但并发 3 P95 +7.6%，按分档规则如实记录。

## 五、失败、跳过与未知项去向（任务 3.5）

| 项 | 状态 | 去向 |
| --- | --- | --- |
| npm `next` critical / `postcss` / `source-map-js` high | OPEN（已附不适用论证） | 升级 15.5.28+ 超出“不大修”；课程已接受适用性论证，门禁脚本仍保持 RED 以防回归 |
| 后端镜像 OS 层 Trivy HIGH=51 | OPEN | 不属 Next 范畴，需基础镜像升级维护另立任务 |
| 密钥扫描范围完整=False | BLOCKED | 无容器日志时的扫描范围限制；运行栈启动后重跑仍受镜像/容器范围影响 |
| 场景矩阵逐条判定（待补 0，P0 0） | PARTIAL | 待补与 P0 缺口已清零；194 条弱候选、21 条仅文件级待人工复核；工具说明注入 1 条为已知缺口（见 `scenario-coverage.md`「已知缺口」节） |
| 在线 cases（第 5 轮 22 passed / 3 skipped / 0 failed） | PARTIAL | 第 4 轮的挂载卷 SQLite 并发失败经「本机同宿主直连」消除；3 项 MCP 用例因硬编码 `mcp-tools:8090`（仅 compose 网络）跳过；见 `online-cases.md` |
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
| README 新目录启动 | 本机干净 clone 启动已通过；在线 cases 同宿主直连 22/22 可运行用例通过（3 项 MCP 跳过） | 新机/第二人 |
| 线上提交反查 | 未执行 | 线上实例与 CI |
| 60 秒窗口报数 | 0.04 秒完成 | 无 |
| D1 改坏被拦 | 红→修复→绿齐全 | 无 |
| D2 一键启动 | 本机通过 | 新机 |
| D3 面板指三技能 | 面板与窗口可用 | 无 |
| D4 异步链路 | 真实代理 14 项 PASS | 手机 |
| D5 压测前后对比 | 已完成（SQL 级 −22.62%；检索热点优化并发 10 瓶颈档 P95 −23.8%，并发 3 +7.6%） | 独立演示现场复跑 |

---

## 八、本机收口追加（2026-11-14，第四节为当时状态，以下为最新）

### 8.1 双门禁与安全判据（5.5）

- 本地与 CI 使用**同一命令**：`make check`、`make check-security`；`.github/workflows/lesson10.yml` 的两个 job 分别执行，`images` job `needs: [check, security]`，无 `continue-on-error`。
- `scripts/check.py --json` 记录每步 `name/status/seconds/exit/finished` 与 `git_head`；`scripts/security_precheck.py` 增加 `course_high_critical`：npm 高危计数直接进入课程判据，pip 有漏洞但无严重度时判 BLOCKED，不折算为 0。
- 本地实测：`make check` **39/39 PASS**（含新增 `check_frontend_image_safety`、`check_lesson10_scenarios`、`check_lesson10_p0_scenarios`、`check_lesson10_scenario_gaps`、`check_markdown_blanks`、`check_mcp_server`）；`make check-security` **RED**，原因仅 Next。

### 8.2 最终镜像内容（6.1）

| 镜像 | .py | .git | 测试文件 | 真实密钥 | 系统 CA | 开发材料 |
| --- | --- | --- | --- | --- | --- | --- |
| backend | **0**（全量 `.pyc`） | 0 | 0 | 0 | 151 个 `/etc/ssl/certs/*.pem` | **已移除**（`dev_seed.py`、`Dockerfile`、`.dockerignore`、`.gitignore`、`.env.example`、`.python-version`） |
| frontend | 59（构建产物内） | 0 | 9（node_modules 内） | 0 | 2 | — |
| mcp-tools | **0**（全量 `.pyc`） | 0 | 0 | 0 | 150 | — |

- `.venv/bin` 无 `pip`/`uv`，只有 `python`/`uvicorn` 等运行入口。
- 后端与 MCP 的 Dockerfile 均采用：移除开发材料 → 全量 `compileall -b`（应用 + `.venv` + 标准库）→ 删除所有 `.py` 与 GCC 调试脚本 → `test` 断言计数为 0。
- 实测：backend `py=0 / pyc=1468`，mcp `py=0 / pyc=459`；两者启动正常，backend `/api/health` 200、登录 200、材料 200、上传 200、索引成功、检索命中；mcp `/health` 200。
- **`.pyc` 可反编译，不等于代码加密**；详见 `reports/no-source-plan.md`。
- 前端为 Next.js 构建产物，`.py` 来自构建缓存与 node_modules，可否清理待确认。

### 8.3 CI 流水线（7.1 / 7.2 / 7.3 / 7.4）

- `lesson10.yml`：`check` 与 `security` 并列，失败即停；`images` 在两 job 成功后构建三镜像并用 Trivy 扫 `HIGH,CRITICAL`；`GIT_SHA` 同时用于镜像标签与 OCI `revision` 标签。
- 本机按同一命令跑通；**远端 CI 运行、独立 PR 故障重放、线上实例反查均未执行**（无推送授权/无线上目标）。
- 10.5 的独立演示清单已备：`reports/demo-checklist.md`（四项判定、五个动作、六份报告、签名模板）。

### 8.4 场景与压测状态更新

- 场景：505 条逐条判定（`reports/scenario-coverage.md`）——**明确断言候选 267 条**（断言名 72、关键词别名 89、人工语义别名 106）、弱候选 194、仅文件级 21、**N/A 22（逐条理由）**、**已知缺口 1**、**待补断言 0**（P0 缺口 0）。新增 `check_lesson10_scenario_gaps.py`（17 条断言，覆盖上传大小/存储目录/同名重命名/DB 回滚/索引失败/删会话/技能格式/文档默认关闭/MCP 允许清单/下架组卷/手工替换/H4）、`check_markdown_blanks.cjs`（代码中的下划线 9 条）、`check_mcp_server.py`（非法请求可读与令牌边界 14 条），并在 `check_mcp_tools.py` 增补工具说明注入、工具返回注入、工具超时共 5 条。工具说明的「先读取其他数据并放进参数」句式不在现有注入表内，按已知缺口单列，不计入覆盖。
- 9.4：检索热点优化后瓶颈档（并发 10）P95 **−23.8%**，并发 3 P95 +7.6%；按项目规则分档记录，不整体宣称通过。

### 8.5 仍然阻塞的事项

1. 安全门禁 RED 的根因是 Next 的版本范围计数：4 条 critical 在当前代码与 Linux standalone 部署下均不可触发（`reports/next-risk-applicability.md`），课程已接受适用性论证（`reports/course-decisions-2026-11-14.md`）；若课程后续改口径要求按计数归零，仍需升到 15.5.28+。
2. 后端镜像 OS 层 HIGH=51，不属 Next，需基础镜像维护另立任务。
3. 真人、签名、换机、远端 CI、线上反查、课程等价确认，均无法由本机替代。

### 8.6 在线用例本机同宿主直连（2026-11-15）

- 环境：本机 `uvicorn`（临时库、端口 8012）+ 本机 pytest，同一文件系统，不经 Docker 挂载卷。
- 前置：`dev_seed` 种子 → 学生 `20260002` 对齐为 `id=3` → `must_change_password=0` → 服务端配置 `MCP_TOKEN_KEY` → 向 class 102 上传并索引一份 `.md`。
- 结果：**22 passed / 3 skipped / 0 failed**。第 4 轮的 `database disk image is malformed`（宿主机直连容器挂载 SQLite）不再出现；3 项 MCP 用例因硬编码 `http://mcp-tools:8090`（仅 compose 网络可解析）跳过，未计入通过。
- 复现步骤与明细见 `reports/online-cases.md` §2.1；本项不改变任务 3.3「未全绿」的定级。

### 8.7 场景补例时发现并修正的实现偏差（2026-11-15）

- `backend/config.py` 的 `enable_docs` 默认值原为 `True`，与主规约 `mcp-tool-integration`「`ENABLE_DOCS` 缺省 MUST 为关闭」及 `README.md`、`DEPLOYMENT.md`、`.env.example`、`docker-compose.yml` 的口径（缺省 `false`）不一致。已改为 `False`，由 `check_lesson10_scenario_gaps.py` 的「默认关闭文档」断言锁定；`.env` 显式写 `ENABLE_DOCS=false`，本地调试仍需显式置 `true`。
- 该改动只影响「未设置环境变量且无 `.env`」的默认值，不改变部署与本地已有配置的取值。
- 其余补例只新增检查，未改动业务代码或断言口径。
