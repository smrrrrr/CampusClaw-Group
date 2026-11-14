# 第10课观测、面板与告警

- 批次：`reports/lesson-10/20261114T072100Z-apply/`
- 组件：`scripts/observability/collect.py`、`docker-compose.observability.yml`、`deploy/observability/`
- 性质：独立 overlay，不替换现有七服务；采集器只读

## 一、指标口径

| 指标 | 来源 | 口径与限制 |
| --- | --- | --- |
| `skill_invocations_total{skill,status}` | 已持久化的业务记录 | 只统计真实存在的事件；不按路由次数伪造 |
| `skill_events_available{skill}` | 采集器判定 | `0` 表示事件来源未接入，**不能按 0 次解释** |
| `grading_tasks{status}` | `grade_tasks` | 当前状态分布 |
| `grading_executions_total` | `grade_tasks.execution_count` | 累计模型执行次数，不等于任务数 |
| `http_requests_total{path,status}` | 访问日志 | 路径中的数字段归一为 `:id`；SSE 响应开始即计数 |
| `http_request_duration_seconds_*` | 访问日志 `duration_ms` | SSE 端点仅首包耗时，不能当完整生成耗时 |

技能映射：

| 技能 | 已记录来源 | 状态映射 |
| --- | --- | --- |
| `tutor_guidance` | `ai_question_logs` | `answer` 非空为 succeeded，空为 unknown |
| `homework_grading` | `grade_tasks` | succeeded / dead→failed / skipped / pending·running·retrying→unknown |
| `mistake_explanation` | **无成功/失败持久事件** | `skill_events_available=0`；只在审计有 403 时记录 denied |

失败率公式：`failed / (succeeded + failed)`；`denied` 单列，不计入执行失败。无分母显示“无样本”，不填 0。

## 二、面板

Grafana 已通过 provisioning 加载（`/api/dashboards/uid/campusclaw-lesson10`）：

1. 三个技能的调用量（按 skill/status）。
2. 各技能失败率（5 分钟）。
3. 三技能对应接口 P95（完整请求；SSE 明确为首包）。
4. 批改队列深度（待执行/执行中）。

只有批改技能有持久队列；引导与错题讲解**不虚构**队列数据。

## 三、采集与新鲜度

- Prometheus 抓取间隔 15 秒，规则评估 15 秒。
- 采集器每次按需读取 SQLite（只读连接、短查询）与日志文件，不写业务库。
- 实测：`collector_status{source="database"}=1`、`{source="access_log"}=1`，`campusclaw-collector` target 为 `up`。
- 新鲜度实测：`time() - timestamp(collector_last_scan_timestamp_seconds)` = **12.3 秒**（目标 ≤30 秒）。

### 时间窗报数

指定 UTC 窗口 `2026-11-14T07:31:02Z` 至 `08:31:02Z`，执行：

```bash
python scripts/observability/collect.py --window <start> <end> --db ... --log ...
```

- 实际耗时 **0.04 秒**，远低于 60 秒目标。
- 窗口内：`tutor_guidance` 成功 1、失败 0；`homework_grading` 成功 0、失败 112、失败率 100%（告警演练注入）；`mistake_explanation` 无样本。
- 证据：`observe/window/report.json`、`observe/window/time.txt`。

仍然待确认：7.4 的“每图看到三个技能”是否接受第三图由“三技能接口 P95 + 批改队列深度”组合表达；错题讲解没有持久事件源，面板显示 No data 而不是 0。

## 四、告警规则

`deploy/observability/alerts.yml`：

- `SkillFailureRateHigh`：某技能 5 分钟失败率 > 1%，且窗口内执行样本 ≥ 20，持续 5 分钟 → Firing。
- `CollectorDown`：采集器不可达 1 分钟 → 告警，避免把“无数据”误读为“无失败”。

通知路径：Prometheus → Alertmanager → 本机测试接收器 `scripts/observability/webhook_receiver.py`（`host.docker.internal:9099/alert`），记录写入 `alert/received.jsonl`。

**限制：** 该接收器只证明“规则 → Firing → 实际送达”链路；真实负责人/群机器人与发送授权尚未落实，不能宣称团队已收到。

## 五、演练记录

- 注入方式：独立演示库持续写入 `grade_tasks(status='dead')`，每 30 秒 5 条，持续 8 分钟（`alert/injection.log`）。
- 观测值：`homework_grading` 失败率 100%，5 分钟窗口执行样本 47.4（≥20）。

| 阶段 | 时间（UTC） | 证据 |
| --- | --- | --- |
| Pending | 2026-11-14T07:43:39Z | Prometheus `ALERTS{alertstate="pending"}` |
| Firing | 2026-11-14T07:48:39.202Z | Prometheus 规则状态；Alertmanager `startsAt` |
| 送达测试接收器 | 2026-11-14T07:48:54.189Z | `alert/received.jsonl`，status=firing |
| Resolved | 2026-11-14T07:53:24.199Z | 同文件 status=resolved；注入停止后窗口跌回阈值 |

- Firing → 实际送达：**15 秒**，满足“60 秒内送达”的目标。
- 通知内容包含技能名、失败率与“窗口内执行样本已超过 20”，可回到面板复核。

**未完成：** 真实负责人/群机器人与发送授权未落实，因此只能证明测试接收器收到；不能宣称团队已收到，也不能把本次演练当成课程人工验收。
