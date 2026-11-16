# Tasks

按项目规则先写规约再改代码：本变更的 proposal / design / spec delta 已落盘，实施范围仅限 `write_audit_log` 内部清洗与一条离线回归。

## 1. 实施

- [x] 1.1 在 `backend/services.py` 增加 `_AUDIT_TEXT_LIMITS` 常量表（`action` 64、`object_id` 128、`skill_id` 64、`request_path` 256、`ip_address` 64、`role` 20、`subject` 32）与 `_clean_audit_text(value, limit)` 函数：`None` 原样返回；控制字符 U+0000–U+001F、U+007F 替换为空格；按 `limit` 截断，不加省略标记。
- [x] 1.2 在 `write_audit_log` 构造 `AuditLog` 前，对上述 7 个文本字段逐个调用 `_clean_audit_text`；数值字段（`user_id`、`class_id`、`status_code`、`duration_ms`、`tokens`）与 `created_at` 保持原样。
- [x] 1.3 确认 `write_audit_log` 签名不变，4 处调用方无需改动；`main.py` 既有的手工 `[:256]`/`[:64]`/`[:128]` 保留为冗余防御。

## 2. 回归

- [x] 2.1 新增 `apitest/check_audit_field_bounds.py`，用临时库直接调用 `write_audit_log` 覆盖四个场景：超长截断到 128、控制字符替换为空格、正常值与 `None` 不变、数值字段不受影响。
- [x] 2.2 该检查断言 `_AUDIT_TEXT_LIMITS` 的键与值与 `models.py` 中 `AuditLog` 对应列的 `type.length` 一致，防止常量与模型漂移。
- [x] 2.3 `make check` 全通过，新检查纳入门禁。

## 3. 文档与收口

- [x] 3.1 更新 `reports/security-fix-lesson09-status-2026-11-16.md`：把 4.6 从"缺失"改为"已实现"，附本变更路径与提交号。
- [x] 3.2 在 `docs/standards/03-安全开发规范.md` 的审计相关处补一句指向本规约的字段上限要求（若该规范已有"转义与截断"表述则只补引用，不重复正文）。
- [x] 3.3 不修改 `security-fix-lesson09/tasks.md` 的勾选状态——该项属于历史变更，是否补勾由该变更的负责人裁定。

## 4. 边界

- 不新增数据库迁移，不修改 `AuditLog` 表结构。
- 不回溯清洗历史超长记录。
- 不放宽 `make check-security` 的任何判据。