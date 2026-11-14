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

1. **换目录/换机**：本轮只在同一目录启动，不能冒充 3.3/10.2。
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
