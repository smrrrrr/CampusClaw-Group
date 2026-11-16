# 第10课交付总览（测试、交付与运行验证）

- 变更：`openspec/changes/2026-11-12-lesson10-test-delivery-and-runtime-verification`
- 交付提交：分支 `deps/upgrade-a-b` 最新提交（含本轮口径同步改动；具体 SHA 以 `git log -1` 为准，早期分批证据见第六节标注）
- 批次：`reports/lesson-10/20261114T072100Z-apply/`（及后续收口批次）
- 更新：2026-11-16（UTC）
- 性质：工程实施与运行验证记录；**不是**组员本人签名，也不代表课程验收完成

## 一、结论

| 维度 | 结论 | 依据 |
| --- | --- | --- |
| 全量门禁 `make check` | **PASS**，41/41 子项 | 第八节最新实测、`gates/check-final.txt` |
| 安全门禁 `make check-security` | **RED**（Next critical + 5 个未登记 npm 包；容器账本 blocked） | `security-run.json`；Next 4 条 critical 适用性见 `next-risk-applicability.md` |
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
| 总要求：同一版本可追溯 | 部分 | 门禁、镜像、报告按批次记录提交；GitHub Actions 已实跑，但因安全门禁 RED 未产出可交付镜像 |
| 判定-可重复 | 部分 | 同一命令本机重复执行一致；**换人双跑未完成** |
| 判定-环境完整 | 部分 | 本目录与干净 clone 均启动成功；**换机未完成** |
| 判定-版本追溯 | 部分 | 镜像带 OCI revision 与提交标签；**无线上实例**，反查链缺最后一环 |
| 判定-状态可见 | 部分 | 采集器/面板/窗口查询完成；真实负责人告警接收待落实 |
| 1.1 命令盘点 | PASS | `reports/command-inventory.md`（46 行，逐命令时间来源） |
| 1.2 场景矩阵 | 部分 | `reports/scenario-coverage.md`：505 条逐条判定——人工复核确认 185 条、部分覆盖 22 条（备注写明未断言部分）、断言名候选 77 条、人工语义别名 106 条、关键词别名 89 条、N/A 23 条（附理由）、已知缺口 3 条、**待补断言 0 条**（P0 缺口亦为 0）、**弱候选 0 条、仅文件级 0 条**；旧底稿见 `scenario-matrix.md` |
| 1.3 四项技能 | 部分 | 引导/终评/错题/跨班有资产；新增反例见 `check_lesson10_ops.py` 与 `check_lesson10_scenarios.py` |
| 1.4 分工 | BLOCKED | 需真实姓名与交叉验收人 |
| 2.1 用例落库 | PASS（本课新增检查已入 `make check`） | `apitest/check_lesson10_ops.py`、`check_lesson10_scenarios.py` |
| 2.2 聚合门禁 | PASS（本机与远端 Ubuntu 均 41/41） | 本机 `make check`；GitHub Actions run `43826707775` 的 `make check` job 通过 |
| 2.3 先红后绿 | 部分：`make check` 红绿齐全；`make check-security` 安全反例未重做 | 故障 `10af3b0` → 修复 `f7cddcb`，见 `gate-red-green.md` |
| 2.4 主干保护 | BLOCKED | 当前账号对远端仓库 `admin=false, maintain=false`，无法设置 required checks 或禁止未审批合入 |
| 3.1 多阶段镜像 | 部分 | 运行层无 uv/gcc/测试，前端无 ts 源码；**backend（.py=0, .pyc=2612）、mcp-tools（.py=0, .pyc=1598）与 frontend（.py=0）均已 0 源码**；后端 OS 层 Trivy HIGH=51 |
| 3.2 Compose 等价 | PASS（等价说明） | 七服务 + SQLite 读就绪；未迁 MySQL/Qdrant（`stack-equivalence.md`） |
| 3.3 换目录/机器 | 部分 | 当前提交 `984c4c8` 经 `git archive` 到全新空目录，独立项目名/端口 8097 构建并启动成功，七服务 Up、`/health` 与 `/login` 200、三镜像 `.py=0`（`reports/lesson-10/20261116T024000Z-clone-registry-rollback/`）；在线 cases compose 网络内 24 passed / 1 skipped / 0 failed（`online-cases.md`）；**换机未做**，换目录不能替代 |
| 3.4 镜像编号 | 部分 | 本机 image ID + OCI revision 可反查；干净 clone 构建成功；本机 registry push/pull 已产生 digest，**远端仓库 digest 仍无** |
| 4.1 自动构建 | 部分 | `.github/workflows/lesson10.yml` 在 Draft PR #3 上实跑：首次因 OpenSpec 包名 404 失败，修正后 `check` 通过；`security` RED，`images` 被 `needs` 跳过，未产出可交付镜像 |
| 4.2 推送反查 | BLOCKED | 远端 CI 未产出镜像 digest（`images` 未运行）；本机 registry 演练已产生 digest，仅为链路验证，不能替代远端仓库或 GHCR |
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
| 7.1 门禁核查 | 部分 | 本机与 GitHub Actions 远端 Ubuntu 的 `make check` 均 41/41；安全门禁 RED（Next critical + 5 个未登记 npm 包，容器账本 blocked）待课程确认 |
| 7.2 可复现核查 | 部分 | 本目录与当前提交空目录（独立项目/端口 8097）均启动成功；backend/mcp/frontend 三镜像均 0 源码已确认；换机未做 |
| 7.3 流水线核查 | 部分 | PR #3 run `43826707775` 已实跑：`check` 通过、`security` RED、`images` 跳过；独立分支故障重放 run `43828237591` 的 `make check` 失败、`images` 跳过。required check 未配置，不能证明阻止合入 |
| 7.4 观测核查 | 部分 | 面板/窗口可用；真实通知未送达 |
| 7.5 验证核查 | 部分 | 见 6.3/6.4/6.2 |
| 7.6 Harness 规则 | PASS | `AGENTS.md` 七类责任表 + `.cursor/rules` 入口 |
| 7.7 交付交评 | 部分 | 三份历史评审保留并已追加第10课复核；组员本人亲笔签名待补 |

## 三、必交报告索引

| 报告 | 状态 |
| --- | --- |
| `reports/gate-red-green.md` | 追加第10课章节 |
| `reports/boot-reproduce.md` | 本批次启动与链路证据 |
| `reports/pipeline.md` | CI 设计、GitHub Actions 实跑记录（红）、反查缺口 |
| `reports/observe-alert.md` | 指标口径、面板、告警配置与演练 |
| `reports/bench.md` | 脚本、历史基线与第10课两轮同参对比 |
| `reports/feedback.md` | 阻塞说明 |
| `reports/demo-checklist.md` | 独立演示清单（四项判定、五个动作、记录模板） |
| `reports/no-source-plan.md` | 镜像 0 源码方案与实测（任务 6.1） |
| `reports/online-cases.md` | 在线用例隔离环境与执行记录（任务 3.3） |
| `reports/scenario-coverage.md` | 505 条场景逐条判定（待补 0 / 弱候选 0 / 仅文件级 0 / N/A 23 / 已知缺口 3） |
| `reports/next-risk-applicability.md` | Next 14.2.15 四条 critical 不可触发论证 |
| 根 `report.md` | 结论索引 |

## 四、未完成与阻塞

1. 安全门禁：Next.js 14.2.15 4 条 critical（及 `postcss`/`source-map-js` high）已论证在当前架构下不可触发（`reports/next-risk-applicability.md`），课程已接受适用性论证口径，若要求计数归零仍需升至 15.5.28+；另有 5 个未登记 npm 包（`katex`、`micromark-extension-math`、`next`、`rehype-katex`、`remark-math`）计入 RED，容器账本因演示库无四个种子身份为 blocked。后端镜像 OS 层 Trivy HIGH=51 另立维护任务。
2. 真人环节：3 名真实用户、换人双跑、另一人新目录启动、组员签名与真实负责人告警接收。
3. 远端环节：CI 已实跑但为红（run `43826707775`，`security` 未过、`images` 跳过）；独立分支故障重放已完成（run `43828237591`，`make check` 失败、`images` 跳过），但 required check 未配置。因此远端镜像仓库 digest、main 保护、线上实例反查仍缺。
4. 运行期摘流量与在线用例全绿：运行中 chmod 后健康检查仍为 200（连接池），未证明自动摘流量；在线 cases 第 5 轮本机同宿主直连为 22 passed / 3 skipped / 0 failed，第 6 轮 compose 网络内为 24 passed / 1 skipped / 0 failed（唯一跳过为未配置模型 Key 的工具审计）（`reports/online-cases.md`）。
5. 场景矩阵已逐条判定（`reports/scenario-coverage.md`）：待补断言 0、P0 缺口 0、弱候选 0、仅文件级 0；505 条均有明确结论（人工复核确认 185、部分覆盖 22、断言名候选 77、人工语义别名 106、关键词别名 89、N/A 23、已知缺口 3）。新增 `check_lesson10_scenario_gaps.py`（19 条）、`check_markdown_blanks.cjs`（9 条）、`check_mcp_server.py`（14 条）、`check_lesson10_review.py`（27 条）、`check_question_rendering.cjs`（4 条），并在 `check_mcp_tools.py`、`check_question_bank.py`、`check_lessons_2_5.py`、`check_teacher_navigation.cjs`、`check_formula_retrieval.py`、`check_sqlite_storage.py` 增补断言。3 条已知缺口（工具说明注入句式、教师端按班级 AI 提问历史、AI 解答加入错题本）与 22 条部分覆盖均单列，不计入完全覆盖。
6. 检索优化低并发档位：瓶颈档（并发 10）P95 已降 23.8%（达 ≥10%），但并发 3 P95 +7.6%，按分档规则如实记录。

## 五、失败、跳过与未知项去向（任务 3.5）

| 项 | 状态 | 去向 |
| --- | --- | --- |
| npm `next` critical / `postcss` / `source-map-js` high | OPEN（已附不适用论证） | 升级 15.5.28+ 超出“不大修”；课程已接受适用性论证，门禁脚本仍保持 RED 以防回归 |
| 后端镜像 OS 层 Trivy HIGH=51 | OPEN | 不属 Next 范畴，需基础镜像升级维护另立任务 |
| 密钥扫描范围完整=True | PASS（范围） | 运行栈启动后按工作目录自动识别 compose 项目，实扫全部容器日志与前端静态包；容器账本仍 blocked（演示库无四个种子身份） |
| 场景矩阵逐条判定（待补 0，P0 0） | PARTIAL | 待补、P0、弱候选与仅文件级均已清零，505 条都有明确结论；仍有 22 条部分覆盖与 3 条已知缺口（见 `scenario-coverage.md`「人工复核清单」「已知缺口」节），不得宣称完全覆盖 |
| 在线 cases（第 6 轮 24 passed / 1 skipped / 0 failed） | PARTIAL | 第 5 轮 22/3/0；第 6 轮在 compose 网络内运行，3 条 MCP 跳过中 2 条转为通过，剩余 1 条仅因未配置模型 Key 而跳过；见 `online-cases.md` §2.2 |
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
| `lesson-10/20261116T161500Z-docker/*` | 本轮工作区提交内容 | 是（`.source-sha256.json` 与源码哈希一致；镜像随该内容重建） |
| `async-grading/20261116tdocker*` | 同一工作区内容，隔离 compose 项目 | 是（运行前以源码哈希清单核对镜像） |
| `lesson-10/20261116T024000Z-clone-registry-rollback/clone-*` | `984c4c8` 干净导出目录，独立项目/端口 8097 | 是（构建参数 `GIT_SHA=984c4c8`） |
| 同目录 `local-registry.txt` | 同提交三镜像经本机 registry push/pull | 是（digest 与 OCI revision 一致） |
| 同目录 `backup-restore.txt`、`rollback-*` | 演示库临时副本备份恢复 + `37aecf9` 镜像回滚 | 回滚镜像为上一批次；主栈仍为 `984c4c8` |
| `20261116T075000Z-remote-ci/*` | PR #3 合并引用 `2ba142a…`（GitHub checkout 实际 SHA） | 是（远端证据自带该 SHA；不等同本机 HEAD） |

结论：报告按批次标注版本；**不宣称全部证据来自同一提交**。

## 七、四项判定与五个当场动作（任务 10.5）

| 判定/动作 | 本机结果 | 缺失 |
| --- | --- | --- |
| 换人双跑一致 | 未执行 | 第二人 |
| README 新目录启动 | 当前提交 `984c4c8` 在空目录、独立项目/端口 8097 构建并启动通过，七服务 Up、`/health` 与 `/login` 200；在线 cases 24 passed / 1 skipped / 0 failed | 新机/第二人 |
| 线上提交反查 | 未执行 | 线上实例与 CI |
| 60 秒窗口报数 | 0.04 秒完成 | 无 |
| D1 改坏被拦 | 红→修复→绿齐全 | 无 |
| D2 一键启动 | 本机空目录通过（当前提交）；主栈未受影响 | 新机 |
| D3 面板指三技能 | 面板与窗口可用 | 无 |
| D4 异步链路 | 真实代理 15 项 PASS | 手机 |
| D5 压测前后对比 | 已完成（SQL 级 −22.62%；检索热点优化并发 10 瓶颈档 P95 −23.8%，并发 3 +7.6%） | 独立演示现场复跑 |

---

## 八、本机收口追加（2026-11-14，第四节为当时状态，以下为最新）

### 8.1 双门禁与安全判据（5.5）

- 本地与 CI 使用**同一命令**：`make check`、`make check-security`；`.github/workflows/lesson10.yml` 的两个 job 分别执行，`images` job `needs: [check, security]`，无 `continue-on-error`。
- `scripts/check.py --json` 记录每步 `name/status/seconds/exit/finished` 与 `git_head`；`scripts/security_precheck.py` 增加 `course_high_critical`：npm 高危计数直接进入课程判据，pip 有漏洞但无严重度时判 BLOCKED，不折算为 0。
- 本地实测：`make check` **41/41 PASS**（含新增 `check_frontend_image_safety`、`check_lesson10_scenarios`、`check_lesson10_p0_scenarios`、`check_lesson10_scenario_gaps`、`check_markdown_blanks`、`check_mcp_server`、`check_lesson10_review`、`check_question_rendering`）；`make check-security` **RED**，原因为 Next critical 与 5 个未登记 npm 包，容器账本 blocked。

### 8.2 最终镜像内容（6.1）

| 镜像 | .py | .git | 测试文件 | 真实密钥 | 系统 CA | 开发材料 |
| --- | --- | --- | --- | --- | --- | --- |
| backend | **0**（全量 `.pyc`） | 0 | 0 | 0 | 151 个 `/etc/ssl/certs/*.pem` | **已移除**（`dev_seed.py`、`Dockerfile`、`.dockerignore`、`.gitignore`、`.env.example`、`.python-version`） |
| frontend | **0**（已删除基础镜像 npm/gyp 脚本） | 0 | 0 | 0 | 2 | — |
| mcp-tools | **0**（全量 `.pyc`） | 0 | 0 | 0 | 150 | — |

- `.venv/bin` 无 `pip`/`uv`，只有 `python`/`uvicorn` 等运行入口。
- 后端与 MCP 的 Dockerfile 均采用：移除开发材料 → 全量 `compileall -b`（应用 + `.venv` + 标准库）→ 删除所有 `.py` 与 GCC 调试脚本 → `test` 断言计数为 0。
- 实测（2026-11-16 当前提交重建）：backend `py=0 / pyc=2612`，mcp `py=0 / pyc=1598`；两者启动正常，backend `/api/health` 200、登录 200、材料 200、上传 200、索引成功、检索命中；mcp `/health` 200。删除源码前写入 `.source-sha256.json`，可核对镜像与源码一致。
- **`.pyc` 可反编译，不等于代码加密**；详见 `reports/no-source-plan.md`。
- 前端运行层只保留 `node server.js`，已删除基础镜像自带的 npm/node-gyp 与 lldb 脚本，整镜像 `.py=0`、测试文件 0（2026-11-16 实测）。

### 8.3 CI 流水线（7.1 / 7.2 / 7.3 / 7.4）

- `lesson10.yml`：`check` 与 `security` 并列，失败即停；`images` 在两 job 成功后构建三镜像并用 Trivy 扫 `HIGH,CRITICAL`；`GIT_SHA` 同时用于镜像标签与 OCI `revision` 标签。
- 本机按同一命令跑通；远端已在 Draft PR #3 上实跑两次，结果见 8.12：`check` 通过、`security` RED、`images` 跳过。**未取得受控绿版本**，独立 PR 故障重放、线上实例反查仍未执行。
- 10.5 的独立演示清单已备：`reports/demo-checklist.md`（四项判定、五个动作、六份报告、签名模板）。

### 8.4 场景与压测状态更新

- 场景：505 条逐条判定（`reports/scenario-coverage.md`）——**人工复核确认 185 条**、**部分覆盖 22 条**、断言名候选 77、关键词别名 89、人工语义别名 106、**N/A 23（逐条理由）**、**已知缺口 3**、**待补断言 0**（P0 缺口 0）、**弱候选 0、仅文件级 0**。新增 `check_lesson10_scenario_gaps.py`（19 条断言，覆盖上传大小/存储目录/同名重命名/DB 回滚/索引失败/删会话/技能格式/文档默认关闭/MCP 允许清单/下架组卷/手工替换/H4/0 源码镜像入口）、`check_markdown_blanks.cjs`（代码中的下划线 9 条）、`check_mcp_server.py`（非法请求可读与令牌边界 14 条）、`check_lesson10_review.py`（登录/JWT/刷新/注册/CSV/种子/匿名审计/AI 计数/旧权限/原稿指纹/存储元数据/渲染来源/并发同名技能等 27 条）、`check_question_rendering.cjs`（多空位、公式答案、作答横线、学生卷 4 条），并在 `check_mcp_tools.py`、`check_question_bank.py`、`check_lessons_2_5.py`、`check_teacher_navigation.cjs`、`check_formula_retrieval.py`、`check_sqlite_storage.py` 增补断言。已知缺口为工具说明「先读取其他数据并放进参数」句式、教师端按班级查看 AI 提问历史、学生把 AI 解答加入错题本，均不计入覆盖。
- 9.4：检索热点优化后瓶颈档（并发 10）P95 **−23.8%**，并发 3 P95 +7.6%；按项目规则分档记录，不整体宣称通过。

### 8.5 仍然阻塞的事项

1. 安全门禁 RED 的直接计数来源：Next 4 条 critical（当前代码与 Linux standalone 部署下不可触发，见 `reports/next-risk-applicability.md`，课程已接受适用性论证 `reports/course-decisions-2026-11-14.md`）以及 5 个未登记 npm 包；容器账本因无四个种子身份为 blocked。若课程要求按计数归零，仍需升到 15.5.28+ 并处置未登记包。
2. 后端镜像 OS 层 HIGH=51，不属 Next，需基础镜像维护另立任务。
3. 真人、签名、换机、线上反查、课程等价确认，均无法由本机替代；远端 CI 已实跑但为红，见 8.12。

### 8.6 在线用例本机同宿主直连（2026-11-15）

- 环境：本机 `uvicorn`（临时库、端口 8012）+ 本机 pytest，同一文件系统，不经 Docker 挂载卷。
- 前置：`dev_seed` 种子 → 学生 `20260002` 对齐为 `id=3` → `must_change_password=0` → 服务端配置 `MCP_TOKEN_KEY` → 向 class 102 上传并索引一份 `.md`。
- 结果：**22 passed / 3 skipped / 0 failed**。第 4 轮的 `database disk image is malformed`（宿主机直连容器挂载 SQLite）不再出现；3 项 MCP 用例因硬编码 `http://mcp-tools:8090`（仅 compose 网络可解析）跳过，未计入通过。
- 复现步骤与明细见 `reports/online-cases.md` §2.1；本项不改变任务 3.3「未全绿」的定级。

### 8.7 场景补例时发现并修正的实现偏差（2026-11-15）

- `backend/config.py` 的 `enable_docs` 默认值原为 `True`，与主规约 `mcp-tool-integration`「`ENABLE_DOCS` 缺省 MUST 为关闭」及 `README.md`、`DEPLOYMENT.md`、`.env.example`、`docker-compose.yml` 的口径（缺省 `false`）不一致。已改为 `False`，由 `check_lesson10_scenario_gaps.py` 的「默认关闭文档」断言锁定；`.env` 显式写 `ENABLE_DOCS=false`，本地调试仍需显式置 `true`。
- 该改动只影响「未设置环境变量且无 `.env`」的默认值，不改变部署与本地已有配置的取值。
- 其余补例只新增检查，未改动业务代码或断言口径。

### 8.8 弱候选与文件级场景逐条复核（2026-11-16）

- 复核范围：生成器 bigram 匹配留下的全部弱候选（本轮起点 194 条）以及「仅文件级、无断言名」的 17 条；合计 210 条逐条人工判定，另加 1 条由新增断言暴露出的 `teacher-workspace/在助手配置页切换班级`。
- 判定口径不再使用「猜测命中」，每条落到四种结论之一：**确认覆盖**（可指名脚本与断言）、**部分覆盖**（写明未断言部分）、**已知缺口**（功能或断言确实缺失）、**N/A（不适用）**（前端交互、真实模型语义、需容器等，写明理由）。复核结果写入 `scripts/lesson10_scenario_map.py` 的 `REVIEWED` 表，报告的「人工复核清单」一节按能力逐条列出结论、脚本、断言与备注。
- 复核后计数（`reports/scenario-coverage.md`）：505 条 = 人工复核确认 185 + 部分覆盖 22 + 断言名候选 77 + 人工语义别名 106 + 关键词别名 89 + N/A 23 + 已知缺口 3；**待补断言 0、弱候选 0、仅文件级 0**；`reviewed_total 210`、`reviewed_unmatched []`（所有复核键都能对上规约原文标题）。
- 复核过程中补的断言：`apitest/check_lesson10_review.py`（新建时为 26 条，后增「并发同名技能」至 27 条）、`apitest/check_question_rendering.cjs`（4 条，新建）、`check_teacher_navigation.cjs` +3、`check_question_bank.py` 增 3 条边界与无 Key 断言、`check_mcp_tools.py` 增学生写工具拒绝、`check_lessons_2_5.py` 增 `agent.class_switch_reads_and_saves_target`、`check_sqlite_storage.py` 与 `check_formula_retrieval.py` 的断言名改为含模式的 f-string 以便逐模式入册。门禁由 39 项增至 **41 项，全绿**。
- 3 条已知缺口（均如实标注，不计入覆盖）：工具说明「先读取其他数据并放进参数」的注入句式未进注入表；教师端没有按班级查询 AI 提问历史的接口与页面（学情汇总只有提问数）；错题本没有「把 AI 解答加入错题本」的写入接口与页面入口。
- 22 条部分覆盖的典型差异：教师发起 AI 提问被拒的文案为「仅学生可执行该操作」而非规约的「AI 提问仅限学生发起」；重置接口对非班主任返回 404 而非 403；教师学科取自数据库当前值而非 JWT 载荷。

### 8.9 Docker 可用后的本机复验（2026-11-16）

- 以分支最新提交重建三个业务镜像并重建栈（含 observability profile），实际运行 **11 个容器**：nginx、backend、frontend、mcp-tools、rabbitmq、grading-worker、grading-dispatcher、collector、prometheus、alertmanager、grafana。核心七服务 Up，backend/frontend/mcp-tools/rabbitmq healthy；`/health`、`/api/health`、`/login` 均 200。
- 容器内 0 源码：backend `py=0 / pyc=2612`，mcp-tools `py=0 / pyc=1598`，frontend `py=0`（删除基础镜像自带的 npm/node-gyp 与 lldb 脚本，测试文件同为 0）。三镜像 OCI `revision` 与当前提交一致。
- 发现并修复真实部署缺陷：grading-worker/dispatcher 原命令按脚本路径执行 `grading_worker.py`，在 0 源码运行层会立即退出；已改为 `python -m grading_worker`，并加静态断言防回归。另在构建期写入 `.source-sha256.json`，让异步复现脚本可核对镜像与源码。
- 真实 RabbitMQ 异步复现（隔离 compose 项目、临时库、合成账号、假模型、无教学数据）：**15 项 PASS**，含 A1、B1/B2/B4、Q1、C1、D1/D2、F1；证据 `reports/async-grading/20261116tdockerreal-broker-result.json`。
- 在线用例在 compose 网络内运行（一次运行器容器 + 隔离后端 + Docker 命名卷）：**24 passed / 1 skipped / 0 failed**。此前 3 条 MCP 跳过中 2 条通过；唯一跳过为未配置模型 Key 时的「模型提议工具 → ok 审计」，不计入通过。见 `reports/online-cases.md` §2.2。
- nginx 入口 smoke：学生提交 200、教师触发初批 202、任务 pending→retrying→dead（模型未配置，属预期降级）、本人结果 200、跨班材料 404、本班 200。证据 `reports/lesson-10/20261116T161500Z-docker/smoke.json`。
- 观测链路复验：collector `/metrics` 200 且有技能/批改/HTTP 指标，Prometheus target `campusclaw-collector=up`，两条告警规则已加载，Alertmanager ready。证据同批 `observability.txt`。
- 仍然不能由本机替代：真实人参与签名、换机、镜像仓库 digest、线上实例反查；真实模型工具审计需有效模型 Key。远端 CI 已于同日实跑（见 8.12），但为红。

### 8.10 容器 0 源码与安全预检补口（2026-11-16）

- 前端镜像此前残留的 59 个 `.py` 来自基础镜像 `node:22-alpine` 自带的 npm/node-gyp 与 lldb 脚本，不是业务构建产物。运行层已改为只保留 `node server.js`，删除 `/usr/local/lib/node_modules`、`lldb_commands.py` 及 npm/npx/corepack 入口，并在构建期断言整镜像 `.py` 为 0。实测 frontend `py=0`、测试文件 0，`/login` 仍 200。三业务镜像至此均为 0 源码。证据 `reports/lesson-10/20261116T161500Z-docker/no-source-final.txt`。
- `scripts/security_precheck.py` 原先把 compose 项目名写死为 `campusclaw-groupv3`，实际项目为 `campusclaw-group`，导致容器日志与前端静态包根本没被扫描。已改为按容器标签中的工作目录自动识别本仓库的 compose 项目；重跑后**密钥扫描范围完整=True、0 命中**。`make check-security` 仍为 RED 的原因是 Next 版本计数；`has_blocked_scope` 仍为真仅因演示库没有四个种子身份，与扫描范围无关。证据 `reports/lesson-10/20261116T161500Z-docker/security-scope.txt`。
- 补「并发同名技能」断言：模拟两个请求都通过前置查重，第二次插入撞唯一约束。此前会以数据库异常返回 500；已按 `agent-assistant` 规约「重名 MUST 返回 400」补 `IntegrityError → 400` 映射（新建与改写均覆盖），断言同时确认不新增第二条。`record_call` 审计写失败的注入验证原已存在于 `check_security_gate.py`（回滚、不中断、告警不含异常原文），本轮只更正安全评审表中的过期描述。
- 场景覆盖重生成后计数不变（505 条，弱候选/仅文件级/待补均为 0）。

### 8.11 换目录、本机 registry 与备份回滚演练（2026-11-16）

- **换目录二次启动**：`git archive HEAD` 把当前提交 `984c4c8` 导出到全新空目录，生成独立 `.env`（随机密钥、临时数据目录），使用不同 compose 项目名与端口 8097，执行 `docker compose build` 与 `up -d`。七服务全部 Up，backend/frontend/mcp-tools/rabbitmq healthy；`/health` 200、`/login` 200；三业务镜像容器内 `.py=0`，OCI revision 均为 `984c4c8…`。演练后 `down -v` 并删除临时目录。**这是换目录，不是换机**。
- **本机 registry digest**：本机 `registry:2`（仅监听 `127.0.0.1:5001`）接收三镜像 tag/push/pull，记录 RepoDigest、OCI revision 并复验 `.py=0`；backend `sha256:3275eeec2ffa…`、mcp-tools `sha256:130a84fe2878…`、frontend `sha256:8b5778d9ac1d…`。registry 容器演练后删除。**不替代远端仓库/GHCR**，4.2 仍 BLOCKED。
- **备份恢复与回滚**：对演示库以只读连接 + SQLite online backup API 生成临时备份，恢复副本与备份字节相同、34 表行数一致、`integrity_check=ok`；`backend/uploads/` 9 个文件的源/备份/恢复 manifest 一致。从上一提交 `37aecf9` 导出临时目录，用上一 tag 三镜像与恢复副本在独立项目/端口 8098 启动，七服务 Up、`/health` 与 `/login` 200、`.py=0`、revision 均为 `37aecf9…`，从启动到 health 200 约 26 秒；演练后清理。主栈全程未切换，事后复核仍为 `984c4c8` 且 health 200。真实教学库与上传目录未被修改。
- **边界**：以上均为本机隔离演练，不构成正式发布；受控绿远端 CI（当前 run 为红）、远端镜像仓库、线上反查、另一名组员复核、自动备份保留策略仍缺。详见 `reports/release-rollback.md`，原始证据在 `reports/lesson-10/20261116T024000Z-clone-registry-rollback/`。

### 8.12 GitHub Actions 远端实跑（2026-11-16）

- **范围**：把分支 `deps/upgrade-a-b` 推到 `smrrrrr/CampusClaw-Group`，以 **Draft PR #3**（未合并）触发 `pull_request` 工作流。这是“另一台 Linux 机器”的运行证据，**不是换人**，也不构成 7.2 的受控绿版本。
- **首次 run `43826358847`（head `9618be7`）**：`make check` 在“安装 uv 与 OpenSpec”步骤失败，npm 返回 404：`'@openspec/cli@1.13.1' is not in this registry`。这是工作流配置错误，不是业务代码失败。
- **修复 `fca85f7`**：两处安装命令改为实际存在的 `@fission-ai/openspec@1.13.1`；`apitest/check_lesson10_ops.py` 增加 CI6 静态断言，锁住包名并禁止回退到 `@openspec/cli`。
- **第二次 run `43826707775`（head `fca85f7`，PR 合并引用 `2ba142a…`）**：
  - `make check`：**success**，远端 Ubuntu 上 41 组全部 PASS（`check-summary.txt` 末尾为“门禁全部通过”）。
  - `make check-security`：**failure**（exit 2）。`security-run.json`：`status=RED`、`has_blocked_scope=true`、`secret_leak_detected=false`、`secret_scope_complete=true`；未登记 npm 包 5 个（`katex`、`micromark-extension-math`、`next`、`rehype-katex`、`remark-math`），课程判据 npm high+critical=1。
  - 容器账本 blocked：`accounts-readonly.json` 的 `identities=[]`、`db_path=null`，原因“四个演示身份未全部在本地库中找到”。这与密钥扫描范围无关。
  - `build-and-scan`：**skipped**，因为 `needs: [check, security]` 且 security 未过；**因此远端没有镜像构建、没有 Trivy 扫描、没有镜像 digest**。
- **远端测试栈**：runner 上 backend/frontend/rabbitmq Healthy，nginx、mcp-tools、grading-worker、grading-dispatcher 已启动；随后安全门禁失败，`if: always()` 的清理步骤执行 `docker compose down -v`。`remote-stack.txt` 中一处 `curl: (56) Recv failure` 出现在等待循环，未影响后续步骤结论。
- **证据**：`reports/lesson-10/20261116T075000Z-remote-ci/`（run 元数据、门禁摘要、脱敏安全状态、首次 404 日志、远端栈状态、README）。目录不含 `.env`、令牌、数据库或上传正文。
- **仍未完成**：受控绿版本（要求 security 绿）、远端镜像构建与 digest（4.2）、main required checks（2.4，当前账号 `admin=false, maintain=false`）、线上实例反查（7.3/7.4）。

### 8.13 独立分支故障重放（7.3，2026-11-16）

- 在隔离分支 `ci-fault-replay`（基于 `6690202`）把 `apitest/check_lesson10_ops.py` 的 M2 预期值从 `1` 改为 `2`，提交 `a626a75`，以 Draft PR #4 触发远端运行；验证后关闭 PR 并删除分支。
- 本机 `scripts/check.py`：退出码 **1**，失败项 `check_lesson10_ops`。
- 远端 run `43828237591`：`make check` **failure**（`AssertionError: M2 边界：纯索引迁移不改分块数据`）；`make check-security` failure（与注入无关，正常分支本就 RED）；`build-and-scan` **skipped**，未构建镜像、无 digest。
- **边界**：证明“可逆故障会让远端门禁失败并跳过镜像”，但不能证明“required check 阻止合入”——当前账号 `admin=false, maintain=false`，required checks 未配置（2.4），7.3 仍为部分完成。
- 证据：`reports/lesson-10/20261116T080640Z-ci-fault-replay/`；PR #4 已关闭，`main` 未包含故障提交。
