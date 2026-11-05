# 作业AI初批：怎么用、怎么复现

教师进入“作业与改分”，选班级和作业，点击“AI 初批”。系统立即受理；“查看提交”中显示后台批改进度。可以离开页面，稍后重新打开“查看提交”恢复记录。任务最终失败时显示原因，检查模型配置后可点“重新排队”。AI仍只给建议，教师负责确认最终成绩。

**界面回执修正：** 初批提示现已显示在对应作业卡片内，重复点击明确显示“没有新建任务。已复用任务 #编号”。不再依赖页面顶部灰字。实际重复点击截图见 [ui-feedback-duplicate.png](ui-feedback-duplicate.png)，失败反馈见 [ui-feedback-error.txt](ui-feedback-error.txt)，人数同步见 [提交前](ui-count-before.txt)/[查看提交后](ui-count-after.txt)。本次24组门禁见 [ui-feedback-full-check.txt](ui-feedback-full-check.txt)，更新时保持用户暂停的消费者和待执行任务原状，见 [更新记录](ui-feedback-deployment.json)。首次异步上线的23组记录保留为历史结果。

## 1. 已实现的边界

**2026-11-04 当前修正：** 已确认的排队消息不再每30秒重投；教师进度显示“批改尝试”，保留原消息累计数作为审计。学生增加作业历史，教师终评及格后同步清理该作业错题。完整步骤与证据见[当前报告](../assignment-history-2026-11-04.md)。上方“更新时保持暂停”描述的是前次界面修正，当前8083部署的消费者正在运行，见[当前部署核对](history-deployment.json)。

- 手工作业、智能命题作业共用后台流程；不自动批改学生刚提交的作业。
- 原初批POST返回202和任务编号，不再等模型执行，不再同步返回评分数量。
- 一份提交版本一个任务；重复点击和重复投递不重复生效。
- 独立投递器从数据库补投；独立消费者按份执行，数据库提交后确认消息。
- 默认最多执行3次，失败间隔5秒、10秒，最后进入死信；中断的运行任务在默认180秒租约到期后可重领，实际恢复还受投递轮询和排队影响。
- 教师终评、学生重交之后，旧批改不能覆盖新状态。模型超时仍为原配置，提示词未改。
- 任务列表显示最近200条；死信队列保留历史编号，人工重试成功不会自动抹掉历史死信。

## 2. 启动应用

按根README安装/启动。已有.env再添加 `.env.example` 的队列配置，尤其是随机 `GRADING_BROKER_PASSWORD`；不要把真实值写进命令或提交。RabbitMQ只在Docker内部访问，镜像固定digest，数据使用命名卷；节点名固定，容器重建仍使用同一持久数据。探针以rabbitmq用户运行。

```text
docker compose up -d --build
docker compose ps
```

当前这台机器已有多套项目，更新本组使用 `docker compose -p campusclaw-groupv3 ...`，入口为8083；不能按旧说明中的8081操作其他部署。新机器使用其自己的项目名、端口和数据目录。

## 3. 一条命令复现三条判据

前提：Docker Desktop/Linux Docker可用，后端按锁安装依赖；首次需联网取得镜像。全部命令从仓库根目录运行。

Windows：

```text
backend\.venv\Scripts\python.exe scripts\reproduce_async_grading.py
```

macOS/Linux：

```text
backend/.venv/bin/python scripts/reproduce_async_grading.py
```

脚本自动构建本次后端镜像；建立随机命名的Compose项目、空临时数据库、合成账号和本地HTTP假模型；启动真实RabbitMQ、投递器和消费者，实际执行stop/start、SIGKILL和重投。脚本退出只清理自己创建的容器/命名卷，不操作现有项目；私有临时文件留在被忽略的.review供排错。

已构建且源码指纹一致时，可加 `--skip-build`；脚本会比对镜像内关键源码，旧镜像会失败。可用 `--image <独立测试镜像名>` 指定构建名称。脚本任一断言失败即非零退出，不将失败改成PASS。

| 判据 | 自动做什么 | 通过信号 |
| --- | --- | --- |
| 提交不等待 | 消费者未启动，连续20次POST，测每次耗时及P95；另测一次200ms假模型 | 全部202、响应无评分、P95小于假模型执行时间，重复编号一致 |
| 中断不丢任务 | 停消费者后提交，再启动；还会杀死执行中的消费者，以及重建代理容器 | 不重交即可完成；运行中断后attempts增加；代理卷里的消息仍在 |
| 重复不重复生效 | 同一提交20次并发、成功后重复发布同一消息 | 一个任务；attempts增加，但分数和提交结果不变 |

另外验证代理故障补投、3次失败死信、人工重试恢复、JSON任务日志及request_id；暂停消费者32秒，确认20条消息仍为20条。本次运行加 `--output-prefix history-`，得到14项通过的 [history-real-broker-result.json](history-real-broker-result.json) 和 [history-worker-events.json](history-worker-events.json)，含时间、镜像ID、代理digest、命令、源码指纹与实测指标。原 [real-broker-result.json](real-broker-result.json) 和 [worker-events.json](worker-events.json) 是前次历史证据；默认不加前缀重跑会覆盖默认文件。

**测量范围：** 真实消息代理 + 本地假模型，不证明真实DeepSeek耗时、准确率、费用或外网性能。本次数据与结论以JSON实际status/时间为准；重跑会更新当前结果，正式提交前可另留副本。

为了缩短故障复现，隔离脚本使用9秒租约、0.2/0.4秒退避、0.1秒轮询和3秒模型超时；这些不是应用默认值。默认应用是180秒租约、5/10秒退避、1秒轮询、原60秒模型超时。最大执行次数均为3。已删除 `GRADING_REPUBLISH_SECONDS`：未确认消息可以补投，同一次过期租约最多确认一条恢复消息，正常暂停消费者不触发重复发布。

## 4. 离线回归和故障检查

```text
Windows:      backend\.venv\Scripts\python.exe scripts\check.py
macOS/Linux:  make check
```

完整门禁自动收集 `apitest/check_async_grading.py`：临时库、假模型、队列替身，覆盖正常/失败/边界、20并发、原子回滚、旧租约、重交/终评、只读查询、权限审计、有限退避、死信补投和旧库迁移。模型、代理真实进程的启停另由上一节脚本复现，不冒称离线检查使用了真实代理。

原30条作业、98条命题作业断言继续检查原评分业务；只是先POST得到202，再显式驱动测试消费者，不伪造同步HTTP评分。检查失效验证在 [mutation-red.json](mutation-red.json)：临时移除终评保护，C2必须失败，随后恢复原源码再跑绿。

## 5. 查状态与运行观测

| 接口/操作 | 行为 |
| --- | --- |
| POST `/api/teacher/homeworks/{id}/ai-grade` | 202，task_ids、created_count、existing_count、skipped_count |
| GET `/api/teacher/homeworks/{id}/grade-tasks` | 只读，最近200条 |
| GET `/api/teacher/grade-tasks/{id}` | 只读详情，无作答/评分依据 |
| POST `/api/teacher/grade-tasks/{id}/retry` | 仅dead可202重新排队；其他409 |
| `docker compose logs grading-worker grading-dispatcher` | 单行JSON，task_id与原request_id；不含学生作答或密钥 |
| `docker compose stop/start grading-worker` | 独立启停消费者；实际教学环境不要擅自做故障演练 |

任务字段：attempts是累计消息处理次数（含成功后的重复消息），execution_count是本次人工重试周期的执行次数；started_at到finished_at为最后一次执行耗时。完整延迟还要看created_at，不能混成模型耗时。

教师页面使用execution_count显示“批改尝试1次（本轮上限3次）”。历史attempts=43保留，不代表调用模型43次。

仅当管理员明确清空或丢失代理持久数据时：先停消费者，再运行 `docker compose -p campusclaw-groupv3 run --rm --no-deps grading-worker /app/.venv/bin/python grading_worker.py --recover-pending`，检查结果后重新启动消费者。此命令只重置pending/retrying的投递标记，不能用于普通暂停恢复；不会修改分数或计数。该恢复语义已通过临时库检查；本次没有在教学数据库执行此命令。

主 `/health` 当前不监控消费者心跳。应用健康不等于队列或消费者可用；用任务状态、后台日志、Compose状态及队列长度一起判断。本轮未实现高可用集群、监控告警或自动备份。

## 6. 页面证据与待验项

页面在独立3009/8009环境使用合成账号实际操作，记录见 [ui-normal.txt](ui-normal.txt)、[ui-dead.txt](ui-dead.txt)、[ui-query-error.txt](ui-query-error.txt)、[ui-class-switch.txt](ui-class-switch.txt)、[ui-reloaded.txt](ui-reloaded.txt)。[截图](ui-completed.png)显示AI建议70、教师正在编辑88，后台完成没有覆盖表单。这里的分数全是合成测试数据。

未执行：另一机器/另一组员复现与交叉评审、真实模型质量/成本测试、外网演示、正式提交与版本标签。未归档OpenSpec变更，未擅自修改tasks勾选；实际实施与检查状态写在validation。课程版本标签要求仍待正式交付时按授权完成，不能用本记录冒充已有标签。
