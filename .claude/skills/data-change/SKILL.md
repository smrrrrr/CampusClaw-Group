---
name: data-change
description: 按 CampusClaw 数据规范做一次表结构变更或数据删除（先备份、只加不改、可重跑、同步注释与规约、删除按副本清单逐项执行）。改 models.py/database.py 或处理删除请求时使用。
---

# 按规范做一次数据变更

输入：变更名、要加的表 / 字段，或要删除的数据范围。

1. 读 `docs/standards/07-数据规范.md`。
2. **先备份**：停写后复制 `${CAMPUSCLAW_DATA_DIR:-./data}/campusclaw.db` 为同目录下 `before-<动作>-<YYYYMMDD-HHMMSS>.db`，用 `PRAGMA integrity_check` 确认备份为 `ok`。不运行 `dev_seed.py`。
3. 表结构变更：
   - 新表：在 `models.py` 加模型，带 `created_at`（可改的表加 `updated_at`）与归属字段（`class_id` / `subject` / `teacher_id`），类文档字符串写用途与状态取值；
   - 存量表加列：在 `database.run_simple_migrations()` 里先 `PRAGMA table_info` 判断再 `ALTER TABLE ... ADD COLUMN`，保证可重跑；
   - 不删列、不改类型；需要删旧字段时另起变更（加 → 兼容 → 发布 → 删）。
4. 在变更 design.md 写回滚动作（通常是“恢复第 2 步的备份”），同步主规约中受影响的字段说明。
5. 删除请求：按 07 规范 §6 副本清单逐项处理（业务行 → 切片 → `uploads/` 文件 → 备份），每项记录结果。
6. 在临时库上跑一遍：对旧结构的库执行两次启动（验证可重跑），然后 `make check`。

产出：模型 / 迁移代码、备份文件名、回滚动作说明、`make check` 输出尾部。
