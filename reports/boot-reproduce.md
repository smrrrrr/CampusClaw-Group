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
