# 发布与回滚演练（2026-11-16）

- 性质：**本机隔离演练**，用临时副本，不触碰真实教学库，不对已有数据的库运行 `dev_seed`。
- 口径：证明“当前提交可构建、可分发、可备份恢复、可回滚到上一 tag”；**不宣称已完成正式发布**。远端 CI 已实跑但为红（run `43826707775`，`images` 跳过），因此远端镜像仓库、线上实例、另一名组员复核仍缺。
- 提交：`984c4c8cc6963bf315bd3f0820c4965043beed23`
- 证据目录：`reports/lesson-10/20261116T024000Z-clone-registry-rollback/`

## 一、备份与恢复（临时库 + 上传目录）

| 项 | 方法 | 结果 |
| --- | --- | --- |
| 数据库备份 | 对 `data/campusclaw.db` 以 `mode=ro` 打开，使用 SQLite online backup API 写入临时文件 | 34 张表；备份 2,695,168 字节；SHA-256 `809c2b588b86bcca2f4fe0410717e779c3eec2f6fb2eb3bb2d404879f9d0a6e3` |
| 完整性 | 源库、备份、恢复副本分别执行 `PRAGMA integrity_check` | 三者均为 `ok` |
| 行数指纹 | 逐表 `count(*)` 比较源库、备份、恢复副本 | 34 表全部相等；关键计数：users=63、materials=2、material_chunks=500、ai_question_logs=487、audit_logs=18、homeworks=1、homework_submissions=1、grade_tasks=2 |
| 恢复 | 备份复制为独立恢复副本后重新计算指纹 | 恢复副本与备份**字节相同**，行数相同，完整性 `ok` |
| 上传目录 | `rsync -a` 备份 `backend/uploads/` 后再恢复 | 9 个文件；源、备份、恢复三份 manifest 完全一致；manifest SHA-256 `e842548263e40b9e03515858649a5b4c77b4537b90c99d44b276e1cde9f6f8e2` |
| 真实库改动 | 仅只读连接；恢复与后续启动都使用临时副本 | **未修改**真实库与上传目录 |

说明：备份是演示库的一次性热备份，不含自动保留、异地存放、加密与清理策略；不能据此声称满足 RPO≤1 天或“最近 7 份”。

原始记录：`backup-restore.txt`。

## 二、镜像回滚到上一 tag

| 项 | 内容 |
| --- | --- |
| 回滚目标 | `37aecf9b52cc9663c6572f657ab05e8ad7f5a2d8`（上一已构建批次） |
| 方式 | 从该提交 `git archive` 导出临时目录；独立 `.env`、compose 项目名、端口 8098、临时数据目录；三业务镜像使用上一 tag；不重建、不影响主栈 |
| 数据 | 使用第一节的**恢复副本**作为 `/app/data/campusclaw.db`，验证上一版代码可读取恢复后的库 |
| 启动结果 | 七服务全部 Up；backend/frontend/mcp-tools/rabbitmq healthy；grading-worker/dispatcher Up |
| 入口 | `GET /health` 200（`database=ok`、`mcp_tools=ok`、`model=not_configured`）；`GET /login` 200 |
| 0 源码 | backend/mcp-tools/frontend 容器内 `.py=0` |
| 版本标签 | 三镜像 OCI `revision` 均为 `37aecf9b52cc9663c6572f657ab05e8ad7f5a2d8` |
| 耗时 | 从创建独立项目到 `/health` 200 约 26 秒（按 UTC 时间戳估算，仅本机） |
| 清理 | 回滚项目 `down -v`，临时目录删除，无残留容器/卷 |

原始记录：`rollback-up.txt`、`rollback-check.txt`、`rollback-health.json`。

## 三、回到当前版本

回滚演练使用独立项目，主栈全程未切换。演练后复核主栈：

- `GET http://127.0.0.1:8086/health` 200，依赖状态 `database=ok`、`mcp_tools=ok`、`model=not_configured`。
- backend/mcp-tools/frontend 容器内 `.py=0`，OCI `revision` 均为 `984c4c8cc6963bf315bd3f0820c4965043beed23`。
- 证据：`main-after-health.json`、`main-after-health.txt`。

## 四、本机镜像仓库分发（补充 4.2 的本机部分）

| 镜像 | RepoDigest | OCI revision | 容器内 `.py` |
| --- | --- | --- | --- |
| backend | `127.0.0.1:5001/campusclaw-backend@sha256:3275eeec2ffa7f0e02e6a313b07bb92bd5812f00653a418d9aa566b84786f73f` | `984c4c8…` | 0 |
| mcp-tools | `127.0.0.1:5001/campusclaw-mcp-tools@sha256:130a84fe2878715296d5051f3cbabf7dcd29b965990eb899972119bea787fc44` | `984c4c8…` | 0 |
| frontend | `127.0.0.1:5001/campusclaw-frontend@sha256:8b5778d9ac1dcdc05d273af33a5c26d4d8fc4f9ce44c63649567c8b36aac23f5` | `984c4c8…` | 0 |

方法：本机启动 `registry:2`（仅监听 `127.0.0.1:5001`），tag → push → pull 后记录 `RepoDigests`、OCI revision 并复验 0 源码；演练后删除 registry 容器。原始记录：`local-registry.txt`。

**边界**：这是本机 registry 链路演练，不等于已推送到远端仓库或 GHCR；没有 CI run、没有远端 digest 签名/保留策略、没有线上实例反查，4.2 仍为 BLOCKED。

## 五、结论与未覆盖

- 已完成：当前提交的临时库备份、恢复指纹核对、上传目录备份恢复；上一 tag 七服务回滚与入口健康；本机 registry push/pull digest。
- 未完成：正式发布审批、受控绿 CI（当前 run `43826707775` 为红，`images` 跳过）、远端镜像仓库/GHCR 推送与 digest 归档、线上部署与反查、另一名组员复核、自动备份保留与恢复时效指标。
- 因此本文只作为 release/rollback **演练证据**，不能把第10课 4.2 或“换机”标为完成。
