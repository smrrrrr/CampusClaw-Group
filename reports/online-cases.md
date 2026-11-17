# 在线用例环境准备与执行记录（任务 3.3）

- 日期：2026-11-14
- 口径依据：课程答复第 7 条——**在线 cases 自行准备**
- 批次：`reports/lesson-10/20261114T125424Z-online/`
- 性质：环境准备与执行记录；**未污染真实教学库**，也**未宣称全部用例通过**

## 一、环境准备

| 项 | 做法 |
| --- | --- |
| 实例 | 独立容器 `lesson10-online`，端口 `127.0.0.1:8004`，镜像 `campusclaw-backend:073ce99…` |
| 数据库 | 临时目录 `campusclaw-online.XXXXXX/data/campusclaw.db`，不挂载 `./data` |
| 种子 | `backend/dev_seed.py` 在新空库运行，生成 TEA001/TEA002/20260001/20260002 与班级 101/102 |
| 固定身份 | 教师 `TEA001`、学生 `20260002`；为复用历史用例，临时库把两名学生 id 对齐为 3/4 |
| 已索引材料 | 经 `/api/teacher/upload-material` 上传 `online-mat.md` 到 class 102，轮询至 `is_indexed=true` |
| ENABLE_DOCS | 容器环境变量 `ENABLE_DOCS=true`，`GET /docs` 返回 200 |
| HTML 前置 | `pytest-html 4.2.0`（测试侧依赖，未写入业务依赖） |

启动命令：

```bash
docker run -d --name lesson10-online --network campusclaw-group_default \
  -p 127.0.0.1:8004:8000 --env-file .env \
  -e DATABASE_URL=sqlite:////app/data/campusclaw.db -e ENABLE_DOCS=true \
  -e MCP_TOOLS_HEALTH_URL=http://mcp-tools:8090/health \
  -v <临时目录>/data:/app/data campusclaw-backend:073ce99…
```

执行命令：

```bash
APITEST_BASE_URL=http://127.0.0.1:8004 \
APITEST_DB_PATH=<临时目录>/data/campusclaw.db \
APITEST_TEACHER_ID=TEA001 APITEST_TEACHER_PASSWORD=… \
APITEST_STUDENT_ID=20260002 APITEST_STUDENT_PASSWORD=… \
backend/.venv/bin/python apitest/run_all.py
```

## 二、结果

| 轮次 | 结果 | 说明 |
| --- | --- | --- |
| 第 1 次（id 未对齐） | 2 failed / 14 passed / 1 skipped / 8 errors | 用例假设学生 id=3，种子实际为 4 |
| 第 2 次（id 对齐、直连库） | 18 passed / 3 skipped / 4 errors | 宿主与容器同时访问同一 SQLite，`disk I/O error` |
| 第 3 次（只读副本） | 5 failed / 17 passed / 3 skipped | 副本不实时，写后读断言失败 |
| 第 4 次（空闲期直连） | **21 passed / 3 skipped / 1 failed** | 唯一失败为 `database disk image is malformed`，并发读导致 |
| 第 5 次（本机同宿主直连，2026-11-15） | **22 passed / 3 skipped / 0 failed** | 后端与 pytest 均在本机同一文件系统访问临时库，无挂载卷锁冲突；3 项 MCP 用例因需 compose 网络跳过 |

最终 HTML：`reports/lesson-10/20261114T125424Z-online/report.html`（已检查：不含口令明文，`thu260002`、`Teach@2026` 计数为 0）。

### 2.1 第 5 轮：本机同宿主直连（可复现步骤）

不再经 Docker 挂载卷，改为本机同一文件系统运行后端与 pytest，彻底消除第 4 轮的跨进程 SQLite 锁冲突：

1. 临时库种子：`DATABASE_URL=sqlite:///$WORK/campusclaw.db` 下运行 `backend/dev_seed.py`（隔离目录，不触碰真实库）。
2. 学生 id 对齐：将 `20260002`（王芳，class 102）调整为 `id=3`，使 conftest 的 `id==3 且 class_id==102` 断言成立（仅临时库）。
3. 清除首次改密标志：`UPDATE users SET must_change_password=0`，否则业务接口返回 403「请先修改初始密码」。
4. 服务端配置 `MCP_TOKEN_KEY`（随机 32 字节 URL-safe base64），否则 `/api/mcp/servers` 登记返回 400。
5. 向 class 102 上传并索引一份 `.md` 材料（`is_indexed=1`），满足 `class102_material_id` 夹具。
6. 启动 `uvicorn main:app --port 8012`，运行：
   ```bash
   APITEST_BASE_URL=http://127.0.0.1:8012 APITEST_DB_PATH=$WORK/campusclaw.db \
   APITEST_TEACHER_ID=TEA001 APITEST_TEACHER_PASSWORD=... APITEST_STUDENT_ID=20260002 APITEST_STUDENT_PASSWORD=... \
   backend/.venv/bin/python -m pytest $(find apitest/cases -name '*.py' ! -name '__init__.py') -q -p no:cacheprovider -p no:randomly
   ```
   结果：`22 passed, 3 skipped in 1.26s`，0 failed / 0 error。

**结论**：第 4 轮的 `database disk image is malformed` 是「宿主机直连容器挂载卷」的 SQLite 并发问题，改到同宿主同一进程访问后消失；22 条可运行用例全部通过。剩余 3 条 MCP 用例硬编码 `http://mcp-tools:8090`（仅 compose 网络可解析），本机不经改 `/etc/hosts` 无法连通，保留 SKIPPED。

### 2.2 第 6 轮：compose 网络内运行（2026-11-16）

第 5 轮剩余 3 条 MCP 用例需要解析 `mcp-tools`，本轮改为在 compose 网络内运行，不修改用例、不改 hosts：

1. 临时库种子与对齐同 2.1 第 1–3 步，但数据库放在 **Docker 命名卷**（Linux 原生文件系统），不在 macOS 挂载卷上并发读写；卷属主显式改为 `10001:10001`。
2. 以当前提交的后端镜像启动隔离容器，接入 `campusclaw-group_default` 网络、别名 `online-api`，使用临时库、临时 `JWT_SECRET_KEY`/`MCP_TOKEN_KEY`、`ENABLE_DOCS=true`。
3. 教师上传并索引一份 class 102 材料（`material_id=1`，`is_indexed=true`）。
4. 测试运行器为一次性 Python 3.12 镜像（`uv sync --locked` 安装 pytest/requests/httpx），以 `--network campusclaw-group_default` 运行，`APITEST_BASE_URL=http://online-api:8000`、`APITEST_DB_PATH=/data/campusclaw.db`、`APITEST_MCP_TOKEN` 取自本机 `.env`。

结果：**24 passed / 1 skipped / 0 failed**（1.37s）。此前跳过的 MCP `GET.py` 连接用例与 `CHAIN.py` 技能命中/meta 用例均已真实通过；唯一跳过为 `CHAIN.py:102`「AI 生成服务不可用（DeepSeek Key 未配置或无效），无法验证模型提议调用 → ok 审计」，属环境限制，未计入通过。证据：`reports/lesson-10/20261116T161500Z-docker/online-pytest.txt`、`online-health.json`、`online-material.json`。

## 三、失败归因

1. **`database disk image is malformed` / `disk I/O error`**：macOS 宿主进程与容器同时读写同一挂载卷上的 SQLite 文件，DELETE journal 模式下锁与页缓存冲突。这不是业务缺陷，已在历史演示库复现过同类问题。
2. **只读副本方案不可用**：用例在 setup 读库、在断言中读“刚刚写入”的记录，副本不实时。
3. **学生 id 断言**：历史 cases 硬编码 id=3，`dev_seed` 先插入两名教师导致学生后移；已在临时库对齐，属测试资产与种子的历史假设差异。

## 四、第 4 轮非通过项明细（提取自 `report.html`）

| 结果 | 用例 ID | 原因 |
| --- | --- | --- |
| Failed | `cases/api/student/conversations/chat/POST.py::test_conversation_chat_sse` | `sqlite3.DatabaseError: database disk image is malformed`（第 60、71 行宿主机直连容器挂载 SQLite 并发冲突） |
| Skipped | `cases/api/mcp/CHAIN.py::test_chain_skill_hit_meta::setup` | 未提供 `APITEST_MCP_TOKEN`（须与服务端 `MCP_AUTH_TOKEN` 一致），跳过真实 `mcp-tools` 联调 |
| Skipped | `cases/api/mcp/CHAIN.py::test_chain_tool_ok_audit::setup` | 同上，未提供 `APITEST_MCP_TOKEN` |
| Skipped | `cases/api/mcp/GET.py::test_connect_then_tools_then_disconnect` | 同上，未提供 `APITEST_MCP_TOKEN` |

## 五、未完成与边界

- 第 5 轮本机同宿主直连为 **22 passed / 3 skipped / 0 failed**；第 6 轮在 compose 网络内为 **24 passed / 1 skipped / 0 failed**，此前 3 条 MCP 跳过中已有 2 条通过，剩余 1 条依赖真实/有效模型 Key（当前 `.env` 为空），**未计入通过**。任务 3.3 因此仍不勾为「全部用例通过」。
- 第 6 轮的运行方式（一次性运行器容器 + 隔离后端 + Docker 命名卷）已写入 2.2；未挂载真实 `./data`，未修改任何用例的硬编码地址，也未改 hosts。
- 本环境未挂载真实 `./data`，未写入真实教学库。
