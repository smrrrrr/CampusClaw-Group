---
name: fresh-start
description: 在一台新机器上按 README 从零克隆、配置、启动 CampusClaw 并验证 /health，记录卡住的步骤。交叉评审（peer review）或怀疑“只在某台机器能跑”时使用。
---

# 从零启动一次

只按 README 操作；README 没写的步骤一律记为“卡点”，不要凭经验补。

1. 在新目录 `git clone` 仓库，切到 `main`。
2. `cp .env.example .env`，生成并填写 `JWT_SECRET_KEY`（`openssl rand -base64 32`）、`MCP_AUTH_TOKEN`、`MCP_TOKEN_KEY`（命令见 `.env.example` 注释）。模型 Key 可留空。
3. 需要组内数据时按 DEPLOYMENT.md 用数据包恢复脚本；不要运行 `dev_seed.py` 覆盖已有数据。
4. `docker compose up -d --build`，等待 backend 为 healthy。
5. `curl -s http://localhost:${CAMPUSCLAW_PORT:-8080}/health`：返回 JSON，`status` 为 `ok`，`version` 与 `backend/version.py` 一致。打开 `/login` 能看到登录页。
6. 开发依赖：`cd backend && uv sync`，`cd frontend && npm ci`，回到根目录 `make check` 全部 PASS。
7. 记录：机器与系统、每步耗时、卡点（哪一步、报错、怎么解决的）。卡点要改的是 README，不是口头说明。

产出：一份启动记录（写进 `docs/lesson-07/` 或对应变更的验证记录），以及对 README 的修改建议。

## 本机差异与结果记录

Windows 用 DEPLOYMENT.md / docs/local-setup-2026-11-04.md 的对应命令；端口以本次 .env 为准，不能假设一定8081或8083。先 docker compose config --quiet；仅空库可初始化，已有数据必须走新目录恢复。模型Key为空可以验证非生成功能；关键JWT缺失必须失败，MCP不可达的 degraded 与全依赖正常的 ok 分开记录。记录操作者、系统、提交、是否全新目录、实际耗时、health、门禁及卡点；模板/本机复跑不冒充另一名组员新机器成功。
