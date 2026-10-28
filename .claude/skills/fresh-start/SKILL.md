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
