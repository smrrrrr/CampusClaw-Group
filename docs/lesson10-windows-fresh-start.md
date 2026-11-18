# 第 10 课 10.2 · Windows 本人启动指南

本次验收是你亲自在一个新目录克隆、配置、构建和启动 PR #3，确认七个服务运行，并拿到健康检查和登录页的结果。可以继续用自己的 Windows 电脑。用空数据库即可验证启动和登录页，首次启动会自动建表。

项目的一键启动命令是 `docker compose -p campusclaw-lesson10-personal up -d --build --wait --wait-timeout 180`。第一次需要先克隆代码并配置本机环境。启动后再核对服务、镜像和网页的实际结果。

## 1. 首次准备

打开 Docker Desktop，等引擎启动。在**同一个 PowerShell 窗口**运行以下两段。

### 克隆到桌面新目录

```powershell
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
git clone -c core.autocrlf=false -b deps/upgrade-a-b https://github.com/smrrrrr/CampusClaw-Group.git campusclaw-10-personal
if ($LASTEXITCODE -ne 0) { throw '克隆失败，先处理上面的报错。' }
Set-Location -LiteralPath 'campusclaw-10-personal'
git log -1 --oneline
git ls-files --eol backend/entrypoint.sh
```

记下 `git log` 输出的提交号。最后一行应出现 `w/lf`。克隆参数 `-c core.autocrlf=false` 保留容器入口脚本的 LF 换行。桌面已有同名目录时，把命令里的两处目录名同时改为一个新名字。

如果克隆报 `Connection was reset`，可让这一次 Git 命令使用 Windows 当前的系统代理。记录这条重试命令作为本次网络卡点的处理步骤。

```powershell
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
$lesson10GitUrl = [uri]'https://github.com/'
$lesson10Proxy = [Net.WebRequest]::GetSystemWebProxy().GetProxy($lesson10GitUrl)
if ($lesson10Proxy.Host -eq $lesson10GitUrl.Host -or $lesson10Proxy.UserInfo) { throw '未找到可直接使用的 Windows 系统代理。' }
git -c "http.proxy=$($lesson10Proxy.AbsoluteUri)" -c http.version=HTTP/1.1 clone -c core.autocrlf=false -b deps/upgrade-a-b https://github.com/smrrrrr/CampusClaw-Group.git campusclaw-10-personal
if ($LASTEXITCODE -ne 0) { throw '克隆失败，先记录上面的报错。' }
Set-Location -LiteralPath 'campusclaw-10-personal'
git log -1 --oneline
git ls-files --eol backend/entrypoint.sh
```

### 创建本次验收的配置

这段命令会生成本机用的随机密钥，写入新目录的 `.env`，并为本次验收使用端口 `18092`。后面的检查会沿用你选的端口。

```powershell
$lesson10Port = 18092
if (Test-Path -LiteralPath '.env') { throw '当前目录已有 .env，请先确认这里是新克隆的目录。' }
function New-Lesson10Secret {
    $bytes = [byte[]]::new(32)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_')
}
$lesson10Revision = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '未能读取提交号，请确认当前位于新克隆的仓库。' }
@(
    "JWT_SECRET_KEY=$(New-Lesson10Secret)"
    "MCP_AUTH_TOKEN=$(New-Lesson10Secret)"
    "MCP_TOKEN_KEY=$(New-Lesson10Secret)"
    "GRADING_BROKER_PASSWORD=$(New-Lesson10Secret)"
    'DEEPSEEK_API_KEY='
    'CAMPUSCLAW_DATA_DIR=./data'
    "CAMPUSCLAW_PORT=$lesson10Port"
    "GIT_SHA=$lesson10Revision"
) | Set-Content -LiteralPath '.env' -Encoding ascii
```

密钥只保存在本次验收目录的 `.env`。上传报告和截图时，保留命令与检查结果即可。

配置生成后，可以用下面一段确认 Docker 引擎和 Compose 配置就绪。

```powershell
docker version --format '{{.Server.Version}}'
if ($LASTEXITCODE -ne 0) { throw '请先打开 Docker Desktop，等 Docker 引擎启动。' }
docker compose -p campusclaw-lesson10-personal config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose 配置检查失败，先记录上面的报错。' }
```

## 2. 一条命令启动七个服务

在仓库根目录执行：

```powershell
docker compose -p campusclaw-lesson10-personal up -d --build --wait --wait-timeout 180
```

这条命令负责构建、启动和等待服务就绪。首次构建会拉取镜像和依赖，网络慢时可能要等一会儿。

如果启动提示端口被占用，把 `.env` 中的 `CAMPUSCLAW_PORT` 和当前窗口的 `$lesson10Port` 设为同一个空闲端口，再重跑启动命令。其他错误也记下原文。

## 3. 验收已启动的服务

启动成功后，跑下面一段，把显示的服务状态、镜像版本和 HTTP 返回码记下来。

```powershell
docker compose -p campusclaw-lesson10-personal ps
docker compose -p campusclaw-lesson10-personal images
curl.exe -sS -w " HTTP %{http_code}\n" "http://127.0.0.1:$lesson10Port/health"
curl.exe -sS -o NUL -w "HTTP %{http_code}\n" "http://127.0.0.1:$lesson10Port/login"
Start-Process "http://127.0.0.1:$lesson10Port/login"
```

`ps` 应列出 nginx、backend、frontend、mcp-tools、rabbitmq、grading-dispatcher 和 grading-worker。四个设有健康探针的服务应显示 `healthy`。两条 curl 都应返回 `200`。健康页的 `status`、`database` 和 `mcp_tools` 应是 `ok`，本次配置的模型状态应是 `not_configured`。浏览器能看到登录页即可记录。某项失败时，写下实际结果和报错。

## 4. 填写你的验收记录

把下面的模板复制到 [启动复现报告](../reports/boot-reproduce.md) 末尾，按你实际运行的结果填写。

```markdown
## 10.2 本人启动复验

- 执行人：
- 日期和时间：
- 系统、Docker 版本：
- Git 提交号：
- 环境：Windows，同一台电脑上的新目录
- 执行命令：第 10 课 Windows 本人启动指南步骤 1–3，实际修改过的参数为：
- 七个服务状态及镜像版本：
- /health 返回码和状态：
- /login 返回码及页面结果：
- 卡点与处理：
- 验收结论：
```

检查结束后，可以停止这次验收创建的容器：

```powershell
docker compose -p campusclaw-lesson10-personal stop
```
