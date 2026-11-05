# Windows 本机搭建方法与验证记录（2026-11-04）

## 本次搭建结果

使用交接说明对应的 `main` 分支、提交 `e10c81b`，版本为 `1.2.0`。已恢复 `CampusClaw-Group-Data-20261025.zip`，构建并启动 Nginx、前端、后端、MCP 工具服务。

| 项目 | 本机位置或配置 |
| --- | --- |
| 项目目录 | `C:\Users\17424\Desktop\CampusClawv3\CampusClaw-Group` |
| 登录入口 | <http://localhost:8083/login> |
| 健康检查 | <http://localhost:8083/health> |
| Compose 项目名 | `campusclaw-groupv3` |
| 数据库 | `data/current/campusclaw.db` |
| 教学资料文件 | `backend/uploads/` |
| 本机密钥及模型配置 | 项目根目录 `.env` |
| 首次启动前备份 | `data/current/before-first-start-20261104-085704.db` |

本机的 8080、8081、8082 已被其他部署使用，因此在这份项目的 `.env` 设置了 `CAMPUSCLAW_PORT=8083` 和 `COMPOSE_PROJECT_NAME=campusclaw-groupv3`。Compose 项目名会覆盖配置文件中的默认名称，使新旧部署各自保留容器、网络和数据挂载。

已随机生成 JWT 密钥、MCP 访问令牌和 MCP 加密密钥，实际值仅保存在本机 `.env`。用户随后填写模型 Key，已重新创建后端并接入 DeepSeek `deepseek-chat`；健康检查的 `model` 为 `configured`，真实流式生成连通测试通过。首次未填写 Key 时的降级检查结果保留在下方验证记录中。

## 这台电脑以后怎么启动

先打开 Docker Desktop，等待 Linux 容器引擎就绪，然后在 PowerShell 执行：

```powershell
Set-Location 'C:\Users\17424\Desktop\CampusClawv3\CampusClaw-Group'
docker compose up -d
docker compose ps
Invoke-RestMethod 'http://localhost:8083/health'
```

健康检查应返回 `status: ok`、`version: 1.2.0`，`database` 和 `mcp_tools` 都为 `ok`。后端、前端和 MCP 服务有健康探针，应显示 `healthy`；Nginx 显示 `Up` 即可，它没有配置健康探针。

打开 <http://localhost:8083/login>。教师账号为 `TEA001`、`TEA002`；学生账号为 `20260001`、`20260002`，密码按随包交接说明的“数据包演示账号”一节填写。这里使用的是恢复的数据包账号，学生不要求首次改密。

停止这套服务：

```powershell
docker compose stop
```

代码更新后重新构建：

```powershell
docker compose up -d --build
```

以上命令在本项目目录执行，读取本目录 `.env`，只操作 `campusclaw-groupv3`。已有数据库不需要重新恢复，也不要运行 `backend/dev_seed.py`。

## 在新目录完整复现

以下步骤用于另一台电脑或**尚无数据的新目录**。本机已经完成恢复，不要再对当前目录重复执行恢复脚本。

### 1. 准备环境与源码

运行项目需要 Git 和 Docker Desktop，并启用 Linux 容器引擎。要运行开发检查，还需要 Python 3.12、uv、Node.js/npm 和 OpenSpec CLI。本机使用 Python 3.12.13、uv 0.12.18、Node.js 22.16.0、npm 10.9.4、OpenSpec CLI 1.13.0。

```powershell
$projectRoot = 'C:\Projects\CampusClaw-Group'
git clone https://github.com/smrrrrr/CampusClaw-Group.git $projectRoot
Set-Location $projectRoot
git log -1 --oneline
docker info
```

本次交接对应提交为 `e10c81b`。如果以后主分支已经更新，复现本次版本时先在新克隆里检出该提交。

### 2. 恢复数据包

先把组内 ZIP 放在本机，下面的 `$packageZip` 改为实际位置。恢复前，目标项目中应没有 `.env`、`data/current/campusclaw.db` 和已有上传资料；脚本遇到这些内容会拒绝覆盖。

```powershell
$packageZip = 'C:\交接资料\CampusClaw-Group-Data-20261025.zip'
$extractRoot = Join-Path $projectRoot '.review\groupdata'
Expand-Archive -LiteralPath $packageZip -DestinationPath $extractRoot
$packageRoot = Join-Path $extractRoot 'CampusClaw-Group-Data-20261025'
& (Join-Path $packageRoot 'Restore-GroupData.ps1') -ProjectRoot $projectRoot
```

恢复脚本会核对清单里的 SHA-256 指纹，复制数据库、31 个资料文件，并生成根目录 `.env` 和新的 JWT 密钥。数据包及解压目录放在已被 Git 忽略的 `.review/` 内；教学资料和数据库也已被项目的 `.gitignore` 忽略。

### 3. 补齐 Windows 恢复脚本未生成的 MCP 密钥

在项目根目录执行以下 PowerShell。它只填写两个空的 MCP 配置项，不显示密钥值；若已经有值，则保留原值。

```powershell
$envFile = Join-Path $projectRoot '.env'
$configText = [IO.File]::ReadAllText($envFile)
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $tokenBytes = New-Object byte[] 32
    $keyBytes = New-Object byte[] 32
    $rng.GetBytes($tokenBytes)
    $rng.GetBytes($keyBytes)
} finally {
    $rng.Dispose()
}
$mcpToken = [BitConverter]::ToString($tokenBytes).Replace('-', '').ToLowerInvariant()
$mcpKey = [Convert]::ToBase64String($keyBytes).Replace('+', '-').Replace('/', '_')
$configText = $configText -replace '(?m)^MCP_AUTH_TOKEN=[ \t]*\r?$', ('MCP_AUTH_TOKEN=' + $mcpToken)
$configText = $configText -replace '(?m)^MCP_TOKEN_KEY=[ \t]*\r?$', ('MCP_TOKEN_KEY=' + $mcpKey)
[IO.File]::WriteAllText($envFile, $configText, [Text.UTF8Encoding]::new($false))
```

恢复包默认使用端口 8081。如需与本次搭建一致，在 `.env` 将端口改成 8083，并加入项目名；其他已有配置保留：

```dotenv
CAMPUSCLAW_DATA_DIR=./data/current
SQLITE_JOURNAL_MODE=DELETE
CAMPUSCLAW_PORT=8083
COMPOSE_PROJECT_NAME=campusclaw-groupv3
ENABLE_DOCS=false
```

在其他机器上，可为独立部署选择未占用的端口和项目名。后续访问地址中的端口也要对应修改。

### 4. 首次启动前备份，再构建服务

首次启动会自动为旧数据库添加新功能所需字段。启动前先备份尚未运行的数据库：

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath '.\data\current\campusclaw.db' -Destination ".\data\current\before-first-start-$stamp.db"
docker compose config --quiet
docker compose up -d --build
docker compose ps
Invoke-RestMethod 'http://localhost:8083/health'
```

只有停写状态的数据库才适合直接复制。运行中的备份应使用 SQLite backup API，命令见 `DEPLOYMENT.md` 的“数据与备份”。原 ZIP 和解压后的 `uploads/` 也保留了迁移前对应的资料副本。

### 5. 恢复二班 MCP 连接

数据包已经清空旧令牌，所以只有工具服务启动成功还不够，需要给教师登记记录重新配置本机令牌。

按交接说明的页面操作方法：以 `TEA001` 登录，选择二班，进入 MCP 服务器设置，删除原来的 `campus-tools` 后重新登记：

| 字段 | 内容 |
| --- | --- |
| 名称 | `campus-tools` |
| 地址 | `http://mcp-tools:8090` |
| 令牌 | 本机根目录 `.env` 中 `MCP_AUTH_TOKEN` 的值 |

点击“连接并发现”，应出现 `formula_hint`、`unit_convert` 两个工具。名称保持 `campus-tools`，因为“公式提示”技能按名称引用它。

本次已通过现有的教师认证接口为原记录补填令牌并连接发现，保留了原记录编号，最终配置和工具清单与上述页面步骤一致，无须再次登记。

### 6. 按需要接入模型

用本机编辑器打开项目根目录 `.env`，自行填写 `DEEPSEEK_API_KEY`。如使用课程网关，同时取消这两项的注释：

```dotenv
DEEPSEEK_BASE_URL=https://ai-gateway.devops.hello1023.com/v1
DEEPSEEK_MODEL=course-chat
```

保存后重新创建后端容器，让它读取新配置：

```powershell
docker compose up -d --force-recreate backend
Invoke-RestMethod 'http://localhost:8083/health'
```

`model: configured` 只说明已经填写 Key，能否真实生成还取决于 Key 有效性、网关连通性和额度。本次首次搭建时未配置 Key；用户填写后已完成一次真实流式连通测试，只发送通用测试文字，消耗少量模型额度。密钥直接在本机填写，无须发到聊天或写进仓库文档。

### 7. 安装开发依赖并运行离线门禁

```powershell
Set-Location (Join-Path $projectRoot 'backend')
uv sync --locked --python 3.12
Set-Location (Join-Path $projectRoot 'frontend')
npm.cmd ci
Set-Location $projectRoot
$env:PYTHONUTF8 = '1'
& '.\backend\.venv\Scripts\python.exe' '.\scripts\check.py'
```

运行前确认 `openspec --version` 可用。门禁使用临时库和假模型，不读取恢复数据库，不消耗模型额度。

## 本次验证记录

| 检查 | 结果 |
| --- | --- |
| 数据包指纹、数据库完整性 | 通过；迁移前备份 `integrity_check=ok` |
| 恢复文件 | 31 个，逐个 SHA-256 与清单一致 |
| 数据恢复 | 4 个账号、2 个班、8 份班级资料、2 份教研组资料、2 份教案、13 道题、2 份试卷 |
| 旧库字段迁移 | 作业、作业提交、错题表的所需字段已就绪，教学数据行数保持一致 |
| Docker 服务 | 后端、前端、MCP 为 healthy；Nginx 正常运行 |
| `/health` | HTTP 200，`status=ok`、`version=1.2.0`、数据库与 MCP 均为 ok |
| 登录页 | HTTP 200，浏览器显示学号/工号、密码及登录按钮 |
| 演示账号 | 四个账号均登录成功，不要求改密 |
| 教师端内容 | 2 份教案、3 道已入库题、2 份试卷可读取 |
| 学生资料 | 一班 3 份、二班 5 份，全部预览内容的指纹与本地文件一致 |
| 访问限制 | 未登录取资料 401；学生跨班预览 403；学生访问教师接口 403 |
| 作业、错题、学情接口 | 两班学生均返回 200；数据包没有作业提交，统计为 0，准确率为空 |
| MCP | 二班 campus-tools 已认证连接，发现公式提示和单位换算工具 |
| 模型未配置时 | 首次搭建时画像返回 `available=false`，符合降级行为 |
| 模型配置后 | `deepseek-chat` 已加载，`/health` 返回 `model=configured`；真实流式响应成功，约 1.04 秒返回 4 个字符 |
| Swagger | `/docs`、`/openapi.json` 均返回 404 |
| 完整离线门禁 | 20 个分组全部 PASS：规约、分层、密钥、类型检查及 16 组离线回归 |

本地详细证据位于 `.review/setup-smoke-20261104.json` 和 `.review/setup-check-20261104.log`，不随源码提交。上述恢复与配置没有修改业务代码，也没有执行 OpenSpec apply/archive 或改变任务勾选。

## 本次耗时与遇到的卡点

| 步骤 | 大致耗时与处理 |
| --- | --- |
| 数据恢复、密钥补齐及备份 | 约 3 秒 |
| Docker 引擎启动 | 约 1 分钟；安装了 Docker Desktop，但开始时引擎未运行，启动后继续 |
| Python 开发依赖 | 约 1 分钟，按锁文件安装 |
| 前端开发依赖 | 约 1 分钟，`npm ci` 安装 133 个包 |
| 三个应用镜像构建及服务启动 | 约 2 分钟，前端构建成功，Python 运行依赖按锁安装 |
| 本机接口与文件核验 | 约 4 秒 |
| 完整离线门禁 | 约 2 分钟，最终输出“门禁全部通过”；初次执行环境中备课检查停留，单独在正常本机环境复核 119 项通过，再运行完整门禁通过 |
| 端口和项目名冲突 | 原有部署占用 8080–8082；新部署改用 8083 和独立项目名，旧部署保持运行 |
| Windows 恢复脚本遗漏 MCP 密钥 | 用系统安全随机数补齐，两项实际值仅写入 `.env` |

README 的快速开始已增加 Windows 数据包搭建入口。后续再次部署时应保留 `.env`、数据库和资料目录；重建容器会继续使用它们。


## 智能命题作业更新（2026-11-04）

当前 8083 已更新：智能命题 → 组卷与发布 → 打开试卷 → 定稿 → 下方「发布为作业」。选择班级、填写截止时间并核对后发布。学生在「交作业」提交，教师在「作业与改分」初批或终评；手工入口与历史资料保留。整份成绩按百分制，未提供逐题改分。详细检查、备份和回滚见 [本次验收记录](../openspec/changes/2026-11-04-publish-quiz-as-homework/validation.md)。
