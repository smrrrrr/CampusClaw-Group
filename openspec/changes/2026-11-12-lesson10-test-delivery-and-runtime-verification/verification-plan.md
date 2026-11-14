# 第10课逐项覆盖与验证计划

依据：用户本轮给出的第10课完整原始清单。表中“已有”仅指已读到文件/实现，不代表本轮运行通过；“需新增”指后续实施，“需确认”决定课程等价接受性或外部条件，未落实为阻塞。Golang语法示例对FastAPI不适用，但对应功能判据仍适用；其余课程要求不因技术栈差异擅自标不适用。

本轮只更新四份规划文档，所有执行结果均为**未执行**。文件与命令均是计划，不伪造测试通过。已知合同差异、指标和分工见 [design.md](design.md)，任务见 [tasks.md](tasks.md)。

## 一、逐项覆盖表

所有证据路径相对仓库根；`reports/lesson-10/<run-id>/` 是后续按实际日期创建的独立批次。任务号是tasks.md中的编号，并非课程编号。

### 总要求与四项判定

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 总要求 | 已有部分／需新增 | 根report.md、reports总索引、单一CI流水线 | 从每课判据追到同一版本流水线和根reports证据；正文仅结论/索引 | report.md；reports/lesson10-delivery.md；reports/pipeline.md | 1.1、4.1、7.1 |
| 判定-可重复 | 需新增 | 换人、同命令两次记录 | 同SHA/锁/数据/参数下断言、退出码和关键状态一致，允许时间/临时名不同 | reports/lesson10-delivery.md；reports/lesson-10/<run-id>/repeat/ | 10.1 |
| 判定-环境完整 | 已有启动资料／需新增实测 | README从零步骤与新目录/新机复现 | 无口头补充，完整前置后compose up -d服务就绪；换目录不冒充换机 | reports/boot-reproduce.md | 2.3、10.2 |
| 判定-版本追溯 | 已有版本号／需新增SHA链 | 提交镜像标签、OCI revision、部署清单 | 线上URL→实际digest→CI run→实际checkout SHA可反查，dirty快照不可交付 | reports/pipeline.md | 6.3、7.4 |
| 判定-状态可见 | 需新增／事件规约待确认 | 三技能时间窗查询与面板 | 指定UTC窗口后三技能调用量/失败率60秒内可报，数据新鲜且可反算 | reports/observe-alert.md；reports/lesson-10/<run-id>/window/ | 8.1～8.4 |

### 1 开工前资产盘点

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 1.1 | 已有命令／需新增盘点 | command-inventory逐命令时间表 | 包含双门禁、全部子检查、异步A/B/C、构建/在线/探针；最近可核实时间有来源，未知不造时间 | reports/command-inventory.md | 1.3、10.1 |
| 1.2 | 已有分散映射／需新增全量 | 按现行规约Scenario的全量矩阵 | 每Scenario至少一用例；统计总数/已覆盖/空项，空项优先补，矛盾先澄清 | reports/scenario-matrix.md | 1.2、5.3 |
| 1.3 | 四项有实现资产／需新增充分用例 | 四项技能正常/反例与语义抽查表 | 引导不给最终答案、终评优先、错题不贴标准答案、跨班检索空，四项分别有判据 | reports/scenario-matrix.md；reports/lesson-10/<run-id>/skills/ | 5.3 |
| 1.4 | 需确认人员／需新增分工 | A测试、B容器CI、C观测压测职责表 | 每段负责人/交叉验收人/发现与结论齐全，无自签代替交叉验收 | reports/lesson10-delivery.md | 5.1 |

### 2 测试收口与门禁

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 2.1 | 已有cases/check／需新增补例 | apitest/cases、现有check单元、合成夹具 | 新反例入套件；临时库/秒级假模型；不把真实模型语义用固定假响应证明 | reports/scenario-matrix.md；reports/lesson-10/<run-id>/tests/ | 3.3、5.3 |
| 2.2 | 双命令已有／需新增全量聚合与严格判据 | 同命令本地/CI双门禁 | 接口/单元全量check；安全反例security；两命令0且高危/critical实际0、范围完整；未知严重度阻塞 | reports/pipeline.md；reports/lesson-10/<run-id>/gates/ | 2.2、5.5、7.1 |
| 2.3 | 已有子项红绿／需新增完整链路 | 故障注入、修复SHA、完整双门禁红绿 | 改坏位置、红屏及非0、真实修复提交、绿屏及0四要素；能当场复跑 | reports/gate-red-green.md | 5.4 |
| 2.4 | 规则已有／远端保护需确认 | 准入流程与required checks配置记录 | AI初稿→自审→双门禁→人工确认→交评→main，未绿/未审批不能合入 | reports/pipeline.md；reports/lesson10-delivery.md | 5.6 |

### 3 容器化

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 3.1 | 前端已有／后端MCP需新增／无源码待确认 | 多阶段Dockerfile与实际镜像扫描 | 运行层无构建工具/密钥/开发材料；Python必要源码例外未获确认不能判绝对无源码通过 | reports/boot-reproduce.md；reports/lesson-10/<run-id>/image-scan/ | 6.1 |
| 3.2 | 已有七服务等价／强制换栈需确认 | SQLite/FastAPI/库内向量及健康依赖说明 | SQLite读就绪、队列service_healthy；不靠wait循环；不能用空MySQL/Qdrant凑三服务 | reports/boot-reproduce.md | 6.2 |
| 3.3 | 已有历史启动／需新增复现 | 新目录和尽可能新机器启动记录 | README前置齐、compose up -d全服务就绪，无口头补步骤，记录实际系统/人/时间 | reports/boot-reproduce.md | 10.2 |
| 3.4 | 需新增 | 构建SHA标签与OCI revision规范 | 最终镜像实际revision等于构建checkout SHA并有digest，不只用latest或应用1.2.0 | reports/pipeline.md | 6.3 |

### 4 流水线

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 4.1 | 未发现workflow／需新增 | 单一GitHub Actions及隔离测试环境 | 检出→同命令双门禁→两者绿才构建，失败也上传脱敏证据 | reports/pipeline.md；reports/lesson-10/<run-id>/ci/ | 7.1 |
| 4.2 | 需确认远端权限／需新增实测 | 一次受控push及CI镜像反查 | push SHA/run编号/digest可对应，不能拿本机构建日志冒充远端 | reports/pipeline.md | 7.2、7.4 |
| 4.3 | 已有迁移惯例／改进方案待测 | SQLite索引扩/迁及兼容复验说明 | 只扩兼容索引、两次迁移幂等、数据不变；本课不缩，纯索引无搬数据则如实说明 | reports/bench.md；reports/lesson-10/<run-id>/migration/ | 6.4、9.3 |
| 4.4 | 已有DB健康／持续摘流需补设计 | 发布前就绪与DB故障演练 | DB不可读503且新实例不接流量；Compose启动依赖不冒充运行期自动摘流 | reports/boot-reproduce.md；reports/lesson-10/<run-id>/readiness/ | 3.1、6.2 |

### 5 观测

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 5.1 | 七列部分已有／三技能统一事件需新增 | 指标/事件字典、采集器及规则 | skill_invocations_total带skill/status；七列真实可追；失败率面板计算，缺数据不填0 | reports/observe-alert.md；reports/lesson-10/<run-id>/metrics/ | 8.1、8.2 |
| 5.2 | 需新增 | 三panel面板配置 | 三技能调用分线、每技能失败率、完整接口P95与队列ready/unacked并排，单位/分母清楚 | reports/observe-alert.md；reports/lesson-10/<run-id>/dashboard/ | 8.3、8.4 |
| 5.3 | 需新增／接收人待确认 | 告警规则、负责人/通道/面板链接 | 观察量+窗口/持续条件+动作齐全；建议5分钟错误率>1%且样本≥20持续5分钟 | reports/observe-alert.md | 8.5 |
| 5.4 | 需新增真实演练／通知条件阻塞 | 连续失败、Firing与实际收信记录 | 独立假模型持续失败，Firing后60秒内收信并含面板；拒绝率告警不能冒充执行错误率 | reports/observe-alert.md；reports/lesson-10/<run-id>/alert/ | 8.6 |

### 6 压测、改进与真实用户

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 6.1 | 已有H5/API资产／字面202角色合同待确认 | 手机角色分步异步与跨班验收 | 学生200→教师202/task_ids并查询三态→学生本人结果→别班讲义404；七列成功/拒绝覆盖另验 | reports/boot-reproduce.md；reports/lesson-10/<run-id>/h5/ | 3.2、8.1 |
| 6.2 | 需新增／真实使用者待确认 | 至少3人真实反馈及去向 | 每人一条脱敏会话/关联ID、接口、返回、期望差异；转任务或说明不做，新坑入套件 | reports/feedback.md | 9.5 |
| 6.3 | 已有小样本耗时／需新增三接口负载 | k6脚本、参数、三接口分档曲线 | 提交接收/查询/检索分别测吞吐/P95/错误率；标观测饱和点，批改执行吞吐另测 | reports/bench.md；reports/lesson-10/<run-id>/load-before/ | 9.1、9.2 |
| 6.4 | 需新增至少一项改进／收益待测 | 有EXPLAIN依据的最小索引及同参复测 | 前后提交/脚本/参数/数据可对齐；三数与瓶颈归因齐，至少一项真实有效，失败不免做 | reports/bench.md；reports/lesson-10/<run-id>/load-after/ | 9.3、9.4 |

### 7 提交前核查

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 7.1 | 已有入口/部分证据／需新增本课结果 | 双门禁全量与红绿四项 | 两命令并列全量且0、高危0，完整门禁能检出故障；无前置不能当绿 | reports/gate-red-green.md；reports/pipeline.md | 2.2、5.4、5.5 |
| 7.2 | 已有Docker/Compose／无源码待确认 | 干净目录启动与镜像内容证据 | compose up -d就绪且镜像无密钥；源码字面冲突未确认则此项不通过 | reports/boot-reproduce.md | 6.1、10.2 |
| 7.3 | 需新增／远端条件待确认 | 绿提交构建与红提交拦截 | 镜像反查成立；同故障本地非0、受控PR线上必失败且不产可交付镜像 | reports/pipeline.md | 7.2、7.3 |
| 7.4 | 需新增／第三图等价需确认 | 三技能面板及至少一次真告警 | 三技能接口P95并列、队列仅批改；不虚构另两技能队列，组合是否满足每图三技能须确认；通知实际送达 | reports/observe-alert.md | 8.4～8.6 |
| 7.5 | 需新增 | 两轮三数、改进归因、3人反馈 | 同脚本同参复测收益成立，反馈均有去向；无真实用户不拿合成用户替代 | reports/bench.md；reports/feedback.md | 9.2～9.5 |
| 7.6 | AGENTS/规范已有／Cursor需新增 | 七类核查责任表及Harness入口 | 七类各标AI/脚本/人工，AGENTS单一总纲，Cursor引用；新会话实读有证据 | reports/lesson10-delivery.md；reports/lesson-10/<run-id>/harness/ | 4.3 |
| 7.7 | 3评审/3风险报告已有／需追加当次交评 | 3份四要素审核、高风险三查、另一人最终四步 | 至少2份来自AI/门禁实际发现；人从新目录完整走四判定，返回码差异记展示前待修 | reports/review-01.md～03；reports/risk-concurrency.md、risk-transaction.md、risk-authz.md；reports/lesson10-delivery.md | 4.2、10.3～10.5 |

### 四项必做技能细化

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| 1.3a 引导 | 已有框架/检查／需补语义反例 | 直接索取答案/注入/追问样本 | 只提示与引导；真实模型抽查独立记录，固定假输出不证明语义 | reports/scenario-matrix.md；reports/lesson-10/<run-id>/skills/tutor/ | 5.3 |
| 1.3b 终评 | 已有C2／需复验 | 终评/重交竞态与mutation | 旧AI任务不覆盖终评/新提交，改坏保护时检查必须红 | reports/gate-red-green.md；reports/lesson-10/<run-id>/skills/grading/ | 3.4、5.4 |
| 1.3c 错题 | 已有提示/接口／需补防答案反例 | 本人解释、私有评分不入输入与拒绝样本 | 不贴标准答案、不泄露他人错题，模型不可用不报生成成功 | reports/scenario-matrix.md；reports/lesson-10/<run-id>/skills/mistake/ | 5.3 |
| 1.3d 跨班 | 已有检索隔离／需复验 | A有来源/B空引用与别班下载 | 他班独有知识空引用、无他班正文；下载404，结果归属服务端判定 | reports/scenario-matrix.md；reports/risk-authz.md | 5.3、10.4 |

### apply页必交证据

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| A1 gate-red-green | 已有历史子项／需补 | reports/gate-red-green.md | 故障位置、红非0、修复SHA、完整绿0齐全且可复跑 | reports/gate-red-green.md | 5.4 |
| A2 boot-reproduce | 需新增 | reports/boot-reproduce.md | 换目录启动、实际镜像检查、手机与就绪、独立操作者证据齐 | reports/boot-reproduce.md | 10.2 |
| A3 pipeline | 需新增 | reports/pipeline.md | 真实CI编号/提交/digest、双门禁、红提交阻断、主干保护 | reports/pipeline.md | 7.1～7.4 |
| A4 observe-alert | 需新增 | reports/observe-alert.md | 口径/三panel/时间窗报数/真告警送达完整 | reports/observe-alert.md | 8.1～8.6 |
| A5 bench | 已有历史／需补本课两轮 | reports/bench.md | 三接口曲线、同参前后吞吐/P95/错误率、归因与改进SHA | reports/bench.md | 9.1～9.4 |
| A6 feedback | 需新增／用户阻塞 | reports/feedback.md | 3名真实使用者每人一条，均有任务或不做理由 | reports/feedback.md | 9.5 |

### 五个当场动作

| 条目 | 本项目现状 | 拟交付物 | 验收判据 | 证据位置 | 任务 |
| --- | --- | --- | --- | --- | --- |
| D1 改坏被拦 | 已有历史／需新现场证据 | 完整门禁mutation演示 | 独立副本改坏使门禁非0，恢复后两命令0，不改main | reports/gate-red-green.md；reports/lesson10-delivery.md | 10.5 |
| D2 一键启动 | 已有资产／需现场复现 | 新目录docker compose up -d | 所有前置在README，无额外口头步骤，全服务就绪 | reports/boot-reproduce.md；reports/lesson10-delivery.md | 10.5 |
| D3 打开面板 | 需新增 | 指定窗口指认三技能调用量 | 三个真实技能分线、错误率可报，操作开始60秒内完成，不用伪造数据 | reports/observe-alert.md；reports/lesson10-delivery.md | 10.5 |
| D4 异步链路 | 已有／角色等价待确认 | H5角色分步与真实队列轨迹 | 教师202、任务三态、旧结果不覆盖、跨班404；学生提交仍200，差异明示 | reports/boot-reproduce.md；reports/lesson10-delivery.md | 10.5 |
| D5 压测对比 | 需新增 | 同参前后三数/曲线现场展示 | 指明瓶颈、至少一项改进SHA和收益，不能只展示历史20次耗时 | reports/bench.md；reports/lesson10-delivery.md | 10.5 |

## 二、命令盘点计划与已查时间依据

后续command-inventory必须逐条列出实际命令、作用/Scenario、前置、隔离/写入范围、预期退出码、上次可核实执行起止时间与时区、源码版本、证据及本次结果。对所有顶层check脚本逐项建行，不能只写一个glob或总组数；真实模型/网络项另列，尚无记录填未知。本轮不执行这些命令，也不把文件mtime当执行时间。

| 入口 | 命令/适用层 | 已读到的时间证据与限制 |
| --- | --- | --- |
| 全量门禁 | make check；Windows为backend对应Python运行scripts/check.py | review-02/03与提交报告有历史记录，原始日志是否含精确时间逐条核实；不得沿用28组等旧数 |
| 安全门禁 | make check-security；对应Python运行scripts/security_precheck.py | review-fix-security-run.json：2026-11-12T07:48:36.874058Z开始，07:49:11.789305Z结束，exit1/RED；不冒充本轮结果或绝对最近一次 |
| 异步三判据 | 对应Python scripts/reproduce_async_grading.py --image campusclaw-lesson10-<run-id>:local --output-prefix lesson10-<run-id>- | history-real-broker-result.json：2026-11-04T13:02:54.874595Z至13:04:25.486911Z，历史PASS；A提交不等/B恢复/C幂等共用该脚本及分项结果 |
| 每个离线子检查 | scripts/check.py按当次文件清单收集apitest/check_*.py与check_*.cjs，单跑用对应Python/Node并配置隔离环境 | 每条查其原始运行记录，找不到写未知；不能凭同目录另一个脚本时间补齐 |
| 在线接口 | 对应Python apitest/run_all.py | 先核APITEST_BASE_URL/DB_PATH/固定身份/已索引材料/ENABLE_DOCS/HTML插件；生成apitest/reports/report.html后脱敏归档reports，不拿默认历史DB路径运行 |
| 安全及模型探针 | probe_security_precheck.py、probe_tutor_guidance.py等实际发现的probe入口 | 分别登记默认替身/真实模型参数及写入/费用；review-fix-mutation.json时间为2026-11-12T07:47:51.165954Z，只代表该记录 |
| Compose与就绪 | docker compose config --quiet；构建/启动；ps；入口GET /health与/login | 项目名/端口/数据目录由独立环境确定，旧8081/8083/8084不可照抄；精确执行时间待盘点 |
| 本课新增命令 | CI同命令、镜像反查/扫描、面板报数、告警演练、k6、索引迁移复验 | 尚未实施，无上次执行时间；新建后纳入同一命令表，不填虚构日期 |

单跑子检查不能只复制门禁里显示的脚本名而漏掉其测试JWT/模型隔离前置；现有安全脚本会覆盖固定目录，必须先保全历史证据并在隔离副本运行。未来CI两job写不同工作区，最终收集到同一run-id清单，不覆盖彼此结果。

## 三、可重复、性能与模型验证的执行协议

1. 另一个人固定交付SHA、锁文件、合成数据、环境变量参数与测试替身，连续执行同一命令两次；比较断言、返回码、计数及副作用，不要求随机ID、时间戳、性能浮点数相等。与初始执行者的结果差异亦留证。
2. make check与make check-security两条必须全量，本轮只做规划结构校验；真实模型质量、真实代理、手机浏览器、远端CI分别记录。未配置模型的假输出不能证明“不给答案”的真实遵从。
3. 压测前后脚本SHA/参数/数据/硬件/模型/worker/冷热策略相同，并发1/5/10/20/40建议每档预热10秒采样60秒，逐档至少两轮。报成功吞吐、完整请求P95、错误率及样本量；接收与消费者执行吞吐分开。若范围内未饱和如实说明。
4. 优化是本课必做，先EXPLAIN和资源证据找缺失索引。无收益则6.4未完成；缓存备选须先有隔离/失效规约。建议收益目标为瓶颈档P95降≥10%、成功吞吐不降、错误率不增，属待评审项目判据，不伪称课程给定指标。
5. 告警要真实进入Firing并送达，不只手工调用通知测试接口。记录失败注入/样本、窗口和持续条件、Firing/发送/收信/恢复时间、面板链接；无人接收或未授权通道则阻塞。
6. 最终四步按四项判定准备，由另一人从新目录独立执行；五个现场动作另做演示，两者不互抵，四步定义仍待课程确认。

## 四、结果、证据与停止条件

- 资产状态与验证结果分列。结果仅能为待执行、PASS、FAIL、BLOCKED、SKIP、N/A、历史引用；N/A需说明适用性依据，SKIP不算PASS，未知严重度不当高危0。
- 每份证据至少有run-id、操作者/角色、开始结束及UTC、OS/工具/锁文件版本、提交和工作区差异、环境/镜像digest、完整脱敏命令、预期、实测、数量单位、退出码、原始输出路径。
- gate-red-green四要素、boot实际启动、pipeline真实远端编号、observe实际面板/收信、bench两轮三数、feedback真人三条任一缺失，均不能用模板/其他绿项替代。
- 线上行为和规约不符、七列缺字段、指标缺源、无法确认数据归属、镜像字面无源码未获确认、课程技术栈/H5等价未认可、通知或远端权限不足，应标明具体阻塞范围，不能自行作豁免。
- reports不保存.env、密钥/令牌、真实作答正文/私有标准答案、数据库、完整私有Compose展开值；私有排错材料留忽略目录，公开证据脱敏，真实用户会话标识去标识化。
- 只有两门禁绿、每个必验项/Scenario有证据、等价决定获认可、缺陷去向明确及人工交叉评审完成后，才可申请交付/合并；本轮不触发这些动作。

## 五、本轮规划更新自检

本次仅核对四份文件的一致性、全清单覆盖、任务全部未勾选、已有文件/链接和修改边界，运行本change的OpenSpec严格校验；不会运行make、CI、容器、故障、模型、压测或通知。上一轮planning-validation.md保持原样，其14任务/旧校验为历史快照；本次校验结果以交付回复及实际CLI输出为准。skip_specs不免除后续应用事件/就绪/索引行为所需的业务规约与评审。

2026-11-12本轮已执行的规划检查：OpenSpec严格校验退出0；结构检查确认47个必覆盖条目与4个技能子项、44项任务（新增30项）全部未勾选、内部链接存在；600个会话前文件的内容指纹对比只有指定四份Markdown改变，其余596个未变，无新增/删除文件。这里的通过仅限规划结构，不是课程运行验收PASS。
