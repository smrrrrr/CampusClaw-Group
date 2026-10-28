---
name: release
description: 按 CampusClaw 部署运维规范发一次版本（门禁、备份、改版本号、重建、/health 验证、打标签、发布记录），以及按同一路径回滚。发版、打标签或演练回滚时使用。
---

# 按规范发一次版本

输入：新版本号 `X.Y.Z`、本次包含的已归档变更。

1. `make check` 全部 PASS；工作区干净，在 `main` 上。
2. 备份数据库（同技能 `data-change` 第 2 步）与 `backend/uploads/`。
3. 改 `backend/version.py` 的 `APP_VERSION = "X.Y.Z"`，README 文末加版本记录；提交，提交信息带 `Change:` / `Verify:` / `Evidence:` 三行。
4. `docker compose up -d --build`，等待 `docker compose ps` 中 backend 为 healthy；记录开始到 healthy 的耗时。
5. `curl -s http://localhost:${CAMPUSCLAW_PORT:-8080}/health`：`version` 等于 `X.Y.Z`，`status` 为 `ok`（`degraded` 需写明原因）。`docker compose logs backend --tail 20` 每行是 JSON 且带 `request_id`。
6. 打标签 `git tag -a vX.Y.Z -m "<一句话>"`；推送分支与标签前先征得组长同意。
7. 写 `docs/releases/YYYY-MM-DD-vX.Y.Z.md`：版本、包含的变更名、验证结论（第 4、5 步输出）。

回滚（每个迭代演练一次）：`git checkout <上一个标签>` → `docker compose up -d --build` → 若有表结构变化，恢复第 2 步备份 → `/health` 的 `version` 为旧版本。记录步骤与耗时到发布记录。

产出：版本提交、标签、发布记录。
