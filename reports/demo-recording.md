# 三分钟项目演示录屏

录屏可使用本机已启动的 CampusClaw。开头介绍产品，然后逐条运行报告中的验证命令并保留输出，接着登录演示学生交作业、教师发起 AI 初批和查看批改结果。课堂汇报使用报告和证据，时长 5 分钟。

## 按录制顺序准备

1. 在独立演示库准备 A 班教师、A 班学生和一份未提交的新作业。先确认两人能登录、教师能看到作业和学生提交、模型服务及批改队列可用。使用合成演示账号和材料。正常的学生提交返回 200，教师发起初批返回 202，最后任务达到 `succeeded`。可以同时展示学生收到的批改反馈。
2. 预先启动本机服务，按 [demo-checklist.md](demo-checklist.md#教师验收智能备课) 准备独立实例、测试账号和示例讲义。模型配置保存在私有环境文件。录制时遮住口令、模型密钥和请求令牌。
3. 打开终端并切到报告对应版本的仓库根，按 [reproduce-checks.md](reproduce-checks.md) 安装依赖并设置 PATH。整个录屏流程中可加速等待部分。

## 命令和结果

在 PowerShell 中依次运行以下三步，每条结束后马上查看 `$LASTEXITCODE`（应为 0）。

```powershell
python apitest/check_async_grading.py
python apitest/probe_security_precheck.py --output .review/security-probe.json
python scripts/check.py
```

Linux/macOS 把最后一行换成 `make check`。第一行验证并发和事务，展示 57 项以及 C1、B3。第二行展示 41 项、0 红项，可以在输出 JSON 中展示实际本班 200、跨班 404。第三行展示各检查通过和“门禁全部通过”。如果结果和预期不同，先排查并重新录制实际通过那一轮。录制时避免只贴历史日志或在画面跳过命令执行。

## 录制时间安排

| 剪辑后时间 | 画面 |
| --- | --- |
| 0:00–0:15 | 一句话说明谁用 CampusClaw、解决什么问题。 |
| 0:15–1:15 | 依次跑三条命令，快进等待并给结果留阅读时间。 |
| 1:15–2:45 | 登录学生账号交一份新作业，切到教师账号触发初批并展示完成后的评分与反馈。 |
| 2:45–2:55 | 简单指出红绿证据在 `reports/gate-red-green.md`。 |

导出后检查总长不超过 3 分钟、终端与系统画面清晰。上传到百度网盘或北大网盘，检查通过分享链接能下载，有提取码则一并注明。把真实下载链接写到 `report.md` 开头，按 [submission-readiness.md](submission-readiness.md) 提交。
