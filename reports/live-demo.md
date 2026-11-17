# 外部部署现场演示

状态：**待教师提供地址后执行**。2026-11-17 用户明确说明预计次日收到地址；此处是操作指引，不是已完成记录。报告第五节只在真实外部环境四步通过后更新。脚本单元测试、本机 localhost、CI临时服务、录屏都不替代此项。

## 先准备什么

1. 确认给到的是托管后的应用网址，还是需要部署的服务器。应用由七个服务组成，外部入口要能连接 Nginx，服务版本须对应已审查提交。由环境管理者确认部署方式，不猜公网地址或填写示例域名。
2. 使用独立演示数据。准备 A 班教师、A 班学生、B 班学生三个真实可登录的演示账号；演示口令私下提供，不写进报告。`scripts/lesson10_seed_fixture.py` 只有两位教师和一位学生，且材料只有元数据，不能当成三账号和可下载材料已就绪。
3. 教师导入作业附件 `第一章 空间立体几何_备课资料包.zip`，生成并核对学生版后发布到 A 班。确认 A 班学生实际下载是200、确实能读到讲义；记下该材料编号。不要拿不存在的编号返回404来证明越权防护。
4. 教师发布一份新的演示作业，A 班学生提交，记下作业编号。首次演示使用未初批的新提交，避免读到上次已经完成的任务。
5. 模型 Key 配在服务器私有环境中；检查模型可调用、RabbitMQ/worker/dispatcher正常。未配置模型时 `dead` 只证明降级，不满足成功演示。

备课、命题、批改和学科问答完整准备见 [demo-checklist.md](demo-checklist.md#教师验收智能备课)。原始组内交接包含库和密钥，不能上传公共仓库。

## 四步对应真实端点

| 步骤 | 在真实页面/网络面板中查看 | 通过判据 |
| --- | --- | --- |
| 登录 | `POST /api/auth/login` | 登录200，令牌只在会话使用，不截进证据。 |
| 返回202 | 教师“作业与改分”点击AI初批：`POST /api/teacher/homeworks/{id}/ai-grade` | HTTP202且有非空 `task_ids`；学生提交返回200。 |
| 查询流转 | `GET /api/teacher/grade-tasks/{task_id}` | 记录实际观察到的排队/运行/完成状态，最终 `succeeded`。若轮询太慢未捕获某中间态，保留实际结果并用同任务运行日志补证，不能补写状态。 |
| 换账号404 | 先A班学生下载，再退出换B班学生访问同一 `GET /api/materials/{id}/download` | 同一存在的资源，有权200、他班404且无内容泄漏。任务端点403不能替代本步骤。 |

## PowerShell 辅助演示命令

浏览器可完成上述步骤。需要展示HTTP状态时，以下命令在本地终端向**外部部署地址**发请求，只操作已准备的合成演示作业。没有默认网址、账号、材料编号或模型Key。

```powershell
$ErrorActionPreference = 'Stop'
$demoBase = (Read-Host '输入实际外部应用根网址，不加结尾斜杠').TrimEnd('/')
$demoUri = [uri]$demoBase
if ($demoUri.Scheme -notin @('http','https') -or $demoUri.IsLoopback) { throw '请使用实际外部部署地址' }
function Login-Demo([string]$roleLabel) {
    $credential = Get-Credential -Message $roleLabel
    if ($null -eq $credential) { throw '取消登录' }
    $body = @{ identifier=$credential.UserName; password=$credential.GetNetworkCredential().Password } | ConvertTo-Json
    $session = Invoke-RestMethod -Method Post -Uri "$demoBase/api/auth/login" -ContentType 'application/json' -Body $body
    if (-not $session.access_token) { throw '登录未返回令牌' }
    return @{ Authorization = 'Bearer ' + $session.access_token }
}
$teacherHeaders = Login-Demo 'A班教师账号'
$studentAHeaders = Login-Demo 'A班学生账号'
$studentBHeaders = Login-Demo 'B班学生账号'
$demoHomeworkId = [int](Read-Host '刚准备好的新演示作业编号')
$demoMaterialId = [int](Read-Host 'A班已发布且能下载的讲义编号')
$accepted = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$demoBase/api/teacher/homeworks/$demoHomeworkId/ai-grade" -Headers $teacherHeaders
if ($accepted.StatusCode -ne 202) { throw '初批未返回202' }
$taskIds = @(($accepted.Content | ConvertFrom-Json).task_ids)
if ($taskIds.Count -eq 0) { throw '没有创建任务，请确认已有待批提交' }
$demoTaskId = $taskIds[0]
Write-Output "HTTP 202，任务编号 $demoTaskId"
$demoSeen = @()
$deadline = (Get-Date).AddSeconds(120)
do {
    $task = Invoke-RestMethod -Uri "$demoBase/api/teacher/grade-tasks/$demoTaskId" -Headers $teacherHeaders
    if ($demoSeen.Count -eq 0 -or $demoSeen[-1] -ne $task.status) {
        $demoSeen += $task.status
        Write-Output "任务 $demoTaskId 状态 $($task.status)"
    }
    if ($task.status -in @('succeeded','dead','skipped')) { break }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)
if ($task.status -ne 'succeeded') { throw '本次未完成成功批改演示，保留实际结果后排查' }
$own = Invoke-WebRequest -UseBasicParsing -Uri "$demoBase/api/materials/$demoMaterialId/download" -Headers $studentAHeaders
if ($own.StatusCode -ne 200) { throw '本班正例未通过' }
$deniedCode = $null
try {
    $denied = Invoke-WebRequest -UseBasicParsing -Uri "$demoBase/api/materials/$demoMaterialId/download" -Headers $studentBHeaders
    $deniedCode = [int]$denied.StatusCode
} catch {
    if ($null -eq $_.Exception.Response) { throw }
    $deniedCode = [int]$_.Exception.Response.StatusCode
}
if ($deniedCode -ne 404) { throw "跨班预期404，实际 $deniedCode" }
Write-Output '同一讲义：A班200，B班404'
```

以上片段经静态语法核对，**尚未在教师提供的环境执行**。它不访问本地数据库，不打印口令/令牌；真实响应是否符合预期仍需部署后验证。SSE或模型出错、跨班拿到200、仅得到不存在404等均不能算成功。

## 实测后怎么留证

将日期、外部URL、运行版本/镜像revision、操作者、初批HTTP202、任务编号与实际状态序列、同资源200/404写进 `reports/deployment-verification.md`，附脱敏网络面板/服务器事件记录的位置。不要保存Authorization、Cookie、密码、Key或真实学生答案。

然后更新 `report.md` 第五节的待部署段落，保持仓库和作业平台上传的 report.md 内容相同。本文件的步骤准备完成不等于部署验收完成。
