# 第10课从零启动与运行链路

- 批次：`reports/lesson-10/20261114T072100Z-apply/`
- 时间：2026-11-14 07:33–07:37 UTC
- 主机：macOS 15.x（Darwin 24.6.0）；Docker 29.8.0 / Compose v5.5.1
- 提交：`fe227a1`（工作区含第10课未提交改动，镜像与证据按 dirty 标注）
- 端口/数据：`CAMPUSCLAW_PORT=8086`、`CAMPUSCLAW_DATA_DIR=./data`
- 性质：同一目录内的真实启动；**不是**换目录/换机复现

## 一、前置

根目录 `.env`（不入库，随机生成）：

```text
JWT_SECRET_KEY / GRADING_BROKER_PASSWORD / MCP_AUTH_TOKEN / MCP_TOKEN_KEY
CAMPUSCLAW_PORT=8086
CAMPUSCLAW_DATA_DIR=./data
```

启动命令：

```bash
GIT_SHA=$(git rev-parse HEAD) docker compose up -d --build
```

## 二、七服务状态

```text
backend             running  Up (healthy)
frontend            running  Up (healthy)
grading-dispatcher  running  Up
grading-worker      running  Up
mcp-tools           running  Up (healthy)
nginx               running  Up
rabbitmq            running  Up (healthy)
```

原始输出：`boot/compose-build.txt`、`boot/compose-ps.txt`。

## 三、入口健康

```json
{"status":"ok","version":"1.2.0","time":"2026-11-14T07:35:39Z",
 "dependencies":{"database":"ok","mcp_tools":"ok","model":"not_configured"}}
```

`model=not_configured` 是本次未提供模型 Key 的真实状态，未伪报可用。

## 四、H5 等价链路（同一 API + 角色分步）

夹具：`scripts/lesson10_seed_fixture.py` 在**空库**写入合成班级 201/202、教师 T10A/T10B、学生 S10A、作业与资料；未运行 `dev_seed`，未触碰任何已有账号。

| 步骤 | 期望 | 实测 |
| --- | --- | --- |
| 学生登录并提交作业 | 200 | **200**（10.8 ms） |
| 教师触发 AI 初批 | 202 + task_ids | **202**，`task_ids=[1]`（6.3 ms） |
| 轮询任务状态 | pending → running/retrying → 终态 | **pending → retrying → dead**，`attempts=3`；错误为“模型调用失败或评分格式无效”，属未配置模型的预期终态 |
| 学生查本人结果 | 200 | **200**，`teacher_score=null`（未被旧 AI 结果覆盖） |
| 本班资料下载 | 200 | **200** |
| 跨班资料下载 | 404 且无正文 | **404「材料不存在」** |

原始输出：`boot/smoke.json`。

**合同差异（保留）：** 学生提交是 200，教师触发才是 202；课程字面的“学生提交即 202 并轮询任务”未实现。本记录只证明现有角色分步的等价链路，是否被课程接受仍待确认。

## 五、镜像与提交

| 镜像 | Image ID | OCI revision | 运行用户 |
| --- | --- | --- | --- |
| `campusclaw-backend:fe227a1` | `sha256:4ef88d1e…` | `fe227a1c8e51…` | `appuser` |
| `campusclaw-frontend:fe227a1` | `sha256:42764a1c…` | `fe227a1c8e51…` | 默认 |
| `campusclaw-mcp-tools:fe227a1` | `sha256:961a3422…` | `fe227a1c8e51…` | `appuser` |

原始输出：`boot/images.txt`。

## 六、未完成

1. **换目录/换机**：本节最初只在同一目录启动；当前提交的换目录复验见 §八，**换机仍需另一人/另一台机器**，不能用换目录冒充。
2. **手机浏览器**：未用真实手机验证；仅用同一 API 走通角色分步。
3. **真实模型**：未配置 Key，语义正确性、完整生成耗时未验证。
4. **源码字面要求**：后端镜像仍包含 Python 运行源码；是否接受待确认。

---

## 七、运行期就绪与摘流量（2026-11-14 追加，对应任务 3.1）

判据：`health=200` 不能直接当作可接流量；还需分别证明页面资源、数据库故障路径、模型与消费者状态、以及“新实例未被反代”可观测。

| 检查 | 方法 | 实测 | 结论 |
| --- | --- | --- | --- |
| 入口健康 | `GET http://127.0.0.1:8086/api/health` | 200，`database=ok`、`mcp_tools=ok`、`model=not_configured` | 三态可辨，未配置不被伪装成 ok |
| 实际页面资源 | `GET /` 经 nginx | 200，首包 6.6–10.0ms | 页面可达（修复见下） |
| request_id | 响应头 `x-request-id` 与 `logs/backend.jsonl` 的 `request_id` | 头 `4c68bd13…` 与日志同一值 | 端到端一致 |
| 数据库故障 | 临时实例（8001）复制库后写入非 SQLite 内容 | `503`，`{"detail":"数据库暂不可用，请稍后重试"}` | 不泄露 SQL/路径/异常原文 |
| 新实例不接流量 | 临时实例 8001 与主栈同网络；经 nginx 请求 3 次、直连 8001 一次 | 临时实例日志行数 6→6（经 nginx）、6→7（直连） | 反代只走 `backend:8000`，新实例未被接入 |
| 模型状态 | health `dependencies.model` | `not_configured` | 未配置 Key 时显式区分 |
| 消费者就绪 | `grading_queue.get()` 使用 `basic_get`；RabbitMQ 两条连接 `running` | 主队列 messages=0、consumers=0 属轮询设计，不是掉线 | 不能仅凭 consumers=0 判为失败 |
| 首包耗时边界 | 上述 curl 计时 | 页面 6.6–10.0ms；`/api/materials` 401 6.9ms | 仅本机回环，不含真实生成 |

### 7.1 新发现：容器重建后 nginx 上游 IP 缓存导致 502

- 现象：frontend 容器重建后 IP 由 `172.19.0.6` 变为 `172.19.0.12`；nginx 仍连旧地址，`GET /` 连续 502，而 `docker exec nginx wget http://frontend:3000/` 正常。
- 证据：nginx error log `connect() failed (111: Connection refused) ... upstream: "http://172.19.0.6:3000/"`；`getent hosts frontend` 返回 `172.19.0.12`。
- 处置：`docker exec campusclaw-group-nginx-1 nginx -s reload`，页面立即恢复 200。
- 结论：**重建 frontend/backend 后必须 reload nginx**，否则 health 正常但页面不可用；这条应写入部署步骤，不能只靠 `depends_on` 或 healthcheck。

### 7.2 未完成

- 换机复现仍缺（需另一人/另一台）。
- 未做持续摘流量的滚动发布；本轮只证明“新实例可独立起、未被反代接入”。

---

## 八、换目录二次启动复验（2026-11-16，当前提交）

- 方法：`git archive HEAD` 把提交 `984c4c8` 导出到全新空目录（不复用工作区文件），生成独立 `.env`（随机密钥、临时数据目录），使用不同 compose 项目名与端口 8097，执行 `docker compose build` 后 `up -d`；不挂载主栈容器或数据卷。
- 结果：七服务全部 Up，backend/frontend/mcp-tools/rabbitmq healthy；`GET /health` 200（`database=ok`、`mcp_tools=ok`、`model=not_configured`）；`GET /login` 200。
- 0 源码与版本：backend/mcp-tools/frontend 容器内 `.py=0`；三镜像 OCI `revision` 均为 `984c4c8cc6963bf315bd3f0820c4965043beed23`。
- 清理：独立项目 `down -v`，临时目录删除，无残留容器/卷。
- **边界**：这证明“空目录 + 新项目名 + 新端口”可以按 README 用当前提交重建并启动；它不是“换机”，不能替代另一人/另一台机器的复验，也不覆盖主机、内核、Docker 版本差异。
- 证据：`reports/lesson-10/20261116T024000Z-clone-registry-rollback/`（`clone-build.txt`、`clone-up.txt`、`clone-ps.txt`、`clone-health.json`、`clone-no-source.txt`、`clone-summary.txt`）。

## 九、10.2 本人启动复验（2026-11-17）

- 执行人 **smrrrrr**。提交号和 HTTP 结果来自本人 PowerShell 终端截图，容器状态与镜像标记在启动后补采。
- 环境为 Windows 10.0.26200.0、Windows PowerShell 5.1、Docker Engine 29.8.0、Compose 5.5.1。同一台电脑上的新目录 `campusclaw-10-personal`，使用独立 Compose 项目与空 SQLite 数据目录。
- 复验对象为 PR #3 的 `deps/upgrade-a-b`，提交 `977bcde028b24892ac58466b5612e844bd5b2ecb`。
- 健康检查记录时间为北京时间 2026-11-17 14:45:01（UTC+08:00）。Compose 显示镜像构建约 177 秒。

### 实际命令与卡点

1. 第一次直接从 GitHub 克隆时出现 `Connection was reset`。使用 Windows 系统代理重试后克隆成功。克隆时设置 `core.autocrlf=false` 保留容器入口脚本的 LF 换行。
2. 在新仓库根目录按 [Windows 本人启动指南](../docs/lesson10-windows-fresh-start.md) 生成本机 `.env`。使用端口 `18092`、空数据目录 `./data`，并把 `GIT_SHA` 设为被验收的提交。模型 Key 留空。
3. 执行一键启动命令。Compose 显示 `up 14/14`，七个服务全部就绪。
4. 使用两条 HTTP 请求验证健康页和登录入口。

```powershell
Set-Location -LiteralPath ([Environment]::GetFolderPath('Desktop'))
$proxy = [Net.WebRequest]::GetSystemWebProxy().GetProxy([uri]'https://github.com/')
git -c "http.proxy=$($proxy.AbsoluteUri)" -c http.version=HTTP/1.1 clone -c core.autocrlf=false -b deps/upgrade-a-b https://github.com/smrrrrr/CampusClaw-Group.git campusclaw-10-personal
Set-Location -LiteralPath 'campusclaw-10-personal'
git log -1 --oneline
# 在此按指南生成本次验收的 .env
docker compose -p campusclaw-lesson10-personal up -d --build --wait --wait-timeout 180
curl.exe -sS -w " HTTP %{http_code}\n" http://127.0.0.1:18092/health
curl.exe -sS -o NUL -w "HTTP %{http_code}\n" http://127.0.0.1:18092/login
```

### 实测结果

| 检查 | 结果 |
| --- | --- |
| `GET /health` | HTTP 200，`status=ok`，应用版本 `1.2.0`，`database=ok`，`mcp_tools=ok`，`model=not_configured` |
| `GET /login` | HTTP 200 |

| 服务 | 容器状态 | 镜像 ID 前 12 位 | OCI revision |
| --- | --- | --- | --- |
| backend | running，healthy | `b4a52b9ff502` | `977bcde` |
| frontend | running，healthy | `1be523b3cd5d` | `977bcde` |
| mcp-tools | running，healthy | `03445d3dd535` | `977bcde` |
| rabbitmq | running，healthy | `4e1c1636957a` | 未标记 |
| nginx | running | `65645c7bb6a0` | 未标记 |
| grading-dispatcher | running | `372c06daca10` | `unknown` |
| grading-worker | running | `38dcd5d8bfc6` | `unknown` |

**验收结论：** 另一名组员在 Windows 新目录按指南亲自完成启动，七服务就绪，健康检查和登录入口均返回 200。记录覆盖本机启动和 HTTP 可达性。
