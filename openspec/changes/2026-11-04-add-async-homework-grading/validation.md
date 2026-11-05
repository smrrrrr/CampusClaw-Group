# 作业AI异步初批验证记录

日期：2026-11-04。用户明确要求在作业AI批改加入异步处理和消息队列，必须可复现并归档证据。先完成proposal/design/specs/tasks与实施前自审，再写代码；没有将课程示例的Go文件、404策略或假定数据直接复制进本项目。

## 实现与边界

教师主动点击初批，原POST改202+任务编号；学生提交不自动调用模型。GradeTask按提交版本唯一，任务行同时充当事务发件箱，持久RabbitMQ只收任务ID。投递器与消费者独立进程，先持久结果再ack；失败有限退避、死信可人工重试，租约防旧执行覆盖。冻结依据、百分制折算、教师终评优先、重交和错题学情规则保留，提示词及模型参数未修改。

前端新增进度与未完成数量、查询错误重试、dead重新排队和刷新恢复；后台结果不得覆盖教师正在编辑的分数/评语；切班后旧轮询失效。Settings集中配置、分层登记、pika依赖锁、Compose与.env.example同步。主规约已同步但变更未归档，原有未提交业务修改保留，不将整个工作区差异都归到本变更。

## Scenario → 检查 → 证据

| Scenario | 实际检查 | 证据 |
| --- | --- | --- |
| A1 正常提交不等待 | 20次202，响应无分数；离线断言无模型调用，真实代理环境比较P95与单次假执行 | offline-result.json A1；real-broker-result.json A1 |
| A2 查询只读与空批次 | 多次GET完整响应/attempts/时间不变；空作业task_ids为空 | offline-result.json A2 |
| A3 参数与资源失败 | 非法ID422、未知资源404、非dead重试409 | offline-result.json A3 |
| B1 消费者停止再启动 | 停止时pending无分数，启动无需重交完成；代理容器重建后持久消息仍在 | real-broker-result.json B1 |
| B2 队列故障后补投 | 故障不标确认；真实停止代理时202持久接收，恢复后补投完成 | offline-result.json B2；real-broker-result.json B2 |
| B3 事务中途失败 | 第二条INSERT故障HTTP503，任务/发件箱整批0，原提交及分数不变 | offline-result.json B3；risk-transaction.md |
| B4 杀进程与旧租约 | 真实SIGKILL后重启恢复；离线旧claim写回被拒绝 | real-broker-result.json B4；offline-result.json B4 |
| C1 并发与重复投递 | 20并发同编号一个任务；再次发布后attempts增，分数/评分结果不变 | real-broker-result.json C1；offline-result.json C1；risk-concurrency.md |
| C2 重交与终评竞态 | 旧结果skipped，保留新答案/教师分；原命题回归继续验证冻结依据与折算 | offline-result.json C2；check_quiz_homework |
| D1 失败、退避与死信 | 三次失败状态/次数/间隔，未到期不执行；死信补投确认及真实死信数量 | offline-result.json D1；real-broker-result.json D1 |
| D2 手动重试 | dead显式202，活跃409，成功保留累计attempts，当前执行周期重置 | offline-result.json D2；real-broker-result.json D2；ui-dead.txt |
| E1 未登录与越权 | 四个接口×未登录/学生/他班/他科，16反例及403审计 | offline-result.json E1；risk-authz.md |
| E2 页面与刷新恢复 | 真浏览器：排队/完成/死信/重新排队、503重试入口、6秒慢查询切班、刷新重开提交；编辑88和评语保留，AI建议70 | ui-normal.txt、ui-dead.txt、ui-query-error.txt、ui-class-switch.txt、ui-reloaded.txt、ui-completed.png |
| F1 可复现与迁移 | 临时旧库无任务表升级两次，旧账号/作答/评分逐行一致；真实进程脚本、JSON日志+request_id；完整门禁 | offline-result.json F1；real-broker-result.json F1；full-check.txt |

表中JSON、UI记录、门禁均在根 `reports/async-grading/`；风险记录在根reports。复跑命令、环境、限制见该目录README，报告用语不将“有脚本”冒充另一机器已经跑过。

## 已执行结果

- 离线异步检查52条通过；模型/网络为替身，临时库隔离。
- 真实RabbitMQ隔离实验13条通过，实际stop/start、SIGKILL、代理容器重建及重复发布。结果包含20次原始响应时间、P95、假模型执行时间、队列长度、最后一次执行耗时、attempts、死信与镜像/源码指纹。
- 原作业30条、命题作业98条检查保留原业务断言，初批契约调整为202后显式驱动测试消费者；没有伪造同步HTTP评分响应。
- 完整门禁23组全部通过；最终记录在reports/async-grading/full-check.txt。失败子项非零仍阻断。
- 页面使用独立3009/8009、合成账号与临时库实际操作，未触碰教学数据；验收进程已停止。
- 新依赖pika 1.3.2为BSD-3-Clause，实际查询PyPI该版本公开漏洞记录为空；dependency-audit.json有时间和来源。只审新增依赖，不冒称全项目漏洞扫描通过。

## 失败记录及检查有效性

1. 首次A1检查发现重复请求逐份查询，机器抖动时P95超过200ms假执行。改为整批预读已有任务和冻结依据，保持原阈值，复跑通过；没有放宽测试。
2. 首次真实代理探针用root运行诊断工具，抢先生成root拥有的内部cookie导致服务不能启动。改为rabbitmq用户探测；新空测试卷复跑通过。最初FAIL记录保留在first-broker-start-failure.json。隔离初始化还补了显式PYTHONPATH；这些不是业务通过结果。
3. 故意临时移除“写回必须pending”的保护，C2教师终评场景失败；恢复原字节并比较SHA256相同，随后重新跑离线和完整门禁通过。mutation-red.json存具体失败名和红态输出。
4. 构建镜像内关键源码与工作区指纹逐项比对，拒绝用旧镜像冒充当前代码。代理固定digest和节点名，并额外验证重建容器后的队列持久性。

## 本机数据与更新

初始备份在data/current/before-async-grading-20261104-171242.db，integrity_check为ok。更新前再次通过SQLite backup API备份数据库及完整31个上传文件，位置在 `.review/async-predeploy-20261104-175655/`，另记旧容器镜像ID用于回滚；这些私有文件不入Git。

只更新campusclaw-groupv3/8083，新增代理、投递器、消费者共7个服务。更新后health正常、队列可连接；34张旧表内容指纹和31个文件指纹均与更新前相同，新grade_tasks为0，数据库完整性ok。没有执行真实学生批改或真实模型调用；其余三套Compose仍运行。实测见local-deployment.json。

## 完成定义与尚未执行

| 完成定义 | 实施者自检结论 |
| --- | --- |
| 每个Scenario有对应检查 | 满足上述映射；E2为实际浏览器检查，未声称所有页面尺寸自动回归已覆盖 |
| 完整门禁 | 满足，23组PASS，见full-check.txt |
| 提示词评测 | 本次未改提示词/模型参数，不适用；真实模型质量与费用未验 |
| README/主规约/规范/模型注释 | 已同步；根reports和新检查可入库，.env/数据库/临时配置仍忽略 |
| 验证归档 | 已放根reports及本文件，包含真实失败和红绿记录 |

未执行：另一组员/另一机器复现、人工交叉评审、外网演示、正式提交与发布标签、OpenSpec归档。tasks勾选按项目未经明确指示不修改的规则保留，实际实施状态以本记录为准。当前是本机已实施验证，不代表第11课完整交付或已获合并批准；正式合并前仍须另一名组员复核。

## 后续：用户现场反馈看不到“已有任务”提示

实际检查了用户正在使用的极速浏览器：提示在页面顶部一行灰字，用户截图所在作业卡片处看不到，长文案还会截断。此前仅凭源码告诉用户向上找，没有核实可见性，不能把这种反馈当作可用。现将成功/复用/失败回执按homework_id放入当前卡片，明确编号，正常换行；查看提交与轮询同步submitted_count，保留上下文保护和教师编辑保护。

| 新场景 | 验证 | 证据（reports/async-grading） |
| --- | --- | --- |
| E3 同一卡片显示回执 | 新建、复用、混合、空批次固定输入输出；AST核对反馈属于作业卡片；实际合成作业连续点击两次，第二次显示复用#1；503在同卡片显示 | ui-feedback-checks.txt、ui-feedback-duplicate.txt/png、ui-feedback-error.txt |
| E4 提交人数同步 | 只更新目标行且不修改原数组；页面先加载0/1，再向隔离库加入提交，点击查看提交实际变为1/1 | ui-count-before.txt、ui-count-after.txt |
| 检查有效性 | 暂时把所有回执编号写成#999，新检查失败；恢复原字节后8项通过 | ui-feedback-red-green.json |
| 完整回归 | 在最终界面代码上24组PASS（新增check_grading_feedback），类型及原52项异步检查仍通过 | ui-feedback-full-check.txt |
| 用户实验现场保留 | 仅重建/更新frontend并重启nginx刷新上游；worker在更新前后均exited且StartedAt相同，真实任务仍#1、pending、attempts=0，任务快照完全相同 | ui-feedback-deployment.json |

本轮没有点击真实8083的AI初批，没有恢复用户暂停的消费者，没有调用真实模型，没有修改真实提交/成绩或归档变更。实际页面检查使用独立3009/8009合成数据，验收后停止对应进程。本节结果为首次异步上线之后的补充，不把旧23组记录改成24组冒充同次执行。
